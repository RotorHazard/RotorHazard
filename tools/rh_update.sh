#!/bin/bash

if [ -d "RotorHazard" ]; then
    mkdir -p old
    OLD_RH_DIR=old/RotorHazard_$(date -d "today" +"%Y%m%d_%H%M%S");
    echo 'Moving existing RotorHazard directory to: ' $OLD_RH_DIR
    mv RotorHazard/ $OLD_RH_DIR
else
    OLD_RH_DIR=;
fi
if [ -z "$1" ]; then
    RH_VERSION=$(curl -s https://api.github.com/repos/rotorhazard/rotorhazard/releases/latest | sed -n -e 's/^.*"tag_name": "v\(.*\)".*$/\1/p');
else
    RH_VERSION=$1;
    # remove leading 'v'
    case "$RH_VERSION" in
        v*)
            RH_VERSION="${RH_VERSION#?}"
            ;;
        V*)
            RH_VERSION="${RH_VERSION#?}"
            ;;
    esac
fi
if [ -n "$RH_VERSION" ]; then
    echo 'Updating RotorHazard to version' $RH_VERSION
    RH_URL=https://codeload.github.com/RotorHazard/RotorHazard/zip
    if wget --spider $RH_URL/$RH_VERSION > /dev/null 2>&1; then
        wget $RH_URL/$RH_VERSION -O temp.zip
    else
        wget $RH_URL/v$RH_VERSION -O temp.zip
    fi
    if [ $? -eq 0 ]; then
        unzip -n temp.zip
        mv RotorHazard-$RH_VERSION RotorHazard
        rm temp.zip
        SCRIPT_NAME=`basename $0`
        mv $SCRIPT_NAME RotorHazard/tools/${SCRIPT_NAME%.*}_bkp.${SCRIPT_NAME##*.}
        if [ -n "$OLD_RH_DIR" ]; then
            if [ -f "$OLD_RH_DIR/src/server/datapath.ini" ]; then
                cp $OLD_RH_DIR/src/server/datapath.ini RotorHazard/src/server/
            fi
            if [ -f "$OLD_RH_DIR/src/server/config.json" ]; then
                cp $OLD_RH_DIR/src/server/config.json RotorHazard/src/server/
            fi
            if [ -f "$OLD_RH_DIR/src/server/database.db" ]; then
                cp $OLD_RH_DIR/src/server/database.db RotorHazard/src/server/
            fi
        fi
        echo 'Update successful; updating RotorHazard server dependencies...'
        pip install --upgrade --no-cache-dir -r RotorHazard/src/server/requirements.txt
        echo 'Finished updating RotorHazard server dependencies'
    else
        echo 'Unable to download RotorHazard archive from GitHub'
    fi
else
    echo 'Unable to fetch RotorHazard version code from GitHub'
fi
