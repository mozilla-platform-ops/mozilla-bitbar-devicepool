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
    def __init__(self, ci_mode=False, quiet=False):
        # TODO?: mash all values into 'config'?
        self.lt_access_key = None
        self.lt_username = None
        self.config = {}
        self.ci_mode = ci_mode
        self.quiet = quiet
        # for tracking if lt_device_selector is set and devices are configured
        self.fully_configured_projects = {}

        if self.ci_mode and not self.quiet:
            print("ConfigurationLt: Running in CI mode. Using fake credentials.")

    def _load_file_config(self, config_path="config/lambdatest.yml"):
        # get this file's directory path
        this_dir = os.path.dirname(os.path.realpath(__file__))
        # get the absolute path
        full_config_path = os.path.join(this_dir, "..", config_path)

        with open(full_config_path) as lt_configfile:
            loaded_config = yaml.load(lt_configfile.read(), Loader=yaml.SafeLoader)
        self.config = loaded_config

    def get_config(self):
        return self.config

    def _set_lt_api_key(self):
        # load from os environment
        if self.ci_mode:
            self.lt_api_key = "fake123"
            return
        if "LT_ACCESS_KEY" not in os.environ:
            raise ValueError("LT_ACCESS_KEY not found in environment variables")
        self.lt_access_key = os.environ.get("LT_ACCESS_KEY")
        # self.config["lt_access_key"] = self.lt_api_key

    def _set_lt_username(self):
        # load from os environment
        if self.ci_mode:
            self.lt_username = "fake123"
            return
        if "LT_USERNAME" not in os.environ:
            raise ValueError("LT_USERNAME not found in environment variables")
        self.lt_username = os.environ.get("LT_USERNAME")
        # self.config["lt_username"] = self.lt_username

    def _load_tc_env_vars(self):
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

    def _expand_configuration(self):
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

        # massage device_groups into a more usable format
        for item in project_device_groups:
            if project_device_groups[item] is not None:
                project_device_groups[item] = project_device_groups[item].split(" ")
            else:
                # if we don't have a entry in projects, skip it
                projects_config[item] = {}

        # remove the defaults project
        del projects_config["defaults"]

    def get_project_for_udid(self, udid):
        """
        Finds the project name associated with a given device UDID.

        Args:
            udid (str): The UDID of the device to look up.

        Returns:
            str or None: The name of the project the device belongs to,
                         or None if the UDID is not found in any device group.
        """
        device_groups = self.config.get("device_groups", {})
        for project_name, udid_list in device_groups.items():
            if not udid_list:
                # if the project has no phones, skip it
                continue
            if udid in udid_list:
                return project_name
        return None

    def get_device_count_for_project(self, project_name):
        """
        Returns the number of devices associated with a given project.

        Args:
            project_name (str): The name of the project to look up.

        Returns:
            int: The number of devices associated with the project.
        """
        device_groups = self.config.get("device_groups", {})
        import pprint

        pprint.pprint(device_groups)
        if project_name in device_groups:
            return len(device_groups[project_name])
        return 0

    def configure(self, config_blob=None, config_path=None):
        # TODO?: add filespath?

        # Check for hyperexecute binary on path using a shell command
        if not self.ci_mode:
            cmd = "where" if sys.platform == "win32" else "which"
            try:
                subprocess.check_call([cmd, "hyperexecute"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError:
                raise FileNotFoundError("hyperexecute binary not found on the system PATH")

        if config_blob and config_path:
            raise ValueError("Cannot specify both config_blob and config_path")

        # load the data we need
        if config_blob:
            self.config = config_blob
        elif config_path:
            self._load_file_config(config_path)
        else:
            self._load_file_config()

        self._load_tc_env_vars()
        self._set_lt_api_key()
        self._set_lt_username()

        self._set_fully_configured_projects()

        # debug print
        # print(self.get_config())

        # expand the configuration
        self._expand_configuration()

    def is_project_fully_configured(self, project_name):
        """
        Checks if a project is fully configured for LambdaTest execution.

        A project is considered fully configured when it's present in
        self.fully_configured_projects (see _set_fully_configured_projects
        for full details).

        Args:
            project_name (str): The name of the project to check.

        Returns:
            bool: True if the project is fully configured, False otherwise.
        """
        return project_name in self.fully_configured_projects

    def _set_fully_configured_projects(self):
        """
        Identifies which projects are fully configured for LambdaTest execution.
        A project is considered fully configured when:
        1. It exists in the projects configuration (not 'defaults')
        2. It has at least one device assigned in device_groups
        3. It has a lt_device_selector configured in the project configuration

        Sets self.fully_configured_projects to a list of project names that are fully configured.
        """
        self.fully_configured_projects = []
        projects_config = self.config.get("projects", {})
        device_groups = self.config.get("device_groups", {})

        for project_name in projects_config:
            if project_name == "defaults":
                continue

            # Check if the project has devices assigned
            has_devices = (
                project_name in device_groups
                and device_groups[project_name] is not None
                and len(device_groups[project_name]) > 0
            )

            # Check if the project has lt_device_selector configured
            has_device_selector = (
                "lt_device_selector" in projects_config[project_name]
                and projects_config[project_name]["lt_device_selector"] is not None
            )

            # A project is fully configured if it has both devices assigned and a device selector
            if has_devices and has_device_selector:
                self.fully_configured_projects.append(project_name)

        sorted(self.fully_configured_projects)

        if not self.quiet:
            configured_count = len(self.fully_configured_projects)
            total_count = len(projects_config) - 1  # Exclude defaults
            print(f"Fully configured projects: {configured_count}/{total_count}")


if __name__ == "__main__":
    clt = ConfigurationLt()
    clt.configure()
    pprint.pprint(clt.get_config())
