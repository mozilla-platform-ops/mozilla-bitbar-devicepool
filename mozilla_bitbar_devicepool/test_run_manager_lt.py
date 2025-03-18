# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.


import shutil
import signal
import logging
import time
import os
import subprocess
import sys

from mozilla_bitbar_devicepool import configuration_lt, logging_setup
from mozilla_bitbar_devicepool.lambdatest import job_config


# state constants
STOP = "000000001"
RUNNING = "000000002"


class TestRunManagerLT(object):
    def __init__(self, exit_wait=5):
        self.exit_wait = exit_wait
        self.state = RUNNING
        self.config_object = configuration_lt.ConfigurationLt()
        self.config_object.configure()

        # signal.signal(signal.SIGUSR2, self.handle_signal)
        # signal.signal(signal.SIGINT, self.handle_signal)

    def handle_signal(self, signalnum, frame):
        if self.state != RUNNING:
            return

        if signalnum == signal.SIGINT or signalnum == signal.SIGUSR2:
            self.state = STOP
            sys.exit(0)
            logging.info(
                # f" handle_signal: set state to stop, exiting in {self.exit_wait} seconds or less"
                " handle_signal: set state to stop"
            )

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

            DEBUG = True
            if DEBUG:
                logging.info(
                    f"would be running command: '{command_string}' in path '{test_run_dir}'..."
                )
            else:
                logging.info(f"running: '{command_string}' in path '{test_run_dir}'...")
                # TODO: use --no-track or figure out how to make subprocess interactive so it doesn't die
                subprocess.run(command_string, shell=True, cwd=test_run_dir)

            if self.state == STOP:
                break
            time.sleep(60)
            if self.state == STOP:
                break


if __name__ == "__main__":
    # Configure logging explicitly
    logging_setup.setup_logging()

    # logging is now properly configured
    trmlt = TestRunManagerLT()

    # debugging
    # import pprint
    # pprint.pprint(trmlt.config_object.config)

    # start the main run loop
    trmlt.run()
