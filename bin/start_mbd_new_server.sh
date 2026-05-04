#!/usr/bin/env bash

set -e
set -x

# dev path
# . ./bitbar_env-v3-server.sh
# prod path
. /etc/bitbar/bitbar-v3.env

cd /home/bitbar/mozilla-bitbar-devicepool
/home/bitbar/.local/bin/poetry run mbd start-test-run-manager -b config/config-v3-server.yml --update-bitbar
