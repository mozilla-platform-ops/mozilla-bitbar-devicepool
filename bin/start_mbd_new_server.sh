#!/usr/bin/env bash

set -e
set -x

. ./bitbar_env-v3-server.sh
poetry run mbd start-test-run-manager -b config/config-v3-server.yml --update-bitbar
