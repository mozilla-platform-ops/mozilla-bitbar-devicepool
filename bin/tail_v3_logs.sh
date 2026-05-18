#!/usr/bin/env bash

set -e
# set -x

GREP_COLOR_RED='1;31'
GREP_COLOR_GREEN='1;32'
GREP_COLOR_YELLOW='1;33'
GREP_COLOR_BLUE='1;34'
GREP_COLOR_PURPLE='1;35'
GREP_COLOR_CYAN='1;36'
# not the most usable...
GREP_COLOR_BLACK='1;30'
GREP_COLOR_WHITE='1;37'

LINES_TO_SHOW=2000
GREP_OPTIONS='--line-buffered'

# Check if local log file exists, use it instead of journalctl
if [ -f "local_bitbar_devicepool.log" ]; then
    echo "Using local log file: local_bitbar_devicepool.log"
    LOG_SOURCE="tail -f -n ${LINES_TO_SHOW} local_bitbar_devicepool.log"
else
    echo "Using journalctl for bitbar-v3 service logs"
    LOG_SOURCE="journalctl -u bitbar-v3 -f -n ${LINES_TO_SHOW}"
fi

${LOG_SOURCE} | \
        grep --line-buffered -v DEBUG | \
        GREP_COLOR=$GREP_COLOR_RED grep ${GREP_OPTIONS} --color=always -E '.*WARNING.*|^' | \
        GREP_COLOR=$GREP_COLOR_YELLOW grep ${GREP_OPTIONS} --color=always -E '.*Main.*|^' | \
        GREP_COLOR=$GREP_COLOR_CYAN grep ${GREP_OPTIONS} --color=always -E '.*getting active runs.*|^' | \
        GREP_COLOR=$GREP_COLOR_GREEN grep ${GREP_OPTIONS} --color=always -E '.*started.*|^' | \
        GREP_COLOR=$GREP_COLOR_BLUE grep ${GREP_OPTIONS} --color=always -E '.*Bitbar API.*|^' | \
        GREP_COLOR=$GREP_COLOR_PURPLE grep ${GREP_OPTIONS} --color=always -E '.*TC API.*|^'
