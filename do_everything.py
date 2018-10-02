#!/usr/bin/env python3

"""
Run the entire matching pipeline for the dat identified on the command
line and output matched data in JSON and CSV.

Note that the individual processing scripts can be run one at a time
using the corresponding stand-alone scripts.
"""

import datetime
import logging
import sys

from util import (
    BOUNDING_BOX, TNDS_REGIONS, API_SCHEMA, get_client, get_stops
)
from get_journeys import get_journeys
from get_trips import get_trips, derive_timings
from merge import do_merge, clasify_matches
from extract_stops import lookup_stops, emit_stops
from expand_merged import expand, emit_json
from create_csv import emit_csv


logger = logging.getLogger('__name__')


def main():

    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

    logger.info('Start')

    try:
        day = datetime.datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
    except ValueError:
        logger.error('Failed to parse date')
        sys.exit()

    # Setup a coreapi client
    client = get_client()
    schema = client.get(API_SCHEMA)

    # Get the list of all the stops we are interested in
    interesting_stops = get_stops(client, schema, BOUNDING_BOX)
    assert len(interesting_stops) > 0, 'Failed to get any stops'

    # Retrieve timetable journeys
    journeys = get_journeys(day, interesting_stops, TNDS_REGIONS)
    assert len(journeys) > 0, 'Failed to get any journeys'

    # Collect real-time journeys
    trips = get_trips(client, schema, day, interesting_stops)
    assert len(trips) > 0, 'Failed to get any trips'

    # Derive trip departure and arrival timings
    derive_timings(trips)

    # Merge journeys and trips
    merged = do_merge(trips, journeys)

    # Classify matched journeys
    clasify_matches(merged)

    # Lookup stops referenced in the merged data
    all_stops = lookup_stops(client, schema, merged, interesting_stops)

    # Expand merged data into one row per journey/trip match
    rows = expand(day, merged, all_stops)

    # And print the result
    emit_stops(day, BOUNDING_BOX, all_stops)
    emit_json(day, BOUNDING_BOX, rows)

    # and again, as CSV
    emit_csv(day, rows)

    logger.info('Stop')


if __name__ == "__main__":
    main()
