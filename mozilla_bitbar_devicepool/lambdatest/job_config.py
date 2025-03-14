def write_config(tc_client_id, tc_access_token, concurrency=1):
    config = return_config(tc_client_id, tc_access_token, concurrency)
    with open("/tmp/hyperexecute.yaml", "w") as f:
        f.write(config)
    return "/tmp/hyperexecute.yaml"


# TODO: take devices, workerType
def return_config(tc_client_id, tc_access_token, concurrency=1):

    # here doc with the config, we need string interpolation
    config = """
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
  command: echo "taskcluster generic-worker"
  # Test discovery mode is static
  mode: static
  # Test type is raw (custom test implementation)
  type: raw

env:
  TASKCLUSTER_CLIENT_ID: {tc_client_id}
  TASKCLUSTER_ACCESS_TOKEN: {tc_access_token}

# Command to run the tests using the testRunnerCommand
testRunnerCommand: python3 /home/ltuser/taskcluster/run_gw.py

# Only report the status of the test framework
frameworkStatusOnly: true

# Enable dynamic allocation of resources
dynamicAllocation: true

# Pre-install required dependencies using pip
pre:
  - pip3 install mozdevice
  - bash ./user_script/setup-script.sh

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
#    devices: ["pixel 5","pixel 5"]
#    devices: ["Galaxy A51-11"]
    devices: ["Galaxy A55 5G-14"]
    # Enable or disable video recording support
    video: true
    # Enable or disable device log support
    deviceLogs: true
    # App ID to be installed (mandatory field, using <app_id>)
    appId: lt://APP10160501071738874437060712
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
