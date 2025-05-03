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
import multiprocessing  # Add import for multiprocessing.Manager

import pprint

from mozilla_bitbar_devicepool import configuration_lt, logging_setup
from mozilla_bitbar_devicepool.lambdatest import job_config, status
from mozilla_bitbar_devicepool.lambdatest.job_tracker import JobTracker
from mozilla_bitbar_devicepool.taskcluster import get_taskcluster_pending_tasks

# TODO: add a semaphore file that makes that turns on --debug mode
#    - main should check for the file every cycle and set the debug flag

# TODO: longer term, networked locking for control of job starting for a single pool
#  - high availability
#  - for development, take over starting jobs for a particlar project


class TestRunManagerLT(object):
    """Test Run Manager for LambdaTest"""

    # Add this attribute to make pytest ignore this class
    __test__ = False  # pytest will not collect classes with __test__ = False

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
    # keep around the total number of devices online?
    MAX_INITITATED_JOBS = 40
    # lt api device states
    LT_DEVICE_STATE_ACTIVE = "active"
    LT_DEVICE_STATE_BUSY = "busy"
    LT_DEVICE_STATE_INITIATED = "initiated"
    LT_DEVICE_STATE_CLEANUP = "cleanup"
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
        unit_testing_mode=False,
    ):
        self.interrupt_signal_count = 0
        self.exit_wait = exit_wait
        self.no_job_sleep = no_job_sleep
        self.max_jobs_to_start = max_jobs_to_start
        self.state = self.STATE_RUNNING
        self.debug_mode = debug_mode
        self.unit_testing_mode = unit_testing_mode
        self.logging_padding = 12  # Store the padding value as instance variable
        # Skip hyperexecute binary check in unit testing mode or when running tests
        self.config_object = configuration_lt.ConfigurationLt(ci_mode=self.unit_testing_mode)
        self.config_object.configure()
        self.status_object = status.Status(self.config_object.lt_username, self.config_object.lt_access_key)

        if self.unit_testing_mode:
            # Skip hyperexecute binary check in unit testing mode
            logging.info("TestRunManagerLT: Unit testing mode enabled.")

        # Replace single job_tracker with a dictionary of job trackers per project
        self.job_trackers = {}
        # Initialize job trackers for each project in config
        for project_name in self.config_object.config.get("projects", {}):
            self.job_trackers[project_name] = JobTracker(expiry_seconds=210)
        # Keep a default tracker for backward compatibility
        self.job_tracker = JobTracker(expiry_seconds=210)

        # Create a multiprocessing Manager for thread-safe shared data
        manager = multiprocessing.Manager()
        self.shared_data = manager.dict()

        # Initialize shared data structure
        self.shared_data["lt_g_initiated_jobs"] = 0
        self.shared_data["lt_g_active_devices"] = 0
        self.shared_data["lt_g_cleanup_devices"] = 0  # Add tracking for cleanup devices
        # Initialize projects dictionary as a nested Manager dict
        projects_dict = manager.dict()

        # Initialize project-specific data
        for project_name, project_config in self.config_object.config.get("projects", {}).items():
            project_data = manager.dict()
            project_data["lt_device_selector"] = project_config.get("lt_device_selector", None)
            project_data["tc_job_count"] = 0
            project_data["lt_active_devices"] = 0
            project_data["lt_busy_devices"] = 0
            project_data["lt_cleanup_devices"] = 0  # Add tracking for cleanup devices per project
            project_data["available_devices"] = manager.list()  # Use managed list
            projects_dict[project_name] = project_data

        self.shared_data["projects"] = projects_dict

        # No need for a lock with Manager objects
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

    def add_jobs(self, count, project_name=None, udids=None):
        """Add jobs to the specified project tracker or default tracker if no project specified."""
        if project_name and project_name in self.job_trackers:
            self.job_trackers[project_name].add_job_udids(udids)
        else:
            # For backward compatibility
            self.job_tracker.add_job_udids(udids)

    def get_active_job_count(self, project_name=None):
        """Get active job count from the specified project tracker or default tracker."""
        if project_name and project_name in self.job_trackers:
            return self.job_trackers[project_name].get_active_job_count()
        # For backward compatibility
        return self.job_tracker.get_active_job_count()

    # --- Multithreaded Implementation ---

    def _taskcluster_monitor_thread(self):
        """Monitors Taskcluster pending tasks for all projects."""
        logging_header = f"[ {'TC Monitor':<{self.logging_padding}} ]"

        while not self.shutdown_event.is_set():
            count_of_fetched_projects = 0
            worker_type_to_count_dict = {}
            # For each project, get taskcluster job count
            for project_name, project_config in self.config_object.config["projects"].items():
                try:
                    tc_worker_type = project_config.get("TC_WORKER_TYPE")
                    if tc_worker_type:
                        # TODO: Make provisioner name dynamic if needed
                        tc_job_count = get_taskcluster_pending_tasks("proj-autophone", tc_worker_type, verbose=False)
                        count_of_fetched_projects += 1
                        worker_type_to_count_dict[tc_worker_type] = tc_job_count

                        # Update shared data without lock
                        if project_name in self.shared_data["projects"]:
                            self.shared_data["projects"][project_name]["tc_job_count"] = tc_job_count
                except Exception as e:
                    logging.error(f"{logging_header} Error fetching TC tasks for {project_name}: {e}", exc_info=True)

            # logging.info(f"{logging_header} Updated data for {count_of_fetched_projects} queues.")
            logging.info(f"{logging_header} Updated. Queue counts: {pprint.pformat(worker_type_to_count_dict)}")

            # Wait for the specified interval or until shutdown is signaled
            self.shutdown_event.wait(self.TC_MONITOR_INTERVAL)

        logging.info("{logging_header} Thread stopped.")

    def _lambdatest_monitor_thread(self):
        """Monitors LambdaTest device status for all projects."""
        logging_header = f"[ {'LT Monitor':<{self.logging_padding}} ]"

        # Track global device utilization
        global_device_utilization = {
            "total_devices": 0,
            "active_devices": 0,
            "busy_devices": 0,
            "initiated_jobs": 0,
            "cleanup_devices": 0,  # Add cleanup devices to utilization tracking
        }

        # Initialize projects structure in shared data
        # No need to lock since we're using Manager objects
        if "projects" not in self.shared_data:
            manager = multiprocessing.Manager()
            self.shared_data["projects"] = manager.dict()

            # Initialize all projects
            for project_name, project_config in self.config_object.config["projects"].items():
                if project_name not in self.shared_data["projects"]:
                    project_data = manager.dict()
                    project_data["lt_device_selector"] = project_config.get("lt_device_selector", None)
                    project_data["tc_job_count"] = 0
                    project_data["lt_active_devices"] = 0
                    project_data["lt_busy_devices"] = 0
                    project_data["lt_cleanup_devices"] = 0  # Add cleanup devices per project
                    project_data["available_devices"] = manager.list()  # Use managed list for device info
                    self.shared_data["projects"][project_name] = project_data

        while not self.shutdown_event.is_set():
            active_device_count_by_project_dict = {}
            # Get entire device list once - we'll filter it for each project
            try:
                device_list = self.status_object.get_device_list()

                # Reset global utilization counts for this cycle
                global_device_utilization["total_devices"] = 0
                global_device_utilization["active_devices"] = 0
                global_device_utilization["busy_devices"] = 0
                global_device_utilization["initiated_jobs"] = 0
                global_device_utilization["cleanup_devices"] = 0  # Reset cleanup count

                # Count total devices across all device types
                for device_type in device_list:
                    global_device_utilization["total_devices"] += len(device_list[device_type])

                    # Count devices by state
                    for udid, state in device_list[device_type].items():
                        if state == self.LT_DEVICE_STATE_ACTIVE:
                            global_device_utilization["active_devices"] += 1
                        elif state == self.LT_DEVICE_STATE_BUSY:
                            global_device_utilization["busy_devices"] += 1
                        elif state == self.LT_DEVICE_STATE_INITIATED:
                            global_device_utilization["initiated_jobs"] += 1
                        elif state == self.LT_DEVICE_STATE_CLEANUP:
                            global_device_utilization["cleanup_devices"] += 1  # Count cleanup devices

            except Exception as e:
                logging.error(f"{logging_header} Error fetching device list: {e}", exc_info=True)
                device_list = {}

            g_initiated_jobs = global_device_utilization["initiated_jobs"]
            g_active_devices = global_device_utilization["active_devices"]
            g_cleanup_devices = global_device_utilization["cleanup_devices"]  # Get global cleanup count

            # For each project, filter the device list based on the project's device_groups
            for project_name, project_config in self.config_object.config["projects"].items():
                try:
                    # TODO: should we gate on this any longer? i think no
                    lt_device_selector = project_config.get("lt_device_selector")
                    if lt_device_selector:
                        active_device_count = 0  # Rename to active_device_count for clarity
                        busy_devices = 0
                        cleanup_devices = 0  # Track cleanup devices per project
                        active_device_list = []  # Rename to active_device_list for clarity

                        # Only continue if there's a device_groups config for this project
                        if project_name in self.config_object.config.get("device_groups", {}):
                            project_device_group = self.config_object.config["device_groups"][project_name]

                            # Now iterate through all devices
                            for device_type in device_list:
                                for udid, state in device_list[device_type].items():
                                    # Only count the device if it's in this project's device group
                                    if udid in project_device_group:
                                        if state == self.LT_DEVICE_STATE_ACTIVE:
                                            active_device_count += 1
                                            active_device_list.append(udid)
                                        elif state == self.LT_DEVICE_STATE_BUSY:
                                            busy_devices += 1
                                        elif state == self.LT_DEVICE_STATE_CLEANUP:
                                            cleanup_devices += 1  # Count cleanup devices for this project

                        active_device_count_by_project_dict[project_name] = active_device_count

                        # Update shared data
                        self.shared_data["lt_g_initiated_jobs"] = g_initiated_jobs
                        self.shared_data["lt_g_active_devices"] = g_active_devices
                        self.shared_data["lt_g_cleanup_devices"] = g_cleanup_devices

                        if "projects" in self.shared_data and project_name in self.shared_data["projects"]:
                            self.shared_data["projects"][project_name]["lt_active_devices"] = active_device_count
                            self.shared_data["projects"][project_name]["lt_busy_devices"] = busy_devices
                            self.shared_data["projects"][project_name]["lt_cleanup_devices"] = cleanup_devices

                            # Clear and update the available_devices list
                            available_devices = self.shared_data["projects"][project_name]["available_devices"]
                            available_devices[:] = []
                            available_devices.extend(active_device_list)  # Update with new data

                except Exception as e:
                    logging.error(f"{logging_header} Error processing devices for {project_name}: {e}", exc_info=True)

            # Log global device utilization statistics
            util_percent = 0
            if global_device_utilization["total_devices"] > 0:
                util_percent = (
                    global_device_utilization["busy_devices"] / global_device_utilization["total_devices"]
                ) * 100

            per_queue_string = f"Active device counts: {pprint.pformat(active_device_count_by_project_dict)}"
            logging.info(
                f"{logging_header} "
                "Global device utilization: Total/Active/Busy/Cleanup/BusyPercentage: "  # Added Cleanup to log
                f"{global_device_utilization['total_devices']}/{global_device_utilization['active_devices']}/"
                f"{global_device_utilization['busy_devices']}/{global_device_utilization['cleanup_devices']}/"  # Added cleanup count
                f"{util_percent:.1f}%"
            )
            logging.info(f"{logging_header} {per_queue_string}")

            self.shutdown_event.wait(self.LT_MONITOR_INTERVAL)

        logging.info("LambdaTest monitor thread stopped.")

    def _job_starter_thread(self, project_name):
        """Starts jobs based on monitored data for a specific project."""

        logging_header = f"[ {'JS ' + project_name:<{self.logging_padding}} ]"

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

            # Store selector for this project - no lock needed with Manager
            if "projects" not in self.shared_data:
                manager = multiprocessing.Manager()
                self.shared_data["projects"] = manager.dict()

            if project_name not in self.shared_data["projects"]:
                project_data = multiprocessing.Manager().dict()
                project_data["lt_device_selector"] = lt_device_selector
                project_data["tc_job_count"] = 0
                project_data["lt_active_devices"] = 0
                project_data["lt_busy_devices"] = 0
                project_data["lt_cleanup_devices"] = 0  # Add cleanup devices for new projects
                project_data["available_devices"] = multiprocessing.Manager().list()
                self.shared_data["projects"][project_name] = project_data
        except KeyError as e:
            logging.error(f"{logging_header} Missing config: {e}. Thread exiting.")
            return

        while not self.shutdown_event.is_set():
            tc_job_count = 0
            active_devices = 0
            available_devices = []

            # Try to get device data for this project - no lock needed
            if "projects" in self.shared_data and project_name in self.shared_data["projects"]:
                project_data = self.shared_data["projects"][project_name]
                tc_job_count = project_data.get("tc_job_count", 0)
                active_devices = project_data.get("lt_active_devices", 0)
                busy_devices = project_data.get("lt_busy_devices", 0)
                cleanup_devices = project_data.get("lt_cleanup_devices", 0)  # Get cleanup devices count
                # Make a copy of the list to avoid modification issues
                available_devices = list(project_data.get("available_devices", []))

            # If we don't have data yet, try to fetch it directly
            if tc_job_count == 0:
                try:
                    tc_job_count = get_taskcluster_pending_tasks("proj-autophone", tc_worker_type, verbose=False)
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

            # TODO: make jobs_to_start consider JobTracker or figure out how to short circuit sooner if no free devices

            jobs_to_start = self.calculate_jobs_to_start(
                tc_jobs_not_handled, len(available_devices), self.shared_data["lt_g_initiated_jobs"]
            )
            jobs_to_start = max(0, jobs_to_start)  # Ensure non-negative

            # logging.info(f"{logging_header} Calculated jobs_to_start: {jobs_to_start}")

            lt_blob_p1 = f"{len(self.config_object.config['device_groups'][project_name])}/{active_devices}/{busy_devices}/{cleanup_devices}"
            lt_blob = f"LT Devs Config/Active/Busy/Cleanup: {lt_blob_p1:>9}"  # Updated label to include cleanup

            logging.info(
                f"{logging_header} TC Jobs: {tc_job_count:>4}, {lt_blob:>41}, "
                f"Recently Started: {recently_started_jobs:>3}, Need Handling: {tc_jobs_not_handled:>3}, Jobs To Start: {jobs_to_start:>3}"
            )
            if jobs_to_start > 0:
                # --- Start Jobs (using background task logic) ---
                # logging.info(f"{logging_header} Starting {jobs_to_start} jobs in background...")
                lt_app_url = "lt://proverbial-android"  # Eternal APK

                cmd_env = os.environ.copy()
                cmd_env["LT_USERNAME"] = self.config_object.lt_username
                cmd_env["LT_ACCESS_KEY"] = self.config_object.lt_access_key

                labels_csv = f"{self.PROGRAM_LABEL},{project_name}"
                # TODO: add the udid to labels
                labels_arg = f"--labels '{labels_csv}'"
                extra_flags = "--exclude-external-binaries"
                base_command_string = f"{project_root_dir}/hyperexecute --no-track {labels_arg} {extra_flags}"

                # outer_start_time = time.time()
                processes_started = 0
                assigned_device_udids = []  # Track UDIDs of assigned devices

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
                            # device in job tracker means it's already in use
                            if d in self.get_job_tracker(project_name).get_active_udids():
                                logging.info(f"{logging_header} Device {d} is already in use, skipping.")
                                # skip to the next device
                                continue

                            device_udid = d

                            # add the udid to labels
                            labels_csv = f"{self.PROGRAM_LABEL},{project_name},{device_udid}"
                            labels_arg = f"--labels '{labels_csv}'"
                            base_command_string = (
                                f"{project_root_dir}/hyperexecute --no-track {labels_arg} {extra_flags}"
                            )

                            # remove the device from available devices to avoid reusing it
                            available_devices.remove(d)
                            # Keep track of the assigned UDID
                            assigned_device_udids.append(device_udid)
                            # update the shared data
                            self.shared_data["projects"][project_name]["available_devices"] = available_devices
                            break

                    if not device_udid:
                        # TODO: mention this? or basically expected.
                        # logging.warning(f"{logging_header} No more available devices to assign!")
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
                            # logging.info(
                            #     f"{logging_header} Would run command: '{base_command_string}' in path '{test_run_dir}'..."
                            # )
                            # logging.info(f"{logging_header} Would target device: {device_info}")
                            logging.info(
                                f"{logging_header} WOULD BE launching job {i + 1}/{jobs_to_start} targeting device '{device_info}'"
                            )
                            time.sleep(0.1)  # Simulate tiny delay
                        else:
                            # Start process in background
                            # TODO: only print one line with number of jobs and all udid we'll be using?
                            logging.info(
                                f"{logging_header} Launching job {i + 1}/{jobs_to_start} targeting device '{device_info}'"
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
                    # Pass the collected UDIDs when adding jobs to the tracker
                    self.add_jobs(processes_started, project_name, udids=assigned_device_udids)
                    # logging.info(
                    #     f"{logging_header} Launched {processes_started} background jobs in {round(outer_end_time - outer_start_time, 2)} seconds"
                    # )

                # TODO: send a signal to the other threads to wake them up and have them gather?
                # TODO: could also track next run for threads, and then sleep just a bit longer also
                # avoid race with tc and lt threads, pause so we have updated data on next loop
                # time.sleep(self.LT_MONITOR_INTERVAL)
                # sleep doesn't work?
                self.shutdown_event.wait(self.LT_MONITOR_INTERVAL)
                # --- End Start Jobs ---
            else:
                # logging.info(f"{logging_header} No jobs to start. Sleeping.")
                pass

            # Wait before next check or until shutdown
            self.shutdown_event.wait(self.JOB_STARTER_INTERVAL)

        logging.info(f"{logging_header} stopped.")

    def run_multithreaded(self):
        logging_header = f"[ {'Main':<{self.logging_padding}} ]"
        """Runs the manager with separate threads for monitoring and job starting for each project."""
        logging.info(f"{logging_header} Starting Test Run Manager in multithreaded mode...")

        # Create monitor threads
        tc_monitor = threading.Thread(target=self._taskcluster_monitor_thread, name="TC Monitor")
        lt_monitor = threading.Thread(target=self._lambdatest_monitor_thread, name="LT Monitor")

        # Start monitor threads
        tc_monitor.start()
        logging.info(f"{logging_header} Started TC Monitor thread.")
        lt_monitor.start()
        logging.info(f"{logging_header} Started LT Monitor thread.")

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
            logging.info(f"{logging_header} Started job starter thread for project: {project_name}")

        # Keep main thread alive until shutdown is signaled
        logging.info(f"{logging_header} Waiting for shutdown signal...")
        self.shutdown_event.wait()
        logging.info(f"{logging_header} Shutdown signal received. Waiting for threads to join...")

        # Wait for threads to finish
        tc_monitor.join(timeout=self.TC_MONITOR_INTERVAL + 5)
        lt_monitor.join(timeout=self.LT_MONITOR_INTERVAL + 5)

        for i, job_starter in enumerate(job_starters):
            job_starter.join(timeout=self.JOB_STARTER_INTERVAL + 10)  # Give starter a bit more time
            if job_starter.is_alive():
                logging.warning(f"{logging_header} Job starter thread {i} did not exit cleanly.")

        logging.info(f"{logging_header} All threads joined. Exiting.")
        if tc_monitor.is_alive():
            logging.warning(f"{logging_header} TC monitor thread did not exit cleanly.")
        if lt_monitor.is_alive():
            logging.warning(f"{logging_header} LT monitor thread did not exit cleanly.")

    def calculate_jobs_to_start(self, tc_jobs_not_handled, available_devices_count, global_initiated, max_jobs=None):
        """
        Calculate the number of jobs to start based on pending TC jobs and available devices.

        Args:
            tc_jobs_not_handled (int): Number of Taskcluster jobs that are not yet handled
            available_devices_count (int): Number of available devices
            max_jobs (int, optional): Maximum jobs to start, defaults to self.max_jobs_to_start

        Returns:
            int: Number of jobs that should be started
        """
        if max_jobs is None:
            max_jobs = self.max_jobs_to_start

        # short circuit if we have too many initiated jobs
        if global_initiated > self.MAX_INITITATED_JOBS:
            # logging.info(f"{logging_header} Too many initiated jobs, not starting any new jobs.")
            jobs_to_start = 0
            return jobs_to_start

        # Calculate the minimum of pending jobs, max jobs limit, and available devices
        jobs_to_start = min(tc_jobs_not_handled, max_jobs, available_devices_count)
        # Ensure the result is not negative
        jobs_to_start = max(0, jobs_to_start)

        return jobs_to_start


def get_git_version_info():
    """
    Returns a string with short git sha (if in a git client) and `-dirty` if there are uncommitted changes.
    Returns empty string if not in a git repository or if git commands fail.
    """
    try:
        # Check if we're in a git repository
        subprocess.check_output(["git", "rev-parse", "--is-inside-work-tree"], stderr=subprocess.DEVNULL)

        # Get the short SHA of the current commit
        git_sha = (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
        )

        # Check for uncommitted changes
        status_output = (
            subprocess.check_output(["git", "status", "--porcelain"], stderr=subprocess.DEVNULL).decode().strip()
        )
        is_dirty = len(status_output) > 0

        # Format the output
        result = git_sha
        if is_dirty:
            result += "-dirty"

        return result
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""  # Return empty string if not in a git repo or git is not available


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
        "--ci-mode",
        action="store_true",
        help="Run in CI testing mode without fake values and disabled bin checks.",
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging level. Defaults to INFO.",
    )
    parser.add_argument(
        "--disable-logging-timestamps",
        "-dlt",
        action="store_true",
        help="Disable logging timestamps.",
    )
    return parser.parse_args()


# TODO: add a function returns a string with short git sha (if in a git client) and `-dirty` if there are uncommitted changes


def main():
    # Parse command line arguments
    available_actions = ["start-test-run-manager"]
    args = parse_args(available_actions)

    # if args.debug:
    #     logging.warning("Running in debug mode. JFake values are used in many places!")

    # Configure logging explicitly
    logging_setup.setup_logging(args.log_level, args.disable_logging_timestamps)

    if args.action == "start-test-run-manager":
        git_version_info = get_git_version_info()
        banner = r"""
      ___                        _____
     /__/\                      /  /::\
    |  |::\                    /  /:/\:\
    |  |:|:\    ___     ___   /  /:/  \:\
  __|__|:|\:\  /__/\   /  /\ /__/:/ \__\:|
 /__/::::| \:\ \  \:\ /  /:/ \  \:\ /  /:/
 \  \:\~~\__\/  \  \:\  /:/   \  \:\  /:/
  \  \:\         \  \:\/:/     \  \:\/:/
   \  \:\         \  \::/       \  \::/
    \  \:\         \__\/         \__\/
     \__\/
        """  # noqa: W605
        name_line = f"  mozilla lambdatest devicepool ({git_version_info})"
        print(banner.lstrip("\n"))
        print(name_line)
        print()

        # logging is now properly configured
        trmlt = TestRunManagerLT(unit_testing_mode=args.ci_mode, debug_mode=args.debug)

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
