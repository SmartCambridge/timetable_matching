#!/bin/bash

# Process one or more day's bus journeys and trips ready to be analysed.

source venv/bin/activate
source setup_environment

process_days () {

    for date in "$@"; do

        if [[ -e "rows-${date}.json" && "${force}" = "0" ]]; then
            echo "Data for ${date} already processed - use -f to overwrite" >&2
        else
            "${base}/scripts/do_everything.py" "${date}"
        fi

    done

}

base="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

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

./refresh_timetable.sh

path="${SAVE_PATH:-/media/tfc/cam_tt_matching/json/}"
if ! cd "${path}" ; then
    echo "Can't cd to ${path} to store output" >&2
    exit
fi

if (( $# < 1 )); then
    process_days "$(date --date=yesterday +%F)"
else
    process_days "$@"
fi
