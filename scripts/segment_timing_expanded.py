#!/usr/bin/env python3

"""
From a set of vehicle track segments, workout wait+travel time for
a selection of arrival times
"""

import datetime
import json
import logging
import sys
import csv

import isodate

logger = logging.getLogger('__name__')

# {
#     "bounding_box": "0.007896,52.155610,0.225048,52.267842",
#     "day": "2019-03-20",
#     "from_stop": {
#         "atco_code": "0500SMILT010",
#         "common_name": "Milton Park-and-Ride",
#         "id": "0500SMILT010",
#         "indicator": "Stop 1",
#         "lat": 52.2451385817,
#         "latitude": 52.2451385817,
#         "lng": 0.15097039186,
#         "locality_name": "Milton",
#         "longitude": 0.15097039186,
#         "naptan_code": "CMBGJTMA",
#         "stop_id": "0500SMILT010"
#     },
#     "line": "PR5",
#     "to_stop": {
#         "atco_code": "0500CCITY486",
#         "common_name": "Drummer Street",
#         "id": "0500CCITY486",
#         "indicator": "Stop D1",
#         "lat": 52.2049274264,
#         "latitude": 52.2049274264,
#         "lng": 0.12463017631,
#         "locality_name": "Cambridge",
#         "longitude": 0.12463017631,
#         "naptan_code": "CMBGJPWJ",
#         "stop_id": "0500CCITY486"
#     },
#     "trips": [
#         {
#             "VehicleRef": "SCCM-10806",
#             "positions": [
#                 {
#                     "Bearing": "60",
#                     "Delay": "PT0S",
#                     "Latitude": "52.2453651",
#                     "Longitude": "0.1514220",
#                     "RecordedAtTime": "2019-03-20T06:21:17+00:00"
#                 },
#                 <...>
#             ],
#         },
#     ],
#  }


def load_segments(basename):

    filename = '{}.json'.format(basename)
    logger.info('Reading %s', filename)

    with open(filename, 'r', newline='') as jsonfile:
        segments = json.load(jsonfile)

    logger.info('Done')

    return segments


def sumarise(segments):

    header = [
        'Passenger_Arrival',
        'Passenger_Wait',
        'Trip_Vehicle',
        'Trip_Departure',
        'Trip_Arrival',
        'Trip_Duration',
        'Passenger_Journey_Duration',
    ]

    values = []

    # Build a table of trip times
    trip_table = []
    for segment in segments['segments']:
        if not segment['on_route']:
            continue
        departure = isodate.parse_datetime(segment['positions'][0]['RecordedAtTime'])
        arrival = isodate.parse_datetime(segment['positions'][-1]['RecordedAtTime'])
        trip_table.append([departure, arrival, segment['VehicleRef']])

    # Find the top of the hour before the first bus
    start = trip_table[0][0].replace(minute=0, second=0)
    # And the top of the hour after the last one
    end = trip_table[-1][0].replace(minute=0, second=0) + datetime.timedelta(hours=1)
    step = datetime.timedelta(minutes=1)

    logger.debug("Start %s, end %s, step %s", start, end, step)

    # Step through the day from 'start' to 'end' in steps of 'step'
    # Find the next bus to depart after 'start'
    while start < end:
        # Find first departure after 'start'
        for row in trip_table:
            logger.debug("row[1]: %s, start: %s", row[1], start)
            if row[0] > start:
                wait = int((row[0] - start).total_seconds())
                traveling = int((row[1] - row[0]).total_seconds())
                duration = wait + traveling
                values.append([
                    start,
                    wait,
                    row[2],
                    row[0],
                    row[1],
                    traveling,
                    duration,
                ])
                break
        else:
            logger.debug("No bus for a departure at %s", start)

        start = start + step

    return header, values


def emit_csv(basename, header, values):

    csv_filename = '{}-expanded.csv'.format(basename)
    logger.info('Outputing CSV to %s', csv_filename)

    with open(csv_filename, 'w', newline='') as csvfile:

        # Create CSV, add headers
        output = csv.writer(csvfile, dialect='excel', quoting=csv.QUOTE_ALL)
        output.writerow(header)
        output.writerows(values)


def main():

    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

    logger.info('Start')

    basename = sys.argv[1]

    segments = load_segments(basename)

    header, values = sumarise(segments)

    emit_csv(basename, header, values)

    logger.info('Stop')


if __name__ == "__main__":
    main()
