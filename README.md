Processing steps
================

* Retrieve all bus stops in the selected area

* Process position reports
    * Convert position reports to monitored journeys based on
        * VehicleRef
        * DestinationRef
        * DirectionRef
        * LineRef
        * OperatorRef
        * OriginAimedDepartureTime
        * OriginRef
    * Discard any with neither DestinationRef nor OriginRef in stops list
    * Derive
        * Actual departure time
        * Actual arrival time

* Process timetable journeys

* Match monitored journeys and timetabled journeys

