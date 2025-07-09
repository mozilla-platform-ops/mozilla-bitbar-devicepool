#!/bin/bash

set -e
# TODO: eventually disable -x
set -x


### variables

TC_VERSION=84.0.2
LT_SETUP_MERCURIAL_VERSION="7.0.2"
LT_SETUP_PYTHON_VERSION="3.12"


### functions

# Function to get the currently focused window
getCurrentWindow() {
    adb shell dumpsys window | grep mFocusedWindow
}

starting_dir=$(pwd)
echo "starting_dir: $starting_dir"


# show information about the user scripts
THIS_SCRIPT_DIR=$(dirname "$0")
if [ -f $THIS_SCRIPT_DIR/version.txt ]; then
    echo "user_scripts version:"
    cat $THIS_SCRIPT_DIR/version.txt
else
    echo "user_scripts version file not found."
fi


### general dependencies

# apt/debs
sudo apt-get update -y
sudo apt-get install gettext-base libgtk-3-0 usbutils -y

# python pips
#   - NOTE: pip is pip3 on the lt image
# upgrade mercurial
# google-cloud-logging is for stackdriver
sudo pip install zstandard \
                 mozdevice \
                 google-cloud-logging \
                 mercurial==$LT_SETUP_MERCURIAL_VERSION

# show mercurial version
hg --version

# test mercurial version
if ! hg --version | grep -q "$LT_SETUP_MERCURIAL_VERSION"; then
    echo "Mercurial version is not $LT_SETUP_MERCURIAL_VERSION, exiting."
    exit 1
fi

# upgrade `python` and `python3` to our desired version
LT_SETUP_PYTHON_FULL_STRING="python$LT_SETUP_PYTHON_VERSION"
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install "$LT_SETUP_PYTHON_FULL_STRING" "$LT_SETUP_PYTHON_FULL_STRING-venv" -y
# update alternatives to use the new python version
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 100
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 10
# python seems to be a symlink to python3, nothing required

# show version
python --version
python3 --version

# check that python3 is at the version we want
if ! python3 --version | grep -q "$LT_SETUP_PYTHON_VERSION"; then
    echo "Python 3 version is not $LT_SETUP_PYTHON_VERSION, exiting."
    exit 1
fi

# check that python is at the version we want
if ! python --version | grep -q "$LT_SETUP_PYTHON_VERSION"; then
    echo "Python version is not $LT_SETUP_PYTHON_VERSION, exiting."
    exit 1
fi


### perftest dependencies

# mercurial is installed above

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

# TODO: fast fail if power meter missing or device permissions are bad


### taskcluster setup

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

# debugging
# ls -la
# find .

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
# worker is configured to exit after one task.
