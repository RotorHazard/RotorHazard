#!/bin/bash

if [ ! -d "RotorHazard" ]; then
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
        echo 'Installing RotorHazard version' $RH_VERSION
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
            echo 'Installation successful; updating RotorHazard server dependencies...'
            pip install --upgrade --no-cache-dir -r RotorHazard/src/server/requirements.txt
            echo 'Finished updating RotorHazard server dependencies'
        else
            echo 'Unable to download RotorHazard archive from GitHub'
        fi
    else
        echo 'Unable to fetch RotorHazard version code from GitHub'
    fi
else
    echo 'A "RotorHazard" directory is already present; please rename or remove it'
fi
