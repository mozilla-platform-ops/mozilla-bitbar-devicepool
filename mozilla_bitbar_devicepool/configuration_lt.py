# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import yaml
import subprocess
import sys


class ConfigurationLt(object):

    def __init__(self):
        # TODO: mash all values into 'config'?
        self.lt_api_key = None
        self.lt_username = None
        self.config = {}
        pass

    def load_file_config(self, config_path="config/lambdatest.yml"):
        # get this file's directory path
        this_dir = os.path.dirname(os.path.realpath(__file__))
        # get the absolute path
        full_config_path = os.path.join(this_dir, "..", config_path)

        with open(full_config_path) as lt_configfile:
            loaded_config = yaml.load(lt_configfile.read(), Loader=yaml.SafeLoader)
        self.config = loaded_config

    def get_config(self):
        return self.config

    def set_lt_api_key(self):
        # load from os environment
        if "LT_API_KEY" not in os.environ:
            raise ValueError("LT_API_KEY not found in environment variables")
        self.lt_api_key = os.environ.get("LT_API_KEY")
        self.config["lt_api_key"] = self.lt_api_key

    def set_lt_username(self):
        # load from os environment
        if "LT_USERNAME" not in os.environ:
            raise ValueError("LT_USERNAME not found in environment variables")
        self.lt_username = os.environ.get("LT_USERNAME")
        self.config["lt_username"] = self.lt_username

    def configure(self):
        # TODO: add filespath?

        # Check for hyperexecute binary on path using a shell command
        cmd = "where" if sys.platform == "win32" else "which"
        try:
            subprocess.check_call(
                [cmd, "hyperexecute"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError:
            raise FileNotFoundError("hyperexecute binary not found on the system PATH")

        # load the data we need
        self.load_file_config()
        self.set_lt_api_key()
        self.set_lt_username()

        # copied from configuration:configure
        #
        # with open(bitbar_configpath) as bitbar_configfile:
        #     CONFIG = yaml.load(bitbar_configfile.read(), Loader=yaml.SafeLoader)

        # global CONFIG, FILESPATH

        # FILESPATH = filespath

        # logger.info("configure: starting configuration")
        # start = time.time()

        # with open(bitbar_configpath) as bitbar_configfile:
        #     CONFIG = yaml.load(bitbar_configfile.read(), Loader=yaml.SafeLoader)
        # logger.info("configure: performing checks")
        # try:
        #     ensure_filenames_are_unique(CONFIG)
        # except ConfigurationFileException as e:
        #     logger.warning(e.message)
        #     sys.exit(1)
        # expand_configuration()
        # try:
        #     configuration_preflight()
        # except ConfigurationFileException as e:
        #     logger.warning(e)
        #     logger.warning(
        #         "Configuration files seem to be missing! Please place and restart. Exiting..."
        #     )
        #     sys.exit(1)
        # configure_device_groups(update_bitbar=update_bitbar)
        # configure_projects(update_bitbar=update_bitbar)

        # end = time.time()
        # diff = end - start
        # logger.info("configure: configuration took {} seconds".format(diff))

        pass


if __name__ == "__main__":
    clt = ConfigurationLt()
    clt.configure()
    print(clt.get_config())
