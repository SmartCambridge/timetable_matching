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

import isodate

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

        # Get the key, type, and *copies* of the trip row(s) and the journey row(s)
        key = result['key']
        type = result['type']
        trips = result['trips'][:]
        journeys = result['journeys'][:]

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
            'Departure day',
            'Departure time',
            'From',
            'To',
            'Trip-Line',
            'Trip-Operator',
            'Trip-Direction',
            'Trip-Vehicle',
            'Trip-Departure',
            'Trip-Arrival',
            '',
            'Journey-Line',
            'Journey-Operator',
            'Journey-Direction',
            'Journey-Departure',
            'Journey-Arrival',
            'Departure-Delay',
            'Arrival-Delay'
        ))

        # For each result row
        for row in rows:

            trip = row['trip']
            departure = arrival = None
            if trip is None:
                trip_fields = ('', '', '', '', '', '')
            else:
                departure_position = trip['departure_position']
                if departure_position is not None:
                    departure = isodate.parse_datetime(trip['positions'][departure_position]['RecordedAtTime'][:19])
                arrival_position = trip['arrival_position']
                if arrival_position is not None:
                    arrival = isodate.parse_datetime(trip['positions'][arrival_position]['RecordedAtTime'][:19])
                trip_fields = (
                    trip['LineRef'],
                    trip['OperatorRef'],
                    trip['DirectionRef'],
                    trip['VehicleRef'],
                    departure.strftime("%H:%M:%S") if departure else '',
                    arrival.strftime("%H:%M:%S") if arrival else '',
                )

            journey = row['journey']
            first = last = None
            if journey is None:
                journey_fields = ('', '', '', '', '')
            else:
                first = isodate.parse_datetime(journey['stops'][0]['time'])
                last = isodate.parse_datetime(journey['stops'][-1]['time'])
                journey_fields = (
                    journey['Service']['LineName'],
                    journey['Service']['OperatorCode'],
                    journey['Direction'],
                    first.strftime("%H:%M"),
                    last.strftime("%H:%M")
                )

            departure_delay = ''
            if departure is not None and first is not None:
                departure_delay = (departure - first).total_seconds() / 60
            arrival_delay = ''
            if arrival is not None and last is not None:
                arrival_delay = (arrival - last).total_seconds() / 60

            time = isodate.parse_datetime(row['time'])

            r = (
                (
                    row['type'],
                    time.strftime("%Y-%m-%d"),
                    time.strftime("%H:%M"),
                    row['origin'],
                    row['destination'],
                ) +
                trip_fields +
                (row['separator'],) +
                journey_fields +
                (departure_delay, arrival_delay)
            )

            output.writerow(r)

    logger.info('CSV output done')


def main():

    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

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
