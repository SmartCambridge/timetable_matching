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

import txc_helper

from util import (
    API_SCHEMA, BOUNDING_BOX, TIMETABLE_PATH, TNDS_REGIONS, get_client, get_stops
)

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger('__name__')

NS = {'n': 'http://www.transxchange.org.uk/'}


def process(filename, day, interesting_stops):
    '''
    Process one TNDS data file
    '''

    logger.debug('Processing %s', filename)

    tree = ET.parse(filename).getroot()

    # Counting on there being only one Service, Line and Operator
    # in each file...
    service = tree.find('n:Services/n:Service', NS)

    # Check the service start/end dates; bail out if out of range
    service_start_element = service.find('n:OperatingPeriod/n:StartDate', NS)
    service_start_date = datetime.datetime.strptime(service_start_element.text, '%Y-%m-%d').date()
    if day < service_start_date:
        return []

    service_end_element = service.find('n:OperatingPeriod/n:EndDate', NS)
    if service_end_element is not None:
        service_end_date = datetime.datetime.strptime(service_end_element.text, '%Y-%m-%d').date()
        if day > service_end_date:
            return []

    service_private_code = service.find('n:PrivateCode', NS).text
    service_description = service.find('n:Description', NS).text
    line_name = service.find('n:Lines/n:Line/n:LineName', NS).text

    service_op_element = service.find('n:OperatingProfile', NS)
    service_op = txc_helper.OperatingProfile.from_et(service_op_element)

    operator = tree.find('n:Operators/n:Operator', NS)
    operator_code = operator.find('n:OperatorCode', NS).text

    journeys = []

    # For each vehicle journey...
    for vjourney in tree.findall('n:VehicleJourneys/n:VehicleJourney', NS):

        journey = {
            'service': {
                'filename': filename,
                'code': service_private_code,
                'description': service_description,
                'line_name': line_name,
                'operator': operator_code,
            }
        }

        journey_op_element = vjourney.find('n:OperatingProfile', NS)
        journey_op = txc_helper.OperatingProfile.from_et(journey_op_element)
        journey_op.defaults_from(service_op)

        # Drop this journey if it isn't valid for today
        if not journey_op.should_show(day):
            continue

        journey['private_code'] = vjourney.find('n:PrivateCode', NS).text
        journey['departure_time'] = vjourney.find('n:DepartureTime', NS).text
        journey_pattern_ref = vjourney.find('n:JourneyPatternRef', NS).text
        journey['journey_pattern_ref'] = journey_pattern_ref

        # Find corresponding JoureyPattern
        journey_pattern = tree.find('n:Services/n:Service/n:StandardService/n:JourneyPattern[@id="%s"]' % journey_pattern_ref, NS)
        journey['direction'] = journey_pattern.find('n:Direction', NS).text

        # and JourneyPatternSection
        journey_pattern_section_ref = journey_pattern.find('n:JourneyPatternSectionRefs', NS).text
        journey['journey_pattern_section_ref'] = journey_pattern_section_ref
        journey_pattern_section = tree.find('n:JourneyPatternSections/n:JourneyPatternSection[@id="%s"]' % journey_pattern_section_ref, NS)

        # Get first and last stop
        origin = journey_pattern_section.find('n:JourneyPatternTimingLink[1]/n:From/n:StopPointRef', NS).text
        destination = journey_pattern_section.find('n:JourneyPatternTimingLink[last()]/n:To/n:StopPointRef', NS).text

        # Drop this journey if neither its start stop nor its end
        # stop is in the stop list
        if origin not in interesting_stops and destination not in interesting_stops:
            continue

        journey['Origin'] = {
            'Ref': origin,
            'Name': '',
            'Indicator': '',
            'Locality': '',
            'LocalityQualifier': '',
        }

        journey['Destination'] = {
            'atco_code': destination,
            'Name': '',
            'Indicator': '',
            'Locality': '',
            'LocalityQualifier': '',
        }

        # Collect all the stops.
        # TODO Collect the positions of all the stops
        # TODO Construct the bounding box of the stops
        journey['stops'] = []
        for stop_point_ref in journey_pattern_section.findall('n:JourneyPatternTimingLink/n:From/n:StopPointRef', NS):
            stop_point = stop_point_ref.text
            journey['stops'].append(stop_point)
        # And then the 'To' of the last one
        journey['stops'].append(destination)

        journeys.append(journey)

    logger.debug('%s yealded %s interesting journeys', filename, len(journeys))

    return journeys


def get_journeys(day, stops, regions):
    '''
    Retrieve timetable journeys

    Retrieve all the timetable journeys from all 'regious' that are
    valid for 'day' and which start or end at one of the stops we are
    interested in
    '''

    journeys = []

    for region in regions:

        path = os.path.join(TIMETABLE_PATH, region, '*.xml')
        logger.info('Processing from %s', path)

        for filename in glob.iglob(path):
            journeys.extend(process(filename, day, stops))

    logger.info('Got %s journeys', len(journeys))

    return journeys


def emit_journeys(day, journeys):
    '''
    Print journey details in json to 'journeys-<YYYY>-<mm>-<dd>.json'
    '''

    filename = 'journeys-{:%Y-%m-%d}.json'.format(day)
    logger.info('Outputing to %s', filename)

    with open(filename, 'w', newline='') as jsonfile:
        output = {
            'day': day.strftime('%Y/%m/%d'),
            'bounding_box': BOUNDING_BOX,
            'journeys': journeys
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
    stops = get_stops(client, schema, BOUNDING_BOX)

    # Retrieve timetable journeys
    journeys = get_journeys(day, stops, TNDS_REGIONS)

    emit_journeys(day, journeys)

    logger.info('Stop')


if __name__ == '__main__':
    main()
