#!/usr/bin/env bash

set -e
set -x

./bin/configuration_device_tool -c lambdatest.yml "$@"
