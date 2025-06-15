#!/bin/bash

if [ ! -d "RotorHazard" ]; then
    RH_VERSION=$(curl -s https://api.github.com/repos/rotorhazard/rotorhazard/releases/latest | sed -n -e 's/^.*"tag_name": "v\(.*\)".*$/\1/p');
    if [ -n "$RH_VERSION" ]; then
        echo 'Installing RotorHazard version' $RH_VERSION
        wget https://codeload.github.com/RotorHazard/RotorHazard/zip/v$RH_VERSION -O temp.zip
        unzip -n temp.zip
        mv RotorHazard-$RH_VERSION RotorHazard
        rm temp.zip
        mv install.sh RotorHazard/tools/rh_install_dl.sh
        echo 'Installation complete'
    else
        echo 'Unable to fetch RotorHazard version from GitHub'
    fi
else
    echo 'A "RotorHazard" directory is already present; please rename or remove it'
fi
