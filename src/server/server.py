'''RotorHazard server script'''
RELEASE_VERSION = "1.2.0 (dev)" # Public release version code
SERVER_API = 12 # Server API version
NODE_API_BEST = 15 # Most recent node API

import os
import sys
import shutil
import base64
import subprocess
from datetime import datetime
from datetime import timedelta
from functools import wraps
from collections import OrderedDict

from flask import Flask, render_template, request, Response
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy

import gevent
import gevent.monkey
gevent.monkey.patch_all()
import gevent.timeout

import random
import json

# LED imports
import time
from neopixel import *
import signal

sys.path.append('../interface')
sys.path.append('/home/pi/RotorHazard/src/interface')  # Needed to run on startup

from RHInterface import get_hardware_interface
from RHRace import get_race_state

APP = Flask(__name__, static_url_path='/static')
APP.config['SECRET_KEY'] = 'secret!'
SOCKET_IO = SocketIO(APP, async_mode='gevent')

HEARTBEAT_THREAD = None

PILOT_ID_NONE = 0  # indicator value for no pilot configured
HEAT_ID_NONE = 0  # indicator value for practice heat
CLASS_ID_NONE = 0  # indicator value for unclassified heat
FREQUENCY_ID_NONE = 0  # indicator value for node disabled

EVENT_RESULTS_CACHE = {} # Cache of results page leaderboards
EVENT_RESULTS_CACHE_VALID = False # Whether cache is valid (False = regenerate cache)

DB_FILE_NAME = 'database.db'
DB_BKP_DIR_NAME = 'db_bkp'
CONFIG_FILE_NAME = 'config.json'
LANGUAGE_FILE_NAME = 'language.json'
IMDTABLER_JAR_NAME = 'static/IMDTabler.jar'

TEAM_NAMES_LIST = [str(unichr(i)) for i in range(65, 91)]  # list of 'A' to 'Z' strings
DEF_TEAM_NAME = 'A'  # default team

BASEDIR = os.path.abspath(os.path.dirname(__file__))
APP.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASEDIR, DB_FILE_NAME)
APP.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
DB = SQLAlchemy(APP)

Config = {}
Config['GENERAL'] = {}
Config['LED'] = {}

# LED strip configuration:
Config['LED']['LED_COUNT']      = 150      # Number of LED pixels.
Config['LED']['LED_PIN']        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
Config['LED']['LED_FREQ_HZ']    = 800000  # LED signal frequency in hertz (usually 800khz)
Config['LED']['LED_DMA']        = 10      # DMA channel to use for generating signal (try 10)
Config['LED']['LED_BRIGHTNESS'] = 255     # Set to 0 for darkest and 255 for brightest
Config['LED']['LED_INVERT']     = False   # True to invert the signal (when using NPN transistor level shift)
Config['LED']['LED_CHANNEL']    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
Config['LED']['LED_STRIP']      = ws.WS2811_STRIP_GRB   # Strip type and colour ordering

# other default configurations
Config['GENERAL']['HTTP_PORT'] = 5000
Config['GENERAL']['ADMIN_USERNAME'] = 'admin'
Config['GENERAL']['ADMIN_PASSWORD'] = 'rotorhazard'
Config['GENERAL']['DEBUG'] = False

# override defaults above with config from file
try:
    with open(CONFIG_FILE_NAME, 'r') as f:
        ExternalConfig = json.load(f)
    Config['GENERAL'].update(ExternalConfig['GENERAL'])
    Config['LED'].update(ExternalConfig['LED'])
    Config['GENERAL']['configFile'] = 1
    print 'Configuration file imported'
    APP.config['SECRET_KEY'] = Config['GENERAL']['SECRET_KEY']
except IOError:
    Config['GENERAL']['configFile'] = 0
    print 'No configuration file found, using defaults'
except ValueError:
    Config['GENERAL']['configFile'] = -1
    print 'Configuration file invalid, using defaults'


INTERFACE = get_hardware_interface()
RACE = get_race_state() # For storing race management variables

PROGRAM_START = datetime.now()
RACE_START = datetime.now() # Updated on race start commands
RACE_DURATION_MS = 0 # calculated when race is stopped

Race_laps_winner_name = None  # set to name of winner in first-to-X-laps race
RACE_STATUS_TIED_STR = 'Race is tied; continuing'  # shown when Most Laps Wins race tied
RACE_STATUS_CROSSING = 'Waiting for cross'  # indicator for Most Laps Wins race

Use_imdtabler_jar_flag = False  # set True if IMDTabler.jar is available

#
# Translation functions
#

Languages = {}
# Load language file
try:
    with open(LANGUAGE_FILE_NAME, 'r') as f:
        Languages = json.load(f)
    print 'Language file imported'
except IOError:
    print 'No language file found, using defaults'
except ValueError:
    print 'Language file invalid, using defaults'

def __(text, domain=''):
    # return translated string
    if not domain:
        lang = getOption('currentLanguage')

    if lang:
        if lang in Languages:
            if text in Languages[lang]['values']:
                return Languages[lang]['values'][text]
    return text

def getLanguages():
    # get list of available languages
    langs = []
    for lang in Languages:
        l = {}
        l['id'] = lang
        l['name'] = Languages[lang]['name']
        langs.append(l)
    return langs

def getAllLanguages():
    # return full language dictionary
    return Languages

#
# Server Info
#

def buildServerInfo():
    serverInfo = {}

    serverInfo['about_html'] = "<ul>"

    # Release Version
    serverInfo['release_version'] = RELEASE_VERSION
    serverInfo['about_html'] += "<li>" + __("Version") + ": " + str(RELEASE_VERSION) + "</li>"

    # Server API
    serverInfo['server_api'] = SERVER_API
    serverInfo['about_html'] += "<li>" + __("Server API") + ": " + str(SERVER_API) + "</li>"

    # Node API levels
    node_api_level = False
    serverInfo['node_api_match'] = True
    if INTERFACE.nodes[0].api_level:
        node_api_level = INTERFACE.nodes[0].api_level
        serverInfo['node_api_lowest'] = node_api_level

        serverInfo['node_api_levels'] = []
        for node in INTERFACE.nodes:
            serverInfo['node_api_levels'].append(node.api_level)

            if node.api_level is not node_api_level:
                serverInfo['node_api_match'] = False

            if node.api_level < serverInfo['node_api_lowest']:
                serverInfo['node_api_lowest'] = node.api_level

    serverInfo['about_html'] += "<li>" + __("Node API") + ": "
    if node_api_level:
        if serverInfo['node_api_match']:
            serverInfo['about_html'] += str(node_api_level)
        else:
            serverInfo['about_html'] += "[ "
            for idx, level in serverInfo['node_api_levels']:
                serverInfo['about_html'] += str(idx+1) + ":" + str(level) + " "
            serverInfo['about_html'] += "]"
    else:
        serverInfo['about_html'] += "None (Delta5)"

    serverInfo['about_html'] += "</li>"

    serverInfo['node_api_best'] = NODE_API_BEST
    if serverInfo['node_api_match'] is False or node_api_level < NODE_API_BEST:
        # Show Recommended API notice
        serverInfo['about_html'] += "<li><strong>" + __("Node Update Available") + ": " + str(NODE_API_BEST) + "</strong></li>"

    serverInfo['about_html'] += "</ul>"

    return serverInfo


#
# LED Code
#

def signal_handler(signal, frame):
        colorWipe(strip, Color(0,0,0))
        sys.exit(0)

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
strip = Adafruit_NeoPixel(Config['LED']['LED_COUNT'], Config['LED']['LED_PIN'], Config['LED']['LED_FREQ_HZ'], Config['LED']['LED_DMA'], Config['LED']['LED_INVERT'], Config['LED']['LED_BRIGHTNESS'], Config['LED']['LED_CHANNEL'], Config['LED']['LED_STRIP'])
# Intialize the library (must be called once before other functions).
strip.begin()


#
# Database Models
#

class Pilot(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    callsign = DB.Column(DB.String(80), unique=True, nullable=False)
    team = DB.Column(DB.String(80), nullable=False, default=DEF_TEAM_NAME)
    phonetic = DB.Column(DB.String(80), nullable=False)
    name = DB.Column(DB.String(120), nullable=False)

    def __repr__(self):
        return '<Pilot %r>' % self.id

class Heat(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    heat_id = DB.Column(DB.Integer, nullable=False)
    node_index = DB.Column(DB.Integer, nullable=False)
    pilot_id = DB.Column(DB.Integer, nullable=False)
    note = DB.Column(DB.String(80), nullable=True)
    class_id = DB.Column(DB.Integer, nullable=False)

    def __repr__(self):
        return '<Heat %r>' % self.heat_id

class RaceClass(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column(DB.String(80), nullable=True)
    description = DB.Column(DB.String(256), nullable=True)
    format_id = DB.Column(DB.Integer, nullable=False)

    def __repr__(self):
        return '<RaceClass %r>' % self.id

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
    class_id = DB.Column(DB.Integer, nullable=False)
    node_index = DB.Column(DB.Integer, nullable=False)
    pilot_id = DB.Column(DB.Integer, nullable=False)
    format_id = DB.Column(DB.Integer, nullable=False)
    lap_id = DB.Column(DB.Integer, nullable=False)
    lap_time_stamp = DB.Column(DB.Integer, nullable=False)
    lap_time = DB.Column(DB.Integer, nullable=False)
    lap_time_formatted = DB.Column(DB.Integer, nullable=False)

    def __repr__(self):
        return '<SavedRace %r>' % self.round_id

class Profiles(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column(DB.String(80), unique=True, nullable=False)
    description = DB.Column(DB.String(256), nullable=True)
    frequencies = DB.Column(DB.String(80), nullable=False)
    enter_ats = DB.Column(DB.String(80), nullable=True)
    exit_ats = DB.Column(DB.String(80), nullable=True)
    f_ratio = DB.Column(DB.Integer, nullable=True)

class RaceFormat(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column(DB.String(80), unique=True, nullable=False)
    race_mode = DB.Column(DB.Integer, nullable=False)
    race_time_sec = DB.Column(DB.Integer, nullable=False)
    start_delay_min = DB.Column(DB.Integer, nullable=False)
    start_delay_max = DB.Column(DB.Integer, nullable=False)
    number_laps_win = DB.Column(DB.Integer, nullable=False)
    win_condition = DB.Column(DB.Integer, nullable=False)
    team_racing_mode = DB.Column(DB.Boolean, nullable=False)

WIN_CONDITION_NONE = 0
WIN_CONDITION_MOST_LAPS = 1
WIN_CONDITION_FIRST_TO_LAP_X = 2
WIN_CONDITION_FASTEST_LAP = 3 # Not yet implemented
WIN_CONDITION_FASTEST_3_CONSECUTIVE = 4 # Not yet implemented

class GlobalSettings(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    option_name = DB.Column(DB.String(40), nullable=False)
    option_value = DB.Column(DB.String(256), nullable=False)

#
# Option helpers
#

def getOption(option, default_value=False):
    try:
        settings = GlobalSettings.query.filter_by(option_name=option).first()
        if settings:
            return settings.option_value
        else:
            return default_value
    except:
        return default_value

def setOption(option, value):
    settings = GlobalSettings.query.filter_by(option_name=option).first()
    if settings:
        settings.option_value = value
    else:
        DB.session.add(GlobalSettings(option_name=option, option_value=value))
    DB.session.commit()

#
# Authentication
#

def check_auth(username, password):
    '''Check if a username password combination is valid.'''
    return username == Config['GENERAL']['ADMIN_USERNAME'] and password == Config['GENERAL']['ADMIN_PASSWORD']

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

@APP.route('/')
def index():
    '''Route to home page.'''
    return render_template('home.html', serverInfo=serverInfo, getOption=getOption, __=__)

@APP.route('/heats')
def heats():
    '''Route to heat summary page.'''
    return render_template('heats.html', serverInfo=serverInfo, getOption=getOption, __=__)

@APP.route('/results')
def results():
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
    return render_template('rounds.html', serverInfo=serverInfo, getOption=getOption, __=__)

@APP.route('/race')
@requires_auth
def race():
    '''Route to race management page.'''
    return render_template('race.html', serverInfo=serverInfo, getOption=getOption, __=__,
        num_nodes=RACE.num_nodes,
        current_heat=RACE.current_heat,
        heats=Heat, pilots=Pilot,
        frequencies=[node.frequency for node in INTERFACE.nodes])

@APP.route('/current')
def racepublic():
    '''Route to race management page.'''
    return render_template('racepublic.html', serverInfo=serverInfo, getOption=getOption, __=__,
        num_nodes=RACE.num_nodes)

@APP.route('/settings')
@requires_auth
def settings():
    '''Route to settings page.'''

    return render_template('settings.html', serverInfo=serverInfo, getOption=getOption, __=__,
        num_nodes=RACE.num_nodes,
        ConfigFile=Config['GENERAL']['configFile'],
        Debug=Config['GENERAL']['DEBUG'])

@APP.route('/imdtabler')
def imdtabler():
    '''Route to IMDTabler page.'''

    return render_template('imdtabler.html', serverInfo=serverInfo, getOption=getOption, __=__)

# Debug Routes

@APP.route('/hardwarelog')
@requires_auth
def hardwarelog():
    '''Route to hardware log page.'''
    return render_template('hardwarelog.html', serverInfo=serverInfo, getOption=getOption, __=__)

@APP.route('/database')
@requires_auth
def database():
    '''Route to database page.'''
    return render_template('database.html', serverInfo=serverInfo, getOption=getOption, __=__,
        pilots=Pilot,
        heats=Heat,
        race_class=RaceClass,
        currentlaps=CurrentLap,
        savedraces=SavedRace,
        profiles=Profiles,
        race_format=RaceFormat,
        globalSettings=GlobalSettings)

#
# Socket IO Events
#

@SOCKET_IO.on('connect')
def connect_handler():
    '''Starts the interface and a heartbeat thread for rssi.'''
    server_log('Client connected')
    heartbeat_thread_function.iter_tracker = 0  # declare/init variables for HB function
    heartbeat_thread_function.imdtabler_flag = False
    INTERFACE.start()
    global HEARTBEAT_THREAD
    if HEARTBEAT_THREAD is None:
        HEARTBEAT_THREAD = gevent.spawn(heartbeat_thread_function)
        server_log('Heartbeat thread started')

@SOCKET_IO.on('disconnect')
def disconnect_handler():
    '''Emit disconnect event.'''
    server_log('Client disconnected')

@SOCKET_IO.on('load_data')
def on_load_data(data):
    '''Allow pages to load needed data'''
    load_types = data['load_types']
    for load_type in load_types:
        if load_type == 'node_data':
            emit_node_data(nobroadcast=True)
        elif load_type == 'frequency_data':
            emit_frequency_data(nobroadcast=True)
        elif load_type == 'heat_data':
            emit_heat_data(nobroadcast=True)
        elif load_type == 'class_data':
            emit_class_data(nobroadcast=True)
        elif load_type == 'pilot_data':
            emit_pilot_data(nobroadcast=True)
        elif load_type == 'round_data':
            emit_round_data(nobroadcast=True)
        elif load_type == 'race_format':
            emit_race_format(nobroadcast=True)
        elif load_type == 'node_tuning':
            emit_node_tuning(nobroadcast=True)
        elif load_type == 'enter_and_exit_at_levels':
            emit_enter_and_exit_at_levels(nobroadcast=True)
        elif load_type == 'min_lap':
            emit_min_lap(nobroadcast=True)
        elif load_type == 'leaderboard':
            emit_leaderboard(nobroadcast=True)
        elif load_type == 'current_laps':
            emit_current_laps(nobroadcast=True)
        elif load_type == 'race_status':
            emit_race_status(nobroadcast=True)
        elif load_type == 'current_heat':
            emit_current_heat(nobroadcast=True)
        elif load_type == 'team_racing_stat_if_enb':
            emit_team_racing_stat_if_enb(nobroadcast=True)
        elif load_type == 'language':
            emit_language(nobroadcast=True)
        elif load_type == 'all_languages':
            emit_all_languages(nobroadcast=True)
        elif load_type == 'imdtabler_page':
            emit_imdtabler_page(nobroadcast=True)

@SOCKET_IO.on('broadcast_message')
def on_broadcast_message(data):
    emit_priority_message(data['message'], data['interrupt'])

# Settings socket io events

@SOCKET_IO.on('set_frequency')
def on_set_frequency(data):
    '''Set node frequency.'''
    node_index = data['node']
    frequency = data['frequency']

    current_profile = int(getOption("currentProfile"))
    profile = Profiles.query.get(current_profile)
    freqs = json.loads(profile.frequencies)
    freqs["f"][node_index] = frequency
    profile.frequencies = json.dumps(freqs)

    DB.session.commit()

    '''Set node frequency.'''
    server_log('Frequency set: Node {0} Frequency {1}'.format(node_index+1, frequency))
    INTERFACE.set_frequency(node_index, frequency)
    emit_frequency_data()

@SOCKET_IO.on('set_frequency_preset')
def on_set_frequency_preset(data):
    ''' Apply preset frequencies '''
    freqs = []
    if data['preset'] == 'All-N1':
        current_profile = int(getOption("currentProfile"))
        profile = Profiles.query.get(current_profile)
        profile_freqs = json.loads(profile.frequencies)
        frequency = profile_freqs["f"][0]
        for idx in range(RACE.num_nodes):
            freqs.append(frequency)
    else:
        if data['preset'] == 'RB-4':
            freqs = [5658, 5732, 5843, 5880, FREQUENCY_ID_NONE, FREQUENCY_ID_NONE, FREQUENCY_ID_NONE, FREQUENCY_ID_NONE]
        elif data['preset'] == 'RB-8':
            freqs = [5658, 5695, 5732, 5769, 5806, 5843, 5880, 5917]
        elif data['preset'] == 'IMD5C':
            freqs = [5658, 5695, 5760, 5800, 5885, FREQUENCY_ID_NONE, FREQUENCY_ID_NONE, FREQUENCY_ID_NONE]
        else: #IMD6C is default
            freqs = [5658, 5695, 5760, 5800, 5880, 5917, FREQUENCY_ID_NONE, FREQUENCY_ID_NONE]

    set_all_frequencies(freqs)
    emit_frequency_data()
    hardware_set_all_frequencies(freqs)

def set_all_frequencies(freqs):
    ''' Set frequencies for all nodes (but do not update hardware) '''
    # Set DB
    current_profile = int(getOption("currentProfile"))
    profile = Profiles.query.get(current_profile)
    profile_freqs = json.loads(profile.frequencies)

    for idx in range(RACE.num_nodes):
        profile_freqs["f"][idx] = freqs[idx]
        server_log('Frequency set: Node {0} Frequency {1}'.format(idx+1, freqs[idx]))

    profile.frequencies = json.dumps(profile_freqs)
    DB.session.commit()

def hardware_set_all_frequencies(freqs):
    '''do hardware update for frequencies'''
    for idx in range(RACE.num_nodes):
        INTERFACE.set_frequency(idx, freqs[idx])

@SOCKET_IO.on('set_enter_at_level')
def on_set_enter_at_level(data):
    '''Set node enter-at level.'''
    node_index = data['node']
    enter_at_level = data['enter_at_level']

    if not enter_at_level:
        server_log('Node enter-at set null; getting from node: Node {0}'.format(node_index+1))
        enter_at_level = INTERFACE.nodes[node_index].enter_at_level

    current_profile = int(getOption("currentProfile"))
    profile = Profiles.query.get(current_profile)
    enter_ats = json.loads(profile.enter_ats)
    enter_ats["v"][node_index] = enter_at_level
    profile.enter_ats = json.dumps(enter_ats)
    DB.session.commit()

    INTERFACE.set_enter_at_level(node_index, enter_at_level)
    server_log('Node enter-at set: Node {0} Level {1}'.format(node_index+1, enter_at_level))

@SOCKET_IO.on('set_exit_at_level')
def on_set_exit_at_level(data):
    '''Set node exit-at level.'''
    node_index = data['node']
    exit_at_level = data['exit_at_level']

    if not exit_at_level:
        server_log('Node exit-at set null; getting from node: Node {0}'.format(node_index+1))
        exit_at_level = INTERFACE.nodes[node_index].exit_at_level

    current_profile = int(getOption("currentProfile"))
    profile = Profiles.query.get(current_profile)
    exit_ats = json.loads(profile.exit_ats)
    exit_ats["v"][node_index] = exit_at_level
    profile.exit_ats = json.dumps(exit_ats)
    DB.session.commit()

    INTERFACE.set_exit_at_level(node_index, exit_at_level)
    server_log('Node exit-at set: Node {0} Level {1}'.format(node_index+1, exit_at_level))

def hardware_set_all_enter_ats(enter_at_levels):
    '''send update to nodes'''
    for idx in range(RACE.num_nodes):
        if enter_at_levels[idx]:
            INTERFACE.set_enter_at_level(idx, enter_at_levels[idx])
        else:
            on_set_enter_at_level({
                'node': idx,
                'enter_at_level': INTERFACE.nodes[idx].enter_at_level
                })

def hardware_set_all_exit_ats(exit_at_levels):
    '''send update to nodes'''
    for idx in range(RACE.num_nodes):
        if exit_at_levels[idx]:
            INTERFACE.set_exit_at_level(idx, exit_at_levels[idx])
        else:
            on_set_exit_at_level({
                'node': idx,
                'exit_at_level': INTERFACE.nodes[idx].exit_at_level
                })


@SOCKET_IO.on('set_language')
def on_set_language(data):
    '''Set interface language.'''
    setOption('currentLanguage', data['language'])
    DB.session.commit()

@SOCKET_IO.on('cap_enter_at_btn')
def on_cap_enter_at_btn(data):
    '''Capture enter-at level.'''
    node_index = data['node_index']
    if INTERFACE.start_capture_enter_at_level(node_index):
        server_log('Starting capture of enter-at level for node {0}'.format(node_index+1))

@SOCKET_IO.on('cap_exit_at_btn')
def on_cap_exit_at_btn(data):
    '''Capture exit-at level.'''
    node_index = data['node_index']
    if INTERFACE.start_capture_exit_at_level(node_index):
        server_log('Starting capture of exit-at level for node {0}'.format(node_index+1))

@SOCKET_IO.on('add_heat')
def on_add_heat():
    '''Adds the next available heat number to the database.'''
    max_heat_id = DB.session.query(DB.func.max(Heat.heat_id)).scalar()
    for node in range(RACE.num_nodes): # Add next heat with pilots 1 thru 5
        DB.session.add(Heat(heat_id=max_heat_id+1, node_index=node, pilot_id=node+1, class_id=CLASS_ID_NONE))
    DB.session.commit()
    server_log('Heat added: Heat {0}'.format(max_heat_id+1))
    emit_heat_data() # Settings page, new pilot position in heats

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
    emit_heat_data(noself=True) # Settings page, new pilot position in heats

@SOCKET_IO.on('set_heat_note')
def on_set_heat_note(data):
    '''Sets name of heat.'''
    global EVENT_RESULTS_CACHE_VALID
    EVENT_RESULTS_CACHE_VALID = False

    heat = data['heat']
    note = data['note']
    db_update = Heat.query.filter_by(heat_id=heat, node_index=0).first()
    db_update.note = note
    DB.session.commit()
    server_log('Heat note: Heat {0}'.format(heat))
    emit_heat_data(noself=True) # Settings page, new pilot position in heats

@SOCKET_IO.on('set_heat_class')
def on_set_heat_class(data):
    '''Sets a new pilot in a heat.'''
    heat = data['heat']
    class_id = data['class']
    db_update = Heat.query.filter_by(heat_id=heat, node_index=0).first()
    db_update.class_id = class_id
    DB.session.commit()
    server_log('Heat {0} set to class {1}'.format(heat, class_id))
    emit_heat_data(noself=True) # Settings page, new pilot position in heats

@SOCKET_IO.on('add_race_class')
def on_add_race_class():
    '''Adds the next available pilot id number in the database.'''
    new_race_class = RaceClass(name='New class', format_id=0)
    DB.session.add(new_race_class)
    DB.session.flush()
    DB.session.refresh(new_race_class)
    new_race_class.name = __('Class %d') % (new_race_class.id)
    new_race_class.description = __('Class %d') % (new_race_class.id)
    DB.session.commit()
    server_log('Class added: Class {0}'.format(new_race_class))
    emit_class_data()
    emit_heat_data() # Update class selections in heat displays

@SOCKET_IO.on('set_race_class_name')
def on_set_race_class_name(data):
    '''Sets race class name.'''
    global EVENT_RESULTS_CACHE_VALID
    EVENT_RESULTS_CACHE_VALID = False

    race_class = data['class_id']
    race_class_name = data['class_name']
    db_update = RaceClass.query.get(race_class)
    db_update.name = race_class_name
    DB.session.commit()
    server_log('Class {0} name: {1}'.format(race_class, race_class_name))
    emit_class_data(noself=True)
    emit_heat_data() # Update class names in heat displays

@SOCKET_IO.on('set_race_class_format')
def on_set_race_class_format(data):
    '''Sets race class format.'''
    race_class = data['class_id']
    race_class_format = data['class_format']
    db_update = RaceClass.query.get(race_class)
    db_update.format_id = race_class_format
    DB.session.commit()
    server_log('Class {0} format: {1}'.format(race_class, race_class_format))
    emit_class_data(noself=True)
    emit_current_heat(noself=True) # in case race operator is a different client, update locked format dropdown

@SOCKET_IO.on('set_race_class_description')
def on_set_race_class_name(data):
    '''Sets race class description.'''
    race_class = data['class_id']
    race_class_description = data['class_description']
    db_update = RaceClass.query.get(race_class)
    db_update.description = race_class_description
    DB.session.commit()
    server_log('Class {0} description: {1}'.format(race_class, race_class_description))
    emit_class_data(noself=True)

@SOCKET_IO.on('add_pilot')
def on_add_pilot():
    '''Adds the next available pilot id number in the database.'''
    new_pilot = Pilot(name='New Pilot',
                           callsign='New Callsign',
                           team=DEF_TEAM_NAME,
                           phonetic = '')
    DB.session.add(new_pilot)
    DB.session.flush()
    DB.session.refresh(new_pilot)
    new_pilot.name = __('Pilot %d Name') % (new_pilot.id)
    new_pilot.callsign = __('Callsign %d') % (new_pilot.id)
    new_pilot.team = DEF_TEAM_NAME
    new_pilot.phonetic = ''
    DB.session.commit()
    server_log('Pilot added: Pilot {0}'.format(new_pilot.id))
    emit_pilot_data()

@SOCKET_IO.on('set_pilot_callsign')
def on_set_pilot_callsign(data):
    '''Gets pilot callsign to update database.'''
    global EVENT_RESULTS_CACHE_VALID
    EVENT_RESULTS_CACHE_VALID = False

    pilot_id = data['pilot_id']
    callsign = data['callsign']
    db_update = Pilot.query.get(pilot_id)
    db_update.callsign = callsign
    DB.session.commit()
    server_log('Pilot callsign set: Pilot {0} Callsign {1}'.format(pilot_id, callsign))
    emit_pilot_data(noself=True) # Settings page, new pilot callsign
    emit_heat_data() # Settings page, new pilot callsign in heats

@SOCKET_IO.on('set_pilot_team')
def on_set_pilot_team(data):
    '''Gets pilot team name to update database.'''
    pilot_id = data['pilot_id']
    team_name = data['team_name']
    db_update = Pilot.query.get(pilot_id)
    db_update.team = team_name
    DB.session.commit()
    server_log('Pilot team set: Pilot {0} Team {1}'.format(pilot_id, team_name))
    emit_pilot_data(noself=True) # Settings page, new pilot team
    #emit_heat_data() # Settings page, new pilot team in heats

@SOCKET_IO.on('set_pilot_phonetic')
def on_set_pilot_phonetic(data):
    '''Gets pilot phonetic to update database.'''
    pilot_id = data['pilot_id']
    phonetic = data['phonetic']
    db_update = Pilot.query.get(pilot_id)
    db_update.phonetic = phonetic
    DB.session.commit()
    server_log('Pilot phonetic set: Pilot {0} Phonetic {1}'.format(pilot_id, phonetic))
    emit_pilot_data(noself=True) # Settings page, new pilot phonetic
    emit_heat_data() # Settings page, new pilot phonetic in heats. Needed?

@SOCKET_IO.on('set_pilot_name')
def on_set_pilot_name(data):
    '''Gets pilot name to update database.'''
    global EVENT_RESULTS_CACHE_VALID
    EVENT_RESULTS_CACHE_VALID = False

    pilot_id = data['pilot_id']
    name = data['name']
    db_update = Pilot.query.get(pilot_id)
    db_update.name = name
    DB.session.commit()
    server_log('Pilot name set: Pilot {0} Name {1}'.format(pilot_id, name))
    emit_pilot_data(noself=True) # Settings page, new pilot name

@SOCKET_IO.on('add_profile')
def on_add_profile():
    '''Adds new profile in the database.'''
    current_profile = int(getOption("currentProfile"))
    profile = Profiles.query.get(current_profile)
    new_freqs = {}
    new_freqs["f"] = default_frequencies()

    new_profile = Profiles(name=__('New Profile'),
                           description = __('New Profile'),
                           frequencies = json.dumps(new_freqs),
                           enter_ats = profile.enter_ats,
                           exit_ats = profile.exit_ats,
                           f_ratio = 100)
    DB.session.add(new_profile)
    DB.session.flush()
    DB.session.refresh(new_profile)
    new_profile.name = __('Profile %s') % new_profile.id
    DB.session.commit()
    on_set_profile(data={ 'profile': new_profile.id })

@SOCKET_IO.on('delete_profile')
def on_delete_profile():
    '''Delete profile'''
    if (DB.session.query(Profiles).count() > 1): # keep one profile
        current_profile = int(getOption("currentProfile"))
        profile = Profiles.query.get(current_profile)
        DB.session.delete(profile)
        DB.session.commit()
        first_profile_id = Profiles.query.first().id
        setOption("currentProfile", first_profile_id)
        on_set_profile(data={ 'profile': first_profile_id })

@SOCKET_IO.on('set_profile_name')
def on_set_profile_name(data):
    ''' update profile name '''
    profile_name = data['profile_name']
    current_profile = int(getOption("currentProfile"))
    profile = Profiles.query.get(current_profile)
    profile.name = profile_name
    DB.session.commit()
    server_log('Set profile name %s' % (profile_name))
    emit_node_tuning(noself=True)

@SOCKET_IO.on('set_profile_description')
def on_set_profile_description(data):
    ''' update profile description '''
    profile_description = data['profile_description']
    current_profile = int(getOption("currentProfile"))
    profile = Profiles.query.get(current_profile)
    profile.description = profile_description
    DB.session.commit()
    server_log('Set profile description %s for profile %s' %
               (profile_name, profile.name))
    emit_node_tuning(noself=True)

@SOCKET_IO.on('set_filter_ratio')
def on_set_filter_ratio(data):
    '''Set Filter Ratio'''
    filter_ratio = data['filter_ratio']
    if filter_ratio >= 1 and filter_ratio <= 10000:
        current_profile = int(getOption("currentProfile"))
        profile = Profiles.query.get(current_profile)
        profile.f_ratio = filter_ratio
        DB.session.commit()
        server_log('Set Filter ratio to: {0}'.format(filter_ratio))
        emit_node_tuning()
        INTERFACE.set_filter_ratio_global(filter_ratio)

@SOCKET_IO.on("set_profile")
def on_set_profile(data, emit_vals=True):
    ''' set current profile '''
    profile_val = int(data['profile'])
    profile = Profiles.query.get(profile_val)
    if profile:
        setOption("currentProfile", data['profile'])
        server_log("Set Profile to '%s'" % profile_val)
        # set freqs, enter_ats, and exit_ats
        freqs_loaded = json.loads(profile.frequencies)
        freqs = freqs_loaded["f"]

        if profile.enter_ats:
            enter_ats_loaded = json.loads(profile.enter_ats)
            enter_ats = enter_ats_loaded["v"]
        else: #handle null data by copying in hardware values
            enter_at_levels = {}
            enter_at_levels["v"] = [node.enter_at_level for node in INTERFACE.nodes]
            enter_levels_serial = json.dumps(enter_at_levels)
            profile.enter_ats = enter_levels_serial
            enter_ats = enter_at_levels["v"]

        if profile.exit_ats:
            exit_ats_loaded = json.loads(profile.exit_ats)
            exit_ats = exit_ats_loaded["v"]
        else: #handle null data by copying in hardware values
            exit_at_levels = {}
            exit_at_levels["v"] = [node.exit_at_level for node in INTERFACE.nodes]
            exit_levels_serial = json.dumps(exit_at_levels)
            profile.exit_ats = exit_levels_serial
            exit_ats = exit_at_levels["v"]

        DB.session.commit()
        if emit_vals:
            emit_node_tuning()
            emit_enter_and_exit_at_levels()
            emit_frequency_data()

        hardware_set_all_frequencies(freqs)
        hardware_set_all_enter_ats(enter_ats)
        hardware_set_all_exit_ats(exit_ats)
        #set filter ratio
        INTERFACE.set_filter_ratio_global(profile.f_ratio)

    else:
        server_log('Invalid set_profile value: ' + str(profile_val))

@SOCKET_IO.on('backup_database')
def on_backup_database():
    '''Backup database.'''
    bkp_name = backup_db_file(True)  # make copy of DB file
         # read DB data and convert to Base64
    with open(bkp_name, mode='rb') as file:
        file_content = base64.encodestring(file.read())
    emit_payload = {
        'file_name': os.path.basename(bkp_name),
        'file_data' : file_content
    }
    SOCKET_IO.emit('database_bkp_done', emit_payload)

@SOCKET_IO.on('reset_database')
def on_reset_database(data):
    '''Reset database.'''
    global EVENT_RESULTS_CACHE_VALID
    EVENT_RESULTS_CACHE_VALID = False

    reset_type = data['reset_type']
    if reset_type == 'races':
        db_reset_saved_races()
        db_reset_current_laps()
    elif reset_type == 'heats':
        db_reset_heats()
        db_reset_saved_races()
        db_reset_current_laps()
    elif reset_type == 'classes':
        db_reset_heats()
        db_reset_classes()
        db_reset_saved_races()
        db_reset_current_laps()
    elif reset_type == 'pilots':
        db_reset_pilots()
        db_reset_heats()
        db_reset_saved_races()
        db_reset_current_laps()
    elif reset_type == 'all':
        db_reset_pilots()
        db_reset_heats()
        db_reset_classes()
        db_reset_saved_races()
        db_reset_current_laps()
    emit_heat_data()
    emit_pilot_data()
    emit_race_format()
    emit_class_data()
    emit_current_laps()
    emit_round_data_notify()
    emit('reset_confirm')

@SOCKET_IO.on('shutdown_pi')
def on_shutdown_pi():
    '''Shutdown the raspberry pi.'''
    emit_priority_message(__('Server has shut down.'), True)
    server_log('Shutdown pi')
    time.sleep(1);
    os.system("sudo shutdown now")

@SOCKET_IO.on("set_min_lap")
def on_set_min_lap(data):
    min_lap = data['min_lap']
    setOption("MinLapSec", data['min_lap'])
    setOption("HistoryExpireDuration", data['min_lap'])
    server_log("set min lap time to %s seconds" % min_lap)
    emit_min_lap(noself=True)
    INTERFACE.set_history_expire_global(data['min_lap'] * 1000)

@SOCKET_IO.on("set_min_lap_behavior")
def on_set_min_lap_behavior(data):
    min_lap_behavior = data['min_lap_behavior']
    setOption("MinLapBehavior", data['min_lap_behavior'])
    server_log("set min lap behavior to %s" % min_lap_behavior)
    emit_min_lap(noself=True)

@SOCKET_IO.on("set_race_format")
def on_set_race_format(data):
    ''' set current race_format '''
    if RACE.race_status == 0: # prevent format change if race running
        race_format_val = data['race_format']
        race_format = RaceFormat.query.get(race_format_val)
        DB.session.flush()
        setOption("currentFormat", race_format_val)
        DB.session.commit()
        emit_race_format()
        server_log("set race format to '%s'" % race_format_val)
    else:
        server_log("format change prevented by active race")

@SOCKET_IO.on('add_race_format')
def on_add_race_format():
    '''Adds new format in the database by duplicating an existing one.'''
    source_format_id = getOption("currentFormat")
    source_format = RaceFormat.query.get(source_format_id)
    new_format = RaceFormat(name=__('Copy of %s') % source_format.name,
                             race_mode=source_format.race_mode,
                             race_time_sec=source_format.race_time_sec ,
                             start_delay_min=source_format.start_delay_min,
                             start_delay_max=source_format.start_delay_max,
                             number_laps_win=source_format.number_laps_win,
                             win_condition=source_format.win_condition,
                             team_racing_mode=source_format.team_racing_mode)
    DB.session.add(new_format)
    DB.session.flush()
    DB.session.refresh(new_format)
    DB.session.commit()
    on_set_race_format(data={ 'race_format': new_format.id })

@SOCKET_IO.on('delete_race_format')
def on_delete_race_format():
    '''Delete profile'''
    if RACE.race_status == 0: # prevent format change if race running
        if (DB.session.query(RaceFormat).count() > 1): # keep one format
            last_raceFormat = int(getOption("currentFormat"))
            raceformat = RaceFormat.query.get(last_raceFormat)
            DB.session.delete(raceformat)
            DB.session.commit()
            first_raceFormat_id = RaceFormat.query.first().id
            setOption("currentFormat", first_raceFormat_id)
            raceformat = RaceFormat.query.get(first_raceFormat_id)
            emit_race_format()
    else:
        server_log("format change prevented by active race")


@SOCKET_IO.on('set_race_format_name')
def on_set_race_format_name(data):
    ''' update profile name '''
    format_name = data['format_name']
    race_format = RaceFormat.query.get(int(getOption('currentFormat')))
    race_format.name = format_name
    DB.session.commit()
    server_log('set format name %s' % (format_name))
    emit_race_format()
    emit_class_data()

@SOCKET_IO.on("set_race_mode")
def on_set_race_mode(data):
    race_mode = data['race_mode']
    last_raceFormat = int(getOption("currentFormat"))
    race_format = RaceFormat.query.get(last_raceFormat)
    race_format.race_mode = race_mode
    DB.session.commit()
    server_log("set race mode to %s" % race_mode)

@SOCKET_IO.on("set_fix_race_time")
def on_set_fix_race_time(data):
    race_time = data['race_time']
    last_raceFormat = int(getOption("currentFormat"))
    race_format = RaceFormat.query.get(last_raceFormat)
    race_format.race_time_sec = race_time
    DB.session.commit()
    server_log("set fixed time race to %s seconds" % race_time)

@SOCKET_IO.on("set_start_delay_min")
def on_set_start_delay_min(data):
    start_delay_min = data['start_delay_min']
    last_raceFormat = int(getOption("currentFormat"))
    race_format = RaceFormat.query.get(last_raceFormat)
    race_format.start_delay_min = start_delay_min
    DB.session.commit()
    server_log("set start delay min to %s" % start_delay_min)

@SOCKET_IO.on("set_start_delay_max")
def on_set_start_delay_max(data):
    start_delay_max = data['start_delay_max']
    last_raceFormat = int(getOption("currentFormat"))
    race_format = RaceFormat.query.get(last_raceFormat)
    race_format.start_delay_max = start_delay_max
    DB.session.commit()
    server_log("set start delay max to %s" % start_delay_max)

@SOCKET_IO.on("set_number_laps_win")
def on_set_number_laps_win(data):
    number_laps_win = data['number_laps_win']
    last_raceFormat = int(getOption("currentFormat"))
    race_format = RaceFormat.query.get(last_raceFormat)
    race_format.number_laps_win = number_laps_win
    DB.session.commit()
    server_log("set number of laps to win to %s" % number_laps_win)

@SOCKET_IO.on("set_win_condition")
def on_set_win_condition(data):
    win_condition = data['win_condition']
    last_raceFormat = int(getOption("currentFormat"))
    race_format = RaceFormat.query.get(last_raceFormat)
    race_format.win_condition = win_condition
    DB.session.commit()
    server_log("set laps wins mode to %s" % win_condition)

@SOCKET_IO.on("set_team_racing_mode")
def on_set_team_racing_mode(data):
    team_racing_mode = data['team_racing_mode']
    last_raceFormat = int(getOption("currentFormat"))
    race_format = RaceFormat.query.get(last_raceFormat)
    race_format.team_racing_mode = (True if team_racing_mode else False)
    DB.session.commit()
    server_log("set team racing mode to %s" % team_racing_mode)

# Race management socket io events

@SOCKET_IO.on('prestage_race')
def on_prestage_race(data):
    '''Common race start events (do early to prevent processing delay when start is called)'''
    initiator = data['initiator'] # client ID of session that started the race
    onoff(strip, Color(255,128,0)) #ORANGE for STAGING
    clear_laps() # Ensure laps are cleared before race start, shouldn't be needed
    RACE.race_status = 3
    emit_current_laps() # Race page, blank laps to the web client
    emit_leaderboard() # Race page, blank leaderboard to the web client
    emit_race_status() # Race page, blank laps to the web client
    INTERFACE.enable_calibration_mode() # Nodes reset triggers on next pass
    last_raceFormat = int(getOption("currentFormat"))
    race_format = RaceFormat.query.get(last_raceFormat)
    if race_format.team_racing_mode:
        check_emit_team_racing_status()  # Show initial team-racing status info
    MIN = min(race_format.start_delay_min, race_format.start_delay_max) # in case values are reversed
    MAX = max(race_format.start_delay_min, race_format.start_delay_max)
    DELAY = random.randint(MIN, MAX)

    SOCKET_IO.emit('prestage_ready', {
        'hide_stage_timer': MIN != MAX,
        'start_delay': DELAY,
        'race_mode': race_format.race_mode,
        'race_time_sec': race_format.race_time_sec,
        'initiator': initiator
    }) # Loop back to race page with chosen delay

    INTERFACE.lock_i2c()


@SOCKET_IO.on('stage_race')
def on_stage_race(data):
    '''Bounce a response back to client for determining response time'''
    INTERFACE.mark_start_time_global()
    INTERFACE.lock_i2c()
    SOCKET_IO.emit('stage_ready', data)

@SOCKET_IO.on('start_race')
def on_start_race(data):
    '''Starts the race'''
    try:
        gevent.with_timeout(10, race_start_thread, data['delay'])
    except Timeout:
        # Race failed to start
        RACE.race_status = 0
        server_log('WARNING: Race start thread timed out')
        emit_race_status()

def race_start_thread(staging_delay):
    gevent.sleep(staging_delay)
    if RACE.race_status != 1: # Only start a race if it is not already in progress
        for node in INTERFACE.nodes:
            node.under_min_lap_count = 0
        RACE.race_status = 1 # To enable registering passed laps
        RACE.timer_running = 1 # indicate race timer is running
        global RACE_START # To redefine main program variable
        RACE_START = datetime.now() # Update the race start time stamp
        global Race_laps_winner_name
        Race_laps_winner_name = None  # name of winner in first-to-X-laps race
        INTERFACE.mark_start_time_global()
        onoff(strip, Color(0,255,0)) #GREEN for GO
        emit_race_status() # Race page, to set race button states
        server_log('Race started at {0}'.format(RACE_START))


@SOCKET_IO.on('stop_race')
def on_stop_race():
    '''Stops the race and stops registering laps.'''
    RACE.race_status = 2 # To stop registering passed laps, waiting for laps to be cleared
    RACE.timer_running = 0 # indicate race timer not running
    global RACE_DURATION_MS # To redefine main program variable
    RACE_END = datetime.now() # Update the race end time stamp

    delta_time = RACE_END - RACE_START
    milli_sec = (delta_time.days * 24 * 60 * 60 + delta_time.seconds) \
        * 1000 + delta_time.microseconds / 1000.0
    RACE_DURATION_MS = milli_sec

    SOCKET_IO.emit('stop_timer') # Loop back to race page to start the timer counting up
    server_log('Race stopped at {0} ({1})'.format(RACE_END, RACE_DURATION_MS))
    emit_race_status() # Race page, to set race button states
    onoff(strip, Color(255,0,0)) #RED ON

    min_laps_list = []  # show nodes with laps under minimum (if any)
    for node in INTERFACE.nodes:
        if node.under_min_lap_count > 0:
            min_laps_list.append('Node {0} Count={1}'.format(node.index+1, node.under_min_lap_count))
    if len(min_laps_list) > 0:
        server_log('Nodes with laps under minimum:  ' + ', '.join(min_laps_list))

@SOCKET_IO.on('save_laps')
def on_save_laps():
    '''Save current laps data to the database.'''
    global EVENT_RESULTS_CACHE_VALID
    EVENT_RESULTS_CACHE_VALID = False
    heat = Heat.query.filter_by(heat_id=RACE.current_heat, node_index=0).first()
    # Get the last saved round for the current heat
    max_round = DB.session.query(DB.func.max(SavedRace.round_id)) \
            .filter_by(heat_id=RACE.current_heat).scalar()
    if max_round is None:
        max_round = 0
    # Loop through laps to copy to saved races
    current_profile = int(getOption("currentProfile"))
    profile = Profiles.query.get(current_profile)
    profile_freqs = json.loads(profile.frequencies)
    for node in range(RACE.num_nodes):
        if profile_freqs["f"][node] != FREQUENCY_ID_NONE:
            for lap in CurrentLap.query.filter_by(node_index=node).all():
                DB.session.add(SavedRace(round_id=max_round+1, heat_id=RACE.current_heat, \
                    format_id=getOption('currentFormat'), class_id=heat.class_id, \
                    node_index=node, pilot_id=lap.pilot_id, lap_id=lap.lap_id, \
                    lap_time_stamp=lap.lap_time_stamp, lap_time=lap.lap_time, \
                    lap_time_formatted=lap.lap_time_formatted))
    DB.session.commit()
    server_log('Current laps saved: Heat {0} Round {1}'.format(RACE.current_heat, max_round+1))
    on_clear_laps() # Also clear the current laps
    emit_round_data_notify() # live update rounds page

@SOCKET_IO.on('clear_laps')
def on_clear_laps():
    '''Clear the current laps due to false start or practice.'''
    clear_laps()
    emit_current_laps() # Race page, blank laps to the web client
    emit_leaderboard() # Race page, blank leaderboard to the web client
    emit_race_status() # Race page, to set race button states
    race_format = RaceFormat.query.get(int(getOption('currentFormat')))
    if race_format.team_racing_mode:
        check_emit_team_racing_status()  # Show team-racing status info
    else:
        emit_team_racing_status('')  # clear any displayed "Winner is" text

def clear_laps():
    '''Clear the current laps due to false start or practice.'''
    RACE.race_status = 0 # Laps cleared, ready to start next race
    RACE.timer_running = 0 # indicate race timer not running
    global Race_laps_winner_name
    Race_laps_winner_name = None  # clear winner in first-to-X-laps race
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
    race_format = RaceFormat.query.get(int(getOption('currentFormat')))
    if race_format.team_racing_mode:
        check_emit_team_racing_status()  # Show initial team-racing status info

@SOCKET_IO.on('recover_pass')
def on_recover_pass(data):
    node_index = data['node']
    catch_history = INTERFACE.get_catch_history(node_index)

    if data['method'] == 'max': # catch missed pass
        server_log('Recovering pass: Node {0} / Pass {1}'.format(node_index + 1, catch_history['pass_ms']))

        # get best lap possible regardless of data validity (client asked for one)
        INTERFACE.intf_simulate_lap(node_index, catch_history['pass_ms'])

        new_enterat = catch_history['rssi_max'] - int(getOption("HistoryMaxOffset"))

        if new_enterat > INTERFACE.nodes[node_index].node_nadir_rssi:
            if new_enterat < INTERFACE.nodes[node_index].node_peak_rssi:
                if new_enterat >= INTERFACE.nodes[node_index].exit_at_level + int(getOption("HistoryMinOffset")):
                    on_set_enter_at_level({
                        'node': node_index,
                        'enter_at_level': new_enterat
                    })
                else:
                    emit_priority_message(__('No tuning adjustment made on node {0}: Requested Enterat of {1} is too close or below ExitAt.').format(node_index + 1, new_enterat), False, nobroadcast=True)
                    server_log('Skipping EnterAt adjustment: RSSI of {0} too close to ExitAt {1}' \
                        .format(catch_history['rssi_max'], INTERFACE.nodes[node_index].exit_at_level))

            else:
                emit_priority_message(__('Tuning adjust failed on node {0}: Bad RSSI value ').format(node_index + 1), False, nobroadcast=True)
                server_log('Skipping EnterAt adjustment: RSSI of {0} below Node Peak {1}' \
                    .format(catch_history['rssi_max'], INTERFACE.nodes[node_index].node_peak_rssi))
        else:
            emit_priority_message(__('Tuning adjust failed on node {0}: Bad RSSI value').format(node_index + 1), False, nobroadcast=True)
            server_log('Skipping EnterAt adjustment: RSSI of {0} above Node Nadir {1}' \
                .format(catch_history['rssi_max'], INTERFACE.nodes[node_index].node_nadir_rssi))

    if data['method'] == 'min': # force end crossing
        server_log('Force end crossing: Node {0}'.format(node_index + 1))

        # end crossing now
        if INTERFACE.nodes[node_index].crossing_flag:
            INTERFACE.force_end_crossing(node_index)

            new_exitat = catch_history['rssi_min'] + int(getOption("HistoryMinOffset"))

            if new_exitat > INTERFACE.nodes[node_index].node_nadir_rssi:
                if new_exitat < INTERFACE.nodes[node_index].node_peak_rssi:
                    if new_exitat >= INTERFACE.nodes[node_index].enter_at_level:
                        if new_exitat + int(getOption("HistoryMaxOffset")) < INTERFACE.nodes[node_index].node_peak_rssi:
                            on_set_enter_at_level({
                                'node': node_index,
                                'enter_at_level': new_exitat + int(getOption("HistoryMaxOffset"))
                            })
                            emit_priority_message(__('WARNING: Force end on node {0} required increase of EnterAt. EnterAt may be improperly calibrated.').format(node_index + 1), False, nobroadcast=True)
                            server_log('Forced end required EnterAt adjustment')
                        else:
                            emit_priority_message(__('WARNING: Force end adjustment on node {0} failed: insufficient RSSI range.').format(node_index + 1), False, nobroadcast=True)
                            server_log('Skipping EnterAt adjustment: adjustment required, but would have set above NodePeak')
                    else:
                        emit_priority_message(__('Force end failed on node {0}: Bad RSSI value.').format(node_index + 1), False, nobroadcast=True)
                        server_log('Skipping ExitAt adjustment: RSSI of {0} under Node Peak {1}' \
                            .format(catch_history['rssi_min'], INTERFACE.nodes[node_index].node_peak_rssi))

                on_set_exit_at_level({
                    'node': node_index,
                    'exit_at_level': new_exitat
                })
            else:
                emit_priority_message(__('Force end failed on node {0}: Bad RSSI value').format(node_index + 1), False, nobroadcast=True)
                server_log('Skipping ExitAt adjustment: RSSI of {0} above Node Nadir {1}' \
                    .format(catch_history['rssi_min'], INTERFACE.nodes[node_index].node_nadir_rssi))
        else:
            emit_priority_message(__('Cannot force end: Node {0} is not crossing').format(node_index + 1), False, nobroadcast=True)
            server_log('Skipping ExitAt adjustment: Node {0} is not crossing'.format(node_index + 1))

    emit_enter_and_exit_at_levels()

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
    server_log('Lap deleted: Node {0} Lap {1}'.format(node_index+1, lap_id))
    emit_current_laps() # Race page, update web client
    emit_leaderboard() # Race page, update web client
    race_format = RaceFormat.query.get(int(getOption('currentFormat')))
    if race_format.team_racing_mode:
        # update team-racing status info
        if race_format.win_condition != WIN_CONDITION_MOST_LAPS:  # if not Most Laps Wins race
            if race_format.number_laps_win > 0:  # if number-laps-win race
                t_laps_dict, team_name, pilot_team_dict = get_team_laps_info(-1, race_format.number_laps_win)
                check_team_laps_win(t_laps_dict, race_format.number_laps_win, pilot_team_dict)
            else:
                t_laps_dict = get_team_laps_info()[0]
        else:  # if Most Laps Wins race enabled
            t_laps_dict, t_name, pilot_team_dict = get_team_laps_info()
            if ms_from_race_start() > race_format.race_time_sec*1000:  # if race done
                check_most_laps_win(node_index, t_laps_dict, pilot_team_dict)
        check_emit_team_racing_status(t_laps_dict)

@SOCKET_IO.on('simulate_lap')
def on_simulate_lap(data):
    '''Simulates a lap (for debug testing).'''
    node_index = data['node']
    server_log('Simulated lap: Node {0}'.format(node_index+1))
    INTERFACE.intf_simulate_lap(node_index, ms_from_race_start())

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

@SOCKET_IO.on('set_option')
def on_set_option(data):
    setOption(data['option'], data['value'])

@SOCKET_IO.on('get_race_elapsed')
def get_race_elapsed():
    # never broadcasts to all
    emit('race_elapsed', {
        'elapsed': ms_from_race_start()
    })

@SOCKET_IO.on('imdtabler_update_freqs')
def imdtabler_update_freqs(data):
    ''' Update IMDTabler page with new frequencies list '''
    emit_imdtabler_data(data['freq_list'].replace(',',' ').split())


# Socket io emit functions

def emit_priority_message(message, interrupt=False, **params):
    ''' Emits message to all clients '''
    emit_payload = {
        'message': message,
        'interrupt': interrupt
    }
    if ('nobroadcast' in params):
        emit('priority_message', emit_payload)
    else:
        SOCKET_IO.emit('priority_message', emit_payload)

def emit_race_status(**params):
    '''Emits race status.'''
    last_raceFormat = int(getOption("currentFormat"))
    race_format = RaceFormat.query.get(last_raceFormat)
    emit_payload = {
            'race_status': RACE.race_status,
            'race_mode': race_format.race_mode,
            'race_time_sec': race_format.race_time_sec,
        }
    if ('nobroadcast' in params):
        emit('race_status', emit_payload)
    else:
        SOCKET_IO.emit('race_status', emit_payload)

def emit_frequency_data(**params):
    '''Emits node data.'''
    profile_freqs = json.loads(Profiles.query.get(int(getOption("currentProfile"))).frequencies)
    emit_payload = {
            'frequency': profile_freqs["f"][:RACE.num_nodes]
        }
    if ('nobroadcast' in params):
        emit('frequency_data', emit_payload)
    else:
        SOCKET_IO.emit('frequency_data', emit_payload)
              # if IMDTabler.java available then trigger call to
              #  'emit_imdtabler_rating' via heartbeat function:
    if Use_imdtabler_jar_flag:
        heartbeat_thread_function.imdtabler_flag = True

def emit_node_data(**params):
    '''Emits node data.'''
    emit_payload = {
            'node_peak_rssi': [node.node_peak_rssi for node in INTERFACE.nodes],
            'node_nadir_rssi': [node.node_nadir_rssi for node in INTERFACE.nodes],
            'pass_peak_rssi': [node.pass_peak_rssi for node in INTERFACE.nodes],
            'pass_nadir_rssi': [node.pass_nadir_rssi for node in INTERFACE.nodes],
            'debug_pass_count': [node.debug_pass_count for node in INTERFACE.nodes]
        }
    if ('nobroadcast' in params):
        emit('node_data', emit_payload)
    else:
        SOCKET_IO.emit('node_data', emit_payload)

def emit_enter_and_exit_at_levels(**params):
    '''Emits enter-at and exit-at levels for nodes.'''
    current_profile = int(getOption("currentProfile"))
    profile = Profiles.query.get(current_profile)
    profile_enter_ats = json.loads(profile.enter_ats)
    profile_exit_ats = json.loads(profile.exit_ats)

    emit_payload = {
        'enter_at_levels': profile_enter_ats["v"][:RACE.num_nodes],
        'exit_at_levels': profile_exit_ats["v"][:RACE.num_nodes]
    }
    if ('nobroadcast' in params):
        emit('enter_and_exit_at_levels', emit_payload)
    else:
        SOCKET_IO.emit('enter_and_exit_at_levels', emit_payload)

def emit_node_tuning(**params):
    '''Emits node tuning values.'''
    current_profile = int(getOption("currentProfile"))
    tune_val = Profiles.query.get(current_profile)
    emit_payload = {
        'profile_ids': [profile.id for profile in Profiles.query.all()],
        'profile_names': [profile.name for profile in Profiles.query.all()],
        'current_profile': current_profile,
        'filter_ratio': tune_val.f_ratio,
        'profile_name': tune_val.name,
        'profile_description': tune_val.description
    }
    if ('nobroadcast' in params):
        emit('node_tuning', emit_payload)
    else:
        SOCKET_IO.emit('node_tuning', emit_payload)

def emit_language(**params):
    '''Emits race status.'''
    emit_payload = {
            'language': getOption("currentLanguage"),
            'languages': getLanguages()
        }
    if ('nobroadcast' in params):
        emit('language', emit_payload)
    else:
        SOCKET_IO.emit('language', emit_payload)

def emit_all_languages(**params):
    '''Emits full language dictionary.'''
    emit_payload = {
            'languages': getAllLanguages()
        }
    if ('nobroadcast' in params):
        emit('all_languages', emit_payload)
    else:
        SOCKET_IO.emit('all_languages', emit_payload)

def emit_min_lap(**params):
    '''Emits current minimum lap.'''
    emit_payload = {
        'min_lap': getOption('MinLapSec'),
        'min_lap_behavior': getOption("MinLapBehavior")
    }
    if ('nobroadcast' in params):
        emit('min_lap', emit_payload)
    else:
        SOCKET_IO.emit('min_lap', emit_payload)

def emit_race_format(**params):
    '''Emits race format values.'''
    current_format = int(getOption("currentFormat"))
    format_val = RaceFormat.query.get(current_format)
    has_race = SavedRace.query.filter_by(format_id=current_format).first()
    if has_race:
        locked = True
    else:
        locked = False

    emit_payload = {
        'format_ids': [raceformat.id for raceformat in RaceFormat.query.all()],
        'format_names': [raceformat.name for raceformat in RaceFormat.query.all()],
        'current_format': current_format,
        'format_name': format_val.name,
        'race_mode': format_val.race_mode,
        'race_time_sec': format_val.race_time_sec,
        'start_delay_min': format_val.start_delay_min,
        'start_delay_max': format_val.start_delay_max,
        'number_laps_win': format_val.number_laps_win,
        'win_condition': format_val.win_condition,
        'team_racing_mode': 1 if format_val.team_racing_mode else 0,
        'locked': locked
    }
    if ('nobroadcast' in params):
        emit('race_format', emit_payload)
    else:
        SOCKET_IO.emit('race_format', emit_payload)
        emit_team_racing_stat_if_enb()
        emit_leaderboard()

def emit_current_laps(**params):
    '''Emits current laps.'''
    current_laps = []
    # for node in DB.session.query(CurrentLap.node_index).distinct():
    for node in range(RACE.num_nodes):
        node_laps = []
        node_lap_raw = []
        node_lap_times = []
        for lap in CurrentLap.query.filter_by(node_index=node).all():
            node_laps.append(lap.lap_id)
            node_lap_raw.append(lap.lap_time)
            node_lap_times.append(lap.lap_time_formatted)
        current_laps.append({
            'lap_id': node_laps,
            'lap_raw': node_lap_raw,
            'lap_time': node_lap_times
        })
    current_laps = {'node_index': current_laps}
    emit_payload = current_laps
    if ('nobroadcast' in params):
        emit('current_laps', emit_payload)
    else:
        SOCKET_IO.emit('current_laps', emit_payload)

def emit_round_data_notify(**params):
    '''Let clients know round data is updated so they can request it.'''
    SOCKET_IO.emit('round_data_notify')

def emit_round_data(**params):
    '''Emits saved races to rounds page.'''
    global EVENT_RESULTS_CACHE
    global EVENT_RESULTS_CACHE_VALID

    if EVENT_RESULTS_CACHE_VALID:
        emit_payload = EVENT_RESULTS_CACHE

    else:
        heats = {}
        for heat in SavedRace.query.with_entities(SavedRace.heat_id).distinct().order_by(SavedRace.heat_id):
            heatnote = Heat.query.filter_by( heat_id=heat.heat_id ).first().note

            rounds = []
            for round in SavedRace.query.with_entities(SavedRace.round_id).distinct().filter_by(heat_id=heat.heat_id).order_by(SavedRace.round_id):
                nodes = []
                for node in range(RACE.num_nodes):
                    pilot_data = Pilot.query.filter_by( id=Heat.query.filter_by(heat_id=heat.heat_id,node_index=node).first().pilot_id ).first()
                    if pilot_data:
                        nodepilot = pilot_data.callsign
                        laps = []
                        for lap in SavedRace.query.filter_by(heat_id=heat.heat_id, round_id=round.round_id, node_index=node).all():
                            laps.append({
                                    'id': lap.lap_id,
                                    'lap_time_formatted': lap.lap_time_formatted
                                })
                        nodes.append({
                            'pilot': nodepilot,
                            'laps': laps
                        })
                rounds.append({
                    'id': round.round_id,
                    'nodes': nodes,
                    'leaderboard': calc_leaderboard(heat_id=heat.heat_id, round_id=round.round_id)
                })
            heats[heat.heat_id] = {
                'heat_id': heat.heat_id,
                'note': heatnote,
                'rounds': rounds,
                'leaderboard': calc_leaderboard(heat_id=heat.heat_id)
            }

        heats_by_class = {}
        heats_by_class[CLASS_ID_NONE] = [heat.heat_id for heat in Heat.query.filter_by(class_id=CLASS_ID_NONE,node_index=0).all()]
        for race_class in RaceClass.query.all():
            heats_by_class[race_class.id] = [heat.heat_id for heat in Heat.query.filter_by(class_id=race_class.id,node_index=0).all()]

        current_classes = {}
        for race_class in RaceClass.query.all():
            current_class = {}
            current_class['id'] = race_class.id
            current_class['name'] = race_class.name
            current_class['description'] = race_class.name
            current_class['leaderboard'] = calc_leaderboard(class_id=race_class.id)
            current_classes[race_class.id] = current_class

        emit_payload = {
            'heats': heats,
            'heats_by_class': heats_by_class,
            'classes': current_classes,
            'event_leaderboard': calc_leaderboard()
        }

        EVENT_RESULTS_CACHE = emit_payload
        EVENT_RESULTS_CACHE_VALID = True

    if ('nobroadcast' in params):
        emit('round_data', emit_payload)
    else:
        SOCKET_IO.emit('round_data', emit_payload)

def calc_leaderboard(**params):
    ''' Generates leaderboards '''
    USE_CURRENT = False
    USE_ROUND = None
    USE_HEAT = None
    USE_CLASS = None

    if ('current_race' in params):
        USE_CURRENT = True

    if ('class_id' in params):
        USE_CLASS = params['class_id']
    elif ('round_id' in params and 'heat_id' in params):
        USE_ROUND = params['round_id']
        USE_HEAT = params['heat_id']
    elif ('heat_id' in params):
        USE_ROUND = None
        USE_HEAT = params['heat_id']

    # Get meta
    if USE_CURRENT:
        current_profile = int(getOption("currentProfile"))
        profile = Profiles.query.get(current_profile)
        profile_freqs = json.loads(profile.frequencies)

        current_format = int(getOption("currentFormat"))
    else:
        if USE_CLASS:
            current_format = RaceClass.query.get(USE_CLASS).format_id

        elif USE_HEAT:
            if USE_ROUND:
                current_format = SavedRace.query.filter_by(heat_id=USE_HEAT, round_id=USE_ROUND).first().format_id
            else:
                heat_class = Heat.query.filter_by(heat_id=USE_HEAT).first().class_id
                if heat_class:
                    current_format = RaceClass.query.get(heat_class).format_id
                else:
                    current_format = None
        else:
            current_format = None

    if current_format:
        race_format = RaceFormat.query.get(current_format)
    else:
        race_format = None

    # Get the pilot ids for all relevant data
    # Add pilot callsigns
    # Add pilot team names
    # Get total laps for each pilot
    pilot_ids = []
    callsigns = []
    team_names = []
    max_laps = []

    for pilot in Pilot.query.filter(Pilot.id != PILOT_ID_NONE):
        if USE_CURRENT:
            stat_query = DB.session.query(DB.func.count(CurrentLap.lap_id)) \
                .filter(CurrentLap.pilot_id == pilot.id, \
                    CurrentLap.lap_id != 0)
            max_lap = stat_query.scalar()
            current_heat = Heat.query.filter_by(heat_id=RACE.current_heat, pilot_id=pilot.id).first()
            if current_heat and profile_freqs["f"][current_heat.node_index] != FREQUENCY_ID_NONE:
                pilot_ids.append(pilot.id)
                callsigns.append(pilot.callsign)
                team_names.append(pilot.team)
                max_laps.append(max_lap)
        else:
            if USE_CLASS:
                stat_query = DB.session.query(DB.func.count(SavedRace.lap_id)) \
                    .filter(SavedRace.pilot_id == pilot.id, \
                        SavedRace.class_id == USE_CLASS, \
                        SavedRace.lap_id != 0)
            elif USE_HEAT:
                if USE_ROUND:
                    stat_query = DB.session.query(DB.func.count(SavedRace.lap_id)) \
                        .filter(SavedRace.pilot_id == pilot.id, \
                            SavedRace.heat_id == USE_HEAT, \
                            SavedRace.round_id == USE_ROUND, \
                            SavedRace.lap_id != 0)
                else:
                    stat_query = DB.session.query(DB.func.count(SavedRace.lap_id)) \
                        .filter(SavedRace.pilot_id == pilot.id, \
                            SavedRace.heat_id == USE_HEAT, \
                            SavedRace.lap_id != 0)
            else:
                stat_query = DB.session.query(DB.func.count(SavedRace.lap_id)) \
                    .filter(SavedRace.pilot_id == pilot.id, \
                        SavedRace.lap_id != 0)

            max_lap = stat_query.scalar()
            if max_lap > 0:
                pilot_ids.append(pilot.id)
                callsigns.append(pilot.callsign)
                team_names.append(pilot.team)
                max_laps.append(max_lap)

    total_time = []
    last_lap = []
    average_lap = []
    fastest_lap = []
    consecutives = []

    for i, pilot in enumerate(pilot_ids):
        # Get the total race time for each pilot
        if max_laps[i] is 0:
            total_time.append(0) # Add zero if no laps completed
        else:
            if USE_CURRENT:
                stat_query = DB.session.query(DB.func.sum(CurrentLap.lap_time)) \
                    .filter_by(pilot_id=pilot)
            else:
                if USE_CLASS:
                    stat_query = DB.session.query(DB.func.sum(SavedRace.lap_time)) \
                        .filter_by(pilot_id=pilot, \
                        class_id=USE_CLASS)
                elif USE_HEAT:
                    if USE_ROUND:
                        stat_query = DB.session.query(DB.func.sum(SavedRace.lap_time)) \
                            .filter_by(pilot_id=pilot, \
                            round_id=USE_ROUND, \
                            heat_id=USE_HEAT)
                    else:
                        stat_query = DB.session.query(DB.func.sum(SavedRace.lap_time)) \
                            .filter_by(pilot_id=pilot, \
                            heat_id=USE_HEAT)

                else:
                    stat_query = DB.session.query(DB.func.sum(SavedRace.lap_time)) \
                        .filter_by(pilot_id=pilot)

            total_time.append(stat_query.scalar())

        # Get the last lap for each pilot (current race only)
        if max_laps[i] is 0:
            last_lap.append(None) # Add zero if no laps completed
        else:
            if USE_CURRENT:
                stat_query = CurrentLap.query \
                    .filter_by(pilot_id=pilot) \
                    .order_by(-CurrentLap.lap_id)
                last_lap.append(stat_query.first().lap_time)
            else:
                last_lap.append(None)

        # Get the average lap time for each pilot
        if max_laps[i] is 0:
            average_lap.append(0) # Add zero if no laps completed
        else:
            if USE_CURRENT:
                stat_query = DB.session.query(DB.func.avg(CurrentLap.lap_time)) \
                    .filter(CurrentLap.pilot_id == pilot, CurrentLap.lap_id != 0)
            else:
                if USE_CLASS:
                    stat_query = DB.session.query(DB.func.avg(SavedRace.lap_time)) \
                        .filter(SavedRace.pilot_id == pilot, \
                            SavedRace.lap_id != 0, \
                            SavedRace.class_id == USE_CLASS)
                elif USE_HEAT:
                    if USE_ROUND:
                        stat_query = DB.session.query(DB.func.avg(SavedRace.lap_time)) \
                            .filter(SavedRace.pilot_id == pilot, \
                                SavedRace.lap_id != 0, \
                                SavedRace.round_id == USE_ROUND, \
                                SavedRace.heat_id == USE_HEAT)
                    else:
                        stat_query = DB.session.query(DB.func.avg(SavedRace.lap_time)) \
                            .filter(SavedRace.pilot_id == pilot, \
                                SavedRace.lap_id != 0, \
                                SavedRace.heat_id == USE_HEAT)
                else:
                    stat_query = DB.session.query(DB.func.avg(SavedRace.lap_time)) \
                        .filter(SavedRace.pilot_id == pilot, SavedRace.lap_id != 0)

            avg_lap = stat_query.scalar()
            average_lap.append(avg_lap)

        # Get the fastest lap time for each pilot
        if max_laps[i] is 0:
            fastest_lap.append(0) # Add zero if no laps completed
        else:
            if USE_CURRENT:
                stat_query = DB.session.query(DB.func.min(CurrentLap.lap_time)) \
                    .filter(CurrentLap.pilot_id == pilot, CurrentLap.lap_id != 0)
            else:
                if USE_CLASS:
                    stat_query = DB.session.query(DB.func.min(SavedRace.lap_time)) \
                        .filter(SavedRace.pilot_id == pilot, SavedRace.lap_id != 0, \
                            SavedRace.class_id == USE_CLASS)
                elif USE_HEAT:
                    if USE_ROUND:
                        stat_query = DB.session.query(DB.func.min(SavedRace.lap_time)) \
                            .filter(SavedRace.pilot_id == pilot, SavedRace.lap_id != 0, \
                                SavedRace.round_id == USE_ROUND, \
                                SavedRace.heat_id == USE_HEAT)
                    else:
                        stat_query = DB.session.query(DB.func.min(SavedRace.lap_time)) \
                            .filter(SavedRace.pilot_id == pilot, SavedRace.lap_id != 0, \
                                SavedRace.heat_id == USE_HEAT)
                else:
                    stat_query = DB.session.query(DB.func.min(SavedRace.lap_time)) \
                        .filter(SavedRace.pilot_id == pilot, SavedRace.lap_id != 0)

            fast_lap = stat_query.scalar()
            fastest_lap.append(fast_lap)

        # find best consecutive 3 laps
        races = []
        if USE_CURRENT:
            single_race = DB.session.query(CurrentLap.lap_time) \
                .filter(CurrentLap.lap_id != 0, \
                CurrentLap.pilot_id == pilot).all()
        else:
            if USE_CLASS:
                races = SavedRace.query.with_entities(SavedRace.round_id, SavedRace.heat_id) \
                    .filter(SavedRace.class_id == USE_CLASS) \
                    .distinct().all()
            elif USE_HEAT:
                if USE_ROUND:
                    single_race = DB.session.query(SavedRace.lap_time) \
                        .filter(SavedRace.lap_id != 0, \
                            SavedRace.round_id == USE_ROUND, \
                            SavedRace.heat_id == USE_HEAT, \
                            SavedRace.pilot_id == pilot).all()
                else:
                    races = SavedRace.query.with_entities(SavedRace.round_id, SavedRace.heat_id) \
                        .filter(SavedRace.heat_id == USE_HEAT) \
                        .distinct().all()
            else:
                races = SavedRace.query.with_entities(SavedRace.round_id, SavedRace.heat_id).distinct().all()

        all_consecutives = []
        if races:
            for race in races:
                thisrace = DB.session.query(SavedRace.lap_time) \
                    .filter(SavedRace.round_id == race.round_id, \
                        SavedRace.heat_id == race.heat_id, \
                        SavedRace.lap_id != 0, \
                        SavedRace.pilot_id == pilot).all()

                if len(thisrace) >= 3:
                    for i in range(len(thisrace) - 2):
                        all_consecutives.append(thisrace[i].lap_time + thisrace[i+1].lap_time + thisrace[i+2].lap_time)

        else:
            if len(single_race) >= 3:
                for i in range(len(single_race) - 2):
                    all_consecutives.append(single_race[i].lap_time + single_race[i+1].lap_time + single_race[i+2].lap_time)

        # Sort consecutives
        all_consecutives = sorted(all_consecutives, key = lambda x: (x is None, x))
        # Get lowest not-none value (if any)

        if all_consecutives:
            consecutives.append(all_consecutives[0])
        else:
            consecutives.append(None)

    # Combine for sorting
    leaderboard = zip(callsigns, max_laps, total_time, average_lap, fastest_lap, team_names, consecutives)

    # Reverse sort max_laps x[1], then sort on total time x[2]
    leaderboard_by_race_time = sorted(leaderboard, key = lambda x: (-x[1], x[2]))

    leaderboard_total_data = []
    for i, row in enumerate(leaderboard_by_race_time, start=1):
        leaderboard_total_data.append({
            'position': i,
            'callsign': row[0],
            'laps': row[1],
            'behind': (leaderboard_by_race_time[0][1] - row[1]),
            'total_time': time_format(row[2]),
            'average_lap': time_format(row[3]),
            'fastest_lap': time_format(row[4]),
            'team_name': row[5],
            'consecutives': time_format(row[6]),
        })

    # Sort fastest_laps x[4]
    leaderboard_by_fastest_lap = sorted(leaderboard, key = lambda x: (x[4] if x[4] > 0 else float('inf')))

    leaderboard_fast_lap_data = []
    for i, row in enumerate(leaderboard_by_fastest_lap, start=1):
        leaderboard_fast_lap_data.append({
            'position': i,
            'callsign': row[0],
            'total_time': time_format(row[2]),
            'average_lap': time_format(row[3]),
            'fastest_lap': time_format(row[4]),
            'team_name': row[5],
            'consecutives': time_format(row[6]),
        })

    # Sort consecutives x[6]
    leaderboard_by_consecutives = sorted(leaderboard, key = lambda x: (x[6] if x[6] > 0 else float('inf')))

    leaderboard_consecutives_data = []
    for i, row in enumerate(leaderboard_by_consecutives, start=1):
        leaderboard_consecutives_data.append({
            'position': i,
            'callsign': row[0],
            'total_time': time_format(row[2]),
            'average_lap': time_format(row[3]),
            'fastest_lap': time_format(row[4]),
            'team_name': row[5],
            'consecutives': time_format(row[6]),
        })

    leaderboard_output = {
        'by_race_time': leaderboard_total_data,
        'by_fastest_lap': leaderboard_fast_lap_data,
        'by_consecutives': leaderboard_consecutives_data
    }

    if race_format:
        leaderboard_output['meta'] = {
            'win_condition': race_format.win_condition,
            'team_racing_mode': race_format.team_racing_mode,
        }
    else:
        leaderboard_output['meta'] = {
            'win_condition': WIN_CONDITION_NONE,
            'team_racing_mode': False
        }

    return leaderboard_output

def emit_leaderboard(**params):
    '''Emits leaderboard.'''
    emit_payload = calc_leaderboard(current_race=True)

    if ('nobroadcast' in params):
        emit('leaderboard', emit_payload)
    else:
        SOCKET_IO.emit('leaderboard', emit_payload)

def emit_heat_data(**params):
    '''Emits heat data.'''
    current_heats = {}
    for heat in Heat.query.with_entities(Heat.heat_id).distinct():
        heatdata = Heat.query.filter_by(heat_id=heat.heat_id, node_index=0).first()
        pilots = []
        for node in range(RACE.num_nodes):
            pilot_id = Heat.query.filter_by(heat_id=heat.heat_id, node_index=node).first().pilot_id
            pilots.append(pilot_id)
        heat_id = heatdata.heat_id
        note = heatdata.note
        race_class = heatdata.class_id
        has_race = SavedRace.query.filter_by(heat_id=heat.heat_id).first()
        if has_race:
            locked = True
        else:
            locked = False

        current_heats[heat_id] = {'pilots': pilots,
                              'note': note,
                              'heat_id': heat_id,
                              'class_id': race_class,
                              'locked': locked}

    current_classes = []
    for race_class in RaceClass.query.all():
        current_class = {}
        current_class['id'] = race_class.id
        current_class['name'] = race_class.name
        current_class['description'] = race_class.description
        current_classes.append(current_class)

    emit_payload = {
        'heats': current_heats,
        'pilot_data': {
            'pilot_id': [pilot.id for pilot in Pilot.query.all()],
            'callsign': [pilot.callsign for pilot in Pilot.query.all()],
            'name': [pilot.name for pilot in Pilot.query.all()]
        },
        'classes': current_classes,
    }
    if ('nobroadcast' in params):
        emit('heat_data', emit_payload)
    elif ('noself' in params):
        emit('heat_data', emit_payload, broadcast=True, include_self=False)
    else:
        SOCKET_IO.emit('heat_data', emit_payload)

def emit_class_data(**params):
    '''Emits class data.'''
    current_classes = []
    for race_class in RaceClass.query.all():
        current_class = {}
        current_class['id'] = race_class.id
        current_class['name'] = race_class.name
        current_class['description'] = race_class.description
        current_class['format'] = race_class.format_id

        has_race = SavedRace.query.filter_by(class_id=race_class.id).first()
        if has_race:
            current_class['locked'] = True
        else:
            current_class['locked'] = False

        current_classes.append(current_class)

    formats = []
    for race_format in RaceFormat.query.all():
        raceformat = {}
        raceformat['id'] = race_format.id
        raceformat['name'] = race_format.name
        formats.append(raceformat)

    emit_payload = {
        'classes': current_classes,
        'formats': formats
    }
    if ('nobroadcast' in params):
        emit('class_data', emit_payload)
    elif ('noself' in params):
        emit('class_data', emit_payload, broadcast=True, include_self=False)
    else:
        SOCKET_IO.emit('class_data', emit_payload)

def emit_pilot_data(**params):
    '''Emits pilot data.'''
    team_options_list = []  # create team-options string for each pilot, with current team selected
    for pilot in Pilot.query.all():
        opts_str = ''
        for name in TEAM_NAMES_LIST:
            opts_str += '<option value="' + name + '"'
            if name == pilot.team:
                opts_str += ' selected'
            opts_str += '>' + name + '</option>'
        team_options_list.append(opts_str)

    emit_payload = {
        'pilot_id': [pilot.id for pilot in Pilot.query.all()],
        'callsign': [pilot.callsign for pilot in Pilot.query.all()],
        'team': [pilot.team for pilot in Pilot.query.all()],
        'phonetic': [pilot.phonetic for pilot in Pilot.query.all()],
        'name': [pilot.name for pilot in Pilot.query.all()],
        'team_options': team_options_list
    }
    if ('nobroadcast' in params):
        emit('pilot_data', emit_payload)
    elif ('noself' in params):
        emit('pilot_data', emit_payload, broadcast=True, include_self=False)
    else:
        SOCKET_IO.emit('pilot_data', emit_payload)

    emit_heat_data()

def emit_current_heat(**params):
    '''Emits the current heat.'''
    callsigns = []
                             # dict for current heat with key=node_index, value=pilot_id
    node_pilot_dict = dict(Heat.query.with_entities(Heat.node_index, Heat.pilot_id). \
                      filter(Heat.heat_id==RACE.current_heat, Heat.pilot_id!=PILOT_ID_NONE).all())
    for node_index in range(RACE.num_nodes):
        pilot_id = node_pilot_dict.get(node_index)
        if pilot_id:
            pilot = Pilot.query.get(pilot_id)
            if pilot:
                callsigns.append(pilot.callsign)
            else:
                callsigns.append(None)
        else:
            callsigns.append(None)

    heat_data = Heat.query.filter_by(heat_id=RACE.current_heat, node_index=0).first()

    heat_note = heat_data.note

    heat_format = None
    if heat_data.class_id != CLASS_ID_NONE:
        heat_format = RaceClass.query.get(heat_data.class_id).format_id

    emit_payload = {
        'current_heat': RACE.current_heat,
        'callsign': callsigns,
        'heat_note': heat_note,
        'heat_format': heat_format
    }
    if ('nobroadcast' in params):
        emit('current_heat', emit_payload)
    else:
        SOCKET_IO.emit('current_heat', emit_payload)

def get_team_laps_info(cur_pilot_id=-1, num_laps_win=0):
    '''Calculates and returns team-racing info.'''
              # create dictionary with key=pilot_id, value=team_name
    pilot_team_dict = {}
    profile_freqs = json.loads(Profiles.query.get(int(getOption("currentProfile"))).frequencies)
                             # dict for current heat with key=node_index, value=pilot_id
    node_pilot_dict = dict(Heat.query.with_entities(Heat.node_index, Heat.pilot_id). \
                      filter(Heat.heat_id==RACE.current_heat, Heat.pilot_id!=PILOT_ID_NONE).all())
    for node in INTERFACE.nodes:
        if profile_freqs["f"][node.index] != FREQUENCY_ID_NONE:
            pilot_id = node_pilot_dict.get(node.index)
            if pilot_id:
                pilot_team_dict[pilot_id] = Pilot.query.filter_by(id=pilot_id).first().team
    #server_log('DEBUG get_team_laps_info pilot_team_dict: {0}'.format(pilot_team_dict))

    t_laps_dict = {}  # create dictionary (key=team_name, value=[lapCount,timestamp]) with initial zero laps
    for team_name in pilot_team_dict.values():
        if len(team_name) > 0 and team_name not in t_laps_dict:
            t_laps_dict[team_name] = [0, 0]

              # iterate through list of laps, sorted by lap timestamp
    for item in sorted(CurrentLap.query.with_entities(CurrentLap.lap_time_stamp, CurrentLap.lap_id, \
                                                      CurrentLap.pilot_id).all()):
        if item[1] > 0:  # current lap is > 0
            team_name = pilot_team_dict[item[2]]
            if team_name in t_laps_dict:
                t_laps_dict[team_name][0] += 1       # increment lap count for team
                if num_laps_win == 0 or t_laps_dict[team_name][0] <= num_laps_win:
                    t_laps_dict[team_name][1] = item[0]  # update lap_time_stamp (if not past winning lap)
                #server_log('DEBUG get_team_laps_info team[{0}]={1} item: {2}'.format(team_name, t_laps_dict[team_name], item))
    #server_log('DEBUG get_team_laps_info t_laps_dict: {0}'.format(t_laps_dict))

    if cur_pilot_id >= 0:  # determine name for 'cur_pilot_id' if given
        cur_team_name = pilot_team_dict[cur_pilot_id]
    else:
        cur_team_name = None

    return t_laps_dict, cur_team_name, pilot_team_dict

def check_emit_team_racing_status(t_laps_dict=None, **params):
    '''Checks and emits team-racing status info.'''
              # if not passed in then determine number of laps for each team
    if t_laps_dict is None:
        t_laps_dict = get_team_laps_info()[0]
    disp_str = ''
    for t_name in sorted(t_laps_dict.keys()):
        disp_str += ' <span class="team-laps">Team ' + t_name + ' Lap: ' + str(t_laps_dict[t_name][0]) + '</span>'
    if Race_laps_winner_name is not None:
        if Race_laps_winner_name is not RACE_STATUS_TIED_STR and \
                Race_laps_winner_name is not RACE_STATUS_CROSSING:
            disp_str += '<span class="team-winner">Winner is Team ' + Race_laps_winner_name + '</span>'
        else:
            disp_str += '<span class="team-winner">' + Race_laps_winner_name + '</span>'
    #server_log('Team racing status: ' + disp_str)
    emit_team_racing_status(disp_str)

def emit_team_racing_stat_if_enb(**params):
    '''Emits team-racing status info if team racing is enabled.'''
    race_format = RaceFormat.query.get(int(getOption('currentFormat')))
    if race_format.team_racing_mode:
        check_emit_team_racing_status(**params)
    else:
        emit_team_racing_status('')

def emit_team_racing_status(disp_str, **params):
    '''Emits given team-racing status info.'''
    emit_payload = {'team_laps_str': disp_str}
    if ('nobroadcast' in params):
        emit('team_racing_status', emit_payload)
    else:
        SOCKET_IO.emit('team_racing_status', emit_payload)

def check_pilot_laps_win(pass_node_index, num_laps_win):
    '''Checks if a pilot has completed enough laps to win.'''
    win_pilot_id = -1
    win_lap_tstamp = 0
    profile_freqs = json.loads(Profiles.query.get(int(getOption("currentProfile"))).frequencies)
                             # dict for current heat with key=node_index, value=pilot_id
    node_pilot_dict = dict(Heat.query.with_entities(Heat.node_index, Heat.pilot_id). \
                      filter(Heat.heat_id==RACE.current_heat, Heat.pilot_id!=PILOT_ID_NONE).all())
    for node in INTERFACE.nodes:
        if profile_freqs["f"][node.index] != FREQUENCY_ID_NONE:
            pilot_id = node_pilot_dict.get(node.index)
            if pilot_id:
                lap_id = DB.session.query(DB.func.max(CurrentLap.lap_id)) \
                        .filter_by(node_index=node.index).scalar()
                if lap_id is None:
                    lap_id = 0
                            # if (other) pilot crossing for possible winning lap then wait
                            #  in case lap time turns out to be earliest:
                if node.crossing_flag and node.index != pass_node_index and lap_id == num_laps_win - 1:
                    server_log('check_pilot_laps_win waiting for crossing, Node {0}'.format(node.index+1))
                    return -1
                if lap_id >= num_laps_win:
                    lap_data = CurrentLap.query.filter_by(node_index=node.index, lap_id=num_laps_win).first()
                    #server_log('DEBUG check_pilot_laps_win Node {0} pilot_id={1} tstamp={2}'.format(node.index+1, pilot_id, lap_data.lap_time_stamp))
                             # save pilot_id for earliest lap time:
                    if win_pilot_id < 0 or lap_data.lap_time_stamp < win_lap_tstamp:
                        win_pilot_id = pilot_id
                        win_lap_tstamp = lap_data.lap_time_stamp
    #server_log('DEBUG check_pilot_laps_win returned win_pilot_id={0}'.format(win_pilot_id))
    return win_pilot_id

def check_team_laps_win(t_laps_dict, num_laps_win, pilot_team_dict, pass_node_index=-1):
    '''Checks if a team has completed enough laps to win.'''
    global Race_laps_winner_name
         # make sure there's not a pilot in the process of crossing for a winning lap
    if Race_laps_winner_name is None and pilot_team_dict:
        profile_freqs = None
                                  # dict for current heat with key=node_index, value=pilot_id
        node_pilot_dict = dict(Heat.query.with_entities(Heat.node_index, Heat.pilot_id). \
                          filter(Heat.heat_id==RACE.current_heat, Heat.pilot_id!=PILOT_ID_NONE).all())
        for node in INTERFACE.nodes:  # check if (other) pilot node is crossing gate
            if node.crossing_flag and node.index != pass_node_index:
                if not profile_freqs:
                    profile_freqs = json.loads(Profiles.query.get( \
                                               int(getOption("currentProfile"))).frequencies)
                if profile_freqs["f"][node.index] != FREQUENCY_ID_NONE:  # node is enabled
                    pilot_id = node_pilot_dict.get(node.index)
                    if pilot_id:  # node has pilot assigned to it
                        team_name = pilot_team_dict[pilot_id]
                        if team_name:
                            ent = t_laps_dict[team_name]  # entry for team [lapCount,timestamp]
                                        # if pilot crossing for possible winning lap then wait
                                        #  in case lap time turns out to be earliest:
                            if ent and ent[0] == num_laps_win - 1:
                                server_log('check_team_laps_win waiting for crossing, Node {0}'.format(node.index+1))
                                return
    win_name = None
    win_tstamp = -1
         # for each team, check if team has enough laps to win (and, if more
         #  than one has enough laps, pick team with earliest timestamp)
    for team_name in t_laps_dict.keys():
        ent = t_laps_dict[team_name]  # entry for team [lapCount,timestamp]
        if ent[0] >= num_laps_win and (win_tstamp < 0 or ent[1] < win_tstamp):
            win_name = team_name
            win_tstamp = ent[1]
    #server_log('DEBUG check_team_laps_win win_name={0} tstamp={1}'.format(win_name,win_tstamp))
    Race_laps_winner_name = win_name

def check_most_laps_win(pass_node_index=-1, t_laps_dict=None, pilot_team_dict=None):
    '''Checks if pilot or team has most laps for a win.'''
    # pass_node_index: -1 if called from 'race_time_finished()'; node.index if called from 'pass_record_callback()'
    global Race_laps_winner_name

    race_format = RaceFormat.query.get(int(getOption('currentFormat')))
    if race_format.team_racing_mode: # team racing mode enabled

             # if not passed in then determine number of laps for each team
        if t_laps_dict is None:
            t_laps_dict, t_name, pilot_team_dict = get_team_laps_info()

        max_lap_count = -1
        win_name = None
        win_tstamp = -1
        tied_flag = False
        num_max_lap = 0
             # find team with most laps
        for team_name in t_laps_dict.keys():
            ent = t_laps_dict[team_name]  # entry for team [lapCount,timestamp]
            if ent[0] >= max_lap_count:
                if ent[0] > max_lap_count:  # if team has highest lap count found so far
                    max_lap_count = ent[0]
                    win_name = team_name
                    win_tstamp = ent[1]
                    tied_flag = False
                    num_max_lap = 1
                else:  # if team is tied for highest lap count found so far
                             # if called from 'pass_record_callback()' and not waiting for crossing
                    if pass_node_index >= 0 and Race_laps_winner_name is not RACE_STATUS_CROSSING:
                        num_max_lap += 1  # count number of teams at max lap
                        if ent[1] < win_tstamp:  # this team has earlier lap time
                            win_name = team_name
                            win_tstamp = ent[1]
                    else:  # called from 'race_time_finished()' or was waiting for crossing
                        tied_flag = True
        #server_log('DEBUG check_most_laps_win tied={0} win_name={1} tstamp={2}'.format(tied_flag,win_name,win_tstamp))

        if tied_flag or max_lap_count <= 0:
            Race_laps_winner_name = RACE_STATUS_TIED_STR  # indicate status tied
            check_emit_team_racing_status(t_laps_dict)
            emit_phonetic_text('Race tied', 'race_winner')
            return  # wait for next 'pass_record_callback()' event

        if win_name:  # if a team looks like the winner

                 # make sure there's not a pilot in the process of crossing for a winning lap
            if (Race_laps_winner_name is None or Race_laps_winner_name is RACE_STATUS_TIED_STR or \
                                Race_laps_winner_name is RACE_STATUS_CROSSING) and pilot_team_dict:
                profile_freqs = None
                node_pilot_dict = None  # dict for current heat with key=node_index, value=pilot_id
                for node in INTERFACE.nodes:  # check if (other) pilot node is crossing gate
                    if node.index != pass_node_index:  # if node is for other pilot
                        if node.crossing_flag:
                            if not profile_freqs:
                                profile_freqs = json.loads(Profiles.query.get( \
                                                int(getOption("currentProfile"))).frequencies)
                            if profile_freqs["f"][node.index] != FREQUENCY_ID_NONE:  # node is enabled
                                if not node_pilot_dict:
                                    node_pilot_dict = dict(Heat.query.with_entities(Heat.node_index, Heat.pilot_id). \
                                              filter(Heat.heat_id==RACE.current_heat, Heat.pilot_id!=PILOT_ID_NONE).all())
                                pilot_id = node_pilot_dict.get(node.index)
                                if pilot_id:  # node has pilot assigned to it
                                    team_name = pilot_team_dict[pilot_id]
                                    if team_name:
                                        ent = t_laps_dict[team_name]  # entry for team [lapCount,timestamp]
                                                    # if pilot crossing for possible winning lap then wait
                                                    #  in case lap time turns out to be earliest:
                                        if ent and ent[0] == max_lap_count - 1:
                                                          # if called from 'race_time_finished()' then allow
                                                          #  race tied when gate crossing completes
                                            if pass_node_index < 0:
                                                Race_laps_winner_name = RACE_STATUS_CROSSING
                                            else:  # if called from 'pass_record_callback()' then no more ties
                                                Race_laps_winner_name = RACE_STATUS_TIED_STR
                                            server_log('check_most_laps_win waiting for crossing, Node {0}'.\
                                                                                  format(node.index+1))
                                            return

                   # if race currently tied and more than one team at max lap
                   #  then don't stop the tied race in progress
            if (Race_laps_winner_name is not RACE_STATUS_TIED_STR) or num_max_lap <= 1:
                Race_laps_winner_name = win_name  # indicate a team has won
                check_emit_team_racing_status(t_laps_dict)
                emit_phonetic_text('Race done, winner is team ' + Race_laps_winner_name, 'race_winner')

        else:    # if no team looks like the winner
            Race_laps_winner_name = RACE_STATUS_TIED_STR  # indicate status tied

    else:  # not team racing mode

        pilots_list = []  # (lap_id, lap_time_stamp, pilot_id, node)
        max_lap_id = 0
        num_max_lap = 0
        profile_freqs = json.loads(Profiles.query.get(int(getOption("currentProfile"))).frequencies)
                                  # dict for current heat with key=node_index, value=pilot_id
        node_pilot_dict = dict(Heat.query.with_entities(Heat.node_index, Heat.pilot_id). \
                          filter(Heat.heat_id==RACE.current_heat, Heat.pilot_id!=PILOT_ID_NONE).all())
        for node in INTERFACE.nodes:  # load per-pilot data into 'pilots_list'
            if profile_freqs["f"][node.index] != FREQUENCY_ID_NONE:
                pilot_id = node_pilot_dict.get(node.index)
                if pilot_id:
                    lap_id = DB.session.query(DB.func.max(CurrentLap.lap_id)) \
                            .filter_by(node_index=node.index).scalar()
                    if lap_id > 0:
                        lap_data = CurrentLap.query.filter_by(node_index=node.index, lap_id=lap_id).first()
                        if lap_data:
                            pilots_list.append((lap_id, lap_data.lap_time_stamp, pilot_id, node))
                            if lap_id > max_lap_id:
                                max_lap_id = lap_id
                                num_max_lap = 1
                            elif lap_id == max_lap_id:
                                num_max_lap += 1  # count number of nodes at max lap
        #server_log('DEBUG check_most_laps_win pass_node_index={0} max_lap={1}'.format(pass_node_index, max_lap_id))

        if max_lap_id <= 0:  # if no laps then bail out
            Race_laps_winner_name = RACE_STATUS_TIED_STR  # indicate status tied
            if pass_node_index < 0:  # if called from 'race_time_finished()'
                emit_team_racing_status(Race_laps_winner_name)
                emit_phonetic_text('Race tied', 'race_winner')
            return

        # if any (other) pilot is in the process of crossing the gate and within one lap of
        #  winning then bail out (and wait for next 'pass_record_callback()' event)
        pass_node_lap_id = -1
        for item in pilots_list:
            if item[3].index != pass_node_index:  # if node is for other pilot
                if item[3].crossing_flag and item[0] >= max_lap_id - 1:
                           # if called from 'race_time_finished()' then allow race tied after crossing
                    if pass_node_index < 0:
                        Race_laps_winner_name = RACE_STATUS_CROSSING
                    else:  # if called from 'pass_record_callback()' then no more ties
                        Race_laps_winner_name = RACE_STATUS_TIED_STR
                    server_log('check_most_laps_win waiting for crossing, Node {0}'.format(item[3].index+1))
                    return
            else:
                pass_node_lap_id = item[0]  # save 'lap_id' for node/pilot that caused current lap pass

        # if race currently tied and called from 'pass_record_callback()'
        #  and current-pass pilot is not only one at max lap
        #  then clear 'pass_node_index' so pass will not stop a tied race in progress
        if Race_laps_winner_name is RACE_STATUS_TIED_STR and pass_node_index >= 0 and \
                (pass_node_lap_id < max_lap_id or (pass_node_lap_id == max_lap_id and num_max_lap > 1)):
            pass_node_index = -1

        # check for pilots with max laps; if more than one then select one with
        #  earliest lap time (if called from 'pass_record_callback()' fn) or
        #  indicate status tied (if called from 'race_time_finished()' fn)
        win_pilot_id = -1
        win_lap_tstamp = 0
        for item in pilots_list:
            if item[0] == max_lap_id:
                if win_pilot_id < 0:  # this is first one so far at max_lap
                    win_pilot_id = item[2]
                    win_lap_tstamp = item[1]
                else:  # other pilots found at max_lap
                             # if called from 'pass_record_callback()' and not waiting for crossing
                    if pass_node_index >= 0 and Race_laps_winner_name is not RACE_STATUS_CROSSING:
                        if item[1] < win_lap_tstamp:  # this pilot has earlier lap time
                            win_pilot_id = item[2]
                            win_lap_tstamp = item[1]
                    else:  # called from 'race_time_finished()' or was waiting for crossing
                        if Race_laps_winner_name is not RACE_STATUS_TIED_STR:
                            Race_laps_winner_name = RACE_STATUS_TIED_STR  # indicate status tied
                            emit_team_racing_status(Race_laps_winner_name)
                            emit_phonetic_text('Race tied', 'race_winner')
                        return  # wait for next 'pass_record_callback()' event
        #server_log('DEBUG check_most_laps_win win_pilot_id={0}'.format(win_pilot_id))

        if win_pilot_id >= 0:
            win_callsign = Pilot.query.filter_by(id=win_pilot_id).first().callsign
            Race_laps_winner_name = win_callsign  # indicate a pilot has won
            emit_team_racing_status('Winner is ' + Race_laps_winner_name)
            win_phon_name = Pilot.query.filter_by(id=win_pilot_id).first().phonetic
            if len(win_phon_name) <= 0:  # if no phonetic then use callsign
                win_phon_name = win_callsign
            emit_phonetic_text('Race done, winner is ' + win_phon_name, 'race_winner')
        else:
            Race_laps_winner_name = RACE_STATUS_TIED_STR  # indicate status tied

def emit_phonetic_data(pilot_id, lap_id, lap_time, team_name, team_laps, **params):
    '''Emits phonetic data.'''
    raw_time = lap_time
    phonetic_time = phonetictime_format(lap_time)
    phonetic_name = Pilot.query.get(pilot_id).phonetic
    callsign = Pilot.query.get(pilot_id).callsign
    pilot_id = Pilot.query.get(pilot_id).id
    emit_payload = {
        'pilot': phonetic_name,
        'callsign': callsign,
        'pilot_id': pilot_id,
        'lap': lap_id,
        'raw_time': raw_time,
        'phonetic': phonetic_time,
        'team_name' : team_name,
        'team_laps' : team_laps
    }
    if ('nobroadcast' in params):
        emit('phonetic_data', emit_payload)
    else:
        SOCKET_IO.emit('phonetic_data', emit_payload)

def emit_first_pass_registered(node_idx, **params):
    '''Emits when first pass (lap 0) is registered during a race'''
    emit_payload = {
        'node_index': node_idx,
    }
    if ('nobroadcast' in params):
        emit('first_pass_registered', emit_payload)
    else:
        SOCKET_IO.emit('first_pass_registered', emit_payload)

def emit_phonetic_text(text_str, domain=False, **params):
    '''Emits given phonetic text.'''
    emit_payload = {
        'text': text_str,
        'domain': domain
    }
    if ('nobroadcast' in params):
        emit('phonetic_text', emit_payload)
    else:
        SOCKET_IO.emit('phonetic_text', emit_payload)

def emit_enter_at_level(node, **params):
    '''Emits enter-at level for given node.'''
    emit_payload = {
        'node_index': node.index,
        'level': node.enter_at_level
    }
    if ('nobroadcast' in params):
        emit('node_enter_at_level', emit_payload)
    else:
        SOCKET_IO.emit('node_enter_at_level', emit_payload)

def emit_exit_at_level(node, **params):
    '''Emits exit-at level for given node.'''
    emit_payload = {
        'node_index': node.index,
        'level': node.exit_at_level
    }
    if ('nobroadcast' in params):
        emit('node_exit_at_level', emit_payload)
    else:
        SOCKET_IO.emit('node_exit_at_level', emit_payload)

def emit_node_crossing_change(node, **params):
    '''Emits crossing-flag change for given node.'''
    emit_payload = {
        'node_index': node.index,
        'crossing_flag': node.crossing_flag
    }
    if ('nobroadcast' in params):
        emit('node_crossing_change', emit_payload)
    else:
        SOCKET_IO.emit('node_crossing_change', emit_payload)

def emit_imdtabler_page(**params):
    '''Emits IMDTabler page, using current profile frequencies.'''
    if Use_imdtabler_jar_flag:
        try:                          # get IMDTabler version string
            imdtabler_ver = subprocess.check_output( \
                                ['java', '-jar', IMDTABLER_JAR_NAME, '-v']).rstrip()
            profile_freqs = json.loads(Profiles.query.get(int(getOption("currentProfile"))).frequencies)
            fi_list = list(OrderedDict.fromkeys(profile_freqs['f']))  # remove duplicates
            fs_list = []
            for val in fi_list:  # convert list of integers to list of strings
                if val > 0:      # drop any zero entries
                    fs_list.append(str(val))
            emit_imdtabler_data(fs_list, imdtabler_ver)
        except Exception as ex:
            server_log('emit_imdtabler_page exception:  ' + str(ex))

def emit_imdtabler_data(fs_list, imdtabler_ver=None, **params):
    '''Emits IMDTabler data for given frequencies.'''
    try:
        imdtabler_data = None
        if len(fs_list) > 2:  # if 3+ then invoke jar; get response
            imdtabler_data = subprocess.check_output( \
                        ['java', '-jar', IMDTABLER_JAR_NAME, '-t'] + fs_list)
    except Exception as ex:
        imdtabler_data = None
        server_log('emit_imdtabler_data exception:  ' + str(ex))
    emit_payload = {
        'freq_list': ' '.join(fs_list),
        'table_data': imdtabler_data,
        'version_str': imdtabler_ver
    }
    if ('nobroadcast' in params):
        emit('imdtabler_data', emit_payload)
    else:
        SOCKET_IO.emit('imdtabler_data', emit_payload)

def emit_imdtabler_rating():
    '''Emits IMDTabler rating for current profile frequencies.'''
    try:
        profile_freqs = json.loads(Profiles.query.get(int(getOption("currentProfile"))).frequencies)
        imd_val = None
        fi_list = list(OrderedDict.fromkeys(profile_freqs['f']))  # remove duplicates
        fs_list = []
        for val in fi_list:  # convert list of integers to list of strings
            if val > 0:      # drop any zero entries
                fs_list.append(str(val))
        if len(fs_list) > 2:
            imd_val = subprocess.check_output(  # invoke jar; get response
                        ['java', '-jar', IMDTABLER_JAR_NAME, '-r'] + fs_list).rstrip()
    except Exception as ex:
        imd_val = None
        server_log('emit_imdtabler_rating exception:  ' + str(ex))
    emit_payload = {
            'imd_rating': imd_val
        }
    SOCKET_IO.emit('imdtabler_rating', emit_payload)


#
# Program Functions
#

def heartbeat_thread_function():
    '''Emits current rssi data.'''
    while True:
        SOCKET_IO.emit('heartbeat', INTERFACE.get_heartbeat_json())
        heartbeat_thread_function.iter_tracker += 1

        # check if race timer is finished
        if RACE.timer_running:
            check_race_time_expired()

        # update displayed IMD rating after freqs changed:
        if heartbeat_thread_function.imdtabler_flag and \
                (heartbeat_thread_function.iter_tracker % 5) == 0:
            heartbeat_thread_function.imdtabler_flag = False
            emit_imdtabler_rating()
        # emit rest of node data, but less often:
        if heartbeat_thread_function.iter_tracker >= 20:
            heartbeat_thread_function.iter_tracker = 0
            emit_node_data()
        gevent.sleep(0.100)

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
    if millis is None:
        return None

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
        return '{0:01d} {1:02d}.{2:01d}'.format(minutes, seconds, tenths)
    else:
        return '{0:01d}.{1:01d}'.format(seconds, tenths)

def check_race_time_expired():
    last_raceFormat = int(getOption("currentFormat"))
    race_format = RaceFormat.query.get(last_raceFormat)
    if race_format and race_format.race_mode == 0: # count down
        if datetime.now() >= RACE_START + timedelta(0, race_format.race_time_sec):
            RACE.timer_running = 0 # indicate race timer no longer running
            if race_format.win_condition == WIN_CONDITION_MOST_LAPS:  # Most Laps Wins Enabled
                check_most_laps_win()  # check if pilot or team has most laps for win

def pass_record_callback(node, ms_since_lap):
    '''Handles pass records from the nodes.'''
    #if node.lap_ms_since_start >= 0:
    #    server_log('Raw pass record: Node: {0}, Lap TimeMS: {1}'.format(node.index+1, node.lap_ms_since_start))
    #else:
    #    server_log('Raw pass record: Node: {0}, MS Since Lap: {1}'.format(node.index+1, ms_since_lap))
    node.debug_pass_count += 1
    emit_node_data() # For updated triggers and peaks

    global Race_laps_winner_name
    profile_freqs = json.loads(Profiles.query.get(int(getOption("currentProfile"))).frequencies)
    if profile_freqs["f"][node.index] != FREQUENCY_ID_NONE:
        # always count laps if race is running, otherwise test if lap should have counted before race end (RACE_DURATION_MS is invalid while race is in progress)
        if RACE.race_status is 1 \
            or (node.lap_ms_since_start >=0 and \
                node.lap_ms_since_start < RACE_DURATION_MS):

            # Get the current pilot id on the node
            pilot_id = Heat.query.filter_by( \
                heat_id=RACE.current_heat, node_index=node.index).first().pilot_id

            if pilot_id != PILOT_ID_NONE:

                if node.lap_ms_since_start >= 0:
                    lap_time_stamp = node.lap_ms_since_start
                else:  # use milliseconds since start of race if old-firmware node
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

                race_format = RaceFormat.query.get(int(getOption('currentFormat')))
                min_lap = int(getOption("MinLapSec"))
                min_lap_behavior = int(getOption("MinLapBehavior"))

                lap_ok_flag = True
                if lap_id != 0:  # if initial lap then always accept and don't check lap time; else:
                    if lap_time < (min_lap * 1000):  # if lap time less than minimum
                        node.under_min_lap_count += 1
                        server_log('Pass record under lap minimum ({3}): Node={0}, Lap={1}, LapTime={2}, Count={4}' \
                                   .format(node.index+1, lap_id, time_format(lap_time), min_lap, node.under_min_lap_count))
                        if min_lap_behavior != 0:  # if behavior is 'Discard New Short Laps'
                            lap_ok_flag = False

                if lap_ok_flag:
                    # Add the new lap to the database
                    DB.session.add(CurrentLap(node_index=node.index, pilot_id=pilot_id, lap_id=lap_id, \
                        lap_time_stamp=lap_time_stamp, lap_time=lap_time, \
                        lap_time_formatted=time_format(lap_time)))
                    DB.session.commit()

                    #server_log('Pass record: Node: {0}, Lap: {1}, Lap time: {2}' \
                    #    .format(node.index+1, lap_id, time_format(lap_time)))
                    emit_current_laps() # update all laps on the race page
                    emit_leaderboard() # update leaderboard

                    if race_format.team_racing_mode: # team racing mode enabled

                        # if win condition is first-to-x-laps and x is valid
                        #  then check if a team has enough laps to win
                        if race_format.win_condition == WIN_CONDITION_FIRST_TO_LAP_X and race_format.number_laps_win > 0:
                            t_laps_dict, team_name, pilot_team_dict = \
                                get_team_laps_info(pilot_id, race_format.number_laps_win)
                            team_laps = t_laps_dict[team_name][0]
                            check_team_laps_win(t_laps_dict, race_format.number_laps_win, pilot_team_dict, node.index)
                        else:
                            t_laps_dict, team_name, pilot_team_dict = get_team_laps_info(pilot_id)
                            team_laps = t_laps_dict[team_name][0]
                        check_emit_team_racing_status(t_laps_dict)

                        if lap_id > 0:   # send phonetic data to be spoken
                            emit_phonetic_data(pilot_id, lap_id, lap_time, team_name, team_laps)

                            # if Most Laps Wins race is tied then check for winner
                            if race_format.win_condition == WIN_CONDITION_MOST_LAPS:
                                if Race_laps_winner_name is RACE_STATUS_TIED_STR or \
                                            Race_laps_winner_name is RACE_STATUS_CROSSING:
                                    check_most_laps_win(node.index, t_laps_dict, pilot_team_dict)

                            # if a team has won the race and this is the winning lap
                            elif Race_laps_winner_name is not None and \
                                        team_name == Race_laps_winner_name and \
                                        team_laps >= race_format.number_laps_win:
                                emit_phonetic_text('Winner is team ' + Race_laps_winner_name, 'race_winner')
                        elif lap_id == 0:
                            emit_first_pass_registered(node.index) # play first-pass sound

                    else:  # not team racing mode
                        if lap_id > 0:
                                            # send phonetic data to be spoken
                            if race_format.win_condition != WIN_CONDITION_FIRST_TO_LAP_X or race_format.number_laps_win <= 0:
                                emit_phonetic_data(pilot_id, lap_id, lap_time, None, None)

                                                 # if Most Laps Wins race is tied then check for winner
                                if race_format.win_condition == WIN_CONDITION_MOST_LAPS:
                                    if Race_laps_winner_name is RACE_STATUS_TIED_STR or \
                                                Race_laps_winner_name is RACE_STATUS_CROSSING:
                                        check_most_laps_win(node.index)

                            else:           # need to check if any pilot has enough laps to win
                                if race_format.win_condition == WIN_CONDITION_FIRST_TO_LAP_X:
                                    win_pilot_id = check_pilot_laps_win(node.index, race_format.number_laps_win)
                                    if win_pilot_id >= 0:  # a pilot has won the race
                                        win_callsign = Pilot.query.get(win_pilot_id).callsign
                                        emit_team_racing_status('Winner is ' + win_callsign)
                                        emit_phonetic_data(pilot_id, lap_id, lap_time, None, None)

                                        if Race_laps_winner_name is None:
                                                # a pilot has won the race and has not yet been announced
                                            win_phon_name = Pilot.query.get(win_pilot_id).phonetic
                                            if len(win_phon_name) <= 0:  # if no phonetic then use callsign
                                                win_phon_name = win_callsign
                                            Race_laps_winner_name = win_callsign  # call out winner (once)
                                            emit_phonetic_text('Winner is ' + win_phon_name, 'race_winner')

                                    else:  # no pilot has won the race; send phonetic data to be spoken
                                        emit_phonetic_data(pilot_id, lap_id, lap_time, None, None)
                                else:  # other win conditions
                                        emit_phonetic_data(pilot_id, lap_id, lap_time, None, None)
                        elif lap_id == 0:
                            emit_first_pass_registered(node.index) # play first-pass sound

                    if node.index==0:
                        onoff(strip, Color(0,0,255))  #BLUE
                    elif node.index==1:
                        onoff(strip, Color(255,50,0)) #ORANGE
                    elif node.index==2:
                        onoff(strip, Color(255,0,60)) #PINK
                    elif node.index==3:
                        onoff(strip, Color(150,0,255)) #PURPLE
                    elif node.index==4:
                        onoff(strip, Color(250,210,0)) #YELLOW
                    elif node.index==5:
                        onoff(strip, Color(0,255,255)) #CYAN
                    elif node.index==6:
                        onoff(strip, Color(0,255,0)) #GREEN
                    elif node.index==7:
                        onoff(strip, Color(255,0,0)) #RED
            else:
                server_log('Pass record dismissed: Node: {0}, Pilot not defined' \
                    .format(node.index+1))
    else:
        server_log('Pass record dismissed: Node: {0}, Frequency not defined' \
            .format(node.index+1))

def new_enter_or_exit_at_callback(node, is_enter_at_flag):
    if is_enter_at_flag:
        server_log('Finished capture of enter-at level for node {0}, level={1}, count={2}'.format(node.index+1, node.enter_at_level, node.cap_enter_at_count))
        emit_enter_at_level(node)
    else:
        server_log('Finished capture of exit-at level for node {0}, level={1}, count={2}'.format(node.index+1, node.exit_at_level, node.cap_exit_at_count))
        emit_exit_at_level(node)

def node_crossing_callback(node):
    emit_node_crossing_change(node)

# set callback functions invoked by interface module
INTERFACE.pass_record_callback = pass_record_callback
INTERFACE.new_enter_or_exit_at_callback = new_enter_or_exit_at_callback
INTERFACE.node_crossing_callback = node_crossing_callback

def server_log(message):
    '''Messages emitted from the server script.'''
    print message
    SOCKET_IO.emit('hardware_log', message)

def hardware_log_callback(message):
    '''Message emitted from the interface class.'''
    print message
    SOCKET_IO.emit('hardware_log', message)

INTERFACE.hardware_log_callback = hardware_log_callback

def default_frequencies():
    '''Set node frequencies, R1367 for 4, IMD6C+ for 5+.'''
    if RACE.num_nodes < 5:
        freqs = [5658, 5732, 5843, 5880, FREQUENCY_ID_NONE, FREQUENCY_ID_NONE, FREQUENCY_ID_NONE, FREQUENCY_ID_NONE]
    else:
        freqs = [5658, 5695, 5760, 5800, 5880, 5917, FREQUENCY_ID_NONE, FREQUENCY_ID_NONE]
    return freqs

def assign_frequencies():
    '''Assign frequencies to nodes'''
    current_profile = int(getOption("currentProfile"))
    profile = Profiles.query.get(current_profile)
    freqs = json.loads(profile.frequencies)

    for idx in range(RACE.num_nodes):
        INTERFACE.set_frequency(idx, freqs["f"][idx])
        server_log('Frequency set: Node {0} Frequency {1}'.format(idx+1, freqs["f"][idx]))
    DB.session.commit()

def db_init():
    '''Initialize database.'''
    DB.create_all() # Creates tables from database classes/models
    db_reset_pilots()
    db_reset_heats()
    db_reset_current_laps()
    db_reset_saved_races()
    db_reset_profile()
    db_reset_race_formats()
    db_reset_options_defaults()
    assign_frequencies()
    server_log('Database initialized')

def db_reset():
    '''Resets database.'''
    db_reset_pilots()
    db_reset_heats()
    db_reset_current_laps()
    db_reset_saved_races()
    db_reset_profile()
    db_reset_race_formats()
    assign_frequencies()
    server_log('Database reset')

def db_reset_pilots():
    '''Resets database pilots to default.'''
    DB.session.query(Pilot).delete()
    for node in range(RACE.num_nodes):
        DB.session.add(Pilot(callsign='Callsign {0}'.format(node+1), \
            name='Pilot {0} Name'.format(node+1), team=DEF_TEAM_NAME, phonetic=''))
    DB.session.commit()
    server_log('Database pilots reset')

def db_reset_heats():
    '''Resets database heats to default.'''
    DB.session.query(Heat).delete()
    for node in range(RACE.num_nodes):
        if node == 0:
            DB.session.add(Heat(heat_id=1, node_index=node, class_id=CLASS_ID_NONE, note='', pilot_id=node+1))
        else:
            DB.session.add(Heat(heat_id=1, node_index=node, class_id=CLASS_ID_NONE, pilot_id=node+1))
    DB.session.commit()
    server_log('Database heats reset')

def db_reset_classes():
    '''Resets database race classes to default.'''
    DB.session.query(RaceClass).delete()
    DB.session.commit()
    server_log('Database race classes reset')

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

    new_freqs = {}
    new_freqs["f"] = default_frequencies()

    template = {}
    template["v"] = [None, None, None, None, None, None, None, None]

    DB.session.add(Profiles(name=__("Outdoor"),
                             description = __("Medium filtering"),
                             frequencies = json.dumps(new_freqs),
                             enter_ats = json.dumps(template),
                             exit_ats = json.dumps(template),
                             f_ratio=100))
    DB.session.add(Profiles(name=__("Indoor"),
                             description = __("Strong filtering"),
                             frequencies = json.dumps(new_freqs),
                             enter_ats = json.dumps(template),
                             exit_ats = json.dumps(template),
                             f_ratio=10))
    DB.session.commit()
    setOption("currentProfile", 1)
    server_log("Database set default profiles")

def db_reset_race_formats():
    DB.session.query(RaceFormat).delete()
    DB.session.add(RaceFormat(name=__("MultiGP Standard"),
                             race_mode=0,
                             race_time_sec=120,
                             start_delay_min=2,
                             start_delay_max=5,
                             number_laps_win=0,
                             win_condition=WIN_CONDITION_MOST_LAPS,
                             team_racing_mode=False))
    DB.session.add(RaceFormat(name=__("Whoop Sprint"),
                             race_mode=0,
                             race_time_sec=90,
                             start_delay_min=2,
                             start_delay_max=5,
                             number_laps_win=0,
                             win_condition=WIN_CONDITION_MOST_LAPS,
                             team_racing_mode=False))
    DB.session.add(RaceFormat(name=__("Limited Class"),
                             race_mode=0,
                             race_time_sec=210,
                             start_delay_min=2,
                             start_delay_max=5,
                             number_laps_win=0,
                             win_condition=WIN_CONDITION_MOST_LAPS,
                             team_racing_mode=False))
    DB.session.add(RaceFormat(name=__("First to 3 Laps"),
                             race_mode=1,
                             race_time_sec=0,
                             start_delay_min=2,
                             start_delay_max=5,
                             number_laps_win=3,
                             win_condition=WIN_CONDITION_FIRST_TO_LAP_X,
                             team_racing_mode=False))
    DB.session.add(RaceFormat(name=__("Open Practice"),
                             race_mode=1,
                             race_time_sec=0,
                             start_delay_min=3,
                             start_delay_max=3,
                             number_laps_win=0,
                             win_condition=WIN_CONDITION_NONE,
                             team_racing_mode=False))
    DB.session.add(RaceFormat(name=__("Team / Most Laps Wins"),
                             race_mode=0,
                             race_time_sec=120,
                             start_delay_min=2,
                             start_delay_max=5,
                             number_laps_win=0,
                             win_condition=WIN_CONDITION_MOST_LAPS,
                             team_racing_mode=True))
    DB.session.add(RaceFormat(name=__("Team / First to 7 Laps"),
                             race_mode=0,
                             race_time_sec=120,
                             start_delay_min=2,
                             start_delay_max=5,
                             number_laps_win=7,
                             win_condition=WIN_CONDITION_FIRST_TO_LAP_X,
                             team_racing_mode=True))
    DB.session.commit()
    setOption("currentFormat", 1)
    server_log("Database reset race formats")

def db_reset_options_defaults():
    DB.session.query(GlobalSettings).delete()
    setOption("server_api", SERVER_API)
    setOption("timerName", __("RotorHazard"))
    setOption("timerLogo", "")

    setOption("hue_0", "212")
    setOption("sat_0", "55")
    setOption("lum_0_low", "29.2")
    setOption("lum_0_high", "46.7")
    setOption("contrast_0_low", "#ffffff")
    setOption("contrast_0_high", "#ffffff")

    setOption("hue_1", "25")
    setOption("sat_1", "85.3")
    setOption("lum_1_low", "37.6")
    setOption("lum_1_high", "54.5")
    setOption("contrast_1_low", "#ffffff")
    setOption("contrast_1_high", "#000000")

    setOption("currentLanguage", "")
    setOption("currentProfile", "1")
    setOption("currentFormat", "1")
    setOption("MinLapSec", "10")
    setOption("MinLapBehavior", "0")

    setOption("HistoryExpireDuration", "10000")
    setOption("HistoryMaxOffset", "10")
    setOption("HistoryMinOffset", "10")

    setOption("eventName", __("FPV Race"))
    setOption("eventDescription", "")

    server_log("Reset global settings")

def backup_db_file(copy_flag):
    DB.session.close()
    try:     # generate timestamp from last-modified time of database file
        time_str = datetime.fromtimestamp(os.stat(DB_FILE_NAME).st_mtime).strftime('%Y%m%d_%H%M%S')
    except:  # if error then use 'now' timestamp
        time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    try:
        (dbname, dbext) = os.path.splitext(DB_FILE_NAME)
        bkp_name = DB_BKP_DIR_NAME + '/' + dbname + '_' + time_str + dbext
        if copy_flag:
            if not os.path.exists(DB_BKP_DIR_NAME):
                os.makedirs(DB_BKP_DIR_NAME)
            shutil.copy2(DB_FILE_NAME, bkp_name);
            server_log('Copied database file to:  ' + bkp_name)
        else:
            os.renames(DB_FILE_NAME, bkp_name);
            server_log('Moved old database file to:  ' + bkp_name)
    except Exception as ex:
        server_log('Error backing up database file:  ' + str(ex))
    return bkp_name

def query_table_data(class_type, filter_crit=None, filter_value=0):
    try:
        if filter_crit is None:
            return class_type.query.all()
        return class_type.query.filter(filter_crit==filter_value).all()
    except Exception:
        server_log('Unable to read "{0}" table from previous database'.format(class_type.__name__))

def restore_table(class_type, table_query_data, match_name='name'):
    if table_query_data:
        try:
            for row_data in table_query_data:
                if (class_type is not Pilot) or getattr(row_data, 'callsign', '') != '-' or \
                                              getattr(row_data, 'name', '') != '-None-':
                    db_update = class_type.query.filter(getattr(class_type,match_name)==getattr(row_data,match_name)).first()
                    if db_update is None:
                        new_data = class_type()
                        for col in class_type.__table__.columns.keys():
                            if col != 'id':
                                setattr(new_data, col, getattr(row_data, col))
                        #server_log('DEBUG row_data add:  ' + str(getattr(new_data, match_name)))
                        DB.session.add(new_data)
                    else:
                        #server_log('DEBUG row_data update:  ' + str(getattr(row_data, match_name)))
                        for col in class_type.__table__.columns.keys():
                            if col != 'id':
                                setattr(db_update, col, getattr(row_data, col))
                    DB.session.flush()
            server_log('Database table "{0}" restored'.format(class_type.__name__))
        except Exception as ex:
            server_log('Error restoring "{0}" table from previous database:  {1}'.format(class_type.__name__, ex))

def recover_database():
    try:
        server_log('Recovering data from previous database')
        pilot_query_data = query_table_data(Pilot)
        raceFormat_query_data = query_table_data(RaceFormat)
        profiles_query_data = query_table_data(Profiles)
        raceClass_query_data = query_table_data(RaceClass)
        heat_query_data = query_table_data(Heat, Heat.heat_id, 1)

        carryoverOpts = [
            "timerName",
            "timerLogo",
            "hue_0",
            "sat_0",
            "lum_0_low",
            "lum_0_high",
            "contrast_0_low",
            "contrast_0_high",
            "hue_1",
            "sat_1",
            "lum_1_low",
            "lum_1_high",
            "contrast_1_low",
            "contrast_1_high",
            "currentLanguage",
            "currentProfile",
            "currentFormat",
            "MinLapSec",
        ]
        carryOver = {}
        for opt in carryoverOpts:
            val = getOption(opt, None)
            if val is not None:
                carryOver[opt] = val

    except Exception as ex:
        server_log('Error reading data from previous database:  ' + str(ex))

    backup_db_file(False)  # rename and move DB file
    db_init()
    try:
        if pilot_query_data:
            DB.session.query(Pilot).delete()
            restore_table(Pilot, pilot_query_data, 'callsign')
        restore_table(RaceFormat, raceFormat_query_data)
        restore_table(Profiles, profiles_query_data)
        restore_table(RaceClass, raceClass_query_data)
        if heat_query_data and len(heat_query_data) == RACE.num_nodes:
            DB.session.query(Heat).delete()
            restore_table(Heat, heat_query_data, 'node_index')

        for opt in carryOver:
            setOption(opt, carryOver[opt])
        server_log('UI Options restored')

    except Exception as ex:
        server_log('Error while writing data from previous database:  ' + str(ex))

    DB.session.commit()

def expand_heats():
    for heat_ids in Heat.query.with_entities(Heat.heat_id).distinct():
        for node in range(RACE.num_nodes):
            heat_row = Heat.query.filter_by(heat_id=heat_ids.heat_id, node_index=node)
            if not heat_row.count():
                DB.session.add(Heat(heat_id=heat_ids.heat_id, node_index=node, pilot_id=PILOT_ID_NONE, class_id=CLASS_ID_NONE))

    DB.session.commit()

#
# Program Initialize
#

# Save number of nodes found
RACE.num_nodes = len(INTERFACE.nodes)
print 'Number of nodes found: {0}'.format(RACE.num_nodes)

# Delay to get I2C addresses through interface class initialization
gevent.sleep(0.500)

# if no DB file then create it now (before "__()" fn used in 'buildServerInfo()')
db_inited_flag = False
if not os.path.exists(DB_FILE_NAME):
    server_log('No database.db file found; creating initial database')
    db_init()
    db_inited_flag = True

# collect server info for About panel
serverInfo = buildServerInfo()
server_log('Release: {0} / Server API: {1} / Latest Node API: {2}'.format(RELEASE_VERSION, SERVER_API, NODE_API_BEST))
if serverInfo['node_api_match'] is False:
    server_log('** WARNING: Node API mismatch **')
if serverInfo['node_api_lowest'] < NODE_API_BEST:
    server_log('** NOTICE: Node firmware update available **')

if not db_inited_flag:
    if int(getOption('server_api')) < SERVER_API:
        server_log('Old server API version; resetting database')
        recover_database()
    elif not Heat.query.count():
        server_log('Heats are empty; resetting database')
        recover_database()
    elif not Profiles.query.count():
        server_log('Profiles are empty; resetting database')
        recover_database()
    elif not RaceFormat.query.count():
        server_log('Formats are empty; resetting database')
        recover_database()

# Expand heats (if number of nodes increases)
expand_heats()

# Import IMDTabler
if os.path.exists(IMDTABLER_JAR_NAME):  # if 'IMDTabler.jar' is available
    try:
        java_ver = subprocess.check_output(['java', '-version'], stderr=subprocess.STDOUT)
        server_log('Found installed:  ' + java_ver.split('\n')[0])
    except:
        java_ver = None
        server_log('Unable to find java; for IMDTabler functionality try:')
        server_log('sudo apt-get install oracle-java8-jdk')
    if java_ver:
        try:
            imdtabler_ver = subprocess.check_output( \
                        ['java', '-jar', IMDTABLER_JAR_NAME, '-v'], \
                        stderr=subprocess.STDOUT).rstrip()
            Use_imdtabler_jar_flag = True  # indicate IMDTabler.jar available
            server_log('Found installed:  ' + imdtabler_ver)
        except Exception as ex:
            server_log('Error checking IMDTabler:  ' + str(ex))
else:
    server_log('IMDTabler lib not found at: ' + IMDTABLER_JAR_NAME)


# Clear any current laps from the database on each program start
# DB session commit needed to prevent 'application context' errors
db_reset_current_laps()

# Send initial profile values to nodes
current_profile = int(getOption("currentProfile"))
on_set_profile({'profile': current_profile}, False)
INTERFACE.set_history_expire_global(int(getOption("HistoryExpireDuration")))

# Set current heat on startup
if Heat.query.first():
    RACE.current_heat = Heat.query.first().heat_id

# Start HTTP server
if __name__ == '__main__':
    port_val = Config['GENERAL']['HTTP_PORT']
    print "Running http server at port " + str(port_val)
    try:
        SOCKET_IO.run(APP, host='0.0.0.0', port=port_val, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        print "Server terminated by keyboard interrupt"
    except Exception as ex:
        print "Server exception:  " + str(ex)
