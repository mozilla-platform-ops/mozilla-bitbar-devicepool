#!/usr/bin/env bash

set -e
# set -x


# functions
function usage() {
    echo "Usage: $0 [--change]"
    echo "Checks the latest TC version and compares it with the configured version in the setup script."
    echo "If --change is passed, it updates the version in the setup script."
}
function error() {
    echo "ERROR: $1"
    exit 1
}
function info() {
    echo "INFO: $1"
}
function success() {
    echo "SUCCESS: $1"
}
function alert() {
    echo "ALERT: $1"
}

function get_latest_tc_version() {
    # This function fetches the latest TC version from the specified URL.
    # It uses curl to get the content and grep to extract the version number.
    # The version number is then returned.
    command="curl -L -s https://api.github.com/repos/taskcluster/taskcluster/releases/latest | jq -r '.tag_name' | sed 's/^v//'"
    eval "$command"
}

# setup

# if --help passed, show help
if [[ "$1" == "--help" ]]; then
    usage
    exit 0
fi


root_path=$(cd "$(dirname "$0")/.." && pwd)
setup_script="$root_path/mozilla_bitbar_devicepool/lambdatest/user_script/setup_script.sh"
if [[ ! -f "$setup_script" ]]; then
    error "Setup script not found at $setup_script"
fi

# if we're on os x use gnu sed
if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v gsed &> /dev/null; then
        error "gsed could not be found, please install it with brew install gnu-sed"
    fi
    sed_cmd="gsed"
else
    sed_cmd="sed"
fi


# main


latest_tc_version=$(get_latest_tc_version)
if [[ $? -ne 0 ]]; then
    error "Failed to fetch the latest TC version."
fi
echo "latest tc version: "
echo "  $latest_tc_version"


rg_output=$(rg "^TC_VERSION" "$setup_script")
configured_tc_version=$(echo "$rg_output" | cut -d'=' -f2 | tr -d '[:space:]')
if [[ -z "$configured_tc_version" ]]; then
    error "Unable to find TC_VERSION in setup script."
fi
echo "configured version in lt setup: "
echo "  $configured_tc_version"

# if versions are the same, exit
if [[ "$latest_tc_version" == "$configured_tc_version" ]]; then
    info "Versions are the same, no action needed."
    exit 0
fi

# if --change is passed, change the version in the setup file
# else mention that the latest version is greater than the configured version
if [[ "$1" == "--change" ]]; then
    info "Changing version in setup file..."
    $sed_cmd -i "s/^TC_VERSION=.*/TC_VERSION=$latest_tc_version/" "$setup_script"
    success "SUCCESS: Version changed to: $latest_tc_version"
else
    alert "Latest version is greater than configured version!"
    echo "  Rerun this script with '--change' to update the version."
fi

# TODO: generate a link to the changelog deeplinking to the current version
# https://github.com/taskcluster/taskcluster/blob/main/CHANGELOG.md#v83101
