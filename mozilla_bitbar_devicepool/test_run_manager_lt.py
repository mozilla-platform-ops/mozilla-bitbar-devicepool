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
    MAX_JOBS_TO_START_AT_ONCE = 5
    # lt api device states
    LT_DEVICE_STATE_ACTIVE = "active"
    LT_DEVICE_STATE_BUSY = "busy"
    # background task control
    # TODO: making this work when False is going to require more work...
    #     - our loop is too fast and we end up
    #       - overwriting dirs (handled within loop with path per job)
    #       - starting too many jobs... we don't detect that they've started yet (TODO: check state name they are in)
    WAIT_FOR_BACKGROUND_TASKS = True

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

        # ISSUE: lt jobs (even more so concurrent jobs) take 1-3 minutes to start and grab a tc task, in that time
        #        we can start more jobs and end up with too many jobs running.
        # SOLUTION: maintain a list of started jobs, when they were started, and how many tasks (if concurrency)
        # .       we will remove any entries older than our estimated time to start a job (3.5 minutes)
        # TODO: maintain a jobs started log with datetimes
        #
        # Initialize job tracker with 3.5 minute expiry
        self.job_tracker = JobTracker(expiry_seconds=210)

        signal.signal(signal.SIGUSR2, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)

    def handle_signal(self, signalnum, frame):
        MAX_SIGNAL_COUNT = 3

        if signalnum == signal.SIGINT or signalnum == signal.SIGUSR2:
            # track how many times we've received the signal. at 3, exit immediately.
            self.interrupt_signal_count += 1
            if self.interrupt_signal_count < MAX_SIGNAL_COUNT:
                self.state = self.STATE_STOP
                logging.info(
                    # f" handle_signal: set state to stop, exiting in {self.exit_wait} seconds or less"
                    " handle_signal: set state to stop, will exit when safe."
                )
                logging.info(
                    f"will exit immediately if signal received {MAX_SIGNAL_COUNT - self.interrupt_signal_count} more times."
                )
                # for testing, exit immediately (no wait)
                # sys.exit(0)
            else:
                logging.info(f" handle_signal: received signal {MAX_SIGNAL_COUNT} times, exiting immediately")
                sys.exit(0)

    def handle_signal_old(self, signalnum, frame):
        if self.state == self.STATE_STOP:
            return

        self.state = self.STATE_STOP
        logging.info(
            # f" handle_signal: set state to stop, exiting in {self.exit_wait} seconds or less"
            " handle_signal: set state to stop, will exit after current job completes"
        )
        # for testing, exit immediately
        # sys.exit(0)

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
            recently_started_jobs = self.job_tracker.get_active_job_count()

            # New calculation that includes recently started jobs
            tc_jobs_not_handled = tc_job_count - initiated_job_count - recently_started_jobs

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
                if foreground:
                    command_string = f"{project_root_dir}/hyperexecute {labels_arg}"
                else:
                    command_string = f"{project_root_dir}/hyperexecute --no-track {labels_arg}"

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
                    self.job_tracker.add_jobs(jobs_to_start)
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
                    self.job_tracker.add_jobs(jobs_to_start)
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
                    self.job_tracker.add_jobs(jobs_to_start)
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
        trmlt.run_single_project_single_thread_multi_job(
            # mode=trmlt.MODE_RUN_NOTRACK_BACKGROUND_TASKS
            mode=trmlt.MODE_RUN_NOTRACK_WITH_CONCURRENCY,
        )
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
