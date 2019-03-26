#!/usr/bin/env python3

"""
Extract best and worse total journey times in the time ranges
before 10:00, from 10:00 to before 15:00, from 15:00 onward
from the supplied vehicle journey segments
"""

import json
import logging
import sys
import csv

import isodate

from dateutil import tz

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


def load_segments(filename):

    logger.info('Reading %s', filename)

    with open(filename, 'r', newline='') as jsonfile:
        segments = json.load(jsonfile)

    logger.info('Done')

    return segments


def sumarise(segments):

    uklocal = tz.gettz('Europe/London')

    results = {
        'morning': {
            'best': None,
            'worst': None
        },
        'daytime': {
            'best': None,
            'worst': None
        },
        'evening': {
            'best': None,
            'worst': None
        }
    }
    previous_departure = None
    day = None

    for segment in segments['segments']:

        departure = isodate.parse_datetime(segment['positions'][0]['RecordedAtTime'])
        arrival = isodate.parse_datetime(segment['positions'][-1]['RecordedAtTime'])

        if not day:
            day = departure.date()

        duration = int((arrival-departure).total_seconds())
        max_wait = None
        if previous_departure:
            max_wait = int((departure-previous_departure).total_seconds())

        hour = departure.astimezone(uklocal).hour
        slot = 'morning'
        if hour >= 10:
            slot = 'daytime'
        if hour >= 15:
            slot = 'evening'

        logger.debug("hour %s, slot: %s", hour, slot)

        if results[slot]['best'] is None or results[slot]['best'] > duration:
            results[slot]['best'] = duration

        if max_wait and (results[slot]['worst'] is None or
                         results[slot]['worst'] < duration - max_wait):
            results[slot]['worst'] = duration + max_wait

        previous_departure = departure

    values = [
        day,
        segments['from_stop']['atco_code'],
        segments['to_stop']['atco_code'],
        results['morning']['best'],
        results['morning']['worst'],
        results['daytime']['best'],
        results['daytime']['worst'],
        results['evening']['best'],
        results['evening']['worst'],
    ]

    return values


def main():

    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

    logger.info('Start')

    values = []
    header = [
        'Day',
        'Origin',
        'Destination',
        'Morning best',
        'Morning worst',
        'Daytime best',
        'Daytime worst',
        'Evening best',
        'Evening worst',
    ]

    for filename in sys.argv[1:]:

        segments = load_segments(filename)

        values.append(sumarise(segments))

    values.sort(key=lambda row: row[0])

    output = csv.writer(sys.stdout, dialect='excel', quoting=csv.QUOTE_ALL)
    output.writerow(header)
    output.writerows(values)

    logger.info('Stop')


if __name__ == "__main__":
    main()
