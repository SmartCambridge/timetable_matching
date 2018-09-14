#!/usr/bin/env python3

import csv
import datetime
import logging
import sys

from util import (
    API_SCHEMA, BOUNDING_BOX, WEEKDAYS, DAYNAMES, BANK_HOLIDAYS,
    get_client, get_stops
)

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger('__name__')


def normalise(days):
    '''
    Convert various DayOfWeek representations into a plain list
    of day of the week names
    '''

    result = []
    for day in days:
        if 'To' in day:
            day_range_bounds = [WEEKDAYS[i] for i in day.split('To')]
            day_range = range(day_range_bounds[0], day_range_bounds[1] + 1)
            result += [DAYNAMES[i] for i in day_range]
        elif day == 'Weekend':
            result += [DAYNAMES[5], DAYNAMES[6]]
        else:
            result.append(day)
    return result


def should_show(journey, date):
    '''
    Should a journey be shown (i.e. does it run) on this date?
    '''

    # start and end dates of the underlying line

    line = journey['journey_pattern']['route']['line']

    start = datetime.datetime.strptime(line['start_date'], '%Y-%m-%d').date()
    end = datetime.datetime.strptime(line['end_date'], '%Y-%m-%d').date()

    if date < start or date > end:
        return False

    # nonopertional_days - no information

    # nonoperation bank holidays
    if date in BANK_HOLIDAYS:
        nonoperation_bank_holidays = journey['nonoperation_bank_holidays'].split(' ')
        if 'AllBankHolidays' in nonoperation_bank_holidays:
            return False
        for bank_holiday in BANK_HOLIDAYS[date]:
            if bank_holiday in nonoperation_bank_holidays:
                return False

    # opertional_days - no information

    # operation bank holidays

    if date in BANK_HOLIDAYS:
        operation_bank_holidays = journey['operation_bank_holidays'].split(' ')
        if 'AllBankHolidays' in operation_bank_holidays:
            return True
        for bank_holiday in BANK_HOLIDAYS[date]:
            if bank_holiday in operation_bank_holidays:
                return True

    # Normal days of the week

    # Assume an empty days_of_week means every day and that otherwise
    # it contains a space-seperated list of capitalised day names
    days_of_week = journey['days_of_week']
    day_list = days_of_week.split(' ')
    dow = date.strftime('%A')
    if days_of_week == '' or dow in day_list:
        return True

    return False


def get_journeys(client, schema, year, month, day, stops):
    '''
    Retrieve all timetabled journeys for year/month/day that have
    origin or destination stops in our stops list (and so fall within
    our bounding box)
    '''

    journeys = []

    date = datetime.date(year, month, day)

    action = ['transport', 'journeys', 'list']
    params = {'page_size': 250}
    page = 1
    raw_journeys = 0
    while 1:
        logger.info('Getting journeys, page %i', page)
        params['page'] = page
        api_results = client.action(schema, action, params=params)
        for result in api_results['results']:
            raw_journeys += 1

            stops_list = result['journey_pattern']['route']['stops_list'].split(',')
            first_stop = stops_list[0]
            last_stop = stops_list[-1]
            if first_stop not in stops and last_stop not in stops:
                continue

            if not should_show(result, date):
                continue

            journeys.append(result)

        if api_results['next'] is None:
            break
        page += 1
        logger.info('Raw journeys so far: %i', raw_journeys)
        logger.info('Interesting journeys so far: %i', len(journeys))
        if len(journeys) > 10:
            break
    logger.info('Retrieved %i journeys.', len(journeys))
    return journeys


def emit_journeys(journeys):
    '''
    Print journey details in CSV
    '''

    output = csv.writer(sys.stdout)
    heading = (
        'JourneyID',
        'OriginRefRef',
        'OriginName',
        'OriginLocality',
        'DestinationRef',
        'DestinationName',
        'DestinationLocality',
        'DepartureTime',
        'LineName',
        'Operator',
        'Direction',
        'RegulardaysOfWeek',
        'BankHolidayOperation',
        'BankHolidayNonOperation',
        'StartDate',
        'EndDate',
        )
    output.writerow(heading)

    for journey in journeys:

        row = (
            journey['id'],
            journey['timetable'][0]['stop']['atco_code'],
            journey['timetable'][0]['stop']['common_name'],
            journey['timetable'][0]['stop']['locality_name'],
            journey['timetable'][-1]['stop']['atco_code'],
            journey['timetable'][-1]['stop']['common_name'],
            journey['timetable'][-1]['stop']['locality_name'],
            journey['departure_time'],
            journey['journey_pattern']['route']['line']['line_name'],
            journey['journey_pattern']['route']['line']['operator']['code'],
            journey['journey_pattern']['direction'],
            journey['days_of_week'],
            journey['operation_bank_holidays'],
            journey['nonoperation_bank_holidays'],
            journey['journey_pattern']['route']['line']['start_date'],
            journey['journey_pattern']['route']['line']['end_date'],

        )
        output.writerow(row)


def main():

    # Setup a coreapi client
    client = get_client()
    schema = client.get(API_SCHEMA)

    # Get the list of all the stops we are interested in
    stops = get_stops(client, schema, BOUNDING_BOX)

    # Get the list of all the stops we are interested in
    journeys = get_journeys(client, schema, 2018, 9, 5, stops)

    emit_journeys(journeys)


if __name__ == "__main__":
    main()
