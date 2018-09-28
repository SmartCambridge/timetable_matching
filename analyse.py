#!/usr/bin/env python3

"""
Produce sumamry statistics about a day's bus journeys
"""

import datetime
import logging
import sys

import pandas as pd


logger = logging.getLogger('__name__')


def sumarise(day):

    filename = 'rows-{:%Y-%m-%d}.csv'.format(day)

    data = pd.read_csv(filename)

    logger.info('There were %s matched rows', data['Type'].count())
    logger.info('There were %s journeys', data['Journey_Line'].count())
    logger.info('There were %s trips', data['Trip_Line'].count())

    type_desc = {
        '0-1': 'No journey, single trip',
        '0-*': 'No journey, multiple trips',
        '1-0': 'Single journey, no trips',
        '1-1': 'Single journey, single trip',
        '1-*': 'Single journey, multiple trips',
        '*-0': 'Multiple journeys, no trips',
        '*-1': 'Multiple journeys, one trip',
        '*-*': 'Multiple journeys, multiple trips'
    }

    types = data['Type'].value_counts()
    logger.info('Type breakdown:')
    for key, value in types.iteritems():
        logger.info('    %s: %s', type_desc[key], value)

    logger.info('Trips with departure_time %s', data['Trip_Departure'].count())
    logger.info('Trips with arival_time %s', data['Trip_Arrival'].count())

    logger.info(
        'Trips with departure_time and arrival_time %s',
        data[data['Trip_Departure'].notnull() & data['Trip_Arrival'].notnull()]['Type'].count())

    missing_trips = data[data['Trip_Line'].isnull()].groupby('Journey_Line').size()
    logger.info('Journeys with no trips, by line:')
    for key, value in missing_trips.iteritems():
        logger.info('    %s: %s', key, value)

    missing_journeys = data[data['Journey_Line'].isnull()].groupby('Trip_Line').size()
    logger.info('Trips with no journeys, by line:')
    for key, value in missing_journeys.iteritems():
        logger.info('    %s: %s', key, value)


def main():

    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

    logger.info('Start')

    try:
        day = datetime.datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
    except ValueError:
        logger.error('Failed to parse date')
        sys.exit()

    sumarise(day)

    logger.info('Stop')


if __name__ == "__main__":
    main()
