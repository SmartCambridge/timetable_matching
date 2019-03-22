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
#             ]
#         },
#     ]
# }

def extract_trips(tracks):
    '''
    Extract all trips from start stop to end stop 
    '''


 # Borrowed from get_trips.pt: derive_timings

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
        # the very last position if it's within threshold * 4
        if arrival_position is None:
            final_position = trip['positions'][-1]
            final = (float(final_position['Latitude']), float(final_position['Longitude']))
            if (haversine(final, destination) * 1000) < (threshold * 4):
                arrival_position = len(trip['positions']) - 1
                logger.debug('Using final position for arrival')


        logger.debug('Departure row %s; arrival row %s', departure_position, arrival_position)
        logger.debug('')

        trip['departure_position'] = departure_position
        trip['arrival_position'] = arrival_position

# END borrow

    return trips


def emit_trips(day, trips):
    '''
    Print trip details in json to 'trips-<YYYY>-<mm>-<dd>.json'
    '''

    filename = 'trips-from-tracks-{:%Y-%m-%d}.json'.format(day)
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

    logger.info('Start')

    try:
        day = datetime.datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
    except ValueError:
        logger.error('Failed to parse date')
        sys.exit()

    tracks = load_tracks(day)

    trips = extract_trips(tracks)

    emit_trips(day, tracks['bounding_box'], trips)

    logger.info('Stop')


if __name__ == "__main__":
    main()
