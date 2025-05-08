#!/usr/bin/env bash

set -e
set -x

# more restricted
#journalctl -u lambdatest -f -n 20000 | grep -E 'Launched|TC Jobs' | grep 'a55-perf' | GREP_COLOR='1;32' grep --color=always -E '.*Launched.*|^'

# wider, more color
#journalctl -u lambdatest -f -n 20000 | grep 'a55-perf' | GREP_COLOR='1;32' grep --color=always -E '.*Launched.*|^' | GREP_COLOR='1;33' grep --color=always -E '.*Monitor.*|^'

GREP_COLOR_RED='1;31'
GREP_COLOR_GREEN='1;32'
GREP_COLOR_YELLOW='1;33'
GREP_COLOR_BLUE='1;34'
GREP_COLOR_PURPLE='1;35'
GREP_COLOR_CYAN='1;36'
# not the most usable...
GREP_COLOR_BLACK='1;30'
GREP_COLOR_WHITE='1;37'

# even wider
LINES_TO_SHOW=2000
GREP_OPTIONS='--line-buffered'
#journalctl -u lambdatest -f -n "${LINES_TO_SHOW}" | grep 'a55-perf' | \
#journalctl -u lambdatest -f -n "${LINES_TO_SHOW}" | grep -E 'Monitor|a55-perf' | \
#journalctl -u lambdatest -f -n "${LINES_TO_SHOW}" | \
        #GREP_COLOR='1;36' grep --color=always -E '.* TC Jobs.*|^' | \
        #grep --line-buffered -E 'Monitor|a55-perf' | \
journalctl -u lambdatest -f -n "${LINES_TO_SHOW}" | \
        grep --line-buffered -v DEBUG | \
        GREP_COLOR=$GREP_COLOR_RED grep ${GREP_OPTIONS} --color=always -E '.*WARNING.*|^' | \
        GREP_COLOR=$GREP_COLOR_YELLOW grep ${GREP_OPTIONS} --color=always -E '.*Main.*|^' | \
        GREP_COLOR=$GREP_COLOR_GREEN grep ${GREP_OPTIONS} --color=always -E '.*Launched.*|^' | \
        GREP_COLOR=$GREP_COLOR_PURPLE grep ${GREP_OPTIONS} --color=always -E '.*LT Monitor.*|^' | \
        GREP_COLOR=$GREP_COLOR_BLUE grep ${GREP_OPTIONS} --color=always -E '.*TC Monitor.*|^'
