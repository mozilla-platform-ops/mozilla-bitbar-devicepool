# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import threading
import time

import yaml

from mozilla_bitbar_devicepool import TESTDROID, logger
from mozilla_bitbar_devicepool.bitbar.device_groups import (
    add_devices_to_device_group,
    create_device_group,
    delete_device_from_device_group,
    get_device_group_devices,
    get_device_groups,
)
from mozilla_bitbar_devicepool.bitbar.devices import get_devices
from mozilla_bitbar_devicepool.bitbar.files import get_files
from mozilla_bitbar_devicepool.bitbar.frameworks import get_frameworks
from mozilla_bitbar_devicepool.bitbar.projects import (
    create_project,
    get_projects,
    update_project,
)
from mozilla_bitbar_devicepool.util.template import apply_dict_defaults

BITBAR_CACHE = {
    "device_groups": {},
    "devices": {},
    "files": {},
    "frameworks": {},
    "me": {},
    "projects": {},
    "test_runs": {},
}

FILESPATH = None
CONFIG = None


class ConfigurationException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class ConfigurationFileException(ConfigurationException):
    pass


class ConfigurationFileDuplicateFilenamesException(ConfigurationFileException):
    pass


class DuplicateProjectException(ConfigurationException):
    pass


def get_filespath():
    """Return files path where application and test files are kept."""
    return FILESPATH


def get_me_id():
    """Returns the Bitbar User ID that the application is using."""

    if BITBAR_CACHE["me"] == {}:
        BITBAR_CACHE["me"] = TESTDROID.get_me()
    # use 'id'
    # - not 'mainUserId' (user's can create sub-users)
    # - not 'accountId' (the organization's id))
    return BITBAR_CACHE["me"]["id"]


def ensure_filenames_are_unique(config):
    seen_filenames = []
    # TODO: break extraction of filenames out for easier testing
    try:
        for item in config["projects"]:
            for deeper_item in config["projects"][item]:
                if deeper_item == "application_file" or deeper_item == "test_file":
                    a_filename = config["projects"][item][deeper_item]
                    if a_filename in seen_filenames:
                        raise ConfigurationFileDuplicateFilenamesException(
                            "duplicate filenames found!"
                        )
                    seen_filenames.append(a_filename)
    except KeyError as e:
        print(e)
        raise ConfigurationFileException(
            "config does not appear to be in proper format"
        )
    return seen_filenames


def configure(bitbar_configpath, filespath=None, update_bitbar=False):
    """Parse and load the configuration yaml file
    defining the Mozilla Bitbar test setup.

    :param bitbar_configpath: string path to the config.yml
                              containing the Mozilla Bitbar
                              configuration.
    :param filespath: string path to the files directory where
                      application and test files are kept.
    """
    global CONFIG, FILESPATH

    FILESPATH = filespath

    logger.info("configure: starting configuration")
    start = time.time()

    with open(bitbar_configpath) as bitbar_configfile:
        CONFIG = yaml.load(bitbar_configfile.read(), Loader=yaml.SafeLoader)
    logger.info("configure: performing checks")
    try:
        ensure_filenames_are_unique(CONFIG)
    except ConfigurationFileException as e:
        logger.warning(e.message)
        sys.exit(1)
    expand_configuration()
    try:
        configuration_preflight()
    except ConfigurationFileException as e:
        logger.warning(e)
        logger.warning(
            "Configuration files seem to be missing! Please place and restart. Exiting..."
        )
        sys.exit(1)
    configure_device_groups(update_bitbar=update_bitbar)
    configure_projects(update_bitbar=update_bitbar)

    end = time.time()
    diff = end - start
    logger.info("configure: configuration took {} seconds".format(diff))


def expand_configuration():
    """Materializes the configuration. Sets default values when none are specified."""
    projects_config = CONFIG["projects"]
    project_defaults = projects_config["defaults"]

    for project_name in projects_config:
        if project_name == "defaults":
            continue

        project_config = projects_config[project_name]
        # Set the default project values.
        projects_config[project_name] = apply_dict_defaults(
            project_config, project_defaults
        )

    # TODO: remove 'defaults' from CONFIG['projects']?
    #   - would save later code from having to exclude it


def configuration_preflight():
    """Ensure that everything necessary for configuration is present."""
    projects_config = CONFIG["projects"]

    for project_name in projects_config:
        if project_name == "defaults":
            continue

        project_config = projects_config[project_name]
        file_name = project_config.get("test_file")
        if file_name:
            file_path = os.path.join(FILESPATH, file_name)
            if not os.path.exists(file_path):
                raise ConfigurationFileException("'%s' does not exist!" % file_path)

        file_name = project_config.get("application_file")
        if file_name:
            file_path = os.path.join(FILESPATH, file_name)
            if not os.path.exists(file_path):
                raise ConfigurationFileException("'%s' does not exist!" % file_path)


def configure_device_groups(update_bitbar=False):
    """Configure device groups from configuration.

    :param config: parsed yaml configuration containing
                   a device_groups attribute which contains
                   and object for each device group which contains
                   objects for each contained device.
    """
    # Cache the bitbar device data in the configuration.
    devices_cache = BITBAR_CACHE["devices"] = {}
    for device in get_devices():
        devices_cache[device["displayName"]] = device

    device_groups_config = CONFIG["device_groups"]
    for device_group_name in device_groups_config:
        logger.info(
            "configure_device_groups: configuring group {}".format(device_group_name)
        )
        device_group_config = device_groups_config[device_group_name]
        if device_group_config is None:
            # Handle the case where the configured device group is empty.
            device_group_config = device_groups_config[device_group_name] = {}
        new_device_group_names = set(device_group_config.keys())

        # get the current definition of the device group at bitbar.
        bitbar_device_groups = get_device_groups(displayname=device_group_name)
        if len(bitbar_device_groups) > 1:
            raise Exception(
                "device group {} has {} duplicates".format(
                    device_group_name, len(bitbar_device_groups) - 1
                )
            )
        elif len(bitbar_device_groups) == 1:
            bitbar_device_group = bitbar_device_groups[0]
            logger.debug(
                "configure_device_groups: configuring group {} to use {}".format(
                    device_group_name, bitbar_device_group
                )
            )
        else:
            # no such device group. create it.
            if update_bitbar:
                bitbar_device_group = create_device_group(device_group_name)
                logger.debug(
                    "configure_device_groups: configuring group {} to use newly created group {}".format(
                        device_group_name, bitbar_device_group
                    )
                )
            else:
                raise Exception(
                    "device group {} does not exist but can not create.".format(
                        device_group_name
                    )
                )

        bitbar_device_group_devices = get_device_group_devices(
            bitbar_device_group["id"]
        )
        bitbar_device_group_names = set(
            [device["displayName"] for device in bitbar_device_group_devices]
        )

        # determine which devices need to be deleted from or added to
        # the device group at bitbar.
        delete_device_names = bitbar_device_group_names - new_device_group_names
        add_device_names = new_device_group_names - bitbar_device_group_names

        delete_device_ids = [devices_cache[name]["id"] for name in delete_device_names]
        add_device_ids = [
            devices_cache[name]["id"]
            for name in add_device_names
            if name in devices_cache
        ]

        for device_id in delete_device_ids:
            if update_bitbar:
                delete_device_from_device_group(bitbar_device_group["id"], device_id)
            else:
                raise Exception(
                    "Attempting to remove device {} from group {}, but not configured to update bitbar config.".format(
                        device_id, bitbar_device_group["id"]
                    )
                )
            bitbar_device_group["deviceCount"] -= 1
            if bitbar_device_group["deviceCount"] < 0:
                raise Exception(
                    "device group {} has negative deviceCount".format(device_group_name)
                )

        if add_device_ids:
            if update_bitbar:
                bitbar_device_group = add_devices_to_device_group(
                    bitbar_device_group["id"], add_device_ids
                )
            else:
                raise Exception(
                    "Attempting to add device(s) {} to group {}, but not configured to update bitbar config.".format(
                        add_device_ids, bitbar_device_group["id"]
                    )
                )

        BITBAR_CACHE["device_groups"][device_group_name] = bitbar_device_group


def configure_projects(update_bitbar=False):
    """Configure projects from configuration.

    :param config: parsed yaml configuration containing
                   a projects attribute which contains
                   and object for each project.

    CONFIG['projects']['defaults'] contains values which will be set
    on the other projects if they are not already explicitly set.

    """
    projects_config = CONFIG["projects"]

    project_total = len(projects_config)
    counter = 0
    for project_name in projects_config:
        counter += 1
        log_header = "configure_projects: {} ({}/{})".format(
            project_name, counter, project_total
        )

        if project_name == "defaults":
            logger.info("{}: skipping".format(log_header))
            continue
        logger.info("{}: configuring...".format(log_header))

        project_config = projects_config[project_name]

        # for the project name at bitbar, add user id to the project_name
        # - prevents collision with other users' projects and allows us to
        #   avoid having to share projects
        api_user_id = get_me_id()
        user_project_name = "%s-%s" % (api_user_id, project_name)

        bitbar_projects = get_projects(name=user_project_name)
        if len(bitbar_projects) > 1:
            raise DuplicateProjectException(
                "project {} ({}) has {} duplicates".format(
                    project_name, user_project_name, len(bitbar_projects) - 1
                )
            )
        elif len(bitbar_projects) == 1:
            bitbar_project = bitbar_projects[0]
            logger.debug(
                "configure_projects: using project {} ({})".format(
                    bitbar_project, user_project_name
                )
            )
        else:
            if update_bitbar:
                bitbar_project = create_project(
                    user_project_name, project_type=project_config["project_type"]
                )
                logger.debug(
                    "configure_projects: created project {} ({})".format(
                        bitbar_project, user_project_name
                    )
                )
            else:
                raise Exception(
                    "Project {} ({}) does not exist, but not creating as not configured to update bitbar!".format(
                        project_name, user_project_name
                    )
                )

        framework_name = project_config["framework_name"]
        BITBAR_CACHE["frameworks"][framework_name] = get_frameworks(
            name=framework_name
        )[0]

        logger.info("{}: configuring test file".format(log_header))
        file_name = project_config.get("test_file")
        if file_name:
            bitbar_files = get_files(name=file_name)
            if len(bitbar_files) > 0:
                bitbar_file = bitbar_files[-1]
            else:
                if update_bitbar:
                    TESTDROID.upload_file(os.path.join(FILESPATH, file_name))
                    bitbar_file = get_files(name=file_name)[-1]
                else:
                    raise Exception(
                        "Test file {} not found and not configured to update bitbar configuration!".format(
                            file_name
                        )
                    )
            BITBAR_CACHE["files"][file_name] = bitbar_file

        logger.info("{}: configuring application file".format(log_header))
        file_name = project_config.get("application_file")
        if file_name:
            bitbar_files = get_files(name=file_name)
            if len(bitbar_files) > 0:
                bitbar_file = bitbar_files[-1]
            else:
                if update_bitbar:
                    TESTDROID.upload_file(os.path.join(FILESPATH, file_name))
                    bitbar_file = get_files(name=file_name)[-1]
                else:
                    raise Exception(
                        "Application file {} not found and not configured to update bitbar configuration!".format(
                            file_name
                        )
                    )
            BITBAR_CACHE["files"][file_name] = bitbar_file

        # Sync the base project properties if they have changed.
        if (
            project_config["archivingStrategy"] != bitbar_project["archivingStrategy"]
            or project_config["archivingItemCount"]
            != bitbar_project["archivingItemCount"]
            or project_config["description"] != bitbar_project["description"]
        ):
            # project basic attributes changed in config, update bitbar version.
            if update_bitbar:
                bitbar_project = update_project(
                    bitbar_project["id"],
                    user_project_name,
                    archiving_item_count=project_config["archivingItemCount"],
                    archiving_strategy=project_config["archivingStrategy"],
                    description=project_config["description"],
                )
            else:
                logger.warning(
                    'archivingStrategy: pc: "{}" bb: "{}"'.format(
                        project_config["archivingStrategy"],
                        bitbar_project["archivingStrategy"],
                    )
                )
                logger.warning(
                    'archivingItemCount: pc: "{}" bb: "{}"'.format(
                        project_config["archivingItemCount"],
                        bitbar_project["archivingItemCount"],
                    )
                )
                logger.warning(
                    'description: pc: "{}" bb: "{}"'.format(
                        project_config["description"], bitbar_project["description"]
                    )
                )
                raise Exception(
                    "The remote configuration for {} ({}) differs from the local configuration, but not configured to update bitbar!".format(
                        project_name, user_project_name
                    )
                )

        additional_parameters = project_config["additional_parameters"]
        if "TC_WORKER_TYPE" in additional_parameters:
            # Add the TASKCLUSTER_ACCESS_TOKEN from the environment to
            # the additional_parameters in order that the bitbar
            # projects may be configured to use it. Non-taskcluster
            # projects such as mozilla-docker-build are not invoke by
            # Taskcluster currently.
            taskcluster_access_token_name = additional_parameters[
                "TC_WORKER_TYPE"
            ].replace("-", "_")
            additional_parameters["TASKCLUSTER_ACCESS_TOKEN"] = os.environ[
                taskcluster_access_token_name
            ]

        BITBAR_CACHE["projects"][project_name] = bitbar_project
        BITBAR_CACHE["projects"][project_name]["lock"] = threading.Lock()

        device_group_name = project_config["device_group_name"]
        device_group = BITBAR_CACHE["device_groups"][device_group_name]

        BITBAR_CACHE["projects"][project_name]["stats"] = {
            "COUNT": device_group["deviceCount"],
            "IDLE": 0,
            "OFFLINE_DEVICES": 0,
            "OFFLINE": 0,
            "DISABLED": 0,
            "RUNNING": 0,
            "WAITING": 0,
        }
