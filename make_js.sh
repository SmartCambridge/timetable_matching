#!/bin/bash

set -e

for f in rows-*.json
do
    echo 'data =' | cat - "${f}" > "${f%.json}.js"
done

for f in stops-*.json
do
    echo 'stops =' | cat - "${f}" > "${f%.json}.js"
done
