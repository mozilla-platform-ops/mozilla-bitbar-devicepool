#!/bin/bash

. /etc/bitbar/lambdatest.env

cd /home/bitbar/mozilla-bitbar-devicepool
/home/bitbar/.local/bin/poetry run mld start-test-run-manager
