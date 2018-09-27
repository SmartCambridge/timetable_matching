#!/usr/bin/env python3

"""
Match trips to journeys

Read a list of (vehicle) trips and a list of (timetable) journeys for a
given day and attempt to match them. Output the result as a list of
matched journeys and trips (as merged-<YYYY>-<mm>-<dd>.json).
"""

import collections
import datetime
import json
import logging
import sys

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


def load_stops(day):

    filename = 'stops-{:%Y-%m-%d}.json'.format(day)
    logger.info('Reading %s', filename)

    with open(filename, 'r', newline='') as jsonfile:
        stops = json.load(jsonfile)

    logger.info('Done')

    return stops


def do_merge(trips, journeys):
    '''
    Merge trips and journeys into one list, matching those with
    identical departure time, origin and destination
    '''

    # Group trips by OriginAimedDepartureTime/OriginRef/DestinationRef
    # and create a sorted list of keys
    trip_index = collections.defaultdict(list)
    trip_list = []
    for trip in trips:
        key = (
            trip['OriginAimedDepartureTime'],
            trip['OriginRef'],
            trip['DestinationRef']
        )
        trip_index[key].append(trip)
    trip_list = sorted(trip_index.keys())
    logger.info('Grouped %s trips into %s groups', len(trips), len(trip_list))

    # Dito for journeys, grouped by DepartureTime and first and last stop
    journey_index = collections.defaultdict(list)
    journey_list = []
    for journey in journeys:
        key = (
            journey['DepartureTime'],
            journey['stops'][0]['StopPointRef'],
            journey['stops'][-1]['StopPointRef']
        )
        journey_index[key].append(journey)
    journey_list = sorted(journey_index.keys())
    logger.info('Grouped %s journeys into %s groups', len(journeys), len(journey_list))

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

    logger.info('Created %s merged records', len(results))

    return results


def clasify_matches(merged):
    '''
    Add a type field to matches
    '''

    logger.info('Classifying %s merged records', len(merged))

    for merge in merged:
        trips = merge['trips']
        journeys = merge['journeys']
        # Derive the type string
        type = ((str(len(journeys)) if len(journeys) <= 1 else '*') +
                '-' +
                (str(len(trips)) if len(trips) <= 1 else '*'))
        merge['type'] = type
        logger.debug('jlen %s, tlen %s, type %s', len(journeys), len(trips), type)

    logger.info('Classification done')


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

    trip_data = load_trips(day)
    journey_data = load_journeys(day)
    stops_data = load_stops(day)

    if trip_data['day'] != journey_data['day']:
        logger.error('Date in trips (%s) doesn\'t match that in journeys (%s)',
                     trip_data['day'], journey_data['day'])
        sys.exit()

    if trip_data['bounding_box'] != journey_data['bounding_box']:
        logger.error('Bounding box in trips (%s) doesn\'t match that in journeys (%s)',
                     trip_data['bounding_box'], journey_data['bounding_box'])
        sys.exit()

    if trip_data['day'] != stops_data['day']:
        logger.error('Date in trips (%s) doesn\'t match that in stops (%s)',
                     trip_data['day'], stops_data['day'])
        sys.exit()

    if trip_data['bounding_box'] != stops_data['bounding_box']:
        logger.error('Bounding box in trips (%s) doesn\'t match that in stops (%s)',
                     trip_data['bounding_box'], _data['bounding_box'])
        sys.exit()

    merged = do_merge(trip_data['trips'], journey_data['journeys'])

    clasify_matches(merged)

    emit_merged(day, trip_data['bounding_box'], merged)

    logger.info('Stop')


if __name__ == "__main__":
    main()
