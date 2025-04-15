#!/usr/bin/env bash

set -e
set -x

# Get the directory where the script is located
SCRIPT_DIR=$(dirname "$(realpath "$0")")

# Get the parent directory of the script directory
PARENT_DIR=$(dirname "$SCRIPT_DIR")

# TODO: if we're not on master, run against master and the current branch

poetry run ${PARENT_DIR}/bin/device_group_report
