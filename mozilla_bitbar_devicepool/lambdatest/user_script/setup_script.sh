#!/bin/bash

set -e
set -x

starting_dir=$(pwd)
echo "starting_dir: $starting_dir"

sudo apt update -y
sudo apt-get install gettext-base libgtk-3-0 mercurial usbutils -y

pip install zstandard

### for perftest jobs
# AJE: mercurial installed above

echo "[extensions]" > ~/.hgrc
echo "sparse =" >> ~/.hgrc

# profgen
# TODO: get this from a real location
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
POWER_METER_DEVICE_ID="0483:fffe"

# AJE: usbutils intalled above
# list everything (ignore exit code)
usbreset || true

# list everthing (and capture output)
usbreset 2>&1 | tee /tmp/usbreset.log
# if the power meter is present issue reset commands
if grep -q "$POWER_METER_DEVICE_ID" /tmp/usbreset.log; then
    echo "Found power meter, resetting..."
    # reset the power meter
    usbreset $POWER_METER_DEVICE_ID
    sleep 2
    usbreset $POWER_METER_DEVICE_ID
else
    echo "Power meter not found, skipping reset."
fi

# aje 3/17/25: not needed per LT.
#   - was interfering with their monitoring and made the main testRunCommand not work.
#
# install adb
# sudo rm -f /usr/bin/adb
# sudo rm -f /home/ltuser/adb-original/adb
# sudo rm -rf /usr/lib/android-sdk/platform-tools
# sudo mkdir -p /usr/local/android-sdk
# # if /usr/local/android-sdk/ doesn't exist, we need to install it
# if [ ! -d "/usr/local/android-sdk" ]; then
#     cd /usr/local/android-sdk/
#     sudo curl -OL https://dl.google.com/android/repository/platform-tools-latest-linux.zip
#     sudo unzip platform-tools-latest-linux.zip
#     sudo rm -f platform-tools-latest-linux.zip
#     sudo ln -s /usr/local/android-sdk/platform-tools/adb /usr/bin/adb
#     sudo cp -r /usr/local/android-sdk/platform-tools /usr/lib/android-sdk/
# fi

rm -Rf taskcluster/

# setup taskcluster client in home/ltuser:
# assume taskcluster/* was copied over
# TODO: either clone repo, or build package for single download;  a lot of this is added via dockerfile
cd /home/ltuser/
# TODO?: this can already exist, `-p` for now, but how to manage this?
mkdir -p taskcluster
cd taskcluster
TC_VERSION=83.3.0
wget -O generic-worker https://github.com/taskcluster/taskcluster/releases/download/v${TC_VERSION}/generic-worker-insecure-linux-amd64
wget -O livelog https://github.com/taskcluster/taskcluster/releases/download/v${TC_VERSION}/livelog-linux-amd64
wget -O taskcluster-proxy https://github.com/taskcluster/taskcluster/releases/download/v${TC_VERSION}/taskcluster-proxy-linux-amd64
wget -O start-worker https://github.com/taskcluster/taskcluster/releases/download/v${TC_VERSION}/start-worker-linux-amd64





# mozilla-bitbar-docker bits




#
# jmaher sed method
#

# # mozilla_platform_ops_git_commit=master
# mozilla_platform_ops_git_commit=b13c723154cebebc48e71566eede9b5129b675ea # right before jdk 17 upgrade
# # https://raw.githubusercontent.com/mozilla-platform-ops/mozilla-bitbar-docker/b13c723154cebebc48e71566eede9b5129b675ea/taskcluster/worker-runner-config.yml.template
# wget https://raw.githubusercontent.com/mozilla-platform-ops/mozilla-bitbar-docker/${mozilla_platform_ops_git_commit}/taskcluster/worker-runner-config.yml.template
# wget https://raw.githubusercontent.com/mozilla-platform-ops/mozilla-bitbar-docker/${mozilla_platform_ops_git_commit}/scripts/entrypoint.sh
# wget https://raw.githubusercontent.com/mozilla-platform-ops/mozilla-bitbar-docker/${mozilla_platform_ops_git_commit}/scripts/entrypoint.py
# wget https://raw.githubusercontent.com/mozilla-platform-ops/mozilla-bitbar-docker/${mozilla_platform_ops_git_commit}/scripts/run_gw.py
# wget https://raw.githubusercontent.com/mozilla-platform-ops/mozilla-bitbar-docker/${mozilla_platform_ops_git_commit}/taskcluster/script.py

# # edit paths in entrypoint.*, run_gw.py, and maybe others /builds/taskcluster & /usr/local/bin -> /home/ltuser/taskcluster
# sed -i 's/builds\/taskcluster/home\/ltuser\/taskcluster/g' entrypoint.sh
# sed -i 's/builds\/taskcluster/home\/ltuser\/taskcluster/g' entrypoint.py
# sed -i 's/builds\/taskcluster/home\/ltuser\/taskcluster/g' run_gw.py
# sed -i 's/builds\/taskcluster/home\/ltuser\/taskcluster/g' worker-runner-config.yml.template
# sed -i 's/usr\/local\/bin/home\/ltuser\/taskcluster/g' worker-runner-config.yml.template
# sed -i 's/builds\/worker/home\/ltuser\/taskcluster/g' entrypoint.sh
# sed -i 's/chown/# chown/g' entrypoint.sh # avoid chown worker

# # hack to get android_serial to be added to the environment - important as we have usb+tcp listed with `adb devices`
# sed -i 's/"TC_WORKER_GROUP",/"TC_WORKER_GROUP","ANDROID_SERIAL","UserPorts",/g' entrypoint.py

# # hack on script.py - ideally fix this in the script.py itself
# sed -i 's/builds\/worker/home\/ltuser\/taskcluster/g' script.py
# sed -i 's/builds\/taskcluster/home\/ltuser\/taskcluster/g' script.py

# # ignore error about >1 device, we have adb + tcp_ip connections for our current device.
# sed -i s/sys.exit\(exit_code\)/#pass/g script.py

# # need to figure out how to set this - scripts depend on this file existing
# echo '80.0.0' > /home/ltuser/taskcluster/version

# # we want entrypoint.sh to setup everything in the "pre-step", but the scenario needs to run "run_gw.py"
# sed -i 's/run_gw.py/# run_gw.py/g' entrypoint.sh
# # aje: busted, getting `sed: -e expression #1, char 13: unterminated `s' command`
# # sed -i s/run_gw.py/# run_gw.py/g entrypoint.sh

# # adjust defaults for taskIdleTimeout and cleanuptasksdir
# #sed -i 's/5400/5/g' worker-runner-config.yml.template  # I assume we can use an exit code
# echo "disableReboots:   true" >> worker-runner-config.yml.template  # this ensures that the docker container can be managed on it's own




#
# inline files (snapshots of jmaher's files from above)
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

# # debugging: output all scripts so i can store their mods

# set +x

# echo "********"
# printenv
# echo "********"

# echo "********"
# cat entrypoint.sh
# echo "********"
# cat entrypoint.py
# echo "********"
# cat run_gw.py
# echo "********"
# cat script.py
# echo "********"
# cat worker-runner-config.yml.template
# echo "********"
# set -x

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


ss -np

cd taskcluster
bash entrypoint.sh

# TODO: now that test command is run_gw.py, we need to configure the worker to terminate after each task...
#       this ensures that it won't hang around forever and we can ensure the phone and hyperexecute are running together
