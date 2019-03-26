#!/usr/bin/env python3

"""
Extract NAPTAN stop details from merged trips/journeys

Read a list of merged trip/journey records for a given day. Output
NAPTAN stop details for all stops mentioned.
"""

import argparse
import datetime
import json
import logging
import sys

from haversine import haversine

from util import (
    API_SCHEMA, get_client, lookup
)

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)
logger = logging.getLogger('__name__')


def load_tracks(day):

    filename = 'tracks-{:%Y-%m-%d}.json'.format(day)
    logger.info('Reading %s', filename)

    with open(filename, 'r', newline='') as jsonfile:
        tracks = json.load(jsonfile)

    logger.info('Done')

    return tracks


# {
#     "bounding_box": "0.007896,52.155610,0.225048,52.267842",
#     "day": "2019-03-20",
#     "tracks": [
#         {
#             "bbox": [
#                 "0.0827980",
#                 "52.2041054",
#                 "0.1594470",
#                 "52.2311440"
#             ],
#             "destinations": [
#                 "0500CCITY144",
#                 "0500CCITY494"
#             ],
#             "lines": [
#                 "PR1"
#             ],
#             "origins": [
#                 "0500CCITY144",
#                 "0500CCITY494"
#             ],
#             "positions": [
#                 {
#                     "Bearing": "0",
#                     "Delay": "PT0S",
#                     "Latitude": "52.2308846",
#                     "Longitude": "0.1594450",
#                     "RecordedAtTime": "2019-03-20T06:45:57+00:00"
#                 },
#                 <...>
#             ],
#             "trips": [
#                {
#                    "DestinationName": "Tesco",
#                    "DestinationRef": "0500SBARH011",
#                    "DirectionRef": "INBOUND",
#                    "LineRef": "8",
#                    "OperatorRef": "WP",
#                    "OriginAimedDepartureTime": "2019-03-20T07:12:00+00:00",
#                    "OriginName": "Scotts Crescent",
#                    "OriginRef": "0500HHILT004",
#                    "VehicleRef": "WP-325"
#                },
#                <...>
#             ],
#             "vehicle": "WP-325"
#         },
#     ]
# }

def extract_trips(tracks, from_stop, to_stop, line):
    '''
    Extract all trips from start stop to end stop
    '''

    origin = (float(from_stop['latitude']), float(from_stop['longitude']))
    destination = (float(to_stop['latitude']), float(to_stop['longitude']))

    trips = []

    threshold = 50

    for track in tracks['tracks']:
q
        if (line and line not in track['lines']):
            logger.debug("Skipping %s - doesn't service line %s", track['vehicle'], line)
            continue

        logger.debug('Processing %s', track['vehicle'])

        state = 'before'
        positions = []

        for row, position in enumerate(track['positions']):

            logger.debug('      timestamp %s', position['RecordedAtTime'])

            here = (float(position['Latitude']), float(position['Longitude']))

            origin_distance = haversine(here, origin) * 1000  # in meters

            # logger.debug('Origin distance %s', origin_distance)

            # Arrive at start
            if state == 'before' and origin_distance < threshold:
                state = 'at_start'
                logger.debug('State transition before --> at_start')

            # Leave start
            elif state == 'at_start' and origin_distance > threshold:
                positions.append(track['positions'][row - 1])
                state = 'travelling'
                logger.debug('State transition at_start --> travelling')

            # Between start and destination
            if state == 'travelling':
                positions.append(position)

            destination_distance = haversine(here, destination) * 1000  # in meters

            # logger.debug('Destination distance %s', destination_distance)

            # Arrive destination
            if state == 'travelling' and destination_distance < threshold:
                trips.append({'VehicleRef': track['vehicle'], 'positions': positions})
                state = 'before'
                logger.debug('State transition travelling --> before')
                logger.debug("Trip length %s", len(positions))
                positions = []

    logger.debug("Found %s trips", len(trips))

    # Sort trips by start time
    trips.sort(key=lambda trip: trip['positions'][0]['RecordedAtTime'])

    return trips


def emit_trips(day, bbox, from_stop, to_stop, line, trips):
    '''
    Print trip details in json to 'trips-<YYYY>-<mm>-<dd>.json'
    '''

    filename = 'trips-from-tracks-{:%Y-%m-%d}.json'.format(day)
    logger.info('Outputing to %s', filename)

    with open(filename, 'w', newline='') as jsonfile:
        output = {
            'day': day.strftime("%Y-%m-%d"),
            'bounding_box': bbox,
            'from_stop': from_stop,
            'to_stop': to_stop,
            'line': line,
            'trips': trips
        }
        json.dump(output, jsonfile, indent=4, sort_keys=True)

        logger.info('Output done')


def parse_command_line():

    parser = argparse.ArgumentParser(description='Extract trips from tracks information.')

    parser.add_argument(
        '--from',
        dest='from_',
        required=True,
        help='extract stops from this stop')
    parser.add_argument(
        '--to',
        required=True,
        help='extract stops to this stop')
    parser.add_argument(
        '--line',
        help='restrict to tracks from vehicles servicing a particular line')
    parser.add_argument(
        'date',
        help='date to process')

    return parser.parse_args()


def main():

    logger.info('Start')

    args = parse_command_line()

    try:
        day = datetime.datetime.strptime(args.date, '%Y-%m-%d').date()
    except ValueError:
        logger.error('Failed to parse date')
        sys.exit()

    # Setup a coreapi client
    client = get_client()
    schema = client.get(API_SCHEMA)

    from_stop = lookup(client, schema, args.from_, {}, {})
    to_stop = lookup(client, schema, args.to, {}, {})

    tracks = load_tracks(day)

    trips = extract_trips(tracks, from_stop, to_stop, args.line)

    emit_trips(day, tracks['bounding_box'], from_stop, to_stop, args.line, trips)

    logger.info('Stop')


if __name__ == "__main__":
    main()
