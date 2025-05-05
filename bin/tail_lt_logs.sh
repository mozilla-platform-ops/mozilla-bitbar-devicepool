#!/usr/bin/env bash

set -e
set -x

# more restricted
#journalctl -u lambdatest -f -n 20000 | grep -E 'Launched|TC Jobs' | grep 'a55-perf' | GREP_COLOR='1;32' grep --color=always -E '.*Launched.*|^'

# wider, more color
#journalctl -u lambdatest -f -n 20000 | grep 'a55-perf' | GREP_COLOR='1;32' grep --color=always -E '.*Launched.*|^' | GREP_COLOR='1;33' grep --color=always -E '.*Monitor.*|^'

# even wider
LINES_TO_SHOW=1000
#journalctl -u lambdatest -f -n "${LINES_TO_SHOW}" | grep 'a55-perf' | \
#journalctl -u lambdatest -f -n "${LINES_TO_SHOW}" | grep -E 'Monitor|a55-perf' | \
#journalctl -u lambdatest -f -n "${LINES_TO_SHOW}" | \
        #GREP_COLOR='1;36' grep --color=always -E '.* TC Jobs.*|^' | \
journalctl -u lambdatest -f -n "${LINES_TO_SHOW}" | \
        grep --line-buffered -v DEBUG | \
        GREP_COLOR='1;32' grep --line-buffered --color=always -E '.*Launched.*|^' | \
        GREP_COLOR='1;35' grep --line-buffered --color=always -E '.*LT Monitor.*|^' | \
        GREP_COLOR='1;34' grep --line-buffered --color=always -E '.*TC Monitor.*|^' | \
        GREP_COLOR='1;31' grep --line-buffered --color=always -E '.*WARNING.*|^'
