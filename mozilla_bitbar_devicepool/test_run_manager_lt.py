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
from mozilla_bitbar_devicepool.taskcluster import get_taskcluster_pending_tasks
from mozilla_bitbar_devicepool.lambdatest.util import shorten_worker_type


class TestRunManagerLT(object):
    # Constants at class level
    PROGRAM_LABEL = "tcdp"
    STATE_STOP = 0x10
    STATE_RUNNING = 0x15
    MODE_NO_OP = 0x50
    MODE_SINGLE_JOB = 0x55
    MODE_SINGLE_JOB_WITH_CONCURRENCY = 0x60
    # TODO: rename this to something more descriptive
    MAX_JOBS_TO_START_AT_ONCE = 2000

    def __init__(
        self, max_jobs_to_start=5, exit_wait=5, no_job_sleep=60, debug_mode=False
    ):
        self.interrupt_signal_count = 0
        self.exit_wait = exit_wait
        self.no_job_sleep = no_job_sleep
        self.max_jobs_to_start = max_jobs_to_start
        self.state = self.STATE_RUNNING
        self.test_mode = debug_mode
        self.config_object = configuration_lt.ConfigurationLt()
        self.config_object.configure()
        self.status_object = status.Status(
            self.config_object.lt_username, self.config_object.lt_access_key
        )

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
                    " handle_signal: set state to stop, will exit after current job completes."
                )
                logging.info(
                    f"will exit immediately if signal received {MAX_SIGNAL_COUNT - self.interrupt_signal_count} more times."
                )
                # for testing, exit immediately (no wait)
                # sys.exit(0)
            else:
                logging.info(
                    f" handle_signal: received signal {MAX_SIGNAL_COUNT} times, exiting immediately"
                )
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
        user_script_golden_dir = os.path.join(
            project_source_dir, "lambdatest", "user_script"
        )
        test_run_dir = "/tmp/mozilla-lt-devicepool-job-dir"
        test_run_file = os.path.join(test_run_dir, "hyperexecute.yaml")

        test_run_dir = "/tmp/mozilla-lt-devicepool-job-dir"
        test_run_file = os.path.join(test_run_dir, "hyperexecute.yaml")
        while True:
            # only a single project for now, so load that up
            current_project = self.config_object.config["projects"]["a55-alpha"]

            tc_worker_type = current_project["TC_WORKER_TYPE"]
            tc_client_id = current_project["TASKCLUSTER_CLIENT_ID"]
            tc_client_key = current_project["TASKCLUSTER_ACCESS_TOKEN"]

            # TODO: verify this apk is ok, update the apk if needed, and store/use it's app_id
            lt_app_url = "lt://APP1016023521741987818221818"

            # remove /tmp/user_script dir
            shutil.rmtree(test_run_dir, ignore_errors=True)
            # create /tmp/mozilla-lt-devicepool-job-dir dir
            os.makedirs(test_run_dir, exist_ok=True)

            # TODO: copy user-script dir to correct dir (use basename on config_file_path?)
            # copy user_script_golden_dir to correct path using python shutil
            shutil.copytree(
                user_script_golden_dir, os.path.join(test_run_dir, "user_script")
            )

            cmd_env = os.environ.copy()
            cmd_env["LT_USERNAME"] = self.config_object.lt_username
            cmd_env["LT_ACCESS_KEY"] = self.config_object.lt_access_key

            # set the device type, OS, and optionally UDID for this job
            #
            # for now we have a single pool of devices
            device_type_and_os = "Galaxy A55 5G-14"

            command_string = f"{project_root_dir}/hyperexecute"

            job_config.write_config(
                tc_client_id,
                tc_client_key,
                tc_worker_type,
                lt_app_url,
                test_run_file,
                device_type_and_os,
                # udid
                concurrency=1,
            )

            logging.info("starting job...")
            # Use test_mode instead of hardcoded DEBUG
            if self.test_mode:
                logging.info(
                    f"would be running command: '{command_string}' in path '{test_run_dir}'..."
                )
                logging.info("sleeping 30 seconds (to simulate starting job)...")
                time.sleep(30)
            else:
                logging.info(f"running: '{command_string}' in path '{test_run_dir}'...")
                start_time = time.time()
                # TODO: background so we can do this faster or set concurrencty in the YAML?
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

    # about modes
    #
    # MODE_SINGLE_JOB: single job started at a time
    # issues with mode 1:
    #   - depending on job run time, with more than 30-60 devices,
    #       we can't keep enough jobs running to keep up
    #
    # MODE_SINGLE_JOB_CONCURRENCY: single task, but use hyperexecute.yaml's concurrency
    # status: currently broken / needs more work
    # mode = MODE_SINGLE_JOB_CONCURRENCY
    #
    def run_single_project_single_thread_multi_job(
        self, max_jobs_to_start=None, foreground=False, mode=None
    ):
        if mode is None:
            mode = self.MODE_SINGLE_JOB
        # default the value
        if max_jobs_to_start is None:
            max_jobs_to_start = self.MAX_JOBS_TO_START_AT_ONCE
        # base on __file__ to get the project root dir
        project_source_dir = os.path.dirname(os.path.realpath(__file__))
        project_root_dir = os.path.abspath(os.path.join(project_source_dir, ".."))
        user_script_golden_dir = os.path.join(
            project_source_dir, "lambdatest", "user_script"
        )

        test_run_dir = "/tmp/mozilla-lt-devicepool-job-dir"
        test_run_file = os.path.join(test_run_dir, "hyperexecute.yaml")

        # overview:
        #   1. do configuration / load config data
        #   2. in loop:
        #     a. update tc queue count for lt queues
        #     b. update lt job status (how many running per each 'queue')
        #     c. start jobs for the tc queue with the appropriate devices

        # TODO: if we do multithreading, use messaging vs shared object with locks

        logging.info("entering run loop...")
        while self.state == self.STATE_RUNNING:
            # only a single project for now, so load that up
            current_project = self.config_object.config["projects"]["a55-alpha"]

            tc_worker_type = current_project["TC_WORKER_TYPE"]
            tc_client_id = current_project["TASKCLUSTER_CLIENT_ID"]
            tc_client_key = current_project["TASKCLUSTER_ACCESS_TOKEN"]
            # debug
            # print(f"tc_client_id: {tc_client_id}")
            # print(f"tc_client_key: {tc_client_key}")

            # TODO: check tc and if there are jobs, continue, exist go to sleep
            tc_job_count = get_taskcluster_pending_tasks(
                "proj-autophone", tc_worker_type, verbose=False
            )
            logging.info(f"tc_job_count: {tc_job_count}")
            if tc_job_count <= 0:
                logging.info(f"no jobs found, sleeping {self.no_job_sleep}s...")
                time.sleep(self.no_job_sleep)
            else:
                # TODO: verify this apk is ok, update the apk if needed, and store/use it's app_id
                lt_app_url = "lt://APP1016023521741987818221818"

                # remove /tmp/user_script dir
                shutil.rmtree(test_run_dir, ignore_errors=True)
                # create /tmp/mozilla-lt-devicepool-job-dir dir
                os.makedirs(test_run_dir, exist_ok=True)

                # TODO: copy user-script dir to correct dir (use basename on config_file_path?)
                # copy user_script_golden_dir to correct path using python shutil
                shutil.copytree(
                    user_script_golden_dir, os.path.join(test_run_dir, "user_script")
                )

                cmd_env = os.environ.copy()
                cmd_env["LT_USERNAME"] = self.config_object.lt_username
                cmd_env["LT_ACCESS_KEY"] = self.config_object.lt_access_key

                # set the device type, OS, and optionally UDID for this job
                #
                # for now we have a single pool of devices
                device_type_and_os = "Galaxy A55 5G-14"
                # udid = None
                # TODO: manage device state and specify UDID of exact device to target for each job
                #
                # DEBUG: jmaher is using the A55's right now
                device_type_and_os = "Galaxy A51-11"

                # hyperexecute job labels
                #
                # indicate this is scheduled by this program
                #   - use new name 'mozilla-taskcluster-devicepool'
                labels_csv = self.PROGRAM_LABEL
                # add the workerType to the labels
                labels_csv += f",{shorten_worker_type(tc_worker_type)}"
                # add the device type to the labels
                dtao_underscore = device_type_and_os.replace(" ", "_")
                labels_csv += f",{dtao_underscore}"
                # TODO: enable adding udid to the labels?
                # if udid:
                #     labels_csv += f",{udid}"

                # lt user and lt key are passsed in via env vars
                #   old: command_string = f"{project_root_dir}/hyperexecute --user \
                #           '{self.config_object.lt_username}' --key '{self.config_object.lt_api_key}'"
                labels_arg = f"--labels '{labels_csv}'"
                if foreground:
                    command_string = f"{project_root_dir}/hyperexecute {labels_arg}"
                else:
                    command_string = (
                        f"{project_root_dir}/hyperexecute --no-track {labels_arg}"
                    )

                #
                initiated_job_count = self.status_object.get_initiated_job_count()
                tc_jobs_not_handled = tc_job_count - initiated_job_count
                logging.debug(f"tc_jobs_not_handled: {tc_jobs_not_handled}")
                logging.debug(f"self.max_jobs_to_start: {self.max_jobs_to_start}")
                logging.debug(f"max_jobs_to_start: {self.max_jobs_to_start}")
                logging.debug(f"tc_job_count: {tc_job_count}")
                # logging.debug(f"initiated_job_count: {initiated_job_count}")
                jobs_to_start = min(
                    tc_jobs_not_handled, self.max_jobs_to_start, max_jobs_to_start
                )
                logging.info(f"jobs_to_start: {jobs_to_start}")
                # subtract the number of jobs already initiated
                # jobs_to_start = jobs_to_start - initiated_job_count
                # logging.info(f"initiated_job_count: {initiated_job_count}")
                # logging.info(f"jobs_to_start 2: {jobs_to_start}")

                current_mode = mode
                if jobs_to_start <= 0:
                    logging.info("no jobs to start, setting mode MODE_NO_OP...")
                    current_mode = self.MODE_NO_OP

                if current_mode == self.MODE_SINGLE_JOB:
                    # start the desired number of jobs (concurrency: 1)

                    # create hyperexecute.yaml specific to each queue
                    job_config.write_config(
                        tc_client_id,
                        tc_client_key,
                        tc_worker_type,
                        lt_app_url,
                        test_run_file,
                        device_type_and_os,
                        # udid
                        concurrency=1,
                    )

                    for i in range(jobs_to_start):
                        logging.info(f"starting job {i + 1} of {jobs_to_start}...")
                        # Use test_mode instead of hardcoded DEBUG
                        if self.test_mode:
                            logging.info(
                                f"would be running command: '{command_string}' in path '{test_run_dir}'..."
                            )
                            logging.info(
                                "sleeping 30 seconds (to simulate starting job)..."
                            )
                            time.sleep(30)
                        else:
                            logging.info(
                                f"running: '{command_string}' in path '{test_run_dir}'..."
                            )
                            start_time = time.time()
                            # TODO: background so we can do this faster or set concurrencty in the YAML?
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
                elif current_mode == self.MODE_SINGLE_JOB_WITH_CONCURRENCY:
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
                        test_run_file,
                        device_type_and_os,
                        # udid
                        concurrency=jobs_to_start,
                    )

                    logging.info(f"starting job with concurrency {jobs_to_start}...")
                    # Use test_mode instead of hardcoded DEBUG
                    if self.test_mode:
                        logging.info(
                            f"would be running command: '{command_string}' in path '{test_run_dir}'..."
                        )
                        logging.info(
                            "sleeping 30 seconds (to simulate starting job)..."
                        )
                        time.sleep(30)
                    else:
                        logging.info(
                            f"running: '{command_string}' in path '{test_run_dir}'..."
                        )
                        start_time = time.time()
                        # TODO: background so we can do this faster or set concurrencty in the YAML?
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
                            f"starting job took {round(end_time - start_time, 2)} seconds"
                        )
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

        # debugging
        # import pprint
        # pprint.pprint(trmlt.config_object.config)

        # start the main run loop

        # single job started at a time
        # trmlt.run_single_project_single_thread_multi_job(max_jobs_to_start=1, foreground=True)

        # multiple jobs started in background
        #   problems:
        #     - can start too many jobs since no get_pending_jobs lt call yet
        trmlt.run_single_project_single_thread_multi_job()  # max_jobs_to_start=5, foreground=False)
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
