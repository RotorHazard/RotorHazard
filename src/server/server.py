'''RotorHazard server script'''
from __builtin__ import True
RELEASE_VERSION = "2.1.0 (dev 1)" # Public release version code
SERVER_API = 24 # Server API version
NODE_API_SUPPORTED = 18 # Minimum supported node version
NODE_API_BEST = 19 # Most recent node API
JSON_API = 2 # JSON API version

import os
import sys
import shutil
import base64
import subprocess
import importlib
import bisect
import socketio
from monotonic import monotonic
from datetime import datetime
from functools import wraps
from collections import OrderedDict

from flask import Flask, render_template, request, Response, session
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy

import gevent
import gevent.monkey
gevent.monkey.patch_all()

import random
import json

# LED imports
import time
import signal

sys.path.append('../interface')
sys.path.append('/home/pi/RotorHazard/src/interface')  # Needed to run on startup

from RHRace import get_race_state

APP = Flask(__name__, static_url_path='/static')
APP.config['SECRET_KEY'] = 'secret!'

HEARTBEAT_THREAD = None

PILOT_ID_NONE = 0  # indicator value for no pilot configured
HEAT_ID_NONE = 0  # indicator value for practice heat
CLASS_ID_NONE = 0  # indicator value for unclassified heat
FREQUENCY_ID_NONE = 0  # indicator value for node disabled

EVENT_RESULTS_CACHE = {} # Cache of results page leaderboards
EVENT_RESULTS_CACHE_VALID = False # Whether cache is valid (False = regenerate cache)

LAST_RACE_CACHE = {} # Cache of current race after clearing
LAST_RACE_LAPS_CACHE = {} # Cache of current race after clearing
LAST_RACE_CACHE_VALID = False # Whether cache is valid (False = regenerate cache)

DB_FILE_NAME = 'database.db'
DB_BKP_DIR_NAME = 'db_bkp'
CONFIG_FILE_NAME = 'config.json'
LANGUAGE_FILE_NAME = 'language.json'
IMDTABLER_JAR_NAME = 'static/IMDTabler.jar'

TEAM_NAMES_LIST = [str(unichr(i)) for i in range(65, 91)]  # list of 'A' to 'Z' strings
DEF_TEAM_NAME = 'A'  # default team

BASEDIR = os.getcwd()
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
Config['LED']['LED_INVERT']     = False   # True to invert the signal (when using NPN transistor level shift)
Config['LED']['LED_CHANNEL']    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
Config['LED']['LED_STRIP']      = 'GRB'   # Strip type and colour ordering

# other default configurations
Config['GENERAL']['HTTP_PORT'] = 5000
Config['GENERAL']['ADMIN_USERNAME'] = 'admin'
Config['GENERAL']['ADMIN_PASSWORD'] = 'rotorhazard'
Config['GENERAL']['SLAVES'] = []
Config['GENERAL']['SLAVE_TIMEOUT'] = 300 # seconds
Config['GENERAL']['DEBUG'] = False
Config['GENERAL']['CORS_ALLOWED_HOSTS'] = '*'

Config['GENERAL']['NODE_DRIFT_CALC_TIME'] = 10

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

# start SocketIO service
SOCKET_IO = SocketIO(APP, async_mode='gevent', cors_allowed_origins=Config['GENERAL']['CORS_ALLOWED_HOSTS'])

try:
    interfaceModule = importlib.import_module('RHInterface')
except ImportError:
    interfaceModule = importlib.import_module('MockInterface')
INTERFACE = interfaceModule.get_hardware_interface()
RACE = get_race_state() # For storing race management variables

def diff_milliseconds(t2, t1):
    dt = t2 - t1
    ms = round((dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0)
    return ms

EPOCH_START = datetime(1970, 1, 1)
PROGRAM_START_TIMESTAMP = diff_milliseconds(datetime.now(), EPOCH_START)
print 'Program started at {0:13f}'.format(PROGRAM_START_TIMESTAMP)
PROGRAM_START = monotonic()
PROGRAM_START_MILLIS_OFFSET = 1000.0*PROGRAM_START - PROGRAM_START_TIMESTAMP

def monotonic_to_milliseconds(secs):
    return 1000.0*secs - PROGRAM_START_MILLIS_OFFSET

RACE_START = monotonic() # Updated on race start commands
RACE_START_TOKEN = False # Check start thread matches correct stage sequence
RACE_DURATION_MS = 0 # Calculated when race is stopped
RACE_END = 0 # Updated when race is stopped

RACE_SCHEDULED = False # Whether to start a race when time
RACE_SCHEDULED_TIME = 0 # Start race when time reaches this value

RACE_STATUS_READY = 0
RACE_STATUS_STAGING = 3
RACE_STATUS_RACING = 1
RACE_STATUS_DONE = 2

Race_laps_winner_name = None  # set to name of winner in first-to-X-laps race
RACE_STATUS_TIED_STR = 'Race is tied; continuing'  # shown when Most Laps Wins race tied
RACE_STATUS_CROSSING = 'Waiting for cross'  # indicator for Most Laps Wins race

Use_imdtabler_jar_flag = False  # set True if IMDTabler.jar is available

Pixel = None

#
# Slaves
#

class Slave:

    TIMER_MODE = 'timer'
    MIRROR_MODE = 'mirror'

    def __init__(self, id, info):
        self.id = id
        self.info = info
        addr = info['address']
        if not '://' in addr:
            addr = 'http://'+addr
        self.address = addr
        self.lastContact = -1
        self.sio = socketio.Client()
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('pass_record', self.on_pass_record)

    def reconnect(self):
        if self.lastContact == -1:
            startConnectTime = monotonic()
            print "Slave {0}: connecting to {1}...".format(self.id+1, self.address)
            while monotonic() < startConnectTime + self.info['timeout']:
                try:
                    self.sio.connect(self.address)
                    print "Slave {0}: connected to {1}".format(self.id+1, self.address)
                    return True
                except socketio.exceptions.ConnectionError:
                    gevent.sleep(0.1)
            print "Slave {0}: connection to {1} failed!".format(self.id+1, self.address)
            return False

    def emit(self, event, data = None):
        if self.reconnect():
            self.sio.emit(event, data)
            self.lastContact = monotonic()

    def on_connect(self):
        self.lastContact = monotonic()

    def on_disconnect(self):
        self.lastContact = -1

    def on_pass_record(self, data):
        self.lastContact = monotonic()
        node_index = data['node']
        pilot_id = Heat.query.filter_by( \
            heat_id=RACE.current_heat, node_index=node_index).one_or_none().pilot_id

        if pilot_id != PILOT_ID_NONE:

            split_ts = data['timestamp'] + (PROGRAM_START_MILLIS_OFFSET - 1000.0*RACE_START)
            last_lap_id = DB.session.query(DB.func.max(CurrentLap.lap_id)).filter_by(node_index=node_index).scalar()
            if last_lap_id is None: # first lap
                current_lap_id = 0
                last_lap_ts = 0
            else:
                current_lap_id = last_lap_id + 1
                last_lap_ts = CurrentLap.query.filter_by(node_index=node_index, lap_id=last_lap_id).one().lap_time_stamp

            split_id = self.id
            last_split_id = DB.session.query(DB.func.max(LapSplit.split_id)).filter_by(node_index=node_index, lap_id=current_lap_id).scalar()
            if last_split_id is None: # first split for this lap
                if split_id > 0:
                    server_log('Ignoring missing splits before {0} for node {1}'.format(split_id+1, node_index+1))
                last_split_ts = last_lap_ts
            else:
                if split_id > last_split_id:
                    if split_id > last_split_id + 1:
                        server_log('Ignoring missing splits between {0} and {1} for node {2}'.format(last_split_id+1, split_id+1, node_index+1))
                    last_split_ts = LapSplit.query.filter_by(node_index=node_index, lap_id=current_lap_id, split_id=last_split_id).one().split_time_stamp
                else:
                    server_log('Ignoring out-of-order split {0} for node {1}'.format(split_id+1, node_index+1))
                    last_split_ts = None

            if last_split_ts is not None:
                split_time = split_ts - last_split_ts
                split_speed = float(self.info['distance'])*1000.0/float(split_time) if 'distance' in self.info else None
                server_log('Split pass record: Node: {0}, Lap: {1}, Split time: {2}, Split speed: {3}' \
                    .format(node_index+1, current_lap_id+1, time_format(split_time), \
                    ('{0:.2f}'.format(split_speed) if split_speed <> None else 'None')))

                DB.session.add(LapSplit(node_index=node_index, pilot_id=pilot_id, lap_id=current_lap_id, split_id=split_id, \
                    split_time_stamp=split_ts, split_time=split_time, split_time_formatted=time_format(split_time), \
                    split_speed=split_speed))
                DB.session.commit()
                emit_current_laps() # update all laps on the race page
        else:
            server_log('Split pass record dismissed: Node: {0}, Frequency not defined' \
                .format(node_index+1))

class Cluster:
    def __init__(self):
        self.slaves = []

    def addSlave(self, slave):
        slave.emit('join_cluster')
        self.slaves.append(slave)

    def emit(self, event, data = None):
        for slave in self.slaves:
            gevent.spawn(slave.emit, event, data)

    def emitToMirrors(self, event, data = None):
        for slave in self.slaves:
            if slave.info['mode'] == Slave.MIRROR_MODE:
                gevent.spawn(slave.emit, event, data)

    def emitStatus(self):
        now = monotonic()
        SOCKET_IO.emit('cluster_status', {'slaves': [ \
            {'address': slave.address, \
            'last_contact': int(now-slave.lastContact) if slave.lastContact >= 0 else 'connection lost' \
            }] for slave in self.slaves})

CLUSTER = Cluster()
hasMirrors = False
for index, slave_info in enumerate(Config['GENERAL']['SLAVES']):
    if isinstance(slave_info, basestring):
        slave_info = {'address': slave_info, 'mode': Slave.TIMER_MODE}
    if 'timeout' not in slave_info:
        slave_info['timeout'] = Config['GENERAL']['SLAVE_TIMEOUT']
    isMirror = (slave_info['mode'] == Slave.MIRROR_MODE)
    if isMirror:
        hasMirrors = True
    elif hasMirrors:
        print '** Mirror slaves must be last - ignoring remaining slave config **'
        break
    slave = Slave(index, slave_info)
    CLUSTER.addSlave(slave)

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

    # Server API
    serverInfo['json_api'] = JSON_API

    # Node API levels
    node_api_level = False
    serverInfo['node_api_match'] = True

    serverInfo['node_api_lowest'] = None
    serverInfo['node_api_levels'] = [None]

    if len(INTERFACE.nodes):
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
            for idx, level in enumerate(serverInfo['node_api_levels']):
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
# Database Models
#

class Pilot(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    callsign = DB.Column(DB.String(80), nullable=False)
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
    source = DB.Column(DB.Integer, nullable=False)

    def __repr__(self):
        return '<CurrentLap %r>' % self.pilot_id

class LapSplit(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    node_index = DB.Column(DB.Integer, nullable=False)
    pilot_id = DB.Column(DB.Integer, nullable=False)
    lap_id = DB.Column(DB.Integer, nullable=False)
    split_id = DB.Column(DB.Integer, nullable=False)
    split_time_stamp = DB.Column(DB.Integer, nullable=False)
    split_time = DB.Column(DB.Integer, nullable=False)
    split_time_formatted = DB.Column(DB.Integer, nullable=False)
    split_speed = DB.Column(DB.Float, nullable=True)

    def __repr__(self):
        return '<LapSplit %r>' % self.pilot_id

class SavedRaceMeta(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    round_id = DB.Column(DB.Integer, nullable=False)
    heat_id = DB.Column(DB.Integer, nullable=False)
    class_id = DB.Column(DB.Integer, nullable=False)
    format_id = DB.Column(DB.Integer, nullable=False)
    start_time = DB.Column(DB.Integer, nullable=False) # internal monotonic time
    start_time_formatted = DB.Column(DB.String, nullable=False) # local human-readable time

    def __repr__(self):
        return '<SavedRaceMeta %r>' % self.id

class SavedPilotRace(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    race_id = DB.Column(DB.Integer, nullable=False)
    node_index = DB.Column(DB.Integer, nullable=False)
    pilot_id = DB.Column(DB.Integer, nullable=False)
    history_values = DB.Column(DB.String, nullable=True)
    history_times = DB.Column(DB.String, nullable=True)
    penalty_time = DB.Column(DB.Integer, nullable=False)
    penalty_desc = DB.Column(DB.String, nullable=True)
    enter_at = DB.Column(DB.Integer, nullable=False)
    exit_at = DB.Column(DB.Integer, nullable=False)

    def __repr__(self):
        return '<SavedPilotRace %r>' % self.id

class SavedRaceLap(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    race_id = DB.Column(DB.Integer, nullable=False)
    pilotrace_id = DB.Column(DB.Integer, nullable=False)
    node_index = DB.Column(DB.Integer, nullable=False)
    pilot_id = DB.Column(DB.Integer, nullable=False)
    lap_time_stamp = DB.Column(DB.Integer, nullable=False)
    lap_time = DB.Column(DB.Integer, nullable=False)
    lap_time_formatted = DB.Column(DB.String, nullable=False)
    source = DB.Column(DB.Integer, nullable=False)
    deleted = DB.Column(DB.Boolean, nullable=False)

    def __repr__(self):
        return '<SavedRaceLap %r>' % self.id

LAP_SOURCE_REALTIME = 0
LAP_SOURCE_MANUAL = 1
LAP_SOURCE_RECALC = 2

class Profiles(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column(DB.String(80), nullable=False)
    description = DB.Column(DB.String(256), nullable=True)
    frequencies = DB.Column(DB.String(80), nullable=False)
    enter_ats = DB.Column(DB.String(80), nullable=True)
    exit_ats = DB.Column(DB.String(80), nullable=True)
    f_ratio = DB.Column(DB.Integer, nullable=True)

class RaceFormat(DB.Model):
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column(DB.String(80), nullable=False)
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
        settings = GlobalSettings.query.filter_by(option_name=option).one_or_none()
        if settings:
            return settings.option_value
        else:
            return default_value
    except:
        return default_value

def setOption(option, value):
    settings = GlobalSettings.query.filter_by(option_name=option).one_or_none()
    if settings:
        settings.option_value = value
    else:
        DB.session.add(GlobalSettings(option_name=option, option_value=value))
    DB.session.commit()

def getCurrentRaceFormat():
    if RACE.format is None:
        val = int(getOption('currentFormat'))
        race_format = RaceFormat.query.get(val)
        # create a shared instance
        RACE.format = RHRaceFormat.copy(race_format)
        RACE.format.id = race_format.id
    return RACE.format

def getCurrentDbRaceFormat():
    if RACE.format is None or RHRaceFormat.isDbBased(RACE.format):
        val = int(getOption('currentFormat'))
        return RaceFormat.query.get(val)
    else:
        return None

def setCurrentRaceFormat(race_format):
    if RHRaceFormat.isDbBased(race_format): # stored in DB, not internal race format
        setOption('currentFormat', race_format.id)
        # create a shared instance
        RACE.format = RHRaceFormat.copy(race_format)
        RACE.format.id = race_format.id
    else:
        RACE.format = race_format

class RHRaceFormat():
    def __init__(self, name, race_mode, race_time_sec, start_delay_min, start_delay_max, number_laps_win, win_condition, team_racing_mode):
        self.name = name
        self.race_mode = race_mode
        self.race_time_sec = race_time_sec
        self.start_delay_min = start_delay_min
        self.start_delay_max = start_delay_max
        self.number_laps_win = number_laps_win
        self.win_condition = win_condition
        self.team_racing_mode = team_racing_mode

    @classmethod
    def copy(cls, race_format):
        return RHRaceFormat(name=race_format.name,
                            race_mode=race_format.race_mode,
                            race_time_sec=race_format.race_time_sec,
                            start_delay_min=race_format.start_delay_min,
                            start_delay_max=race_format.start_delay_max,
                            number_laps_win=race_format.number_laps_win,
                            win_condition=race_format.win_condition,
                            team_racing_mode=race_format.team_racing_mode)

    @classmethod
    def isDbBased(cls, race_format):
        return hasattr(race_format, 'id')

#
# LED Code
#

def isLedEnabled():
    return Pixel is not None

def signal_handler(signal, frame):
    if isLedEnabled():
        onoff(strip, Color(0,0,0))
        sys.exit(0)

# LED one color ON/OFF
def onoff(strip, color):
    if isLedEnabled():
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color)
        strip.show()

def theaterChase(strip, color, wait_ms=50, iterations=5):
    """Movie theater light style chaser animation."""
    if isLedEnabled():
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
    if isLedEnabled():
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
    if isLedEnabled():
        for j in range(256*iterations):
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, wheel((i+j) & 255))
            strip.show()
            time.sleep(wait_ms/1000.0)

def rainbowCycle(strip, wait_ms=2, iterations=1):
    """Draw rainbow that uniformly distributes itself across all pixels."""
    if isLedEnabled():
        for j in range(256*iterations):
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, wheel((int(i * 256 / strip.numPixels()) + j) & 255))
            strip.show()
            time.sleep(wait_ms/1000.0)

def theaterChaseRainbow(strip, wait_ms=25):
    """Rainbow movie theater light style chaser animation."""
    if isLedEnabled():
        for j in range(256):
            for q in range(3):
                for i in range(0, strip.numPixels(), 3):
                    strip.setPixelColor(i+q, wheel((i+j) % 255))
                strip.show()
                time.sleep(wait_ms/1000.0)
                for i in range(0, strip.numPixels(), 3):
                    strip.setPixelColor(i+q, 0)

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

@APP.route('/marshal')
@requires_auth
def marshal():
    '''Route to race management page.'''
    return render_template('marshal.html', serverInfo=serverInfo, getOption=getOption, __=__,
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
        savedraceMeta=SavedRaceMeta,
        savedraceLap=SavedRaceLap,
        profiles=Profiles,
        race_format=RaceFormat,
        globalSettings=GlobalSettings)

# JSON API

from sqlalchemy.ext.declarative import DeclarativeMeta

class AlchemyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                if field is not "query" \
                    and field is not "query_class":
                    try:
                        json.dumps(data) # this will fail on non-encodable values, like other classes
                        if field is "frequencies":
                            fields[field] = json.loads(data)["f"]
                        elif field is "enter_ats" or field is "exit_ats":
                            fields[field] = json.loads(data)["v"]
                        else:
                            fields[field] = data
                    except TypeError:
                        fields[field] = None
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)

@APP.route('/api/pilot/all')
def api_pilot_all():
    pilots = Pilot.query.all()
    payload = []
    for pilot in pilots:
        payload.append(pilot)

    return json.dumps({"pilots": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/pilot/<int:pilot_id>')
def api_pilot(pilot_id):
    pilot = Pilot.query.get(pilot_id)

    return json.dumps({"pilot": pilot}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/heat/all')
def api_heat_all():
    all_heats = {}
    for heat in Heat.query.with_entities(Heat.heat_id).distinct():
        heatdata = Heat.query.filter_by(heat_id=heat.heat_id, node_index=0).first()
        pilots = []
        for node in range(RACE.num_nodes):
            pilot_id = Heat.query.filter_by(heat_id=heat.heat_id, node_index=node).first().pilot_id
            pilots.append(pilot_id)
        heat_id = heatdata.heat_id
        note = heatdata.note
        race_class = heatdata.class_id
        has_race = SavedRaceMeta.query.filter_by(heat_id=heat.heat_id).first()
        if has_race:
            locked = True
        else:
            locked = False

        all_heats[heat_id] = {'pilots': pilots,
            'note': note,
            'heat_id': heat_id,
            'class_id': race_class,
            'locked': locked}

    return json.dumps({"heats": all_heats}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/heat/<int:heat_id>')
def api_heat(heat_id):
    heatdata = Heat.query.filter_by(heat_id=heat_id, node_index=0).first()
    if heatdata:
        pilots = []
        for node in range(RACE.num_nodes):
            pilot_id = Heat.query.filter_by(heat_id=heat_id, node_index=node).first().pilot_id
            pilots.append(pilot_id)
        note = heatdata.note
        race_class = heatdata.class_id
        has_race = SavedRaceMeta.query.filter_by(heat_id=heat_id).first()
        if has_race:
            locked = True
        else:
            locked = False

        heat = {'pilots': pilots,
          'note': note,
          'heat_id': heat_id,
          'class_id': race_class,
          'locked': locked}
    else:
        heat = None

    payload = {
        'setup': heat,
        'leaderboard': calc_leaderboard(heat_id=heat_id)
    }

    return json.dumps({"heat": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/class/all')
def api_class_all():
    race_classes = RaceClass.query.all()
    payload = []
    for race_class in race_classes:
        payload.append(race_class)

    return json.dumps({"classes": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/class/<int:class_id>')
def api_class(class_id):
    race_class = RaceClass.query.get(class_id)

    return json.dumps({"class": race_class}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/format/all')
def api_format_all():
    formats = RaceFormat.query.all()
    payload = []
    for race_format in formats:
        payload.append(race_format)

    return json.dumps({"formats": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/format/<int:format_id>')
def api_format(format_id):
    raceformat = RaceFormat.query.get(format_id)

    return json.dumps({"format": raceformat}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/profile/all')
def api_profile_all():
    profiles = Profiles.query.all()
    payload = []
    for profile in profiles:
        payload.append(profile)

    return json.dumps({"profiles": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/profile/<int:profile_id>')
def api_profile(profile_id):
    profile = Profiles.query.get(profile_id)

    return json.dumps({"profile": profile}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/race/current')
def api_race_current():
    query = CurrentLap.query.all()
    laps = []
    for lap in query:
        laps.append(lap)

    payload = {
        "raw_laps": laps,
        "leaderboard": calc_leaderboard(current_race=True)
    }

    return json.dumps({"race": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/race/all')
def api_race_all():
    heats = []
    for heat in SavedRaceMeta.query.with_entities(SavedRaceMeta.heat_id).distinct().order_by(SavedRaceMeta.heat_id):
        max_rounds = DB.session.query(DB.func.max(SavedRaceMeta.round_id)).filter_by(heat_id=heat.heat_id).scalar()
        heats.append({
            "id": heat.heat_id,
            "rounds": max_rounds
        })

    payload = {
        "heats": heats,
        "leaderboard": calc_leaderboard()
    }

    return json.dumps({"races": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/race/<int:heat_id>/<int:round_id>')
def api_race(heat_id, round_id):
    race = SavedRaceMeta.query.filter_by(heat_id=heat_id, round_id=round_id).one()

    pilotraces = []
    for pilotrace in SavedPilotRace.query.filter_by(race_id=race.id).all():
        laps = []
        for lap in SavedRaceLap.query.filter_by(pilotrace_id=pilotrace.id).all():
            laps.append({
                    'id': lap.id,
                    'lap_time_stamp': lap.lap_time_stamp,
                    'lap_time': lap.lap_time,
                    'lap_time_formatted': lap.lap_time_formatted,
                    'source': lap.source,
                    'deleted': lap.deleted
                })

        pilot_data = Pilot.query.filter_by(id=pilotrace.pilot_id).first()
        if pilot_data:
            nodepilot = pilot_data.callsign
        else:
            nodepilot = None

        pilotraces.append({
            'callsign': nodepilot,
            'pilot_id': pilotrace.pilot_id,
            'node_index': pilotrace.node_index,
            'laps': laps
        })
    payload = {
        'start_time_formatted': race.start_time_formatted,
        'nodes': pilotraces,
        'leaderboard': calc_leaderboard(heat_id=heat_id, round_id=round_id)
    }

    return json.dumps({"race": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/status')
def api_status():
    data = {
        "server_info": {
            "server_api": serverInfo['server_api'],
            "json_api": serverInfo['json_api'],
            "node_api_best": serverInfo['node_api_best'],
            "release_version": serverInfo['release_version'],
            "node_api_match": serverInfo['node_api_match'],
            "node_api_lowest": serverInfo['node_api_lowest'],
            "node_api_levels": serverInfo['node_api_levels']
        },
        "state": {
            "current_heat": RACE.current_heat,
            "num_nodes": RACE.num_nodes,
            "race_status": RACE.race_status,
            "currentProfile": getOption('currentProfile'),
            "currentFormat": getOption('currentFormat'),
        }
    }

    return json.dumps({"status": data}), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/options')
def api_options():
    opt_query = GlobalSettings.query.all()
    options = {}
    if opt_query:
        for opt in opt_query:
            options[opt.option_name] = opt.option_value

        payload = options
    else:
        payload = None

    return json.dumps({"options": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

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

# LiveTime compatible events

@SOCKET_IO.on('get_version')
def on_get_version():
    session['LiveTime'] = True
    ver_parts = RELEASE_VERSION.split('.')
    return {'major': ver_parts[0], 'minor': ver_parts[1]}

@SOCKET_IO.on('get_timestamp')
def on_get_timestamp():
    if RACE.race_status == RACE_STATUS_STAGING:
        now = RACE_START
    else:
        now = monotonic()
    return {'timestamp': monotonic_to_milliseconds(now)}

@SOCKET_IO.on('get_settings')
def on_get_settings():
    return {'nodes': [{
        'frequency': node.frequency,
        'trigger_rssi': node.enter_at_level
        } for node in INTERFACE.nodes
    ]}

@SOCKET_IO.on('reset_auto_calibration')
def on_reset_auto_calibration(data):
    on_stop_race()
    on_discard_laps()
    setCurrentRaceFormat(SLAVE_RACE_FORMAT)
    emit_race_format()
    setOption("MinLapSec", "0")
    setOption("MinLapBehavior", "0")
    on_stage_race()

# Cluster events

@SOCKET_IO.on('join_cluster')
def on_join_cluster():
    setCurrentRaceFormat(SLAVE_RACE_FORMAT)
    emit_race_format()
    setOption("MinLapSec", "0")
    setOption("MinLapBehavior", "0")
    server_log('Joined cluster')

# RotorHazard events

@SOCKET_IO.on('load_data')
def on_load_data(data):
    '''Allow pages to load needed data'''
    load_types = data['load_types']
    for load_type in load_types:
        if load_type == 'node_data':
            emit_node_data(nobroadcast=True)
        elif load_type == 'environmental_data':
            emit_environmental_data(nobroadcast=True)
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
        elif load_type == 'leaderboard_cache':
            emit_leaderboard(nobroadcast=True, use_cache=True)
        elif load_type == 'current_laps':
            emit_current_laps(nobroadcast=True)
        elif load_type == 'race_status':
            emit_race_status(nobroadcast=True)
        elif load_type == 'current_heat':
            emit_current_heat(nobroadcast=True)
        elif load_type == 'team_racing_stat_if_enb':
            emit_team_racing_stat_if_enb(nobroadcast=True)
        elif load_type == 'race_list':
            emit_race_list(nobroadcast=True)
        elif load_type == 'language':
            emit_language(nobroadcast=True)
        elif load_type == 'all_languages':
            emit_all_languages(nobroadcast=True)
        elif load_type == 'imdtabler_page':
            emit_imdtabler_page(nobroadcast=True)
        elif load_type == 'cluster_status':
            CLUSTER.emitStatus()

@SOCKET_IO.on('broadcast_message')
def on_broadcast_message(data):
    emit_priority_message(data['message'], data['interrupt'])

# Settings socket io events

@SOCKET_IO.on('set_frequency')
def on_set_frequency(data):
    '''Set node frequency.'''
    CLUSTER.emit('set_frequency', data)
    if isinstance(data, basestring): # LiveTime compatibility
        data = json.loads(data)
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
    if session.get('LiveTime', False):
        emit('frequency_set', data)
    else:
        emit_frequency_data()

@SOCKET_IO.on('set_frequency_preset')
def on_set_frequency_preset(data):
    ''' Apply preset frequencies '''
    CLUSTER.emit('set_frequency_preset', data)
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

@SOCKET_IO.on('alter_heat')
def on_alter_heat(data):
    '''Update heat.'''
    heat = data['heat']
    node_index = data['node'] if 'node' in data else 0
    db_update = Heat.query.filter_by(heat_id=heat, node_index=node_index).one()
    if 'pilot' in data:
        db_update.pilot_id = data['pilot']
    if 'note' in data:
        global EVENT_RESULTS_CACHE_VALID
        EVENT_RESULTS_CACHE_VALID = False
        db_update.note = data['note']
    if 'class' in data:
        db_update.class_id = data['class']
    DB.session.commit()
    server_log('Heat {0} Node {1} altered to {2}'.format(heat, node_index+1, data))
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

@SOCKET_IO.on('alter_race_class')
def on_alter_race_class(data):
    '''Update race class.'''
    race_class = data['class_id']
    db_update = RaceClass.query.get(race_class)
    if 'class_name' in data:
        global EVENT_RESULTS_CACHE_VALID
        EVENT_RESULTS_CACHE_VALID = False
        db_update.name = data['class_name']
    if 'class_format' in data:
        db_update.format_id = data['class_format']
    if 'class_description' in data:
        db_update.description = data['class_description']
    DB.session.commit()
    server_log('Altered race class {0} to {1}'.format(race_class, data))
    emit_class_data(noself=True)
    if 'class_name' in data:
        emit_heat_data() # Update class names in heat displays
    if 'class_format' in data:
        emit_current_heat(noself=True) # in case race operator is a different client, update locked format dropdown

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

@SOCKET_IO.on('alter_pilot')
def on_alter_pilot(data):
    '''Update pilot.'''
    global EVENT_RESULTS_CACHE_VALID
    pilot_id = data['pilot_id']
    db_update = Pilot.query.get(pilot_id)
    if 'callsign' in data:
        EVENT_RESULTS_CACHE_VALID = False
        db_update.callsign = data['callsign']
    if 'team_name' in data:
        db_update.team = data['team_name']
    if 'phonetic' in data:
        db_update.phonetic = data['phonetic']
    if 'name' in data:
        EVENT_RESULTS_CACHE_VALID = False
        db_update.name = data['name']
    DB.session.commit()
    server_log('Altered pilot {0} to {1}'.format(pilot_id, data))
    emit_pilot_data(noself=True) # Settings page, new pilot settings
    if 'callsign' in data:
        emit_heat_data() # Settings page, new pilot callsign in heats
    if 'phonetic' in data:
        emit_heat_data() # Settings page, new pilot phonetic in heats. Needed?

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

@SOCKET_IO.on('alter_profile')
def on_alter_profile(data):
    ''' update profile '''
    current_profile = int(getOption("currentProfile"))
    profile = Profiles.query.get(current_profile)
    if 'profile_name' in data:
        profile.name = data['profile_name']
    if 'profile_description' in data:
        profile.description = data['profile_description']
    DB.session.commit()
    server_log('Altered current profile to %s' % (data))
    emit_node_tuning(noself=True)

@SOCKET_IO.on("set_profile")
def on_set_profile(data, emit_vals=True):
    ''' set current profile '''
    CLUSTER.emit('set_profile', data)
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
    CLUSTER.emit('shutdown_pi')
    emit_priority_message(__('Server has shut down.'), True)
    server_log('Shutdown pi')
    time.sleep(1);
    os.system("sudo shutdown now")

@SOCKET_IO.on("set_min_lap")
def on_set_min_lap(data):
    min_lap = data['min_lap']
    setOption("MinLapSec", data['min_lap'])
    server_log("set min lap time to %s seconds" % min_lap)
    emit_min_lap(noself=True)

@SOCKET_IO.on("set_min_lap_behavior")
def on_set_min_lap_behavior(data):
    min_lap_behavior = data['min_lap_behavior']
    setOption("MinLapBehavior", data['min_lap_behavior'])
    server_log("set min lap behavior to %s" % min_lap_behavior)
    emit_min_lap(noself=True)

@SOCKET_IO.on("set_race_format")
def on_set_race_format(data):
    ''' set current race_format '''
    if RACE.race_status == RACE_STATUS_READY: # prevent format change if race running
        race_format_val = data['race_format']
        race_format = RaceFormat.query.get(race_format_val)
        DB.session.flush()
        setCurrentRaceFormat(race_format)
        DB.session.commit()
        emit_race_format()
        server_log("set race format to '%s' (%s)" % (race_format.name, race_format.id))
        CLUSTER.emitToMirrors('set_race_format', data)
    else:
        emit_priority_message(__('Format change prevented by active race: Stop and save/discard laps'), False, nobroadcast=True)
        server_log("Format change prevented by active race")
        emit_race_format()

@SOCKET_IO.on('add_race_format')
def on_add_race_format():
    '''Adds new format in the database by duplicating an existing one.'''
    source_format = getCurrentRaceFormat()
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
    if RACE.race_status == RACE_STATUS_READY: # prevent format change if race running
        raceformat = getCurrentDbRaceFormat()
        if raceformat and (DB.session.query(RaceFormat).count() > 1): # keep one format
            DB.session.delete(raceformat)
            DB.session.commit()
            first_raceFormat = RaceFormat.query.first()
            setCurrentRaceFormat(first_raceFormat)
            emit_race_format()
    else:
        emit_priority_message(__('Format change prevented by active race: Stop and save/discard laps'), False, nobroadcast=True)
        server_log("Format change prevented by active race")

@SOCKET_IO.on('alter_race_format')
def on_alter_race_format(data):
    ''' update race format '''
    race_format = getCurrentDbRaceFormat()
    if race_format:
        emit = False
        if 'format_name' in data:
            race_format.name = data['format_name']
            emit = True
        if 'race_mode' in data:
            race_format.race_mode = data['race_mode']
        if 'race_time' in data:
            race_format.race_time_sec = data['race_time']
        if 'start_delay_min' in data:
            race_format.start_delay_min = data['start_delay_min']
        if 'start_delay_max' in data:
            race_format.start_delay_max = data['start_delay_max']
        if 'number_laps_win' in data:
            race_format.number_laps_win = data['number_laps_win']
        if 'win_condition' in data:
            race_format.win_condition = data['win_condition']
        if 'team_racing_mode' in data:
            race_format.team_racing_mode = (True if data['team_racing_mode'] else False)
        DB.session.commit()
        setCurrentRaceFormat(race_format)
        server_log('Altered race format to %s' % (data))
        if emit:
            emit_race_format()
            emit_class_data()

# Race management socket io events

@SOCKET_IO.on('schedule_race')
def on_schedule_race(data):
    global RACE_SCHEDULED
    global RACE_SCHEDULED_TIME

    RACE_SCHEDULED_TIME = monotonic() + (data['m'] * 60) + data['s']
    RACE_SCHEDULED = True

    SOCKET_IO.emit('race_scheduled', {
        'scheduled': RACE_SCHEDULED,
        'scheduled_at': RACE_SCHEDULED_TIME
        })

    emit_priority_message(__("Next race begins in {0:01d}:{1:02d}".format(data['m'], data['s'])), True)

@SOCKET_IO.on('cancel_schedule_race')
def cancel_schedule_race():
    global RACE_SCHEDULED

    RACE_SCHEDULED = False

    SOCKET_IO.emit('race_scheduled', {
        'scheduled': RACE_SCHEDULED,
        'scheduled_at': RACE_SCHEDULED_TIME
        })

    emit_priority_message(__("Scheduled race cancelled"), False)

@SOCKET_IO.on('get_pi_time')
def on_get_pi_time():
    # never broadcasts to all (client must make request)
    emit('pi_time', {
        'pi_time_s': monotonic()
    })

@SOCKET_IO.on('stage_race')
def on_stage_race():
    CLUSTER.emit('stage_race')
    if RACE.race_status == RACE_STATUS_READY: # only initiate staging if ready
        '''Common race start events (do early to prevent processing delay when start is called)'''
        global RACE_START
        global RACE_START_TOKEN
        global LAST_RACE_CACHE_VALID
        INTERFACE.enable_calibration_mode() # Nodes reset triggers on next pass

        onoff(strip, Color(255,128,0)) #ORANGE for STAGING
        clear_laps() # Clear laps before race start
        LAST_RACE_CACHE_VALID = False # invalidate last race results cache
        RACE.timer_running = 0 # indicate race timer not running
        RACE.race_status = RACE_STATUS_STAGING
        INTERFACE.set_race_status(RACE_STATUS_STAGING)
        emit_current_laps() # Race page, blank laps to the web client
        emit_leaderboard() # Race page, blank leaderboard to the web client
        emit_race_status()

        race_format = getCurrentRaceFormat()
        if race_format.team_racing_mode:
            check_emit_team_racing_status()  # Show initial team-racing status info
        MIN = min(race_format.start_delay_min, race_format.start_delay_max) # in case values are reversed
        MAX = max(race_format.start_delay_min, race_format.start_delay_max)
        DELAY = random.randint(MIN, MAX) + 1 # Add 1 for prestage

        RACE_START = monotonic() + DELAY
        RACE_START_TOKEN = random.random()
        gevent.spawn(race_start_thread, RACE_START_TOKEN)

        SOCKET_IO.emit('stage_ready', {
            'hide_stage_timer': MIN != MAX,
            'race_mode': race_format.race_mode,
            'race_time_sec': race_format.race_time_sec,
            'pi_starts_at_s': RACE_START
        }) # Announce staging with chosen delay

def race_start_thread(start_token):
    global Race_laps_winner_name

    # non-blocking delay before time-critical code
    while (monotonic() < RACE_START - 2):
        gevent.sleep(0.1)

    if RACE.race_status == RACE_STATUS_STAGING and \
        RACE_START_TOKEN == start_token:
        # Only start a race if it is not already in progress
        # Null this thread if token has changed (race stopped/started quickly)

        # create blocking delay until race start
        while monotonic() < RACE_START:
            pass

        # do time-critical tasks
        onoff(strip, Color(0,255,0)) #GREEN for GO

        # do secondary start tasks (small delay is acceptable)
        RACE.start_time = datetime.now()

        for node in INTERFACE.nodes:
            node.history_values = [] # clear race history
            node.history_times = []
            node.under_min_lap_count = 0

        RACE.race_status = RACE_STATUS_RACING # To enable registering passed laps
        INTERFACE.set_race_status(RACE_STATUS_RACING)
        RACE.timer_running = 1 # indicate race timer is running
        Race_laps_winner_name = None  # name of winner in first-to-X-laps race
        emit_race_status() # Race page, to set race button states
        server_log('Race started at {0} ({1:13f})'.format(RACE_START, monotonic_to_milliseconds(RACE_START)))

@SOCKET_IO.on('stop_race')
def on_stop_race():
    '''Stops the race and stops registering laps.'''
    global RACE_END

    CLUSTER.emit('stop_race')
    if RACE.race_status == RACE_STATUS_RACING:
        global RACE_DURATION_MS # To redefine main program variable
        RACE_END = monotonic() # Update the race end time stamp
        delta_time = RACE_END - RACE_START
        milli_sec = delta_time * 1000.0
        RACE_DURATION_MS = milli_sec

        server_log('Race stopped at {0} ({1:13f}), duration {2}ms'.format(RACE_END, monotonic_to_milliseconds(RACE_END), RACE_DURATION_MS))

        min_laps_list = []  # show nodes with laps under minimum (if any)
        for node in INTERFACE.nodes:
            if node.under_min_lap_count > 0:
                min_laps_list.append('Node {0} Count={1}'.format(node.index+1, node.under_min_lap_count))
        if len(min_laps_list) > 0:
            server_log('Nodes with laps under minimum:  ' + ', '.join(min_laps_list))

        RACE.race_status = RACE_STATUS_DONE # To stop registering passed laps, waiting for laps to be cleared
        INTERFACE.set_race_status(RACE_STATUS_DONE)
    else:
        server_log('No active race to stop')
        RACE.race_status = RACE_STATUS_READY # Go back to ready state
        INTERFACE.set_race_status(RACE_STATUS_READY)

    RACE.timer_running = 0 # indicate race timer not running
    RACE_SCHEDULED = False # also stop any deferred start

    SOCKET_IO.emit('stop_timer') # Loop back to race page to start the timer counting up
    emit_race_status() # Race page, to set race button states
    onoff(strip, Color(255,0,0)) #RED ON

@SOCKET_IO.on('save_laps')
def on_save_laps():
    '''Save current laps data to the database.'''
    global EVENT_RESULTS_CACHE_VALID
    EVENT_RESULTS_CACHE_VALID = False
    race_format = getCurrentRaceFormat()
    heat = Heat.query.filter_by(heat_id=RACE.current_heat, node_index=0).one()
    # Get the last saved round for the current heat
    max_round = DB.session.query(DB.func.max(SavedRaceMeta.round_id)) \
            .filter_by(heat_id=RACE.current_heat).scalar()
    if max_round is None:
        max_round = 0
    # Loop through laps to copy to saved races
    current_profile = int(getOption("currentProfile"))
    profile = Profiles.query.get(current_profile)
    profile_freqs = json.loads(profile.frequencies)

    new_race = SavedRaceMeta( \
        round_id=max_round+1, \
        heat_id=RACE.current_heat, \
        class_id=heat.class_id, \
        format_id=getOption('currentFormat'), \
        start_time = RACE_START, \
        start_time_formatted = RACE.start_time.strftime("%Y-%m-%d %H:%M:%S")
    )
    DB.session.add(new_race)
    DB.session.flush()
    DB.session.refresh(new_race)

    for node_index in range(RACE.num_nodes):
        if profile_freqs["f"][node_index] != FREQUENCY_ID_NONE:
            pilot_id = Heat.query.filter_by(heat_id=RACE.current_heat, node_index=node_index).first().pilot_id

            if pilot_id != PILOT_ID_NONE:
                new_pilotrace = SavedPilotRace( \
                    race_id=new_race.id, \
                    node_index=node_index, \
                    pilot_id=pilot_id, \
                    history_values=json.dumps(INTERFACE.nodes[node_index].history_values), \
                    history_times=json.dumps(INTERFACE.nodes[node_index].history_times), \
                    penalty_time=0, \
                    enter_at=INTERFACE.nodes[node_index].enter_at_level, \
                    exit_at=INTERFACE.nodes[node_index].exit_at_level
                )
                DB.session.add(new_pilotrace)
                DB.session.flush()
                DB.session.refresh(new_pilotrace)

                for lap in CurrentLap.query.filter_by(node_index=node_index).all():
                    DB.session.add(SavedRaceLap( \
                        race_id=new_race.id, \
                        pilotrace_id=new_pilotrace.id, \
                        node_index=node_index, \
                        pilot_id=pilot_id, \
                        lap_time_stamp=lap.lap_time_stamp, \
                        lap_time=lap.lap_time, \
                        lap_time_formatted=lap.lap_time_formatted, \
                        source = lap.source, \
                        deleted = False
                    ))

    DB.session.commit()
    server_log('Current laps saved: Heat {0} Round {1}'.format(RACE.current_heat, max_round+1))
    on_discard_laps() # Also clear the current laps
    emit_round_data_notify() # live update rounds page

@SOCKET_IO.on('resave_laps')
def on_resave_laps(data):
    global EVENT_RESULTS_CACHE_VALID
    EVENT_RESULTS_CACHE_VALID = False

    heat_id = data['heat_id']
    round_id = data['round_id']
    callsign = data['callsign']

    race_id = data['race_id']
    pilotrace_id = data['pilotrace_id']
    node = data['node']
    pilot_id = data['pilot_id']
    laps = data['laps']
    enter_at = data['enter_at']
    exit_at = data['exit_at']

    Pilotrace = SavedPilotRace.query.filter_by(id=pilotrace_id).one()
    Pilotrace.enter_at = enter_at
    Pilotrace.exit_at = exit_at

    SavedRaceLap.query.filter_by(pilotrace_id=pilotrace_id).delete()

    for lap in laps:
        tmp_lap_time_formatted = lap['lap_time']
        if isinstance(tmp_lap_time_formatted, float):
            tmp_lap_time_formatted = time_format(lap['lap_time'])
        DB.session.add(SavedRaceLap( \
            race_id=race_id, \
            pilotrace_id=pilotrace_id, \
            node_index=node, \
            pilot_id=pilot_id, \
            lap_time_stamp=lap['lap_time_stamp'], \
            lap_time=lap['lap_time'], \
            lap_time_formatted=tmp_lap_time_formatted,\
            source = lap['source'], \
            deleted = lap['deleted']
        ))

    DB.session.commit()
    message = __('Race times adjusted for: Heat {0} Round {1} / {2}').format(heat_id, round_id, callsign)
    emit_priority_message(message, False)
    emit_round_data_notify()
    server_log(message)

@SOCKET_IO.on('discard_laps')
def on_discard_laps():
    '''Clear the current laps without saving.'''
    CLUSTER.emit('discard_laps')
    clear_laps()
    RACE.race_status = RACE_STATUS_READY # Flag status as ready to start next race
    INTERFACE.set_race_status(RACE_STATUS_READY)
    emit_current_laps() # Race page, blank laps to the web client
    emit_leaderboard() # Race page, blank leaderboard to the web client
    emit_race_status() # Race page, to set race button states
    race_format = getCurrentRaceFormat()
    if race_format.team_racing_mode:
        check_emit_team_racing_status()  # Show team-racing status info
    else:
        emit_team_racing_status('')  # clear any displayed "Winner is" text

def clear_laps():
    '''Clear the current laps table.'''
    global LAST_RACE_CACHE
    global LAST_RACE_CACHE_VALID
    global Race_laps_winner_name
    LAST_RACE_CACHE = calc_leaderboard(current_race=True)
    LAST_RACE_CACHE_VALID = True
    Race_laps_winner_name = None  # clear winner in first-to-X-laps race
    DB.session.query(CurrentLap).delete() # Clear out the current laps table
    DB.session.query(LapSplit).delete()
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
    race_format = getCurrentRaceFormat()
    if race_format.team_racing_mode:
        check_emit_team_racing_status()  # Show initial team-racing status info

@SOCKET_IO.on('recover_pass')
def on_recover_pass(data):
    node_index = data['node']

    # define catch window
    start_time = monotonic() - int(getOption('MinLapSec'))

    history_values = INTERFACE.nodes[node_index].history_values
    history_times = INTERFACE.nodes[node_index].history_times

    if len(history_values):
        start_index = bisect.bisect_left(history_times, start_time)

        if start_index <= len(history_values):
            if data['method'] == 'max': # catch missed pass
                max_idx_local = max(xrange(len(history_values[start_index:])), key=history_values[start_index:].__getitem__)
                max_idx = start_index + max_idx_local
                max_rssi = history_values[max_idx]
                max_rssi_time = history_times[max_idx]

                server_log('Recovering pass: Node {0} / Pass {1}'.format(node_index + 1, max_rssi_time))

                # record best lap possible regardless of data validity (client asked for one)
                INTERFACE.intf_simulate_lap(node_index, max_rssi_time)

                new_enterat = max_rssi - int(getOption("HistoryMaxOffset"))

                if new_enterat > INTERFACE.nodes[node_index].node_nadir_rssi:
                    if new_enterat < INTERFACE.nodes[node_index].node_peak_rssi:
                        if new_enterat >= INTERFACE.nodes[node_index].exit_at_level + int(getOption("HistoryMinOffset")):
                            on_set_enter_at_level({
                                'node': node_index,
                                'enter_at_level': new_enterat
                            })
                        else:
                            emit_priority_message(__('No tuning adjustment made on node {0}: Requested Enterat of {1} is too close or below ExitAt.').format(node_index + 1, new_enterat), False, nobroadcast=True)
                            server_log('Skipping EnterAt adjustment: new RSSI of {0} too close to ExitAt {1}' \
                                .format(new_enterat, INTERFACE.nodes[node_index].exit_at_level))

                    else:
                        emit_priority_message(__('Tuning adjust failed on node {0}: Bad RSSI value ').format(node_index + 1), False, nobroadcast=True)
                        server_log('Skipping EnterAt adjustment: new RSSI of {0} not below Node Peak {1}' \
                            .format(new_enterat, INTERFACE.nodes[node_index].node_peak_rssi))
                else:
                    emit_priority_message(__('Tuning adjust failed on node {0}: Bad RSSI value').format(node_index + 1), False, nobroadcast=True)
                    server_log('Skipping EnterAt adjustment: new RSSI of {0} not above Node Nadir {1}' \
                        .format(new_enterat, INTERFACE.nodes[node_index].node_nadir_rssi))

            elif data['method'] == 'min': # force end crossing
                server_log('Force end crossing: Node {0}'.format(node_index + 1))

                # end crossing now
                if INTERFACE.nodes[node_index].crossing_flag:
                    INTERFACE.force_end_crossing(node_index)

                    min_idx_local = min(xrange(len(history_values[start_index:])), key=history_values[start_index:].__getitem__)
                    min_idx = start_index + min_idx_local
                    min_rssi = history_values[min_idx]
                    min_rssi_time = history_times[min_idx]

                    new_exitat = min_rssi + int(getOption("HistoryMinOffset"))

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
                                    .format(min_rssi, INTERFACE.nodes[node_index].node_peak_rssi))

                        on_set_exit_at_level({
                            'node': node_index,
                            'exit_at_level': new_exitat
                        })
                    else:
                        emit_priority_message(__('Force end failed on node {0}: Bad RSSI value').format(node_index + 1), False, nobroadcast=True)
                        server_log('Skipping ExitAt adjustment: RSSI of {0} above Node Nadir {1}' \
                            .format(min_rssi, INTERFACE.nodes[node_index].node_nadir_rssi))
                else:
                    emit_priority_message(__('Cannot force end: Node {0} is not crossing').format(node_index + 1), False, nobroadcast=True)
                    server_log('Skipping ExitAt adjustment: Node {0} is not crossing'.format(node_index + 1))

            emit_enter_and_exit_at_levels()
        else:
            emit_priority_message(__('Cannot perform operation on Node {0}: Not enough history').format(node_index + 1), False, nobroadcast=True)
            server_log('Cannot perform operation on Node {0}: Not enough history'.format(node_index + 1))
    else:
        emit_priority_message(__('Cannot perform operation on Node {0}: Not enough history').format(node_index + 1), False, nobroadcast=True)
        server_log('Cannot perform operation on Node {0}: Not enough history'.format(node_index + 1))


@SOCKET_IO.on('delete_lap')
def on_delete_lap(data):
    '''Delete a false lap.'''
    node_index = data['node']
    lap_id = data['lapid']
    max_lap = DB.session.query(DB.func.max(CurrentLap.lap_id)) \
        .filter_by(node_index=node_index).scalar()
    if lap_id is not max_lap:
        # Update the lap_time for the next lap
        previous_lap = CurrentLap.query.filter_by(node_index=node_index, lap_id=lap_id-1).one()
        next_lap = CurrentLap.query.filter_by(node_index=node_index, lap_id=lap_id+1).one()
        next_lap.lap_time = next_lap.lap_time_stamp - previous_lap.lap_time_stamp
        next_lap.lap_time_formatted = time_format(next_lap.lap_time)
        # Delete the false lap
        CurrentLap.query.filter_by(node_index=node_index, lap_id=lap_id).delete()
        # Update lap numbers
        for lap in CurrentLap.query.filter(CurrentLap.node_index==node_index, CurrentLap.lap_id>lap_id).all():
            lap.lap_id = lap.lap_id - 1
        # Update splits
        last_split_id = DB.session.query(DB.func.max(LapSplit.split_id)).filter_by(lap_id=lap_id-1).scalar()
        if last_split_id:
            LapSplit.query.filter(LapSplit.node_index==node_index, LapSplit.lap_id==lap_id, LapSplit.split_id<=last_split_id).delete()
            for split in LapSplit.query.filter(LapSplit.node_index==node_index, LapSplit.lap_id==lap_id, LapSplit.split_id>last_split_id).all():
                split.lap_id = split.lap_id - 1
            for split in LapSplit.query.filter(LapSplit.node_index==node_index, LapSplit.lap_id>lap_id).all():
                split.lap_id = split.lap_id - 1
    else:
        # Delete the false lap
        CurrentLap.query.filter(CurrentLap.node_index==node_index, CurrentLap.lap_id==lap_id).delete()
        # Merge splits
        last_split_id = DB.session.query(DB.func.max(LapSplit.split_id)).filter_by(lap_id=lap_id-1).scalar()
        if last_split_id:
            LapSplit.query.filter(LapSplit.node_index==node_index, LapSplit.lap_id==lap_id, LapSplit.split_id<=last_split_id).delete()
            for split in LapSplit.query.filter(LapSplit.node_index==node_index, LapSplit.lap_id==lap_id, LapSplit.split_id>last_split_id).all():
                split.lap_id = split.lap_id - 1
    DB.session.commit()
    server_log('Lap deleted: Node {0} Lap {1}'.format(node_index+1, lap_id))
    emit_current_laps() # Race page, update web client
    emit_leaderboard() # Race page, update web client
    race_format = getCurrentRaceFormat()
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
    INTERFACE.intf_simulate_lap(node_index, 0)

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

@SOCKET_IO.on('LED_brightness')
def on_LED_brightness(data):
    '''Change LED Brightness'''
    brightness = data['brightness']
    strip.setBrightness(brightness)
    strip.show()
    setOption("ledBrightness", brightness)

@SOCKET_IO.on('set_option')
def on_set_option(data):
    setOption(data['option'], data['value'])

@SOCKET_IO.on('get_race_scheduled')
def get_race_elapsed():
    # never broadcasts to all

    emit('race_scheduled', {
        'scheduled': RACE_SCHEDULED,
        'scheduled_at': RACE_SCHEDULED_TIME
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
    race_format = getCurrentRaceFormat()

    emit_payload = {
            'race_status': RACE.race_status,
            'race_mode': race_format.race_mode,
            'race_time_sec': race_format.race_time_sec,
            'hide_stage_timer': race_format.start_delay_min != race_format.start_delay_max,
            'pi_starts_at_s': RACE_START
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

def emit_environmental_data(**params):
    '''Emits environmental data.'''
    emit_payload = {
        'core_temperature': INTERFACE.core_temp,
        'aux_voltage': [data['voltage'] for data in INTERFACE.ina219_data],
        'aux_current': [data['current'] for data in INTERFACE.ina219_data],
        'aux_power': [data['power'] for data in INTERFACE.ina219_data],
        'aux_temperature': [data.temperature for data in INTERFACE.bme280_data],
        'aux_pressure': [data.pressure for data in INTERFACE.bme280_data],
        'aux_humidity': [data.humidity for data in INTERFACE.bme280_data]
    }
    if ('nobroadcast' in params):
        emit('environmental_data', emit_payload)
    else:
        SOCKET_IO.emit('environmental_data', emit_payload)

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
    race_format = getCurrentRaceFormat()
    is_db_race_format = RHRaceFormat.isDbBased(race_format)
    has_race = not is_db_race_format or SavedRaceMeta.query.filter_by(format_id=race_format.id).first()
    if has_race:
        locked = True
    else:
        locked = False

    emit_payload = {
        'format_ids': [raceformat.id for raceformat in RaceFormat.query.all()],
        'format_names': [raceformat.name for raceformat in RaceFormat.query.all()],
        'current_format': race_format.id if is_db_race_format else None,
        'format_name': race_format.name,
        'race_mode': race_format.race_mode,
        'race_time_sec': race_format.race_time_sec,
        'start_delay_min': race_format.start_delay_min,
        'start_delay_max': race_format.start_delay_max,
        'number_laps_win': race_format.number_laps_win,
        'win_condition': race_format.win_condition,
        'team_racing_mode': 1 if race_format.team_racing_mode else 0,
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
    global LAST_RACE_LAPS_CACHE
    if 'use_cache' in params and LAST_RACE_CACHE_VALID:
        emit_payload = LAST_RACE_LAPS_CACHE
    else:
        current_laps = []
        # for node in DB.session.query(CurrentLap.node_index).distinct():
        for node in range(RACE.num_nodes):
            node_laps = []
            last_lap_id = -1
            for lap in CurrentLap.query.filter_by(node_index=node).order_by(CurrentLap.lap_id).all():
                splits = get_splits(node, lap.lap_id, True)
                node_laps.append({
                    'lap_id': lap.lap_id,
                    'lap_raw': lap.lap_time,
                    'lap_time': lap.lap_time_formatted,
                    'lap_time_stamp': lap.lap_time_stamp,
                    'splits': splits
                })
                last_lap_id = lap.lap_id
            splits = get_splits(node, last_lap_id+1, False)
            if splits:
                node_laps.append({
                    'lap_id': last_lap_id+1,
                    'lap_time': '',
                    'lap_time_stamp': 0,
                    'splits': splits
                })
            current_laps.append({
                'laps': node_laps
            })
        current_laps = {'node_index': current_laps}
        emit_payload = current_laps
        LAST_RACE_LAPS_CACHE = current_laps

    if ('nobroadcast' in params):
        emit('current_laps', emit_payload)
    else:
        SOCKET_IO.emit('current_laps', emit_payload)

def get_splits(node, lap_id, lapCompleted):
    splits = []
    for slave_index in range(len(CLUSTER.slaves)):
        split = LapSplit.query.filter_by(node_index=node,lap_id=lap_id,split_id=slave_index).one_or_none()
        if split:
            split_payload = {
                'split_id': slave_index,
                'split_raw': split.split_time,
                'split_time': split.split_time_formatted,
                'split_speed': '{0:.2f}'.format(split.split_speed) if split.split_speed <> None else '-'
            }
        elif lapCompleted:
            split_payload = {
                'split_id': slave_index,
                'split_time': '-'
            }
        else:
            break
        splits.append(split_payload)

    return splits

def emit_race_list(**params):
    '''Emits race listing'''
    heats = {}
    for heat in SavedRaceMeta.query.with_entities(SavedRaceMeta.heat_id).distinct().order_by(SavedRaceMeta.heat_id):
        heatnote = Heat.query.filter_by( heat_id=heat.heat_id ).first().note

        rounds = {}
        for round in SavedRaceMeta.query.distinct().filter_by(heat_id=heat.heat_id).order_by(SavedRaceMeta.round_id):
            pilotraces = []
            for pilotrace in SavedPilotRace.query.filter_by(race_id=round.id).all():
                laps = []
                for lap in SavedRaceLap.query.filter_by(pilotrace_id=pilotrace.id).order_by(SavedRaceLap.lap_time_stamp).all():
                    laps.append({
                            'id': lap.id,
                            'lap_time_stamp': lap.lap_time_stamp,
                            'lap_time': lap.lap_time,
                            'lap_time_formatted': lap.lap_time_formatted,
                            'source': lap.source,
                            'deleted': lap.deleted
                        })

                pilot_data = Pilot.query.filter_by(id=pilotrace.pilot_id).first()
                if pilot_data:
                    nodepilot = pilot_data.callsign
                else:
                    nodepilot = None

                pilotraces.append({
                    'pilotrace_id': pilotrace.id,
                    'callsign': nodepilot,
                    'pilot_id': pilotrace.pilot_id,
                    'node_index': pilotrace.node_index,
                    'history_values': json.loads(pilotrace.history_values),
                    'history_times': json.loads(pilotrace.history_times),
                    'laps': laps,
                    'enter_at': pilotrace.enter_at,
                    'exit_at': pilotrace.exit_at,
                })
            rounds[round.round_id] = {
                'race_id': round.id,
                'class_id': round.class_id,
                'format_id': round.format_id,
                'start_time': round.start_time,
                'start_time_formatted': round.start_time_formatted,
                'pilotraces': pilotraces
            }
        heats[heat.heat_id] = {
            'heat_id': heat.heat_id,
            'note': heatnote,
            'rounds': rounds,
        }

    '''
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
        current_classes[race_class.id] = current_class
    '''

    emit_payload = {
        'heats': heats,
        # 'heats_by_class': heats_by_class,
        # 'classes': current_classes,
    }

    if ('nobroadcast' in params):
        emit('race_list', emit_payload)
    else:
        SOCKET_IO.emit('race_list', emit_payload)

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
        for heat in SavedRaceMeta.query.with_entities(SavedRaceMeta.heat_id).distinct().order_by(SavedRaceMeta.heat_id):
            heatnote = Heat.query.filter_by( heat_id=heat.heat_id ).first().note

            rounds = []
            for round in SavedRaceMeta.query.distinct().filter_by(heat_id=heat.heat_id).order_by(SavedRaceMeta.round_id):
                pilotraces = []
                for pilotrace in SavedPilotRace.query.filter_by(race_id=round.id).all():
                    laps = []
                    for lap in SavedRaceLap.query.filter_by(pilotrace_id=pilotrace.id).all():
                        laps.append({
                                'id': lap.id,
                                'lap_time_stamp': lap.lap_time_stamp,
                                'lap_time': lap.lap_time,
                                'lap_time_formatted': lap.lap_time_formatted,
                                'source': lap.source,
                                'deleted': lap.deleted
                            })

                    pilot_data = Pilot.query.filter_by(id=pilotrace.pilot_id).first()
                    if pilot_data:
                        nodepilot = pilot_data.callsign
                    else:
                        nodepilot = None

                    pilotraces.append({
                        'callsign': nodepilot,
                        'pilot_id': pilotrace.pilot_id,
                        'node_index': pilotrace.node_index,
                        'laps': laps
                    })
                rounds.append({
                    'id': round.round_id,
                    'start_time_formatted': round.start_time_formatted,
                    'nodes': pilotraces,
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

    # Get profile (current), frequencies (current), race query (saved), and race format (all)
    if USE_CURRENT:
        current_profile = int(getOption("currentProfile"))
        profile = Profiles.query.get(current_profile)
        profile_freqs = json.loads(profile.frequencies)

        race_format = getCurrentRaceFormat()
    else:
        if USE_CLASS:
            race_query = SavedRaceMeta.query.filter_by(class_id=USE_CLASS)
            current_format = RaceClass.query.get(USE_CLASS).format_id
        elif USE_HEAT:
            if USE_ROUND:
                race_query = SavedRaceMeta.query.filter_by(heat_id=USE_HEAT, round_id=USE_ROUND)
                current_format = race_query.first().format_id
            else:
                race_query = SavedRaceMeta.query.filter_by(heat_id=USE_HEAT)
                heat_class = race_query.first().class_id
                if heat_class:
                    current_format = RaceClass.query.get(heat_class).format_id
                else:
                    current_format = None
        else:
            race_query = SavedRaceMeta.query
            current_format = None

        selected_races = race_query.all()
        racelist = [r.id for r in selected_races]

        if current_format:
            race_format = RaceFormat.query.get(current_format)
        else:
            race_format = None

    # Get the pilot ids for all relevant races
    # Add pilot callsigns
    # Add pilot team names
    # Get total laps for each pilot
    # Get hole shot laps
    pilot_ids = []
    callsigns = []
    team_names = []
    max_laps = []
    holeshots = []

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
            # find hole shots
            holeshot_laps = []
            for race in racelist:
                pilotraces = SavedPilotRace.query \
                    .filter(SavedPilotRace.pilot_id == pilot.id, \
                    SavedPilotRace.race_id == race \
                    ).all()

                for pilotrace in pilotraces:
                    holeshot_lap = SavedRaceLap.query \
                        .filter(SavedRaceLap.pilotrace_id == pilotrace.id, \
                            SavedRaceLap.deleted != 1, \
                            ).order_by(SavedRaceLap.lap_time_stamp).first()

                    if holeshot_lap:
                        holeshot_laps.append(holeshot_lap.id)

            # get total laps
            stat_query = DB.session.query(DB.func.count(SavedRaceLap.id)) \
                .filter(SavedRaceLap.pilot_id == pilot.id, \
                    SavedRaceLap.deleted != 1, \
                    SavedRaceLap.race_id.in_(racelist), \
                    ~SavedRaceLap.id.in_(holeshot_laps))

            max_lap = stat_query.scalar()
            if max_lap > 0:
                pilot_ids.append(pilot.id)
                callsigns.append(pilot.callsign)
                team_names.append(pilot.team)
                max_laps.append(max_lap)
                holeshots.append(holeshot_laps)

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
                stat_query = DB.session.query(DB.func.sum(SavedRaceLap.lap_time)) \
                    .filter(SavedRaceLap.pilot_id == pilot, \
                        SavedRaceLap.deleted != 1, \
                        SavedRaceLap.race_id.in_(racelist))

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
                stat_query = DB.session.query(DB.func.avg(SavedRaceLap.lap_time)) \
                    .filter(SavedRaceLap.pilot_id == pilot, \
                        SavedRaceLap.deleted != 1, \
                        SavedRaceLap.race_id.in_(racelist), \
                        ~SavedRaceLap.id.in_(holeshots[i]))

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
                stat_query = DB.session.query(DB.func.min(SavedRaceLap.lap_time)) \
                    .filter(SavedRaceLap.pilot_id == pilot, \
                        SavedRaceLap.deleted != 1, \
                        SavedRaceLap.race_id.in_(racelist), \
                        ~SavedRaceLap.id.in_(holeshots[i]))

            fast_lap = stat_query.scalar()
            fastest_lap.append(fast_lap)

        # find best consecutive 3 laps
        if max_laps[i] < 3:
            consecutives.append(None)
        else:
            all_consecutives = []

            if USE_CURRENT:
                thisrace = DB.session.query(CurrentLap.lap_time) \
                    .filter(CurrentLap.lap_id != 0, \
                    CurrentLap.pilot_id == pilot).all()

                for j in range(len(thisrace) - 2):
                    all_consecutives.append(thisrace[j].lap_time + thisrace[j+1].lap_time + thisrace[j+2].lap_time)

            else:
                for race_id in racelist:
                    thisrace = DB.session.query(SavedRaceLap.lap_time) \
                        .filter(SavedRaceLap.pilot_id == pilot, \
                            SavedRaceLap.race_id == race_id, \
                            SavedRaceLap.deleted != 1, \
                            ~SavedRaceLap.id.in_(holeshots[i]) \
                            ).all()

                    if len(thisrace) >= 3:
                        for j in range(len(thisrace) - 2):
                            all_consecutives.append(thisrace[j].lap_time + thisrace[j+1].lap_time + thisrace[j+2].lap_time)

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
    if 'use_cache' in params and LAST_RACE_CACHE_VALID:
        emit_payload = LAST_RACE_CACHE
    else:
        emit_payload = calc_leaderboard(current_race=True)

    if ('nobroadcast' in params):
        emit('leaderboard', emit_payload)
    else:
        SOCKET_IO.emit('leaderboard', emit_payload)

def emit_heat_data(**params):
    '''Emits heat data.'''
    current_heats = {}
    for heat in Heat.query.with_entities(Heat.heat_id).distinct():
        heatdata = Heat.query.filter_by(heat_id=heat.heat_id, node_index=0).one()
        pilots = []
        for node in range(RACE.num_nodes):
            pilot_id = Heat.query.filter_by(heat_id=heat.heat_id, node_index=node).one().pilot_id
            pilots.append(pilot_id)
        heat_id = heatdata.heat_id
        note = heatdata.note
        race_class = heatdata.class_id
        has_race = SavedRaceMeta.query.filter_by(heat_id=heat.heat_id).first()
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

    pilots = []
    for pilot in Pilot.query.all():
        pilots.append({
            'pilot_id': pilot.id,
            'callsign': pilot.callsign,
            'name': pilot.name
            })

    emit_payload = {
        'heats': current_heats,
        'pilot_data': pilots,
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

        has_race = SavedRaceMeta.query.filter_by(class_id=race_class.id).one_or_none()
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
    pilots_list = []
    for pilot in Pilot.query.all():
        opts_str = '' # create team-options string for each pilot, with current team selected
        for name in TEAM_NAMES_LIST:
            opts_str += '<option value="' + name + '"'
            if name == pilot.team:
                opts_str += ' selected'
            opts_str += '>' + name + '</option>'

        pilots_list.append({
            'pilot_id': pilot.id,
            'callsign': pilot.callsign,
            'team': pilot.team,
            'phonetic': pilot.phonetic,
            'name': pilot.name,
            'team_options': opts_str
        })

    emit_payload = {
        'pilots': pilots_list
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

    heat_data = Heat.query.filter_by(heat_id=RACE.current_heat, node_index=0).one()

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
                pilot_team_dict[pilot_id] = Pilot.query.filter_by(id=pilot_id).one().team
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
    race_format = getCurrentRaceFormat()
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
                    lap_data = CurrentLap.query.filter_by(node_index=node.index, lap_id=num_laps_win).one()
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
    global Race_laps_winner_name

    race_format = getCurrentRaceFormat()
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
                    # not waiting for crossing
                    if pass_node_index >= 0 and Race_laps_winner_name is not RACE_STATUS_CROSSING:
                        num_max_lap += 1  # count number of teams at max lap
                        if ent[1] < win_tstamp:  # this team has earlier lap time
                            win_name = team_name
                            win_tstamp = ent[1]
                    else:  # waiting for crossing
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
                                            # allow race tied when gate crossing completes
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
                        lap_data = CurrentLap.query.filter_by(node_index=node.index, lap_id=lap_id).one_or_none()
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
            win_callsign = Pilot.query.filter_by(id=win_pilot_id).one().callsign
            Race_laps_winner_name = win_callsign  # indicate a pilot has won
            emit_team_racing_status('Winner is ' + Race_laps_winner_name)
            win_phon_name = Pilot.query.filter_by(id=win_pilot_id).one().phonetic
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
                                'java -jar ' + IMDTABLER_JAR_NAME + ' -v', shell=True).rstrip()
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
                        'java -jar ' + IMDTABLER_JAR_NAME + ' -t ' + ' '.join(fs_list), shell=True)
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
                        'java -jar ' + IMDTABLER_JAR_NAME + ' -r ' + ' '.join(fs_list), shell=True).rstrip()
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
    '''Allow time for connection handshake to terminate before emitting data'''
    gevent.sleep(0.010)

    '''Emits current rssi data.'''
    while True:
        node_data = INTERFACE.get_heartbeat_json()

        SOCKET_IO.emit('heartbeat', node_data)
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
        if (heartbeat_thread_function.iter_tracker % 20) == 0:
            emit_node_data()

        # emit cluster status less often:
        if (heartbeat_thread_function.iter_tracker % 20) == 10:
            CLUSTER.emitStatus()

        # emit environment data less often:
        if (heartbeat_thread_function.iter_tracker % 100) == 0:
            INTERFACE.update_environmental_data()
            emit_environmental_data()

        # check if race is to be started
        global RACE_SCHEDULED
        if RACE_SCHEDULED:
            if monotonic() > RACE_SCHEDULED_TIME:
                on_stage_race()
                RACE_SCHEDULED = False

        gevent.sleep(0.100)

def ms_from_race_start():
    '''Return milliseconds since race start.'''
    delta_time = monotonic() - RACE_START
    milli_sec = delta_time * 1000.0
    return milli_sec

def ms_to_race_scheduled():
    '''Return milliseconds since race start.'''
    if RACE_SCHEDULED:
        delta_time = monotonic() - RACE_SCHEDULED_TIME
        milli_sec = delta_time * 1000.0
        return milli_sec
    else:
        return None

def ms_from_program_start():
    '''Returns the elapsed milliseconds since the start of the program.'''
    delta_time = monotonic() - PROGRAM_START
    milli_sec = delta_time * 1000.0
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

def time_format_mmss(millis):
    '''Convert milliseconds to 00:00'''
    if millis is None:
        return None

    millis = int(millis)
    minutes = millis / 60000
    over = millis % 60000
    seconds = over / 1000
    over = over % 1000
    return '{0:01d}:{1:02d}'.format(minutes, seconds)

def check_race_time_expired():
    race_format = getCurrentRaceFormat()
    if race_format and race_format.race_mode == 0: # count down
        if monotonic() >= RACE_START + race_format.race_time_sec:
            RACE.timer_running = 0 # indicate race timer no longer running
            if race_format.win_condition == WIN_CONDITION_MOST_LAPS:  # Most Laps Wins Enabled
                check_most_laps_win()  # check if pilot or team has most laps for win

def pass_record_callback(node, lap_timestamp_absolute, source):
    '''Handles pass records from the nodes.'''

    server_log('Raw pass record: Node: {0}, MS Since Lap: {1}'.format(node.index+1, lap_timestamp_absolute))
    node.debug_pass_count += 1
    emit_node_data() # For updated triggers and peaks

    global Race_laps_winner_name
    profile_freqs = json.loads(Profiles.query.get(int(getOption("currentProfile"))).frequencies)
    if profile_freqs["f"][node.index] != FREQUENCY_ID_NONE:
        # always count laps if race is running, otherwise test if lap should have counted before race end (RACE_DURATION_MS is invalid while race is in progress)
        if RACE.race_status is RACE_STATUS_RACING \
            or (RACE.race_status is RACE_STATUS_DONE and \
                lap_timestamp_absolute < RACE_END):

            # Get the current pilot id on the node
            pilot_id = Heat.query.filter_by( \
                heat_id=RACE.current_heat, node_index=node.index).one().pilot_id

            # reject passes before race start and with disabled (no-pilot) nodes
            if pilot_id != PILOT_ID_NONE:
                if lap_timestamp_absolute >= RACE_START:

                    lap_time_stamp = (lap_timestamp_absolute - RACE_START)
                    lap_time_stamp *= 1000 # store as milliseconds

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
                            node_index=node.index, lap_id=last_lap_id).one().lap_time_stamp
                        # New lap time is the difference between the current time stamp and the last
                        lap_time = lap_time_stamp - last_lap_time_stamp
                        lap_id = last_lap_id + 1

                    race_format = getCurrentRaceFormat()
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
                        SOCKET_IO.emit('pass_record', {
                            'node': node.index,
                            'frequency': node.frequency,
                            'timestamp': lap_time_stamp + monotonic_to_milliseconds(RACE_START)
                        })
                        # Add the new lap to the database
                        DB.session.add(CurrentLap(node_index=node.index, pilot_id=pilot_id, lap_id=lap_id, \
                            lap_time_stamp=lap_time_stamp, lap_time=lap_time, \
                            lap_time_formatted=time_format(lap_time), source=source))
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

                else:
                    server_log('Pass record dismissed: Node: {0}, Race not started' \
                        .format(node.index+1))
            else:
                server_log('Pass record dismissed: Node: {0}, Pilot not defined' \
                    .format(node.index+1))
    else:
        server_log('Pass record dismissed: Node: {0}, Frequency not defined' \
            .format(node.index+1))

def new_enter_or_exit_at_callback(node, is_enter_at_flag):
    if is_enter_at_flag:
        server_log('Finished capture of enter-at level for node {0}, level={1}, count={2}'.format(node.index+1, node.enter_at_level, node.cap_enter_at_count))
        on_set_enter_at_level({
            'node': node.index,
            'enter_at_level': node.enter_at_level
        })
        emit_enter_at_level(node)
    else:
        server_log('Finished capture of exit-at level for node {0}, level={1}, count={2}'.format(node.index+1, node.exit_at_level, node.cap_exit_at_count))
        on_set_exit_at_level({
            'node': node.index,
            'exit_at_level': node.exit_at_level
        })
        emit_exit_at_level(node)

def node_crossing_callback(node):
    if node.crossing_flag:
        if node.index==0:
            onoff(strip, Color(0,31,255)) # Blue
        elif node.index==1:
            onoff(strip, Color(255,63,0)) # Orange
        elif node.index==2:
            onoff(strip, Color(127,255,0)) # Light Green
        elif node.index==3:
            onoff(strip, Color(255,255,0)) # Yellow
        elif node.index==4:
            onoff(strip, Color(127,0,255)) # Purple
        elif node.index==5:
            onoff(strip, Color(255,0,127)) # Pink
        elif node.index==6:
            onoff(strip, Color(63,255,63)) # Mint
        elif node.index==7:
            onoff(strip, Color(0,191,255)) # Sky
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
    DB.session.query(SavedRaceMeta).delete()
    DB.session.query(SavedPilotRace).delete()
    DB.session.query(SavedRaceLap).delete()
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
    setCurrentRaceFormat(RaceFormat.query.first())
    server_log("Database reset race formats")

def db_reset_options_defaults():
    DB.session.query(GlobalSettings).delete()
    setOption("server_api", SERVER_API)
    # group identifiers
    setOption("timerName", __("RotorHazard"))
    setOption("timerLogo", "")
    # group colors
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
    # timer state
    setOption("currentLanguage", "")
    setOption("currentProfile", "1")
    setCurrentRaceFormat(RaceFormat.query.first())
    # minimum lap
    setOption("MinLapSec", "10")
    setOption("MinLapBehavior", "0")
    # pass catching settings
    setOption("HistoryExpireDuration", "10000")
    setOption("HistoryMaxOffset", "10")
    setOption("HistoryMinOffset", "10")
    # event information
    setOption("eventName", __("FPV Race"))
    setOption("eventDescription", "")
    # LED settings
    setOption("ledBrightness", "32")

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

        # RSSI reduced by half for 2.0.0
        if int(getOption('server_api')) < 23:
            for profile in profiles_query_data:
                if profile.enter_ats:
                    enter_ats = json.loads(profile.enter_ats)
                    enter_ats["v"] = [val/2 for val in enter_ats["v"]]
                    profile.enter_ats = json.dumps(enter_ats)
                if profile.exit_ats:
                    exit_ats = json.loads(profile.exit_ats)
                    exit_ats["v"] = [val/2 for val in exit_ats["v"]]
                    profile.exit_ats = json.dumps(exit_ats)

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
if RACE.num_nodes == 0:
    print '*** WARNING: NO RECEIVER NODES FOUND ***'
else:
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
    server_log('** WARNING: Node API mismatch. **')

if serverInfo['node_api_lowest'] < NODE_API_SUPPORTED:
    server_log('** WARNING: Node firmware is out of date and may not function properly **')
elif serverInfo['node_api_lowest'] < NODE_API_BEST:
    server_log('** NOTICE: Node firmware update is available **')
elif serverInfo['node_api_lowest'] > NODE_API_BEST:
    server_log('** WARNING: Node firmware is newer than this server version supports **')

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

# internal slave race format for LiveTime (needs to be created after initial DB setup)
global SLAVE_RACE_FORMAT
SLAVE_RACE_FORMAT = RHRaceFormat(name=__("Slave"),
                         race_mode=1,
                         race_time_sec=0,
                         start_delay_min=0,
                         start_delay_max=0,
                         number_laps_win=0,
                         win_condition=WIN_CONDITION_NONE,
                         team_racing_mode=False)

# Import IMDTabler
if os.path.exists(IMDTABLER_JAR_NAME):  # if 'IMDTabler.jar' is available
    try:
        java_ver = subprocess.check_output('java -version', stderr=subprocess.STDOUT, shell=True)
        server_log('Found installed:  ' + java_ver.split('\n')[0])
    except:
        java_ver = None
        server_log('Unable to find java; for IMDTabler functionality try:')
        server_log('sudo apt-get install oracle-java8-jdk')
    if java_ver:
        try:
            imdtabler_ver = subprocess.check_output( \
                        'java -jar ' + IMDTABLER_JAR_NAME + ' -v', \
                        stderr=subprocess.STDOUT, shell=True).rstrip()
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

# Set current heat on startup
if Heat.query.first():
    RACE.current_heat = Heat.query.first().heat_id

# Create LED object with appropriate configuration.
try:
    pixelModule = importlib.import_module('rpi_ws281x')
    Pixel = getattr(pixelModule, 'Adafruit_NeoPixel')
    print 'LED: selecting library "rpi_ws2812x"'
except ImportError:
    pass

try:
    pixelModule = importlib.import_module('neopixel')
    Pixel = getattr(pixelModule, 'Adafruit_NeoPixel')
    print 'LED: selecting library "neopixel" (older)'
except ImportError:
    pass

if Pixel != None:
    Color = getattr(pixelModule, 'Color')
    led_strip_config = Config['LED']['LED_STRIP']
    if led_strip_config == 'RGB':
        led_strip = 0x00100800
    elif led_strip_config == 'RBG':
        led_strip = 0x00100008
    elif led_strip_config == 'GRB':
        led_strip = 0x00081000
    elif led_strip_config == 'GBR':
        led_strip = 0x00080010
    elif led_strip_config == 'BRG':
        led_strip = 0x00001008
    elif led_strip_config == 'BGR':
        led_strip = 0x00000810
    else:
        print 'LED: disabled (Invalid LED_STRIP value: {0})'.format(led_strip_config)
        Pixel = None
    print 'LED: hardware GPIO enabled'
else:
    try:
        pixelModule = importlib.import_module('ANSIPixel')
        Pixel = getattr(pixelModule, 'ANSIPixel')
        Color = getattr(pixelModule, 'Color')
        led_strip = None
        print 'LED: simulated via ANSIPixel (no physical LED support enabled)'
    except ImportError:
        strip = None
        Color = lambda r, g, b:None
        led_strip = None
        print 'LED: disabled (no modules available)'

if isLedEnabled():
    # note: any calls to 'getOption()' need to happen after the DB initialization,
    #       otherwise it causes problems when run with no existing DB file
    strip = Pixel(Config['LED']['LED_COUNT'], Config['LED']['LED_PIN'], Config['LED']['LED_FREQ_HZ'], Config['LED']['LED_DMA'], Config['LED']['LED_INVERT'], int(getOption("ledBrightness")), Config['LED']['LED_CHANNEL'], led_strip)
    # Intialize the library (must be called once before other functions).
    strip.begin()

def start(port_val = Config['GENERAL']['HTTP_PORT']):
    print "Running http server at port " + str(port_val)
    try:
        SOCKET_IO.run(APP, host='0.0.0.0', port=port_val, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        print "Server terminated by keyboard interrupt"
    except Exception as ex:
        print "Server exception:  " + str(ex)

# Start HTTP server
if __name__ == '__main__':
    start()
