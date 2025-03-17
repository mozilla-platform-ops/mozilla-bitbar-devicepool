#!/usr/bin/env bash

set -e
set -x

pip3 install mozdevice
bash ./user_script/setup_script.sh
# cat /home/ltuser/taskcluster/worker-runner-config.yml
python3 /home/ltuser/taskcluster/run_gw.py
