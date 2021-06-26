#!/bin/sh
cd src
python3 -m pip install -r requirements.txt
sudo apt-get install python3-numpy

# TTS
cd ../..
sudo apt-get install m4 libtool libasound2-dev
git clone https://github.com/gmn/nanotts
cd nanotts
make
sudo make install

# Bluetooth audio
sudo usermod -G bluetooth -a pi
sudo apt-get install bluealsa
