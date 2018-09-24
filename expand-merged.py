#!/usr/bin/env python3

"""
Expand merged trip/journey records to rows.

Read a list of merged trip/journey records for a given day. Output the
result in a spreadsheet-like row-by-row representation where each trip
and/or journey appears on its own row (as rows-{:%Y-%m-%d}.json and
rows-{:%Y-%m-%d}.csv)
"""

import csv
import datetime
import json
import logging
import sys


logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger('__name__')


def load_merged(day):

    filename = 'merged-{:%Y-%m-%d}.json'.format(day)
    logger.info('Reading %s', filename)

    with open(filename, 'r', newline='') as jsonfile:
        merged = json.load(jsonfile)

    logger.info('Done')

    return merged


seps = {
    '0-1': (' ', ' ', '\u21a6'),
    '1-0': (' ', ' ', '\u21a4'),
    '*-*': ('\u2533', '\u2503', '\u253b'),
    '0-*': ('\u250f', '\u2503', '\u2517'),
    '1-*': ('\u2533', '\u2503', '\u2517'),
    '*-0': ('\u2513', '\u2503', '\u251b'),
    '*-1': ('\u2533', '\u2503', '\u251b'),
}


def expand(day, results):

    rows = []

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
        n_rows = max(len(trips), len(journeys))
        if type in seps:
            seperator = [seps[type][1] for _ in range(n_rows)]
            seperator[0] = seps[type][0]
            seperator[-1] = seps[type][2]
        else:
            seperator = [' ' for _ in range(n_rows)]

        row_ctr = 0
        # Process matching trips/journeys
        while trips or journeys:
            row = {
                'type': type,
                'time': key[0],
                'origin': key[1],
                'destination': key[2],
                'trip': trips.pop(0) if trips else None,
                'separator': seperator[row_ctr],
                'journey': journeys.pop(0) if journeys else None,
            }
            rows.append(row)
            row_ctr += 1

    logger.info('Expanded into %s rows', len(rows))

    return rows


def emit_json(day, bounding_box, rows):
    '''
    Print row details in json to 'rows-<YYYY>-<mm>-<dd>.json'
    '''

    json_filename = 'rows-{:%Y-%m-%d}.json'.format(day)
    logger.info('Outputing JSON to %s', json_filename)

    with open(json_filename, 'w', newline='') as jsonfile:
        output = {
            'day': day.strftime('%Y-%m-%d'),
            'bounding_box': bounding_box,
            'rows': rows,
        }
        json.dump(output, jsonfile, indent=4, sort_keys=True)

    logger.info('Json output done')


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


def emit_csv(day, rows):
    '''
    Print row details in CSV to 'rows-<YYYY>-<mm>-<dd>.csv'
    '''

    csv_filename = 'rows-{:%Y-%m-%d}.csv'.format(day)
    logger.info('Outputing CSV to %s', csv_filename)

    with open(csv_filename, 'w', newline='') as csvfile:

        output = csv.writer(csvfile, dialect='excel', quoting=csv.QUOTE_ALL)

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
        for row in rows:

            r = (
                row['type'],
                '',
                row['time'],
                row['origin'],
                row['destination'],
                '',
            ) + trip_fields(row['trip']) + ('', row['separator'], '') + journey_fields(row['journey'])
            output.writerow(r)

    logger.info('CSV output done')


def main():

    logger.info('Start')

    try:
        day = datetime.datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
    except ValueError:
        logger.error('Failed to parse date')
        sys.exit()

    merged_data = load_merged(day)

    rows = expand(day, merged_data['merged'])

    emit_json(day, merged_data['bounding_box'], rows)
    emit_csv(day, rows)

    logger.info('Stop')


if __name__ == "__main__":
    main()
