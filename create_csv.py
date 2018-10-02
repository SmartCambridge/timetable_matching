#!/usr/bin/env python3

"""
Output merged and expanded trip/journey records to CVS.
"""

import csv
import datetime
import json
import logging
import sys

import isodate

logger = logging.getLogger('__name__')


def load_rows(day):

    filename = 'rows-{:%Y-%m-%d}.json'.format(day)
    logger.info('Reading %s', filename)

    with open(filename, 'r', newline='') as jsonfile:
        merged = json.load(jsonfile)

    logger.info('Done')

    return merged


def format_minutes(seconds):
    '''
    Format a datetime in minuites and fractions thereof
    '''
    if seconds is None:
        return ''
    return '{0:.2f}'.format(seconds/60)


def emit_csv(day, rows):
    '''
    Emit partial row details in CSV to 'rows-<YYYY>-<mm>-<dd>.csv'
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
            'From_Description',
            'To',
            'To_Description',
            'Journey_Line',
            'Journey_Operator_Code',
            'Journey_Operator_Name',
            'Journey_Direction',
            'Journey_Departure',
            'Journey_Arrival',
            ' ',
            'Trip_Line',
            'Trip_Operator',
            'Trip_Direction',
            'Trip_Vehicle',
            'Trip_Departure',
            'Trip_Arrival',
            'Delay_Departure',
            'Delay_Arrival',
        ))

        # For each result row
        for row in rows:

            journey = row['journey']
            first = last = None
            if journey is None:
                journey_fields = ('', '', '', '', '', '')
            else:
                first = isodate.parse_datetime(journey['stops'][0]['time'])
                last = isodate.parse_datetime(journey['stops'][-1]['time'])
                journey_fields = (
                    journey['Service']['LineName'],
                    journey['Service']['OperatorCode'],
                    journey['Service']['OperatorName'],
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

            time = isodate.parse_datetime(row['time'])

            r = (
                    (
                        row['type'],
                        time.strftime("%Y-%m-%d"),
                        time.strftime("%H:%M"),
                        row['origin'],
                        row['origin_desc'],
                        row['destination'],
                        row['destination_desc'],
                    ) +
                    journey_fields +
                    (
                        row['separator'],
                    ) +
                    trip_fields +
                    (
                        format_minutes(row['departure_delay']),
                        format_minutes(row['arrival_delay'])
                    )
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

    row_data = load_rows(day)

    emit_csv(day, row_data['rows'])

    logger.info('Stop')


if __name__ == "__main__":
    main()
