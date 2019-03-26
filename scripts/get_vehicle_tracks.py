#!/usr/bin/env python3

'''
Retrieve vehicle track information

Given a date, process SIRI-VM data in JSON for that day and spit out the
collected position reports for each vehicle based on VehicleRef, where
at least one of the origin or destination stops for the corresponding
journey is in a list of stops defined by a bounding box. Output the
resulting data in json.

Input file format:

"request_data": [
    {
        "Bearing": "300",
        "DataFrameRef": "1",
        "DatedVehicleJourneyRef": "119",
        "Delay": "-PT33S",
        "DestinationName": "Emmanuel St Stop E1",
        "DestinationRef": "0500CCITY487",
        "DirectionRef": "OUTBOUND",
        "InPanic": "0",
        "Latitude": "52.2051239",
        "LineRef": "7",
        "Longitude": "0.1242290",
        "Monitored": "true",
        "OperatorRef": "SCCM",
        "OriginAimedDepartureTime": "2017-10-25T23:14:00+01:00",
        "OriginName": "Park Road",
        "OriginRef": "0500SSAWS023",
        "PublishedLineName": "7",
        "RecordedAtTime": "2017-10-25T23:59:48+01:00",
        "ValidUntilTime": "2017-10-25T23:59:48+01:00",
        "VehicleMonitoringRef": "SCCM-19597",
        "VehicleRef": "SCCM-19597",
        "acp_id": "SCCM-19597",
        "acp_lat": 52.2051239,
        "acp_lng": 0.124229,
        "acp_ts": 1508972388
    },
    ...
]
'''

import datetime
import glob
import json
import logging
import os
import sys

from util import (
    API_SCHEMA, BOUNDING_BOX, LOAD_PATH, get_client, get_stops,
    update_bbox
)

logger = logging.getLogger('__name__')

other_stops = {}


def get_tracks(client, schema, date, interesting_stops):
    '''
    Extract vehicle tracks for a day

    Return a list of all vehicle tracks on the day
    indicated by year/month/day for journeys that have origin or destination stops in
    our stops list (and so fall within our bounding box)

    '''

    tracks = {}

    path = os.path.join(
        LOAD_PATH, date.strftime('%Y'), date.strftime('%m'),
        date.strftime('%d'), '*.json')
    logger.info('Processing from %s', path)

    for filename in glob.iglob(path):

        logger.debug("Processing %s", filename)

        with open(filename) as data_file:
            data = json.load(data_file)

        for record in data["request_data"]:

            # Skip if neither origin nor destination in our list of stops
            if (record['OriginRef'] not in interesting_stops and
               record['DestinationRef'] not in interesting_stops):
                continue

            vehicle = record['VehicleRef']

            if vehicle not in tracks:

                tracks[vehicle] = {}
                tracks[vehicle]['vehicle'] = vehicle
                tracks[vehicle]['positions'] = []
                tracks[vehicle]['bbox'] = [None, None, None, None]
                tracks[vehicle]['trips'] = []
                tracks[vehicle]['lines'] = set()
                tracks[vehicle]['origins'] = set()
                tracks[vehicle]['destinations'] = set()

            # Collect all the data that's common for one trip
            TRIP_FIELDS = (
                'DestinationName', 'DestinationRef', 'DirectionRef', 'LineRef',
                'OperatorRef', 'OriginAimedDepartureTime', 'OriginName',
                'OriginRef', 'VehicleRef'
            )

            trip = {field: record[field] for field in TRIP_FIELDS}
            if trip not in tracks[vehicle]['trips']:
                tracks[vehicle]['trips'].append(trip)
            trip_pos = tracks[vehicle]['trips'].index(trip)

            # ... and the data that makes up a position report
            POSITION_FIELDS = (
                'Bearing', 'Delay', 'Latitude', 'Longitude', 'RecordedAtTime'
            )

            position = {field: record[field] for field in POSITION_FIELDS}
            position['trip'] = trip_pos
            tracks[vehicle]['positions'].append(position)

            tracks[vehicle]['lines'].add(record['LineRef'])
            tracks[vehicle]['origins'].add(record['OriginRef'])
            tracks[vehicle]['destinations'].add(record['DestinationRef'])

            update_bbox(tracks[vehicle]['bbox'],
                        record['Longitude'],
                        record['Latitude'])

    logger.info("Found %s tracks", len(tracks))

    # Sort position records by time, and line, origin and destination as text
    # (but not trips, because we use their index for the 'trip' key in 'position')
    result = []
    for track in tracks.values():
        track['positions'].sort(key=lambda pos: pos['RecordedAtTime'])
        track['lines'] = sorted(track['lines'])
        track['origins'] = sorted(track['origins'])
        track['destinations'] = sorted(track['destinations'])
        result.append(track)

    return result


def emit_tracks(day, tracks):
    '''
    Print trip details in json to 'trips-<YYYY>-<mm>-<dd>.json'
    '''

    filename = 'tracks-{:%Y-%m-%d}.json'.format(day)
    logger.info('Outputing to %s', filename)

    with open(filename, 'w', newline='') as jsonfile:
        output = {
            'day': day.strftime("%Y-%m-%d"),
            'bounding_box': BOUNDING_BOX,
            'tracks': tracks
        }
        json.dump(output, jsonfile, indent=4, sort_keys=True)

        logger.info('Output done')


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

    # Collect tracks
    tracks = get_tracks(client, schema, day, interesting_stops)

    emit_tracks(day, tracks)

    logger.info('Stop')


if __name__ == "__main__":
    main()
