#!/bin/bash

. /etc/bitbar/lambdatest.env

cd /home/bitbar/mozilla-bitbar-devicepool

# debugging
# /home/bitbar/.local/bin/poetry run mld start-test-run-manager --log-level DEBUG

# normal
/home/bitbar/.local/bin/poetry run mld start-test-run-manager
