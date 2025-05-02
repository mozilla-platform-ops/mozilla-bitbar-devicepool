# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import yaml
import subprocess
import sys
import pprint

from mozilla_bitbar_devicepool.util.template import apply_dict_defaults


class ConfigurationLt(object):
    def __init__(self, ci_mode=False):
        # TODO?: mash all values into 'config'?
        self.lt_access_key = None
        self.lt_username = None
        self.config = {}
        self.ci_mode = ci_mode

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
        if self.ci_mode:
            self.lt_api_key = "fake123"
            return
        if "LT_ACCESS_KEY" not in os.environ:
            raise ValueError("LT_ACCESS_KEY not found in environment variables")
        self.lt_access_key = os.environ.get("LT_ACCESS_KEY")
        # self.config["lt_access_key"] = self.lt_api_key

    def set_lt_username(self):
        # load from os environment
        if self.ci_mode:
            self.lt_username = "fake123"
            return
        if "LT_USERNAME" not in os.environ:
            raise ValueError("LT_USERNAME not found in environment variables")
        self.lt_username = os.environ.get("LT_USERNAME")
        # self.config["lt_username"] = self.lt_username

    def load_tc_env_vars(self):
        for project_name in self.config["projects"]:
            if project_name == "defaults":
                continue
            data = self.config["projects"][project_name]
            taskcluster_access_token_name = data["TC_WORKER_TYPE"].replace("-", "_")
            # ensure the environment variable is set
            if self.ci_mode:
                data["TASKCLUSTER_ACCESS_TOKEN"] = "fake123"
                continue
            if taskcluster_access_token_name not in os.environ:
                raise ValueError(f"Environment variable {taskcluster_access_token_name} not found")
            data["TASKCLUSTER_ACCESS_TOKEN"] = os.environ[taskcluster_access_token_name]

    def expand_configuration(self):
        """Materializes the configuration. Sets default values when none are specified."""
        projects_config = self.config["projects"]
        project_defaults = projects_config["defaults"]
        project_device_groups = self.config["device_groups"]

        for project_name in projects_config:
            if project_name == "defaults":
                continue

            project_config = projects_config[project_name]
            # Set the default project values.
            projects_config[project_name] = apply_dict_defaults(project_config, project_defaults)

        # TODO?: remove 'defaults' from CONFIG['projects']?
        #   - would save later code from having to exclude it

        # massage device_groups into a more usable format
        for item in project_device_groups:
            project_device_groups[item] = project_device_groups[item].split(" ")

        # remove the defaults project
        del projects_config["defaults"]

    def configure(self):
        # TODO?: add filespath?

        # Check for hyperexecute binary on path using a shell command
        if not self.ci_mode:
            cmd = "where" if sys.platform == "win32" else "which"
            try:
                subprocess.check_call([cmd, "hyperexecute"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError:
                raise FileNotFoundError("hyperexecute binary not found on the system PATH")

        # load the data we need
        self.load_file_config()
        self.load_tc_env_vars()
        self.set_lt_api_key()
        self.set_lt_username()

        # debug print
        # print(self.get_config())

        # expand the configuration
        self.expand_configuration()


if __name__ == "__main__":
    clt = ConfigurationLt()
    clt.configure()
    pprint.pprint(clt.get_config())
