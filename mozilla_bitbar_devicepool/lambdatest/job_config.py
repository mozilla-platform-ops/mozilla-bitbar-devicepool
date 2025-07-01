# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import os


def write_config(
    tc_client_id,
    tc_access_token,
    tc_worker_type,
    lt_app_url,
    udid=None,
    concurrency=1,
    path="/tmp/mozilla-lt-devicepool-job-dir/hyperexecute.yaml",
):
    """
    Generate a LambdaTest HyperExecute configuration and write it to a file.

    Args:
        tc_client_id (str): Taskcluster client ID for authentication.
        tc_access_token (str): Taskcluster access token for authentication.
        lt_app_url (str): URL to the application under test on LambdaTest.
        udid (str, optional): The unique device identifier if targeting a specific device. Defaults to None.
        path (str, optional): Destination path for the config file.
                              Defaults to "/tmp/mozilla-lt-devicepool-job-dir/hyperexecute.yaml".
        concurrency (int, optional): Number of parallel test executions. Defaults to 1.

    Returns:
        str: Path where the configuration file was written.
    """

    # show all options passed in
    logging.debug(f"write_config: tc_client_id: {tc_client_id}")
    logging.debug(f"write_config: tc_access_token: {tc_access_token}")
    logging.debug(f"write_config: tc_worker_type: {tc_worker_type}")
    logging.debug(f"write_config: lt_app_url: {lt_app_url}")
    logging.debug(f"write_config: udid: {udid}")
    logging.debug(f"write_config: path: {path}")
    logging.debug(f"write_config: concurrency: {concurrency}")

    config = return_config(
        tc_client_id,
        tc_access_token,
        tc_worker_type,
        lt_app_url,
        udid,
        concurrency,
    )

    # mkdir -p the path
    dir_to_create = os.path.dirname(path)
    os.makedirs(dir_to_create, exist_ok=True)

    with open(path, "w") as f:
        f.write(config)
    return path


def return_config(
    tc_client_id,
    tc_access_token,
    tc_worker_type,
    lt_app_url,
    udid=None,
    concurrency=1,
):
    """
    Generate a LambdaTest HyperExecute configuration YAML as a string.

    Args:
        tc_client_id (str): Taskcluster client ID for authentication.
        tc_access_token (str): Taskcluster access token for authentication.
        lt_app_url (str): URL to the application under test on LambdaTest.
        udid (str, optional): The unique device identifier if targeting a specific device. Defaults to None.
        concurrency (int, optional): Number of parallel test executions. Defaults to 1.

    Returns:
        str: Complete HyperExecute YAML configuration as a string.
    """
    # TODO: document decision to inject secrets here vs using lt's built-in secret storage
    #   thinking:
    #   - they already have the secrets in their systems
    #   - why store it in another spot that we have to maintain?
    #
    # template code for using LT secrets:
    # use lt's built-in secret storage
    # TASKCLUSTER_ACCESS_TOKEN: ${{.secrets.TC_ACCESS_TOKEN}}
    # TASKCLUSTER_CLIENT_ID: ${{.secrets.TC_CLIENT_ID}}

    test_discover_cmd = ""
    for i in range(concurrency):
        test_discover_cmd += f'echo "taskcluster generic-worker {i}"; '

    fixed_ip_line = "#"
    if udid:
        fixed_ip_line = f'fixedIP: "{udid}"'

    # TODO?: sanity check device_type_and_os (includes hyphen, valid device type)

    # here doc with the config, we need string interpolation
    config = f"""
# Define the version of the configuration file
version: "0.2"

# Enable autosplit for test execution
autosplit: true

# Specify the target platform for test execution (Android in this case)
runson: android

# Set the concurrency level for test execution (2 devices in parallel)
concurrency: {concurrency}

# Test discovery configuration
testDiscovery:
  command: {test_discover_cmd}
  # Test discovery mode is static
  mode: static
  # Test type is raw (custom test implementation)
  type: raw

runtime:
  - language: java
    version: "17"
  - language: node
    version: '20'

env:
    # inject our own secrets
    TASKCLUSTER_CLIENT_ID: {tc_client_id}
    TASKCLUSTER_ACCESS_TOKEN: {tc_access_token}
    TC_WORKER_TYPE: {tc_worker_type}

# Command to run the tests using the testRunnerCommand
# testRunnerCommand: ls -la
# testRunnerCommand: cat /home/ltuser/taskcluster/worker-runner-config.yml
# testRunnerCommand: start-worker /home/ltuser/taskcluster/worker-runner-config.yml
testRunnerCommand: python3 /home/ltuser/taskcluster/run_gw.py

# Only report the status of the test framework
frameworkStatusOnly: true

# Enable dynamic allocation of resources
dynamicAllocation: true

shell: bash

# aje: moved all to test command as something we're doing in pre is disconnecting the device per LT
#
# Pre-install required dependencies using pip
pre:
  - pip3 install mozdevice
  - bash ./user_script/setup_script.sh

# reboot and wait for device to come online
post:
  - python3 ./user_script/reboot_and_wait.py

# cache the payload
differentialUpload:
  enabled: true
  ttlHours: 360

# Test framework configuration
framework:
  # Name of the test framework (raw in this case)
  name: raw
  args:
    # used to restrict device model and os version
    # - we don't use it currently (see fixedIP), so use wildcard
    devices: ".*-.*"
    framework:
    # fixedIP: can take the UDID a specific devices to run on
    {fixed_ip_line}
    # Enable or disable video recording support
    video: true
    # Enable or disable device log support
    deviceLogs: true
    # App ID to be installed (mandatory field, using <app_id>)
    # appId: {lt_app_url}
    # Build name for identification on the automation dashboard
    buildName: geckoview_example.apk
    # All devices are in a private cloud
    privateCloud: true
    # Timeout for device queue
    queueTimeout: 600
    # Configuration fields specific to running raw tests
    region: us
    disableReleaseDevice: true
    isRealMobile: true
    reservation: false
    platformName: android

"""
    return config
