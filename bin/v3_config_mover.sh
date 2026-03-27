#!/usr/bin/env bash

set -e
set -x

poetry run ./bin/configuration_device_tool -c config-v3-server.yml "$@"
