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


def load_stops(day):

    filename = 'stops-{:%Y-%m-%d}.json'.format(day)
    logger.info('Reading %s', filename)

    with open(filename, 'r', newline='') as jsonfile:
        stops = json.load(jsonfile)

    logger.info('Done')

    return stops


seps = {
    '0-1': (' ', ' ', '\u21a6'),
    '1-0': (' ', ' ', '\u21a4'),
    '*-*': ('\u2533', '\u2503', '\u253b'),
    '0-*': ('\u250f', '\u2503', '\u2517'),
    '1-*': ('\u2533', '\u2503', '\u2517'),
    '*-0': ('\u2513', '\u2503', '\u251b'),
    '*-1': ('\u2533', '\u2503', '\u251b'),
}


def describe_stop(stop_code, stops):

    if stop_code not in stops:
        return stop_code

    result = []
    stop = stops[stop_code]
    if 'common_name' in stop:
        if ('indicator' in stop and
            stop['indicator'] in ('opp', 'outside', 'o/s', 'adj', 'near',
                                  'nr', 'behind', 'inside', 'by', 'in',
                                  'at', 'on', 'before', 'just before',
                                  'after', 'just after', 'corner of')):
            result.append(stop['indicator'] + ' ' + stop['common_name'])
        elif ('indicator' in stop):
            result.append(stop['common_name'] + ' ' + stop['indicator'])
        else:
            result.append(stop['common_name'])

    if 'locality_name' in stop:
        result.append(stop['locality_name'])

    return ', '.join(result)


def expand(day, merged, stops):

    rows = []

    # For each result row
    for result in merged:

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
                'origin_desc': describe_stop(key[1], stops),
                'destination': key[2],
                'destination_desc': describe_stop(key[2], stops),
                'journey': journeys.pop(0) if journeys else None,
                'separator': seperator[row_ctr],
                'trip': trips.pop(0) if trips else None,
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


def emit_csv(day, rows, stops):
    '''
    Print row details in CSV to 'rows-<YYYY>-<mm>-<dd>.csv'
    '''

    csv_filename = 'rows-{:%Y-%m-%d}.csv'.format(day)
    logger.info('Outputing CSV to %s', csv_filename)

    with open(csv_filename, 'w', newline='') as csvfile:

        output = csv.writer(csvfile, dialect='excel', quoting=csv.QUOTE_ALL)

        output.writerow((
            'Type',
            'Day',
            'Time',
            'From',
            'To',
            'Journey: Line',
            'Journey: Operator',
            'Journey: Direction',
            'Journey: Departure',
            'Journey: Arrival',
            ' ',
            'Trip: Line',
            'Trip: Operator',
            'Trip: Direction',
            'Trip: Vehicle',
            'Trip: Departure',
            'Trip: Arrival',
            'Delay: Departure',
            'Delay: Arrival',
        ))

        # For each result row
        for row in rows:

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

            trip = row['trip']
            departure = arrival = None
            if trip is None:
                trip_fields = ('', '', '', '', '', '')
            else:
                departure_position = trip['departure_position']
                if departure_position is not None:
                    departure = isodate.parse_datetime(trip['positions'][departure_position]['RecordedAtTime'])
                arrival_position = trip['arrival_position']
                if arrival_position is not None:
                    arrival = isodate.parse_datetime(trip['positions'][arrival_position]['RecordedAtTime'])
                trip_fields = (
                    trip['LineRef'],
                    trip['OperatorRef'],
                    trip['DirectionRef'],
                    trip['VehicleRef'],
                    departure.strftime("%H:%M:%S") if departure else '',
                    arrival.strftime("%H:%M:%S") if arrival else '',
                )

            departure_delay = None
            if departure is not None and first is not None:
                departure_delay = (departure - first)
            arrival_delay = None
            if arrival is not None and last is not None:
                arrival_delay = (arrival - last)

            time = isodate.parse_datetime(row['time'])

            r = (
                (
                    row['type'],
                    time.strftime("%Y-%m-%d"),
                    time.strftime("%H:%M"),
                    row['origin_desc'],
                    row['destination_desc'],
                ) +
                journey_fields +
                (row['separator'],) +
                trip_fields +
                (format_timedelta(departure_delay),
                 format_timedelta(arrival_delay))
            )

            output.writerow(r)

    logger.info('CSV output done')


def format_timedelta(delta):
    if delta is None:
        return ''
    sign = '-' if delta.total_seconds() < 0 else ''
    return sign + isodate.strftime(delta, '%P')


def main():

    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

    logger.info('Start')

    try:
        day = datetime.datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
    except ValueError:
        logger.error('Failed to parse date')
        sys.exit()

    merged_data = load_merged(day)
    stops_data = load_stops(day)

    if merged_data['day'] != stops_data['day']:
        logger.error('Date in merged (%s) doesn\'t match that in stops (%s)',
                     merged_data['day'], stops_data['day'])
        sys.exit()

    if merged_data['bounding_box'] != stops_data['bounding_box']:
        logger.error('Bounding box in merged (%s) doesn\'t match that in stops (%s)',
                     merged_data['bounding_box'], stops_data['bounding_box'])
        sys.exit()

    rows = expand(day, merged_data['merged'], stops_data['stops'])

    emit_json(day, merged_data['bounding_box'], rows)
    emit_csv(day, rows, stops_data['stops'])

    logger.info('Stop')


if __name__ == "__main__":
    main()
