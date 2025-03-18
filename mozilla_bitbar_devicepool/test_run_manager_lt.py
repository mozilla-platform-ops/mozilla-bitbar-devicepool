# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.


import shutil
import signal
import logging
import time
import os
import subprocess
import argparse

from mozilla_bitbar_devicepool import configuration_lt, logging_setup
from mozilla_bitbar_devicepool.lambdatest import job_config
from mozilla_bitbar_devicepool.taskcluster import get_taskcluster_pending_tasks


# state constants
STOP = "000000001"
RUNNING = "000000002"


class TestRunManagerLT(object):
    def __init__(self, exit_wait=5, no_job_sleep=60, test_mode=False):
        self.exit_wait = exit_wait
        self.no_job_sleep = no_job_sleep
        self.state = RUNNING
        self.test_mode = test_mode
        self.config_object = configuration_lt.ConfigurationLt()
        self.config_object.configure()

        signal.signal(signal.SIGUSR2, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)

    def handle_signal(self, signalnum, frame):
        if self.state != RUNNING:
            return

        if signalnum == signal.SIGINT or signalnum == signal.SIGUSR2:
            self.state = STOP
            logging.info(
                # f" handle_signal: set state to stop, exiting in {self.exit_wait} seconds or less"
                " handle_signal: set state to stop, will exit after current job completes"
            )
            # for testing, exit immediately
            # sys.exit(0)

    def run(self):
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

        logging.info("entering run loop...")
        while self.state == RUNNING:
            # only a single project for now, so load that up
            current_project = self.config_object.config["projects"]["a55-alpha"]

            # TODO: check tc and if there are jobs, continue, exist go to sleep
            tc_job_count = get_taskcluster_pending_tasks(
                "proj-autophone", current_project["TC_WORKER_TYPE"], verbose=False
            )
            print(f"tc_job_count: {tc_job_count}")
            if tc_job_count <= 0:
                print(f"no jobs found, sleeping {self.no_job_sleep}s...")
                time.sleep(self.no_job_sleep)
            else:
                # tc_worker_type = current_project["TC_WORKER_TYPE"]
                tc_client_id = current_project["TASKCLUSTER_CLIENT_ID"]
                tc_client_key = current_project["TASKCLUSTER_ACCESS_TOKEN"]
                # debug
                # print(f"tc_client_id: {tc_client_id}")
                # print(f"tc_client_key: {tc_client_key}")

                # TODO: verify this apk is ok, update the apk if needed, and store/use it's app_id
                lt_app_url = "lt://APP1016023521741987818221818"

                # remove /tmp/user_script dir
                shutil.rmtree(test_run_dir, ignore_errors=True)
                # create /tmp/mozilla-lt-devicepool-job-dir dir
                os.makedirs(test_run_dir, exist_ok=True)

                # TODO: create hyperexecute.yaml specific to each queue
                job_config.write_config(
                    tc_client_id,
                    tc_client_key,
                    lt_app_url,
                    test_run_file,
                    concurrency=1,
                )

                # TODO: copy user-script dir to correct dir (use basename on config_file_path?)
                # copy user_script_golden_dir to correct path using python shutil
                shutil.copytree(
                    user_script_golden_dir, os.path.join(test_run_dir, "user_script")
                )

                # TODO: loop the number of jobs we need
                # TODO: use env vars for setting user and key
                # lt user and lt key are passsed in via env vars
                # command_string = f"{project_root_dir}/hyperexecute --user '{self.config_object.lt_username}' --key '{self.config_object.lt_api_key}'"
                command_string = f"{project_root_dir}/hyperexecute"

                cmd_env = os.environ.copy()
                cmd_env["LT_USERNAME"] = self.config_object.lt_username
                cmd_env["LT_ACCESS_KEY"] = self.config_object.lt_api_key

                # Use test_mode instead of hardcoded DEBUG
                if self.test_mode:
                    logging.info(
                        f"would be running command: '{command_string}' in path '{test_run_dir}'..."
                    )
                else:
                    logging.info(
                        f"running: '{command_string}' in path '{test_run_dir}'..."
                    )
                    # TODO: use --no-track or figure out how to make subprocess interactive so it doesn't die
                    subprocess.run(
                        command_string, shell=True, env=cmd_env, cwd=test_run_dir
                    )

            if self.state == STOP:
                break
            time.sleep(self.exit_wait)
            if self.state == STOP:
                break


def parse_args():
    parser = argparse.ArgumentParser(description="Test Run Manager for LambdaTest")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode without executing commands",
    )
    return parser.parse_args()


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_args()

    # Configure logging explicitly
    logging_setup.setup_logging()

    # logging is now properly configured
    trmlt = TestRunManagerLT(test_mode=args.test)

    # debugging
    # import pprint
    # pprint.pprint(trmlt.config_object.config)

    # start the main run loop
    trmlt.run()
