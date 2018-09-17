import calendar
import coreapi
import datetime
import logging
import os

logger = logging.getLogger('__name__')

# Where to find the real-time data
LOAD_PATH = ('/Users/jw35/icp/data/sirivm_json/data_bin/')

# Where to find the TFC API schema
API_SCHEMA = 'https://tfc-app4.cl.cam.ac.uk/api/docs/'

# Huntingdon -> Milndehall, Saffron Walden -> Earith
# BOUNDING_BOX = "-0.289078,51.933682,0.579529,52.383144"
# Bar Hill <-> Fulbourn
BOUNDING_BOX = '0.007896,52.155610,0.225048,52.267842'

# Names of days of the week and vv.
WEEKDAYS = {day: i for i, day in enumerate(calendar.day_name)}
DAYNAMES = calendar.day_name

# Dates of UK Bank Holidays
BANK_HOLIDAYS = {
    datetime.date(2017, 1, 1): ('NewYearsDay', 'AllHolidaysExceptChristmas'),
    datetime.date(2017, 4, 14): ('GoodFriday', 'AllHolidaysExceptChristmas'),
    datetime.date(2017, 4, 17): ('EasterMonday', 'HolidayMondays', 'AllHolidaysExceptChristmas'),
    datetime.date(2017, 5, 1): ('MayDay', 'HolidayMondays', 'AllHolidaysExceptChristmas'),
    datetime.date(2017, 5, 29): ('SpringBank', 'HolidayMondays', 'AllHolidaysExceptChristmas'),
    datetime.date(2017, 8, 28): ('LateSummerBankHolidayNotScotland', 'HolidayMondays', 'AllHolidaysExceptChristmas'),
    datetime.date(2017, 12, 25): ('ChristmasDay', 'Christmas'),
    datetime.date(2017, 12, 26): ('BoxingDay', 'Christmas'),

    datetime.date(2018, 1, 1): ('NewYearsDay', 'AllHolidaysExceptChristmas'),
    datetime.date(2018, 3, 30): ('GoodFriday', 'AllHolidaysExceptChristmas'),
    datetime.date(2018, 4, 2): ('EasterMonday', 'HolidayMondays', 'AllHolidaysExceptChristmas'),
    datetime.date(2018, 5, 7): ('MayDay', 'HolidayMondays', 'AllHolidaysExceptChristmas'),
    datetime.date(2018, 5, 28): ('SpringBank', 'HolidayMondays', 'AllHolidaysExceptChristmas'),
    datetime.date(2018, 8, 27): ('LateSummerBankHolidayNotScotland', 'HolidayMondays', 'AllHolidaysExceptChristmas'),
    datetime.date(2018, 12, 25): ('ChristmasDay', 'Christmas'),
    datetime.date(2018, 12, 26): ('BoxingDay', 'Christmas'),

    datetime.date(2019, 1, 1): ('NewYearsDay', 'AllHolidaysExceptChristmas'),
    datetime.date(2019, 4, 19): ('GoodFriday', 'AllHolidaysExceptChristmas'),
    datetime.date(2019, 4, 22): ('EasterMonday', 'HolidayMondays', 'AllHolidaysExceptChristmas'),
    datetime.date(2019, 5, 6): ('MayDay', 'HolidayMondays', 'AllHolidaysExceptChristmas'),
    datetime.date(2019, 5, 27): ('SpringBank', 'HolidayMondays', 'AllHolidaysExceptChristmas'),
    datetime.date(2019, 8, 26): ('LateSummerBankHolidayNotScotland', 'HolidayMondays', 'AllHolidaysExceptChristmas'),
    datetime.date(2019, 12, 25): ('ChristmasDay', 'Christmas'),
    datetime.date(2019, 12, 26): ('BoxingDay', 'Christmas'),

    datetime.date(2019, 1, 1): ('NewYearsDay', 'AllHolidaysExceptChristmas'),
    datetime.date(2019, 4, 10): ('GoodFriday', 'AllHolidaysExceptChristmas'),
    datetime.date(2019, 4, 13): ('EasterMonday', 'HolidayMondays', 'AllHolidaysExceptChristmas'),
    datetime.date(2019, 5, 4): ('MayDay', 'HolidayMondays', 'AllHolidaysExceptChristmas'),
    datetime.date(2019, 5, 25): ('SpringBank', 'HolidayMondays', 'AllHolidaysExceptChristmas'),
    datetime.date(2019, 8, 31): ('LateSummerBankHolidayNotScotland', 'HolidayMondays', 'AllHolidaysExceptChristmas'),
    datetime.date(2019, 12, 25): ('ChristmasDay', 'Christmas'),
    datetime.date(2019, 12, 26): ('BoxingDay', 'Christmas'),
    datetime.date(2019, 12, 28): ('BoxingDayHoliday', 'DisplacementHolidays')
}


def get_client():
    '''
    Return a coreapi client instance initialised with an access token.
    '''
    token = os.getenv('API_TOKEN', None)
    assert token, 'API_TOKEN environment variable not set'
    auth = coreapi.auth.TokenAuthentication(
        scheme='Token',
        token=token
    )
    client = coreapi.Client(auth=auth)
    return client


def get_stops(client, schema, bounding_box):
    '''
    Return a dictionary of all bus stops that fall inside the
    bounding_box. The dictionary key is the stop ATCOCode and
    the content of the information record returned by the API.
    '''
    stops = {}
    action = ['transport', 'stops', 'list']
    params = {'bounding_box': bounding_box, 'page_size': 500}
    page = 1
    while 1:
        logger.info("Getting stops, page %s", page)
        params['page'] = page
        api_results = client.action(schema, action, params=params)
        for result in api_results['results']:
            stops[result['atco_code']] = result
        if api_results['next'] is None:
            break
        page += 1
    logger.info('Retrieved %s stops.', len(stops))
    return stops

def update_bbox(box, lat, lng):
    if box[0] is None or lat < box[0]:
        box[0] = lat
    if box[1] is None or lng < box[1]:
        box[1] = lng
    if box[2] is None or lat > box[2]:
        box[2] = lat
    if box[3] is None or lng > box[3]:
        box[3] = lng
