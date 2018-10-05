#!/bin/bash

# Start up a local web server for the viewer

python3 -m http.server 8000 --bind 127.0.0.1 --directory viewer/
