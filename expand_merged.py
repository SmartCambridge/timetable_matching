#!/usr/bin/env python3

"""
Expand merged trip/journey records to rows.

Read a list of merged trip/journey records for a given day. Output the
result in a spreadsheet-like row-by-row representation where each trip
and/or journey appears on its own row (as rows-{:%Y-%m-%d}.json and
rows-{:%Y-%m-%d}.csv)
"""

import datetime
import json
import logging
import sys

import isodate

logger = logging.getLogger('__name__')

# Unicode characters used to show relationship between journeys and trips
# seps{ }[0] for the first row, seps{ }[2] for the last (or only)
# seps{ }[1] otherwise
seps = {
    '0-1': (' ', ' ', '\u21a6'),
    '1-0': (' ', ' ', '\u21a4'),
    '*-*': ('\u2533', '\u2503', '\u253b'),
    '0-*': ('\u250f', '\u2503', '\u2517'),
    '1-*': ('\u250f', '\u2503', '\u2517'),
    '*-0': ('\u2513', '\u2503', '\u251b'),
    '*-1': ('\u2513', '\u2503', '\u251b'),
}


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


def describe_stop(stop_code, stops):
    '''
    Expand ATCO Code to human-redable stop description
    '''

    if stop_code not in stops:
        return stop_code

    result = []
    stop = stops[stop_code]
    if 'common_name' in stop:
        if (
            'indicator' in stop and
            stop['indicator'].lower() in (
                'opp', 'outside', 'o/s', 'adj', 'near',
                'nr', 'behind', 'inside', 'by', 'in',
                'at', 'on', 'before', 'just before',
                'after', 'just after', 'corner of'
            )
        ):
            result.append(stop['indicator'] + ' ' + stop['common_name'])
        elif ('indicator' in stop):
            result.append(stop['common_name'] + ' ' + stop['indicator'])
        else:
            result.append(stop['common_name'])

    if 'locality_name' in stop:
        result.append(stop['locality_name'])

    return ', '.join(result)


def expand(day, merged, stops):
    '''
    Expand merged representation of the relationship into an array of
    rows (in date/time order). Add departure & arrival delay for all
    journey -> trip matches.
    '''

    rows = []

    # For each result row
    for result in merged:

        # Get the key, type,  trip row(s) and the journey row(s)
        type = result['type']
        trips = result['trips']
        journeys = result['journeys']

        # Pre-populate a list of separators
        n_rows = max(1, len(trips)) * max(1, len(journeys))
        if type in seps:
            seperator = [seps[type][1] for _ in range(n_rows)]
            seperator[0] = seps[type][0]
            seperator[-1] = seps[type][2]
        else:
            seperator = [' ' for _ in range(n_rows)]

        # Trips with no journeys
        if len(journeys) == 0:
            row_ctr = 0
            for trip in trips:
                row = {
                    'type': type,
                    'time': trip['OriginAimedDepartureTime'],
                    'origin': trip['OriginRef'],
                    'origin_desc': describe_stop(trip['OriginRef'], stops),
                    'destination': trip['DestinationRef'],
                    'destination_desc': describe_stop(trip['DestinationRef'], stops),
                    'journey': None,
                    'separator': seperator[row_ctr],
                    'trip': trip,
                    'departure_delay': None,
                    'arrival_delay': None
                }
                rows.append(row)
                row_ctr += 1
        # Journeys with no trips
        elif len(trips) == 0:
            row_ctr = 0
            for journey in journeys:
                row = {
                    'type': type,
                    'time': journey['DepartureTime'],
                    'origin': journey['stops'][0]['StopPointRef'],
                    'origin_desc': describe_stop(journey['stops'][0]['StopPointRef'], stops),
                    'destination': journey['stops'][-1]['StopPointRef'],
                    'destination_desc': describe_stop(journey['stops'][-1]['StopPointRef'], stops),
                    'journey': journey,
                    'separator': seperator[row_ctr],
                    'trip': None,
                    'departure_delay': None,
                    'arrival_delay': None
                }
                rows.append(row)
                row_ctr += 1
        # Everything else
        else:
            row_ctr = 0
            for journey in journeys:
                first_stop_time = isodate.parse_datetime(journey['stops'][0]['time'])
                last_stop_time = isodate.parse_datetime(journey['stops'][-1]['time'])
                for trip in trips:

                    departure_position = trip['departure_position']
                    if departure_position is not None:
                        departure_time = isodate.parse_datetime(trip['positions'][departure_position]['RecordedAtTime'])
                        departure_delay = int((departure_time - first_stop_time).total_seconds())
                    else:
                        departure_delay = None

                    arrival_position = trip['arrival_position']
                    if arrival_position is not None:
                        arrival_time = isodate.parse_datetime(trip['positions'][arrival_position]['RecordedAtTime'])
                        arrival_delay = int((arrival_time - last_stop_time).total_seconds())
                    else:
                        arrival_delay = None

                    row = {
                        'type': type,
                        'time': journey['DepartureTime'],
                        'origin': journey['stops'][0]['StopPointRef'],
                        'origin_desc': describe_stop(journey['stops'][0]['StopPointRef'], stops),
                        'destination': journey['stops'][-1]['StopPointRef'],
                        'destination_desc': describe_stop(journey['stops'][-1]['StopPointRef'], stops),
                        'journey': journey,
                        'separator': seperator[row_ctr],
                        'trip': trip,
                        'departure_delay': departure_delay,
                        'arrival_delay': arrival_delay
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

    logger.info('Stop')


if __name__ == "__main__":
    main()
