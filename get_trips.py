#!/usr/bin/env python3

'''
Retrieve trip information

Given a date, process SIRI-VM data in JSON for that day and spit out all
unique vehicle trips (based on OriginRef, DestinationRef,
OriginAimedDepartureTime, LineRef, OperatorRef, DirectionRef, and
VehicleRef) where at least one of the origin or destination in a list of
stops defined by a bounding box. Output the resulting data in json.

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

from haversine import haversine
import isodate

from util import (
    API_SCHEMA, BOUNDING_BOX, LOAD_PATH, get_client, get_stops,
    update_bbox, lookup
)

logger = logging.getLogger('__name__')

other_stops = {}


def get_trips(client, schema, date, interesting_stops):
    '''
    Extract trips for a day

    Return a list of all trips (realtime journeys) on the day
    indicated by year/month/day that have origin or destination stops in
    our stops list (and so fall within our bounding box)
    '''

    trips = {}

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

            # Collect all the data that's common for one trip
            TRIP_FIELDS = (
                'DestinationName', 'DestinationRef', 'DirectionRef', 'LineRef',
                'OperatorRef', 'OriginAimedDepartureTime', 'OriginName',
                'OriginRef', 'VehicleRef'
            )

            if key not in trips:

                trips[key] = {field: record[field] for field in TRIP_FIELDS}

                trips[key]['OriginStop'] = lookup(
                    client, schema,
                    record['OriginRef'],
                    interesting_stops,
                    other_stops)
                trips[key]['DestinationStop'] = lookup(
                    client, schema,
                    record['DestinationRef'],
                    interesting_stops,
                    other_stops)

                trips[key]['positions'] = []

                trips[key]['bbox'] = [None, None, None, None]

            # ... and the data that makes up a position report
            POSITION_FIELDS = (
                'Bearing', 'Delay', 'Latitude', 'Longitude', 'RecordedAtTime'
            )

            position = {field: record[field] for field in POSITION_FIELDS}
            trips[key]['positions'].append(position)

            update_bbox(trips[key]['bbox'],
                        record['Longitude'],
                        record['Latitude'])

    logger.info("Found %s trips", len(trips))

    # Collect only trips that actually start today (at least some will have
    # started yesterday), and sort their position records by time
    result = []
    skipped_trips = 0
    for trip in trips.values():
        departure_timestamp = isodate.parse_datetime(trip['OriginAimedDepartureTime'])
        if date == departure_timestamp.date():
            trip['positions'].sort(key=lambda pos: pos['RecordedAtTime'])
            result.append(trip)
        else:
            skipped_trips += 1

    logger.info("Skipped %s trips which started in the wrong day", skipped_trips)
    logger.info("Found %s interesting trips", len(result))

    return result


def derive_timings(trips):
    '''
    Workout actual departure and arrival timings for each trip
    '''

    logger.info('Deriving timings for %s trips', len(trips))

    threshold = 100

    for trip in trips:

        logger.debug('')
        logger.debug('Processing %s to %s at %s', trip['OriginRef'],
                     trip['DestinationRef'], trip['OriginAimedDepartureTime'])

        origin = (float(trip['OriginStop']['latitude']),
                  float(trip['OriginStop']['longitude']))
        destination = (float(trip['DestinationStop']['latitude']),
                       float(trip['DestinationStop']['longitude']))

        departure_state = 'before'
        arrival_state = 'before'
        departure_position = arrival_position = None

        for row, position in enumerate(trip['positions']):

            logger.debug('')
            logger.debug('Processing position %s', row)
            logger.debug('initial origin state %s; destination state %s', departure_state, arrival_state)

            here = (float(position['Latitude']), float(position['Longitude']))

            origin_distance = haversine(here, origin) * 1000  # in meters

            logger.debug('Origin distance %s', origin_distance)

            if departure_state == 'before' and origin_distance < threshold:
                departure_state = 'at'
                logger.debug('Departure state transition before --> at')
            elif departure_state == 'at' and origin_distance > threshold:
                departure_position = row - 1
                departure_state = 'after'
                logger.debug('Departure state transition at --> after')

            destination_distance = haversine(here, destination) * 1000  # in meters

            logger.debug('Destination distance %s', destination_distance)

            if arrival_state == 'before' and destination_distance < threshold:
                arrival_state = 'at'
                arrival_position = row
                logger.debug('Arrival state transition before --> at')

            logger.debug('Final origin state %s; destination state %s', departure_state, arrival_state)

        # Try a bit harder if we still don't have an arrival_position - use
        # the very last position if it's within threshold * 2
        if arrival_position is None:
            final_position = trip['positions'][-1]
            final = (float(final_position['Latitude']), float(final_position['Longitude']))
            if (haversine(final, destination) * 1000) < (threshold * 2):
                arrival_position = len(trip['positions']) - 1
                logger.debug('Using final position for arrival')


        logger.debug('Departure row %s; arrival row %s', departure_position, arrival_position)
        logger.debug('')

        trip['departure_position'] = departure_position
        trip['arrival_position'] = arrival_position


def emit_trips(day, trips):
    '''
    Print trip details in json to 'trips-<YYYY>-<mm>-<dd>.json'
    '''

    filename = 'trips-{:%Y-%m-%d}.json'.format(day)
    logger.info('Outputing to %s', filename)

    with open(filename, 'w', newline='') as jsonfile:
        output = {
            'day': day.strftime("%Y-%m-%d"),
            'bounding_box': BOUNDING_BOX,
            'trips': trips
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

    # Collect realtime journeys
    trips = get_trips(client, schema, day, interesting_stops)

    # Derive departure and arrival timings
    derive_timings(trips)

    emit_trips(day, trips)

    logger.info('Stop')


if __name__ == "__main__":
    main()
