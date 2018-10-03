#!/bin/bash

set -e

for f in results/rows-*.json
do
    echo 'data =' | cat - "${f}" > "${f%.json}.js"
done

for f in results/stops-*.json
do
    echo 'stops =' | cat - "${f}" > "${f%.json}.js"
done
