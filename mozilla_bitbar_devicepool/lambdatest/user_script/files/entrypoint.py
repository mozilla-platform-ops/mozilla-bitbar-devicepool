#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import os


def dump_scriptvars():
    """
    Read the variables passed from the Docker host via the environment
    and create a json file /home/ltuser/taskcluster/scriptvars.json containing
    their values.

    The payload script will read this file and recreate the necessary
    environment

    This is necessary due to the fact that taskcluster-worker does not
    pass the environment variables in its environment to its payload
    script.

    """
    names = (
        "ANDROID_DEVICE",
        "DEVICE_IP",
        "DEVICE_NAME",
        "DEVICE_SERIAL",
        "DOCKER_IMAGE_VERSION",
        "HOME",
        "HOST_IP",
        "HOSTNAME",
        "PATH",
        "PYTHONIOENCODING",
        "TC_WORKER_GROUP",
        "ANDROID_SERIAL",
        "UserPorts",
        "TC_WORKER_TYPE",
        "TESTDROID_BUILD_ID",
        "TESTDROID_PROJECT_ID",
        "TESTDROID_RUN_ID",
        "USER",
    )
    variables = dict((k, get_envvar(k)) for k in names)

    with open("/home/ltuser/taskcluster/scriptvars.env", "w") as scriptvarsb:
        for item in variables:
            scriptvarsb.write('export %s="%s"\n' % (item, variables[item]))

    with open("/home/ltuser/taskcluster/scriptvars.json", "w") as scriptvars:
        scriptvars.write(json.dumps(variables))


# returns empty string if not defined
def get_envvar(name):
    if name in os.environ:
        return os.environ[name]
    return ""


def main():
    dump_scriptvars()


if __name__ == "__main__":
    main()
