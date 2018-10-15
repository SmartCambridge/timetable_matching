import calendar
import datetime
import pprint
#TODO
#import json
import collections
import re

DUMP_FORMAT = 1

WEEKDAYS = {day: i for i, day in enumerate(calendar.day_name)}
DAYNAMES = calendar.day_name
# For England & Wales - don't include Scottish Holidays
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

def as_list(thing):
    '''
    Coerce a single thing into a one element list
    '''
    if isinstance(thing, collections.Sequence) and not isinstance(thing, str):
        return thing
    return [thing]


def normalise(days):
        '''
        Convert assorted DayOfWeek representations into a plain list
        of day of the week names
        '''

        result = []
        for day in days:
            if 'To' in day:
                day_range_bounds = [WEEKDAYS[i] for i in day.split('To')]
                day_range = range(day_range_bounds[0], day_range_bounds[1] + 1)
                result += [DayOfWeek(i) for i in day_range]
            elif day == 'Weekend':
                result += [DayOfWeek(5), DayOfWeek(6)]
            else:
                result.append(DayOfWeek(day))
        return result


class DayOfWeek(object):
    def __init__(self, day):
        if isinstance(day, int):
            self.day = day
        else:
            self.day = WEEKDAYS[day]

    def __eq__(self, other):
        if type(other) == int:
            return self.day == other
        return self.day == other.day

    def __repr__(self):
        return calendar.day_name[self.day]

class DateRange(object):
    # Use this to represent the object that will later be stored in the database as a DateRangeField
    # https://docs.djangoproject.com/en/1.11/ref/contrib/postgres/fields/#django.contrib.postgres.fields.DateRangeField
    def __init__(self, element):
        self.start = datetime.datetime.strptime(element['StartDate'], '%Y-%m-%d').date()
        self.end = datetime.datetime.strptime(element['EndDate'], '%Y-%m-%d').date()

    def contains(self, date):
        return self.start <= date and (not self.end or self.end >= date)

    def __repr__(self):
        return "%s->%s" % (str(self.start), str(self.end))


class OperatingProfile(object):
    def __init__(self):

        self.regular_days = []
        self.nonoperation_days = []
        self.operation_days = []
        self.nonoperation_bank_holidays = []
        self.operation_bank_holidays = []


    def from_list(element):
        '''
        Initialise object from an xmltodict element
        '''

        this = OperatingProfile()

        # RegularDayType
        if 'RegularDayType' in element:
            if 'HolidaysOnly' in element['RegularDayType']:
                this.regular_days =  ['HolidaysOnly']
            elif 'DaysOfWeek' in element['RegularDayType']:
                week_days_element = element['RegularDayType']['DaysOfWeek']
                this.regular_days = normalise(list(week_days_element.keys()))

        # PeriodicDayType -- NOT IMPLIMENTED

        # ServicedOrganisationDayType -- NOT IMPLIMENTED

        # SpecialDaysOperation
        if 'SpecialDaysOperation' in element:
            if 'DaysOfNonOperation' in element['SpecialDaysOperation']:
                this.nonoperation_days = list(map(DateRange, as_list(element['SpecialDaysOperation']['DaysOfNonOperation']['DateRange'])))
            if 'DaysOfOperation' in element['SpecialDaysOperation']:
                this.operation_days = list(map(DateRange, as_list(element['SpecialDaysOperation']['DaysOfOperation']['DateRange'])))

        # BankHolidayOperation
        if 'BankHolidayOperation' in element:
            if 'DaysOfNonOperation' in element['BankHolidayOperation']:
                this.nonoperation_bank_holidays = list(element['BankHolidayOperation']['DaysOfNonOperation'].keys())
            if 'DaysOfOperation' in element['BankHolidayOperation']:
                this.operation_bank_holidays = list(element['BankHolidayOperation']['DaysOfOperation'].keys())

        return this


    def from_et(element):
        '''
        Initialise object from an XmlElementTree element
        '''

        this = OperatingProfile()
        if element == None:
            return this

        ns = {'n': 'http://www.transxchange.org.uk/'}
        xml_ns = re.compile(r'\{.*\}')

        for child in element:

            # RegularDayType'
            if child.tag == '{http://www.transxchange.org.uk/}RegularDayType':
                if child.find('n:HolidaysOnly', ns) is not None:
                    this.regular_days = ['HolidaysOnly']
                else:
                    days = [ xml_ns.sub('', e.tag) for e in child.findall('n:DaysOfWeek/*', ns) ]
                    this.regular_days = normalise(days)

            # Not implemented
            elif child.tag == '{http://www.transxchange.org.uk/}PeriodicDayType':
                pass

            # Not implemented
            elif child.tag == '{http://www.transxchange.org.uk/}ServicedOrganisationDayType':
                pass

            # SpecialDaysOperation
            elif child.tag == '{http://www.transxchange.org.uk/}SpecialDaysOperation':
                for range in child.findall('n:DaysOfNonOperation/n:DateRange', ns):
                    this.nonoperation_days.append(DateRange({'StartDate': range.find('n:StartDate', ns).text,
                                                             'EndDate': range.find('n:EndDate', ns).text}))
                for range in child.findall('n:DaysOfOperation/n:DateRange', ns):
                    this.operation_days.append(DateRange({'StartDate': range.find('n:StartDate', ns).text,
                                                          'EndDate': range.find('n:EndDate', ns).text}))

            # BankHolidayOperation
            elif child.tag == '{http://www.transxchange.org.uk/}BankHolidayOperation':
                for holiday in child.findall('n:DaysOfNonOperation/*', ns):
                    this.nonoperation_bank_holidays.append(xml_ns.sub('', holiday.tag))
                for holiday in child.findall('n:DaysOfOperation/*', ns):
                    this.operation_bank_holidays.append(xml_ns.sub('', holiday.tag))

            else:
                assert False, "Unrecognised <OperatingProfile> tag %s" % child.tag

        return this


    def __repr__(self):
        return (str(self.regular_days) +
            str(self.nonoperation_days) +
            str(self.operation_days) +
            str(self.nonoperation_bank_holidays) +
            str(self.operation_bank_holidays))


    def should_show(self, date):
        '''
        Should an entity with this OperatingProfile be shown (i.e.
        does it run) on this date?
        '''

        # "days of explicit non-operation should be interpreted as
        # further constraining the days of week and month of the
        # Normal Operating Profile" (3.15.2, Schema Guide 2.1)
        #...and...
        # "If conflicting dates are specified, days of non-operation
        # are given precedence (6.9.2.4, Schema Guide 2.1)
        for daterange in self.nonoperation_days:
            if daterange.contains(date):
                return False

        if date in BANK_HOLIDAYS:
            if 'AllBankHolidays' in self.nonoperation_bank_holidays:
                return False
            for bank_holiday in BANK_HOLIDAYS[date]:
                if bank_holiday in self.nonoperation_bank_holidays:
                    return False

        # "days of explicit operation should be interpreted as being
        # additive" (3.15.2, Schema Guide 2.1)
        for daterange in self.operation_days:
            if daterange.contains(date):
                return True

        if date in BANK_HOLIDAYS:
            if 'AllBankHolidays' in self.operation_bank_holidays:
                return True
            for bank_holiday in BANK_HOLIDAYS[date]:
                if bank_holiday in self.operation_bank_holidays:
                    return True

        if date.weekday() in self.regular_days:
            return True

        return False


    def defaults_from(self, defaults):
        '''
        Update this object from a second one containing defaults
        according to the rules in the schema guide (3.15.6, Schema
        Guide 2.1)
        '''

        if not self.regular_days:
            self.regular_days = defaults.regular_days
        if not self.nonoperation_days:
            self.nonoperation_days = defaults.nonoperation_days
        if not self.operation_days:
            self.operation_days = defaults.operation_days
        if not self.nonoperation_bank_holidays:
            self.nonoperation_bank_holidays = defaults.nonoperation_bank_holidays
        if not self.operation_bank_holidays:
            self.operation_bank_holidays = defaults.operation_bank_holidays

# TODO This code would need a custom DateRange searaliser
#    def to_json(self):
#        '''
#        Return the object's state as a JSON object
#        '''
#        return json.dumps({
#            'DUMP_FORMAT': DUMP_FORMAT,
#            'regular_days': self.regular_days,
#            'nonoperation_days': self.nonoperation_days,
#            'operation_days': self.operation_days,
#            'nonoperation_bank_holidays': self.nonoperation_bank_holidays,
#            'operation_bank_holidays': self.operation_bank_holidays
#        })#

#

#    def from_json(json_object):
#        '''
#        Initialise an object from its JSON representation, as returned
#        by as_json
#        '''
#        ##TODO make this ur own exception?
#        assert 'DUMP_FORMAT' in json_object and json_object['DUMP_FORMAT'] == DUMP_FORMAT
#        this = OperatingProfile()
#        this.regular_days = json_object.regular_days
#        this.nonoperation_days = json_object.nonoperation_days
#        this.operation_days = json_object.operation_days
#        this.nonoperation_bank_holidays = json-object.nonoperation_bank_holidays
#        this.operation_bank_holidays = json_object.operation_bank_holidays 
#        return this#


