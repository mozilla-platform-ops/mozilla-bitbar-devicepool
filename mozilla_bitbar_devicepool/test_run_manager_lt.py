# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.


import shutil
import signal
import logging
import time
import os
import sys
import subprocess
import argparse
import threading  # Added import

from mozilla_bitbar_devicepool import configuration_lt, logging_setup
from mozilla_bitbar_devicepool.lambdatest import job_config, status
from mozilla_bitbar_devicepool.lambdatest.job_tracker import JobTracker
from mozilla_bitbar_devicepool.taskcluster import get_taskcluster_pending_tasks


class TestRunManagerLT(object):
    # Constants at class level
    PROGRAM_LABEL = "tcdp"
    #
    STATE_STOP = "STATE_STOP"
    STATE_RUNNING = "STATE_RUNNING"
    #
    MODE_NO_OP = "MODE_NO_OP"
    MODE_RUN_NOTRACK = "MODE_RUN_NOTRACK"
    MODE_RUN_NOTRACK_WITH_CONCURRENCY = "MODE_RUN_NOTRACK_WITH_CONCURRENCY"
    MODE_RUN_NOTRACK_BACKGROUND_TASKS = "MODE_RUN_NOTRACK_BACKGROUND_TASKS"
    # TODO: increase this to 10, 20, 30 once we're more confident
    MAX_JOBS_TO_START_AT_ONCE = 10
    # lt api device states
    LT_DEVICE_STATE_ACTIVE = "active"
    LT_DEVICE_STATE_BUSY = "busy"
    # background task control
    # TODO: making this work when False is going to require more work...
    #     - our loop is too fast and we end up
    #       - overwriting dirs (handled within loop with path per job)
    #       - starting too many jobs... we don't detect that they've started yet (TODO: check state name they are in)
    WAIT_FOR_BACKGROUND_TASKS = True
    # Threading constants
    TC_MONITOR_INTERVAL = 30  # seconds
    LT_MONITOR_INTERVAL = 30  # seconds
    JOB_STARTER_INTERVAL = 10  # seconds

    def __init__(
        self,
        max_jobs_to_start=MAX_JOBS_TO_START_AT_ONCE,
        exit_wait=5,
        no_job_sleep=60,
        debug_mode=False,
    ):
        self.interrupt_signal_count = 0
        self.exit_wait = exit_wait
        self.no_job_sleep = no_job_sleep
        self.max_jobs_to_start = max_jobs_to_start
        self.state = self.STATE_RUNNING
        self.debug_mode = debug_mode
        self.config_object = configuration_lt.ConfigurationLt()
        self.config_object.configure()
        self.status_object = status.Status(self.config_object.lt_username, self.config_object.lt_access_key)

        # Replace single job_tracker with a dictionary of job trackers per project
        self.job_trackers = {}
        # Initialize job trackers for each project in config
        for project_name in self.config_object.config.get("projects", {}):
            self.job_trackers[project_name] = JobTracker(expiry_seconds=210)
        # Keep a default tracker for backward compatibility
        self.job_tracker = JobTracker(expiry_seconds=210)

        # Threading related initializations
        self.shared_data = {
            "tc_job_count": 0,
            "lt_active_devices": 0,
            "lt_device_selector": None,  # Store selector for job starter
            "current_project_name": None,  # Store project name for job starter
        }
        self.shared_data_lock = threading.Lock()
        self.shutdown_event = threading.Event()

        signal.signal(signal.SIGUSR2, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)

    def handle_signal(self, signalnum, frame):
        MAX_SIGNAL_COUNT = 3

        if signalnum == signal.SIGINT or signalnum == signal.SIGUSR2:
            # track how many times we've received the signal. at 3, exit immediately.
            self.interrupt_signal_count += 1
            if self.interrupt_signal_count < MAX_SIGNAL_COUNT:
                logging.info(" handle_signal: Signalling threads to stop, will exit when safe.")
                logging.info(
                    f"will exit immediately if signal received {MAX_SIGNAL_COUNT - self.interrupt_signal_count} more times."
                )
                self.shutdown_event.set()  # Signal threads to stop
            else:
                logging.info(f" handle_signal: received signal {MAX_SIGNAL_COUNT} times, exiting immediately")
                # Force exit if threads don't stop quickly
                os._exit(1)  # Use os._exit for immediate termination

    # Helper methods for project-specific job trackers
    def get_job_tracker(self, project_name):
        """Get the job tracker for a specific project, creating it if it doesn't exist."""
        if project_name not in self.job_trackers:
            self.job_trackers[project_name] = JobTracker(expiry_seconds=210)
        return self.job_trackers[project_name]

    def add_jobs(self, count, project_name=None):
        """Add jobs to the specified project tracker or default tracker if no project specified."""
        if project_name and project_name in self.job_trackers:
            self.job_trackers[project_name].add_jobs(count)
        else:
            # For backward compatibility
            self.job_tracker.add_jobs(count)

    def get_active_job_count(self, project_name=None):
        """Get active job count from the specified project tracker or default tracker."""
        if project_name and project_name in self.job_trackers:
            return self.job_trackers[project_name].get_active_job_count()
        # For backward compatibility
        return self.job_tracker.get_active_job_count()

    # jmaher poc replice
    def single_project_single_thread_single_job(self):
        project_source_dir = os.path.dirname(os.path.realpath(__file__))
        project_root_dir = os.path.abspath(os.path.join(project_source_dir, ".."))
        user_script_golden_dir = os.path.join(project_source_dir, "lambdatest", "user_script")
        test_run_dir = "/tmp/mozilla-lt-devicepool-job-dir"
        test_run_file = os.path.join(test_run_dir, "hyperexecute.yaml")

        test_run_dir = "/tmp/mozilla-lt-devicepool-job-dir"
        test_run_file = os.path.join(test_run_dir, "hyperexecute.yaml")
        while True:
            # only a single project for now, so load that up
            current_project = self.config_object.config["projects"]["a55-perf"]

            tc_worker_type = current_project["TC_WORKER_TYPE"]
            tc_client_id = current_project["TASKCLUSTER_CLIENT_ID"]
            tc_client_key = current_project["TASKCLUSTER_ACCESS_TOKEN"]
            lt_device_selector = current_project["lt_device_selector"]

            # TODO: verify this apk is ok, update the apk if needed, and store/use it's app_id
            lt_app_url = "lt://APP1016023521741987818221818"

            # remove /tmp/user_script dir
            shutil.rmtree(test_run_dir, ignore_errors=True)
            # create /tmp/mozilla-lt-devicepool-job-dir dir
            os.makedirs(test_run_dir, exist_ok=True)

            # copy user_script_golden_dir to correct path using python shutil
            shutil.copytree(user_script_golden_dir, os.path.join(test_run_dir, "user_script"))

            cmd_env = os.environ.copy()
            cmd_env["LT_USERNAME"] = self.config_object.lt_username
            cmd_env["LT_ACCESS_KEY"] = self.config_object.lt_access_key

            # set the device type, OS, and optionally UDID for this job
            #
            # for now we have a single pool of devices
            # device_type_and_os = "Galaxy A51-11"
            # device_type_and_os = "Galaxy A55 5G-14"
            device_type_and_os = lt_device_selector

            command_string = f"{project_root_dir}/hyperexecute"

            job_config.write_config(
                tc_client_id,
                tc_client_key,
                tc_worker_type,
                lt_app_url,
                device_type_and_os,
                udid=None,
                concurrency=1,
                path=test_run_file,
            )

            logging.info("starting job...")
            # Use test_mode instead of hardcoded DEBUG
            if self.debug_mode:
                logging.info(f"would be running command: '{command_string}' in path '{test_run_dir}'...")
                logging.info("sleeping 30 seconds (to simulate starting job)...")
                time.sleep(30)
            else:
                logging.info(f"running: '{command_string}' in path '{test_run_dir}'...")
                start_time = time.time()
                # NOTE: background so we can do this faster or set concurrencty in the YAML?
                #   - can only get 1-2 jobs going in parallel with trivial tasks
                #   - for concurrency to work, would we need to emit multiple test targets (1:1 with concurrency?)
                # start_new_session=True ensures process ignores ctrl-c sent to this process (so it cleans up)
                subprocess.run(
                    command_string,
                    shell=True,
                    env=cmd_env,
                    cwd=test_run_dir,
                    start_new_session=True,
                )
                end_time = time.time()
                logging.info(f"job took {round(end_time - start_time, 2)} seconds")
            # take a short break
            time.sleep(5)

    def run_single_project_single_thread_multi_job(self, max_jobs_to_start=None, foreground=False, mode=None):
        if mode is None:
            mode = self.MODE_RUN_NOTRACK
        # default the value
        if max_jobs_to_start is None:
            max_jobs_to_start = self.MAX_JOBS_TO_START_AT_ONCE
        # base on __file__ to get the project root dir
        project_source_dir = os.path.dirname(os.path.realpath(__file__))
        project_root_dir = os.path.abspath(os.path.join(project_source_dir, ".."))
        user_script_golden_dir = os.path.join(project_source_dir, "lambdatest", "user_script")

        test_run_dir = "/tmp/mozilla-lt-devicepool-job-dir"
        test_run_file = os.path.join(test_run_dir, "hyperexecute.yaml")

        # TODO?: if we do multithreading, use messaging vs shared object with locks

        # TODO?: once we can target multiple specific devices in hyperexecute.yaml or implement single
        #         device targeting/tracking, we can have multiple projects within the same
        #         device_type-os_version pool.
        #
        # hard code for now
        current_project_name = "a55-perf"
        logging.info(f"current project: {current_project_name}")

        logging.info(f"entering run loop (execution mode is {mode})...")
        while self.state == self.STATE_RUNNING:
            current_project = self.config_object.config["projects"][current_project_name]

            tc_worker_type = current_project["TC_WORKER_TYPE"]
            tc_client_id = current_project["TASKCLUSTER_CLIENT_ID"]
            tc_client_key = current_project["TASKCLUSTER_ACCESS_TOKEN"]
            lt_device_selector = current_project["lt_device_selector"]
            # debug
            # print(f"tc_client_id: {tc_client_id}")
            # print(f"tc_client_key: {tc_client_key}")

            tc_job_count = get_taskcluster_pending_tasks("proj-autophone", tc_worker_type, verbose=False)
            # gather data targeting the current project or current device_type_and_os
            label_filters = [self.PROGRAM_LABEL, current_project_name]
            running_job_count = self.status_object.get_running_job_count(label_filter_arr=label_filters)
            initiated_job_count = self.status_object.get_initiated_job_count(label_filter_arr=label_filters)
            active_devices_in_requested_config = self.status_object.get_device_state_count(
                lt_device_selector, self.LT_DEVICE_STATE_ACTIVE
            )

            # Get count of recently started jobs that are still in startup phase
            recently_started_jobs = self.get_active_job_count(current_project_name)

            # New calculation that includes recently started jobs
            # TODO: should this include initiated_job_count?
            tc_jobs_not_handled = tc_job_count - recently_started_jobs

            # TODO: print out how this is calculatted

            # tc data
            logging.info(f"tc_job_count: {tc_job_count}")
            # lt data
            logging.debug(f"running_job_count: {running_job_count}")
            logging.debug(f"initiated job count: {initiated_job_count}")
            logging.debug(f"self.max_jobs_to_start: {self.max_jobs_to_start}")
            logging.debug(f"max_jobs_to_start: {self.max_jobs_to_start}")
            logging.debug(
                f"active_devices_in_requested_config ({lt_device_selector}): {active_devices_in_requested_config}"
            )
            # state data
            logging.debug(f"recently_started_jobs: {recently_started_jobs}")
            # merged data
            logging.debug(f"tc_jobs_not_handled: {tc_jobs_not_handled}")

            # limit the amount of jobs we start to a local and global max
            jobs_to_start = min(tc_jobs_not_handled, self.max_jobs_to_start, max_jobs_to_start)
            logging.debug(f"min of tc_jobs_not_handled, self.max_jobs_to_start, max_jobs_to_start is {jobs_to_start}")
            # don't try to start more jobs than free devices
            jobs_to_start = min(jobs_to_start, active_devices_in_requested_config)
            logging.debug(f"min of jobs_to_start and active_devices_in_requested_config is {jobs_to_start}")

            logging.info(f"jobs_to_start: {jobs_to_start}")

            if jobs_to_start <= 0:
                logging.info(
                    f"no unhandled jobs (no tc jobs, no active lt devices, or lt jobs already started), sleeping {self.no_job_sleep}s..."
                )
                time.sleep(self.no_job_sleep)
            else:
                # eternal APK provided by LT
                lt_app_url = "lt://proverbial-android"

                # remove /tmp/user_script dir
                shutil.rmtree(test_run_dir, ignore_errors=True)
                # create /tmp/mozilla-lt-devicepool-job-dir dir
                os.makedirs(test_run_dir, exist_ok=True)

                # copy user_script_golden_dir to correct path using python shutil
                shutil.copytree(user_script_golden_dir, os.path.join(test_run_dir, "user_script"))

                cmd_env = os.environ.copy()
                cmd_env["LT_USERNAME"] = self.config_object.lt_username
                cmd_env["LT_ACCESS_KEY"] = self.config_object.lt_access_key

                # set the device type, OS, and optionally UDID for this job
                #
                device_type_and_os = lt_device_selector
                # udid = None
                # TODO?: manage device state and specify UDID of exact device to target for each job

                # hyperexecute job labels
                #
                # indicate this is scheduled by this program
                #   - use new name 'mozilla-taskcluster-devicepool'
                labels_csv = self.PROGRAM_LABEL
                # add the workerType to the labels
                #   - we really want the lt side name for this... they turn out to be the same
                # labels_csv += f",{shorten_worker_type(tc_worker_type)}"
                labels_csv += f",{current_project_name}"
                # TODO: revisit this decision in a bit
                #   - not adding device type because it's largely redundant given current_project_name
                # add the device type to the labels
                # dtao_underscore = device_type_and_os.replace(" ", "_")
                # labels_csv += f",{dtao_underscore}"
                # TODO?: enable adding udid to the labels?
                # if udid:
                #     labels_csv += f",{udid}"

                # lt user and lt key are passsed in via env vars
                #   old: command_string = f"{project_root_dir}/hyperexecute --user \
                #           '{self.config_object.lt_username}' --key '{self.config_object.lt_api_key}'"
                labels_arg = f"--labels '{labels_csv}'"
                extra_flags = "--exclude-external-binaries"

                if foreground:
                    command_string = f"{project_root_dir}/hyperexecute {labels_arg} {extra_flags} "
                else:
                    command_string = f"{project_root_dir}/hyperexecute --no-track {labels_arg} {extra_flags}"

                current_mode = mode
                if jobs_to_start <= 0:
                    logging.info("no jobs to start, setting mode MODE_NO_OP...")
                    current_mode = self.MODE_NO_OP

                if current_mode == self.MODE_RUN_NOTRACK:
                    # start the desired number of jobs (concurrency: 1)

                    # create hyperexecute.yaml specific to each queue
                    job_config.write_config(
                        tc_client_id,
                        tc_client_key,
                        tc_worker_type,
                        lt_app_url,
                        device_type_and_os,
                        udid=None,
                        concurrency=1,
                        path=test_run_file,
                    )

                    outer_start_time = time.time()
                    for i in range(jobs_to_start):
                        logging.info(f"starting job {i + 1} of {jobs_to_start}...")
                        # Use test_mode instead of hardcoded DEBUG
                        if self.debug_mode:
                            logging.info(f"would be running command: '{command_string}' in path '{test_run_dir}'...")
                            logging.info("sleeping 30 seconds (to simulate starting job)...")
                            time.sleep(30)
                        else:
                            logging.info(f"running: '{command_string}' in path '{test_run_dir}'...")
                            start_time = time.time()
                            # NOTE: background so we can do this faster or set concurrencty in the YAML?
                            #   - can only get 1-2 jobs going in parallel with trivial tasks
                            #   - for concurrency to work, would we need to emit multiple test targets (1:1 with concurrency?)
                            # start_new_session=True ensures process ignores ctrl-c sent to this process (so it cleans up)
                            subprocess.run(
                                command_string,
                                shell=True,
                                env=cmd_env,
                                cwd=test_run_dir,
                                start_new_session=True,
                            )
                            end_time = time.time()
                            logging.info(
                                f"starting job {i + 1} of {jobs_to_start} took {round(end_time - start_time, 2)} seconds"
                            )
                            if self.state == self.STATE_STOP:
                                break
                    outer_end_time = time.time()
                    # Record the jobs we just started
                    self.add_jobs(jobs_to_start, current_project_name)
                    logging.info(
                        f"starting {jobs_to_start} jobs took {round(outer_end_time - outer_start_time, 2)} seconds"
                    )
                elif current_mode == self.MODE_RUN_NOTRACK_BACKGROUND_TASKS:
                    # Background tasks mode - starts all tasks concurrently
                    logging.info(f"Starting {jobs_to_start} jobs in background mode...")

                    outer_start_time = time.time()
                    processes = []

                    output_arr = []
                    for i in range(jobs_to_start):
                        logging.info(f"Launching background job {i + 1} of {jobs_to_start}...")

                        # we need unique paths or we'll overwrite the dir we're using in a backgrounded task
                        test_run_dir = f"/tmp/mozilla-lt-devicepool-job-dir.{i}"
                        test_run_file = os.path.join(test_run_dir, "hyperexecute.yaml")

                        # this is done at the start of this function, but with the non unique paths
                        # so we need to redo.
                        #
                        # remove /tmp/user_script dir
                        shutil.rmtree(test_run_dir, ignore_errors=True)
                        # create /tmp/mozilla-lt-devicepool-job-dir dir
                        os.makedirs(test_run_dir, exist_ok=True)
                        # copy user_script_golden_dir to correct path using python shutil
                        shutil.copytree(
                            user_script_golden_dir,
                            os.path.join(test_run_dir, "user_script"),
                        )

                        job_config.write_config(
                            tc_client_id,
                            tc_client_key,
                            tc_worker_type,
                            lt_app_url,
                            device_type_and_os,
                            udid=None,
                            concurrency=1,
                            path=test_run_file,
                        )

                        if self.debug_mode:
                            logging.info(f"Would run command: '{command_string}' in path '{test_run_dir}'...")
                            time.sleep(1)  # Just a short delay to simulate starting job
                        else:
                            # Start process in background
                            process = subprocess.Popen(
                                command_string,
                                shell=True,
                                env=cmd_env,
                                cwd=test_run_dir,
                                start_new_session=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                            )
                            processes.append(process)
                            output_arr.append(None)  # Initialize output slot
                            logging.info(f"Started background job {i + 1} with PID {process.pid}")

                        if self.state == self.STATE_STOP:
                            break

                    # Wait for processes to complete if configured to do so
                    if self.WAIT_FOR_BACKGROUND_TASKS and processes:
                        logging.info(f"Waiting for {len(processes)} background tasks to complete...")

                        # Initialize output array with None values
                        output_arr = [None] * len(processes)
                        remaining_processes = list(enumerate(processes))

                        # Wait for all processes to complete
                        while remaining_processes:
                            # Check each process without blocking
                            still_running = []
                            for i, process in remaining_processes:
                                if process.poll() is None:
                                    # Process is still running
                                    still_running.append((i, process))
                                else:
                                    # Process completed, collect output
                                    stdout, stderr = process.communicate()
                                    output_arr[i] = {
                                        "stdout": stdout.decode("utf-8") if stdout else "",
                                        "stderr": stderr.decode("utf-8") if stderr else "",
                                        "returncode": process.returncode,
                                    }
                                    logging.info(
                                        f"Background job {i + 1} completed with return code {process.returncode}"
                                    )

                            # Update the remaining processes list
                            remaining_processes = still_running

                            # If processes are still running, sleep briefly before checking again
                            if remaining_processes:
                                time.sleep(0.5)

                        # Display output from all completed processes
                        for i, output in enumerate(output_arr):
                            if output:  # Skip any None entries
                                logging.info(
                                    f"Output for job {i + 1} (rc is {output['returncode']}):\nSTDOUT: {output['stdout']}\nSTDERR: {output['stderr']}"
                                )

                    outer_end_time = time.time()
                    # Record the jobs we just started
                    self.add_jobs(jobs_to_start, current_project_name)
                    logging.info(
                        f"Launching {len(processes) if not self.debug_mode else jobs_to_start} background jobs took {round(outer_end_time - outer_start_time, 2)} seconds"
                    )
                elif current_mode == self.MODE_RUN_NOTRACK_WITH_CONCURRENCY:
                    # start the desired number of jobs (concurrency: jobs_to_start)
                    #
                    # issues:
                    #   - doesn't work

                    # create hyperexecute.yaml specific to each queue
                    job_config.write_config(
                        tc_client_id,
                        tc_client_key,
                        tc_worker_type,
                        lt_app_url,
                        device_type_and_os,
                        udid=None,
                        concurrency=jobs_to_start,
                        path=test_run_file,
                    )

                    logging.info(f"starting job with concurrency {jobs_to_start}...")
                    # Use test_mode instead of hardcoded DEBUG
                    if self.debug_mode:
                        logging.info(f"would be running command: '{command_string}' in path '{test_run_dir}'...")
                        logging.info("sleeping 30 seconds (to simulate starting job)...")
                        time.sleep(30)
                    else:
                        logging.info(f"running: '{command_string}' in path '{test_run_dir}'...")
                        start_time = time.time()
                        # NOTE: background so we can do this faster or set concurrencty in the YAML?
                        #   - can only get 1-2 jobs going in parallel with trivial tasks
                        #   - for concurrency to work, would we need to emit multiple test targets (1:1 with concurrency?)
                        # start_new_session=True ensures process ignores ctrl-c sent to this process (so it cleans up)
                        subprocess.run(
                            command_string,
                            shell=True,
                            env=cmd_env,
                            cwd=test_run_dir,
                            start_new_session=True,
                        )
                        end_time = time.time()
                        logging.info(f"starting job took {round(end_time - start_time, 2)} seconds")
                        if self.state == self.STATE_STOP:
                            break

                    # Record the jobs we just started
                    self.add_jobs(jobs_to_start, current_project_name)
                    if self.state == self.STATE_STOP:
                        break
                elif current_mode == self.MODE_NO_OP:
                    # no op mode (used to get to the sleep)
                    logging.info("mode 3: no op mode")
                else:
                    raise ValueError(f"unknown mode: {current_mode}")

            if self.state == self.STATE_STOP:
                break
            time.sleep(self.exit_wait)
            if self.state == self.STATE_STOP:
                break

    # --- Multithreaded Implementation ---

    def _taskcluster_monitor_thread(self):
        """Monitors Taskcluster pending tasks for all projects."""
        logging_header = "[TC Monitor]"
        # logging.info(f"{logging_header} Thread started.")

        # Initialize projects structure in shared data
        with self.shared_data_lock:
            if "projects" not in self.shared_data:
                self.shared_data["projects"] = {}

            # Initialize all projects
            for project_name, project_config in self.config_object.config["projects"].items():
                if project_name not in self.shared_data["projects"]:
                    self.shared_data["projects"][project_name] = {
                        "lt_device_selector": project_config.get("lt_device_selector", None),
                        "tc_job_count": 0,
                        "lt_active_devices": 0,
                    }

        while not self.shutdown_event.is_set():
            # For each project, get taskcluster job count
            for project_name, project_config in self.config_object.config["projects"].items():
                try:
                    tc_worker_type = project_config.get("TC_WORKER_TYPE")
                    if tc_worker_type:
                        # logging.info(f"{logging_header} Getting queue count for for {project_name} - {tc_worker_type}")
                        # TODO: Make provisioner name dynamic if needed
                        tc_job_count = get_taskcluster_pending_tasks("proj-autophone", tc_worker_type, verbose=False)
                        with self.shared_data_lock:
                            if "projects" in self.shared_data and project_name in self.shared_data["projects"]:
                                self.shared_data["projects"][project_name]["tc_job_count"] = tc_job_count
                        if tc_job_count > 0:
                            logging.debug(
                                f"{logging_header} Found {tc_job_count} pending tasks for {project_name} ({tc_worker_type})"
                            )
                        else:
                            logging.debug(f"{logging_header} No pending tasks for {project_name} ({tc_worker_type})")
                except Exception as e:
                    logging.error(f"{logging_header} Error fetching TC tasks for {project_name}: {e}", exc_info=True)

            # Wait for the specified interval or until shutdown is signaled
            self.shutdown_event.wait(self.TC_MONITOR_INTERVAL)

        logging.info("{logging_header} Thread stopped.")

    def _lambdatest_monitor_thread(self):
        """Monitors LambdaTest device status for all projects."""
        # logging.info("[LT Monitor] Thread started.")

        # Initialize projects structure in shared data
        with self.shared_data_lock:
            if "projects" not in self.shared_data:
                self.shared_data["projects"] = {}

            # Initialize all projects
            for project_name, project_config in self.config_object.config["projects"].items():
                if project_name not in self.shared_data["projects"]:
                    self.shared_data["projects"][project_name] = {
                        "lt_device_selector": project_config.get("lt_device_selector", None),
                        "tc_job_count": 0,
                        "lt_active_devices": 0,
                        "available_devices": [],  # List to store detailed device info
                    }

        while not self.shutdown_event.is_set():
            # Get entire device list once - we'll filter it for each project
            try:
                device_list = self.status_object.get_device_list()
            except Exception as e:
                logging.error(f"[LT Monitor] Error fetching device list: {e}", exc_info=True)
                device_list = {}

            # For each project, filter the device list based on the project's device_groups
            for project_name, project_config in self.config_object.config["projects"].items():
                try:
                    lt_device_selector = project_config.get("lt_device_selector")
                    if lt_device_selector:
                        active_devices = 0
                        available_devices = []

                        # Only continue if there's a device_groups config for this project
                        if project_name in self.config_object.config.get("device_groups", {}):
                            project_device_group = self.config_object.config["device_groups"][project_name]

                            # Now iterate through all devices
                            for device_type in device_list:
                                for udid, state in device_list[device_type].items():
                                    # Only count the device if it's active AND in this project's device group
                                    if state == self.LT_DEVICE_STATE_ACTIVE and udid in project_device_group:
                                        active_devices += 1
                                        available_devices.append(udid)

                        with self.shared_data_lock:
                            if "projects" in self.shared_data and project_name in self.shared_data["projects"]:
                                self.shared_data["projects"][project_name]["lt_active_devices"] = active_devices
                                self.shared_data["projects"][project_name]["available_devices"] = available_devices

                        logging.debug(
                            f"[LT Monitor] Found {active_devices} active devices for '{project_name}' ({lt_device_selector}) filtered by device_groups"
                        )
                except Exception as e:
                    logging.error(f"[LT Monitor] Error processing devices for {project_name}: {e}", exc_info=True)

            self.shutdown_event.wait(self.LT_MONITOR_INTERVAL)

        logging.info("LambdaTest monitor thread stopped.")

    def _job_starter_thread(self, project_name):
        """Starts jobs based on monitored data for a specific project."""

        logging_header = f"[Job Starter] {project_name:>10}:"

        # logging.info(
        #     f"{logging_header} {len(self.config_object.config['device_groups'][project_name])} devices configured.]"
        # )
        project_source_dir = os.path.dirname(os.path.realpath(__file__))
        project_root_dir = os.path.abspath(os.path.join(project_source_dir, ".."))
        user_script_golden_dir = os.path.join(project_source_dir, "lambdatest", "user_script")

        try:
            current_project = self.config_object.config["projects"][project_name]
            tc_worker_type = current_project["TC_WORKER_TYPE"]
            tc_client_id = current_project["TASKCLUSTER_CLIENT_ID"]
            tc_client_key = current_project["TASKCLUSTER_ACCESS_TOKEN"]
            lt_device_selector = current_project["lt_device_selector"]

            # Store selector for this project
            with self.shared_data_lock:
                if "projects" not in self.shared_data:
                    self.shared_data["projects"] = {}
                if project_name not in self.shared_data["projects"]:
                    self.shared_data["projects"][project_name] = {
                        "lt_device_selector": lt_device_selector,
                        "tc_job_count": 0,
                        "lt_active_devices": 0,
                        "available_devices": [],
                    }
        except KeyError as e:
            logging.error(f"{logging_header} Missing config: {e}. Thread exiting.")
            return

        while not self.shutdown_event.is_set():
            tc_job_count = 0
            active_devices = 0
            available_devices = []

            # Try to get device data for this project
            with self.shared_data_lock:
                if "projects" in self.shared_data and project_name in self.shared_data["projects"]:
                    project_data = self.shared_data["projects"][project_name]
                    tc_job_count = project_data.get("tc_job_count", 0)
                    active_devices = project_data.get("lt_active_devices", 0)
                    available_devices = project_data.get(
                        "available_devices", []
                    ).copy()  # Copy to avoid modification issues

            # If we don't have data yet, try to fetch it directly
            if tc_job_count == 0:
                try:
                    tc_job_count = get_taskcluster_pending_tasks("proj-autophone", tc_worker_type, verbose=False)
                    with self.shared_data_lock:
                        self.shared_data["projects"][project_name]["tc_job_count"] = tc_job_count
                except Exception as e:
                    logging.error(f"{logging_header} {project_name}] Error fetching TC tasks: {e}")

            if not available_devices:
                # normal case... do nohting
                pass

            # Get count of recently started jobs that are still in startup phase for this project
            # Use the project-specific job tracker
            recently_started_jobs = self.get_active_job_count(project_name)
            tc_jobs_not_handled = tc_job_count - recently_started_jobs

            # logging.info(
            #     f"{logging_header} TC Jobs: {tc_job_count}, Active LT Devs: {active_devices}, "
            #     f"Recently Started: {recently_started_jobs}, Need Handling: {tc_jobs_not_handled}"
            # )

            jobs_to_start = min(tc_jobs_not_handled, self.max_jobs_to_start, len(available_devices))
            jobs_to_start = max(0, jobs_to_start)  # Ensure non-negative

            # logging.info(f"{logging_header} Calculated jobs_to_start: {jobs_to_start}")

            logging.info(
                f"{logging_header} TC Jobs: {tc_job_count:>4}, Configured LT Devs: {len(self.config_object.config['device_groups'][project_name]):>3}, Active LT Devs: {active_devices:>3}, "
                f"Recently Started: {recently_started_jobs:>3}, Need Handling: {tc_jobs_not_handled:>3}, Jobs To Start: {jobs_to_start:>3}"
            )

            if jobs_to_start > 0:
                # --- Start Jobs (using background task logic) ---
                logging.info(f"{logging_header} Starting {jobs_to_start} jobs in background...")
                lt_app_url = "lt://proverbial-android"  # Eternal APK

                cmd_env = os.environ.copy()
                cmd_env["LT_USERNAME"] = self.config_object.lt_username
                cmd_env["LT_ACCESS_KEY"] = self.config_object.lt_access_key

                labels_csv = f"{self.PROGRAM_LABEL},{project_name}"
                labels_arg = f"--labels '{labels_csv}'"
                extra_flags = "--exclude-external-binaries"
                base_command_string = f"{project_root_dir}/hyperexecute --no-track {labels_arg} {extra_flags}"

                # outer_start_time = time.time()
                processes_started = 0

                # Track which devices we've assigned
                # assigned_devices = []

                for i in range(jobs_to_start):
                    if self.shutdown_event.is_set():
                        logging.info(f"{logging_header} Shutdown signaled during job starting loop.")
                        break

                    # Get next available device that hasn't been assigned yet
                    device_udid = None
                    for d in available_devices:
                        # only use the udid if it's assigned to the project
                        if d in self.config_object.config["device_groups"][project_name]:
                            device_udid = d
                            # remove the device from available devices to avoid reusing it
                            available_devices.remove(d)
                            break

                    if not device_udid:
                        logging.warning(f"{logging_header} No more available devices to assign!")
                        break

                    test_run_dir = f"/tmp/mozilla-lt-devicepool-job-dir.{project_name}.{time.time_ns()}"  # Project-specific unique dir
                    test_run_file = os.path.join(test_run_dir, "hyperexecute.yaml")

                    try:
                        # Setup job directory
                        shutil.rmtree(test_run_dir, ignore_errors=True)
                        os.makedirs(test_run_dir, exist_ok=True)
                        shutil.copytree(
                            user_script_golden_dir,
                            os.path.join(test_run_dir, "user_script"),
                        )

                        # Write config with specific device IP
                        job_config.write_config(
                            tc_client_id,
                            tc_client_key,
                            tc_worker_type,
                            lt_app_url,
                            lt_device_selector,
                            udid=device_udid,  # Use device UDID if available
                            concurrency=1,  # Each job is separate
                            path=test_run_file,
                        )

                        device_info = f"{device_udid}"

                        if self.debug_mode:
                            logging.info(
                                f"{logging_header} Would run command: '{base_command_string}' in path '{test_run_dir}'..."
                            )
                            logging.info(f"{logging_header} Would target device: {device_info}")
                            time.sleep(0.1)  # Simulate tiny delay
                        else:
                            # Start process in background
                            logging.info(
                                f"{logging_header} Launching job {i + 1}/{jobs_to_start} targeting device: {device_info}"
                            )
                            process = subprocess.Popen(
                                base_command_string,
                                shell=True,
                                env=cmd_env,
                                cwd=test_run_dir,
                                start_new_session=True,
                                stdout=subprocess.DEVNULL,  # Discard output for background tasks
                                stderr=subprocess.DEVNULL,
                            )
                            logging.debug(f"{logging_header} Started background job {i + 1} with PID {process.pid}")
                        processes_started += 1

                    except Exception as e:
                        logging.error(f"{logging_header} Error starting job {i + 1}: {e}", exc_info=True)
                        # Clean up potentially partially created dir
                        shutil.rmtree(test_run_dir, ignore_errors=True)

                # outer_end_time = time.time()
                if processes_started > 0 and not self.debug_mode:
                    self.add_jobs(processes_started, project_name)
                    # logging.info(
                    #     f"{logging_header} Launched {processes_started} background jobs in {round(outer_end_time - outer_start_time, 2)} seconds"
                    # )
                # --- End Start Jobs ---
            else:
                # logging.info(f"{logging_header} No jobs to start. Sleeping.")
                pass

            # Wait before next check or until shutdown
            self.shutdown_event.wait(self.JOB_STARTER_INTERVAL)

        logging.info(f"Job starter thread for {project_name} stopped.")

    def run_multithreaded(self):
        """Runs the manager with separate threads for monitoring and job starting for each project."""
        logging.info("[Main] Starting Test Run Manager in multithreaded mode...")

        # Create monitor threads
        tc_monitor = threading.Thread(target=self._taskcluster_monitor_thread, name="TC Monitor")
        lt_monitor = threading.Thread(target=self._lambdatest_monitor_thread, name="LT Monitor")

        # Start monitor threads
        tc_monitor.start()
        logging.info("[Main] Started TC Monitor thread.")
        lt_monitor.start()
        logging.info("[Main] Started LT Monitor thread.")

        # Give monitors a moment to potentially fetch initial data
        time.sleep(2)

        # Create and start a job starter thread for each project
        job_starters = []
        for project_name in self.config_object.config["projects"]:
            job_starter = threading.Thread(
                target=self._job_starter_thread, args=(project_name,), name=f"Job Starter - {project_name}"
            )
            job_starters.append(job_starter)
            job_starter.start()
            logging.info(f"[Main] Started job starter thread for project: {project_name}")

        # Keep main thread alive until shutdown is signaled
        logging.info("[Main] Waiting for shutdown signal...")
        self.shutdown_event.wait()
        logging.info("[Main] Shutdown signal received. Waiting for threads to join...")

        # Wait for threads to finish
        tc_monitor.join(timeout=self.TC_MONITOR_INTERVAL + 5)
        lt_monitor.join(timeout=self.LT_MONITOR_INTERVAL + 5)

        for i, job_starter in enumerate(job_starters):
            job_starter.join(timeout=self.JOB_STARTER_INTERVAL + 10)  # Give starter a bit more time
            if job_starter.is_alive():
                logging.warning(f"[Main] Job starter thread {i} did not exit cleanly.")

        logging.info("[Main] All threads joined. Exiting.")
        if tc_monitor.is_alive():
            logging.warning("[Main] TC monitor thread did not exit cleanly.")
        if lt_monitor.is_alive():
            logging.warning("[Main] LT monitor thread did not exit cleanly.")


def parse_args(action_array):
    actions_str = ", ".join(action_array)
    # trim the last comma if more than one action
    if len(action_array) > 1:
        actions_str = actions_str[:-2]

    parser = argparse.ArgumentParser(description="Test Run Manager for LambdaTest")
    parser.add_argument(
        "action",
        nargs="?",
        # meta="action",
        # choices=["start-test-run-manager"],
        help=f"Action to perform (e.g. {actions_str})",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode without executing commands.",
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging level. Defaults to INFO.",
    )
    return parser.parse_args()


def main():
    # Parse command line arguments
    available_actions = ["start-test-run-manager"]
    args = parse_args(available_actions)

    # Configure logging explicitly
    logging_setup.setup_logging(args.log_level)

    if args.action == "start-test-run-manager":
        # logging is now properly configured
        trmlt = TestRunManagerLT(debug_mode=args.debug)

        # start the main run loop using background tasks mode
        # trmlt.run_single_project_single_thread_multi_job(
        #     # mode=trmlt.MODE_RUN_NOTRACK_BACKGROUND_TASKS
        #     mode=trmlt.MODE_RUN_NOTRACK_WITH_CONCURRENCY,
        # )

        # Start the main run loop using the multithreaded runner
        trmlt.run_multithreaded()

    elif args.action is None:
        # No action was provided
        # list the available actions
        logging.error("No action provided.")
        logging.error("Available actions:")
        for action in available_actions:
            logging.error(f"  {action}")
        sys.exit(1)
    else:
        # This should not happen with argparse choices, but just in case
        logging.error(f"Unknown action: {args.action}")
        sys.exit(1)


if __name__ == "__main__":
    main()
