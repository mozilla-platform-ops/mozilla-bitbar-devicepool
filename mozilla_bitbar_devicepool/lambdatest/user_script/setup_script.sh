#!/bin/bash

set -e
set -x

# variables

usbreset_log_file=/tmp/usbreset.log
usbreset_log_file2=/tmp/usbreset-pass2.log
POWER_METER_DEVICE_ID="0483:fffe"
TC_VERSION=83.5.6
POWER_METER_FAST_FAIL=0


# functions

# Function to get the currently focused window
getCurrentWindow() {
    adb shell dumpsys window | grep mFocusedWindow
}


### main

starting_dir=$(pwd)
echo "starting_dir: $starting_dir"

sudo apt update -y
sudo apt-get install gettext-base libgtk-3-0 mercurial usbutils -y

# google-cloud-logging is for stackdriver
pip install zstandard google-cloud-logging

### for perftest jobs
# AJE: mercurial installed above

echo "[extensions]" > ~/.hgrc
echo "sparse =" >> ~/.hgrc

# profgen
wget -O cmdlinetools.zip --no-check-certificate "https://android-packages.s3.us-west-2.amazonaws.com/commandlinetools-linux-13114758_latest.zip"
unzip cmdlinetools.zip

# this is in PATH, lets use it:
mkdir -p /home/ltuser/taskcluster/android-sdk-linux
mkdir -p /home/ltuser/taskcluster/android-sdk-linux/tools
mkdir -p /home/ltuser/taskcluster/android-sdk-linux/tools/bin
mkdir -p /home/ltuser/taskcluster/android-sdk-linux/tools/lib

sudo cp -R cmdline-tools/bin/* /home/ltuser/taskcluster/android-sdk-linux/tools/bin/
sudo cp -R cmdline-tools/lib/* /home/ltuser/taskcluster/android-sdk-linux/tools/lib/

### for power meter jobs

# AJE: usbutils intalled above
# list everything (ignore exit code)
# usbreset || true

# list everthing (and capture output)
# usbreset 2>&1 | tee $usbreset_log_file
# if the power meter is present issue reset commands
# if grep -q "$POWER_METER_DEVICE_ID" $usbreset_log_file; then
#     echo "Found power meter, resetting..."
#     # reset the power meter
#     usbreset $POWER_METER_DEVICE_ID
#     sleep 2
#     usbreset $POWER_METER_DEVICE_ID 2>&1 | tee $usbreset_log_file2
# else
#     echo "Power meter not found, skipping reset."
# fi

# if /tmp/usbreset-pass2.log contains `permission denied` then exit 1 with message
#
# example bad output:
#   Resetting Korona YK003C in Application Mode ... can't open [Permission denied]
#
# if POWER_METER_FAST_FAIL is set to 1, then fail if permission denied
if [ "$POWER_METER_FAST_FAIL" -eq 1 ]; then
    if grep -qi "permission denied" $usbreset_log_file2; then
        echo "Permission denied on power meter, please check permissions."
        # show the output of pass2.log
        cat $usbreset_log_file2
        exit 1
    fi
fi

rm -Rf taskcluster/

# setup taskcluster client in home/ltuser:
# assume taskcluster/* was copied over
# TODO: either clone repo, or build package for single download;  a lot of this is added via dockerfile
cd /home/ltuser/
# TODO?: this can already exist, `-p` for now, but how to manage this?
mkdir -p taskcluster
cd taskcluster
wget -O generic-worker https://github.com/taskcluster/taskcluster/releases/download/v${TC_VERSION}/generic-worker-insecure-linux-amd64
wget -O livelog https://github.com/taskcluster/taskcluster/releases/download/v${TC_VERSION}/livelog-linux-amd64
wget -O taskcluster-proxy https://github.com/taskcluster/taskcluster/releases/download/v${TC_VERSION}/taskcluster-proxy-linux-amd64
wget -O start-worker https://github.com/taskcluster/taskcluster/releases/download/v${TC_VERSION}/start-worker-linux-amd64


# copy inline files into place
#
# TODO: eventually move these to their own repo like mozilla-bitbar-docker?

ls -la
find .

script_dir=$(dirname $0)
echo "script_dir: $script_dir"

# TODO: figure out the path to use
cp $starting_dir/$script_dir/files/worker-runner-config.yml.template .
cp $starting_dir/$script_dir/files/entrypoint.sh .
cp $starting_dir/$script_dir/files/entrypoint.py .
cp $starting_dir/$script_dir/files/run_gw.py .
cp $starting_dir/$script_dir/files/script.py .

# fix up perms
chmod +x generic-worker
chmod +x livelog
chmod +x start-worker
chmod +x taskcluster-proxy
chmod +x entrypoint.sh
chmod +x entrypoint.py
chmod +x run_gw.py
chmod +x script.py

cd /home/ltuser

# robust checkout plugin: update sha1 to latest when building a new image
wget https://hg.mozilla.org/mozilla-central/raw-file/260e22f03e984e0ced16b6c5ff63201cdef0a1f6/testing/mozharness/external_tools/robustcheckout.py
wget https://raw.githubusercontent.com/mozilla-platform-ops/mozilla-bitbar-docker/refs/heads/master/scripts/tooltool.py
chmod +x robustcheckout.py
chmod +x tooltool.py

export PATH=/home/ltuser/taskcluster:$PATH

# TODO: figure out how to set these env vars securely
export TC_WORKER_GROUP=lambda

# DEBUG
/usr/bin/adb devices
/usr/bin/adb devices -l

# export DEVICE_NAME=${HOSTNAME} # TODO: no spaces- need to find a way to make this unique
export DEVICE_NAME=$(/usr/bin/adb devices -l | grep usb | grep -v 'List of devices attached' | sed '/^[[:space:]]*$/d' | cut -f 1 -d ' ')
# aje: TC_WORKER_TYPE is now set in the hyperexecute.yaml file
# export TC_WORKER_TYPE=gecko-t-lambda-alpha-a55

# hacks to prepare lambda environment (serial is super hacky right now):
export HOST_IP=$HostIP
export DEVICE_SERIAL=$DEVICE_NAME
export ANDROID_SERIAL=$DEVICE_NAME # mozdevice uses this if it exists, avoids issue with >1 device

# set the screen to never turn off
adb shell svc power stayon true
# detect if screen is off, wake if not
if [ -z "$(getCurrentWindow)" ] || [[ "$(getCurrentWindow)" == *"NotificationShade"* ]]; then
    echo "Screen is asleep or showing notification shade. Waking up..."
    # wake the screen by pressing MENU key
    adb shell input keyevent 82
else
    echo "Screen is awake."
fi

ss -np

cd taskcluster
bash entrypoint.sh

# TODO: now that test command is run_gw.py, we need to configure the worker to terminate after each task...
#       this ensures that it won't hang around forever and we can ensure the phone and hyperexecute are running together
