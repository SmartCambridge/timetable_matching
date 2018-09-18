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


def do_merge(trips, journeys):

    trip_index = collections.defaultdict(list)
    trip_list = []
    for trip in trips['trips']:
        key = (
            trip['OriginAimedDepartureTime'][:19],
            trip['OriginRef'],
            trip['DestinationRef']
        )
        trip_index[key].append(trip)
    trip_list = sorted(trip_index.keys())
    logger.debug(json.dumps(trip_list, indent=4))

    journey_index = collections.defaultdict(list)
    journey_list = []
    for journey in journeys['journeys']:
        key = (
            journey['DepartureTime'],
            journey['stops'][0]['StopPointRef'],
            journey['stops'][-1]['StopPointRef']
        )
        journey_index[key].append(journey)
    journey_list = sorted(journey_index.keys())
    logger.debug(json.dumps(journey_list, indent=4))

    results = []
    while trip_list and journey_list:
        if trip_list[0] < journey_list[0]:
            results.append({
                'trips': trip_index[trip_list.pop(0)],
                'journeys': []
            })
        elif trip_list[0] > journey_list[0]:
            results.append({
                'trips': [],
                'journeys': journey_index[journey_list.pop(0)]
            })
        else:
            trips = trip_index[trip_list.pop(0)]
            journeys = journey_index[journey_list.pop(0)]
            results.append({
                'trips': trips,
                'journeys': journeys
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

    return results


def sumarise(results):

    output = csv.writer(sys.stdout)

    for result in results:

        if len(result['journeys']) == 0:
            for trip in result['trips']:
                row = (
                    'Unmatched trip',
                    '',
                    trip['OriginAimedDepartureTime'][:19],
                    trip['OriginRef'],
                    trip['OriginName'],
                    trip['DestinationRef'],
                    trip['DestinationName'],
                    '',
                    trip['PublishedLineName'],
                    '',
                    '',
                )
                output.writerow(row)
        elif len(result['trips']) == 0:
            for journey in result['journeys']:
                row = (
                    'Unmatched journey',
                    '',
                    journey['DepartureTime'],
                    journey['stops'][0]['StopPointRef'],
                    journey['stops'][0]['CommonName'],
                    journey['stops'][-1]['StopPointRef'],
                    journey['stops'][-1]['CommonName'],
                    '',
                    ''
                    '',
                    journey['Service']['LineName'],
                )
                output.writerow(row)
        elif len(result['journeys']) == 1 and len(result['trips']) == 1:
            trip = result['trips'][0]
            journey = result['journeys'][0]
            row = (
                'Matched trip/journey',
                '',
                trip['OriginAimedDepartureTime'][:19],
                trip['OriginRef'],
                trip['OriginName'],
                trip['DestinationRef'],
                trip['DestinationName'],
                '',
                trip['PublishedLineName'],
                '',
                journey['Service']['LineName'],
            )
            output.writerow(row)
        else:
            row = (
                'Multi-matched journey(s)',
                '',
            )
            output.writerow(row)


def main():

    logger.info('Start')

    try:
        day = datetime.datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
    except ValueError:
        logger.error('Failed to parse date')
        sys.exit()

    trips = load_trips(day)
    journeys = load_journeys(day)

    if trips['day'] != journeys['day']:
        logger.error('Date in trips (%s) doesn\'t match that in journeys (%s)',
                     trips['day'], journeys['day'])
        sys.exit()

    if trips['bounding_box'] != journeys['bounding_box']:
        logger.error('Bounding box in trips (%s) doesn\'t match that in journeys (%s)',
                     trips['bounding_box'], journeys['bounding_box'])
        sys.exit()

    results = do_merge(trips, journeys)

    sumarise(results)

    logger.info('Stop')


if __name__ == "__main__":
    main()
