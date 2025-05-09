# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.


import argparse
import logging
import multiprocessing  # Add import for multiprocessing.Manager
import os
import shutil
import signal
import subprocess
import sys
import threading  # Added import
import time

# TODO: add a semaphore file that makes that turns on --debug mode
#    - main should check for the file every cycle and set the debug flag
# TODO: longer term, networked locking for control of job starting for a single pool
#  - high availability
#  - for development, take over starting jobs for a particlar project
import sentry_sdk

from mozilla_bitbar_devicepool import configuration_lt, logging_setup
from mozilla_bitbar_devicepool.lambdatest import job_config, status
from mozilla_bitbar_devicepool.lambdatest.job_tracker import JobTracker
from mozilla_bitbar_devicepool.taskcluster import get_taskcluster_pending_tasks
from mozilla_bitbar_devicepool.util import misc


class TestRunManagerLT(object):
    """Test Run Manager for LambdaTest"""

    # Add this attribute to make pytest ignore this class
    __test__ = False  # pytest will not collect classes with __test__ = False

    # Constants at class level
    PROGRAM_LABEL = "tcdp"
    # TODO: increase this to 10, 20, 30 once we're more confident
    MAX_JOBS_TO_START_IN_ONE_CYCLE = 10
    GLOBAL_MAX_INITITATED_JOBS = 40
    # roughly the time it takes for a LT job to start, install deps, start g-w, and pickup a TC job
    JOB_TRACKER_EXPIRY_SECONDS = 210  # seconds

    # Threading constants
    TC_MONITOR_INTERVAL = 30  # seconds
    LT_MONITOR_INTERVAL = 30  # seconds
    JOB_STARTER_INTERVAL = 10  # seconds
    # Debug constants - set higher log levels for specific areas
    DEBUG_JOB_STARTER = True  # Enable detailed debugging for job starter
    DEBUG_DEVICE_SELECTION = True  # Enable detailed debugging for device selection
    DEBUG_JOB_CALCULATION = True  # Enable detailed debugging for job calculation

    # lt api device states
    LT_DEVICE_STATE_ACTIVE = "active"
    LT_DEVICE_STATE_BUSY = "busy"
    LT_DEVICE_STATE_INITIATED = "initiated"
    LT_DEVICE_STATE_CLEANUP = "cleanup"

    # Shared data keys (Constants)
    SHARED_SESSION_STARTED_JOBS = "session_started_jobs"
    SHARED_LT_G_INITIATED_JOBS = "lt_g_initiated_jobs"
    SHARED_LT_G_ACTIVE_DEVICES = "lt_g_active_devices"
    SHARED_LT_G_CLEANUP_DEVICES = "lt_g_cleanup_devices"
    # Shared data keys for project-specific data
    SHARED_PROJECTS = "projects"
    PROJECT_LT_DEVICE_SELECTOR = "lt_device_selector"
    PROJECT_TC_JOB_COUNT = "tc_job_count"
    PROJECT_LT_ACTIVE_DEVICE_COUNT = "lt_active_device_count"
    PROJECT_LT_BUSY_DEVICE_COUNT = "lt_busy_device_count"
    PROJECT_LT_CLEANUP_DEVICE_COUNT = "lt_cleanup_device_count"
    PROJECT_LT_ACTIVE_DEVICES = "lt_active_devices"

    def __init__(
        self,
        max_jobs_to_start=MAX_JOBS_TO_START_IN_ONE_CYCLE,
        exit_wait=5,
        no_job_sleep=60,
        debug_mode=False,
        unit_testing_mode=False,
    ):
        self.interrupt_signal_count = 0
        self.exit_wait = exit_wait
        self.no_job_sleep = no_job_sleep
        self.max_jobs_to_start = max_jobs_to_start
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

        # TODO: this in not thread-safe per-se, but only one thread will be using it (JS per project)
        # Replace single job_tracker with a dictionary of job trackers per project
        self.job_trackers = {}
        # Initialize job trackers for each project in config
        # TODO: configuration lt call to get projects?
        for project_name in self.config_object.config.get("projects", {}):
            self.job_trackers[project_name] = self.get_job_tracker(project_name)

        # Create a multiprocessing Manager for thread-safe shared data
        manager = multiprocessing.Manager()
        self.shared_data = manager.dict()

        # Initialize shared data structure - Moved all initialization here
        self.shared_data[self.SHARED_LT_G_INITIATED_JOBS] = 0
        self.shared_data[self.SHARED_LT_G_ACTIVE_DEVICES] = 0
        self.shared_data[self.SHARED_LT_G_CLEANUP_DEVICES] = 0  # Add tracking for cleanup devices
        self.shared_data[self.SHARED_SESSION_STARTED_JOBS] = 0
        # Initialize projects dictionary as a nested Manager dict
        projects_dict = manager.dict()

        # Initialize project-specific data for all projects defined in config
        for project_name, _project_config in self.config_object.config.get("projects", {}).items():
            project_data = manager.dict()
            project_data[self.PROJECT_TC_JOB_COUNT] = 0
            project_data[self.PROJECT_LT_ACTIVE_DEVICE_COUNT] = 0
            project_data[self.PROJECT_LT_BUSY_DEVICE_COUNT] = 0
            project_data[self.PROJECT_LT_CLEANUP_DEVICE_COUNT] = 0  # Add tracking for cleanup devices per project
            project_data[self.PROJECT_LT_ACTIVE_DEVICES] = manager.list()  # Use managed list
            projects_dict[project_name] = project_data

        self.shared_data[self.SHARED_PROJECTS] = projects_dict

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
            self.job_trackers[project_name] = JobTracker(expiry_seconds=self.JOB_TRACKER_EXPIRY_SECONDS)
        return self.job_trackers[project_name]

    def add_jobs_to_tracker(self, project_name, udids):
        """Add jobs to the specified project tracker."""
        if project_name in self.job_trackers:
            self.job_trackers[project_name].add_job_udids(udids)
        else:
            raise Exception(f"No job tracker found for project '{project_name}' (1).")

    def get_active_job_count(self, project_name):
        """Get active job count from the specified project tracker."""
        if project_name in self.job_trackers:
            return self.job_trackers[project_name].get_active_job_count()
        else:
            raise Exception(f"No job tracker found for project '{project_name}' (2).")

    # Thread functions

    def _taskcluster_monitor_thread(self):
        logging_header = f"[ {'TC Monitor':<{self.logging_padding}} ]"

        while not self.shutdown_event.is_set():
            count_of_fetched_projects = 0
            worker_type_to_count_dict = {}
            # For each project, get taskcluster job count
            for project_name, project_config in self.config_object.config["projects"].items():
                if not self.config_object.is_project_fully_configured(project_name):
                    # logging.warning(f"{logging_header} Project '{project_name}' is not fully configured. Skipping.")
                    continue
                try:
                    tc_worker_type = project_config.get("TC_WORKER_TYPE")
                    tc_job_count = get_taskcluster_pending_tasks("proj-autophone", tc_worker_type, verbose=False)
                    count_of_fetched_projects += 1
                    worker_type_to_count_dict[tc_worker_type] = tc_job_count

                    # Update shared data without lock
                    if project_name in self.shared_data[self.SHARED_PROJECTS]:
                        self.shared_data[self.SHARED_PROJECTS][project_name][self.PROJECT_TC_JOB_COUNT] = tc_job_count
                except Exception as e:
                    logging.error(f"{logging_header} Error fetching TC tasks for {project_name}: {e}", exc_info=True)

            formatted_wttcd = str(worker_type_to_count_dict).strip("{}").replace("'", "")
            logging.info(f"{logging_header} Queue counts: {formatted_wttcd}")

            # Wait for the specified interval or until shutdown is signaled
            self.shutdown_event.wait(self.TC_MONITOR_INTERVAL)

        logging.info(f"{logging_header} Thread stopped.")

    def _lambdatest_monitor_thread(self):
        """Monitors LambdaTest device status for all projects."""
        logging_header = f"[ {'LT Monitor':<{self.logging_padding}} ]"

        # Track global device utilization
        local_device_stats = {
            "total_devices": 0,
            "active_devices": 0,
            "busy_devices": 0,
            "initiated_jobs": 0,
            "cleanup_devices": 0,
        }

        while not self.shutdown_event.is_set():
            active_device_count_by_project_dict = {}
            try:
                device_list = self.status_object.get_device_list()

                # Reset global utilization counts for this cycle
                local_device_stats["total_devices"] = 0
                local_device_stats["active_devices"] = 0
                local_device_stats["busy_devices"] = 0
                local_device_stats["cleanup_devices"] = 0

                try:
                    # Use status_object to get jobs list
                    jobs_summary = self.status_object.get_job_summary()

                    # Count initiated jobs
                    initiated_jobs_count = 0
                    for job_status in jobs_summary:
                        if job_status == self.LT_DEVICE_STATE_INITIATED:
                            initiated_jobs_count += jobs_summary[job_status]

                    # Add more detailed breakdown of job states
                    if self.DEBUG_JOB_CALCULATION:
                        job_states_str = ", ".join([f"{state}: {count}" for state, count in jobs_summary.items()])
                        logging.debug(f"{logging_header} Job state counts: {job_states_str}")

                    local_device_stats["initiated_jobs"] = initiated_jobs_count
                except Exception as e:
                    logging.error(f"{logging_header} Error fetching jobs list: {e}", exc_info=True)
                    # TODO: needed?
                    # Keep previous value if there's an error
                    local_device_stats["initiated_jobs"] = self.shared_data.get(self.SHARED_LT_G_INITIATED_JOBS, 0)

                # Count total devices across all device types
                for device_type in device_list:
                    local_device_stats["total_devices"] += len(device_list[device_type])

                    # Count devices by state
                    for udid, state in device_list[device_type].items():
                        if state == self.LT_DEVICE_STATE_ACTIVE:
                            local_device_stats["active_devices"] += 1
                        elif state == self.LT_DEVICE_STATE_BUSY:
                            local_device_stats["busy_devices"] += 1
                        elif state == self.LT_DEVICE_STATE_CLEANUP:
                            local_device_stats["cleanup_devices"] += 1

            except Exception as e:
                logging.error(f"{logging_header} Error fetching device list: {e}", exc_info=True)
                device_list = {}

            # Update shared data with accurate job count and device stats
            self.shared_data[self.SHARED_LT_G_INITIATED_JOBS] = local_device_stats["initiated_jobs"]
            self.shared_data[self.SHARED_LT_G_ACTIVE_DEVICES] = local_device_stats["active_devices"]
            self.shared_data[self.SHARED_LT_G_CLEANUP_DEVICES] = local_device_stats["cleanup_devices"]

            # For each project, filter the device list based on the project's device_groups
            for project_name, project_config in self.config_object.config["projects"].items():
                try:
                    if not self.config_object.is_project_fully_configured(project_name):
                        # logging.warning(f"{logging_header} Project '{project_name}' is not fully configured. Skipping.")
                        continue

                    project_active_device_count_api = 0
                    project_busy_devices_api = 0
                    project_cleanup_devices_api = 0
                    project_active_devices_api_list = []

                    # Now iterate through all devices
                    for device_type in device_list:
                        for udid, state in device_list[device_type].items():
                            if udid is None:
                                # empty device list
                                continue
                            # Only count the device if it's in this project's device group
                            device_project = self.config_object.get_project_for_udid(udid)
                            if device_project == project_name:
                                if state == self.LT_DEVICE_STATE_ACTIVE:
                                    project_active_device_count_api += 1
                                    project_active_devices_api_list.append(udid)
                                elif state == self.LT_DEVICE_STATE_BUSY:
                                    project_busy_devices_api += 1
                                elif state == self.LT_DEVICE_STATE_CLEANUP:
                                    project_cleanup_devices_api += 1

                    active_device_count_by_project_dict[project_name] = project_active_device_count_api

                    # Update shared data for the project
                    project_data = self.shared_data[self.SHARED_PROJECTS][project_name]
                    project_data[self.PROJECT_LT_ACTIVE_DEVICE_COUNT] = project_active_device_count_api
                    project_data[self.PROJECT_LT_BUSY_DEVICE_COUNT] = project_busy_devices_api
                    project_data[self.PROJECT_LT_CLEANUP_DEVICE_COUNT] = project_cleanup_devices_api

                    # Clear and update the PROJECT_LT_ACTIVE_DEVICES list with API reported active devices
                    shared_active_devices_list = project_data[self.PROJECT_LT_ACTIVE_DEVICES]
                    shared_active_devices_list[:] = []  # Clear the managed list
                    shared_active_devices_list.extend(project_active_devices_api_list)  # Update with new data from API

                    # Log the available device list after updating for debugging
                    logging.debug(
                        f"{logging_header} Updated API active devices for {project_name}: {list(shared_active_devices_list)}"
                    )

                except Exception as e:
                    logging.error(f"{logging_header} Error processing devices for {project_name}: {e}", exc_info=True)

            # Log global device utilization statistics
            global_total_device_count = self.config_object.get_total_device_count()
            util_percent = 0
            if global_total_device_count > 0:
                util_percent = (local_device_stats["busy_devices"] / global_total_device_count) * 100

            formatted_active_device_count = str(active_device_count_by_project_dict).strip("{}").replace("'", "")
            per_queue_string = f"Active device counts: {formatted_active_device_count}"
            logging.info(
                f"{logging_header} "
                f"Session started jobs: {self.shared_data[self.SHARED_SESSION_STARTED_JOBS]}, "
                "Global device utilization: Total/Active/Busy/Cleanup/BusyPercentage: "
                f"{global_total_device_count}/{self.shared_data[self.SHARED_LT_G_ACTIVE_DEVICES]}/"
                f"{local_device_stats['busy_devices']}/{self.shared_data[self.SHARED_LT_G_CLEANUP_DEVICES]}/"
                f"{util_percent:.1f}%"
            )
            logging.info(f"{logging_header} {per_queue_string}")

            self.shutdown_event.wait(self.LT_MONITOR_INTERVAL)

        logging.info(f"{logging_header} Thread stopped.")

    def _job_starter_thread(self, project_name):
        """Starts jobs based on monitored data for a specific project."""

        logging_header = f"[ {'JS ' + project_name:<{self.logging_padding}} ]"

        project_source_dir = os.path.dirname(os.path.realpath(__file__))
        project_root_dir = os.path.abspath(os.path.join(project_source_dir, ".."))
        user_script_golden_dir = os.path.join(project_source_dir, "lambdatest", "user_script")

        current_project = self.config_object.config["projects"][project_name]
        tc_worker_type = current_project["TC_WORKER_TYPE"]
        tc_client_id = current_project["TASKCLUSTER_CLIENT_ID"]
        tc_client_key = current_project["TASKCLUSTER_ACCESS_TOKEN"]
        lt_device_selector = current_project["lt_device_selector"]

        while not self.shutdown_event.is_set():
            tc_job_count = 0
            project_active_device_count_api = 0
            project_active_devices_api_list = []
            project_busy_devices_api = 0
            project_cleanup_devices_api = 0

            project_data = self.shared_data[self.SHARED_PROJECTS][project_name]
            tc_job_count = project_data.get(self.PROJECT_TC_JOB_COUNT, 0)
            project_active_device_count_api = project_data.get(self.PROJECT_LT_ACTIVE_DEVICE_COUNT, 0)
            project_busy_devices_api = project_data.get(self.PROJECT_LT_BUSY_DEVICE_COUNT, 0)
            project_cleanup_devices_api = project_data.get(self.PROJECT_LT_CLEANUP_DEVICE_COUNT, 0)
            # Make a copy of the list from shared data
            project_active_devices_api_list = list(project_data.get(self.PROJECT_LT_ACTIVE_DEVICES, []))

            # Get count of recently started jobs (and their UDIDs) from the project-specific job tracker
            job_tracker = self.get_job_tracker(project_name)
            recently_started_jobs_count = job_tracker.get_active_job_count()
            job_tracker_active_udids = job_tracker.get_active_udids()  # UDIDs tracked by job tracker

            # Calculate devices truly available for starting jobs: API Active minus JobTracker Active
            available_devices_for_job_start = [
                udid for udid in project_active_devices_api_list if udid not in job_tracker_active_udids
            ]
            available_devices_for_job_start_count = len(available_devices_for_job_start)

            # Debug logging for job tracker and available devices calculation
            if self.DEBUG_JOB_STARTER or self.DEBUG_DEVICE_SELECTION:
                logging.debug(
                    f"{logging_header} Job tracker has {recently_started_jobs_count} active jobs "
                    f"for devices: {job_tracker_active_udids if job_tracker_active_udids else 'none'}"
                )
                logging.debug(f"{logging_header} API Active Devices: {project_active_devices_api_list}")
                logging.debug(f"{logging_header} Available for Job Start: {available_devices_for_job_start}")

            # Warn if the API count and the list length from shared data don't match (indicates potential sync issue)
            if project_active_device_count_api != len(project_active_devices_api_list):
                logging.warning(
                    f"{logging_header} API active device count ({project_active_device_count_api}) and "
                    f"shared list length ({len(project_active_devices_api_list)}) mismatch!"
                )

            tc_jobs_not_handled = tc_job_count - recently_started_jobs_count

            # Debug log with all key variables for easier debugging
            if self.DEBUG_JOB_STARTER:
                logging.debug(
                    f"{logging_header} Decision variables: TC Jobs:{tc_job_count}, "
                    f"API Active LT Devs:{project_active_device_count_api}, "
                    f"Available for Start:{available_devices_for_job_start_count}, "
                    f"Device UDIDs (Available):{available_devices_for_job_start}"
                )

            jobs_to_start = self.calculate_jobs_to_start(
                tc_jobs_not_handled,
                available_devices_for_job_start_count,
                self.shared_data[self.SHARED_LT_G_INITIATED_JOBS],
            )
            jobs_to_start = max(0, jobs_to_start)

            lt_blob_p1 = f"{len(self.config_object.config['device_groups'][project_name])}/{project_active_device_count_api}/{project_busy_devices_api}/{project_cleanup_devices_api}"
            lt_blob = f"LT Devs Config/Active/Busy/Cleanup: {lt_blob_p1:>11}"

            # Add global initiated jobs count to the log for better visibility
            logging.info(
                f"{logging_header} TC Jobs: {tc_job_count:>4}, {lt_blob:>41}, "
                f"RStarted/NeedH/Avail/ToStart: {recently_started_jobs_count}/{tc_jobs_not_handled}/{available_devices_for_job_start_count}/{jobs_to_start}, "  # Added Avail count
                f"GInit/GInitMax {self.shared_data[self.SHARED_LT_G_INITIATED_JOBS]}/{self.GLOBAL_MAX_INITITATED_JOBS}"
            )

            if jobs_to_start > 0:
                # TODO: not used any longer, remove eventually
                lt_app_url = "lt://proverbial-android"  # Eternal APK

                cmd_env = os.environ.copy()
                cmd_env["LT_USERNAME"] = self.config_object.lt_username
                cmd_env["LT_ACCESS_KEY"] = self.config_object.lt_access_key

                processes_started = 0
                assigned_device_udids = []

                # Create a mutable copy to iterate and modify for selection
                devices_to_assign_from = list(available_devices_for_job_start)

                for i in range(jobs_to_start):
                    if self.shutdown_event.is_set():
                        logging.info(f"{logging_header} Shutdown signaled during job starting loop.")
                        break

                    # Get next available device that hasn't been assigned yet in this loop
                    device_udid = None
                    if devices_to_assign_from:
                        # Simple selection: take the first one
                        device_udid = devices_to_assign_from.pop(0)

                        # Debug device selection process
                        if self.DEBUG_DEVICE_SELECTION:
                            logging.debug(f"{logging_header} Selecting device {device_udid} for job {i + 1}")

                        # add the udid to labels
                        labels_csv = f"{self.PROGRAM_LABEL},{project_name},{device_udid}"
                        labels_arg = f"--labels '{labels_csv}'"
                        extra_flags = "--exclude-external-binaries"
                        base_command_string = f"{project_root_dir}/hyperexecute --no-track {labels_arg} {extra_flags}"
                        # Keep track of the assigned UDID for this loop
                        assigned_device_udids.append(device_udid)
                    else:
                        # This shouldn't happen if jobs_to_start was calculated correctly based on available_devices_for_job_start_count
                        logging.warning(
                            f"{logging_header} Ran out of devices to assign mid-loop! Should have started {jobs_to_start}, assigned {len(assigned_device_udids)}."
                        )
                        break  # Exit the loop if no more devices are available

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

                        # Write config with specific device UDID
                        job_config.write_config(
                            tc_client_id,
                            tc_client_key,
                            tc_worker_type,
                            lt_app_url,
                            lt_device_selector,
                            udid=device_udid,
                            concurrency=1,
                            path=test_run_file,
                        )

                        if self.debug_mode:
                            # Simulate tiny delay if in debug mode
                            time.sleep(0.1)
                        else:
                            # Check if hyperexecute exists before executing
                            hyperexecute_path = os.path.join(project_root_dir, "hyperexecute")
                            max_retry = 5
                            retry_count = 0

                            while retry_count < max_retry:
                                if os.path.exists(hyperexecute_path) and os.access(hyperexecute_path, os.X_OK):
                                    # Start process in background
                                    _process = subprocess.Popen(
                                        base_command_string,
                                        shell=True,
                                        env=cmd_env,
                                        cwd=test_run_dir,
                                        start_new_session=True,
                                        stdout=subprocess.DEVNULL,  # Discard output for background tasks
                                        stderr=subprocess.DEVNULL,
                                    )
                                    # Add a small delay between job launches to avoid race conditions
                                    #   - when multiple jobs run at once and decide to update.
                                    #   - lots of jobs being started at once can swamp USB.
                                    # TODO: if USB issues are resolved, remove this sleep and potentially run with
                                    #     `--disable-updates` option, and then have main thread run without the option occasionally
                                    #     to update (with locking)
                                    time.sleep(2)
                                    break
                                else:
                                    logging.warning(
                                        f"{logging_header} hyperexecute binary not found or not executable, retry {retry_count + 1}/{max_retry}"
                                    )
                                    time.sleep(2)  # Wait for 2 seconds before retrying
                                    retry_count += 1

                            if retry_count >= max_retry:
                                raise FileNotFoundError(f"hyperexecute binary not found after {max_retry} retries")

                        processes_started += 1
                        self.shared_data[self.SHARED_SESSION_STARTED_JOBS] += 1

                    except Exception as e:
                        logging.error(f"{logging_header} Error starting job {i + 1}: {e}", exc_info=True)
                        shutil.rmtree(test_run_dir, ignore_errors=True)

                if processes_started > 0 and not self.debug_mode:
                    # Pass the collected UDIDs when adding jobs to the tracker
                    self.add_jobs_to_tracker(project_name, assigned_device_udids)

                # print a summary of number of jobs started and the udids
                if processes_started > 0:
                    if self.debug_mode:
                        logging.info(
                            f"{logging_header} Would have launched {processes_started} jobs targeting devices: {', '.join(assigned_device_udids)}"
                        )
                    else:
                        logging.info(
                            f"{logging_header} Launched {processes_started} jobs targeting devices: {', '.join(assigned_device_udids)}"
                        )

                # TODO: send a signal to the other threads to wake them up and have them gather?
                # TODO: could also track next run for threads, and then sleep just a bit longer also
                #
                # avoid race with tc and lt threads, pause so we have updated data on next loop
                #
                # disabled... i don't think we need this. if there are 30 jobs and max to start per turn is 10,
                #    we can get some more jobs launched before the next LT_UPDATE
                #
                # update: not needed, but we end up launching jobs too quickly without it
                self.shutdown_event.wait(self.LT_MONITOR_INTERVAL)
            else:
                # If no jobs to start but there are TC jobs and available devices, log debug info
                if tc_job_count > 0 and available_devices_for_job_start_count > 0:
                    logging.debug(
                        f"{logging_header} Not starting jobs despite TC jobs ({tc_job_count}) and available devices ({available_devices_for_job_start_count}). "
                        f"Check: Recently Started={recently_started_jobs_count}, Global Initiated={self.shared_data[self.SHARED_LT_G_INITIATED_JOBS]}/{self.GLOBAL_MAX_INITITATED_JOBS}"
                    )

            # Wait before next check or until shutdown
            self.shutdown_event.wait(self.JOB_STARTER_INTERVAL)

        logging.info(f"{logging_header} Thread stopped.")

    # main thread
    def run_multithreaded(self):
        """Runs the manager with separate threads for monitoring and job starting for each project."""
        logging_header = f"[ {'Main':<{self.logging_padding}} ]"
        logging.info(f"{logging_header} Starting Test Run Manager in multithreaded mode...")

        thread_started_count = 0

        # Create monitor threads
        tc_monitor = threading.Thread(target=self._taskcluster_monitor_thread, name="TC Monitor")
        lt_monitor = threading.Thread(target=self._lambdatest_monitor_thread, name="LT Monitor")

        # Start monitor threads
        tc_monitor.start()
        thread_started_count += 1
        logging.info(f"{logging_header} Started TC Monitor thread.")
        lt_monitor.start()
        thread_started_count += 1
        logging.info(f"{logging_header} Started LT Monitor thread.")

        # Give monitors a moment to potentially fetch initial data
        time.sleep(2)

        # Create and start a job starter thread for each project
        job_starters = []
        for project_name in self.config_object.get_fully_configured_projects():
            job_starter = threading.Thread(
                target=self._job_starter_thread, args=(project_name,), name=f"Job Starter - {project_name}"
            )
            job_starters.append(job_starter)
            job_starter.start()
            thread_started_count += 1
            logging.info(f"{logging_header} Started Job Starter thread 'JS {project_name}'.")

        # Keep main thread alive until shutdown is signaled
        logging.info(f"{logging_header} {thread_started_count} threads started. Waiting for shutdown signal...")
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

    # Helper methods

    def calculate_jobs_to_start(self, tc_jobs_not_handled, available_devices_count, global_initiated, max_jobs=None):
        """
        Calculate the number of jobs to start based on pending TC jobs and available devices.

        Args:
            tc_jobs_not_handled (int): Number of Taskcluster jobs that are not yet handled
            available_devices_count (int): Number of available devices
            global_initiated (int): Current count of globally initiated jobs
            max_jobs (int, optional): Maximum jobs to start, defaults to self.max_jobs_to_start

        Returns:
            int: Number of jobs that should be started
        """
        if max_jobs is None:
            max_jobs = self.max_jobs_to_start

        # Debug output for job calculation
        if self.DEBUG_JOB_CALCULATION:
            logging.debug(
                f"Job calculation - TCJobsNotHandled: {tc_jobs_not_handled}, "
                f"AvailableDevices: {available_devices_count}, "
                f"GlobalInitiated: {global_initiated}, "
                f"MaxJobsToStartAtOnce: {max_jobs}"
            )

        # TODO: move global_initiated out of this function and consider it in 'job start' threads separately
        # Inspect global initiated jobs threshold
        if global_initiated > self.GLOBAL_MAX_INITITATED_JOBS:
            if self.DEBUG_JOB_CALCULATION:
                logging.debug(
                    f"Not starting new jobs: Global initiated jobs ({global_initiated}) > "
                    f"GLOBAL_MAX_INITITATED_JOBS ({self.GLOBAL_MAX_INITITATED_JOBS})"
                )
            jobs_to_start = 0
            return jobs_to_start

        # Calculate the minimum of pending jobs, max jobs limit, and available devices
        jobs_to_start = min(tc_jobs_not_handled, max_jobs, available_devices_count)

        # Debug output for the actual calculation
        if self.DEBUG_JOB_CALCULATION:
            logging.debug(
                f"Job start calculation (min(tc_jobs_not_handled, max_jobs, available_devices_count)): min({tc_jobs_not_handled}, {max_jobs}, {available_devices_count}) = {jobs_to_start}"
            )

        # Ensure the result is not negative
        jobs_to_start = max(0, jobs_to_start)

        return jobs_to_start


# Main and main helpers


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


def main():
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        # Sentry DSN is set, initialize Sentry SDK
        sentry_sdk.init(
            dsn=sentry_dsn,
            # Add data like request headers and IP for users,
            # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
            send_default_pii=True,
        )
    else:
        # Sentry DSN is not set, disable Sentry
        logging.warning("SENTRY_DSN is not set. Sentry SDK will not be initialized.")

    # TODO: log in sentry when a particular git sha (version?) has run X jobs.

    # Parse command line arguments
    available_actions = ["start-test-run-manager"]
    args = parse_args(available_actions)

    # if args.debug:
    #     logging.warning("Running in debug mode. JFake values are used in many places!")

    # Configure logging explicitly
    logging_setup.setup_logging(args.log_level, args.disable_logging_timestamps)

    if args.action == "start-test-run-manager":
        git_version_info = misc.get_git_info()
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
