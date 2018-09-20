#!/usr/bin/env python3

"""

"""

import collections
import csv
import datetime
import json
import logging
import sys

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger('__name__')


def load_trips(day):

    filename = 'trips-{:%Y-%m-%d}.json'.format(day)
    logger.info('Reading %s', filename)

    with open(filename, 'r', newline='') as jsonfile:
        trips = json.load(jsonfile)

    logger.info('Done')

    return trips


def load_journeys(day):

    filename = 'journeys-{:%Y-%m-%d}.json'.format(day)
    logger.info('Reading %s', filename)

    with open(filename, 'r', newline='') as jsonfile:
        journeys = json.load(jsonfile)

    logger.info('Done')

    return journeys


def do_merge(trip_data, journey_data):
    '''
    Merge trips and journeys into one list, matching those with
    identical departure time, origin and destination
    '''

    # Group trips by OriginAimedDepartureTime/OriginRef/DestinationRef
    # and create a sorted list of keys
    trip_index = collections.defaultdict(list)
    trip_list = []
    for trip in trip_data['trips']:
        key = (
            trip['OriginAimedDepartureTime'][:19],
            trip['OriginRef'],
            trip['DestinationRef']
        )
        trip_index[key].append(trip)
    trip_list = sorted(trip_index.keys())
    logger.info('Grouped %s trips into %s groups', len(trip_data['trips']), len(trip_list))

    # Dito for journeys, grouped by DepartureTime and first and last stop
    journey_index = collections.defaultdict(list)
    journey_list = []
    for journey in journey_data['journeys']:
        key = (
            journey['DepartureTime'],
            journey['stops'][0]['StopPointRef'],
            journey['stops'][-1]['StopPointRef']
        )
        journey_index[key].append(journey)
    journey_list = sorted(journey_index.keys())
    logger.info('Grouped %s journeys into %s groups', len(journey_data['journeys']), len(journey_list))

    # Merge trips and journeys into one list that has one row per distinct
    # departure tile/origin/destination and whose first column contains a
    # (possibly empty) list of trips and whose second column contains a
    # (possibly empty) list of journeys
    results = []
    while trip_list and journey_list:
        if trip_list[0] < journey_list[0]:
            results.append({
                'key': trip_list[0],
                'trips': trip_index[trip_list.pop(0)],
                'journeys': []
            })
        elif trip_list[0] > journey_list[0]:
            results.append({
                'key': journey_list[0],
                'trips': [],
                'journeys': journey_index[journey_list.pop(0)]
            })
        else:
            results.append({
                'key': trip_list[0],
                'trips': trip_index[trip_list.pop(0)],
                'journeys': journey_index[journey_list.pop(0)]
            })
    while trip_list:
        results.append({
            'trips': trip_index[trip_list.pop(0)],
            'journeys': []
        })
    while journey_list:
        results.append({
            'trips': [],
            'journeys': journey_index[journey_list.pop(0)]
        })

    logger.info('Created %s merged rows', len(results))

    return results


seps = {
    '0-1': (' ', ' ', '\u21a6'),
    '1-0': (' ', ' ', '\u21a4'),
    '*-*': ('\u2533', '\u2503', '\u253b'),
    '0-*': ('\u250f', '\u2503', '\u2517'),
    '1-*': ('\u2533', '\u2503', '\u2517'),
    '*-0': ('\u2513', '\u2503', '\u251b'),
    '*-1': ('\u2533', '\u2503', '\u251b'),
}


def sumarise(day, results):

    filename = 'merged-{:%Y-%m-%d}.csv'.format(day)
    logger.info('Outputing CSV to %s', filename)

    with open(filename, 'w', newline='') as csvfile:

        output = csv.writer(csvfile)

        output.writerow((
            'Type',
            '',
            'Departure time',
            'From',
            'To',
            '',
            'Trip-Line',
            'Trip-Operator',
            'Trip-Direction',
            'Trip-Vehicle',
            'Trip-Positions',
            '',
            '',
            '',
            'Journey-Line',
            'Journey-Operator',
            'Journey-Direction',
        ))

        # For each result row
        for result in results:

            # Get the key, and *copies* of the trip row(s) and the journey row(s)
            key = result['key']
            trips = result['trips'][:]
            journeys = result['journeys'][:]

            # Derive the type string
            type = ((str(len(trips)) if len(trips) <= 1 else '*') +
                    '-' +
                    (str(len(journeys)) if len(journeys) <= 1 else '*'))
            logger.debug('tlen %s, jlen %s, type %s', len(trips), len(journeys), type)

            # Pre-populate a list of separators
            rows = max(len(trips), len(journeys))
            if type in seps:
                seperator = [seps[type][1] for _ in range(rows)]
                seperator[0] = seps[type][0]
                seperator[-1] = seps[type][2]
            else:
                seperator = [' ' for _ in range(rows)]

            row = 0
            # Process matching trips/journeys
            while trips and journeys:
                r = (
                    type,
                    '',
                    key[0],
                    key[1],
                    key[2],
                    '',
                ) + trip_fields(trips.pop(0)) + ('', seperator[row], '') + journey_fields(journeys.pop(0))
                output.writerow(r)
                row += 1
            # Process remaining trips
            while trips:
                r = (
                    type,
                    '',
                    key[0],
                    key[1],
                    key[2],
                    '',
                ) + trip_fields(trips.pop(0)) + ('', seperator[row], '') + journey_fields(None)
                output.writerow(r)
                row += 1
            # Process remaining journeys
            while journeys:
                r = (
                    type,
                    '',
                    key[0],
                    key[1],
                    key[2],
                    '',
                ) + trip_fields(None) + ('', seperator[row], '') + journey_fields(journeys.pop(0))
                output.writerow(r)
                row += 1

    logger.info('Output done')


def trip_fields(trip):
    if trip is None:
        return ('', '', '', '', '')
    return (
        trip['LineRef'],
        trip['OperatorRef'],
        trip['DirectionRef'],
        trip['VehicleRef'],
        len(trip['positions']),
    )


def journey_fields(journey):
    if journey is None:
        return ('', '', '')
    return (
        journey['Service']['LineName'],
        journey['Service']['OperatorCode'],
        journey['Direction']
    )


def emit_merged(day, bounding_box, results):
    '''
    Print merged details in json to 'merged-<YYYY>-<mm>-<dd>.json'
    '''

    filename = 'merged-{:%Y-%m-%d}.json'.format(day)
    logger.info('Outputing JSON to %s', filename)

    with open(filename, 'w', newline='') as jsonfile:
        output = {
            'day': day.strftime('%Y-%m-%d'),
            'bounding_box': bounding_box,
            'merged': results
        }
        json.dump(results, jsonfile, indent=4, sort_keys=True)

    logger.info('Output done')


def main():

    logger.info('Start')

    try:
        day = datetime.datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
    except ValueError:
        logger.error('Failed to parse date')
        sys.exit()

    trip_data = load_trips(day)
    journey_data = load_journeys(day)

    if trip_data['day'] != journey_data['day']:
        logger.error('Date in trips (%s) doesn\'t match that in journeys (%s)',
                     trip_data['day'], journey_data['day'])
        sys.exit()

    if trip_data['bounding_box'] != journey_data['bounding_box']:
        logger.error('Bounding box in trips (%s) doesn\'t match that in journeys (%s)',
                     trip_data['bounding_box'], journey_data['bounding_box'])
        sys.exit()

    results = do_merge(trip_data, journey_data)

    emit_merged(day, trip_data['bounding_box'], results)

    sumarise(day, results)

    logger.info('Stop')


if __name__ == "__main__":
    main()
