Matching timetabled bus journeys to archived real-time bus trips
================================================================

The scripts in this repository attempt to match real-time bus position information against timetabled journeys and to present the results as a table from which trips and journeys can be viewed on a map.

The processing takes place in several phases. These can be run individually, with intermediate output saved in JSON files, or in a single pass by `do_everything.py` which uses the individual scripts as libraries and which only saves the final analysed files.

Processing is based on 24 hour periods from midnight. This is problematic for journeys and trips that span midnight.

Processing is limited to journeys and trips that start or end within a bounding box. The default extends roughly from Bar Hill in the north-west to Fulbourn in the south-east and includes all journeys that might be considered to serve Cambridge. This area contains about 870 bus stops.

Most scripts in this suite take a date (as `YYYY-MM-DD`) as a single command-line argument.

Initial setup
=============

**Note** that this processing requires access to archived SIRI-VM real-time bus data in the JSON format used by the University of Cambridge adaptive Cities Project.

1. Clone this repository
2. Obtain a copy of the `txc_helper` module from `https://github.com/jw35/operating_profile`
3. If required, create and activate a Python virtual environment
4. Install dependencies: `pip install -r requirements.txt`
5. Make a copy of `setup_environment.skel` as `setup_environment` and edit it to suite
6. `source setup_environment`

Processing steps
================

Extract journeys
----------------

All timetabled vehicle journeys for a particular day are extracted from the TNDS data, taking account of their associated service's start and end dates, and of the operating profile of the associated service and of the journey itself. Journey's that do not run on the day on question are ignored, as are journeys that neither start nor end within the configured bounding box. Journey patterns are expanded to include a timestamp for the journey at each stop.

The extraction is performed by `get_journeys.py`, which emits `journeys-<yyy>-<mm>-<dd>.json`. In addition to metadata, this file contains a list of every possible journey:

```
{
    "bounding_box": "0.007896,52.155610,0.225048,52.267842",
    "day": "2018-10-13",
    "journeys": [
        {
            "DepartureTime": "2018-10-13T18:00:00+01:00",
            "Direction": "inbound",
            "JourneyPatternId": "JP_20-1-A-y08-1-1-R-1",
            "JourneyPatternSectionIds": [
                "JPS_20-1-A-y08-1-1-1-R"
            ],
            "PrivateCode": "ea-20-1-A-y08-1-175-T2",
            "Service": {
                "Description": "Arbury - City Centre - Addenbrookes - Cherry Hinton - Fulbourn",
                "LineName": "1|Citi",
                "OperatorCode": "SCCM",
                "OperatorName": "Stagecoach in Cambridge",
                "PrivateCode": "20-1-A-y08-1",
                "ServiceCode": "20-1-A-y08-1"
            },
            "VehicleJourneyCode": "VJ_20-1-A-y08-1-175-T2",
            "file": "/Users/jon/icp/data/TNDS_bus_data/sections/EA/ea_20-1-A-y08-1.xml",
            "stops": [
                {
                    "Activity": "pickUp",
                    "Order": "1",
                    "StopPointRef": "0500SFULB020",
                    "TimingStatus": "PTP",
                    "run_time": "PT0S",
                    "time": "2018-10-13T18:00:00+01:00"
                },
                <...>
            ],
        },
        <...>
    ]
}
```

Alternatively, this processing can be done by `do_everything.py` which keeps intermediate results in memory.

It yields about 2500 journeys.

Extract trips
-------------

Position records contain repeating data relating to a particular bus trip: `DestinationName`, `DestinationRef`, `DirectionRef`, `LineRef`, `OperatorRef`, `OriginAimedDepartureTime`, `OriginName`, `OriginRef`, `VehicleRef`, together with data relating to the position observation: `Bearing`, `Delay`, `Latitude`, `Longitude`, `RecordedAtTime`.

All position records for a particular day are processed. Positions are amalgamated into trips based on common values of `DestinationRef`, `DirectionRef`, `LineRef`, `OperatorRef`, `OriginAimedDepartureTime`, `OriginRef` and `VehicleRef`. Trips with neither an origin nor a destination within the configured bounding box are ignored. Trips with an `OriginAimedDepartureTime` not on the day in question are ignored (typically 10-12 trips which started on the previous day; also potentially early position reports for trips starting the following day). Trips frequently start well before their origin and/or extend beyond their destination, due to 'Out of service' legs needed to provision the service.

This process yield about 2100 trips.

An attempt is made to derive an actual departure time for the origin stop and an arrival time for the destination stop. The algorithm is as follows:

* **Departure time** is the timestamp of the final position report within 50m of the origin stop after the first time the bus has been within 50m of the stop. Only the first time this happens is considered to allow for situations such as in Cambourne where buses re-pass their origin stop later in their journey.

* **Arrival time** is the timestamp of the first position report that is within 50m of the destination stop. If there is no such position report, arrival time is taken from the final position report of the trip if that is within 200m of the destination stop. The latter step tries to allow for the fact that many trips stop short of their destination, probably because the driver has indicated that his vehicle is already undertaking its next scheduled journey.

This process yields departure times for about 2000 trips, arrival times for about 1500 trips, and both for about 1300 trips.

This processing is performed by `get_trips.py`, which emits `trips-<yyy>-<mm>-<dd>.json`. In addition to metadata, this contains a list of all extracted trips:

```
{
    "bounding_box": "0.007896,52.155610,0.225048,52.267842",
    "day": "2018-10-13",
    "trips": [
        {
            "DestinationName": "Telegraph Street",
            "DestinationRef": "0500SCOTT025",
            "DestinationStop": {
                "atco_code": "0500SCOTT025",
                "common_name": "Telegraph Street",
                "id": "0500SCOTT025",
                "indicator": "opp",
                "lat": 52.2858098724,
                "latitude": 52.2858098724,
                "lng": 0.12808762701,
                "locality_name": "Cottenham",
                "longitude": 0.12808762701,
                "naptan_code": "CMBDWATD",
                "stop_id": "0500SCOTT025"
            },
            "DirectionRef": "OUTBOUND",
            "LineRef": "8",
            "OperatorRef": "SCCM",
            "OriginAimedDepartureTime": "2018-10-13T00:15:00+01:00",
            "OriginName": "Emmanuel St Stop E1",
            "OriginRef": "0500CCITY487",
            "OriginStop": {
               <...>
            },
            "VehicleRef": "SCCM-19596",
            "arrival_position": 147,
            "bbox": [
                "0.1030410",
                "52.2040825",
                "0.1593890",
                "52.2884941"
            ],
            "departure_position": 52,
            "positions": [
                {
                    "Bearing": "294",
                    "Delay": "PT0S",
                    "Latitude": "52.2054596",
                    "Longitude": "0.1240630",
                    "RecordedAtTime": "2018-10-12T23:59:48+01:00"
                },
                <...>
            ]
        },
        <...>
    ]
}
```

Alternatively, the processing can be done by `do_everything.py` which keeps intermediate results in memory.

Match journeys and trips
------------------------

Both journeys and trips contain information on first and last stop, first stop departure time, direction, line (i.e. bus route), and operator. The codings for line and operator are not consistent between the two data sources, and direction is implied by first and last stop. This leaves first stop, last stop and first stop departure time by which the two can be matched.

Doing so results in about 2000 one-to-one (`1-1`) matches. The alternative outcomes are:

* **Zero journeys but a single trip** (`0-1`). Typically about 30/day of these, of which most are the open topped tour bus which does not appear in the timetable. Most of the remainder are the result of minor differences in destination stop for late-evening services (e.g. Drummer Street Stop D3 vs. Emmanuel Street Stop E4).

* **Zero journeys with multiple trips** (`0-*`). Not normally observed.

* **Single journey but zero corresponding trips** (`1-0`) Typically about 300/day. About 75 of these correspond to operators who do not appear to ever provide real-time data. Some of the rest probably represent vehicles with defective positioning systems. The rest are presumably journeys that simply did not take place.

* **Single journey with multiple trips** (`1-*`) Typically about 30 of these, falling into one of three categories: journeys where the vehicle apparently changed part way through the journey; journeys where a second vehicle briefly claimed to be servicing the same journey as the first; journeys where a second vehicle claims to be performing all or most of the journey of the first one but clear is not, based on position or timing. The latter two cases may be explained by someone, probably the driver, associating an incorrect journey with a particular vehicle.

* **Multiple journeys with zero, 1, or multiple trips** (`*-0`, `*-1`, `*-*`) These are very rare and normally appear to be errors in the timetable.

This processing is performed by `merge.py` which reads `journeys-<yyy>-<mm>-<dd>.json` and `trips-<yyy>-<mm>-<dd>.json` and emits `merged-<yyy>-<mm>-<dd>.json`. In addition to metadata, this includes a list where each row contains:

* Zero or more matching journeys
* Zero or more matching trips
* An indicator of the cardinality of the match

```
{
    "bounding_box": "0.007896,52.155610,0.225048,52.267842",
    "day": "2018-10-13",
    "merged": [
        {
            "journeys": [
                {
                	...
                },
                ...
            ],
            "trips": [
                {
                	...
               	},
                ...
            ],
            "type": "1-1"
        },
        ...
    ]
}
```

Alternatively, the processing can be done by `do_everything.py` which keeps intermediate results in memory.

Lookup full stop information
----------------------------

In the merged data, calling points in journeys are identified by NAPTAN 'ATCO' codes. This step generates a lookup table between ATCO codes and other stop information, such as the stop's 'common name' and 'locality'. This step protects against changes in the NAPTAN stop data in the future.

This processing is performed by `extract_stops.py` which reads `merged-<yyy>-<mm>-<dd>.json`, or by `do_everything.py`. Both emit `stops-<yyy>-<mm>-<dd>.json`. In addition to metadata, this includes a simple list:

```
{
    "bounding_box": "0.007896,52.155610,0.225048,52.267842",
    "day": "2018-10-13",
    "stops": {
        "021026141": {
            "atco_code": "021026141",
            "common_name": "Church Lane",
            "id": "021026141",
            "indicator": "opp",
            "lat": 52.1098471995,
            "latitude": 52.1098471995,
            "lng": -0.1650802786,
            "locality_name": "Wrestlingworth",
            "longitude": -0.1650802786,
            "naptan_code": "ahlajgwg",
            "stop_id": "021026141"
        },
        ...
    ]
}
```

Expand matched journeys and trips
---------------------------------

This step expands the merged data into what you would expect from an 'OUTER JOIN' in SQL, repeating the 'one' side of one-to-many or many-to-one relations so that each journey appears with its matched trips and each trip appears with its matched journey. Where there is no matched journey or trip its information is left blank. This format is convenient for display as a table, either directly in a spreadsheet application or by the viewer web application (see below).

This step also calculates departure and arrival delays for those trips for which it was possible to extract actual departure and arrival times.

This processing is performed by `expand_merged.py` which reads `merged-<yyy>-<mm>-<dd>.json` and `stops-<yyy>-<mm>-<dd>.json`, or by `do_everything.py`. Both emit results in JSON as `rows-<yyy>-<mm>-<dd>.json`. In addition to metadata, this includes a list of matched rows each including a single journey and a single trip (or `null` if there is no corresponding journey or trip):

```
{
    "bounding_box": "0.007896,52.155610,0.225048,52.267842",
    "day": "2018-10-13",
    "rows": [
        {
            "arrival_delay": 85,
            "departure_delay": 155,
            "destination": "0500SCOTT025",
            "destination_desc": "opp Telegraph Street, Cottenham",
            "origin": "0500CCITY487",
            "origin_desc": "Emmanuel Street Stop E1, Cambridge",
            "separator": " ",
            "time": "2018-10-13T00:15:00+01:00",
            "journey": {
            	...
            },
            "trip": {
            	...
            },
            "type": "1-1"
        },
        ...
    ]
}
```

Generate CSV
------------

This step converts the row data into CSV, suitable for processing in a spreadsheet. This contains a subset of the row data omitting the stops in journeys and the individual position reports in trips. The first row of the file contains column headings. The file uses the UTF-8 character encoding.

This processing is performed by `create_csv.py` which reads `rows-<yyy>-<mm>-<dd>.json`, or by `do_everything.py`. Both emit results as `rows-<yyy>-<mm>-<dd>.csv`.

Analysis steps
==============

Analyse performance
-------------------

This step produces numeric summaries of a day's bus services and prints them. It uses the row data created by the step above which means it over-counts the number of trips and journeys that appear on the 'one' side of many-to-one or one-to-many matches, or on either side of many-to-many matches.

This process is performed by `analyse.py` (but not by `do_everything.py`). It reads `rows-<yyy>-<mm>-<dd>.csv` and prints its results to STDOUT.

Web-based viewer
----------------

The HTML page in `viewer/index.html` and its associated CSS and JavaScript files display a table in its top half containing the journeys and trips for a selected day. Data in the table's columns can be filtered using the input boxes above each column (there is a filtering quick reference available from the '?' icon at the top left of the table).

Journeys and/or routes can be shown on the map on the bottom half of the page by clicking the associated 'Show' links. Once displayed, the corresponding 'Show' link turns into 'Hide' and will remove the journey or trip from the map. The 'Trash' button on the map will remove all journeys and trips from the map. Popups containing additional information are associated with the stops and the connecting lines of journeys, and with the positions and the connecting lines for trips.

The origin and destination stops of displayed trips as shown by circles. The positions used for the start and end timing of the trip (if any) are identified by markers displaying 'play' and 'stop' icon respectively.

The day to be analysed is selected by providing an HTML fragment-id after a '#' in the URL which must containing 'YYYY-MM-DD'. The JavaScript powering the page expects to find `rows-<yyy>-<mm>-<dd>.json` and corresponding `stops-<yyy>-<mm>-<dd>.json` files within the relative URL `results/`.

The HTML page requires no server-side processing, but has to be served over HTTP and not accessed directly as a file (at least by Chrome) otherwise the XHR requests it uses to load the data fail. For local use, the script `start_server.sh` will start a stand-alone web server (using Python's http.server module) serving the page at `http://127.0.0.1#8000/`.

Alternative the page an analysed data files can be served by any other web server.

Accessing the page directly will result in an error popup if no date has been selected. Select a day to display (for which data file need to be available) like this:

    http://127.0.0.1#8000/#2018-10-01
