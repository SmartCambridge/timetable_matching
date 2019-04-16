// Segment viewer

/* jshint esversion:6, strict:global, browser:true */
/* globals moment, L, alert */

'use strict';

var map;                     // Leaflet Map object

var data;                    // Loaded segment data

var segment_layers = {};     // Segment number to segment layer

// Default polyline and marker options
const segment_marker_opts = {
    radius: 3,
    weight: 2,
    fill: true,
    stroke: true,
    fillOpacity: 0.8
};

const segment_line_opts = {
    weight: 3,
};


// Handler for onload event
function init(){

    // Get the name of the data to process
    // {FROM-STOP}-{TO-STOP}-{YYYY}-{MM}-{DD}
    var name = window.location.search.substring(1);

    var xhr1 = new XMLHttpRequest();
    xhr1.open('GET', `results/segments-${name}.json`, true);
    xhr1.send();
    xhr1.onreadystatechange = function() {
        if(xhr1.readyState === XMLHttpRequest.DONE) {
            if (xhr1.status !== 200) {
                alert(`Failed to get segment data for ${name} - status ${xhr1.status}`);
            }
            else {
                data = JSON.parse(xhr1.responseText);
                setup();
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
    L.easyButton('fa-trash-alt', function() {
        for (var row in segment_layers) {
            if (segment_layers.hasOwnProperty(row)) {
                toggle_segment(row);
            }
        }
        line_colors = {};
        next_color = 0;
    }).addTo(map);

    // Mark the selection bounding box
    var area = L.rectangle([[52.155610, 0.007896], [52.267842, 0.225048]],
        {color: '#000000', weight: 1, fill: false}).addTo(map);
    map.fitBounds(area.getBounds());

    // Mark the origin and destination stop
    L.circle([data.from_stop.lat, data.from_stop.lng], {
        radius: data.origin_threshold,
        color: '#ff0000',
        fill: false
    }).addTo(map);
    L.circle([data.to_stop.lat, data.to_stop.lng], {
        radius: data.destination_threshold,
        color: '#00ff00',
        fill: false
    }).addTo(map);

}

// Draw the data table and populate it
function draw_table() {

    var table = document.createElement('table');

    var trow = document.createElement('tr');
    add_heading(trow, 'Row');
    add_heading(trow, 'Vehicle');
    add_heading(trow, 'On route');
    add_heading(trow, 'Start');
    add_heading(trow, 'End');
    add_heading(trow, 'Time (m)');
    add_heading(trow, 'Length');
    add_heading(trow, 'Show');

    var thead = document.createElement('thead');
    thead.appendChild(trow);
    table.appendChild(thead);

    var counter = 0;

    var tbody = document.createElement('tbody');

    data.segments.forEach(function(segment) {
        tbody.appendChild(draw_row(counter, segment));
        counter += 1;
    });

    table.appendChild(tbody);

    var results = document.getElementById('data-table');
    results.innerHTML = '';
    results.appendChild(table);

}

function draw_row(counter, segment) {
    var trow = document.createElement('tr');

    add_heading(trow, counter+1);

    add_data(trow, segment.VehicleRef);
    add_data(trow, segment.on_route);

    var start = moment(segment.positions[0].RecordedAtTime);
    add_data(trow, start.format('HH:mm:ss'));

    var end = moment(segment.positions[segment.positions.length-1].RecordedAtTime);
    add_data(trow, end.format('HH:mm:ss'));

    add_data(trow, end.diff(start, 'minutes'));

    add_data(trow, segment.positions.length);

    var a1 = document.createElement('a');
    a1.setAttribute('href', '#');
    a1.onclick = function(c) {
        return function() {
            toggle_segment(c);
            return false;
        };
    }(counter);
    a1.id = 'segment-' + counter;
    a1.innerHTML = 'Show';
    var cell1 = document.createElement('td');
    cell1.appendChild(a1);
    trow.appendChild(cell1);

    return trow;

}


// Handler for toggling trip display
function toggle_segment(row_num) {

    var element = document.getElementById('segment-' + row_num);

    // If already displayed then hide
    if (segment_layers.hasOwnProperty(row_num)) {
        map.removeLayer(segment_layers[row_num]);
        delete segment_layers[row_num];
        element.innerHTML = 'Show';
    }

    // Otherwise add
    else {

        var layer = L.layerGroup();

        var color = get_color(row_num);

        var segment = data.segments[row_num];
        var polyline = L.polyline([], segment_line_opts)
            .setStyle({color: color})
            .addTo(layer)
            .bindPopup(segment_as_html(segment, row_num));
        segment.positions.forEach(function(position, index) {
            polyline.addLatLng([position.Latitude, position.Longitude]);
            L.circleMarker([position.Latitude, position.Longitude], segment_marker_opts)
                .setStyle({color: color})
                .bindPopup(position_as_html(position, index))
                .addTo(layer);
        });
        L.polylineDecorator(polyline, {
            patterns: [{
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
            }]
        } ).addTo(layer);

        segment_layers[row_num] = layer;
        map.addLayer(layer);

        element.innerHTML = '<b>Hide</b>';

    }

}

// Render trips, positions, etc. as HTML for popups

function segment_as_html(segment, counter) {

    var result = [];
    result.push('<h1>Segment</h1>');
    result.push('<table class="popup">');
    result.push(`<tr><th align="right">Vehicle</th><td>${segment.VehicleRef}</td></tr>`);
    result.push(`<tr><th align="right">On Route</th><td>${segment.on_route}</td></tr>`);
    result.push('</table>');
    result.push(`<p><a href="#" onclick="toggle_segment(${counter}); return false">Hide this segment</a></p>`);
    return result.join(' ');
}

function position_as_html(position, index) {

    var result = [];
    var timestamp = moment(position.RecordedAtTime);
    result.push('<h1>Position</h1>');
    result.push('<table class="popup">');
    result.push(`<tr><th align="right">Date</th><td>${timestamp.format('YYYY-MM-DD')}</td></tr>`);
    result.push(`<tr><th align="right">Time</th><td>${timestamp.format('HH:mm.ss')}</td></tr>`);
    result.push(`<tr><th align="right">Bearing</th><td>${position.Bearing}</td></tr>`);
    result.push(`<tr><th align="right">Order</th><td>${index}</td></tr>`);
    result.push(`<tr><th align="right">Delay</th><td>${position.Delay}</td></tr>`);
    result.push('</table>');
    return result.join(' ');
}


// Colour sequence for displaying trips and journeys
// https://sashat.me/2017/01/11/list-of-20-simple-distinct-colors/
const colors = [
    '#e6194B', '#3cb44b', '#4363d8', '#f58231', '#911eb4', '#f032e6',
    '#469990', '#9A6324', '#800000', '#808000', '#000075', '#000000'];
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
