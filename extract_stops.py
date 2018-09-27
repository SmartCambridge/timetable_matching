#!/usr/bin/env python3

"""
Extract NAPTAN stop details from merged trips/journeys

Read a list of merged trip/journey records for a given day. Output
NAPTAN stop details for all stops mentioned.
"""

import datetime
import json
import logging
import sys

from util import (
    API_SCHEMA, BOUNDING_BOX, get_client, get_stops, lookup
)

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger('__name__')


def load_merged(day):

    filename = 'merged-{:%Y-%m-%d}.json'.format(day)
    logger.info('Reading %s', filename)

    with open(filename, 'r', newline='') as jsonfile:
        merged = json.load(jsonfile)

    logger.info('Done')

    return merged


def lookup_stops(client, schema, matches, interesting_stops):
    '''
    Lookup the NapTAN data for every stop mentioned in the merged data
    '''

    logger.info('Looking up stops')

    stop_ids = set()

    for match in matches:

        for trip in match['trips']:
            stop_ids.add(trip['OriginRef'])
            stop_ids.add(trip['DestinationRef'])

        for journey in match['journeys']:
            for stop in journey['stops']:
                stop_ids.add(stop['StopPointRef'])

    logger.info('Found %s stops in merged data', len(stop_ids))

    other_stops = {}
    results = {}
    for stop in stop_ids:
        results[stop] = lookup(client, schema, stop, interesting_stops, other_stops)

    logger.info('Looked up %s stops, needed %s extra', len(results), len(other_stops))

    return results


def emit_stops(day, bounding_box, stops):
    '''
    Print stop details in json to 'stops-<YYYY>-<mm>-<dd>.json'
    '''

    json_filename = 'stops-{:%Y-%m-%d}.json'.format(day)
    logger.info('Outputing JSON to %s', json_filename)

    with open(json_filename, 'w', newline='') as jsonfile:
        output = {
            'day': day.strftime('%Y-%m-%d'),
            'bounding_box': bounding_box,
            'stops': stops
        }
        json.dump(output, jsonfile, indent=4, sort_keys=True)

    logger.info('Json output done')


def main():

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

    matched_data = load_merged(day)

    stops = lookup_stops(client, schema, matched_data['merged'], interesting_stops)

    emit_stops(day, matched_data['bounding_box'], stops)

    logger.info('Stop')


if __name__ == "__main__":
    main()
