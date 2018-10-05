// Trip and Journey viewer

/* jshint esversion:6, strict:global, browser:true */
/* globals moment, L, TableFilter, alert */

'use strict';

var map;                     // Leaflet Map object

var data;                    // Loaded journey/trip data
var stops;                   // Loaded Stop data

var journey_layers = {};     // Row numbers to journey layer
var trip_layers = {};        // Row numbers to trip layer

// Default polyline and marker options
const trip_marker_opts = {
    radius: 3,
    weight: 2,
    fill: true,
    stroke: true,
    fillOpacity: 0.8
};

const trip_line_opts = {
    weight: 3,
};

const trip_departure = L.AwesomeMarkers.icon({
    prefix: 'fa',
    icon: 'play-circle',
    markerColor: 'darkblue'
});

const trip_arrival = L.AwesomeMarkers.icon({
    prefix: 'fa',
    icon: 'stop-circle',
    markerColor: 'darkblue'
});

const journey_marker_opts = {
    radius: 4,
    weight: 2,
    fill: false,
    stroke: true,
};

const journey_line_opts = {
    dashArray: "5",
    weight: 2,
};

// Handler for onload event
function init(){

    var date = window.location.hash.substring(1);

    var requests_done = 0;

    var xhr1 = new XMLHttpRequest();
    xhr1.open('GET', `results/rows-${date}.json`, true);
    xhr1.send();
    xhr1.onreadystatechange = function() {
        if(xhr1.readyState === XMLHttpRequest.DONE) {
            if (xhr1.status !== 200) {
                alert('Failed to get data - API error: ' + xhr1.status);
            }
            else {
                data = JSON.parse(xhr1.responseText);
                ++requests_done;
                if (requests_done >= 2) {
                    setup();
                }
            }

        }
    };

    var xhr2 = new XMLHttpRequest();
    xhr2.open('GET', `results/stops-${date}.json`, true);
    xhr2.send();
    xhr2.onreadystatechange = function() {
        if(xhr2.readyState === XMLHttpRequest.DONE) {
            if (xhr2.status !== 200) {
                alert('Failed to get stops - API error' + xhr2.status);
            }
            else {
                stops = JSON.parse(xhr2.responseText);
                ++requests_done;
                if (requests_done >= 2) {
                    setup();
                }
            }

        }
    };

}

// Setup the table and the map
function setup() {
    draw_map();
    draw_table();
}

// Setup the map
function draw_map() {

    map = L.map('map');

    var osm = L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
       attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>',
       maxZoom: 19
    });
    map.addLayer(osm);
    L.control.scale().addTo(map);

    // Add a 'clear' button. Also resets the line<->color mapping
    L.easyButton('fa-trash-alt', function(btn, map) {
        for (var row in journey_layers) {
            if (journey_layers.hasOwnProperty(row)) {
                toggle_journey(row);
            }
        }
        for (row in trip_layers) {
            if (trip_layers.hasOwnProperty(row)) {
                toggle_trip(row);
            }
        }
        line_colors = {};
        next_color = 0;
    }).addTo(map);

    // Mark the selection bounding box
    var area = L.rectangle([[52.155610, 0.007896], [52.267842, 0.225048]],
        {color: "#000000", weight: 1, fill: false}).addTo(map);
    map.fitBounds(area.getBounds());

}

// Draw the data table and populate it
function draw_table() {

    var table = document.createElement('table');

    var trow = document.createElement('tr');
    add_heading(trow, '');
    add_heading(trow, 'Type');
    add_heading(trow, 'Date');
    add_heading(trow, 'Time');
    add_heading(trow, 'From');
    add_heading(trow, 'To');

    add_heading(trow, 'Journey: Line');
    add_heading(trow, 'Journey: Direction');
    add_heading(trow, 'Journey: Depart');
    add_heading(trow, 'Journey: Arrive');
    add_heading(trow, '');

    add_heading(trow, '');

    add_heading(trow, '');
    add_heading(trow, 'Trip: Line');
    add_heading(trow, 'Trip: Vehicle');
    add_heading(trow, 'Trip: Depart');
    add_heading(trow, 'Trip: Arrive');

    add_heading(trow, 'Delay (min): Departure');
    add_heading(trow, 'Delay (min): Arrival');

    var thead = document.createElement('thead');
    thead.appendChild(trow);
    table.appendChild(thead);

    var counter = 0;

    var tbody = document.createElement('tbody');

    data.rows.forEach(function(row) {
        var trow = document.createElement('tr');
        if (row.type !== '1-1') {
            trow.classList.add('mismatch');
        }

        add_heading(trow, counter+1);

        add_data(trow, row.type);
        var timestamp = moment(row.time);
        add_data(trow, timestamp.format("YYYY-MM-DD"));
        add_data(trow, timestamp.format("HH:mm"));
        add_data(trow, row.origin_desc);
        add_data(trow, row.destination_desc);

        if (row.journey) {
            add_data(trow, row.journey.Service.LineName);
            add_data(trow, row.journey.Direction);
            add_data(trow, moment(row.journey.stops[0].time).format("HH:mm"));
            add_data(trow, moment(row.journey.stops[row.journey.stops.length - 1].time).format("HH:mm"));
            var a1 = document.createElement('a');
            a1.setAttribute('href', '#');
            a1.onclick = function(c) {
                return function() {
                    toggle_journey(c);
                    return false;
                };
            }(counter);
            a1.id = 'journey-' + counter;
            a1.innerHTML = 'Show';
            var cell1 = document.createElement('td');
            cell1.appendChild(a1);
            trow.appendChild(cell1);
        }
        else {
            add_data(trow, '');
            add_data(trow, '');
            add_data(trow, '');
            add_data(trow, '');
            add_data(trow, '');
        }

        add_data(trow, row.separator);

        if (row.trip) {
            var a2 = document.createElement('a');
            a2.setAttribute('href', '#');
            a2.onclick = function(c) {
                return function() {
                    toggle_trip(c);
                    return false;
                };
            }(counter);
            a2.id = 'trip-' + counter;
            a2.innerHTML = 'Show';
            var cell2 = document.createElement('td');
            cell2.appendChild(a2);
            trow.appendChild(cell2);
            add_data(trow, row.trip.LineRef);
            add_data(trow, row.trip.VehicleRef);
            if (row.trip.departure_position !== null) {
                add_data(trow, moment(row.trip.positions[row.trip.departure_position].RecordedAtTime).format("HH:mm"));
            }
            else {
                add_data(trow, '');
            }
            if (row.trip.arrival_position !== null) {
                add_data(trow, moment(row.trip.positions[row.trip.arrival_position].RecordedAtTime).format("HH:mm"));
            }
            else {
                add_data(trow, '');
            }
        }
        else {
            add_data(trow, '');
            add_data(trow, '');
            add_data(trow, '');
            add_data(trow, '');
            add_data(trow, '');
        }

        add_data(trow, as_minutes(row.departure_delay));
        add_data(trow, as_minutes(row.arrival_delay));

        tbody.appendChild(trow);

        counter += 1;

    });

    table.appendChild(tbody);

    const tf_config = {
        base_path: 'tablefilter/',
        alternate_rows: true,
        rows_counter: true,
        btn_reset: true,
        status_bar: true,
        sticky_headers: true
    };

    var tf = new TableFilter(table, tf_config);
    tf.init();

    var results = document.getElementById('data-table');
    results.appendChild(table);

}

// Handler for toggling journey display
function toggle_journey(row_num) {

    var element = document.getElementById('journey-' + row_num);

    // If already displayed then hide
    if (journey_layers.hasOwnProperty(row_num)) {
        map.removeLayer(journey_layers[row_num]);
        delete journey_layers[row_num];
        element.innerHTML = 'Show';
    }

    /// Otherwise add
    else {
        var layer = L.layerGroup();
        var color = get_color(row_num);

        var journey = data.rows[row_num].journey;
        var polyline = L.polyline([], journey_line_opts)
            .setStyle({color: color})
            .addTo(layer)
            .bindPopup(journey_as_html(journey, row_num));

        journey.stops.forEach(function(stop, index, journey_stops) {
            var full_stop = stops.stops[stop.StopPointRef];
            polyline.addLatLng([full_stop.latitude, full_stop.longitude]);
            L.circleMarker([full_stop.latitude, full_stop.longitude], journey_marker_opts)
                .setStyle({color: color})
                .bindPopup(journey_stop_as_html(stop))
                .addTo(layer);
        });
        L.polylineDecorator(polyline, {
            patterns: [ {
                offset: 25,
                repeat: 75,
                symbol: L.Symbol.arrowHead( {
                    pixelSize: 15,
                    polygon: false,
                    pathOptions: {
                        stroke: true,
                        color: color,
                    }
                } )
            } ]
        } ).addTo(layer);

        journey_layers[row_num] = layer;
        map.addLayer(layer);

        element.innerHTML = '<b>Hide</b>';

    }

}

// Handler for toggling trip display
function toggle_trip(row_num) {

    var element = document.getElementById('trip-' + row_num);

    // If already displayed then hide
    if (trip_layers.hasOwnProperty(row_num)) {
        map.removeLayer(trip_layers[row_num]);
        delete trip_layers[row_num];
        element.innerHTML = 'Show';
    }

    // Otherwise add
    else {

        var layer = L.layerGroup();

        var color = get_color(row_num);

        var trip = data.rows[row_num].trip;
        var polyline = L.polyline([], trip_line_opts)
            .setStyle({color: color})
            .addTo(layer)
            .bindPopup(trip_as_html(trip, row_num));
        trip.positions.forEach(function(position, index, positions) {
            polyline.addLatLng([position.Latitude, position.Longitude]);
            // Additional marker for trip start
            if (index == trip.departure_position) {
                L.marker([position.Latitude, position.Longitude], {icon: trip_departure})
                .bindPopup(position_as_html(position, index))
                .addTo(layer);
            }
            // Additional marker for trip end
            else if (index == trip.arrival_position) {
                L.marker([position.Latitude, position.Longitude], {icon: trip_arrival})
                .bindPopup(position_as_html(position, index))
                .addTo(layer);
            }
            L.circleMarker([position.Latitude, position.Longitude], trip_marker_opts)
                .setStyle({color: color})
                .bindPopup(position_as_html(position, index))
                .addTo(layer);
        });
        L.polylineDecorator(polyline, {
            patterns: [ {
                offset: 25,
                repeat: 75,
                symbol: L.Symbol.arrowHead( {
                    pixelSize: 15,
                    polygon: false,
                    pathOptions: {
                        stroke: true,
                        color: color,
                    }
                } )
            } ]
        } ).addTo(layer);

        // Markers for trip scheduled origin and destination
        var origin = stops.stops[trip.OriginRef];
        L.circleMarker([origin.latitude, origin.longitude], trip_marker_opts)
            .bindPopup(stop_as_html(origin))
            .setStyle({color: color, radius: 10, fill: false, weight: 2 })
            .addTo(layer);
        var destination = stops.stops[trip.DestinationRef];
        var destination_marker = L.circleMarker([destination.latitude, destination.longitude], trip_marker_opts)
            .bindPopup(stop_as_html(destination))
            .setStyle({color: color, radius: 10, fill: false, weight: 2 })
            .addTo(layer);

        trip_layers[row_num] = layer;
        map.addLayer(layer);

        element.innerHTML = '<b>Hide</b>';

    }

}

// Render trips, positions, etc. as HTML for popups

function trip_as_html(trip, counter) {

    var result = [];
    var timestamp = moment(trip.OriginAimedDepartureTime);
    result.push('<h1>Trip</h1>');
    result.push('<table class="popup">');
    result.push(`<tr><th align="right">Date</th><td>${timestamp.format("YYYY-MM-DD")}</td></tr>`);
    result.push(`<tr><th align="right">Time</th><td>${timestamp.format("HH:mm")}</td></tr>`);
    result.push(`<tr><th align="right">From</th><td>${trip.OriginName} (${trip.OriginRef})</td></tr>`);
    result.push(`<tr><th align="right">To</th><td>${trip.DestinationName} (${trip.DestinationRef})</td></tr>`);
    result.push(`<tr><th align="right">Line</th><td>${trip.LineRef}</td></tr>`);
    result.push(`<tr><th align="right">Operator</th><td>${trip.OperatorRef}</td></tr>`);
    result.push(`<tr><th align="right">Direction</th><td>${trip.DirectionRef}</td></tr>`);
    result.push(`<tr><th align="right">Vehicle</th><td>${trip.VehicleRef}</td></tr>`);
    result.push('</table>');
    result.push(`<p><a href="#" onclick="toggle_trip(${counter}); return false">Hide this trip</a></p>`);
    return result.join(" ");
}

function position_as_html(position, index) {

    var result = [];
    var timestamp = moment(position.RecordedAtTime);
    result.push('<h1>Position</h1>');
    result.push('<table class="popup">');
    result.push(`<tr><th align="right">Date</th><td>${timestamp.format("YYYY-MM-DD")}</td></tr>`);
    result.push(`<tr><th align="right">Time</th><td>${timestamp.format("HH:mm")}</td></tr>`);
    result.push(`<tr><th align="right">Bearing</th><td>${position.Bearing}</td></tr>`);
    result.push(`<tr><th align="right">Order</th><td>${index}</td></tr>`);
    result.push(`<tr><th align="right">Delay</th><td>${position.Delay}</td></tr>`);
    result.push('</table>');
    return result.join(" ");
}

function journey_as_html(journey, counter) {

    var result = [];

    var from = stops.stops[journey.stops[0].StopPointRef];
    var to = stops.stops[journey.stops[journey.stops.length -1].StopPointRef];
    var timestamp = moment(journey.DepartureTime);

    result.push('<h1>Journey</h1>');
    result.push('<table class="popup">');
    result.push(`<tr><th align="right">Date</th><td>${timestamp.format("YYYY-MM-DD")}</td></tr>`);
    result.push(`<tr><th align="right">Time</th><td>${timestamp.format("HH:mm")}</td></tr>`);
    result.push(`<tr><th align="right">From</th><td>${from.indicator} ${from.common_name}, ${from.locality_name} (${from.atco_code})</td></tr>`);
    result.push(`<tr><th align="right">To</th><td>${to.indicator} ${to.common_name}, ${to.locality_name} (${to.atco_code})</td></tr>`);
    result.push(`<tr><th align="right">Line</th><td>${journey.Service.LineName}</td></tr>`);
    result.push(`<tr><th align="right">Operator</th><td>${journey.Service.OperatorCode}</td></tr>`);
    result.push(`<tr><th align="right">Direction</th><td>${journey.Direction}</td></tr>`);
    result.push('</table>');
    result.push(`<p><a href="#" onclick="toggle_journey(${counter}); return false">Hide this journey</a></p>`);

    return result.join(" ");
}


function stop_as_html(stop) {
    return(`<h1>Stop</h1><p>${stop.indicator} ${stop.common_name}, ${stop.locality_name} (${stop.atco_code})</p>`);
}

function journey_stop_as_html(stop) {

    var result = [];
    var full_stop = stops.stops[stop.StopPointRef];
    var timestamp = moment(stop.time);

    result.push('<h1>Journey stop</h1>');
    result.push('<table class="popup">');
    result.push(`<tr><th align="right">Date</th><td>${timestamp.format("YYYY-MM-DD")}</td></tr>`);
    result.push(`<tr><th align="right">Time</th><td>${timestamp.format("HH:mm")}</td></tr>`);
    result.push(`<tr><th align="right">Activity</th><td>${stop.Activity}</td></tr>`);
    result.push(`<tr><th align="right">Order</th><td>${stop.Order}</td></tr>`);
    result.push(`<tr><th align="right">Timing status</th><td>${stop.TimingStatus}</td></tr>`);
    result.push(`<tr><th align="right">Run time</th><td>${stop.run_time}</td></tr>`);
    result.push(`<tr><th align="right">ATCO Code</th><td>${full_stop.atco_code}</td></tr>`);
    result.push(`<tr><th align="right">Common name</th><td>${full_stop.common_name}</td></tr>`);
    result.push(`<tr><th align="right">Indicator</th><td>${full_stop.indicator}</td></tr>`);
    result.push(`<tr><th align="right">Locality name</th><td>${full_stop.locality_name}</td></tr>`);
    result.push('</table>');

    return result.join(" ");
}

// Format time in seconds in minutes
function as_minutes(seconds) {
    if (seconds === null || seconds === '') {
        return '';
    }
    else {
        return (seconds/60).toFixed(2);
    }
}


// Colour sequence for displaying trips and journeys
// https://sashat.me/2017/01/11/list-of-20-simple-distinct-colors/
const colors = [
    "#e6194B", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#f032e6",
    "#469990", "#9A6324", "#800000", "#808000", "#000075", "#000000"];
var line_colors = {};     // Current line to colour assignment
var next_color = 0;       // Next colour to use

// Get current colour for a row, or allocate a new one
function get_color(row) {
    var color;
    if (line_colors.hasOwnProperty(row)) {
        color = line_colors[row];
    }
    else {
        color = colors[next_color % colors.length];
        line_colors[row] = color;
        next_color += 1;
    }
    return color;
}

// Append a <th> to a row
function add_heading(row, text) {
    var cell = document.createElement('th');
    cell.appendChild(document.createTextNode(text));
    row.appendChild(cell);
}

// Add a <td> to a row
function add_data(row, text) {
    var cell = document.createElement('td');
    cell.appendChild(document.createTextNode(text));
    row.appendChild(cell);
}
