#!/usr/bin/env bash

set -e
# set -x

LINES_TO_SHOW=2000

# ANSI color codes
RED='\033[1;31m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
GREEN='\033[1;32m'
BLUE='\033[1;34m'
PURPLE='\033[1;35m'
RESET='\033[0m'

# hi vis color codes
HI_RED='\033[0;91m'
HI_YELLOW='\033[0;93m'
HI_CYAN='\033[0;96m'
HI_GREEN='\033[0;92m'
HI_BLUE='\033[0;94m'
HI_PURPLE='\033[0;95m'

journalctl -u lambdatest -f -n "${LINES_TO_SHOW}" | \
    grep --line-buffered -v DEBUG | \
    awk -v red="$RED" -v yellow="$YELLOW" -v cyan="$CYAN" -v green="$GREEN" -v blue="$BLUE" -v purple="$PURPLE" -v reset="$RESET" \
        -v hired="$HI_RED" -v hiyellow="$HI_YELLOW" -v hicyan="$HI_CYAN" -v higreen="$HI_GREEN" -v hiblue="$HI_BLUE" -v hipurple="$HI_PURPLE" '
    {
        line = $0
        if (line ~ /WARNING/) {
            print red line reset
        } else if (line ~ /Main/) {
            print hiyellow line reset
        } else if (line ~ /Cleaner/) {
            print hiblue line reset
        } else if (line ~ /Monitor/) {
            print cyan line reset
        } else if (line ~ /Launched/) {
            print green line reset
        } else if (line ~ /LT API/) {
            print blue line reset
        } else if (line ~ /TC API/) {
            print purple line reset
        } else {
            print line
        }
    }
'
