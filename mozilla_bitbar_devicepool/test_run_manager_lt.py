# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import signal
import logging
import time

from mozilla_bitbar_devicepool import configuration_lt

STOP = "000000001"
RUNNING = "000000002"


class TestRunManagerLT(object):

    def __init__(self, exit_wait=5):
        self.exit_wait = exit_wait
        self.state = RUNNING
        self.config_object = configuration_lt.ConfigurationLt()
        self.config_object.configure()

        signal.signal(signal.SIGUSR2, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)

    def handle_signal(self, signalnum, frame):
        if self.state != RUNNING:
            return

        if signalnum == signal.SIGINT or signalnum == signal.SIGUSR2:
            self.state = STOP
            # logging.info doesn't work in signal handlers
            print(
                f" handle_signal: set state to stop, exiting in {self.exit_wait} seconds or less"
            )

    def run(self):

        # overview:
        #   1. do configuration / load config data
        #   2. in loop:
        #     a. update tc queue count for lt queues
        #     b. update lt job status (how many running per each 'queue')
        #     c. start jobs for the tc queue with the appropriate devices

        while self.state == RUNNING:
            # use logging to print 'running' with a datetime
            logging.info("Running...")

            print("Running...")

            # `./hyperexecute –config hyperexecute.yaml

            if self.state == STOP:
                break
            time.sleep(self.exit_wait)
            if self.state == STOP:
                break


if __name__ == "__main__":
    # set logging levvel to info
    logging.basicConfig(level=logging.INFO)
    trmlt = TestRunManagerLT()
    trmlt.run()
