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

stops_cache = {}


def expand_stop(tree, stop_point_ref):
    '''
    Given a StopPointRef, retrieve a dictionary containing all the
    available StopPoint information
    '''
    logger.debug(stop_point_ref)
    try:
        stop = stops_cache[stop_point_ref]
        logger.debug('stops_cache HIT')
        return stop
    except KeyError:
        logger.debug('stops_cache MISS')
        stop = tree.find("n:StopPoints/n:AnnotatedStopPointRef[n:StopPointRef='%s']" % stop_point_ref, NS)
        result = {'StopPointRef': stop_point_ref}
        for name in 'CommonName', 'Indicator', 'LocalityName', 'LocalityQualifier':
            logger.debug(name)
            element = stop.find('n:%s' % name, NS)
            logger.debug(element)
            if element is not None:
                logger.debug("GOT IT %s", element.text)
                result[name] = element.text
        stops_cache[stop_point_ref] = result
        logger.debug(repr(result))
        return result


def process(filename, day, interesting_stops):
    '''
    Process one TNDS data file
    '''

    logger.debug('Processing %s', filename)

    # Clear the stops_cache so we only use consistent information from one file

    tree = ET.parse(filename).getroot()

    journeys = []

    # Process each VehicleJourney in the file
    for vehicle_journey in tree.findall('n:VehicleJourneys/n:VehicleJourney', NS):

        logger.debug(filename)
        logger.debug(vehicle_journey.find('n:PrivateCode', NS).text)

        # Find and process the journey's 'parent' service
        #
        # This is probably inefficient, since TNDS data files seem only
        # ever to contain one service, but at least this avoids having to
        # make that assumption
        service_ref = vehicle_journey.find('n:ServiceRef', NS).text
        service = tree.find("n:Services/n:Service[n:ServiceCode='%s']" % service_ref, NS)

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

        # Find corresponding JourneyPattern
        journey_pattern_id = vehicle_journey.find('n:JourneyPatternRef', NS).text
        journey_pattern = tree.find('n:Services/n:Service/n:StandardService/n:JourneyPattern[@id="%s"]' % journey_pattern_id, NS)

        # and loop over the included JourneyPatternSection
        #
        # As with Service and Operator, this is probably inefficient since
        # TNDS files only ever seem to contain a single JourneyPatternSection
        # in each JourneyPattern
        journey_pattern_section_ids = []
        journey_stops = []
        for journey_pattern_section_id_element in journey_pattern.findall('n:JourneyPatternSectionRefs', NS):
            journey_pattern_section_id = journey_pattern_section_id_element.text
            journey_pattern_section_ids.append(journey_pattern_section_id)
            journey_pattern_section = tree.find('n:JourneyPatternSections/n:JourneyPatternSection[@id="%s"]' % journey_pattern_section_id, NS)

            for stop_point in journey_pattern_section.findall('n:JourneyPatternTimingLink/n:From/n:StopPointRef', NS):
                journey_stops.append(expand_stop(tree, stop_point.text))
                very_last_stop = journey_pattern_section.find('n:JourneyPatternTimingLink[last()]/n:To/n:StopPointRef', NS).text
            journey_stops.append(expand_stop(tree, very_last_stop))

        # Drop this journey if neither its start stop nor its end
        # stop is in the stop list
        if (journey_stops[0]['StopPointRef'] not in interesting_stops and
            journey_stops[-1]['StopPointRef'] not in interesting_stops):
            continue

        # Populate the result
        journey = {
            'file': filename,
            'PrivateCode': vehicle_journey.find('n:PrivateCode', NS).text,
            'DepartureTime': vehicle_journey.find('n:DepartureTime', NS).text,
            'Direction': journey_pattern.find('n:Direction', NS).text,
            'JourneyPatternId': journey_pattern_id,
            'JourneyPatternSectionIds': journey_pattern_section_ids,
            'Service': {
                'PrivateCode': service.find('n:PrivateCode', NS).text,
                'Description': service.find('n:Description', NS).text,
                'LineName': service.find('n:Lines/n:Line/n:LineName', NS).text,
                'OperatorCode': operator.find('n:OperatorCode', NS).text,
            },
            'stops': journey_stops,
        }

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

    try:

        for region in regions:

            path = os.path.join(TIMETABLE_PATH, region, '*.xml')
            logger.info('Processing from %s', path)

            for filename in glob.iglob(path):
                journeys.extend(process(filename, day, stops))

    except KeyboardInterrupt:
        pass

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
