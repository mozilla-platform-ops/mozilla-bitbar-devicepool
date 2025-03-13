# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import yaml


def get_config(config_path="config/lambdatest.yml"):
    # get this file's directory path
    this_dir = os.path.dirname(os.path.realpath(__file__))
    # get the absolute path of the config file at ../config/lambdatest.yml
    full_config_path = os.path.join(this_dir, "..", config_path)

    with open(full_config_path) as lt_configfile:
        loaded_config = yaml.load(lt_configfile.read(), Loader=yaml.SafeLoader)
    return loaded_config


def configure():
    # TODO: add filespath?

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
    config = get_config()
    print(config)
