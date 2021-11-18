#!/bin/sh
cd src
python3 -m pip install --upgrade -r requirements.txt
sudo apt-get install python3-numpy
cd ..

# Build json schema docs
python3 -m pip install --upgrade json-schema-for-humans
mkdir -p doc/schemas
python3 -m json_schema_for_humans.generate src/config.schema.json doc/schemas/config.html
python3 -m json_schema_for_humans.generate src/race_formats.schema.json doc/schemas/race_formats.html
python3 -m json_schema_for_humans.generate src/vtxconfig_schema-1.0.json doc/schemas/vtxconfig.html

# Race explorer
sudo apt-get install nodejs
cd race-explorer
npm install
npm run build
cd ..

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
