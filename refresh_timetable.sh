#!/bin/bash

# Retrieve the bus timetables from the Traveline National Dataset (TNDS)
# for the regions listed in TNDS_REGIONS (default 'EA' and 'SE') using
# credentials from TNDS_USERNAME and TNDS_PASSWORD.
#
# Unzip the results and store them in directories named after the regions
# within TIMETABLE_PATH (default /media/tfc/tnds/sections/).
#
# Only do anything at most once every few hours (120 min), and even then
# only download files if their modification date has changed.

set -e

source setup_environment


process_section() {
    # Do a 'get if modified' on a section file and unzip it if its change

    section=$1
    echo "Doing section ${section}" >&2

    filename="${section}.zip"

    # Try getting it
    size=$(curl --user "${TNDS_USERNAME}:${TNDS_PASSWORD}" \
         --output "${filename}" \
         --remote-time \
         --time-cond "${filename}" \
         --write-out '%{size_download}' \
         "${base}${filename}")

    # Unzip it if it actually changed (or it was new)
    if [[ ${size} -ne 0 ]]; then
        echo "Section ${section} new or changed - unzipping"
        tmp=$(mktemp -d XXXXXX)
        unzip -q -d "${tmp}" "${filename}"
        # Move it into place with two 'mv's to be a fast as possible
        if [[ -e "${section}" ]]; then
            mv "${section}" "${section}.old"
        fi
        mv "${tmp}" "${section}"
        rm -rf "${section}.old"
    else
        echo "Section ${section} unchanged"
    fi

}

base='ftp://ftp.tnds.basemap.co.uk/'

if [[ "${TNDS_USERNAME}" = "" || "${TNDS_PASSWORD}" = "" ]]; then
    echo 'Please set TNDS_USERNAME and/or TNDS_PASSWORD in setup_environment' >&2
    exit 1
fi

path="${TIMETABLE_PATH:-/media/tfc/tnds/sections/}"
if  ! cd "${path}"; then
    echo "Can't cd to ${path} to store the timetables" >&2
    exit
fi

# Do all of this no more than once every few hours
if [[ -e .last_update ]]; then
    if ! test "$(find .last_update -mmin +120)"; then
        echo 'Timetable files updated recently - not doing so again' >&2
        exit
    fi
fi

echo 'Updating timetable files' >&2

for section in ${TNDS_REGIONS:-EA SE}; do
    process_section "${section}"
done

touch .last_update

echo 'Timetable files up to date' >&2
