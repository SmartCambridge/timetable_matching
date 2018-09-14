#!/usr/bin/env python3

"""
Given one or more directories containing SIRI-VM data in Json, spit
out all unique vehicle journeys (based on OriginRef, DestinationRef,
OriginAimedDepartureTime, LineRef, OperatorRef, DirectionRef, and
VehicleRef) with start or end stops in our list of stops in CSV

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
"""

import csv
import json
import logging
import os
import sys

from util import (
    API_SCHEMA, BOUNDING_BOX, get_client, get_stops
)

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger('__name__')


def update_bbox(box, lng, lat):
    '''
    Update a bounding box represented as (min longitude, min latitude,
    max longitude, max latitude) with a new point
    '''
    if lng < box[0]:
        box[0] = lng
    if lat < box[1]:
        box[1] = lat
    if lng > box[2]:
        box[2] = lng
    if lat > box[3]:
        box[3] = lat


def get_trips(directories, stops):
    '''
    Return a dictionary of all trips (realtime journeys) on the day
    indicated by year/month/day that have origin or destination stops in
    our stops list (and so fall within our bounding box)
    '''

    trips = {}

    for directory in directories:
        logger.info('Processing from %s', directory)
        for file in os.listdir(os.fsencode(directory)):
            filename = os.path.join(directory, os.fsdecode(file))
            if not filename.endswith(".json"):
                continue

            # print("Processing %s" % filename)

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
                    trips[key]['positions'] = [(record['acp_lng'],
                                                record['acp_lat'],
                                                record['acp_ts']
                                                )]
                    trips[key]['bbox'] = [record['acp_lng'], record['acp_lat'],
                                          record['acp_lng'], record['acp_lat']]
                else:
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


def emit_trips(trips):
    '''
    Print trip details in CSV
    '''

    output = csv.writer(sys.stdout)
    heading = (
        'OriginRef',
        'OriginName',
        'DestinationRef',
        'DestinationName',
        'OriginAimedDepartureTime',
        'LineRef',
        'OperatorRef',
        'DirectionRef',
        'VehicleRef',
        'positions',
        'bounding_box')
    output.writerow(heading)

    for trip in trips:
        position_list = ','.join([','.join(p) for p in trip['positions']])
        bounding_box = '{},{},{},{}'.format(
            trip['bounding_box'][0],
            trip['bounding_box'][1],
            trip['bounding_box'][2],
            trip['bounding_box'][3],
            )
        row = (
            trip['OriginRef'],
            trip['OriginName'],
            trip['DestinationRef'],
            trip['DestinationName'],
            trip['OriginAimedDepartureTime'],
            trip['LineRef'],
            trip['OperatorRef'],
            trip['DirectionRef'],
            trip['VehicleRef'],
            position_list,
            bounding_box,
        )
        output.writerow(row)


def main():

    # Setup a coreapi client
    client = get_client()
    schema = client.get(API_SCHEMA)

    # Get the list of all the stops we are interested in
    stops = get_stops(client, schema, BOUNDING_BOX)

    # Collect realtime journeys
    trips = get_trips(sys.argv[1:], stops)

    emit_trips(trips)


if __name__ == "__main__":
    main()
