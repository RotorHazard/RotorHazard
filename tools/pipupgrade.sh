#!/bin/sh

if [ -e ../src/server/requirements.txt ]; then
    pip install --upgrade --no-cache-dir -r ../src/server/requirements.txt
elif [ -e src/server/requirements.txt ]; then
    pip install --upgrade --no-cache-dir -r src/server/requirements.txt
elif [ -e requirements.txt ]; then
    pip install --upgrade --no-cache-dir -r requirements.txt
else
    echo 'Unable to find "requirements.txt" file'
fi
