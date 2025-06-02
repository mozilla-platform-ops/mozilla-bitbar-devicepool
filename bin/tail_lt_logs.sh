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

# heredoc with test input, store in variable, preserve newlines
# HEREDOC_INPUT=$(cat << EOM
read -r -d '' HEREDOC_INPUT <<EOF || true
INFO: Main process started \n
WARNING: Potential issue detected \n
INFO: Cleaner process started \n
INFO: Monitor process started \n
INFO: Launched new instance \n
INFO: LT API request made \n
INFO: TC API request made \n
DEBUG: Not shown! \n
INFO: Normal text is like this. \n
EOF

# if --test is passed in, use a heredoc as input and colorize it
command_to_run="journalctl -u lambdatest -f -n ${LINES_TO_SHOW}"
if [[ "$1" == "--test" ]]; then
    command_to_run="echo -e ${HEREDOC_INPUT}"
    # command_to_run="printf '%s\n' '${HEREDOC_INPUT}'"
    echo "Running in test mode. Using heredoc input."
fi

# echo $HEREDOC_INPUT
# exit

$command_to_run | \
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
