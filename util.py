
import coreapi
import logging
import os

logger = logging.getLogger('__name__')

# Where to find the real-time data
LOAD_PATH = os.getenv('SIRIVM_PATH', '/media/tfc/sirivm_json/data_bin/')

# Where to find the timetable data
TIMETABLE_PATH = os.getenv('TIMETABLE_PATH', '/media/tfc/tnds/sections/')

# Where to find the TFC API schema
API_SCHEMA = os.getenv('API_SCHEMA', 'https://smartcambridge.org/api/docs/')

# Default is roughly Bar Hill <-> Fulbourn
BOUNDING_BOX = os.getenv('BOUNDING_BOX', '0.007896,52.155610,0.225048,52.267842')

# TNDS regious to process
TNDS_REGIONS = os.getenv('TNDS_REGIONS', 'EA SE').split()

API_TOKEN = os.getenv('API_TOKEN', None)
assert API_TOKEN, 'API_TOKEN environment variable not set'


def get_client():
    '''
    Return a coreapi client instance initialised with an access token.
    '''
    auth = coreapi.auth.TokenAuthentication(
        scheme='Token',
        token=API_TOKEN
    )
    client = coreapi.Client(auth=auth)
    return client


def get_stops(client, schema, bounding_box):
    '''
    Return a dictionary of all bus stops that fall inside the
    bounding_box. The dictionary key is the stop ATCOCode and
    the content of the information record returned by the API.
    '''
    logger.info("Getting stops in %s", bounding_box)
    stops = {}
    action = ['transport', 'stops', 'list']
    params = {'bounding_box': bounding_box, 'page_size': 500}
    page = 1
    while 1:
        logger.debug("Getting stops, page %s", page)
        params['page'] = page
        api_results = client.action(schema, action, params=params)
        for result in api_results['results']:
            stops[result['atco_code']] = result
        if api_results['next'] is None:
            break
        page += 1
    logger.info('Retrieved %s stops.', len(stops))
    return stops


def update_bbox(box, lng, lat):
    '''
    Update a bounding box

    Update a bounding box represented as (min longitude, min latitude,
    max longitude, max latitude) with a new point
    '''

    if box[0] is None or lng < box[0]:
        box[0] = lng
    if box[1] is None or lat < box[1]:
        box[1] = lat
    if box[2] is None or lng > box[2]:
        box[2] = lng
    if box[3] is None or lat > box[3]:
        box[3] = lat


def lookup(client, schema, stop, stops1, stops2):
    '''
    Lookup details of a bus stop by ATCOCode

    Find stop details in stops1 or in stops2, and failing that
    get the details via the client and cache the result in stops2
    '''

    if stop in stops1:
        return stops1[stop]
    if stop in stops2:
        return stops2[stop]
    try:
        action = ['transport', 'stop', 'read']
        params = {'atco_code': stop}
        logger.debug("Getting stop details for %s", stop)
        result = client.action(schema, action, params=params)
    except coreapi.exceptions.ErrorMessage as e:
        logger.error("Failed to lookup stop %s: %s", stop, e)
        result = {}

    stops2[result['atco_code']] = result
    return result
