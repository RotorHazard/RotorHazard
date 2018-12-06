'''Delta5 race timer server script'''

import os
import sys
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, Response
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy

import gevent
import gevent.monkey
gevent.monkey.patch_all()

import random

sys.path.append('../delta5interface')
sys.path.append('/home/pi/delta5_race_timer/src/delta5interface')  # Needed to run on startup
from Delta5Interface import get_hardware_interface

from Delta5Race import get_race_state

APP = Flask(__name__, static_url_path='/static')
APP.config['SECRET_KEY'] = 'secret!'
SOCKET_IO = SocketIO(APP, async_mode='gevent')

HEARTBEAT_THREAD = None

BASEDIR = os.path.abspath(os.path.dirname(__file__))
APP.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASEDIR, 'database.db')
APP.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
DB = SQLAlchemy(APP)

INTERFACE = get_hardware_interface()
RACE = get_race_state() # For storing race management variables

PROGRAM_START = datetime.now()
RACE_START = datetime.now() # Updated on race start commands

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

def wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

def rainbow(strip, wait_ms=2, iterations=1):
    """Draw rainbow that fades across all pixels at once."""
    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((i+j) & 255))
        strip.show()
        time.sleep(wait_ms/1000.0)

def rainbowCycle(strip, wait_ms=2, iterations=1):
    """Draw rainbow that uniformly distributes itself across all pixels."""
    for j in range(256*iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, wheel((int(i * 256 / strip.numPixels()) + j) & 255))
        strip.show()
        time.sleep(wait_ms/1000.0)

def theaterChaseRainbow(strip, wait_ms=25):
    """Rainbow movie theater light style chaser animation."""
    for j in range(256):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, wheel((i+j) % 255))
            strip.show()
            time.sleep(wait_ms/1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, 0)

# Create NeoPixel object with appropriate configuration.
strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL, LED_STRIP)
# Intialize the library (must be called once before other functions).
strip.begin()


#
# Database Models
#

class Pilot(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    pilot_id = DB.Column(DB.Integer, unique=True, nullable=False)
    callsign = DB.Column(DB.String(80), unique=True, nullable=False)
    phonetic = DB.Column(DB.String(80), unique=True, nullable=False)
    name = DB.Column(DB.String(120), nullable=False)

    def __repr__(self):
        return '<Pilot %r>' % self.pilot_id

class Heat(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    heat_id = DB.Column(DB.Integer, nullable=False)
    node_index = DB.Column(DB.Integer, nullable=False)
    pilot_id = DB.Column(DB.Integer, nullable=False)

    def __repr__(self):
        return '<Heat %r>' % self.heat_id

class CurrentLap(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    node_index = DB.Column(DB.Integer, nullable=False)
    pilot_id = DB.Column(DB.Integer, nullable=False)
    lap_id = DB.Column(DB.Integer, nullable=False)
    lap_time_stamp = DB.Column(DB.Integer, nullable=False)
    lap_time = DB.Column(DB.Integer, nullable=False)
    lap_time_formatted = DB.Column(DB.Integer, nullable=False)

    def __repr__(self):
        return '<CurrentLap %r>' % self.pilot_id

class SavedRace(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    round_id = DB.Column(DB.Integer, nullable=False)
    heat_id = DB.Column(DB.Integer, nullable=False)
    node_index = DB.Column(DB.Integer, nullable=False)
    pilot_id = DB.Column(DB.Integer, nullable=False)
    lap_id = DB.Column(DB.Integer, nullable=False)
    lap_time_stamp = DB.Column(DB.Integer, nullable=False)
    lap_time = DB.Column(DB.Integer, nullable=False)
    lap_time_formatted = DB.Column(DB.Integer, nullable=False)

    def __repr__(self):
        return '<SavedRace %r>' % self.round_id

class Frequency(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    band = DB.Column(DB.Integer, nullable=False)
    channel = DB.Column(DB.Integer, nullable=False)
    frequency = DB.Column(DB.Integer, nullable=False)

    def __repr__(self):
        return '<Frequency %r>' % self.frequency

class Profiles(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column(DB.String(80), unique=True, nullable=False)
    description = DB.Column(DB.String(256), nullable=True)
    c_offset = DB.Column(DB.Integer, nullable=True)
    c_threshold = DB.Column(DB.Integer, nullable=True)
    t_threshold = DB.Column(DB.Integer, nullable=True)
    f_ratio = DB.Column(DB.Integer, nullable=True)

class LastProfile(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    profile_id = DB.Column(DB.Integer, nullable=False)

class RaceFormat(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    race_mode = DB.Column(DB.Integer, nullable=False)
    race_time_sec = DB.Column(DB.Integer, nullable=False)
    min_lap_sec = DB.Column(DB.Integer, nullable=False)
    hide_stage_timer = DB.Column(DB.Integer, nullable=False)
    start_delay_min = DB.Column(DB.Integer, nullable=False)
    start_delay_max = DB.Column(DB.Integer, nullable=False)

class NodeData(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    frequency = DB.Column(DB.Integer, nullable=False)
    offset = DB.Column(DB.Integer, nullable=False)
    scale = DB.Column(DB.Integer, nullable=False)

#
# Authentication
#

def check_auth(username, password):
    '''Check if a username password combination is valid.'''
    return username == 'admin' and password == 'delta5'

def authenticate():
    '''Sends a 401 response that enables basic auth.'''
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

#
# Routes
#

@APP.route('/results')
def index():
    '''Route to round summary page.'''
    # A more generic and flexible way of viewing saved race data is needed
    # - Individual round/race summaries
    # - Heat summaries
    # - Pilot summaries
    # Make a new dynamic route for each? /pilotname /heatnumber /
    # Three different summary pages?
    # - One for all rounds, grouped by heats
    # - One for all pilots, sorted by fastest lap and shows average and other stats
    # - One for individual heats
    #
    # Calculate heat summaries
    # heat_max_laps = []
    # heat_fast_laps = []
    # for heat in SavedRace.query.with_entities(SavedRace.heat_id).distinct() \
    #     .order_by(SavedRace.heat_id):
    #     max_laps = []
    #     fast_laps = []
    #     for node in range(RACE.num_nodes):
    #         node_max_laps = 0
    #         node_fast_lap = 0
    #         for race_round in SavedRace.query.with_entities(SavedRace.round_id).distinct() \
    #             .filter_by(heat_id=heat.heat_id).order_by(SavedRace.round_id):
    #             round_max_lap = DB.session.query(DB.func.max(SavedRace.lap_id)) \
    #                 .filter_by(heat_id=heat.heat_id, round_id=race_round.round_id, \
    #                 node_index=node).scalar()
    #             if round_max_lap is None:
    #                 round_max_lap = 0
    #             else:
    #                 round_fast_lap = DB.session.query(DB.func.min(SavedRace.lap_time)) \
    #                 .filter(SavedRace.node_index == node, SavedRace.lap_id != 0).scalar()
    #                 if node_fast_lap == 0:
    #                     node_fast_lap = round_fast_lap
    #                 if node_fast_lap != 0 and round_fast_lap < node_fast_lap:
    #                     node_fast_lap = round_fast_lap
    #             node_max_laps = node_max_laps + round_max_lap
    #         max_laps.append(node_max_laps)
    #         fast_laps.append(time_format(node_fast_lap))
    #     heat_max_laps.append(max_laps)
    #     heat_fast_laps.append(fast_laps)
    # print heat_max_laps
    # print heat_fast_laps
    return render_template('rounds.html', num_nodes=RACE.num_nodes, rounds=SavedRace, \
        pilots=Pilot, heats=Heat)
        #, heat_max_laps=heat_max_laps, heat_fast_laps=heat_fast_laps

@APP.route('/')
def heats():
    '''Route to heat summary page.'''
    return render_template('heats.html', num_nodes=RACE.num_nodes, heats=Heat, pilots=Pilot, \
        frequencies=[node.frequency for node in INTERFACE.nodes], \
        channels=[Frequency.query.filter_by(frequency=node.frequency).first().channel \
            for node in INTERFACE.nodes])

@APP.route('/race')
@requires_auth
def race():
    '''Route to race management page.'''
    return render_template('race.html', num_nodes=RACE.num_nodes,
                           current_heat=RACE.current_heat,
                           heats=Heat, pilots=Pilot,
                           race_format=RaceFormat.query.get(1),
        frequencies=[node.frequency for node in INTERFACE.nodes],
        channels=[Frequency.query.filter_by(frequency=node.frequency).first().channel
            for node in INTERFACE.nodes])

@APP.route('/current')
def racepublic():
    '''Route to race management page.'''
    return render_template('racepublic.html', num_nodes=RACE.num_nodes,
                           current_heat=RACE.current_heat,
                           heats=Heat, pilots=Pilot,
                           race_format=RaceFormat.query.get(1),
        frequencies=[node.frequency for node in INTERFACE.nodes],
        channels=[Frequency.query.filter_by(frequency=node.frequency).first().channel
            for node in INTERFACE.nodes])

@APP.route('/settings')
@requires_auth
def settings():
    '''Route to settings page.'''

    return render_template('settings.html', num_nodes=RACE.num_nodes,
                           pilots=Pilot,
                           frequencies=Frequency,
                           heats=Heat,
                           last_profile =  LastProfile,
                           profiles = Profiles,
                           race_format=RaceFormat.query.get(1))

@APP.route('/correction')
@requires_auth
def correction():
    '''Route to node correction page.'''

    return render_template('correction.html', num_nodes=RACE.num_nodes,
                           frequencies=Frequency,
                           last_profile =  LastProfile,
                           profiles = Profiles)

# Debug Routes

@APP.route('/hardwarelog')
@requires_auth
def hardwarelog():
    '''Route to hardware log page.'''
    return render_template('hardwarelog.html')

@APP.route('/database')
@requires_auth
def database():
    '''Route to database page.'''
    return render_template('database.html', pilots=Pilot, heats=Heat, currentlaps=CurrentLap, \
        savedraces=SavedRace, frequencies=Frequency, race_format=RaceFormat.query.get(1), \
        node_data=NodeData, )

#
# Socket IO Events
#

@SOCKET_IO.on('connect')
def connect_handler():
    '''Starts the delta 5 interface and a heartbeat thread for rssi.'''
    server_log('Client connected')
    INTERFACE.start()
    global HEARTBEAT_THREAD
    if HEARTBEAT_THREAD is None:
        HEARTBEAT_THREAD = gevent.spawn(heartbeat_thread_function)
        server_log('Heartbeat thread started')
    emit_node_data() # Settings page, node channel and triggers
    emit_node_tuning() # Settings page, node tuning values
    emit_race_status() # Race page, to set race button states
    emit_current_laps() # Race page, load and current laps
    emit_leaderboard() # Race page, load leaderboard for current laps

@SOCKET_IO.on('disconnect')
def disconnect_handler():
    '''Emit disconnect event.'''
    server_log('Client disconnected')

# Settings socket io events

@SOCKET_IO.on('set_frequency')
def on_set_frequency(data):
    '''Set node frequency.'''
    node_index = data['node']
    frequency = data['frequency']
    INTERFACE.set_frequency(node_index, frequency)
    node_data = NodeData.query.filter_by(id=node_index).first()
    node_data.frequency = frequency
    DB.session.commit()
    server_log('Frequency set: Node {0} Frequency {1}'.format(node_index+1, frequency))
    emit_node_data() # Settings page, new node channel

@SOCKET_IO.on('set_node_offset')
def on_set_node_offset(data):
    '''Set node offset.'''
    node_index = data['node']
    node_offset = data['node_offset']
    node_data = NodeData.query.filter_by(id=node_index).first()
    node_data.offset = node_offset
    DB.session.commit()
    server_log('Node offset set: Node {0} Offset {1}'.format(node_index+1, node_offset))
#    emit_node_data() # Settings page, new node channel

@SOCKET_IO.on('set_node_scale')
def on_set_node_scale(data):
    '''Set node scale.'''
    node_index = data['node']
    node_scale = data['node_scale']
    INTERFACE.set_node_scale(node_index, node_scale)
    node_data = NodeData.query.filter_by(id=node_index).first()
    node_data.scale = node_scale
    DB.session.commit()
    server_log('Node scale set: Node {0} Scale {1}'.format(node_index+1, node_scale))
    emit_node_data() # Settings page, new node channel

@SOCKET_IO.on('add_heat')
def on_add_heat():
    '''Adds the next available heat number to the database.'''
    max_heat_id = DB.session.query(DB.func.max(Heat.heat_id)).scalar()
    for node in range(RACE.num_nodes): # Add next heat with pilots 1 thru 5
        DB.session.add(Heat(heat_id=max_heat_id+1, node_index=node, pilot_id=node+1))
    DB.session.commit()
    server_log('Heat added: Heat {0}'.format(max_heat_id+1))

@SOCKET_IO.on('set_pilot_position')
def on_set_pilot_position(data):
    '''Sets a new pilot in a heat.'''
    heat = data['heat']
    node_index = data['node']
    pilot = data['pilot']
    db_update = Heat.query.filter_by(heat_id=heat, node_index=node_index).first()
    db_update.pilot_id = pilot
    DB.session.commit()
    server_log('Pilot position set: Heat {0} Node {1} Pilot {2}'.format(heat, node_index+1, pilot))
    emit_heat_data() # Settings page, new pilot position in heats

@SOCKET_IO.on('add_pilot')
def on_add_pilot():
    '''Adds the next available pilot id number in the database.'''
    max_pilot_id = DB.session.query(DB.func.max(Pilot.pilot_id)).scalar()
    DB.session.add(Pilot(pilot_id=max_pilot_id+1, callsign='callsign{0}'.format(max_pilot_id+1), \
        phonetic='callsign{0}'.format(max_pilot_id+1), name='Pilot Name'))
    DB.session.commit()
    server_log('Pilot added: Pilot {0}'.format(max_pilot_id+1))

@SOCKET_IO.on('set_pilot_callsign')
def on_set_pilot_callsign(data):
    '''Gets pilot callsign to update database.'''
    pilot_id = data['pilot_id']
    callsign = data['callsign']
    db_update = Pilot.query.filter_by(pilot_id=pilot_id).first()
    db_update.callsign = callsign
    DB.session.commit()
    server_log('Pilot callsign set: Pilot {0} Callsign {1}'.format(pilot_id, callsign))
    emit_pilot_data() # Settings page, new pilot callsign
    emit_heat_data() # Settings page, new pilot callsign in heats

@SOCKET_IO.on('set_pilot_phonetic')
def on_set_pilot_phonetic(data):
    '''Gets pilot phonetic to update database.'''
    pilot_id = data['pilot_id']
    phonetic = data['phonetic']
    db_update = Pilot.query.filter_by(pilot_id=pilot_id).first()
    db_update.phonetic = phonetic
    DB.session.commit()
    server_log('Pilot phonetic set: Pilot {0} Phonetic {1}'.format(pilot_id, phonetic))
    emit_pilot_data() # Settings page, new pilot phonetic
    emit_heat_data() # Settings page, new pilot phonetic in heats. Needed?

@SOCKET_IO.on('set_pilot_name')
def on_set_pilot_name(data):
    '''Gets pilot name to update database.'''
    pilot_id = data['pilot_id']
    name = data['name']
    db_update = Pilot.query.filter_by(pilot_id=pilot_id).first()
    db_update.name = name
    DB.session.commit()
    server_log('Pilot name set: Pilot {0} Name {1}'.format(pilot_id, name))
    emit_pilot_data() # Settings page, new pilot name

@SOCKET_IO.on('speak_pilot')
def on_speak_pilot(data):
    '''Speaks the phonetic name of the pilot.'''
    pilot_id = data['pilot_id']
    phtext = Pilot.query.filter_by(pilot_id=pilot_id).first().phonetic
    emit_phonetic_text(phtext)
    server_log('Speak pilot: {0}'.format(phtext))

@SOCKET_IO.on('add_profile')
def on_add_profile():
    '''Adds new profile in the database.'''
    max_profile_id = DB.session.query(Profiles).count()+1
    DB.session.add(Profiles(name='New Profile %s' % max_profile_id,
                           description = 'New Profile %s' % max_profile_id,
                           c_offset=8,
                           c_threshold=90,
                           t_threshold=40,
                           f_ratio=100))
    DB.session.commit()
    on_set_profile(data={ 'profile': 'New Profile %s' % max_profile_id})

@SOCKET_IO.on('delete_profile')
def on_delete_profile():
    '''Delete profile'''
    if (DB.session.query(Profiles).count() > 1): # keep one profile
     last_profile = LastProfile.query.get(1).profile_id
     profile = Profiles.query.get(last_profile)
     DB.session.delete(profile)
     DB.session.commit()
     last_profile =  LastProfile.query.get(1)
     first_profile_id = Profiles.query.first().id
     last_profile.profile_id = first_profile_id
     DB.session.commit()
     profile =Profiles.query.get(first_profile_id)
     INTERFACE.set_calibration_threshold_global(profile.c_threshold)
     INTERFACE.set_calibration_offset_global(profile.c_offset)
     INTERFACE.set_trigger_threshold_global(profile.t_threshold)
     INTERFACE.set_filter_ratio_global(profile.f_ratio)
     emit_node_tuning()

@SOCKET_IO.on('set_profile_name')
def on_set_profile_name(data):
    ''' update profile name '''
    profile_name = data['profile_name']
    last_profile = LastProfile.query.get(1)
    profile = Profiles.query.filter_by(id=last_profile.profile_id).first()
    profile.name = profile_name
    DB.session.commit()
    server_log('set profile name %s' % (profile_name))
    emit_node_tuning()

@SOCKET_IO.on('set_profile_description')
def on_set_profile_description(data):
    ''' update profile description '''
    profile_description = data['profile_description']
    last_profile = LastProfile.query.get(1)
    profile = Profiles.query.filter_by(id=last_profile.profile_id).first()
    profile.description = profile_description
    DB.session.commit()
    server_log('set profile description %s for profile %s' %
               (profile_name, profile.name))
    emit_node_tuning()

@SOCKET_IO.on('set_calibration_threshold')
def on_set_calibration_threshold(data):
    '''Set Calibration Threshold.'''
    calibration_threshold = data['calibration_threshold']
    INTERFACE.set_calibration_threshold_global(calibration_threshold)
    last_profile = LastProfile.query.get(1)
    profile = Profiles.query.filter_by(id=last_profile.profile_id).first()
    profile.c_threshold = calibration_threshold
    DB.session.commit()
    server_log('Calibration threshold set: {0}'.format(calibration_threshold))
    emit_node_tuning()

@SOCKET_IO.on('set_calibration_offset')
def on_set_calibration_offset(data):
    '''Set Calibration Offset.'''
    calibration_offset = data['calibration_offset']
    INTERFACE.set_calibration_offset_global(calibration_offset)
    last_profile = LastProfile.query.get(1)
    profile = Profiles.query.filter_by(id=last_profile.profile_id).first()
    profile.c_offset = calibration_offset
    DB.session.commit()
    server_log('Calibration offset set: {0}'.format(calibration_offset))
    emit_node_tuning()

@SOCKET_IO.on('set_trigger_threshold')
def on_set_trigger_threshold(data):
    '''Set Trigger Threshold.'''
    trigger_threshold = data['trigger_threshold']
    INTERFACE.set_trigger_threshold_global(trigger_threshold)
    last_profile = LastProfile.query.get(1)
    profile = Profiles.query.filter_by(id=last_profile.profile_id).first()
    profile.t_threshold = trigger_threshold
    DB.session.commit()
    server_log('Trigger threshold set: {0}'.format(trigger_threshold))
    emit_node_tuning()

@SOCKET_IO.on('set_filter_ratio')
def on_set_filter_ratio(data):
    '''Set Trigger Threshold.'''
    filter_ratio = data['filter_ratio']
    INTERFACE.set_filter_ratio_global(filter_ratio)
    last_profile = LastProfile.query.get(1)
    profile = Profiles.query.filter_by(id=last_profile.profile_id).first()
    profile.f_ratio = filter_ratio
    DB.session.commit()
    server_log('Filter ratio set: {0}'.format(filter_ratio))
    emit_node_tuning()

@SOCKET_IO.on('reset_database')
def on_reset_database():
    '''Reset database.'''
    db_reset()

@SOCKET_IO.on('reset_database_keep_pilots')
def on_reset_database_keep_pilots():
    '''Reset database but keep pilots list.'''
    db_reset_keep_pilots()

@SOCKET_IO.on('reset_database_laps')
def on_reset_database_laps():
    '''Reset database laps only.'''
    db_reset_laps()

@SOCKET_IO.on('shutdown_pi')
def on_shutdown_pi():
    '''Shutdown the raspberry pi.'''
    server_log('Shutdown pi')
    os.system("sudo shutdown now")


@SOCKET_IO.on("set_profile")
def on_set_profile(data):
    ''' set current profile '''
    profile_val = data['profile']
    profile =Profiles.query.filter_by(name=profile_val).first()
    DB.session.flush()
    last_profile = LastProfile.query.get(1)
    last_profile.profile_id = profile.id
    DB.session.commit()
    INTERFACE.set_calibration_threshold_global(profile.c_threshold)
    INTERFACE.set_calibration_offset_global(profile.c_offset)
    INTERFACE.set_trigger_threshold_global(profile.t_threshold)
    emit_node_tuning()
    server_log("set tune paramas for profile '%s'" % profile_val)

@SOCKET_IO.on("set_race_mode")
def on_set_race_mode(data):
    race_mode = data['race_mode']
    race_format = RaceFormat.query.get(1)
    race_format.race_mode = race_mode
    DB.session.commit()
    server_log("set race mode to %s" % race_mode)

@SOCKET_IO.on("set_fix_race_time")
def on_set_fix_race_time(data):
    race_time = data['race_time']
    fix_race_time = RaceFormat.query.get(1)
    fix_race_time.race_time_sec = race_time
    DB.session.commit()
    server_log("set fixed time race to %s seconds" % race_time)

@SOCKET_IO.on("set_min_lap")
def on_set_min_lap(data):
    min_lap = data['min_lap']
    race_format = RaceFormat.query.get(1)
    race_format.min_lap_sec = min_lap
    DB.session.commit()
    server_log("set min lap time to %s seconds" % min_lap)

@SOCKET_IO.on("set_hide_stage_timer")
def on_set_hide_stage_timer(data):
    hide_stage_timer = data['hide_stage_timer']
    race_format = RaceFormat.query.get(1)
    race_format.hide_stage_timer = hide_stage_timer
    DB.session.commit()
    server_log("set start type to %s" % hide_stage_timer)

@SOCKET_IO.on("set_start_delay_min")
def on_set_start_delay(data):
    start_delay_min = data['start_delay_min']
    race_format = RaceFormat.query.get(1)
    race_format.start_delay_min = start_delay_min
    DB.session.commit()
    server_log("set start delay to %s" % start_delay_min)

@SOCKET_IO.on("set_start_delay_max")
def on_set_start_delay(data):
    start_delay_max = data['start_delay_max']
    race_format = RaceFormat.query.get(1)
    race_format.start_delay_max = start_delay_max
    DB.session.commit()
    server_log("set start delay to %s" % start_delay_max)

# Race management socket io events

@SOCKET_IO.on('prestage_race')
def on_prestage_race():
    '''Common race start events (do early to prevent processing delay when start is called)'''
    onoff(strip, Color(255,128,0)) #ORANGE for STAGING
    clear_laps() # Ensure laps are cleared before race start, shouldn't be needed
    emit_current_laps() # Race page, blank laps to the web client
    emit_leaderboard() # Race page, blank leaderboard to the web client
    INTERFACE.enable_calibration_mode() # Nodes reset triggers on next pass
    race_format = RaceFormat.query.get(1)
    DELAY = random.randint(race_format.start_delay_min, race_format.start_delay_max)

    SOCKET_IO.emit('prestage_ready', {
        'hide_stage_timer': race_format.hide_stage_timer,
        'start_delay': DELAY,
        'race_mode': race_format.race_mode,
        'race_time_sec': race_format.race_time_sec
    }) # Loop back to race page with chosen delay


@SOCKET_IO.on('stage_race')
def on_stage_race(data):
    '''Bounce a response back to client for determining response time'''
    SOCKET_IO.emit('stage_ready', data)

@SOCKET_IO.on('start_race')
def on_start_race(data):
    '''Starts the D5 race'''
    time.sleep(data['delay']) # TODO: Make this a non-blocking delay so race can be cancelled inside staging ***
    RACE.race_status = 1 # To enable registering passed laps
    global RACE_START # To redefine main program variable
    RACE_START = datetime.now() # Update the race start time stamp
    onoff(strip, Color(0,255,0)) #GREEN for GO
    emit_race_status() # Race page, to set race button states
    emit_node_data() # Settings page, node channel and triggers on the launch pads
    server_log('Race started at {0}'.format(RACE_START))

@SOCKET_IO.on('stop_race')
def on_race_status():
    '''Stops the race and stops registering laps.'''
    RACE.race_status = 2 # To stop registering passed laps, waiting for laps to be cleared
    SOCKET_IO.emit('stop_timer') # Loop back to race page to start the timer counting up
    server_log('Race stopped')
    emit_race_status() # Race page, to set race button states
    onoff(strip, Color(255,0,0)) #RED ON

@SOCKET_IO.on('save_laps')
def on_save_laps():
    '''Save current laps data to the database.'''
    # Get the last saved round for the current heat
    max_round = DB.session.query(DB.func.max(SavedRace.round_id)) \
            .filter_by(heat_id=RACE.current_heat).scalar()
    if max_round is None:
        max_round = 0
    # Loop through laps to copy to saved races
    for node in range(RACE.num_nodes):
        for lap in CurrentLap.query.filter_by(node_index=node).all():
            DB.session.add(SavedRace(round_id=max_round+1, heat_id=RACE.current_heat, \
                node_index=node, pilot_id=lap.pilot_id, lap_id=lap.lap_id, \
                lap_time_stamp=lap.lap_time_stamp, lap_time=lap.lap_time, \
                lap_time_formatted=lap.lap_time_formatted))
    DB.session.commit()
    server_log('Current laps saved: Heat {0} Round {1}'.format(RACE.current_heat, max_round+1))
    on_clear_laps() # Also clear the current laps

@SOCKET_IO.on('clear_laps')
def on_clear_laps():
    '''Clear the current laps due to false start or practice.'''
    clear_laps()
    emit_current_laps() # Race page, blank laps to the web client
    emit_leaderboard() # Race page, blank leaderboard to the web client
    emit_race_status() # Race page, to set race button states

def clear_laps():
    '''Clear the current laps due to false start or practice.'''
    RACE.race_status = 0 # Laps cleared, ready to start next race
    DB.session.query(CurrentLap).delete() # Clear out the current laps table
    DB.session.commit()
    server_log('Current laps cleared')

@SOCKET_IO.on('set_current_heat')
def on_set_current_heat(data):
    '''Update the current heat variable.'''
    new_heat_id = data['heat']
    RACE.current_heat = new_heat_id
    server_log('Current heat set: Heat {0}'.format(new_heat_id))
    emit_current_heat() # Race page, to update heat selection button
    emit_leaderboard() # Race page, to update callsigns in leaderboard

@SOCKET_IO.on('delete_lap')
def on_delete_lap(data):
    '''Delete a false lap.'''
    node_index = data['node']
    lap_id = data['lapid']
    max_lap = DB.session.query(DB.func.max(CurrentLap.lap_id)) \
        .filter_by(node_index=node_index).scalar()
    if lap_id is not max_lap:
        # Update the lap_time for the next lap
        previous_lap = CurrentLap.query.filter_by(node_index=node_index, lap_id=lap_id-1).first()
        next_lap = CurrentLap.query.filter_by(node_index=node_index, lap_id=lap_id+1).first()
        next_lap.lap_time = next_lap.lap_time_stamp - previous_lap.lap_time_stamp
        next_lap.lap_time_formatted = time_format(next_lap.lap_time)
        # Delete the false lap
        CurrentLap.query.filter_by(node_index=node_index, lap_id=lap_id).delete()
        # Update lap numbers
        for lap in CurrentLap.query.filter_by(node_index=node_index).all():
            if lap.lap_id > lap_id:
                lap.lap_id = lap.lap_id - 1
    else:
        # Delete the false lap
        CurrentLap.query.filter_by(node_index=node_index, lap_id=lap_id).delete()
    DB.session.commit()
    server_log('Lap deleted: Node {0} Lap {1}'.format(node_index, lap_id))
    emit_current_laps() # Race page, update web client
    emit_leaderboard() # Race page, update web client

@SOCKET_IO.on('simulate_lap')
def on_simulate_lap(data):
    '''Simulates a lap (for debug testing).'''
    node_index = data['node']
    server_log('Simulated lap: Node {0}'.format(node_index))
    INTERFACE.intf_simulate_lap(node_index)

@SOCKET_IO.on('LED_solid')
def on_LED_solid(data):
    '''LED Solid Color'''
    led_red = data['red']
    led_green = data['green']
    led_blue = data['blue']
    onoff(strip, Color(led_red,led_green,led_blue))

@SOCKET_IO.on('LED_chase')
def on_LED_chase(data):
    '''LED Solid Color'''
    led_red = data['red']
    led_green = data['green']
    led_blue = data['blue']
    theaterChase(strip, Color(led_red,led_green,led_blue))

@SOCKET_IO.on('LED_RB')
def on_LED_RB():
    rainbow(strip) #Rainbow

@SOCKET_IO.on('LED_RBCYCLE')
def on_LED_RBCYCLE():
    rainbowCycle(strip) #Rainbow Cycle

@SOCKET_IO.on('LED_RBCHASE')
def on_LED_RBCHASE():
    theaterChaseRainbow(strip) #Rainbow Chase

# Socket io emit functions

def emit_race_status():
    '''Emits race status.'''
    SOCKET_IO.emit('race_status', {'race_status': RACE.race_status})

def emit_node_data():
    '''Emits node data.'''
    SOCKET_IO.emit('node_data', {
        'frequency': [node.frequency for node in INTERFACE.nodes],
        'channel': [Frequency.query.filter_by(frequency=node.frequency).first().channel \
            for node in INTERFACE.nodes],
        'trigger_rssi': [node.trigger_rssi for node in INTERFACE.nodes],
        'peak_rssi': [node.peak_rssi for node in INTERFACE.nodes],
        'node_offset': [node.offset for node in NodeData.query.all()],
        'node_scale': [node.node_scale for node in INTERFACE.nodes]
    })

def emit_node_tuning():
    '''Emits node tuning values.'''
    last_profile = LastProfile.query.get(1)
    tune_val = Profiles.query.get(last_profile.profile_id)
    SOCKET_IO.emit('node_tuning', {
        'calibration_threshold': \
            tune_val.c_threshold,
        'calibration_offset': \
            tune_val.c_offset,
        'trigger_threshold': \
            tune_val.t_threshold,
        'filter_ratio': \
            tune_val.f_ratio,
        'profile_name':
            tune_val.name,
        'profile_description':
            tune_val.description
    })

def emit_current_laps():
    '''Emits current laps.'''
    current_laps = []
    # for node in DB.session.query(CurrentLap.node_index).distinct():
    for node in range(RACE.num_nodes):
        node_laps = []
        node_lap_times = []
        for lap in CurrentLap.query.filter_by(node_index=node).all():
            node_laps.append(lap.lap_id)
            node_lap_times.append(lap.lap_time_formatted)
        current_laps.append({'lap_id': node_laps, 'lap_time': node_lap_times})
    current_laps = {'node_index': current_laps}
    SOCKET_IO.emit('current_laps', current_laps)

def emit_leaderboard():
    '''Emits leaderboard.'''
    # Get the max laps for each pilot
    max_laps = []
    for node in range(RACE.num_nodes):
        max_lap = DB.session.query(DB.func.max(CurrentLap.lap_id)) \
            .filter_by(node_index=node).scalar()
        if max_lap is None:
            max_lap = 0
        max_laps.append(max_lap)
    # Get the total race time for each pilot
    total_time = []
    for node in range(RACE.num_nodes):
        if max_laps[node] is 0:
            total_time.append(0) # Add zero if no laps completed
        else:
            total_time.append(CurrentLap.query.filter_by(node_index=node, \
                lap_id=max_laps[node]).first().lap_time_stamp)
    # Get the last lap for each pilot
    last_lap = []
    for node in range(RACE.num_nodes):
        if max_laps[node] is 0:
            last_lap.append(0) # Add zero if no laps completed
        else:
            last_lap.append(CurrentLap.query.filter_by(node_index=node, \
                lap_id=max_laps[node]).first().lap_time)
    # Get the average lap time for each pilot
    average_lap = []
    for node in range(RACE.num_nodes):
        if max_laps[node] is 0:
            average_lap.append(0) # Add zero if no laps completed
        else:
            avg_lap = DB.session.query(DB.func.avg(CurrentLap.lap_time)) \
                .filter(CurrentLap.node_index == node, CurrentLap.lap_id != 0).scalar()
            average_lap.append(avg_lap)
    # Get the fastest lap time for each pilot
    fastest_lap = []
    for node in range(RACE.num_nodes):
        if max_laps[node] is 0:
            fastest_lap.append(0) # Add zero if no laps completed
        else:
            fast_lap = DB.session.query(DB.func.min(CurrentLap.lap_time)) \
                .filter(CurrentLap.node_index == node, CurrentLap.lap_id != 0).scalar()
            fastest_lap.append(fast_lap)
    # Get the pilot callsigns to add to sort
    callsigns = []
    for node in range(RACE.num_nodes):
        pilot_id = Heat.query.filter_by( \
            heat_id=RACE.current_heat, node_index=node).first().pilot_id
        callsigns.append(Pilot.query.filter_by(pilot_id=pilot_id).first().callsign)
    # Combine for sorting
    leaderboard = zip(callsigns, max_laps, total_time, last_lap, average_lap, fastest_lap)
    # Reverse sort max_laps x[1], then sort on total time x[2]
    leaderboard_sorted = sorted(leaderboard, key = lambda x: (-x[1], x[2]))

    SOCKET_IO.emit('leaderboard', {
        'position': [i+1 for i in range(RACE.num_nodes)],
        'callsign': [leaderboard_sorted[i][0] for i in range(RACE.num_nodes)],
        'laps': [leaderboard_sorted[i][1] for i in range(RACE.num_nodes)],
        'total_time': [time_format(leaderboard_sorted[i][2]) for i in range(RACE.num_nodes)],
        'last_lap': [time_format(leaderboard_sorted[i][3]) for i in range(RACE.num_nodes)],
        'behind': [(leaderboard_sorted[0][1] - leaderboard_sorted[i][1]) \
            for i in range(RACE.num_nodes)],
        'average_lap': [time_format(leaderboard_sorted[i][4]) for i in range(RACE.num_nodes)],
        'fastest_lap': [time_format(leaderboard_sorted[i][5]) for i in range(RACE.num_nodes)]
    })

def emit_heat_data():
    '''Emits heat data.'''
    current_heats = []
    for heat in Heat.query.with_entities(Heat.heat_id).distinct():
        pilots = []
        for node in range(RACE.num_nodes):
            pilot_id = Heat.query.filter_by(heat_id=heat.heat_id, node_index=node).first().pilot_id
            pilots.append(pilot_id)
        current_heats.append({'callsign': pilots})
    current_heats = {'heat_id': current_heats}
    SOCKET_IO.emit('heat_data', current_heats)

def emit_pilot_data():
    '''Emits pilot data.'''
    SOCKET_IO.emit('pilot_data', {
        'pilot_id': [pilot.pilot_id for pilot in Pilot.query.all()],
        'callsign': [pilot.callsign for pilot in Pilot.query.all()],
        'name': [pilot.name for pilot in Pilot.query.all()]
    })
    emit_heat_data()

def emit_current_heat():
    '''Emits the current heat.'''
    callsigns = []
    for node in range(RACE.num_nodes):
        pilot_id = Heat.query.filter_by( \
            heat_id=RACE.current_heat, node_index=node).first().pilot_id
        callsigns.append(Pilot.query.filter_by(pilot_id=pilot_id).first().callsign)

    SOCKET_IO.emit('current_heat', {
        'current_heat': RACE.current_heat,
        'callsign': callsigns
    })

def emit_phonetic_data(pilot_id, lap_id, lap_time):
    '''Emits phonetic data.'''
    phonetic_time = phonetictime_format(lap_time)
    phonetic_name = Pilot.query.filter_by(pilot_id=pilot_id).first().phonetic
    pilot_id = Pilot.query.filter_by(pilot_id=pilot_id).first().pilot_id
    SOCKET_IO.emit('phonetic_data', {'pilot': phonetic_name, 'pilot_id': pilot_id, 'lap': lap_id, 'phonetic': phonetic_time})

def emit_current_fix_race_time():
    ''' Emit current fixed time race time '''
    race_time_sec = RaceFormat.query.get(1).race_time_sec
    SOCKET_IO.emit('set_fix_race_time',{ fix_race_time: race_time_sec})

def emit_min_lap():
    ''' Emit minimum lap time '''
    min_lap_sec = RaceFormat.query.get(1).min_lap_sec
    SOCKET_IO.emit('set_min_lap',{ min_lap: min_lap_sec})

def emit_phonetic_text(phtext):
    '''Emits given phonetic text.'''
    SOCKET_IO.emit('speak_phonetic_text', {'text': phtext})

#
# Program Functions
#

def heartbeat_thread_function():
    '''Emits current rssi data.'''
    while True:
        SOCKET_IO.emit('heartbeat', INTERFACE.get_heartbeat_json())
        gevent.sleep(0.250)

def ms_from_race_start():
    '''Return milliseconds since race start.'''
    delta_time = datetime.now() - RACE_START
    milli_sec = (delta_time.days * 24 * 60 * 60 + delta_time.seconds) \
        * 1000 + delta_time.microseconds / 1000.0
    return milli_sec

def ms_from_program_start():
    '''Returns the elapsed milliseconds since the start of the program.'''
    delta_time = datetime.now() - PROGRAM_START
    milli_sec = (delta_time.days * 24 * 60 * 60 + delta_time.seconds) \
        * 1000 + delta_time.microseconds / 1000.0
    return milli_sec

def time_format(millis):
    '''Convert milliseconds to 00:00.000'''
    millis = int(millis)
    minutes = millis / 60000
    over = millis % 60000
    seconds = over / 1000
    over = over % 1000
    milliseconds = over
    return '{0:01d}:{1:02d}.{2:03d}'.format(minutes, seconds, milliseconds)

def phonetictime_format(millis):
    '''Convert milliseconds to phonetic'''
    millis = int(millis + 50)  # round to nearest tenth of a second
    minutes = millis / 60000
    over = millis % 60000
    seconds = over / 1000
    over = over % 1000
    tenths = over / 100

    if minutes > 0:
        return '{0:01d} {1:01d}.{2:01d}'.format(minutes, seconds, tenths)
    else:
        return '{0:01d}.{1:01d}'.format(seconds, tenths)

def pass_record_callback(node, ms_since_lap):
    '''Handles pass records from the nodes.'''
    server_log('Raw pass record: Node: {0}, MS Since Lap: {1}'.format(node.index, ms_since_lap))
    emit_node_data() # For updated triggers and peaks

    if RACE.race_status is 1:
        # Get the current pilot id on the node
        pilot_id = Heat.query.filter_by( \
            heat_id=RACE.current_heat, node_index=node.index).first().pilot_id

        # Calculate the lap time stamp, milliseconds since start of race
        lap_time_stamp = ms_from_race_start() - ms_since_lap

        # Get the last completed lap from the database
        last_lap_id = DB.session.query(DB.func.max(CurrentLap.lap_id)) \
            .filter_by(node_index=node.index).scalar()

        if last_lap_id is None: # No previous laps, this is the first pass
            # Lap zero represents the time from the launch pad to flying through the gate
            lap_time = lap_time_stamp
            lap_id = 0
        else: # This is a normal completed lap
            # Find the time stamp of the last lap completed
            last_lap_time_stamp = CurrentLap.query.filter_by( \
                node_index=node.index, lap_id=last_lap_id).first().lap_time_stamp
            # New lap time is the difference between the current time stamp and the last
            lap_time = lap_time_stamp - last_lap_time_stamp
            lap_id = last_lap_id + 1

        race_format = RaceFormat.query.get(1)
        min_lap = race_format.min_lap_sec
        if lap_time > (min_lap * 1000) or lap_id == 0:
            # Add the new lap to the database
            DB.session.add(CurrentLap(node_index=node.index, pilot_id=pilot_id, lap_id=lap_id, \
                lap_time_stamp=lap_time_stamp, lap_time=lap_time, \
                lap_time_formatted=time_format(lap_time)))
            DB.session.commit()

            server_log('Pass record: Node: {0}, Lap: {1}, Lap time: {2}' \
                .format(node.index, lap_id, time_format(lap_time)))
            emit_current_laps() # Updates all laps on the race page
            emit_leaderboard() # Updates leaderboard
            if lap_id > 0:
                emit_phonetic_data(pilot_id, lap_id, lap_time) # Sends phonetic data to be spoken
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
        else:
            server_log('Pass record dismissed: Node: {0}, Lap: {1}, Lap time: {2}' \
                .format(node.index, lap_id, time_format(lap_time)))

INTERFACE.pass_record_callback = pass_record_callback

def server_log(message):
    '''Messages emitted from the server script.'''
    print message
    SOCKET_IO.emit('hardware_log', message)

def hardware_log_callback(message):
    '''Message emitted from the delta 5 interface class.'''
    print message
    SOCKET_IO.emit('hardware_log', message)

INTERFACE.hardware_log_callback = hardware_log_callback

def default_frequencies():
    '''Set node frequencies, R1367 for 4, IMD for 5 or 6, Raceband for 7 or 8.'''
    frequencies_imd_5_6 = [5685, 5760, 5800, 5860, 5905, 5645]
    frequencies_raceband = [5658, 5695, 5732, 5769, 5806, 5843, 5880, 5917]
    frequencies_rb4 = [5658, 5732, 5843, 5880]
    for index, node in enumerate(INTERFACE.nodes):
        gevent.sleep(0.100)
        node_data = NodeData.query.filter_by(id=index).first()
        if RACE.num_nodes < 5:
            node_data.frequency = frequencies_rb4[index]
        elif RACE.num_nodes < 7:
            node_data.frequency = frequencies_imd_5_6[index]
        else:
            node_data.frequency = frequencies_raceband[index]

    server_log('Default frequencies set')

def assign_frequencies():
    '''Assign set frequencies to nodes'''
    for node in NodeData.query.all():
        gevent.sleep(0.100)
        INTERFACE.set_frequency(node.id, node.frequency)
        gevent.sleep(0.100)
        INTERFACE.set_node_scale(node.id, node.scale)

    server_log('Frequencies asigned to nodes')

def db_init():
    '''Initialize database.'''
    DB.create_all() # Creates tables from database classes/models
    db_reset_pilots()
    db_reset_heats()
    db_reset_frequencies()
    db_reset_current_laps()
    db_reset_saved_races()
    db_reset_profile()
    db_reset_default_profile()
    db_reset_fix_race_time()
    db_reset_node_values()
    assign_frequencies()
    server_log('Database initialized')

def db_reset():
    '''Resets database.'''
    db_reset_pilots()
    db_reset_heats()
    db_reset_frequencies()
    db_reset_current_laps()
    db_reset_saved_races()
    db_reset_profile()
    db_reset_default_profile()
    db_reset_fix_race_time()
    db_reset_node_values()
    assign_frequencies()
    server_log('Database reset')

def db_reset_keep_pilots():
    '''Resets database, keeps pilots.'''
    db_reset_heats()
    db_reset_frequencies()
    db_reset_current_laps()
    db_reset_saved_races()
    db_reset_fix_race_time()
    server_log('Database reset, pilots kept')

def db_reset_laps():
    '''Resets database laps only. '''
    db_reset_current_laps()
    db_reset_saved_races()
    server_log('Database reset, laps only')

def db_reset_pilots():
    '''Resets database pilots to default.'''
    DB.session.query(Pilot).delete()
    DB.session.add(Pilot(pilot_id='0', callsign='-', name='-None-', phonetic=""))
    for node in range(RACE.num_nodes):
        DB.session.add(Pilot(pilot_id=node+1, callsign='callsign{0}'.format(node+1), \
            name='Pilot Name', phonetic='callsign{0}'.format(node+1)))
    DB.session.commit()
    server_log('Database pilots reset')
def db_reset_heats():
    '''Resets database heats to default.'''
    DB.session.query(Heat).delete()
    for node in range(RACE.num_nodes):
        DB.session.add(Heat(heat_id=1, node_index=node, pilot_id=node+1))
    DB.session.commit()
    server_log('Database heats reset')
def db_reset_frequencies():
    '''Resets database frequencies to default.'''
    DB.session.query(Frequency).delete()
    # IMD Channels
    DB.session.add(Frequency(band='IMD', channel='E2', frequency='5685'))
    DB.session.add(Frequency(band='IMD', channel='F2', frequency='5760'))
    DB.session.add(Frequency(band='IMD', channel='F4', frequency='5800'))
    DB.session.add(Frequency(band='IMD', channel='F7', frequency='5860'))
    DB.session.add(Frequency(band='IMD', channel='E6', frequency='5905'))
    DB.session.add(Frequency(band='IMD', channel='E4', frequency='5645'))
    # Band R - Raceband
    DB.session.add(Frequency(band='R', channel='R1', frequency='5658'))
    DB.session.add(Frequency(band='R', channel='R2', frequency='5695'))
    DB.session.add(Frequency(band='R', channel='R3', frequency='5732'))
    DB.session.add(Frequency(band='R', channel='R4', frequency='5769'))
    DB.session.add(Frequency(band='R', channel='R5', frequency='5806'))
    DB.session.add(Frequency(band='R', channel='R6', frequency='5843'))
    DB.session.add(Frequency(band='R', channel='R7', frequency='5880'))
    DB.session.add(Frequency(band='R', channel='R8', frequency='5917'))
    # Band F - ImmersionRC, Iftron
    DB.session.add(Frequency(band='F', channel='F1', frequency='5740'))
    DB.session.add(Frequency(band='F', channel='F2', frequency='5760'))
    DB.session.add(Frequency(band='F', channel='F3', frequency='5780'))
    DB.session.add(Frequency(band='F', channel='F4', frequency='5800'))
    DB.session.add(Frequency(band='F', channel='F5', frequency='5820'))
    DB.session.add(Frequency(band='F', channel='F6', frequency='5840'))
    DB.session.add(Frequency(band='F', channel='F7', frequency='5860'))
    DB.session.add(Frequency(band='F', channel='F8', frequency='5880'))
    # Band E - HobbyKing, Foxtech
    DB.session.add(Frequency(band='E', channel='E1', frequency='5705'))
    DB.session.add(Frequency(band='E', channel='E2', frequency='5685'))
    DB.session.add(Frequency(band='E', channel='E3', frequency='5665'))
    DB.session.add(Frequency(band='E', channel='E4', frequency='5645'))
    DB.session.add(Frequency(band='E', channel='E5', frequency='5885'))
    DB.session.add(Frequency(band='E', channel='E6', frequency='5905'))
    DB.session.add(Frequency(band='E', channel='E7', frequency='5925'))
    DB.session.add(Frequency(band='E', channel='E8', frequency='5945'))
    # Band B - FlyCamOne Europe
    DB.session.add(Frequency(band='B', channel='B1', frequency='5733'))
    DB.session.add(Frequency(band='B', channel='B2', frequency='5752'))
    DB.session.add(Frequency(band='B', channel='B3', frequency='5771'))
    DB.session.add(Frequency(band='B', channel='B4', frequency='5790'))
    DB.session.add(Frequency(band='B', channel='B5', frequency='5809'))
    DB.session.add(Frequency(band='B', channel='B6', frequency='5828'))
    DB.session.add(Frequency(band='B', channel='B7', frequency='5847'))
    DB.session.add(Frequency(band='B', channel='B8', frequency='5866'))
    # Band A - Team BlackSheep, RangeVideo, SpyHawk, FlyCamOne USA
    DB.session.add(Frequency(band='A', channel='A1', frequency='5865'))
    DB.session.add(Frequency(band='A', channel='A2', frequency='5845'))
    DB.session.add(Frequency(band='A', channel='A3', frequency='5825'))
    DB.session.add(Frequency(band='A', channel='A4', frequency='5805'))
    DB.session.add(Frequency(band='A', channel='A5', frequency='5785'))
    DB.session.add(Frequency(band='A', channel='A6', frequency='5765'))
    DB.session.add(Frequency(band='A', channel='A7', frequency='5745'))
    DB.session.add(Frequency(band='A', channel='A8', frequency='5725'))
    # Band L - Lowband
    DB.session.add(Frequency(band='L', channel='L1', frequency='5362'))
    DB.session.add(Frequency(band='L', channel='L2', frequency='5399'))
    DB.session.add(Frequency(band='L', channel='L3', frequency='5436'))
    DB.session.add(Frequency(band='L', channel='L4', frequency='5473'))
    DB.session.add(Frequency(band='L', channel='L5', frequency='5510'))
    DB.session.add(Frequency(band='L', channel='L6', frequency='5547'))
    DB.session.add(Frequency(band='L', channel='L7', frequency='5584'))
    DB.session.add(Frequency(band='L', channel='L8', frequency='5621'))
    DB.session.commit()
    server_log('Database frequencies reset')

def db_reset_current_laps():
    '''Resets database current laps to default.'''
    DB.session.query(CurrentLap).delete()
    DB.session.commit()
    server_log('Database current laps reset')

def db_reset_saved_races():
    '''Resets database saved races to default.'''
    DB.session.query(SavedRace).delete()
    DB.session.commit()
    server_log('Database saved races reset')

def db_reset_profile():
    '''Set default profile'''
    DB.session.query(Profiles).delete()
    DB.session.add(Profiles(name="Outdoor 25mW",
                             description ="High speed, 25mW, open area",
                             c_offset=8,
                             c_threshold=65,
                             t_threshold=40,
                             f_ratio=100))
    DB.session.add(Profiles(name="Indoor 25mW",
                             description ="Low speed, 25mW, enclosed area",
                             c_offset=8,
                             c_threshold=65,
                             t_threshold=40,
                             f_ratio=10))
    DB.session.add(Profiles(name="Outdoor 200mW",
                             description ="High speed, 200mW, open area",
                             c_offset=8,
                             c_threshold=90,
                             t_threshold=40,
                             f_ratio=100))
    DB.session.add(Profiles(name="default 600mW",
                             description ="High speed, 600mW, open area",
                             c_offset=8,
                             c_threshold=100,
                             t_threshold=40,
                             f_ratio=100))
    DB.session.commit()
    server_log("Database set default profiles for 25,200,600 mW races")

def db_reset_default_profile():
    DB.session.query(LastProfile).delete()
    DB.session.add(LastProfile(profile_id=1))
    DB.session.commit()
    server_log("Database set default profile on default 25mW race")

def db_reset_fix_race_time():
    DB.session.query(RaceFormat).delete()
    DB.session.add(RaceFormat(race_mode=0,
                             race_time_sec=120,
                             min_lap_sec=0,
                             hide_stage_timer=1,
                             start_delay_min=2,
                             start_delay_max=5))
    DB.session.commit()
    server_log("Database set fixed time race to 120 sec (2 minutes)")

def db_reset_node_values():
    DB.session.query(NodeData).delete()
    for node in range(RACE.num_nodes):
        DB.session.add(NodeData(id=node,
                                frequency=0,
                                offset=0,
                                scale=1000))
    DB.session.commit()
    default_frequencies()
    server_log("Database cleared node correction")

#
# Program Initialize
#

# Save number of nodes found
RACE.num_nodes = len(INTERFACE.nodes)
print 'Number of nodes found: {0}'.format(RACE.num_nodes)

# Delay to get I2C addresses through interface class initialization
gevent.sleep(0.500)

# Create database if it doesn't exist
if not os.path.exists('database.db'):
    db_init()
else:
	# Set frequencies and load node correction data
	assign_frequencies()

# Clear any current laps from the database on each program start
# DB session commit needed to prevent 'application context' errors
db_reset_current_laps()

# Send initial profile values to nodes
last_profile = LastProfile.query.get(1)
tune_val = Profiles.query.get(last_profile.profile_id)
INTERFACE.set_calibration_threshold_global(tune_val.c_threshold)
INTERFACE.set_calibration_offset_global(tune_val.c_offset)
INTERFACE.set_trigger_threshold_global(tune_val.t_threshold)
INTERFACE.set_filter_ratio_global(tune_val.f_ratio)

# Test data - Current laps
# DB.session.add(CurrentLap(node_index=2, pilot_id=2, lap_id=0, lap_time_stamp=1000, lap_time=1000, lap_time_formatted=time_format(1000)))
# DB.session.add(CurrentLap(node_index=2, pilot_id=2, lap_id=1, lap_time_stamp=11000, lap_time=10000, lap_time_formatted=time_format(10000)))
# DB.session.add(CurrentLap(node_index=2, pilot_id=2, lap_id=2, lap_time_stamp=21000, lap_time=10000, lap_time_formatted=time_format(10000)))
# DB.session.add(CurrentLap(node_index=3, pilot_id=3, lap_id=0, lap_time_stamp=1000, lap_time=1000, lap_time_formatted=time_format(1000)))
# DB.session.add(CurrentLap(node_index=3, pilot_id=3, lap_id=1, lap_time_stamp=12000, lap_time=11000, lap_time_formatted=time_format(11000)))
# DB.session.add(CurrentLap(node_index=3, pilot_id=3, lap_id=2, lap_time_stamp=24000, lap_time=12000, lap_time_formatted=time_format(12000)))
# DB.session.add(CurrentLap(node_index=4, pilot_id=4, lap_id=0, lap_time_stamp=1000, lap_time=1000, lap_time_formatted=time_format(1000)))
# DB.session.add(CurrentLap(node_index=4, pilot_id=4, lap_id=1, lap_time_stamp=12000, lap_time=11000, lap_time_formatted=time_format(11000)))
# DB.session.add(CurrentLap(node_index=1, pilot_id=1, lap_id=0, lap_time_stamp=1000, lap_time=1000, lap_time_formatted=time_format(1000)))
# DB.session.add(CurrentLap(node_index=1, pilot_id=1, lap_id=1, lap_time_stamp=13000, lap_time=12000, lap_time_formatted=time_format(12000)))
# DB.session.commit()

# Test data - SavedRace
# db_init()
# on_add_heat()
# DB.session.add(SavedRace(round_id=1, heat_id=2, node_index=2, pilot_id=2, lap_id=0, lap_time_stamp=1000, lap_time=1000, lap_time_formatted=time_format(1000)))
# DB.session.add(SavedRace(round_id=1, heat_id=2, node_index=2, pilot_id=2, lap_id=1, lap_time_stamp=15000, lap_time=14000, lap_time_formatted=time_format(14000)))
# DB.session.add(SavedRace(round_id=1, heat_id=2, node_index=2, pilot_id=2, lap_id=2, lap_time_stamp=30000, lap_time=15000, lap_time_formatted=time_format(15000)))
# DB.session.add(SavedRace(round_id=1, heat_id=2, node_index=3, pilot_id=3, lap_id=0, lap_time_stamp=1500, lap_time=1500, lap_time_formatted=time_format(1500)))
# DB.session.add(SavedRace(round_id=1, heat_id=2, node_index=3, pilot_id=3, lap_id=1, lap_time_stamp=15000, lap_time=13500, lap_time_formatted=time_format(13500)))
# DB.session.add(SavedRace(round_id=1, heat_id=2, node_index=1, pilot_id=1, lap_id=0, lap_time_stamp=750, lap_time=750, lap_time_formatted=time_format(750)))
# DB.session.add(SavedRace(round_id=1, heat_id=2, node_index=1, pilot_id=1, lap_id=1, lap_time_stamp=10750, lap_time=10000, lap_time_formatted=time_format(10000)))
# DB.session.commit()
# DB.session.add(SavedRace(round_id=1, heat_id=1, node_index=2, pilot_id=2, lap_id=0, lap_time_stamp=1000, lap_time=1000, lap_time_formatted=time_format(1000)))
# DB.session.add(SavedRace(round_id=1, heat_id=1, node_index=2, pilot_id=2, lap_id=1, lap_time_stamp=15000, lap_time=14000, lap_time_formatted=time_format(14000)))
# DB.session.add(SavedRace(round_id=1, heat_id=1, node_index=2, pilot_id=2, lap_id=2, lap_time_stamp=30000, lap_time=15000, lap_time_formatted=time_format(15000)))
# DB.session.add(SavedRace(round_id=1, heat_id=1, node_index=3, pilot_id=3, lap_id=0, lap_time_stamp=1500, lap_time=1500, lap_time_formatted=time_format(1500)))
# DB.session.add(SavedRace(round_id=1, heat_id=1, node_index=3, pilot_id=3, lap_id=1, lap_time_stamp=15000, lap_time=13500, lap_time_formatted=time_format(13500)))
# DB.session.add(SavedRace(round_id=1, heat_id=1, node_index=1, pilot_id=1, lap_id=0, lap_time_stamp=750, lap_time=750, lap_time_formatted=time_format(750)))
# DB.session.add(SavedRace(round_id=1, heat_id=1, node_index=1, pilot_id=1, lap_id=1, lap_time_stamp=10750, lap_time=10000, lap_time_formatted=time_format(10000)))
# DB.session.commit()
# DB.session.add(SavedRace(round_id=2, heat_id=1, node_index=2, pilot_id=2, lap_id=0, lap_time_stamp=1000, lap_time=1000, lap_time_formatted=time_format(1000)))
# DB.session.add(SavedRace(round_id=2, heat_id=1, node_index=2, pilot_id=2, lap_id=1, lap_time_stamp=16000, lap_time=15000, lap_time_formatted=time_format(15000)))
# DB.session.add(SavedRace(round_id=2, heat_id=1, node_index=2, pilot_id=2, lap_id=2, lap_time_stamp=31000, lap_time=16000, lap_time_formatted=time_format(16000)))
# DB.session.add(SavedRace(round_id=2, heat_id=1, node_index=3, pilot_id=3, lap_id=0, lap_time_stamp=1500, lap_time=1500, lap_time_formatted=time_format(1500)))
# DB.session.add(SavedRace(round_id=2, heat_id=1, node_index=3, pilot_id=3, lap_id=1, lap_time_stamp=16000, lap_time=14500, lap_time_formatted=time_format(14500)))
# DB.session.add(SavedRace(round_id=2, heat_id=1, node_index=1, pilot_id=1, lap_id=0, lap_time_stamp=750, lap_time=750, lap_time_formatted=time_format(750)))
# DB.session.add(SavedRace(round_id=2, heat_id=1, node_index=1, pilot_id=1, lap_id=1, lap_time_stamp=11750, lap_time=11000, lap_time_formatted=time_format(11000)))
# DB.session.commit()

print 'Server ready'

if __name__ == '__main__':
    SOCKET_IO.run(APP, host='0.0.0.0', port=80, debug=True, use_reloader=False)
