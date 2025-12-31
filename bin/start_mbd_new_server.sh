#!/usr/bin/env bash

set -e
set -x

mbd start-test-run-manager -b config/config-v3-server.yml --update-bitbar
