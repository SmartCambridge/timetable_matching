#!/bin/bash

# Retrieve the bus timetables from the Traveline National Dataset (TNDS)
# for the regions listed in TNDS_REGIONS (default 'EA' and 'SE') using
# credentials from TNDS_USERNAME and TNDS_PASSWORD.
#
# Unzip the results and store them in directories named after the regions
# within TIMETABLE_PATH (default /media/tfc/tnds/sections/).
#
# Do the download at most once every 18 hours (1080 min)

set -e

source setup_environment

base='ftp://ftp.tnds.basemap.co.uk/'
if [[ "${TNDS_USERNAME}" = "" || "${TNDS_PASSWORD}" = "" ]]; then
    echo 'Please set TNDS_USERNAME and/or TNDS_PASSWORD in setup_environment' >&2
    exit 1
fi

path="${TIMETABLE_PATH:-/media/tfc/tnds/sections/}"
if  ! cd "${path}"; then
    echo "Can't cd to ${path} to store the timetable" >&2
    exit
fi

# Update no more than once every 18 hours
if [[ -e .last_update ]]; then
    if ! test "$(find .last_update -mmin +1080)"; then
        echo 'Timetable files updated recently - not doing so again' >&2
        exit
    fi
fi

echo 'Updating timetable files' >&2

zipdir=$(mktemp -d zip.XXXX)
sectiondir=$(mktemp -d sections.XXXX)

for section in ${TNDS_REGIONS:-EA SE}
    do
        echo "Doing section ${section}" >&2
        curl  --user "${TNDS_USERNAME}:${TNDS_PASSWORD}" --output "${zipdir}/${section}.zip" "${base}${section}.zip"
        mkdir -p "${sectiondir}/${section}"
        unzip -d "${sectiondir}/${section}" "${zipdir}/${section}.zip"
    done

rm -r "${zipdir}"

rm -rf sections
mv "${sectiondir}" ./sections

touch .last_update

echo 'Timetable files updated' >&2
