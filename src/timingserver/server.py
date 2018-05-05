#!/usr/bin/env python
import gevent
import gevent.monkey
gevent.monkey.patch_all()

import json

from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect

import sys

import argparse

parser = argparse.ArgumentParser(description='Timing Server')
parser.add_argument('--mock', dest='mock', action='store_true', default=False, help="use mock data for testing")
args = parser.parse_args()

sys.path.append('../delta5interface')
if args.mock or sys.platform.lower().startswith('win'):
    from MockInterface import get_hardware_interface
elif sys.platform.lower().startswith('linux'):
    from Delta5Interface import get_hardware_interface

hardwareInterface = get_hardware_interface()

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = "gevent"

app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
heartbeat_thread = None

firmware_version = {'major': 0, 'minor': 1}


# LED Code
import time
from neopixel import *

import signal
def signal_handler(signal, frame):
        colorWipe(strip, Color(0,0,0))
        sys.exit(0)

# LED strip configuration:
LED_COUNT      = 150      # Number of LED pixels.
#LED_PIN        = 18      # GPIO pin connected to the pixels (18 uses PWM!).
LED_PIN        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
LED_STRIP      = ws.WS2811_STRIP_GRB   # Strip type and colour ordering

# LED one color ON/OFF
def onoff(strip, color):
	for i in range(strip.numPixels()):
		strip.setPixelColor(i, color)
	strip.show()

def theaterChase(strip, color, wait_ms=50, iterations=5):
    """Movie theater light style chaser animation."""
    for j in range(iterations):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, color)
            strip.show()
            time.sleep(wait_ms/1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, 0)

# Create NeoPixel object with appropriate configuration.
strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL, LED_STRIP)
# Intialize the library (must be called once before other functions).
strip.begin()



def parse_json(data):
    if isinstance(data, basestring):
        return json.loads(data)
    return data

@app.route('/')
def index():
    template_data = { }
    return render_template('index.html', async_mode=socketio.async_mode, **template_data)

@app.route('/graphs')
def graphs():
    return render_template('graphs.html', async_mode=socketio.async_mode)

@app.route('/rssi')
def rssi():
    return render_template('rssi.html', async_mode=socketio.async_mode)

@socketio.on('connect')
def connect_handler():
    print ('connected!!');
    hardwareInterface.start()
    global heartbeat_thread
    if (heartbeat_thread is None):
        heartbeat_thread = gevent.spawn(heartbeat_thread_function)

@socketio.on('disconnect')
def disconnect_handler():
    print ('disconnected!!');

@socketio.on('get_version')
def on_get_version():
    return firmware_version

@socketio.on('get_timestamp')
def on_get_timestamp():
    print('get_timestamp')
    return {'timestamp': hardwareInterface.milliseconds()}

@socketio.on('get_settings')
def on_get_settings():
    print('get_settings')
    return hardwareInterface.get_settings_json()

@socketio.on('set_frequency')
def on_set_frequency(data):
    data = parse_json(data)
    print(data)
    index = data['node']
    frequency = data['frequency']
    hardwareInterface.set_frequency(index, frequency)
    emit('frequency_set', hardwareInterface.get_frequency_json(index), broadcast=True)

@socketio.on('set_calibration_threshold')
def on_set_calibration_threshold(data):
    data = parse_json(data)
    print(data)
    calibration_threshold = data['calibration_threshold']
    hardwareInterface.set_calibration_threshold_global(calibration_threshold)
    emit('calibration_threshold_set', hardwareInterface.get_calibration_threshold_json(), broadcast=True)

@socketio.on('set_calibration_offset')
def on_set_calibration_offset(data):
    data = parse_json(data)
    print(data)
    calibration_offset = data['calibration_offset']
    hardwareInterface.set_calibration_offset_global(calibration_offset)
    emit('calibration_offset_set', hardwareInterface.get_calibration_offset_json(), broadcast=True)

@socketio.on('set_trigger_threshold')
def on_set_trigger_threshold(data):
    data = parse_json(data)
    print(data)
    trigger_threshold = data['trigger_threshold']
    hardwareInterface.set_trigger_threshold_global(trigger_threshold)
    emit('trigger_threshold_set', hardwareInterface.get_trigger_threshold_json(), broadcast=True)

@socketio.on('set_filter_ratio')
def on_set_filter_ratio(data):
    data = parse_json(data)
    print(data)
    filter_ratio = data['filter_ratio']
    hardwareInterface.set_filter_ratio_global(filter_ratio)
    emit('filter_ratio_set', hardwareInterface.get_filter_ratio_json(), broadcast=True)

# Keep this around for a bit.. old version of the api
# @socketio.on('reset_auto_calibration')
# def on_reset_auto_calibration():
#     print('reset_auto_calibration all')
#     hardwareInterface.enable_calibration_mode();

@socketio.on('reset_auto_calibration')
def on_reset_auto_calibration(data):
    onoff(strip, Color(255,0,0)) #RED ON
    time.sleep(0.5)
    onoff(strip, Color(0,0,0)) #OFF
    time.sleep(0.5)
    onoff(strip, Color(255,0,0)) #RED ON
    time.sleep(0.5)
    onoff(strip, Color(0,0,0)) #OFF
    time.sleep(0.5)
    onoff(strip, Color(255,0,0)) #RED ON
    time.sleep(0.5)
    onoff(strip, Color(0,0,0)) #OFF
    data = parse_json(data)
    print(data)
    index = data['node']
    if index == -1:
        print('reset_auto_calibration all')
        hardwareInterface.enable_calibration_mode()
    else:
        print('reset_auto_calibration {0}'.format(index))
        hardwareInterface.set_calibration_mode(index, True)
    onoff(strip, Color(0,255,0)) #GREEN ON

@socketio.on('simulate_pass')
def on_simulate_pass(data):
    data = parse_json(data)
    index = data['node']
    # todo: how should frequency be sent?
    emit('pass_record', {'node': index, 'frequency': hardwareInterface.nodes[index].frequency, 'timestamp': hardwareInterface.milliseconds()}, broadcast=True)

def pass_record_callback(node, ms_since_lap):
    print('Pass record from {0}{1}: {2}, {3}'.format(node.index, node.frequency, ms_since_lap, hardwareInterface.milliseconds() - ms_since_lap))
    #TODO: clean this up
    socketio.emit('pass_record', {
        'node': node.index,
        'frequency': node.frequency,
        'timestamp': hardwareInterface.milliseconds() - ms_since_lap,
        'trigger_rssi': node.trigger_rssi,
        'peak_rssi_raw': node.peak_rssi_raw,
        'peak_rssi': node.peak_rssi})
        if node.index==0:
            theaterChase(strip, Color(0,0,255))  #BLUE theater chase
        elif node.index==1:
            theaterChase(strip, Color(255,50,0)) #ORANGE theater chase
        elif node.index==2:
            theaterChase(strip, Color(255,0,60)) #PINK theater chase
        elif node.index==3:
            theaterChase(strip, Color(150,0,255)) #PURPLE theater chase
        elif node.index==4:
            theaterChase(strip, Color(250,210,0)) #YELLOW theater chase
        elif node.index==5:
            theaterChase(strip, Color(0,255,255)) #CYAN theater chase
        elif node.index==6:
            theaterChase(strip, Color(0,255,0)) #GREEN theater chase
        elif node.index==7:
            theaterChase(strip, Color(255,0,0)) #RED theater chase

hardwareInterface.pass_record_callback = pass_record_callback

def hardware_log_callback(message):
    print(message)
    socketio.emit('hardware_log', message)

hardwareInterface.hardware_log_callback = hardware_log_callback

def heartbeat_thread_function():
    while True:
        socketio.emit('heartbeat', hardwareInterface.get_heartbeat_json())
        gevent.sleep(0.5)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True)
