#!/usr/bin/env python3

"""
Retrieve trip information

Given a date and one or more *directories* containing SIRI-VM data in
Json, spit out all unique vehicle journeys (based on OriginRef,
DestinationRef, OriginAimedDepartureTime, LineRef, OperatorRef,
DirectionRef, and VehicleRef) where at least one of the origin or
destination in our list of stops. Output the data in json.

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
"""

import datetime
import glob
import json
import logging
import os
import sys

from util import (
    API_SCHEMA, BOUNDING_BOX, LOAD_PATH, get_client, get_stops, update_bbox
)

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger('__name__')


def get_trips(date, stops):
    '''
    Return a dictionary of all trips (realtime journeys) on the day
    indicated by year/month/day that have origin or destination stops in
    our stops list (and so fall within our bounding box)
    '''

    trips = {}

    path = os.path.join(LOAD_PATH, date.strftime('%Y/%m/%d'), '*.json')
    logger.info('Processing from %s', path)

    for filename in glob.iglob(path):

        logger.debug("Processing %s", filename)

        with open(filename) as data_file:
            data = json.load(data_file)

        for record in data["request_data"]:

            # Form a unique key for this data
            key = (
                record['OriginRef'],
                record['DestinationRef'],
                record['OriginAimedDepartureTime'],
                record['LineRef'],
                record['OperatorRef'],
                record['DirectionRef'],
                record['VehicleRef'],
            )

            if key not in trips:
                trips[key] = record
                trips[key]['positions'] = []
                trips[key]['bbox'] = [None, None, None, None]

            trips[key]['positions'].append((record['acp_lng'],
                                            record['acp_lat'],
                                            record['acp_ts']
                                            ))
            update_bbox(trips[key]['bbox'],
                        record['acp_lng'],
                        record['acp_lat'])

    logger.info("Found %s raw trips journeys", len(trips))

    # List journeys that either start or end at stops we are interested in
    trip_list = [t for t in trips.values()
                 if t['OriginRef'] in stops or t['DestinationRef'] in stops]

    logger.info("Found %s interesting trips", len(trip_list))

    # Sort the position records by time
    for trip in trip_list:
        trip['positions'].sort(key=lambda pos: pos[2])

    return trip_list


def emit_trips(day, trips):
    '''
    Print trip details in json to 'trips-<YYYY>-<mm>-<dd>.json'
    '''

    filename = 'trips-{:%Y-%m-%d}.json'.format(day)
    logger.info('Outputing to %s', filename)

    with open(filename, 'w', newline='') as jsonfile:
        output = {
            'day': day.strftime("%Y/%m/%d"),
            'bounding_box': BOUNDING_BOX,
            'trips': trips
        }
        json.dump(output, jsonfile, indent=4, sort_keys=True)

        logger.info('Output done')


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
    stops = get_stops(client, schema, BOUNDING_BOX)

    # Collect realtime journeys
    trips = get_trips(day, stops)

    emit_trips(day, trips)

    logger.info('Stop')


if __name__ == "__main__":
    main()
