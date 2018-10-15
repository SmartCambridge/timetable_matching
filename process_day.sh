#!/bin/bash

# Process one or more day's bus journeys and trips ready to be analysed.

base="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

source venv/bin/activate
source setup_environment

# Get force flag

OPTIND=1
force=0
while getopts "f" opt; do
    case "$opt" in
    f)  force=1
        ;;
    esac
done
shift $((OPTIND-1))

if (( $# < 1 )); then
    echo "Usage process_day.sh [-f] yyyy-mm-dd [yyyy-mm-dd...]" >&2
    exit
fi

./refresh_timetable.sh

if ! cd "${SAVE_PATH}" ; then
    echo "Can't cd to ${SAVE_PATH} to store output" >&2
    exit
fi

for date in "$@"; do

    if [[ -e "rows-${date}.json" && "${force}" = "0" ]]; then
        echo "Data for ${date} already processed - use -f to overwrite" >&2
    else
        "${base}/scripts/do_everything.py" "${date}"
    fi

done

