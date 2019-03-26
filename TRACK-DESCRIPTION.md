Extracting particular trips from archived real-time bus trips
=============================================================

A problem with the approach to extracting trip information from the real-time data as described in [DESCRIPTION.md](DESCRIPTION.md) is that the trip 'metadata' frequently doesn't match the position data. In particular, it seems very common for the metadata to move on to describe a vehicle's *next* trip before the vehicle has completed its current one. This makes it difficult to establish actual trip arrival time since the arrival event is frequently only available in the data for the vehicle's next trip.

A further set of scripts in this repository take a different approach to analysing trips by creating *vehicle tracks* and then extracing the *segments* of those tracks that lie between nominated stops.

Initial setup
=============

See 'Initial setup' in [DESCRIPTION.md](DESCRIPTION.md).

Processing steps
================

Extract vehicle tracks
----------------------

All position records for a particular day are processed. Positions are amalgamated into tracks based on `VehicleRef`. Positions from trips with neither an origin nor a destination within the configured bounding box are ignored.

This process yield tracks for about 180 vehicles.

This processing is performed by `scripts/get_vehicle_tracks.py`, which requires a date (as `YYYY-MM-DD`) as a single command-line argument and emits `tracks-<YYYY>-<MM>-<DD>.json`. In addition to metadata, this contains a list of all extracted tracks:

```
{
    "bounding_box": "0.007896,52.155610,0.225048,52.267842",
    "day": "2019-03-20",
    "tracks": [
        {
            "bbox": [
                "-0.0001397",
                "52.2048225",
                "0.1273619",
                "52.3037186"
            ],
            "destinations": [
                "0500CCITY119",
                "0500HHILT003",
                "0500SBARH011",
                "0500SPAPE007"
            ],
            "lines": [
                "8"
            ],
            "origins": [
                "0500CCITY119",
                "0500HHILT004",
                "0500SBARH011",
                "0500SPAPE001"
            ],
            "positions": [
                {
                    "Bearing": "192",
                    "Delay": "-PT1M6S",
                    "Latitude": "52.2784538",
                    "Longitude": "-0.1124608",
                    "RecordedAtTime": "2019-03-20T07:11:45+00:00",
                    "trip": 3
                },
                <...>
            ],
            "trips": [
                {
                    "DestinationName": "Scotts Crescent",
                    "DestinationRef": "0500HHILT003",
                    "DirectionRef": "OUTBOUND",
                    "LineRef": "8",
                    "OperatorRef": "WP",
                    "OriginAimedDepartureTime": "2019-03-20T16:30:00+00:00",
                    "OriginName": "Drummer Str Bay 3",
                    "OriginRef": "0500CCITY119",
                    "VehicleRef": "WP-325"
                },
                <...>
            ],
            "vehicle": "WP-325"
        },
        <...>
    ]
}
```

Extract track segments
----------------------

Filter and split track information to emit only those segments of tracks that represent travel between selected pairs of stops. Optionally pre-filter tracks to only include vehicles that services particular lines at some point during the day. Emitted tracks run *from* the last position report that is within 50m of the origin stop *to* the first position report that is within 50m of the destination stop.

This process is run as follows:

```
./scripts/extract_segments.py [-h] --from FROM --to TO [--line LINE] YYYY-MM-DD
```

where FROM and TO are the ATCO codes of the origin and destination stops. The script emits `segments-<FROM>-<TO>-<YYYY>-<MM>-<DD>.json`:

```
{
    "bounding_box": "0.007896,52.155610,0.225048,52.267842",
    "day": "2019-03-20",
    "from_stop": {
        "atco_code": "0500SMILT010",
        "common_name": "Milton Park-and-Ride",
        "id": "0500SMILT010",
        "indicator": "Stop 1",
        "lat": 52.2451385817,
        "latitude": 52.2451385817,
        "lng": 0.15097039186,
        "locality_name": "Milton",
        "longitude": 0.15097039186,
        "naptan_code": "CMBGJTMA",
        "stop_id": "0500SMILT010"
    },
    "line": null,
    "segments": [
        {
            "VehicleRef": "SCCM-10806",
            "positions": [
                {
                    "Bearing": "60",
                    "Delay": "PT0S",
                    "Latitude": "52.2453651",
                    "Longitude": "0.1514220",
                    "RecordedAtTime": "2019-03-20T06:21:17+00:00",
                    "trip": 32
                },
                <...>
            ],
        },
        <...>
    ],
    "to_stop": {
        "atco_code": "0500CCITY486",
        "common_name": "Drummer Street",
        "id": "0500CCITY486",
        "indicator": "Stop D1",
        "lat": 52.2049274264,
        "latitude": 52.2049274264,
        "lng": 0.12463017631,
        "locality_name": "Cambridge",
        "longitude": 0.12463017631,
        "naptan_code": "CMBGJPWJ",
        "stop_id": "0500CCITY486"
    }
}
```

Extract segment timings
-----------------------

Process a segment file and extract departure and arival times for each represented journey, along with the trip duration and the maximum time a customer would have had to wait to catch this service (i.e. the time between the departure of the previous bus and the departure of this one).

This processing is performed by `./scripts/segment_timings.py` which expects a single argument in the form `segments-<FROM>-<TO>-<YYYY>-<MM>-<DD>` (note no filename suffix) and emits `segments-<FROM>-<TO>-<YYYY>-<MM>-<DD>-timings.csv`:

```
"Trip_Vehicle","Trip_Departure","Trip_Arrival","Trip_Max_Wait","Trip_Duration"
"SCCM-10806","2019-03-20 06:21:17+00:00","2019-03-20 06:34:02+00:00","","765"
"SCCM-10805","2019-03-20 06:41:21+00:00","2019-03-20 06:54:27+00:00","1204","786"
<...>
```

Note that the first trip can have no sensible `Trip_Max_Wait` value.

Extract expanded segment timings
--------------------------------

Process a segment file and calculate the actual journey time (waiting time plus trip duration) experienced by a customer arriving each minute during the day.

This processing is performed by `./scripts/segment_timings_expanded.py` which expects a single argument in the form `segments-<FROM>-<TO>-<YYYY>-<MM>-<DD>` (note no filename suffix) and emits `segments-<FROM>-<TO>-<YYYY>-<MM>-<DD>-expanded.csv`:

```
"Passenger_Arrival","Passenger_Wait","Trip_Vehicle","Trip_Departure","Trip_Arrival","Trip_Duration","Passenger_Journey_Duration"
"2019-03-20 06:00:00+00:00","1277","SCCM-10806","2019-03-20 06:21:17+00:00","2019-03-20 06:34:02+00:00","765","2042"
"2019-03-20 06:01:00+00:00","1217","SCCM-10806","2019-03-20 06:21:17+00:00","2019-03-20 06:34:02+00:00","765","1982"
<...>
```

Summarise segment timings
-------------------------

Process one or more segment files. For each one, work out the 'best' and 'worst' journey time in the time bands up to 10:00 ('Morning'), from 10:00 to 15:00 ('Daytime'), and after 15:00 ('Evening'). For this, the 'best' is the segment with the shortest trip duration - as if a customer had arrived just in time to catch this bus before it set off. The 'worst' is the segment with the greatest wait plus trip duration - as if a customer had just missed one bus and the next one had been slow in coming and slow traveling to the destination.

This processing is performed by `./scripts/segment_sumamry.py` which expects one or more filename argument in the form `segments-<FROM>-<TO>-<YYYY>-<MM>-<DD>.json` (note ther *is* a filename suffix) and emits CSV to stdout:

```
"Day","Origin","Destination","Morning best","Morning worst","Daytime best","Daytime worst","Evening best","Evening worst"
"2019-03-19","0500SMILT010","0500CCITY486","745","3122","704","1678","663","1425"
"2019-03-20","0500SMILT010","0500CCITY486","765","1990","743","1298","665","2083"
"2019-03-21","0500SMILT010","0500CCITY486","626","5396","643","2590","724","1519"
<...>
```

The script will sumarise segment data for multiple combinations of origin and destination, though processing such an amalgamation will require care...
