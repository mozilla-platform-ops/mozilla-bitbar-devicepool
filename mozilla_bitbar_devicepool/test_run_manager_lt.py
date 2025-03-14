# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import signal

from mozilla_bitbar_devicepool import configuration_lt


class TestRunManagerLT(object):

    def __init__(self, wait=60):
        self.wait = wait
        self.state = "RUNNING"

        signal.signal(signal.SIGUSR2, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)

    def handle_signal(self, signalnum, frame):
        if self.state != "RUNNING":
            return

        if signalnum == signal.SIGINT or signalnum == signal.SIGUSR2:
            self.state = "STOP"

    def run(self):
        while self.state == "RUNNING":
            print("Running...")
            # do something

            # `./hyperexecute –config hyperexecute.yaml

            pass


if __name__ == "__main__":
    # if main
    # get configuration
    config = configuration_lt.get_config()
    # print configuration
    print(config)
    # end if main
