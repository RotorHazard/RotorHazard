#!/bin/sh
RACE_EXPLORER_VERSION=race-explorer-v0.1
set -e

# Add extra repos
. /etc/os-release
wget -O - http://repo.mosquitto.org/debian/mosquitto-repo.gpg.key | sudo apt-key add -
sudo wget -O /etc/apt/sources.list.d/mosquitto-${VERSION_CODENAME}.list http://repo.mosquitto.org/debian/mosquitto-${VERSION_CODENAME}.list

# Make sure system is up-to-date, security fixes and all
sudo apt-get update
sudo apt-get upgrade -y

# Python packages
cd src
python3 -m pip install --upgrade -r requirements.txt
sudo apt-get install python3-numpy
cd ..

# Mosquitto
sudo apt-get install mosquitto
mosquitto_passwd -c -b mosquitto-bh.pwd race-admin fu56rg20
sudo cp mosquitto-bh.* /etc/mosquitto/conf.d/
sudo systemctl restart mosquitto

# Build json schema docs
python3 -m pip install --upgrade json-schema-for-humans
mkdir -p doc/schemas
python3 -m json_schema_for_humans.generate src/config.schema.json doc/schemas/config.html
python3 -m json_schema_for_humans.generate src/race_formats.schema.json doc/schemas/race_formats.html
python3 -m json_schema_for_humans.generate src/vtxconfig_schema-1.0.json doc/schemas/vtxconfig.html

# Race explorer
wget https://github.com/pulquero/RotorHazard/releases/download/$RACE_EXPLORER_VERSION/race-explorer.zip
unzip race-explorer.zip

# Race explorer dev
#sudo apt-get install nodejs npm
#cd race-explorer
#npm install
#export NODE_OPTIONS=--max_old_space_size=16000
#npm run build
#cd ..

# Text-to-speech
cd ..
sudo apt-get install m4 libtool libasound2-dev
git clone https://github.com/gmn/nanotts
cd nanotts
git pull
make
sudo make install

# Bluetooth audio
sudo usermod -G bluetooth -a pi
sudo apt-get install bluealsa
