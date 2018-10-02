#!/usr/bin/env python3

"""
Produce sumamry statistics about a day's bus journeys
"""

import datetime
import sys

import pandas as pd
import numpy as np


def sumarise(day):

    filename = 'rows-{:%Y-%m-%d}.csv'.format(day)

    data = pd.read_csv(filename)

    title = "Matching summary for {:%Y-%m-%d (%A)}".format(day)
    print(title)
    print("="*len(title))
    print()

    print('Total matched rows: {0}'.format(data['Type'].count()))
    print('Journeys:           {0}'.format(data['Journey_Line'].count()))
    print('Trips:              {0}'.format(data['Trip_Line'].count()))
    print()

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
    print('Type breakdown:')
    for key, value in types.iteritems():
        print('    {0:5}: {1}'.format(value, type_desc[key]))
    print()

    missing_trips = data[data['Trip_Line'].isnull()].groupby('Journey_Line').size()
    trips = data.groupby('Journey_Line').size()

    print('Journeys with no Trips, by Line:')
    for key, value in missing_trips.iteritems():
        print('    {0:5}: {1}'.format(value, key))
    print()

    trips = data.groupby('Journey_Line').size()
    print('All Journeys, by Line:')
    for key, value in trips.iteritems():
        print('    {0:5}: {1}'.format(value, key))
    print()

    missing_trips = data[data['Trip_Line'].isnull()].groupby('Journey_Operator').size()
    print('Journeys with no Trips, by Operator:')
    for key, value in missing_trips.iteritems():
        print('    {0:5}: {1}'.format(value, key))
    print()

    missing_journeys = data[data['Journey_Line'].isnull()].groupby('Trip_Line').size()
    print('No journeys but one or more Trips, by Line:')
    for key, value in missing_journeys.iteritems():
        print('    {0:5}: {1}'.format(value, key))
    print()

    missing_journeys = data[data['Journey_Line'].isnull()].groupby('Trip_Operator').size()
    print('No journeys but one or more Trips, by Operator:')
    for key, value in missing_journeys.iteritems():
        print('    {0:5}: {1}'.format(value, key))
    print()

    print(
        'Trips with departure_time:                       {0}'.format(
         data['Trip_Departure'].count()))
    print(
        'Trips with arival_time:                          {0}'.format(
         data['Trip_Arrival'].count()))
    print(
        'Trips with both departure_time and arrival_time: {0}'.format(
         data[data['Trip_Departure'].notnull() & data['Trip_Arrival'].notnull()]['Type'].count()))
    print()

    print(
        'Rows with departure delay:                        {0}'.format(
         data['Delay_Departure'].count()))
    print(
        'Rows with ariveal delay                           {0}'.format(
         data['Delay_Arrival'].count()))
    print(
        'Rows with both departure delay and arrival delay: {0}'.format(
         data[data['Delay_Departure'].notnull() & data['Delay_Arrival'].notnull()]['Type'].count()))
    print()

    bin_limits = [-np.inf, -1440, -120, -60, -30, -20,  -10, -5, 0, 5, 10, 20, 30, 60, 120, 1440, np.inf]
    labels = [
        "More than a day early",
        "More than 2 hours early",
        "More than 1 hour early",
        "More than 30 minutes early",
        "More than 20 minutes early",
        "More than 10 minutes early",
        "More than 5 minutes early",
        "Less than 5 minutes early",
        "Less than 5 minutes late",
        "More than 5 minutes late",
        "More than 10 minutes late",
        "More than 20 minutes late",
        "More than 30 minutes late",
        "More than 1 hour late",
        "More than 2 hours late",
        "More than a day late",
    ]

    print('Distribution of departure delays:')
    bins = pd.cut(data['Delay_Departure'], bin_limits, labels=labels)
    for key, value in (data.groupby(bins)['Delay_Departure'].agg('count')).iteritems():
        print('    {0:5}: {1}'.format(value, key))
    print()

    print('Distribution of arrival delays:')
    bins = pd.cut(data['Delay_Arrival'], bin_limits, labels=labels)
    for key, value in (data.groupby(bins)['Delay_Arrival'].agg('count')).iteritems():
        print('    {0:5}: {1}'.format(value, key))


def main():

    try:
        day = datetime.datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
    except ValueError:
        print('Failed to parse date', out=sys.stdout)
        sys.exit()

    sumarise(day)


if __name__ == "__main__":
    main()
