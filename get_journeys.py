#!/usr/bin/env python3

'''
Retrieve timetable information

Walk one or more TNDS timetable files and emit all its
VehicleJourneys as CSV
'''

import datetime
import glob
import json
import logging
import os
import sys
import xml.etree.ElementTree as ET

import isodate
import txc_helper

from util import (
    API_SCHEMA, BOUNDING_BOX, TIMETABLE_PATH, TNDS_REGIONS, get_client,
    get_stops, lookup
)

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger('__name__')

NS = {'n': 'http://www.transxchange.org.uk/'}


def process(filename, day, interesting_stops):
    '''
    Process one TNDS data file
    '''

    logger.debug('Processing %s', filename)

    stops = set()
    service_cache = {}

    tree = ET.parse(filename).getroot()

    journeys = []

    # Process each VehicleJourney in the file
    for vehicle_journey in tree.findall('n:VehicleJourneys/n:VehicleJourney', NS):

        # Find and process the journey's 'parent' service
        #
        # This is probably inefficient, since TNDS data files seem only
        # ever to contain one service, but at least this avoids having to
        # make that assumption
        service_ref = vehicle_journey.find('n:ServiceRef', NS).text
        if service_ref in service_cache:
            service = service_cache[service_ref]
        else:
            service = tree.find("n:Services/n:Service[n:ServiceCode='%s']" % service_ref, NS)
            service_cache[service_ref] = service

        # Check the service start/end dates; bail out if out of range
        service_start = service.find('n:OperatingPeriod/n:StartDate', NS)
        service_start_date = datetime.datetime.strptime(service_start.text, '%Y-%m-%d').date()
        if day < service_start_date:
            continue

        service_end = service.find('n:OperatingPeriod/n:EndDate', NS)
        if service_end is not None:
            service_end_date = datetime.datetime.strptime(service_end.text, '%Y-%m-%d').date()
            if day > service_end_date:
                continue

        # Process the Service and Journey OperatingProfile; bail out
        # if this isn't for us
        service_op_element = service.find('n:OperatingProfile', NS)
        service_op = txc_helper.OperatingProfile.from_et(service_op_element)

        journey_op_element = vehicle_journey.find('n:OperatingProfile', NS)
        journey_op = txc_helper.OperatingProfile.from_et(journey_op_element)
        journey_op.defaults_from(service_op)

        if not journey_op.should_show(day):
            continue

        # Extract Operator
        #
        # As with Service, this is probably inefficient since TNDS files
        # only ever seem to contain one Operator, but whatever
        operator_id = service.find('n:RegisteredOperatorRef', NS).text
        operator = tree.find('n:Operators/n:Operator[@id="%s"]' % operator_id, NS)

        # Extract departure time
        departure_time = vehicle_journey.find('n:DepartureTime', NS).text
        departure_time_time = datetime.datetime.strptime(departure_time, '%H:%M:%S').time()
        departure_timestamp = datetime.datetime.combine(day, departure_time_time)

        # Find corresponding JourneyPattern
        journey_pattern_id = vehicle_journey.find('n:JourneyPatternRef', NS).text
        journey_pattern = tree.find('n:Services/n:Service/n:StandardService/n:JourneyPattern[@id="%s"]' % journey_pattern_id, NS)

        # and loop over the included JourneyPatternSections
        #
        # As with Service and Operator, this is probably inefficient since
        # TNDS files only ever seem to contain a single JourneyPatternSection
        # in each JourneyPattern
        journey_pattern_section_ids = []
        journey_stops = []
        time = departure_timestamp
        for journey_pattern_section_id_element in journey_pattern.findall('n:JourneyPatternSectionRefs', NS):

            journey_pattern_section_id = journey_pattern_section_id_element.text
            journey_pattern_section_ids.append(journey_pattern_section_id)
            journey_pattern_section = tree.find('n:JourneyPatternSections/n:JourneyPatternSection[@id="%s"]' % journey_pattern_section_id, NS)

            for link in journey_pattern_section.findall('n:JourneyPatternTimingLink', NS):

                # Append details for the from stop
                From = link.find('n:From', NS)
                stop = {
                    'StopPointRef': From.find('n:StopPointRef', NS).text,
                    'Order': From.get('SequenceNumber'),
                    'Activity': From.find('n:Activity', NS).text,
                    'TimingStatus': From.find('n:TimingStatus', NS).text,
                    'time': time.isoformat()
                }

                # Work out the time at the next stop
                run_time = link.find('n:RunTime', NS).text
                stop['run_time'] = run_time
                run_time_duration = isodate.parse_duration(run_time)
                time += run_time_duration

                to = link.find('n:To', NS)
                wait_time = to.find('n:WaitTime')
                if wait_time is not None:
                    stop['wait_time'] = wait_time.text
                    wait_time_duration = isodate.parse_duration(wait_time.text)
                    time += wait_time_duration

                journey_stops.append(stop)

            # Append details for the final stop
            stop = {
                'StopPointRef': to.find('n:StopPointRef', NS).text,
                'Order': to.get('SequenceNumber'),
                'Activity': to.find('n:Activity', NS).text,
                'TimingStatus': to.find('n:TimingStatus', NS).text,
                'time': time.isoformat()
            }

            journey_stops.append(stop)

        # Drop this journey if neither its start stop nor its end
        # stop is in the stop list
        if (journey_stops[0]['StopPointRef'] not in interesting_stops and
           journey_stops[-1]['StopPointRef'] not in interesting_stops):
            continue

        # Populate the result
        journey = {
            'file': filename,
            'PrivateCode': vehicle_journey.find('n:PrivateCode', NS).text,
            'VehicleJourneyCode': vehicle_journey.find('n:VehicleJourneyCode', NS).text,
            'DepartureTime': departure_timestamp.isoformat(),
            'Service': {
                'PrivateCode': service.find('n:PrivateCode', NS).text,
                'ServiceCode': service.find('n:ServiceCode', NS).text,
                'Description': service.find('n:Description', NS).text,
                'LineName': service.find('n:Lines/n:Line/n:LineName', NS).text,
                'OperatorCode': operator.find('n:OperatorCode', NS).text,
            },
            'JourneyPatternId': journey_pattern_id,
            'Direction': journey_pattern.find('n:Direction', NS).text,
            'JourneyPatternSectionIds': journey_pattern_section_ids,
            'stops': journey_stops,
        }

        journeys.append(journey)

        stops.update(set([s['StopPointRef'] for s in journey_stops]))

    logger.debug('%s yealded %s interesting journeys', filename, len(journeys))

    return journeys, stops


def get_journeys(day, interesting_stops, regions):
    '''
    Retrieve timetable journeys

    Retrieve all the timetable journeys from all 'regious' that are
    valid for 'day' and which start or end at one of the stops we are
    interested in
    '''

    journey_list = []
    stops_list = set()

    try:

        for region in regions:

            path = os.path.join(TIMETABLE_PATH, region, '*.xml')
            logger.info('Processing from %s', path)
            j = s =0

            for filename in glob.iglob(path):
                journeys, stops = process(filename, day, interesting_stops)
                journey_list.extend(journeys)
                stops_list.update(stops)
                j += len(journeys)
                s += len(stops)

            logger.info('Got %s journeys referencing %s stops', j, s)

    except KeyboardInterrupt:
        pass

    logger.info('Got total of %s journeys referencing %s stops', len(journey_list), len(stops_list))

    return journey_list, stops_list


def expand_stops(client, schema, stop_ids, interesting_stops):
    '''
    Lookup full details of all stops used
    '''

    logger.info('Looking up %s stops', len(stop_ids))

    other_stops = {}
    results = {}
    for stop in stop_ids:
        results[stop] = lookup(client, schema, stop, interesting_stops, other_stops)

    logger.info('Looked up %s stops, needed %s extra', len(results), len(other_stops))

    return results


def emit_journeys(day, journeys, stops):
    '''
    Print journey details in json to 'journeys-<YYYY>-<mm>-<dd>.json'
    '''

    filename = 'journeys-{:%Y-%m-%d}.json'.format(day)
    logger.info('Outputing to %s', filename)

    with open(filename, 'w', newline='') as jsonfile:
        output = {
            'day': day.strftime('%Y-%m-%d'),
            'bounding_box': BOUNDING_BOX,
            'journeys': journeys,
            'stops': stops,
        }
        json.dump(output, jsonfile, indent=4, sort_keys=True)

    logger.info('Output done')


def main():

    logger.info('Start')

    try:
        day = datetime.datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
    except ValueError:
        logger.error('Failed to parse date')
        sys.exit()

    # Setup a coreapi client
    client = get_client()
    schema = client.get(API_SCHEMA)

    # Get the list of all the stops we are interested in
    interesting_stops = get_stops(client, schema, BOUNDING_BOX)

    # Retrieve timetable journeys
    journeys, stop_ids = get_journeys(day, interesting_stops, TNDS_REGIONS)

    stops = expand_stops(client, schema, stop_ids, interesting_stops)

    emit_journeys(day, journeys, stops)

    logger.info('Stop')


if __name__ == '__main__':
    main()
