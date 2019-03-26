#!/usr/bin/env python3

"""
Extract start/end times plus durations and maximum wait time for
the track segments in the supplied file
"""

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
#     "segments": [
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
        trips = json.load(jsonfile)

    logger.info('Done')

    return trips


def sumarise(segments):

    header = [
        'Trip_Vehicle',
        'Trip_Departure',
        'Trip_Arrival',
        'Trip_Max_Wait',
        'Trip_Duration',
    ]

    values = []
    previous_departure = None

    for segment in segments['segments']:

        departure = isodate.parse_datetime(segment['positions'][0]['RecordedAtTime'])
        arrival = isodate.parse_datetime(segment['positions'][-1]['RecordedAtTime'])

        duration = int((arrival-departure).total_seconds())
        max_wait = None
        if previous_departure:
            max_wait = int((departure-previous_departure).total_seconds())

        values.append([
            segment['VehicleRef'],
            departure,
            arrival,
            max_wait,
            duration,
        ])

        previous_departure = departure

    return header, values


def emit_csv(basename, header, values):

    csv_filename = '{}.csv'.format(basename)
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
