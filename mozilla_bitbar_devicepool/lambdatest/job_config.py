# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.


def write_config(
    tc_client_id,
    tc_access_token,
    lt_app_url,
    path="/tmp/mozilla-lt-devicepool-job-dir/hyperexecute.yaml",
    concurrency=1,
):
    config = return_config(tc_client_id, tc_access_token, lt_app_url, concurrency)
    with open(path, "w") as f:
        f.write(config)
    return path


# TODO: take devices, workerType
def return_config(tc_client_id, tc_access_token, lt_app_url, concurrency=1):
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

env:
    # inject our own secrets
    TASKCLUSTER_CLIENT_ID: {tc_client_id}
    TASKCLUSTER_ACCESS_TOKEN: {tc_access_token}

# Command to run the tests using the testRunnerCommand
testRunnerCommand: python3 /home/ltuser/taskcluster/run_gw.py
# testRunnerCommand: start-worker /home/ltuser/taskcluster/worker-runner-config.yml
# testRunnerCommand: /home/ltuser/taskcluster/start-worker /home/ltuser/taskcluster/worker-runner-config.yml
# testRunnerCommand: ls -la
# testRunnerCommand: cat /home/ltuser/taskcluster/worker-runner-config.yml
# testRunnerCommand: bash ./user_script/setup_and_run_gw.sh

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
    # List of devices to run tests on (two Pixel 5 devices in this case)
    devices: ["Galaxy A55 5G-14"]
    # Enable or disable video recording support
    video: true
    # Enable or disable device log support
    deviceLogs: true
    # App ID to be installed (mandatory field, using <app_id>)
    appId: {lt_app_url}
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
