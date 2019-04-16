#!/usr/bin/env python3

"""
Extract from a collection of vehicle tracks all the track segments that
correspond to trips from a specified origin stop to a specified
destination stop (optionally only for vehicles that serviced a specified
line sometime during that day).

The output format resembles the output from get_trips.py, but lacks
most of the trip metadata.
"""

import argparse
import datetime
import isodate
import json
import logging
import sys

from haversine import haversine

from util import (
    API_SCHEMA, get_client, lookup
)

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
#                     "RecordedAtTime": "2019-03-20T06:45:57+00:00",
#                     "trip": 3
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


def extract_segments(tracks, from_stop, to_stop, line, origin_threshold, destination_threshold):
    '''
    Extract all trips from from_stop to to_stop (optionally for line)
    '''

    origin = (float(from_stop['latitude']), float(from_stop['longitude']))
    destination = (float(to_stop['latitude']), float(to_stop['longitude']))

    segments = []

    route_timeout = 500  # seconds

    for track in tracks['tracks']:

        if (line and line not in track['lines']):
            logger.debug("Skipping vehicle %s - doesn't service line %s", track['vehicle'], line)
            continue

        logger.debug('Processing %s', track['vehicle'])

        state = 'off_route'
        positions = []

        for row, position in enumerate(track['positions']):

            here = (float(position['Latitude']), float(position['Longitude']))

            origin_distance = haversine(here, origin) * 1000  # in meters

            # State transitions

            if state == 'off_route':
                if origin_distance < origin_threshold:
                    state = 'at_start'
                    logger.debug('State transition (%s): arrived at start (off_route --> at_start)', position['RecordedAtTime'])
                    positions.append(position)
                else:
                    positions.append(position)

            if state == 'at_start':
                if origin_distance > origin_threshold:
                    state = 'on_route'
                    logger.debug('State transition (%s): departed (at_start --> on_route)', position['RecordedAtTime'])
                    previous_position = positions.pop()
                    segments.append({
                        'VehicleRef': track['vehicle'],
                        'on_route': False,
                        'positions': positions})
                    positions = [previous_position, position]
                else:
                    positions.append(position)

            if state == 'on_route':
                destination_distance = haversine(here, destination) * 1000
                previous_timestamp = isodate.parse_datetime(positions[-1]['RecordedAtTime'])
                this_timestamp = isodate.parse_datetime(position['RecordedAtTime'])
                if origin_distance < origin_threshold:
                    state = 'at_start'
                    logger.debug('State transition (%s): returned to start (on_route --> at_start)', position['RecordedAtTime'])
                    positions.append(position)
                elif (this_timestamp - previous_timestamp).total_seconds() > route_timeout:
                    state = 'off_route'
                    logger.debug('State transition (%s): timed-out (on_route --> off_route)', position['RecordedAtTime'])
                elif destination_distance < destination_threshold:
                    state = 'off_route'
                    logger.debug('State transition (%s): arrived (on_route --> off_route)', position['RecordedAtTime'])
                    positions.append(position)
                    segments.append({
                        'VehicleRef': track['vehicle'],
                        'on_route': True,
                        'positions': positions})
                    logger.debug("On route segment length %s", len(positions))
                    positions = []
                else:
                    positions.append(position)

        if positions:
            segments.append({
                'VehicleRef': track['vehicle'],
                'on_route': False,
                'positions': positions})

    logger.info("Found %s segments", len(segments))

    # Sort trips by start time
    segments.sort(key=lambda segment: segment['positions'][0]['RecordedAtTime'])

    return segments


def emit_segments(day, bbox, from_stop, to_stop, line, origin_threshold, destination_threshold, segments):
    '''
    Print trip details in json to 'trips-<YYYY>-<mm>-<dd>.json'
    '''

    filename = 'segments-{}-{}-{:%Y-%m-%d}.json'.format(
        from_stop['atco_code'],
        to_stop['atco_code'],
        day)
    logger.info('Outputing to %s', filename)

    with open(filename, 'w', newline='') as jsonfile:
        output = {
            'day': day.strftime("%Y-%m-%d"),
            'bounding_box': bbox,
            'from_stop': from_stop,
            'to_stop': to_stop,
            'line': line,
            'origin_threshold': origin_threshold,
            'destination_threshold': destination_threshold,
            'segments': segments
        }
        json.dump(output, jsonfile, indent=4, sort_keys=True)

        logger.info('Output done')


def parse_command_line():

    parser = argparse.ArgumentParser(description='Extract trips from tracks information.')

    parser.add_argument(
        '--from',
        dest='from_',  # Can't use 'from' because it's a reserved word
        metavar='FROM',
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
        metavar="YYYY-MM-DD",
        help='date to process')

    return parser.parse_args()


def main():

    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)

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

    origin_threshold = 40  # meters
    destination_threshold = 40  # meters

    tracks = load_tracks(day)

    segments = extract_segments(
        tracks,
        from_stop,
        to_stop,
        args.line,
        origin_threshold,
        destination_threshold)

    emit_segments(day,
        tracks['bounding_box'],
        from_stop,
        to_stop,
        args.line,
        origin_threshold,
        destination_threshold,
        segments)

    logger.info('Stop')


if __name__ == "__main__":
    main()
