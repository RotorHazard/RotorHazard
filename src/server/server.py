'''RotorHazard server script'''
RELEASE_VERSION = "2.3.0-dev.1" # Public release version code
SERVER_API = 27 # Server API version
NODE_API_SUPPORTED = 18 # Minimum supported node version
NODE_API_BEST = 25 # Most recent node API
JSON_API = 3 # JSON API version

# This must be the first import for the time being. It is
# necessary to set up logging *before* anything else
# because there is a lot of code run through imports, and
# we would miss messages otherwise.
import logging
import log
from datetime import datetime

log.early_stage_setup()
logger = logging.getLogger(__name__)

EPOCH_START = datetime(1970, 1, 1)
PROGRAM_START_TIMESTAMP = int((datetime.now() - EPOCH_START).total_seconds() / 1000)

logger.info('RotorHazard v{0}'.format(RELEASE_VERSION))
logger.debug('Program started at {0:13f}'.format(PROGRAM_START_TIMESTAMP))

# Normal importing resumes here
import gevent
import gevent.monkey
gevent.monkey.patch_all()
GEVENT_SUPPORT = True   # For Python Debugger

import io
import os
import sys
import traceback
import platform
import re
import shutil
import base64
import subprocess
import importlib
import socketio
from monotonic import monotonic
from functools import wraps
from collections import OrderedDict

from flask import Flask, render_template, send_file, request, Response, session
from flask_socketio import SocketIO, emit
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy import create_engine, MetaData, Table

import random
import json

import Config
import Options
import Database
import Results
import Language
import RHUtils
from Language import __

# Events manager
from eventmanager import Evt, EventManager

Events = EventManager()

# LED imports
from led_event_manager import LEDEventManager, NoLEDManager, LEDEvent, Color, ColorPattern, hexToColor

sys.path.append('../interface')
sys.path.append('/home/pi/RotorHazard/src/interface')  # Needed to run on startup

from Plugins import Plugins
from RHRace import get_race_state, WinCondition, RaceStatus

APP = Flask(__name__, static_url_path='/static')

HEARTBEAT_THREAD = None
HEARTBEAT_DATA_RATE_FACTOR = 5

ERROR_REPORT_INTERVAL_SECS = 600  # delay between comm-error reports to log
IS_SYS_RASPBERRY_PI = False       # may be set by 'idAndLogSystemInfo()'

FULL_RESULTS_CACHE = {} # Cache of complete results page
FULL_RESULTS_CACHE_BUILDING = False # Whether results are being calculated
FULL_RESULTS_CACHE_VALID = False # Whether cache is valid (False = regenerate cache)

DB_FILE_NAME = 'database.db'
DB_BKP_DIR_NAME = 'db_bkp'
IMDTABLER_JAR_NAME = 'static/IMDTabler.jar'

# command-line arguments:
CMDARG_VERSION_LONG_STR = '--version'  # show program version and exit
CMDARG_VERSION_SHORT_STR = '-v'        # show program version and exit
CMDARG_ZIP_LOGS_STR = '--ziplogs'      # create logs .zip file

if __name__ == '__main__' and len(sys.argv) > 1:
    if CMDARG_VERSION_LONG_STR in sys.argv or CMDARG_VERSION_SHORT_STR in sys.argv:
        sys.exit(0)
    if CMDARG_ZIP_LOGS_STR in sys.argv:
        log.create_log_files_zip(logger, Config.CONFIG_FILE_NAME, DB_FILE_NAME)
        sys.exit(0)
    print("Unrecognized command-line argument(s): {0}".format(sys.argv[1:]))

TEAM_NAMES_LIST = [str(unichr(i)) for i in range(65, 91)]  # list of 'A' to 'Z' strings
DEF_TEAM_NAME = 'A'  # default team

BASEDIR = os.getcwd()
APP.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASEDIR, DB_FILE_NAME)
APP.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
DB = Database.DB
DB.init_app(APP)
DB.app = APP

# start SocketIO service
SOCKET_IO = SocketIO(APP, async_mode='gevent', cors_allowed_origins=Config.GENERAL['CORS_ALLOWED_HOSTS'])

# this is the moment where we can forward log-messages to the frontend, and
# thus set up logging for good.
Current_log_path_name = log.later_stage_setup(Config.LOGGING, SOCKET_IO)

INTERFACE = None  # initialized later
CLUSTER = None    # initialized later
Use_imdtabler_jar_flag = False  # set True if IMDTabler.jar is available

RACE = get_race_state() # For storing race management variables

PROGRAM_START = monotonic()
PROGRAM_START_MILLIS_OFFSET = 1000.0*PROGRAM_START - PROGRAM_START_TIMESTAMP

TONES_NONE = 0
TONES_ONE = 1
TONES_ALL = 2

def monotonic_to_milliseconds(secs):
    return 1000.0*secs - PROGRAM_START_MILLIS_OFFSET

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
            logger.info("Slave {0}: connecting to {1}...".format(self.id+1, self.address))
            while monotonic() < startConnectTime + self.info['timeout']:
                try:
                    self.sio.connect(self.address)
                    logger.info("Slave {0}: connected to {1}".format(self.id+1, self.address))
                    return True
                except socketio.exceptions.ConnectionError:
                    gevent.sleep(0.1)
            logger.warn("Slave {0}: connection to {1} failed!".format(self.id+1, self.address))
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
        pilot_id = Database.HeatNode.query.filter_by( \
            heat_id=RACE.current_heat, node_index=node_index).one_or_none().pilot_id

        if pilot_id != Database.PILOT_ID_NONE:

            split_ts = data['timestamp'] + (PROGRAM_START_MILLIS_OFFSET - 1000.0*RACE.start_time_monotonic)

            lap_count = max(0, len(RACE.get_active_laps()[node_index]) - 1)

            if lap_count:
                last_lap_ts = RACE.get_active_laps()[node_index][-1]['lap_time_stamp']
            else: # first lap
                last_lap_ts = 0

            split_id = self.id
            last_split_id = DB.session.query(DB.func.max(Database.LapSplit.split_id)).filter_by(node_index=node_index, lap_id=lap_count).scalar()
            if last_split_id is None: # first split for this lap
                if split_id > 0:
                    logger.info('Ignoring missing splits before {0} for node {1}'.format(split_id+1, node_index+1))
                last_split_ts = last_lap_ts
            else:
                if split_id > last_split_id:
                    if split_id > last_split_id + 1:
                        logger.info('Ignoring missing splits between {0} and {1} for node {2}'.format(last_split_id+1, split_id+1, node_index+1))
                    last_split_ts = Database.LapSplit.query.filter_by(node_index=node_index, lap_id=lap_count, split_id=last_split_id).one().split_time_stamp
                else:
                    logger.info('Ignoring out-of-order split {0} for node {1}'.format(split_id+1, node_index+1))
                    last_split_ts = None

            if last_split_ts is not None:
                split_time = split_ts - last_split_ts
                split_speed = float(self.info['distance'])*1000.0/float(split_time) if 'distance' in self.info else None
                logger.info('Split pass record: Node: {0}, Lap: {1}, Split time: {2}, Split speed: {3}' \
                    .format(node_index+1, lap_count+1, RHUtils.time_format(split_time), \
                    ('{0:.2f}'.format(split_speed) if split_speed <> None else 'None')))

                DB.session.add(Database.LapSplit(node_index=node_index, pilot_id=pilot_id, lap_id=lap_count, split_id=split_id, \
                    split_time_stamp=split_ts, split_time=split_time, split_time_formatted=RHUtils.time_format(split_time), \
                    split_speed=split_speed))
                DB.session.commit()
                emit_current_laps() # update all laps on the race page
        else:
            logger.info('Split pass record dismissed: Node: {0}, Frequency not defined' \
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

def uniqueName(desiredName, otherNames):
    if desiredName in otherNames:
        newName = desiredName
        match = re.match('^(.*) ([0-9]*)$', desiredName)
        if match:
            nextInt = int(match.group(2))
            nextInt += 1
            newName = match.group(1) + ' ' + str(nextInt)
        else:
            newName = desiredName + " 2"
        newName = uniqueName(newName, otherNames)
        return newName
    else:
        return desiredName

def idAndLogSystemInfo():
    global IS_SYS_RASPBERRY_PI
    try:
        modelStr = None
        try:
            fileHnd = open("/proc/device-tree/model", "r")
            modelStr = fileHnd.read()
            fileHnd.close()
        except:
            pass
        if modelStr and "raspberry pi" in modelStr.lower():
            IS_SYS_RASPBERRY_PI = True
            logger.info("Host machine: " + modelStr.strip('\0'))
        logger.info("Host OS: {0} {1}".format(platform.system(), platform.release()))
    except Exception:
        logger.exception("Error in 'idAndLogSystemInfo()'")

# Checks if the given file is owned by 'root' and changes owner to 'pi' user if so.
# Returns True if file owner changed to 'pi' user; False if not.
def checkSetFileOwnerPi(fileNameStr):
    try:
        if IS_SYS_RASPBERRY_PI:
            # check that 'pi' user exists, file exists, and file owner is 'root'
            if os.path.isdir("/home/pi") and os.path.isfile(fileNameStr) and os.stat(fileNameStr).st_uid == 0:
                subprocess.check_call(["sudo", "chown", "pi:pi", fileNameStr])
                if os.stat(fileNameStr).st_uid != 0:
                    return True
                logger.info("Unable to change owner in 'checkSetFileOwnerPi()', file: " + fileNameStr)
    except Exception:
        logger.exception("Error in 'checkSetFileOwnerPi()'")
    return False

def getCurrentProfile():
    current_profile = int(Options.get('currentProfile'))
    return Database.Profiles.query.get(current_profile)

def getCurrentRaceFormat():
    if RACE.format is None:
        val = int(Options.get('currentFormat'))
        race_format = Database.RaceFormat.query.get(val)
        # create a shared instance
        RACE.format = RHRaceFormat.copy(race_format)
        RACE.format.id = race_format.id
    return RACE.format

def getCurrentDbRaceFormat():
    if RACE.format is None or RHRaceFormat.isDbBased(RACE.format):
        val = int(Options.get('currentFormat'))
        return Database.RaceFormat.query.get(val)
    else:
        return None

def setCurrentRaceFormat(race_format):
    if RHRaceFormat.isDbBased(race_format): # stored in DB, not internal race format
        Options.set('currentFormat', race_format.id)
        # create a shared instance
        RACE.format = RHRaceFormat.copy(race_format)
        RACE.format.id = race_format.id
    else:
        RACE.format = race_format

class RHRaceFormat():
    def __init__(self, name, race_mode, race_time_sec, start_delay_min, start_delay_max, staging_tones, number_laps_win, win_condition, team_racing_mode):
        self.name = name
        self.race_mode = race_mode
        self.race_time_sec = race_time_sec
        self.start_delay_min = start_delay_min
        self.start_delay_max = start_delay_max
        self.staging_tones = staging_tones
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
                            staging_tones=race_format.staging_tones,
                            number_laps_win=race_format.number_laps_win,
                            win_condition=race_format.win_condition,
                            team_racing_mode=race_format.team_racing_mode)

    @classmethod
    def isDbBased(cls, race_format):
        return hasattr(race_format, 'id')

#
# Authentication
#

def check_auth(username, password):
    '''Check if a username password combination is valid.'''
    return username == Config.GENERAL['ADMIN_USERNAME'] and password == Config.GENERAL['ADMIN_PASSWORD']

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
    return render_template('home.html', serverInfo=serverInfo,
                           getOption=Options.get, __=__, Debug=Config.GENERAL['DEBUG'])

@APP.route('/heats')
def heats():
    '''Route to heat summary page.'''
    return render_template('heats.html', serverInfo=serverInfo, getOption=Options.get, __=__)

@APP.route('/results')
def results():
    '''Route to round summary page.'''
    return render_template('rounds.html', serverInfo=serverInfo, getOption=Options.get, __=__)

@APP.route('/race')
@requires_auth
def race():
    '''Route to race management page.'''
    frequencies = [node.frequency for node in INTERFACE.nodes]
    nodes = []
    for idx, freq in enumerate(frequencies):
        if freq:
            nodes.append({
                'freq': freq,
                'index': idx
            })

    return render_template('race.html', serverInfo=serverInfo, getOption=Options.get, __=__,
        led_enabled=led_manager.isEnabled(),
        vrx_enabled=vrx_controller!=None,
        num_nodes=RACE.num_nodes,
        current_heat=RACE.current_heat, pilots=Database.Pilot,
        nodes=nodes)

@APP.route('/current')
def racepublic():
    '''Route to race management page.'''
    frequencies = [node.frequency for node in INTERFACE.nodes]
    nodes = []
    for idx, freq in enumerate(frequencies):
        if freq:
            nodes.append({
                'freq': freq,
                'index': idx
            })

    return render_template('racepublic.html', serverInfo=serverInfo, getOption=Options.get, __=__,
        num_nodes=RACE.num_nodes,
        nodes=nodes)

@APP.route('/marshal')
@requires_auth
def marshal():
    '''Route to race management page.'''
    return render_template('marshal.html', serverInfo=serverInfo, getOption=Options.get, __=__,
        num_nodes=RACE.num_nodes)

@APP.route('/settings')
@requires_auth
def settings():
    '''Route to settings page.'''
    return render_template('settings.html', serverInfo=serverInfo, getOption=Options.get, __=__,
        led_enabled=led_manager.isEnabled(),
        vrx_enabled=vrx_controller!=None,
        num_nodes=RACE.num_nodes,
        ConfigFile=Config.GENERAL['configFile'],
        Debug=Config.GENERAL['DEBUG'])

@APP.route('/streams')
def stream():
    '''Route to stream index.'''
    return render_template('streams.html', serverInfo=serverInfo, getOption=Options.get, __=__,
        num_nodes=RACE.num_nodes)

@APP.route('/stream/results')
def stream_results():
    '''Route to current race leaderboard stream.'''
    return render_template('streamresults.html', serverInfo=serverInfo, getOption=Options.get, __=__,
        num_nodes=RACE.num_nodes)

@APP.route('/stream/node/<int:node_id>')
def stream_node(node_id):
    '''Route to single node overlay for streaming.'''
    if node_id <= RACE.num_nodes:
        return render_template('streamnode.html', serverInfo=serverInfo, getOption=Options.get, __=__,
            node_id=node_id-1
        )
    else:
        return False

@APP.route('/stream/class/<int:class_id>')
def stream_class(class_id):
    '''Route to class leaderboard display for streaming.'''
    return render_template('streamclass.html', serverInfo=serverInfo, getOption=Options.get, __=__,
        class_id=class_id
    )

@APP.route('/stream/heat/<int:heat_id>')
def stream_heat(heat_id):
    '''Route to heat display for streaming.'''
    return render_template('streamheat.html', serverInfo=serverInfo, getOption=Options.get, __=__,
        num_nodes=RACE.num_nodes,
        heat_id=heat_id
    )

@APP.route('/scanner')
@requires_auth
def scanner():
    '''Route to scanner page.'''

    return render_template('scanner.html', serverInfo=serverInfo, getOption=Options.get, __=__,
        num_nodes=RACE.num_nodes)

@APP.route('/decoder')
@requires_auth
def decoder():
    '''Route to race management page.'''
    return render_template('decoder.html', serverInfo=serverInfo, getOption=Options.get, __=__,
        num_nodes=RACE.num_nodes)

@APP.route('/imdtabler')
def imdtabler():
    '''Route to IMDTabler page.'''

    return render_template('imdtabler.html', serverInfo=serverInfo, getOption=Options.get, __=__)

# Debug Routes

@APP.route('/hardwarelog')
@requires_auth
def hardwarelog():
    '''Route to hardware log page.'''
    return render_template('hardwarelog.html', serverInfo=serverInfo, getOption=Options.get, __=__)

@APP.route('/database')
@requires_auth
def database():
    '''Route to database page.'''
    return render_template('database.html', serverInfo=serverInfo, getOption=Options.get, __=__,
        pilots=Database.Pilot,
        heats=Database.Heat,
        heatnodes=Database.HeatNode,
        race_class=Database.RaceClass,
        savedraceMeta=Database.SavedRaceMeta,
        savedraceLap=Database.SavedRaceLap,
        profiles=Database.Profiles,
        race_format=Database.RaceFormat,
        globalSettings=Database.GlobalSettings)

@APP.route('/vrxstatus')
@requires_auth
def vrxstatus():
    '''Route to database page.'''
    if vrx_controller:
        return render_template('vrxstatus.html', serverInfo=serverInfo, getOption=Options.get, __=__,
            vrxstatus=vrx_controller.rx_data)
    else:
        return False

@APP.route('/docs')
def viewDocs():
    '''Route to doc viewer.'''
    docfile = request.args.get('d')

    language = Options.get("currentLanguage")
    if language:
        translation = language + '-' + docfile
        if os.path.isfile('../../doc/' + translation):
            docfile = translation

    with io.open('../../doc/' + docfile, 'r', encoding="utf-8") as f:
        doc = f.read()

    return render_template('viewdocs.html',
        serverInfo=serverInfo,
        getOption=Options.get,
        __=__,
        doc=doc
        )

@APP.route('/img/<path:imgfile>')
def viewImg(imgfile):
    '''Route to img called within doc viewer.'''
    return send_file('../../doc/img/' + imgfile)

# JSON API

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
    pilots = Database.Pilot.query.all()
    payload = []
    for pilot in pilots:
        payload.append(pilot)

    return json.dumps({"pilots": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/pilot/<int:pilot_id>')
def api_pilot(pilot_id):
    pilot = Database.Pilot.query.get(pilot_id)

    return json.dumps({"pilot": pilot}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/heat/all')
def api_heat_all():
    all_heats = {}
    for heat in Database.Heat.query.all():
        heat_id = heat.id
        note = heat.note
        race_class = heat.class_id

        heatnodes = Database.HeatNode.query.filter_by(heat_id=heat.id).all()
        pilots = {}
        for pilot in heatnodes:
            pilots[pilot.node_index] = pilot.pilot_id

        has_race = Database.SavedRaceMeta.query.filter_by(heat_id=heat.id).first()

        if has_race:
            locked = True
        else:
            locked = False

        all_heats[heat_id] = {
            'note': note,
            'heat_id': heat_id,
            'class_id': race_class,
            'nodes_pilots': pilots,
            'locked': locked
        }

    return json.dumps({"heats": all_heats}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/heat/<int:heat_id>')
def api_heat(heat_id):
    heat = Database.Heat.query.get(heat_id)
    if heat:
        note = heat.note
        race_class = heat.class_id

        heatnodes = Database.HeatNode.query.filter_by(heat_id=heat.id).all()
        pilots = {}
        for pilot in heatnodes:
            pilots[pilot.node_index] = pilot.pilot_id

        has_race = Database.SavedRaceMeta.query.filter_by(heat_id=heat.id).first()

        if has_race:
            locked = True
        else:
            locked = False

        heat = {
            'note': note,
            'heat_id': heat_id,
            'class_id': race_class,
            'nodes_pilots': pilots,
            'locked': locked
        }
    else:
        heat = None

    payload = {
        'setup': heat,
        'leaderboard': Results.calc_leaderboard(DB, heat_id=heat_id)
    }

    return json.dumps({"heat": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/class/all')
def api_class_all():
    race_classes = Database.RaceClass.query.all()
    payload = []
    for race_class in race_classes:
        payload.append(race_class)

    return json.dumps({"classes": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/class/<int:class_id>')
def api_class(class_id):
    race_class = Database.RaceClass.query.get(class_id)

    return json.dumps({"class": race_class}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/format/all')
def api_format_all():
    formats = Database.RaceFormat.query.all()
    payload = []
    for race_format in formats:
        payload.append(race_format)

    return json.dumps({"formats": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/format/<int:format_id>')
def api_format(format_id):
    raceformat = Database.RaceFormat.query.get(format_id)

    return json.dumps({"format": raceformat}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/profile/all')
def api_profile_all():
    profiles = Database.Profiles.query.all()
    payload = []
    for profile in profiles:
        payload.append(profile)

    return json.dumps({"profiles": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/profile/<int:profile_id>')
def api_profile(profile_id):
    profile = Database.Profiles.query.get(profile_id)

    return json.dumps({"profile": profile}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/race/current')
def api_race_current():
    global RACE
    if RACE.cacheStatus == Results.CacheStatus.VALID:
        results = RACE.results
    else:
        results = Results.calc_leaderboard(DB, current_race=RACE, current_profile=getCurrentProfile())
        RACE.results = results
        RACE.cacheStatus = Results.CacheStatus.VALID

    payload = {
        "raw_laps": RACE.node_laps,
        "leaderboard": results
    }

    return json.dumps({"race": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/race/all')
def api_race_all():
    heats = []
    for heat in Database.SavedRaceMeta.query.with_entities(Database.SavedRaceMeta.heat_id).distinct().order_by(Database.SavedRaceMeta.heat_id):
        max_rounds = DB.session.query(DB.func.max(Database.SavedRaceMeta.round_id)).filter_by(heat_id=heat.heat_id).scalar()
        heats.append({
            "id": heat.heat_id,
            "rounds": max_rounds
        })

    payload = {
        "heats": heats,
        "leaderboard": Results.calc_leaderboard(DB)
    }

    return json.dumps({"races": payload}, cls=AlchemyEncoder), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/race/<int:heat_id>/<int:round_id>')
def api_race(heat_id, round_id):
    race = Database.SavedRaceMeta.query.filter_by(heat_id=heat_id, round_id=round_id).one()

    pilotraces = []
    for pilotrace in Database.SavedPilotRace.query.filter_by(race_id=race.id).all():
        laps = []
        for lap in Database.SavedRaceLap.query.filter_by(pilotrace_id=pilotrace.id).all():
            laps.append({
                    'id': lap.id,
                    'lap_time_stamp': lap.lap_time_stamp,
                    'lap_time': lap.lap_time,
                    'lap_time_formatted': lap.lap_time_formatted,
                    'source': lap.source,
                    'deleted': lap.deleted
                })

        pilot_data = Database.Pilot.query.filter_by(id=pilotrace.pilot_id).first()
        if pilot_data:
            nodepilot = pilot_data.callsign
        else:
            nodepilot = None

        if Options.get('pilotSort') == 'callsign':
            pilot_data.sort(key=lambda x: (x['callsign'], x['name']))
        else:
            pilot_data.sort(key=lambda x: (x['name'], x['callsign']))

        pilotraces.append({
            'callsign': nodepilot,
            'pilot_id': pilotrace.pilot_id,
            'node_index': pilotrace.node_index,
            'laps': laps
        })
    payload = {
        'start_time_formatted': race.start_time_formatted,
        'nodes': pilotraces,
        'sort': Options.get('pilotSort'),
        'leaderboard': Results.calc_leaderboard(DB, heat_id=heat_id, round_id=round_id)
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
            "currentProfile": Options.get('currentProfile'),
            "currentFormat": Options.get('currentFormat'),
        }
    }

    return json.dumps({"status": data}), 201, {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

@APP.route('/api/options')
def api_options():
    opt_query = Database.GlobalSettings.query.all()
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
    logger.debug('Client connected')
    INTERFACE.start()
    global HEARTBEAT_THREAD
    if HEARTBEAT_THREAD is None:
        HEARTBEAT_THREAD = gevent.spawn(heartbeat_thread_function)
        logger.debug('Heartbeat thread started')
    emit_heat_data(nobroadcast=True)

@SOCKET_IO.on('disconnect')
def disconnect_handler():
    '''Emit disconnect event.'''
    logger.debug('Client disconnected')

# LiveTime compatible events

@SOCKET_IO.on('get_version')
def on_get_version():
    session['LiveTime'] = True
    ver_parts = RELEASE_VERSION.split('.')
    return {'major': ver_parts[0], 'minor': ver_parts[1]}

@SOCKET_IO.on('get_timestamp')
def on_get_timestamp():
    if RACE.race_status == RaceStatus.STAGING:
        now = RACE.start_time_monotonic
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
    Options.set("MinLapSec", "0")
    Options.set("MinLapBehavior", "0")
    on_stage_race()

# Cluster events

@SOCKET_IO.on('join_cluster')
def on_join_cluster():
    setCurrentRaceFormat(SLAVE_RACE_FORMAT)
    emit_race_format()
    Options.set("MinLapSec", "0")
    Options.set("MinLapBehavior", "0")
    logger.debug('Joined cluster')

    Events.trigger(Evt.CLUSTER_JOIN)

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
        elif load_type == 'race_formats':
            emit_race_formats(nobroadcast=True)
        elif load_type == 'node_tuning':
            emit_node_tuning(nobroadcast=True)
        elif load_type == 'enter_and_exit_at_levels':
            emit_enter_and_exit_at_levels(nobroadcast=True)
        elif load_type == 'min_lap':
            emit_min_lap(nobroadcast=True)
        elif load_type == 'leaderboard':
            emit_current_leaderboard(nobroadcast=True)
        elif load_type == 'leaderboard_cache':
            emit_current_leaderboard(nobroadcast=True, use_cache=True)
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
        elif load_type == 'led_effect_setup':
            emit_led_effect_setup()
        elif load_type == 'led_effects':
            emit_led_effects()
        elif load_type == 'callouts':
            emit_callouts()
        elif load_type == 'imdtabler_page':
            emit_imdtabler_page(nobroadcast=True)
        elif load_type == 'vrx_list':
            emit_vrx_list(nobroadcast=True)
        elif load_type == 'cluster_status':
            CLUSTER.emitStatus()
        elif load_type == 'hardware_log_init':
            emit_current_log_file_to_socket()

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

    profile = getCurrentProfile()
    freqs = json.loads(profile.frequencies)
    freqs["f"][node_index] = frequency
    profile.frequencies = json.dumps(freqs)

    DB.session.commit()

    logger.info('Frequency set: Node {0} Frequency {1}'.format(node_index+1, frequency))
    INTERFACE.set_frequency(node_index, frequency)

    Events.trigger(Evt.FREQUENCY_SET, {
        'nodeIndex': node_index,
        'frequency': frequency,
        })

    emit_frequency_data()

@SOCKET_IO.on('set_frequency_preset')
def on_set_frequency_preset(data):
    ''' Apply preset frequencies '''
    CLUSTER.emit('set_frequency_preset', data)
    freqs = []
    if data['preset'] == 'All-N1':
        profile = getCurrentProfile()
        profile_freqs = json.loads(profile.frequencies)
        frequency = profile_freqs["f"][0]
        for idx in range(RACE.num_nodes):
            freqs.append(frequency)
    else:
        if data['preset'] == 'RB-4':
            freqs = [5658, 5732, 5843, 5880, RHUtils.FREQUENCY_ID_NONE, RHUtils.FREQUENCY_ID_NONE, RHUtils.FREQUENCY_ID_NONE, RHUtils.FREQUENCY_ID_NONE]
        elif data['preset'] == 'RB-8':
            freqs = [5658, 5695, 5732, 5769, 5806, 5843, 5880, 5917]
        elif data['preset'] == 'IMD5C':
            freqs = [5658, 5695, 5760, 5800, 5885, RHUtils.FREQUENCY_ID_NONE, RHUtils.FREQUENCY_ID_NONE, RHUtils.FREQUENCY_ID_NONE]
        else: #IMD6C is default
            freqs = [5658, 5695, 5760, 5800, 5880, 5917, RHUtils.FREQUENCY_ID_NONE, RHUtils.FREQUENCY_ID_NONE]

    set_all_frequencies(freqs)
    emit_frequency_data()
    hardware_set_all_frequencies(freqs)

def set_all_frequencies(freqs):
    ''' Set frequencies for all nodes (but do not update hardware) '''
    # Set DB
    profile = getCurrentProfile()
    profile_freqs = json.loads(profile.frequencies)

    for idx in range(RACE.num_nodes):
        profile_freqs["f"][idx] = freqs[idx]
        logger.info('Frequency set: Node {0} Frequency {1}'.format(idx+1, freqs[idx]))

    profile.frequencies = json.dumps(profile_freqs)
    DB.session.commit()

def hardware_set_all_frequencies(freqs):
    '''do hardware update for frequencies'''
    for idx in range(RACE.num_nodes):
        INTERFACE.set_frequency(idx, freqs[idx])

        Events.trigger(Evt.FREQUENCY_SET, {
            'nodeIndex': idx,
            'frequency': freqs[idx],
            })

def restore_node_frequency(node_index):
    ''' Restore frequency for given node index (update hardware) '''
    gevent.sleep(0.250)  # pause to get clear of heartbeat actions for scanner
    profile = getCurrentProfile()
    profile_freqs = json.loads(profile.frequencies)
    freq = profile_freqs["f"][node_index]
    INTERFACE.set_frequency(node_index, freq)
    logger.info('Frequency restored: Node {0} Frequency {1}'.format(node_index+1, freq))

@SOCKET_IO.on('set_enter_at_level')
def on_set_enter_at_level(data):
    '''Set node enter-at level.'''
    node_index = data['node']
    enter_at_level = data['enter_at_level']

    if not enter_at_level:
        logger.info('Node enter-at set null; getting from node: Node {0}'.format(node_index+1))
        enter_at_level = INTERFACE.nodes[node_index].enter_at_level

    profile = getCurrentProfile()
    enter_ats = json.loads(profile.enter_ats)
    enter_ats["v"][node_index] = enter_at_level
    profile.enter_ats = json.dumps(enter_ats)
    DB.session.commit()

    INTERFACE.set_enter_at_level(node_index, enter_at_level)

    Events.trigger(Evt.ENTER_AT_LEVEL_SET, {
        'nodeIndex': node_index,
        'enter_at_level': enter_at_level,
        })

    logger.info('Node enter-at set: Node {0} Level {1}'.format(node_index+1, enter_at_level))

@SOCKET_IO.on('set_exit_at_level')
def on_set_exit_at_level(data):
    '''Set node exit-at level.'''
    node_index = data['node']
    exit_at_level = data['exit_at_level']

    if not exit_at_level:
        logger.info('Node exit-at set null; getting from node: Node {0}'.format(node_index+1))
        exit_at_level = INTERFACE.nodes[node_index].exit_at_level

    profile = getCurrentProfile()
    exit_ats = json.loads(profile.exit_ats)
    exit_ats["v"][node_index] = exit_at_level
    profile.exit_ats = json.dumps(exit_ats)
    DB.session.commit()

    INTERFACE.set_exit_at_level(node_index, exit_at_level)

    Events.trigger(Evt.EXIT_AT_LEVEL_SET, {
        'nodeIndex': node_index,
        'exit_at_level': exit_at_level,
        })

    logger.info('Node exit-at set: Node {0} Level {1}'.format(node_index+1, exit_at_level))

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
    Options.set('currentLanguage', data['language'])
    DB.session.commit()

@SOCKET_IO.on('cap_enter_at_btn')
def on_cap_enter_at_btn(data):
    '''Capture enter-at level.'''
    node_index = data['node_index']
    if INTERFACE.start_capture_enter_at_level(node_index):
        logger.info('Starting capture of enter-at level for node {0}'.format(node_index+1))

@SOCKET_IO.on('cap_exit_at_btn')
def on_cap_exit_at_btn(data):
    '''Capture exit-at level.'''
    node_index = data['node_index']
    if INTERFACE.start_capture_exit_at_level(node_index):
        logger.info('Starting capture of exit-at level for node {0}'.format(node_index+1))

@SOCKET_IO.on('set_scan')
def on_set_scan(data):
    node_index = data['node']
    minScanFreq = data['min_scan_frequency']
    maxScanFreq = data['max_scan_frequency']
    maxScanInterval = data['max_scan_interval']
    minScanInterval = data['min_scan_interval']
    scanZoom = data['scan_zoom']
    node = INTERFACE.nodes[node_index]
    node.set_scan_interval(minScanFreq, maxScanFreq, maxScanInterval, minScanInterval, scanZoom)
    if node.scan_enabled:
        HEARTBEAT_DATA_RATE_FACTOR = 50
    else:
        HEARTBEAT_DATA_RATE_FACTOR = 5
        gevent.sleep(0.100)  # pause/spawn to get clear of heartbeat actions for scanner
        gevent.spawn(restore_node_frequency(node_index))

@SOCKET_IO.on('add_heat')
def on_add_heat():
    '''Adds the next available heat number to the database.'''
    new_heat = Database.Heat(class_id=Database.CLASS_ID_NONE, cacheStatus=Results.CacheStatus.INVALID)
    DB.session.add(new_heat)
    DB.session.flush()
    DB.session.refresh(new_heat)

    for node in range(RACE.num_nodes): # Add next heat with empty pilots
        DB.session.add(Database.HeatNode(heat_id=new_heat.id, node_index=node, pilot_id=Database.PILOT_ID_NONE))

    DB.session.commit()

    Events.trigger(Evt.HEAT_DUPLICATE, {
        'heat_id': new_heat.id,
        })

    logger.info('Heat added: Heat {0}'.format(new_heat.id))
    emit_heat_data()

@SOCKET_IO.on('duplicate_heat')
def on_duplicate_heat(data):
    new_heat_id = duplicate_heat(data['heat'])
    DB.session.commit()

    Events.trigger(Evt.HEAT_DUPLICATE, {
        'heat_id': new_heat_id,
        })

    logger.info('Heat {0} duplicated to heat {1}'.format(data['heat'], new_heat_id))

    emit_heat_data()

def duplicate_heat(source, **kwargs):
    '''Adds new heat by duplicating an existing one.'''
    source_heat = Database.Heat.query.get(source)

    if source_heat.note:
        all_heat_notes = [heat.note for heat in Database.Heat.query.all()]
        new_heat_note = uniqueName(source_heat.note, all_heat_notes)
    else:
        new_heat_note = ''

    if 'dest_class' in kwargs:
        new_class = kwargs['dest_class']
    else:
        new_class = source_heat.class_id

    new_heat = Database.Heat(note=new_heat_note,
        class_id=new_class,
        results=None,
        cacheStatus=Results.CacheStatus.INVALID)

    DB.session.add(new_heat)
    DB.session.flush()
    DB.session.refresh(new_heat)

    for source_heatnode in Database.HeatNode.query.filter_by(heat_id=source_heat.id).all():
        new_heatnode = Database.HeatNode(heat_id=new_heat.id,
            node_index=source_heatnode.node_index,
            pilot_id=source_heatnode.pilot_id)
        DB.session.add(new_heatnode)

    return new_heat.id

@SOCKET_IO.on('alter_heat')
def on_alter_heat(data):
    '''Update heat.'''
    heat_id = data['heat']
    heat = Database.Heat.query.get(heat_id)

    if 'note' in data:
        global FULL_RESULTS_CACHE_VALID
        FULL_RESULTS_CACHE_VALID = False
        heat.note = data['note']
    if 'class' in data:
        heat.class_id = data['class']
    if 'pilot' in data:
        node_index = data['node']
        heatnode = Database.HeatNode.query.filter_by(heat_id=heat.id, node_index=node_index).one()
        heatnode.pilot_id = data['pilot']

    DB.session.commit()

    if heat_id == RACE.current_heat:
        RACE.node_pilots = {}
        RACE.node_teams = {}
        for heatNode in Database.HeatNode.query.filter_by(heat_id=heat_id):
            RACE.node_pilots[heatNode.node_index] = heatNode.pilot_id

            if heatNode.pilot_id is not Database.PILOT_ID_NONE:
                RACE.node_teams[heatNode.node_index] = Database.Pilot.query.get(heatNode.pilot_id).team
            else:
                RACE.node_teams[heatNode.node_index] = None
        RACE.cacheStatus = Results.CacheStatus.INVALID  # refresh leaderboard

    Events.trigger(Evt.HEAT_ALTER, {
        'heat_id': heat_id,
        })

    logger.info('Heat {0} altered with {1}'.format(heat_id, data))
    emit_heat_data(noself=True)
    if 'note' in data:
        emit_round_data_notify() # live update rounds page

@SOCKET_IO.on('delete_heat')
def on_delete_heat(data):
    '''Delete heat.'''
    if (DB.session.query(Database.Heat).count() > 1): # keep one profile
        heat_id = data['heat']
        heat = Database.Heat.query.get(heat_id)
        heatnodes = Database.HeatNode.query.filter_by(heat_id=heat.id).all()

        has_race = Database.SavedRaceMeta.query.filter_by(heat_id=heat.id).first()

        if has_race or (RACE.current_heat == heat.id and RACE.race_status != RaceStatus.READY):
            logger.info('Refusing to delete heat {0}: is in use'.format(heat.id))
        else:
            DB.session.delete(heat)
            for heatnode in heatnodes:
                DB.session.delete(heatnode)
            DB.session.commit()

            logger.info('Heat {0} deleted'.format(heat.id))

            Events.trigger(Evt.HEAT_DELETE, {
                'heat_id': heat_id,
                })

            emit_heat_data()
            if RACE.current_heat == heat.id:
                RACE.current_heat = Database.Heat.query.first().id
                emit_current_heat()

    else:
        logger.info('Refusing to delete only heat')

@SOCKET_IO.on('add_race_class')
def on_add_race_class():
    '''Adds the next available pilot id number in the database.'''
    new_race_class = Database.RaceClass(name='New class', format_id=0, cacheStatus=Results.CacheStatus.INVALID)
    DB.session.add(new_race_class)
    DB.session.flush()
    DB.session.refresh(new_race_class)
    new_race_class.name = ''
    new_race_class.description = ''
    DB.session.commit()

    Events.trigger(Evt.CLASS_ADD, {
        'class_id': new_race_class.id,
        })

    logger.info('Class added: Class {0}'.format(new_race_class))
    emit_class_data()
    emit_heat_data() # Update class selections in heat displays

@SOCKET_IO.on('duplicate_race_class')
def on_duplicate_race_class(data):
    '''Adds new race class by duplicating an existing one.'''
    source_class_id = data['class']
    source_class = Database.RaceClass.query.get(source_class_id)

    if source_class.name:
        all_class_names = [race_class.name for race_class in Database.RaceClass.query.all()]
        new_class_name = uniqueName(source_class.name, all_class_names)
    else:
        new_class_name = ''

    new_class = Database.RaceClass(name=new_class_name,
        description=source_class.description,
        format_id=source_class.format_id,
        results=None,
        cacheStatus=Results.CacheStatus.INVALID)

    DB.session.add(new_class)
    DB.session.flush()
    DB.session.refresh(new_class)

    for heat in Database.Heat.query.filter_by(class_id=source_class.id).all():
        duplicate_heat(heat.id, dest_class=new_class.id)

    DB.session.commit()

    Events.trigger(Evt.CLASS_DUPLICATE, {
        'class_id': new_class.id,
        })

    logger.info('Class {0} duplicated to class {1}'.format(source_class.id, new_class.id))
    emit_class_data()
    emit_heat_data()

@SOCKET_IO.on('alter_race_class')
def on_alter_race_class(data):
    '''Update race class.'''
    race_class = data['class_id']
    db_update = Database.RaceClass.query.get(race_class)
    if 'class_name' in data:
        global FULL_RESULTS_CACHE_VALID
        FULL_RESULTS_CACHE_VALID = False
        db_update.name = data['class_name']
    if 'class_format' in data:
        db_update.format_id = data['class_format']
    if 'class_description' in data:
        db_update.description = data['class_description']
    DB.session.commit()

    Events.trigger(Evt.CLASS_ALTER, {
        'class_id': race_class,
        })

    logger.info('Altered race class {0} to {1}'.format(race_class, data))
    emit_class_data(noself=True)
    if 'class_name' in data:
        emit_heat_data() # Update class names in heat displays
        emit_round_data_notify() # live update rounds page
    if 'class_format' in data:
        emit_current_heat(noself=True) # in case race operator is a different client, update locked format dropdown

@SOCKET_IO.on('delete_class')
def on_delete_class(data):
    '''Delete class.'''
    class_id = data['class']
    race_class = Database.RaceClass.query.get(class_id)

    has_race = Database.SavedRaceMeta.query.filter_by(class_id=race_class.id).first()

    if has_race:
        logger.info('Refusing to delete class {0}: is in use'.format(race_class.id))
    else:
        DB.session.delete(race_class)
        for heat in Database.Heat.query.all():
            if heat.class_id == race_class.id:
                heat.class_id = Database.CLASS_ID_NONE

        DB.session.commit()

        logger.info('Class {0} deleted'.format(race_class.id))
        emit_class_data()
        emit_heat_data()

@SOCKET_IO.on('add_pilot')
def on_add_pilot():
    '''Adds the next available pilot id number in the database.'''
    new_pilot = Database.Pilot(name='New Pilot',
                           callsign='New Callsign',
                           team=DEF_TEAM_NAME,
                           phonetic = '')
    DB.session.add(new_pilot)
    DB.session.flush()
    DB.session.refresh(new_pilot)
    new_pilot.name = __('~Pilot %d Name') % (new_pilot.id)
    new_pilot.callsign = __('~Callsign %d') % (new_pilot.id)
    new_pilot.team = DEF_TEAM_NAME
    new_pilot.phonetic = ''
    DB.session.commit()

    Events.trigger(Evt.PILOT_ADD, {
        'pilot_id': new_pilot.id,
        })

    logger.info('Pilot added: Pilot {0}'.format(new_pilot.id))
    emit_pilot_data()

@SOCKET_IO.on('alter_pilot')
def on_alter_pilot(data):
    '''Update pilot.'''
    global FULL_RESULTS_CACHE_VALID
    pilot_id = data['pilot_id']
    db_update = Database.Pilot.query.get(pilot_id)
    if 'callsign' in data:
        db_update.callsign = data['callsign']
    if 'team_name' in data:
        db_update.team = data['team_name']
    if 'phonetic' in data:
        db_update.phonetic = data['phonetic']
    if 'name' in data:
        db_update.name = data['name']

    DB.session.commit()

    Events.trigger(Evt.PILOT_ALTER, {
        'pilot_id': pilot_id,
        })

    logger.info('Altered pilot {0} to {1}'.format(pilot_id, data))
    emit_pilot_data(noself=True) # Settings page, new pilot settings
    if 'callsign' in data:
        Results.invalidate_all_caches(DB) # wipe caches (all have stored pilot names)
        emit_round_data_notify() # live update rounds page
        emit_heat_data() # Settings page, new pilot callsign in heats
    if 'phonetic' in data:
        emit_heat_data() # Settings page, new pilot phonetic in heats. Needed?

@SOCKET_IO.on('delete_pilot')
def on_delete_pilot(data):
    '''Delete heat.'''
    pilot_id = data['pilot']
    pilot = Database.Pilot.query.get(pilot_id)

    has_race = Database.SavedPilotRace.query.filter_by(pilot_id=pilot.id).first()

    if has_race:
        logger.info('Refusing to delete pilot {0}: is in use'.format(pilot.id))
    else:
        DB.session.delete(pilot)
        for heatNode in Database.HeatNode.query.all():
            if heatNode.pilot_id == pilot.id:
                heatNode.pilot_id = Database.PILOT_ID_NONE
        DB.session.commit()

        logger.info('Pilot {0} deleted'.format(pilot.id))
        emit_pilot_data()
        emit_heat_data()

@SOCKET_IO.on('add_profile')
def on_add_profile():
    '''Adds new profile (frequency set) in the database.'''
    profile = getCurrentProfile()
    new_freqs = {}
    new_freqs["f"] = default_frequencies()

    new_profile = Database.Profiles(name=__('New Profile'),
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

    Events.trigger(Evt.PROFILE_ADD, {
        'profile_id': new_profile.id,
        })

    on_set_profile(data={ 'profile': new_profile.id })

@SOCKET_IO.on('alter_profile')
def on_alter_profile(data):
    ''' update profile '''
    profile = getCurrentProfile()
    if 'profile_name' in data:
        profile.name = data['profile_name']
    if 'profile_description' in data:
        profile.description = data['profile_description']
    DB.session.commit()

    Events.trigger(Evt.PROFILE_ALTER, {
        'profile_id': profile.id,
        })

    logger.info('Altered current profile to %s' % (data))
    emit_node_tuning(noself=True)

@SOCKET_IO.on('delete_profile')
def on_delete_profile():
    '''Delete profile'''
    if (DB.session.query(Database.Profiles).count() > 1): # keep one profile
        profile = getCurrentProfile()
        profile_id = profile.id
        DB.session.delete(profile)
        DB.session.commit()
        first_profile_id = Database.Profiles.query.first().id

        Events.trigger(Evt.PROFILE_DELETE, {
            'profile_id': profile_id,
            })

        Options.set("currentProfile", first_profile_id)
        on_set_profile(data={ 'profile': first_profile_id })
    else:
        logger.info('Refusing to delete only profile')

@SOCKET_IO.on("set_profile")
def on_set_profile(data, emit_vals=True):
    ''' set current profile '''
    CLUSTER.emit('set_profile', data)
    profile_val = int(data['profile'])
    profile = Database.Profiles.query.get(profile_val)
    if profile:
        Options.set("currentProfile", data['profile'])
        logger.info("Set Profile to '%s'" % profile_val)
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

        Events.trigger(Evt.PROFILE_SET, {
            'profile_id': profile_val,
            })

        if emit_vals:
            emit_node_tuning()
            emit_enter_and_exit_at_levels()
            emit_frequency_data()

        hardware_set_all_frequencies(freqs)
        hardware_set_all_enter_ats(enter_ats)
        hardware_set_all_exit_ats(exit_ats)

    else:
        logger.warn('Invalid set_profile value: ' + str(profile_val))

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

    Events.trigger(Evt.DATABASE_BACKUP, {
        'file_name': emit_payload['file_name'],
        })

    SOCKET_IO.emit('database_bkp_done', emit_payload)

@SOCKET_IO.on('reset_database')
def on_reset_database(data):
    '''Reset database.'''
    global FULL_RESULTS_CACHE_VALID
    FULL_RESULTS_CACHE_VALID = False

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

    Events.trigger(Evt.DATABASE_RESET)

@SOCKET_IO.on('shutdown_pi')
def on_shutdown_pi():
    '''Shutdown the raspberry pi.'''
    Events.trigger(Evt.SHUTDOWN)
    CLUSTER.emit('shutdown_pi')
    emit_priority_message(__('Server has shut down.'), True)
    logger.info('Shutdown pi')
    gevent.sleep(1);
    os.system("sudo shutdown now")

@SOCKET_IO.on('reboot_pi')
def on_reboot_pi():
    '''Reboot the raspberry pi.'''
    Events.trigger(Evt.SHUTDOWN)
    CLUSTER.emit('reboot_pi')
    emit_priority_message(__('Server is rebooting.'), True)
    logger.info('Rebooting pi')
    gevent.sleep(1);
    os.system("sudo reboot now")

@SOCKET_IO.on('download_logs')
def on_download_logs(data):
    '''Download logs (as .zip file).'''
    zip_path_name = log.create_log_files_zip(logger, Config.CONFIG_FILE_NAME, DB_FILE_NAME)
    if zip_path_name:
        checkSetFileOwnerPi(zip_path_name)
        try:
            # read logs-zip file data and convert to Base64
            with open(zip_path_name, mode='rb') as file_obj:
                file_content = base64.encodestring(file_obj.read())
            emit_payload = {
                'file_name': os.path.basename(zip_path_name),
                'file_data' : file_content
            }
            Events.trigger(Evt.DATABASE_BACKUP, {
                'file_name': emit_payload['file_name'],
                })
            SOCKET_IO.emit(data['emit_fn_name'], emit_payload)
        except Exception:
            logger.exception("Error downloading logs-zip file")

@SOCKET_IO.on("set_min_lap")
def on_set_min_lap(data):
    min_lap = data['min_lap']
    Options.set("MinLapSec", data['min_lap'])

    Events.trigger(Evt.MIN_LAP_TIME_SET, {
        'min_lap': min_lap,
        })

    logger.info("set min lap time to %s seconds" % min_lap)
    emit_min_lap(noself=True)

@SOCKET_IO.on("set_min_lap_behavior")
def on_set_min_lap_behavior(data):
    min_lap_behavior = int(data['min_lap_behavior'])
    Options.set("MinLapBehavior", min_lap_behavior)

    Events.trigger(Evt.MIN_LAP_BEHAVIOR_SET, {
        'min_lap_behavior': min_lap_behavior,
        })

    logger.info("set min lap behavior to %s" % min_lap_behavior)
    emit_min_lap(noself=True)

@SOCKET_IO.on("set_race_format")
def on_set_race_format(data):
    ''' set current race_format '''
    if RACE.race_status == RaceStatus.READY: # prevent format change if race running
        race_format_val = data['race_format']
        race_format = Database.RaceFormat.query.get(race_format_val)
        DB.session.flush()
        setCurrentRaceFormat(race_format)
        DB.session.commit()

        Events.trigger(Evt.RACE_FORMAT_SET, {
            'race_format': race_format_val,
            })

        emit_race_format()
        logger.info("set race format to '%s' (%s)" % (race_format.name, race_format.id))
        CLUSTER.emitToMirrors('set_race_format', data)
    else:
        emit_priority_message(__('Format change prevented by active race: Stop and save/discard laps'), False, nobroadcast=True)
        logger.info("Format change prevented by active race")
        emit_race_format()

@SOCKET_IO.on('add_race_format')
def on_add_race_format():
    '''Adds new format in the database by duplicating an existing one.'''
    source_format = getCurrentRaceFormat()
    all_format_names = [format.name for format in Database.RaceFormat.query.all()]
    new_format = Database.RaceFormat(name=uniqueName(source_format.name, all_format_names),
                             race_mode=source_format.race_mode,
                             race_time_sec=source_format.race_time_sec ,
                             start_delay_min=source_format.start_delay_min,
                             start_delay_max=source_format.start_delay_max,
                             staging_tones=source_format.staging_tones,
                             number_laps_win=source_format.number_laps_win,
                             win_condition=source_format.win_condition,
                             team_racing_mode=source_format.team_racing_mode)
    DB.session.add(new_format)
    DB.session.flush()
    DB.session.refresh(new_format)
    DB.session.commit()

    Events.trigger(Evt.RACE_FORMAT_ADD, {
        'race_format': new_format.id,
        })

    on_set_race_format(data={ 'race_format': new_format.id })

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
        if 'staging_tones' in data:
            race_format.staging_tones = data['staging_tones']
        if 'number_laps_win' in data:
            race_format.number_laps_win = data['number_laps_win']
        if 'win_condition' in data:
            race_format.win_condition = data['win_condition']
        if 'team_racing_mode' in data:
            race_format.team_racing_mode = (True if data['team_racing_mode'] else False)
        DB.session.commit()
        RACE.cacheStatus = Results.CacheStatus.INVALID  # refresh leaderboard

        Events.trigger(Evt.RACE_FORMAT_ALTER, {
            'race_format': race_format.id,
            })

        setCurrentRaceFormat(race_format)
        logger.info('Altered race format to %s' % (data))
        if emit:
            emit_race_format()
            emit_class_data()

@SOCKET_IO.on('delete_race_format')
def on_delete_race_format():
    '''Delete profile'''
    if RACE.race_status == RaceStatus.READY: # prevent format change if race running
        raceformat = getCurrentDbRaceFormat()
        raceformat_id = raceformat.id
        if raceformat and (DB.session.query(Database.RaceFormat).count() > 1): # keep one format
            DB.session.delete(raceformat)
            DB.session.commit()
            first_raceFormat = Database.RaceFormat.query.first()

            Events.trigger(Evt.RACE_FORMAT_DELETE, {
                'race_format': raceformat_id,
                })

            setCurrentRaceFormat(first_raceFormat)
            emit_race_format()
        else:
            logger.info('Refusing to delete only format')
    else:
        emit_priority_message(__('Format change prevented by active race: Stop and save/discard laps'), False, nobroadcast=True)
        logger.info("Format change prevented by active race")

# LED Effects

def emit_led_effect_setup(**params):
    '''Emits LED event/effect wiring options.'''
    if led_manager.isEnabled():
        effects = led_manager.getRegisteredEffects()

        emit_payload = {
            'events': []
        }

        for event in LEDEvent.configurable_events:
            selectedEffect = led_manager.getEventEffect(event['event'])

            effect_list = []

            for effect in effects:
                if event['event'] in effects[effect]['validEvents']:
                    effect_list.append({
                        'name': effect,
                        'label': __(effects[effect]['label'])
                    })

            emit_payload['events'].append({
                'event': event["event"],
                'label': __(event["label"]),
                'selected': selectedEffect,
                'effects': effect_list
            })

        # never broadcast
        emit('led_effect_setup_data', emit_payload)

def emit_led_effects(**params):
    if led_manager.isEnabled():
        effects = led_manager.getRegisteredEffects()

        effect_list = []
        for effect in effects:
            if LEDEvent.NOCONTROL not in effects[effect]['validEvents']:
                effect_list.append({
                    'name': effect,
                    'label': __(effects[effect]['label'])
                })

        emit_payload = {
            'effects': effect_list
        }

        # never broadcast
        emit('led_effects', emit_payload)

@SOCKET_IO.on('set_led_event_effect')
def on_set_led_effect(data):
    '''Set effect for event.'''
    if led_manager.isEnabled() and 'event' in data and 'effect' in data:
        led_manager.setEventEffect(data['event'], data['effect'])

        effect_opt = Options.get('ledEffects')
        if effect_opt:
            effects = json.loads(effect_opt)
        else:
            effects = {}

        effects[data['event']] = data['effect']
        Options.set('ledEffects', json.dumps(effects))

        Events.trigger(Evt.LED_EFFECT_SET, {
            'effect': data['event'],
            })

        logger.info('Set LED event {0} to effect {1}'.format(data['event'], data['effect']))

@SOCKET_IO.on('use_led_effect')
def on_use_led_effect(data):
    '''Activate arbitrary LED Effect.'''
    if led_manager.isEnabled() and 'effect' in data:
        led_manager.setEventEffect(Evt.LED_MANUAL, data['effect'])

        args = None
        if 'args' in data:
            args = data['args']

        Events.trigger(Evt.LED_MANUAL, args)

# Race management socket io events

@SOCKET_IO.on('schedule_race')
def on_schedule_race(data):
    global RACE

    RACE.scheduled_time = monotonic() + (data['m'] * 60) + data['s']
    RACE.scheduled = True

    Events.trigger(Evt.RACE_SCHEDULE, {
        'scheduled_at': RACE.scheduled_time
        })

    SOCKET_IO.emit('race_scheduled', {
        'scheduled': RACE.scheduled,
        'scheduled_at': RACE.scheduled_time
        })

    emit_priority_message(__("Next race begins in {0:01d}:{1:02d}".format(data['m'], data['s'])), True)

@SOCKET_IO.on('cancel_schedule_race')
def cancel_schedule_race():
    global RACE

    RACE.scheduled = False

    Events.trigger(Evt.RACE_SCHEDULE_CANCEL)

    SOCKET_IO.emit('RACE.scheduled', {
        'scheduled': RACE.scheduled,
        'scheduled_at': RACE.scheduled_time
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
    global RACE
    valid_pilots = False
    heatNodes = Database.HeatNode.query.filter_by(heat_id=RACE.current_heat).all()
    for heatNode in heatNodes:
        if heatNode.node_index < RACE.num_nodes:
            if heatNode.pilot_id != Database.PILOT_ID_NONE:
                valid_pilots = True
                break

    if valid_pilots is False:
        emit_priority_message(__('No valid pilots in race'), True, nobroadcast=True)

    CLUSTER.emit('stage_race')
    if RACE.race_status == RaceStatus.READY: # only initiate staging if ready
        '''Common race start events (do early to prevent processing delay when start is called)'''
        global FULL_RESULTS_CACHE_VALID
        INTERFACE.enable_calibration_mode() # Nodes reset triggers on next pass

        Events.trigger(Evt.RACE_STAGE)
        clear_laps() # Clear laps before race start
        init_node_cross_fields()  # set 'cur_pilot_id' and 'cross' fields on nodes
        RACE.last_race_cacheStatus = Results.CacheStatus.INVALID # invalidate last race results cache
        RACE.timer_running = False # indicate race timer not running
        RACE.race_status = RaceStatus.STAGING
        INTERFACE.set_race_status(RaceStatus.STAGING)
        emit_current_laps() # Race page, blank laps to the web client
        emit_current_leaderboard() # Race page, blank leaderboard to the web client
        emit_race_status()

        race_format = getCurrentRaceFormat()
        if race_format.team_racing_mode:
            check_emit_team_racing_status()  # Show initial team-racing status info
        MIN = min(race_format.start_delay_min, race_format.start_delay_max) # in case values are reversed
        MAX = max(race_format.start_delay_min, race_format.start_delay_max)
        DELAY = random.randint(MIN, MAX) + 0.9 # Add ~1 for prestage (<1 to prevent timer beep)

        RACE.start_time_monotonic = monotonic() + DELAY
        RACE.start_token = random.random()
        gevent.spawn(race_start_thread, RACE.start_token)

        SOCKET_IO.emit('stage_ready', {
            'hide_stage_timer': MIN != MAX,
            'delay': DELAY,
            'race_mode': race_format.race_mode,
            'race_time_sec': race_format.race_time_sec,
            'pi_starts_at_s': RACE.start_time_monotonic
        }) # Announce staging with chosen delay

def autoUpdateCalibration():
    ''' Apply best tuning values to nodes '''
    for node_index, node in enumerate(INTERFACE.nodes):
        calibration = findBestValues(node, node_index)

        if node.enter_at_level is not calibration['enter_at_level']:
            on_set_enter_at_level({
                'node': node_index,
                'enter_at_level': calibration['enter_at_level']
            })

        if node.exit_at_level is not calibration['exit_at_level']:
            on_set_exit_at_level({
                'node': node_index,
                'exit_at_level': calibration['exit_at_level']
            })

    logger.info('Updated calibration with best discovered values')
    emit_enter_and_exit_at_levels()

def findBestValues(node, node_index):
    ''' Search race history for best tuning values '''

    # get commonly used values
    heat = Database.Heat.query.get(RACE.current_heat)
    pilot = Database.HeatNode.query.filter_by(heat_id=RACE.current_heat, node_index=node_index).first().pilot_id
    current_class = heat.class_id

    # test for disabled node
    if pilot is Database.PILOT_ID_NONE or node.frequency is RHUtils.FREQUENCY_ID_NONE:
        logger.debug('Node {0} calibration: skipping disabled node'.format(node.index+1))
        return {
            'enter_at_level': node.enter_at_level,
            'exit_at_level': node.exit_at_level
        }

    # test for same heat, same node
    race_query = Database.SavedRaceMeta.query.filter_by(heat_id=heat.id).order_by(-Database.SavedRaceMeta.id).first()

    if race_query:
        pilotrace_query = Database.SavedPilotRace.query.filter_by(race_id=race_query.id, pilot_id=pilot).order_by(-Database.SavedPilotRace.id).first()
        if pilotrace_query:
            logger.debug('Node {0} calibration: found same pilot+node in same heat'.format(node.index+1))
            return {
                'enter_at_level': pilotrace_query.enter_at,
                'exit_at_level': pilotrace_query.exit_at
            }

    # test for same class, same pilot, same node
    race_query = Database.SavedRaceMeta.query.filter_by(class_id=current_class).order_by(-Database.SavedRaceMeta.id).first()
    if race_query:
        pilotrace_query = Database.SavedPilotRace.query.filter_by(race_id=race_query.id, node_index=node_index, pilot_id=pilot).order_by(-Database.SavedPilotRace.id).first()
        if pilotrace_query:
            logger.debug('Node {0} calibration: found same pilot+node in other heat with same class'.format(node.index+1))
            return {
                'enter_at_level': pilotrace_query.enter_at,
                'exit_at_level': pilotrace_query.exit_at
            }

    # test for same pilot, same node
    pilotrace_query = Database.SavedPilotRace.query.filter_by(node_index=node_index, pilot_id=pilot).order_by(-Database.SavedPilotRace.id).first()
    if pilotrace_query:
        logger.debug('Node {0} calibration: found same pilot+node in other heat with other class'.format(node.index+1))
        return {
            'enter_at_level': pilotrace_query.enter_at,
            'exit_at_level': pilotrace_query.exit_at
        }

    # test for same node
    pilotrace_query = Database.SavedPilotRace.query.filter_by(node_index=node_index).order_by(-Database.SavedPilotRace.id).first()
    if pilotrace_query:
        logger.debug('Node {0} calibration: found same node in other heat'.format(node.index+1))
        return {
            'enter_at_level': pilotrace_query.enter_at,
            'exit_at_level': pilotrace_query.exit_at
        }

    # fallback
    logger.debug('Node {0} calibration: no calibration hints found, no change'.format(node.index+1))
    return {
        'enter_at_level': node.enter_at_level,
        'exit_at_level': node.exit_at_level
    }

def race_start_thread(start_token):
    global RACE

    # clear any lingering crossings at staging (if node rssi < enterAt)
    for node in INTERFACE.nodes:
        if node.crossing_flag and node.frequency > 0 and node.current_pilot_id != Database.PILOT_ID_NONE and \
                    node.current_rssi < node.enter_at_level:
            logger.info("Forcing end crossing for node {0} at staging (rssi={1}, enterAt={2}, exitAt={3})".\
                       format(node.index+1, node.current_rssi, node.enter_at_level, node.exit_at_level))
            INTERFACE.force_end_crossing(node.index)

    # do non-blocking delay before time-critical code
    while (monotonic() < RACE.start_time_monotonic - 0.5):
        gevent.sleep(0.1)

    if RACE.race_status == RaceStatus.STAGING and \
        RACE.start_token == start_token:
        # Only start a race if it is not already in progress
        # Null this thread if token has changed (race stopped/started quickly)

        # do blocking delay until race start
        while monotonic() < RACE.start_time_monotonic:
            pass

        # do time-critical tasks
        Events.trigger(Evt.RACE_START)

        # do secondary start tasks (small delay is acceptable)
        RACE.start_time = datetime.now() # record standard-formatted time

        for node in INTERFACE.nodes:
            node.history_values = [] # clear race history
            node.history_times = []
            node.under_min_lap_count = 0
            # clear any lingering crossing (if rssi>enterAt then first crossing starts now)
            if node.crossing_flag and node.frequency > 0 and node.current_pilot_id != Database.PILOT_ID_NONE:
                logger.info("Forcing end crossing for node {0} at start (rssi={1}, enterAt={2}, exitAt={3})".\
                           format(node.index+1, node.current_rssi, node.enter_at_level, node.exit_at_level))
                INTERFACE.force_end_crossing(node.index)

        RACE.race_status = RaceStatus.RACING # To enable registering passed laps
        INTERFACE.set_race_status(RaceStatus.RACING)
        RACE.timer_running = True # indicate race timer is running
        RACE.laps_winner_name = None  # name of winner in first-to-X-laps race
        RACE.winning_lap_id = 0  # track winning lap-id if race tied during first-to-X-laps race
        emit_race_status() # Race page, to set race button states
        logger.info('Race started at {0} ({1:13f})'.format(RACE.start_time_monotonic, monotonic_to_milliseconds(RACE.start_time_monotonic)))

@SOCKET_IO.on('stop_race')
def on_stop_race():
    '''Stops the race and stops registering laps.'''
    global RACE

    CLUSTER.emit('stop_race')
    if RACE.race_status == RaceStatus.RACING:
        RACE.end_time = monotonic() # Update the race end time stamp
        delta_time = RACE.end_time - RACE.start_time_monotonic
        milli_sec = delta_time * 1000.0
        RACE.duration_ms = milli_sec

        logger.info('Race stopped at {0} ({1:13f}), duration {2}ms'.format(RACE.end_time, monotonic_to_milliseconds(RACE.end_time), RACE.duration_ms))

        min_laps_list = []  # show nodes with laps under minimum (if any)
        for node in INTERFACE.nodes:
            if node.under_min_lap_count > 0:
                min_laps_list.append('Node {0} Count={1}'.format(node.index+1, node.under_min_lap_count))
        if len(min_laps_list) > 0:
            logger.info('Nodes with laps under minimum:  ' + ', '.join(min_laps_list))

        RACE.race_status = RaceStatus.DONE # To stop registering passed laps, waiting for laps to be cleared
        INTERFACE.set_race_status(RaceStatus.DONE)
        Events.trigger(Evt.RACE_STOP)
    else:
        logger.info('No active race to stop')
        RACE.race_status = RaceStatus.READY # Go back to ready state
        INTERFACE.set_race_status(RaceStatus.READY)
        led_manager.clear()

    RACE.timer_running = False # indicate race timer not running
    RACE.scheduled = False # also stop any deferred start

    SOCKET_IO.emit('stop_timer') # Loop back to race page to start the timer counting up
    emit_race_status() # Race page, to set race button states

@SOCKET_IO.on('save_laps')
def on_save_laps():
    '''Save current laps data to the database.'''
    global FULL_RESULTS_CACHE_VALID
    FULL_RESULTS_CACHE_VALID = False
    race_format = getCurrentRaceFormat()
    heat = Database.Heat.query.get(RACE.current_heat)
    # Get the last saved round for the current heat
    max_round = DB.session.query(DB.func.max(Database.SavedRaceMeta.round_id)) \
            .filter_by(heat_id=RACE.current_heat).scalar()
    if max_round is None:
        max_round = 0
    # Loop through laps to copy to saved races
    profile = getCurrentProfile()
    profile_freqs = json.loads(profile.frequencies)

    new_race = Database.SavedRaceMeta( \
        round_id=max_round+1, \
        heat_id=RACE.current_heat, \
        class_id=heat.class_id, \
        format_id=Options.get('currentFormat'), \
        start_time = RACE.start_time_monotonic, \
        start_time_formatted = RACE.start_time.strftime("%Y-%m-%d %H:%M:%S"), \
        cacheStatus=Results.CacheStatus.INVALID
    )
    DB.session.add(new_race)
    DB.session.flush()
    DB.session.refresh(new_race)

    for node_index in range(RACE.num_nodes):
        if profile_freqs["f"][node_index] != RHUtils.FREQUENCY_ID_NONE:
            pilot_id = Database.HeatNode.query.filter_by( \
                heat_id=RACE.current_heat, node_index=node_index).one().pilot_id

            new_pilotrace = Database.SavedPilotRace( \
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

            for lap in RACE.node_laps[node_index]:
                DB.session.add(Database.SavedRaceLap( \
                    race_id=new_race.id, \
                    pilotrace_id=new_pilotrace.id, \
                    node_index=node_index, \
                    pilot_id=pilot_id, \
                    lap_time_stamp=lap['lap_time_stamp'], \
                    lap_time=lap['lap_time'], \
                    lap_time_formatted=lap['lap_time_formatted'], \
                    source = lap['source'], \
                    deleted = lap['deleted']
                ))

    DB.session.commit()

    # spawn thread for updating results caches
    params = {
        'race_id': new_race.id,
        'heat_id': RACE.current_heat,
        'round_id': new_race.round_id,
    }
    gevent.spawn(Results.build_race_results_caches, DB, params)

    Events.trigger(Evt.LAPS_SAVE, {
        'race_id': new_race.id,
        })

    logger.info('Current laps saved: Heat {0} Round {1}'.format(RACE.current_heat, max_round+1))
    on_discard_laps(saved=True) # Also clear the current laps
    emit_round_data_notify() # live update rounds page

@SOCKET_IO.on('resave_laps')
def on_resave_laps(data):
    global FULL_RESULTS_CACHE_VALID
    FULL_RESULTS_CACHE_VALID = False

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

    Pilotrace = Database.SavedPilotRace.query.filter_by(id=pilotrace_id).one()
    Pilotrace.enter_at = enter_at
    Pilotrace.exit_at = exit_at

    Database.SavedRaceLap.query.filter_by(pilotrace_id=pilotrace_id).delete()

    for lap in laps:
        tmp_lap_time_formatted = lap['lap_time']
        if isinstance(tmp_lap_time_formatted, float):
            tmp_lap_time_formatted = RHUtils.time_format(lap['lap_time'])
        DB.session.add(Database.SavedRaceLap( \
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
    logger.info(message)

    # spawn thread for updating results caches
    params = {
        'race_id': race_id,
        'heat_id': heat_id,
        'round_id': round_id,
    }
    gevent.spawn(Results.build_race_results_caches, DB, params)

    Events.trigger(Evt.LAPS_RESAVE, {
        'race_id': race_id,
        'pilot_id': pilot_id,
        })

    emit_round_data_notify()
    if int(Options.get('calibrationMode')):
        autoUpdateCalibration()

@SOCKET_IO.on('discard_laps')
def on_discard_laps(**kwargs):
    '''Clear the current laps without saving.'''
    CLUSTER.emit('discard_laps')
    clear_laps()
    RACE.race_status = RaceStatus.READY # Flag status as ready to start next race
    INTERFACE.set_race_status(RaceStatus.READY)
    emit_current_laps() # Race page, blank laps to the web client
    emit_current_leaderboard() # Race page, blank leaderboard to the web client
    emit_race_status() # Race page, to set race button states
    race_format = getCurrentRaceFormat()
    if race_format.team_racing_mode:
        check_emit_team_racing_status()  # Show team-racing status info
    else:
        emit_team_racing_status('')  # clear any displayed "Winner is" text

    if 'saved' in kwargs and kwargs['saved'] == True:
        # discarding follows a save action
        pass
    else:
        # discarding does not follow a save action
        Events.trigger(Evt.LAPS_DISCARD)

    Events.trigger(Evt.LAPS_CLEAR)

def clear_laps():
    '''Clear the current laps table.'''
    global RACE
    RACE.last_race_results = Results.calc_leaderboard(DB, current_race=RACE, current_profile=getCurrentProfile())
    RACE.last_race_cacheStatus = Results.CacheStatus.VALID
    RACE.laps_winner_name = None  # clear winner in first-to-X-laps race
    RACE.winning_lap_id = 0
    db_reset_current_laps() # Clear out the current laps table
    DB.session.query(Database.LapSplit).delete()
    DB.session.commit()
    logger.info('Current laps cleared')

def init_node_cross_fields():
    '''Sets the 'current_pilot_id' and 'cross' values on each node.'''
    heatnodes = Database.HeatNode.query.filter_by( \
        heat_id=RACE.current_heat).all()

    for node in INTERFACE.nodes:
        node.current_pilot_id = Database.PILOT_ID_NONE
        if node.frequency and node.frequency > 0:
            for heatnode in heatnodes:
                if heatnode.node_index == node.index:
                    node.current_pilot_id = heatnode.pilot_id
                    break

        node.first_cross_flag = False
        node.show_crossing_flag = False

@SOCKET_IO.on('set_current_heat')
def on_set_current_heat(data):
    '''Update the current heat variable.'''
    new_heat_id = data['heat']
    RACE.current_heat = new_heat_id

    RACE.node_pilots = {
        '0': 0,
        '1': 0,
        '2': 0,
        '3': 0,
        '4': 0,
        '5': 0,
        '6': 0,
        '7': 0,
    }
    RACE.node_teams = {
        '0': None,
        '1': None,
        '2': None,
        '3': None,
        '4': None,
        '5': None,
        '6': None,
        '7': None,
    }
    for heatNode in Database.HeatNode.query.filter_by(heat_id=new_heat_id):
        RACE.node_pilots[heatNode.node_index] = heatNode.pilot_id

        if heatNode.pilot_id is not Database.PILOT_ID_NONE:
            RACE.node_teams[heatNode.node_index] = Database.Pilot.query.get(heatNode.pilot_id).team
        else:
            RACE.node_teams[heatNode.node_index] = None

    logger.info('Current heat set: Heat {0}'.format(new_heat_id))

    if int(Options.get('calibrationMode')):
        autoUpdateCalibration()

    Events.trigger(Evt.HEAT_SET, {
        'race': RACE,
        'heat_id': new_heat_id,
        })

    RACE.cacheStatus = Results.CacheStatus.INVALID  # refresh leaderboard
    emit_current_heat() # Race page, to update heat selection button
    emit_current_leaderboard() # Race page, to update callsigns in leaderboard
    race_format = getCurrentRaceFormat()
    if race_format.team_racing_mode:
        check_emit_team_racing_status()  # Show initial team-racing status info

@SOCKET_IO.on('generate_heats')
def on_generate_heats(data):
    '''Spawn heat generator thread'''
    gevent.spawn(generate_heats, data)

def generate_heats(data):
    RESULTS_TIMEOUT = 30 # maximum time to wait for results to generate

    '''Generate heats from qualifying class'''
    input_class = int(data['input_class'])
    output_class = int(data['output_class'])
    suffix = data['suffix']
    pilots_per_heat = int(data['pilots_per_heat'])

    if input_class == Database.CLASS_ID_NONE:
        results = {
            'by_race_time': []
        }
        for pilot in Database.Pilot.query.all():
            # *** if pilot is active
            entry = {}
            entry['pilot_id'] = pilot.id

            pilot_node = Database.HeatNode.query.filter_by(pilot_id=pilot.id).first()
            if pilot_node:
                entry['node'] = pilot_node.node_index
            else:
                entry['node'] = -1

            results['by_race_time'].append(entry)

        win_condition = WinCondition.NONE
        cacheStatus = Results.CacheStatus.VALID
    else:
        race_class = Database.RaceClass.query.get(input_class)
        race_format = Database.RaceFormat.query.get(race_class.format_id)
        results = race_class.results
        if race_format:
            win_condition = race_format.win_condition
            cacheStatus = race_class.cacheStatus
        else:
            win_condition = WinCondition.NONE
            cacheStatus = Results.CacheStatus.VALID
            logger.info('Unable to fetch format from race class {0}'.format(input_class))

    if cacheStatus == Results.CacheStatus.INVALID:
        # build new results if needed
        logger.info("No class cache available for {0}; regenerating".format(input_class))
        race_class.cacheStatus = monotonic()
        race_class.results = Results.calc_leaderboard(DB, class_id=race_class.id)
        race_class.cacheStatus = Results.CacheStatus.VALID
        DB.session.commit()

    time_now = monotonic()
    timeout = time_now + RESULTS_TIMEOUT
    while cacheStatus != Results.CacheStatus.VALID and time_now < timeout:
        gevent.sleep()
        time_now = monotonic()

    if cacheStatus == Results.CacheStatus.VALID:
        if win_condition == WinCondition.NONE:

            leaderboard = random.sample(results['by_race_time'], len(results['by_race_time']))
        else:
            leaderboard = results[results['meta']['primary_leaderboard']]

        generated_heats = []
        unplaced_pilots = []
        new_heat = {}
        assigned_pilots = 0

        available_nodes = []

        profile_freqs = json.loads(getCurrentProfile().frequencies)
        for node_index in range(RACE.num_nodes):
            if profile_freqs["f"][node_index] != RHUtils.FREQUENCY_ID_NONE:
                available_nodes.append(node_index)

        pilots_per_heat = min(pilots_per_heat, RACE.num_nodes, len(available_nodes))

        for i,row in enumerate(leaderboard, start=1):
            logger.debug("Placing {0} into heat {1}".format(row['pilot_id'], len(generated_heats)))

            if row['node'] in new_heat or row['node'] not in available_nodes:
                unplaced_pilots.append(row['pilot_id'])
            else:
                new_heat[row['node']] = row['pilot_id']

            assigned_pilots += 1

            if assigned_pilots >= pilots_per_heat or i == len(leaderboard):
                # find slots for unassigned pilots
                if len(unplaced_pilots):
                    for pilot in unplaced_pilots:
                        for index in available_nodes:
                            if index in new_heat:
                                continue
                            else:
                                new_heat[index] = pilot
                                break

                # heat is full, flush and start next heat
                generated_heats.append(new_heat)
                unplaced_pilots = []
                new_heat = {}
                assigned_pilots = 0

        # commit generated heats to database, lower seeds first
        letters = __('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        for idx, heat in enumerate(reversed(generated_heats), start=1):
            ladder = letters[len(generated_heats) - idx]
            new_heat = Database.Heat(class_id=output_class, cacheStatus=Results.CacheStatus.INVALID, note=ladder + ' ' + suffix)
            DB.session.add(new_heat)
            DB.session.flush()
            DB.session.refresh(new_heat)

            for node in range(RACE.num_nodes): # Add pilots
                if node in heat:
                    DB.session.add(Database.HeatNode(heat_id=new_heat.id, node_index=node, pilot_id=heat[node]))
                else:
                    DB.session.add(Database.HeatNode(heat_id=new_heat.id, node_index=node, pilot_id=Database.PILOT_ID_NONE))

            DB.session.commit()

        logger.info("Generated {0} heats from class {1}".format(len(generated_heats), input_class))
        SOCKET_IO.emit('heat_generate_done')

        Events.trigger(Evt.HEAT_GENERATE)

        emit_heat_data()
    else:
        logger.warning("Unable to generate heats from class {0}: can't get valid results".format(input_class))
        SOCKET_IO.emit('heat_generate_done')

@SOCKET_IO.on('delete_lap')
def on_delete_lap(data):
    '''Delete a false lap.'''

    node_index = data['node']
    lap_index = data['lap_index']

    RACE.node_laps[node_index][lap_index]['deleted'] = True

    time = RACE.node_laps[node_index][lap_index]['lap_time_stamp']

    lap_number = 0
    for lap in RACE.node_laps[node_index]:
        if not lap['deleted']:
            lap['lap_number'] = lap_number
            lap_number += 1
        else:
            lap['lap_number'] = None

    db_last = False
    db_next = False
    for lap in RACE.node_laps[node_index]:
        if not lap['deleted']:
            if lap['lap_time_stamp'] < time:
                db_last = lap
            if lap['lap_time_stamp'] > time:
                db_next = lap
                break

    if db_next and db_last:
        db_next['lap_time'] = db_next['lap_time_stamp'] - db_last['lap_time_stamp']
        db_next['lap_time_formatted'] = RHUtils.time_format(db_next['lap_time'])
    elif db_next:
        db_next['lap_time'] = db_next['lap_time_stamp']
        db_next['lap_time_formatted'] = RHUtils.time_format(db_next['lap_time'])

    Events.trigger(Evt.LAP_DELETE, {
        'race': RACE,
        'node_index': node_index,
        })

    logger.info('Lap deleted: Node {0} Lap {1}'.format(node_index+1, lap_index))
    RACE.cacheStatus = Results.CacheStatus.INVALID  # refresh leaderboard
    emit_current_laps() # Race page, update web client
    emit_current_leaderboard() # Race page, update web client
    race_format = getCurrentRaceFormat()
    if race_format.team_racing_mode:
        # update team-racing status info
        if race_format.win_condition != WinCondition.MOST_LAPS:  # if not Most Laps Wins race
            if race_format.number_laps_win > 0:  # if number-laps-win race
                t_laps_dict, team_name, pilot_team_dict = get_team_laps_info(-1, race_format.number_laps_win)
                check_team_laps_win(t_laps_dict, race_format.number_laps_win, pilot_team_dict)
            else:
                t_laps_dict = get_team_laps_info()[0]
        else:  # if Most Laps Wins race enabled
            t_laps_dict, t_name, pilot_team_dict = get_team_laps_info(-1, RACE.winning_lap_id)
            if ms_from_race_start() > race_format.race_time_sec*1000:  # if race done
                check_most_laps_win(node_index, t_laps_dict, pilot_team_dict)
        check_emit_team_racing_status(t_laps_dict)

@SOCKET_IO.on('simulate_lap')
def on_simulate_lap(data):
    '''Simulates a lap (for debug testing).'''
    node_index = data['node']
    logger.info('Simulated lap: Node {0}'.format(node_index+1))
    Events.trigger(Evt.CROSSING_EXIT, {
        'nodeIndex': node_index,
        'color': hexToColor(Options.get('colorNode_' + str(node_index), '#ffffff'))
        })
    INTERFACE.intf_simulate_lap(node_index, 0)

@SOCKET_IO.on('LED_solid')
def on_LED_solid(data):
    '''LED Solid Color'''
    led_red = data['red']
    led_green = data['green']
    led_blue = data['blue']

    on_use_led_effect({
        'effect': "stripColor",
        'args': {
            'color': Color(led_red,led_green,led_blue),
            'pattern': ColorPattern.SOLID,
            'time': None
        }
    })

@SOCKET_IO.on('LED_chase')
def on_LED_chase(data):
    '''LED Solid Color Chase'''
    led_red = data['red']
    led_green = data['green']
    led_blue = data['blue']

    on_use_led_effect({
        'effect': "stripColor",
        'args': {
            'color': Color(led_red,led_green,led_blue),
#            'pattern': ColorPattern.CHASE,  # TODO implement chase animation pattern
            'pattern': ColorPattern.ALTERNATING,
            'time': 5
        }
    })


@SOCKET_IO.on('LED_RB')
def on_LED_RB():
    '''LED rainbow'''
    on_use_led_effect({
        'effect': "rainbow",
        'args': {
            'time': 5
        }
    })

@SOCKET_IO.on('LED_RBCYCLE')
def on_LED_RBCYCLE():
    '''LED rainbow Cycle'''
    on_use_led_effect({
        'effect': "rainbowCycle",
        'args': {
            'time': 5
        }
    })

@SOCKET_IO.on('LED_RBCHASE')
def on_LED_RBCHASE():
    '''LED Rainbow Cycle Chase'''
    on_use_led_effect({
        'effect': "rainbowCycleChase",
        'args': {
            'time': 5
        }
    })

@SOCKET_IO.on('LED_brightness')
def on_LED_brightness(data):
    '''Change LED Brightness'''
    brightness = data['brightness']
    strip.setBrightness(brightness)
    strip.show()
    Options.set("ledBrightness", brightness)
    Events.trigger(Evt.LED_BRIGHTNESS_SET, {
        'level': brightness,
        })

@SOCKET_IO.on('set_option')
def on_set_option(data):
    Options.set(data['option'], data['value'])
    Events.trigger(Evt.OPTION_SET, {
        'option': data['option'],
        'value': data['value'],
        })

@SOCKET_IO.on('get_race_scheduled')
def get_race_elapsed():
    # get current race status; never broadcasts to all
    emit('race_scheduled', {
        'scheduled': RACE.scheduled,
        'scheduled_at': RACE.scheduled_time
    })

@SOCKET_IO.on('save_callouts')
def save_callouts(data):
    # save callouts to Options
    callouts = json.dumps(data['callouts'])
    Options.set('voiceCallouts', callouts)
    logger.info('Set all voice callouts')
    logger.debug('Voice callouts set to: {0}'.format(callouts))

@SOCKET_IO.on('imdtabler_update_freqs')
def imdtabler_update_freqs(data):
    ''' Update IMDTabler page with new frequencies list '''
    emit_imdtabler_data(data['freq_list'].replace(',',' ').split())

@SOCKET_IO.on('clean_cache')
def clean_results_cache():
    ''' expose cach wiping for frontend debugging '''
    Results.invalidate_all_caches(DB)

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
        if interrupt:
            Events.trigger(Evt.MESSAGE_INTERRUPT, {
                'message': message,
                'interrupt': interrupt
                })
        else:
            Events.trigger(Evt.MESSAGE_STANDARD, {
                'message': message,
                'interrupt': interrupt
                })

        SOCKET_IO.emit('priority_message', emit_payload)

def emit_race_status(**params):
    '''Emits race status.'''
    race_format = getCurrentRaceFormat()

    emit_payload = {
            'race_status': RACE.race_status,
            'race_mode': race_format.race_mode,
            'race_time_sec': race_format.race_time_sec,
            'race_staging_tones': race_format.staging_tones,
            'hide_stage_timer': race_format.start_delay_min != race_format.start_delay_max,
            'pi_starts_at_s': RACE.start_time_monotonic
        }
    if ('nobroadcast' in params):
        emit('race_status', emit_payload)
    else:
        SOCKET_IO.emit('race_status', emit_payload)

def emit_frequency_data(**params):
    '''Emits node data.'''
    profile_freqs = json.loads(getCurrentProfile().frequencies)
    emit_payload = {
            'frequency': profile_freqs["f"][:RACE.num_nodes]
        }
    if ('nobroadcast' in params):
        emit('frequency_data', emit_payload)
    else:
        SOCKET_IO.emit('frequency_data', emit_payload)

        # send changes to LiveTime
        for n in range(RACE.num_nodes):
            # if session.get('LiveTime', False):
            SOCKET_IO.emit('frequency_set', {
                'node': n,
                'frequency': profile_freqs["f"][n]
            })

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
    emit_payload = []
    for sensor in INTERFACE.sensors:
        emit_payload.append({sensor.name: sensor.getReadings()})

    if ('nobroadcast' in params):
        emit('environmental_data', emit_payload)
    else:
        SOCKET_IO.emit('environmental_data', emit_payload)

def emit_enter_and_exit_at_levels(**params):
    '''Emits enter-at and exit-at levels for nodes.'''
    profile = getCurrentProfile()
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
    tune_val = getCurrentProfile()
    emit_payload = {
        'profile_ids': [profile.id for profile in Database.Profiles.query.all()],
        'profile_names': [profile.name for profile in Database.Profiles.query.all()],
        'current_profile': int(Options.get('currentProfile')),
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
            'language': Options.get("currentLanguage"),
            'languages': Language.getLanguages()
        }
    if ('nobroadcast' in params):
        emit('language', emit_payload)
    else:
        SOCKET_IO.emit('language', emit_payload)

def emit_all_languages(**params):
    '''Emits full language dictionary.'''
    emit_payload = {
            'languages': Language.getAllLanguages()
        }
    if ('nobroadcast' in params):
        emit('all_languages', emit_payload)
    else:
        SOCKET_IO.emit('all_languages', emit_payload)

def emit_min_lap(**params):
    '''Emits current minimum lap.'''
    emit_payload = {
        'min_lap': Options.get('MinLapSec'),
        'min_lap_behavior': int(Options.get("MinLapBehavior"))
    }
    if ('nobroadcast' in params):
        emit('min_lap', emit_payload)
    else:
        SOCKET_IO.emit('min_lap', emit_payload)

def emit_race_format(**params):
    '''Emits race format values.'''
    race_format = getCurrentRaceFormat()
    is_db_race_format = RHRaceFormat.isDbBased(race_format)
    has_race = not is_db_race_format or Database.SavedRaceMeta.query.filter_by(format_id=race_format.id).first()
    if has_race:
        locked = True
    else:
        locked = False

    emit_payload = {
        'format_ids': [raceformat.id for raceformat in Database.RaceFormat.query.all()],
        'format_names': [raceformat.name for raceformat in Database.RaceFormat.query.all()],
        'current_format': race_format.id if is_db_race_format else None,
        'format_name': race_format.name,
        'race_mode': race_format.race_mode,
        'race_time_sec': race_format.race_time_sec,
        'start_delay_min': race_format.start_delay_min,
        'start_delay_max': race_format.start_delay_max,
        'staging_tones': race_format.staging_tones,
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
        emit_current_leaderboard()

def emit_race_formats(**params):
    '''Emits all race formats.'''
    formats = Database.RaceFormat.query.all()
    emit_payload = {}
    for race_format in formats:
        format_copy = {
            'format_name': race_format.name,
            'race_mode': race_format.race_mode,
            'race_time_sec': race_format.race_time_sec,
            'start_delay_min': race_format.start_delay_min,
            'start_delay_max': race_format.start_delay_max,
            'staging_tones': race_format.staging_tones,
            'number_laps_win': race_format.number_laps_win,
            'win_condition': race_format.win_condition,
            'team_racing_mode': 1 if race_format.team_racing_mode else 0,
        }

        has_race = Database.SavedRaceMeta.query.filter_by(format_id=race_format.id).first()

        if has_race:
            format_copy['locked'] = True
        else:
            format_copy['locked'] = False

        emit_payload[race_format.id] = format_copy

    if ('nobroadcast' in params):
        emit('race_formats', emit_payload)
    else:
        SOCKET_IO.emit('race_formats', emit_payload)

def emit_current_laps(**params):
    '''Emits current laps.'''
    global RACE
    if 'use_cache' in params and RACE.last_race_cacheStatus == Results.CacheStatus.VALID:
        emit_payload = RACE.last_race_laps
    else:
        current_laps = []
        for node in range(RACE.num_nodes):
            node_laps = []
            fastest_lap_time = float("inf")
            fastest_lap_index = None
            last_lap_id = -1
            for idx, lap in enumerate(RACE.node_laps[node]):
                if not lap['deleted']:
                    splits = get_splits(node, lap['lap_number'], True)
                    node_laps.append({
                        'lap_index': idx,
                        'lap_number': lap['lap_number'],
                        'lap_raw': lap['lap_time'],
                        'lap_time': lap['lap_time_formatted'],
                        'lap_time_stamp': lap['lap_time_stamp'],
                        'splits': splits
                    })
                    last_lap_id = lap['lap_number']
                    if lap['lap_time'] > 0 and idx > 0 and lap['lap_time'] < fastest_lap_time:
                        fastest_lap_time = lap['lap_time']
                        fastest_lap_index = idx

            splits = get_splits(node, last_lap_id+1, False)
            if splits:
                node_laps.append({
                    'lap_number': last_lap_id+1,
                    'lap_time': '',
                    'lap_time_stamp': 0,
                    'splits': splits
                })
            current_laps.append({
                'laps': node_laps,
                'fastest_lap_index': fastest_lap_index,
            })
        current_laps = {
            'node_index': current_laps
        }
        emit_payload = current_laps
        RACE.last_race_laps = current_laps

    if ('nobroadcast' in params):
        emit('current_laps', emit_payload)
    else:
        SOCKET_IO.emit('current_laps', emit_payload)

def get_splits(node, lap_id, lapCompleted):
    splits = []
    for slave_index in range(len(CLUSTER.slaves)):
        split = Database.LapSplit.query.filter_by(node_index=node,lap_id=lap_id,split_id=slave_index).one_or_none()
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
    for heat in Database.SavedRaceMeta.query.with_entities(Database.SavedRaceMeta.heat_id).distinct().order_by(Database.SavedRaceMeta.heat_id):
        heatnote = Database.Heat.query.get(heat.heat_id).note

        rounds = {}
        for round in Database.SavedRaceMeta.query.distinct().filter_by(heat_id=heat.heat_id).order_by(Database.SavedRaceMeta.round_id):
            pilotraces = []
            for pilotrace in Database.SavedPilotRace.query.filter_by(race_id=round.id).all():
                laps = []
                for lap in Database.SavedRaceLap.query.filter_by(pilotrace_id=pilotrace.id).order_by(Database.SavedRaceLap.lap_time_stamp).all():
                    laps.append({
                            'id': lap.id,
                            'lap_time_stamp': lap.lap_time_stamp,
                            'lap_time': lap.lap_time,
                            'lap_time_formatted': lap.lap_time_formatted,
                            'source': lap.source,
                            'deleted': lap.deleted
                        })

                pilot_data = Database.Pilot.query.filter_by(id=pilotrace.pilot_id).first()
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
    heats_by_class[Database.CLASS_ID_NONE] = [heat.id for heat in Database.Heat.query.filter_by(class_id=Database.CLASS_ID_NONE).all()]
    for race_class in Database.RaceClass.query.all():
        heats_by_class[race_class.id] = [heat.id for heat in Database.Heat.query.filter_by(class_id=race_class.id).all()]

    current_classes = {}
    for race_class in Database.RaceClass.query.all():
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
    ''' kick off non-blocking thread to generate data'''
    gevent.spawn(emit_round_data_thread, params, request.sid)

def emit_round_data_thread(params, sid):
    with APP.test_request_context():
        '''Emits saved races to rounds page.'''
        CACHE_TIMEOUT = 30

        global FULL_RESULTS_CACHE
        global FULL_RESULTS_CACHE_BUILDING
        global FULL_RESULTS_CACHE_VALID

        if FULL_RESULTS_CACHE_VALID: # Output existing calculated results
            emit_payload = FULL_RESULTS_CACHE

        elif FULL_RESULTS_CACHE_BUILDING: # Don't restart calculation if another calculation thread exists
            while FULL_RESULTS_CACHE_BUILDING is True: # Pause thread until calculations are completed
                gevent.sleep(1)

            emit_payload = FULL_RESULTS_CACHE

        else:
            FULL_RESULTS_CACHE_BUILDING = True

            heats = {}
            for heat in Database.SavedRaceMeta.query.with_entities(Database.SavedRaceMeta.heat_id).distinct().order_by(Database.SavedRaceMeta.heat_id):
                heatdata = Database.Heat.query.get(heat.heat_id)

                rounds = []
                for round in Database.SavedRaceMeta.query.distinct().filter_by(heat_id=heat.heat_id).order_by(Database.SavedRaceMeta.round_id):
                    pilotraces = []
                    for pilotrace in Database.SavedPilotRace.query.filter_by(race_id=round.id).all():
                        gevent.sleep()
                        laps = []
                        for lap in Database.SavedRaceLap.query.filter_by(pilotrace_id=pilotrace.id).all():
                            laps.append({
                                    'id': lap.id,
                                    'lap_time_stamp': lap.lap_time_stamp,
                                    'lap_time': lap.lap_time,
                                    'lap_time_formatted': lap.lap_time_formatted,
                                    'source': lap.source,
                                    'deleted': lap.deleted
                                })

                        pilot_data = Database.Pilot.query.filter_by(id=pilotrace.pilot_id).first()
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
                    if round.cacheStatus == Results.CacheStatus.INVALID:
                        results = Results.calc_leaderboard(DB, heat_id=heat.heat_id, round_id=round.round_id)
                        round.results = results
                        round.cacheStatus = Results.CacheStatus.VALID
                        DB.session.commit()
                    else:
                        checkStatus = True
                        while checkStatus:
                            gevent.idle()
                            if round.cacheStatus == Results.CacheStatus.VALID:
                                results = round.results
                                break
                            elif isinstance(round.cacheStatus, int) and round.cacheStatus < monotonic() + CACHE_TIMEOUT:
                                checkStatus = False

                    rounds.append({
                        'id': round.round_id,
                        'start_time_formatted': round.start_time_formatted,
                        'nodes': pilotraces,
                        'leaderboard': results
                    })

                if heatdata.cacheStatus == Results.CacheStatus.INVALID:
                    results = Results.calc_leaderboard(DB, heat_id=heat.heat_id)
                    heatdata.results = results
                    heatdata.cacheStatus = Results.CacheStatus.VALID
                    DB.session.commit()
                else:
                    checkStatus = True
                    while checkStatus:
                        gevent.idle()
                        if heatdata.cacheStatus == Results.CacheStatus.VALID:
                            results = heatdata.results
                            break
                        elif isinstance(heatdata.cacheStatus, int) and heatdata.cacheStatus < monotonic() + CACHE_TIMEOUT:
                            checkStatus = False

                heats[heat.heat_id] = {
                    'heat_id': heat.heat_id,
                    'note': heatdata.note,
                    'rounds': rounds,
                    'leaderboard': results
                }

            gevent.sleep()
            heats_by_class = {}
            heats_by_class[Database.CLASS_ID_NONE] = [heat.id for heat in Database.Heat.query.filter_by(class_id=Database.CLASS_ID_NONE).all()]
            for race_class in Database.RaceClass.query.all():
                heats_by_class[race_class.id] = [heat.id for heat in Database.Heat.query.filter_by(class_id=race_class.id).all()]

            gevent.sleep()
            current_classes = {}
            for race_class in Database.RaceClass.query.all():

                if race_class.cacheStatus == Results.CacheStatus.INVALID:
                    results = Results.calc_leaderboard(DB, class_id=race_class.id)
                    race_class.results = results
                    race_class.cacheStatus = Results.CacheStatus.VALID
                    DB.session.commit()
                else:
                    checkStatus = True
                    while checkStatus:
                        gevent.idle()
                        if race_class.cacheStatus == Results.CacheStatus.VALID:
                            results = race_class.results
                            break
                        elif isinstance(race_class.cacheStatus, int) and race_class.cacheStatus < monotonic() + CACHE_TIMEOUT:
                            checkStatus = False

                current_class = {}
                current_class['id'] = race_class.id
                current_class['name'] = race_class.name
                current_class['description'] = race_class.name
                current_class['leaderboard'] = results
                current_classes[race_class.id] = current_class

            gevent.sleep()

            if Options.get("eventResults_cacheStatus") == Results.CacheStatus.INVALID:
                results = Results.calc_leaderboard(DB)
                Options.set("eventResults", json.dumps(results))
                Options.set("eventResults_cacheStatus", Results.CacheStatus.VALID)
                DB.session.commit()
            else:
                checkStatus = True
                while checkStatus:
                    gevent.idle()
                    status = Options.get("eventResults_cacheStatus")
                    if status == Results.CacheStatus.VALID:
                        results = json.loads(Options.get("eventResults"))
                        break
                    elif isinstance(status, int) and status < monotonic() + CACHE_TIMEOUT:
                        checkStatus = False

            emit_payload = {
                'heats': heats,
                'heats_by_class': heats_by_class,
                'classes': current_classes,
                'event_leaderboard': results
            }

            FULL_RESULTS_CACHE = emit_payload
            FULL_RESULTS_CACHE_VALID = True
            FULL_RESULTS_CACHE_BUILDING = False

            Events.trigger(Evt.CACHE_READY)

        if ('nobroadcast' in params):
            emit('round_data', emit_payload, namespace='/', room=sid)
        else:
            SOCKET_IO.emit('round_data', emit_payload, namespace='/')

def emit_current_leaderboard(**params):
    '''Emits leaderboard.'''
    global RACE
    if 'use_cache' in params and RACE.last_race_cacheStatus == Results.CacheStatus.VALID:
        emit_payload = RACE.last_race_results
    elif RACE.cacheStatus == Results.CacheStatus.VALID:
        emit_payload = RACE.results
    else:
        results = Results.calc_leaderboard(DB, current_race=RACE, current_profile=getCurrentProfile())
        RACE.results = results
        RACE.cacheStatus = Results.CacheStatus.VALID
        emit_payload = results

    if ('nobroadcast' in params):
        emit('leaderboard', emit_payload)
    else:
        SOCKET_IO.emit('leaderboard', emit_payload)

def emit_heat_data(**params):
    '''Emits heat data.'''
    current_heats = {}
    for heat in Database.Heat.query.all():
        heat_id = heat.id
        note = heat.note
        race_class = heat.class_id

        heatnodes = Database.HeatNode.query.filter_by(heat_id=heat.id).order_by(Database.HeatNode.node_index).all()
        pilots = []
        for heatnode in heatnodes:
            pilots.append(heatnode.pilot_id)

        has_race = Database.SavedRaceMeta.query.filter_by(heat_id=heat.id).first()

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
    for race_class in Database.RaceClass.query.all():
        current_class = {}
        current_class['id'] = race_class.id
        current_class['name'] = race_class.name
        current_class['description'] = race_class.description
        current_classes.append(current_class)

    pilots = []
    for pilot in Database.Pilot.query.all():
        pilots.append({
            'pilot_id': pilot.id,
            'callsign': pilot.callsign,
            'name': pilot.name
            })

    if Options.get('pilotSort') == 'callsign':
        pilots.sort(key=lambda x: (x['callsign'], x['name']))
    else:
        pilots.sort(key=lambda x: (x['name'], x['callsign']))

    emit_payload = {
        'heats': current_heats,
        'pilot_data': pilots,
        'classes': current_classes,
        'pilotSort': Options.get('pilotSort'),
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
    for race_class in Database.RaceClass.query.all():
        current_class = {}
        current_class['id'] = race_class.id
        current_class['name'] = race_class.name
        current_class['description'] = race_class.description
        current_class['format'] = race_class.format_id

        has_race = Database.SavedRaceMeta.query.filter_by(class_id=race_class.id).all()
        if has_race:
            current_class['locked'] = True
        else:
            current_class['locked'] = False

        current_classes.append(current_class)

    formats = []
    for race_format in Database.RaceFormat.query.all():
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
    for pilot in Database.Pilot.query.all():
        opts_str = '' # create team-options string for each pilot, with current team selected
        for name in TEAM_NAMES_LIST:
            opts_str += '<option value="' + name + '"'
            if name == pilot.team:
                opts_str += ' selected'
            opts_str += '>' + name + '</option>'

        has_race = Database.SavedPilotRace.query.filter_by(pilot_id=pilot.id).first()

        if has_race:
            locked = True
        else:
            locked = False

        pilots_list.append({
            'pilot_id': pilot.id,
            'callsign': pilot.callsign,
            'team': pilot.team,
            'phonetic': pilot.phonetic,
            'name': pilot.name,
            'team_options': opts_str,
            'locked': locked,
        })

        if Options.get('pilotSort') == 'callsign':
            pilots_list.sort(key=lambda x: (x['callsign'], x['name']))
        else:
            pilots_list.sort(key=lambda x: (x['name'], x['callsign']))

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
    pilot_ids = []

    # dict for current heat with key=node_index, value=pilot_id
    node_pilot_dict = dict(Database.HeatNode.query.with_entities(Database.HeatNode.node_index, Database.HeatNode.pilot_id). \
        filter(Database.HeatNode.heat_id==RACE.current_heat, Database.HeatNode.pilot_id!=Database.PILOT_ID_NONE).all())

    for node_index in range(RACE.num_nodes):
        pilot_id = node_pilot_dict.get(node_index)
        if pilot_id:
            pilot = Database.Pilot.query.get(pilot_id)
            if pilot:
                pilot_ids.append(pilot_id)
                callsigns.append(pilot.callsign)
            else:
                pilot_ids.append(None)
                callsigns.append(None)
        else:
            callsigns.append(None)
            pilot_ids.append(None)

    heat_data = Database.Heat.query.get(RACE.current_heat)

    heat_note = heat_data.note

    heat_format = None
    if heat_data.class_id != Database.CLASS_ID_NONE:
        heat_format = Database.RaceClass.query.get(heat_data.class_id).format_id

    emit_payload = {
        'current_heat': RACE.current_heat,
        'callsign': callsigns,
        'pilot_ids': pilot_ids,
        'heat_note': heat_note,
        'heat_format': heat_format,
        'heat_class': heat_data.class_id
    }
    if ('nobroadcast' in params):
        emit('current_heat', emit_payload)
    else:
        SOCKET_IO.emit('current_heat', emit_payload)

def get_team_laps_info(cur_pilot_id=-1, num_laps_win=0):
    '''Calculates and returns team-racing info.'''
    logger.debug('get_team_laps_info cur_pilot_id={0}, num_laps_win={1}'.format(cur_pilot_id, num_laps_win))
              # create dictionary with key=pilot_id, value=team_name
    pilot_team_dict = {}
    profile_freqs = json.loads(getCurrentProfile().frequencies)
                             # dict for current heat with key=node_index, value=pilot_id
    node_pilot_dict = dict(Database.HeatNode.query.with_entities(Database.HeatNode.node_index, Database.HeatNode.pilot_id). \
                      filter(Database.HeatNode.heat_id==RACE.current_heat, Database.HeatNode.pilot_id!=Database.PILOT_ID_NONE).all())

    for node in INTERFACE.nodes:
        if profile_freqs["f"][node.index] != RHUtils.FREQUENCY_ID_NONE:
            pilot_id = node_pilot_dict.get(node.index)
            if pilot_id:
                pilot_team_dict[pilot_id] = Database.Pilot.query.filter_by(id=pilot_id).one().team
    logger.debug('get_team_laps_info pilot_team_dict: {0}'.format(pilot_team_dict))

    t_laps_dict = {}  # create dictionary (key=team_name, value=[lapCount,timestamp,item]) with initial zero laps
    for team_name in pilot_team_dict.values():
        if len(team_name) > 0 and team_name not in t_laps_dict:
            t_laps_dict[team_name] = [0, 0, None]

    # iterate through list of laps, sorted by lap timestamp
    grouped_laps = []
    for node_index in range(RACE.num_nodes):
        for lap in RACE.get_active_laps()[node_index]:
            lap['pilot'] = RACE.node_pilots[node_index]
            grouped_laps.append(lap)

    # each item has:  'lap_time_stamp', 'deleted' (True/False), 'lap_number', 'source', 'lap_time_formatted', 'lap_time' 'pilot' (number)
    for item in sorted(grouped_laps, key=lambda lap : lap['lap_time_stamp']):
        if item['lap_number'] > 0:  # current lap is > 0
            team_name = pilot_team_dict[item['pilot']]
            if team_name in t_laps_dict:
                t_laps_dict[team_name][0] += 1       # increment lap count for team
                if num_laps_win <= 0 or t_laps_dict[team_name][0] <= num_laps_win:
                    t_laps_dict[team_name][1] = item['lap_time_stamp']  # update lap_time_stamp (if not past winning lap)
                    t_laps_dict[team_name][2] = item
                    logger.debug('get_team_laps_info team[{0}]={1} item: {2}'.format(team_name, t_laps_dict[team_name], item))
                else:
                    logger.debug('get_team_laps_info ignoring post-win lap team[{0}]={1} item: {2}'.format(team_name, t_laps_dict[team_name], item))
    logger.debug('get_team_laps_info t_laps_dict: {0}'.format(t_laps_dict))

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
    if RACE.laps_winner_name is not None:
        if RACE.laps_winner_name is not RACE.status_tied_str and \
                RACE.laps_winner_name is not RACE.status_crossing:
            disp_str += '<span class="team-winner">Winner is Team ' + RACE.laps_winner_name + '</span>'
        else:
            disp_str += '<span class="team-winner">' + RACE.laps_winner_name + '</span>'
    #logger.info('Team racing status: ' + disp_str)
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
    profile_freqs = json.loads(getCurrentProfile().frequencies)
                             # dict for current heat with key=node_index, value=pilot_id
    node_pilot_dict = dict(Database.HeatNode.query.with_entities(Database.HeatNode.node_index, Database.HeatNode.pilot_id). \
                      filter(Database.HeatNode.heat_id==RACE.current_heat, Database.HeatNode.pilot_id!=Database.PILOT_ID_NONE).all())

    for node in INTERFACE.nodes:
        if profile_freqs["f"][node.index] != RHUtils.FREQUENCY_ID_NONE:
            pilot_id = node_pilot_dict.get(node.index)
            if pilot_id:
                lap_count = max(0, len(RACE.get_active_laps()[node.index]) - 1)

                            # if (other) pilot crossing for possible winning lap then wait
                            #  in case lap time turns out to be earliest:
                if node.pass_crossing_flag and node.index != pass_node_index and lap_count == num_laps_win - 1:
                    logger.info('check_pilot_laps_win waiting for crossing, Node {0}'.format(node.index+1))
                    return -1
                if lap_count >= num_laps_win:
                    lap_data = filter(lambda lap : lap['lap_number']==num_laps_win, RACE.get_active_laps()[node.index])
                    logger.debug('check_pilot_laps_win Node {0} pilot_id={1} tstamp={2}'.format(node.index+1, pilot_id, lap_data[0]['lap_time_stamp']))
                             # save pilot_id for earliest lap time:
                    if win_pilot_id < 0 or lap_data[0]['lap_time_stamp'] < win_lap_tstamp:
                        win_pilot_id = pilot_id
                        win_lap_tstamp = lap_data[0]['lap_time_stamp']
    logger.debug('check_pilot_laps_win returned win_pilot_id={0}'.format(win_pilot_id))
    return win_pilot_id

def check_team_laps_win(t_laps_dict, num_laps_win, pilot_team_dict, pass_node_index=-1):
    '''Checks if a team has completed enough laps to win.'''
    global RACE
         # make sure there's not a pilot in the process of crossing for a winning lap
    if RACE.laps_winner_name is None and pilot_team_dict:
        profile_freqs = None
                                  # dict for current heat with key=node_index, value=pilot_id
        node_pilot_dict = dict(Database.HeatNode.query.with_entities(Database.HeatNode.node_index, Database.HeatNode.pilot_id). \
                          filter(Database.HeatNode.heat_id==RACE.current_heat, Database.HeatNode.pilot_id!=Database.PILOT_ID_NONE).all())

        for node in INTERFACE.nodes:  # check if (other) pilot node is crossing gate
            if node.pass_crossing_flag and node.index != pass_node_index:
                if not profile_freqs:
                    profile_freqs = json.loads(getCurrentProfile().frequencies)
                if profile_freqs["f"][node.index] != RHUtils.FREQUENCY_ID_NONE:  # node is enabled
                    pilot_id = node_pilot_dict.get(node.index)
                    if pilot_id:  # node has pilot assigned to it
                        team_name = pilot_team_dict[pilot_id]
                        if team_name:
                            ent = t_laps_dict[team_name]  # entry for team [lapCount,timestamp]
                                        # if pilot crossing for possible winning lap then wait
                                        #  in case lap time turns out to be earliest:
                            if ent and ent[0] == num_laps_win - 1:
                                logger.info('check_team_laps_win waiting for crossing, Node {0}'.format(node.index+1))
                                return
    win_name = None
    win_tstamp = -1
    win_item = None
         # for each team, check if team has enough laps to win (and, if more
         #  than one has enough laps, pick team with earliest timestamp)
    for team_name in t_laps_dict.keys():
        ent = t_laps_dict[team_name]  # entry for team [lapCount,timestamp]
        if ent[0] >= num_laps_win and (win_tstamp < 0 or ent[1] < win_tstamp):
            win_name = team_name
            win_tstamp = ent[1]
            win_item = ent[2]
    logger.debug('check_team_laps_win win_name={0} tstamp={1}, win_item: {2}'.format(win_name, win_tstamp, win_item))
    RACE.laps_winner_name = win_name

def check_most_laps_win(pass_node_index=-1, t_laps_dict=None, pilot_team_dict=None):
    '''Checks if pilot or team has most laps for a win.'''
    # pass_node_index: -1 if called from 'check_race_time_expired()'; node.index if called from 'pass_record_callback()'
    global RACE
    logger.debug('Entered check_most_laps_win: pass_node_index={0}, t_laps_dict={1}, pilot_team_dict={2}'.format(pass_node_index, t_laps_dict, pilot_team_dict))

    race_format = getCurrentRaceFormat()
    if race_format.team_racing_mode: # team racing mode enabled

             # if not passed in then determine number of laps for each team
        if t_laps_dict is None:
            t_laps_dict, t_name, pilot_team_dict = get_team_laps_info(-1, RACE.winning_lap_id)

        max_lap_count = -1
        win_name = None
        win_tstamp = -1
        win_item = None
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
                    win_item = ent[2]
                    tied_flag = False
                    num_max_lap = 1
                else:  # if team is tied for highest lap count found so far
                    # not waiting for crossing
                    if pass_node_index >= 0 and RACE.laps_winner_name is not RACE.status_crossing:
                        num_max_lap += 1  # count number of teams at max lap
                        if ent[1] < win_tstamp:  # this team has earlier lap time
                            win_name = team_name
                            win_tstamp = ent[1]
                            win_item = ent[2]
                    else:  # waiting for crossing or called from 'check_race_time_expired()'
                        tied_flag = True
        logger.debug('check_most_laps_win tied={0} win_name={1} tstamp={2}'.format(tied_flag,win_name,win_tstamp))

        if tied_flag or max_lap_count <= 0:
            RACE.laps_winner_name = RACE.status_tied_str  # indicate status tied
            RACE.winning_lap_id = max_lap_count + 1 if max_lap_count >= 0 else 1
            check_emit_team_racing_status(t_laps_dict)
            emit_phonetic_text('Race tied', 'race_winner')
            logger.debug('check_most_laps_win race tied num_max_lap={0} max_lap_count={1}'.format(num_max_lap, max_lap_count))
            return  # wait for next 'pass_record_callback()' event

        if win_name:  # if a team looks like the winner

            # make sure there's not a pilot in the process of crossing for a winning lap
            if (RACE.laps_winner_name is None or RACE.laps_winner_name is RACE.status_tied_str or \
                                RACE.laps_winner_name is RACE.status_crossing) and pilot_team_dict:
                profile_freqs = None
                node_pilot_dict = None  # dict for current heat with key=node_index, value=pilot_id
                for node in INTERFACE.nodes:  # check if (other) pilot node is crossing gate
                    if node.index != pass_node_index:  # if node is for other pilot
                        if node.pass_crossing_flag:
                            if not profile_freqs:
                                profile_freqs = json.loads(getCurrentProfile().frequencies)
                            if profile_freqs["f"][node.index] != RHUtils.FREQUENCY_ID_NONE:  # node is enabled
                                if not node_pilot_dict:
                                    node_pilot_dict = dict(Database.HeatNode.query.with_entities(Database.HeatNode.node_index, Database.HeatNode.pilot_id). \
                                              filter(Database.HeatNode.heat_id==RACE.current_heat, Database.HeatNode.pilot_id!=Database.PILOT_ID_NONE).all())

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
                                                RACE.laps_winner_name = RACE.status_crossing
                                            else:  # if called from 'pass_record_callback()' then no more ties
                                                RACE.laps_winner_name = RACE.status_tied_str
                                            logger.info('check_most_laps_win waiting for crossing, Node {0}'.\
                                                                                  format(node.index+1))
                                            return

            # if race currently tied and more than one team at max_lap_count
            if RACE.laps_winner_name is RACE.status_tied_str and num_max_lap > 1:
                if pass_node_index < 0:  # if called from 'check_race_time_expired()'
                    logger.debug('check_most_laps_win race is tied num_max_lap={0} max_lap_count={1}'.format(num_max_lap, max_lap_count))
                    return
                else:  # if called from 'pass_record_callback()'
                    if max_lap_count < RACE.winning_lap_id:  # if no team has reached winning lap count
                        logger.debug('check_most_laps_win race tied (not winning lap) max_lap_count={0}, winning_lap_id={1}'.format(max_lap_count, RACE.winning_lap_id))
                        return

            RACE.laps_winner_name = win_name  # indicate a team has won
            check_emit_team_racing_status(t_laps_dict)
            logger.info('check_most_laps_win result: Winner is team {0}'.format(RACE.laps_winner_name))
            logger.debug('check_most_laps_win winning lap: {0}'.format(win_item))
            emit_phonetic_text('Race done, winner is team ' + RACE.laps_winner_name, 'race_winner')

        else:    # if no team looks like the winner
            RACE.laps_winner_name = RACE.status_tied_str  # indicate status tied
            RACE.winning_lap_id = max_lap_count + 1 if max_lap_count >= 0 else 1
            logger.debug('check_most_laps_win race tied (no winner yet) max_lap_count={0}, winning_lap_id={1}'.format(max_lap_count, RACE.winning_lap_id))

    else:  # not team racing mode

        pilots_list = []  # (lap_id, lap_time_stamp, pilot_id, node)
        max_lap_id = 0
        num_max_lap = 0
        profile_freqs = json.loads(getCurrentProfile().frequencies)
                                  # dict for current heat with key=node_index, value=pilot_id
        node_pilot_dict = dict(Database.HeatNode.query.with_entities(Database.HeatNode.node_index, Database.HeatNode.pilot_id). \
                          filter(Database.HeatNode.heat_id==RACE.current_heat, Database.HeatNode.pilot_id!=Database.PILOT_ID_NONE).all())

        for node in INTERFACE.nodes:  # load per-pilot data into 'pilots_list'
            if profile_freqs["f"][node.index] != RHUtils.FREQUENCY_ID_NONE:
                pilot_id = node_pilot_dict.get(node.index)
                if pilot_id:
                    lap_count = max(0, len(RACE.get_active_laps()[node.index]) - 1)
                    if lap_count > 0:
                        lap_data = filter(lambda lap : lap['lap_number']==lap_count, RACE.get_active_laps()[node.index])

                        if lap_data:
                            pilots_list.append((lap_count, lap_data[0]['lap_time_stamp'], pilot_id, node))
                            logger.debug('check_most_laps_win pilots_list.append lap_count={0} pilot_id={1}, node.index={2}'.\
                                        format(lap_count, pilot_id, node.index))
                            if lap_count > max_lap_id:
                                max_lap_id = lap_count
                                num_max_lap = 1
                            elif lap_count == max_lap_id:
                                num_max_lap += 1  # count number of nodes at max lap
        logger.debug('check_most_laps_win pass_node_index={0} max_lap={1}, num_max_lap={2}'.\
                    format(pass_node_index, max_lap_id, num_max_lap))

        if max_lap_id <= 0:  # if no laps then bail out
            RACE.laps_winner_name = RACE.status_tied_str  # indicate status tied
            RACE.winning_lap_id = 1
            if pass_node_index < 0:  # if called from 'check_race_time_expired()'
                emit_team_racing_status(RACE.laps_winner_name)
                emit_phonetic_text('Race tied', 'race_winner')
            return

        # if any (other) pilot is in the process of crossing the gate and within one lap of
        #  winning then bail out (and wait for next 'pass_record_callback()' event)
        pass_node_lap_id = -1
        for item in pilots_list:
            logger.debug('check_most_laps_win check crossing, item_index={0}, item.crossing_flag={1}'.\
                         format(item[3].index, item[3].pass_crossing_flag))
            if item[3].index != pass_node_index:  # if node is for other pilot
                if item[3].pass_crossing_flag and item[0] >= max_lap_id - 1:
                    # if called from 'check_race_time_expired()' then allow race tied after crossing
                    if pass_node_index < 0:
                        RACE.laps_winner_name = RACE.status_crossing
                    else:  # if called from 'pass_record_callback()' then no more ties
                        RACE.laps_winner_name = RACE.status_tied_str
                    logger.info('check_most_laps_win waiting for crossing, Node {0}'.format(item[3].index+1))
                    return
            else:
                pass_node_lap_id = item[0]  # save 'lap_id' for node/pilot that caused current lap pass

        # if race currently tied and called from 'pass_record_callback()' and current-pass pilot
        #  has not reached winning lap then bail out so pass will not stop a tied race in progress
        if RACE.laps_winner_name is RACE.status_tied_str and pass_node_index >= 0 and \
                pass_node_lap_id < RACE.winning_lap_id:
            logger.debug('check_most_laps_win pilot not at winning lap, pass_node_index={0}, winning_lap_id={1}'.\
                         format(pass_node_index, RACE.winning_lap_id))
            return

        # check for pilots with max laps; if more than one then select one with
        #  earliest lap time (if called from 'pass_record_callback()' fn) or
        #  indicate status tied (if called from 'check_race_time_expired()' fn)
        win_pilot_id = -1
        win_lap_tstamp = 0
        logger.debug('check_most_laps_win check max laps, pass_node_index={0}, max_lap_id={1}, laps_winner_name={2}'.\
                format(pass_node_index, max_lap_id, RACE.laps_winner_name))
        for item in pilots_list:
            if item[0] == max_lap_id:
                logger.debug('check_most_laps_win check max laps checking: pilot_id={0}, lap_tstamp={1}'.\
                        format(item[2], item[1]))
                if win_pilot_id < 0:  # this is first one so far at max_lap
                    win_pilot_id = item[2]
                    win_lap_tstamp = item[1]
                else:  # other pilots found at max_lap
                             # if called from 'pass_record_callback()' and not waiting for crossing
                    if pass_node_index >= 0 and RACE.laps_winner_name is not RACE.status_crossing:
                        if item[1] < win_lap_tstamp:  # this pilot has earlier lap time
                            win_pilot_id = item[2]
                            win_lap_tstamp = item[1]
                    else:  # called from 'check_race_time_expired()' or was waiting for crossing
                        if RACE.laps_winner_name is not RACE.status_tied_str:
                            logger.debug('check_most_laps_win check max laps, laps_winner_name was "{0}", setting to "{1}"'.\
                                        format(RACE.laps_winner_name, RACE.status_tied_str))
                            RACE.laps_winner_name = RACE.status_tied_str  # indicate status tied
                            RACE.winning_lap_id = max_lap_id + 1
                            emit_team_racing_status(RACE.laps_winner_name)
                            emit_phonetic_text('Race tied', 'race_winner')
                        else:
                            logger.debug('check_most_laps_win check max laps, laps_winner_name={0}'.\
                                        format(RACE.laps_winner_name))
                        return  # wait for next 'pass_record_callback()' event
        logger.debug('check_most_laps_win check max laps, win_pilot_id={0}, win_lap_tstamp={1}'.\
                        format(win_pilot_id, win_lap_tstamp))

        if win_pilot_id >= 0:
            win_callsign = Database.Pilot.query.filter_by(id=win_pilot_id).one().callsign
            RACE.laps_winner_name = win_callsign  # indicate a pilot has won
            emit_team_racing_status('Winner is ' + RACE.laps_winner_name)
            logger.info('check_most_laps_win result: Winner is {0}'.format(RACE.laps_winner_name))
            win_phon_name = Database.Pilot.query.filter_by(id=win_pilot_id).one().phonetic
            if len(win_phon_name) <= 0:  # if no phonetic then use callsign
                win_phon_name = win_callsign
            emit_phonetic_text('Race done, winner is ' + win_phon_name, 'race_winner')
        else:
            RACE.laps_winner_name = RACE.status_tied_str  # indicate status tied

def emit_phonetic_data(pilot_id, lap_id, lap_time, team_name, team_laps, **params):
    '''Emits phonetic data.'''
    raw_time = lap_time
    phonetic_time = RHUtils.phonetictime_format(lap_time)
    phonetic_name = Database.Pilot.query.get(pilot_id).phonetic
    callsign = Database.Pilot.query.get(pilot_id).callsign
    pilot_id = Database.Pilot.query.get(pilot_id).id
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
    Events.trigger(Evt.RACE_FIRST_PASS, {
        'node_index': node_idx,
        })

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

def emit_callouts():
    callouts = Options.get('voiceCallouts')
    if callouts:
        emit('callouts', json.loads(callouts))

def emit_imdtabler_page(**params):
    '''Emits IMDTabler page, using current profile frequencies.'''
    if Use_imdtabler_jar_flag:
        try:                          # get IMDTabler version string
            imdtabler_ver = subprocess.check_output( \
                                'java -jar ' + IMDTABLER_JAR_NAME + ' -v', shell=True).rstrip()
            profile_freqs = json.loads(getCurrentProfile().frequencies)
            fi_list = list(OrderedDict.fromkeys(profile_freqs['f'][:RACE.num_nodes]))  # remove duplicates
            fs_list = []
            for val in fi_list:  # convert list of integers to list of strings
                if val > 0:      # drop any zero entries
                    fs_list.append(str(val))
            emit_imdtabler_data(fs_list, imdtabler_ver)
        except Exception:
            logger.exception('emit_imdtabler_page exception')

def emit_imdtabler_data(fs_list, imdtabler_ver=None, **params):
    '''Emits IMDTabler data for given frequencies.'''
    try:
        imdtabler_data = None
        if len(fs_list) > 2:  # if 3+ then invoke jar; get response
            imdtabler_data = subprocess.check_output( \
                        'java -jar ' + IMDTABLER_JAR_NAME + ' -t ' + ' '.join(fs_list), shell=True)
    except Exception:
        imdtabler_data = None
        logger.exception('emit_imdtabler_data exception')
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
        profile_freqs = json.loads(getCurrentProfile().frequencies)
        imd_val = None
        fi_list = list(OrderedDict.fromkeys(profile_freqs['f'][:RACE.num_nodes]))  # remove duplicates
        fs_list = []
        for val in fi_list:  # convert list of integers to list of strings
            if val > 0:      # drop any zero entries
                fs_list.append(str(val))
        if len(fs_list) > 2:
            imd_val = subprocess.check_output(  # invoke jar; get response
                        'java -jar ' + IMDTABLER_JAR_NAME + ' -r ' + ' '.join(fs_list), shell=True).rstrip()
    except Exception:
        imd_val = None
        logger.exception('emit_imdtabler_rating exception')
    emit_payload = {
            'imd_rating': imd_val
        }
    SOCKET_IO.emit('imdtabler_rating', emit_payload)

def emit_vrx_list(*args, **params):
    ''' get list of connected VRx devices '''
    if vrx_controller:
        # if vrx_controller.has_connection:
            vrx_list = {}
            for vrx in vrx_controller.rx_data:
                vrx_list[vrx] = vrx_controller.rx_data[vrx]

            emit_payload = {
                'enabled': True,
                'connection': True,
                'vrx': vrx_list
            }
        # else:
            # emit_payload = {
            #     'enabled': True,
            #     'connection': False,
            # }
    else:
        emit_payload = {
            'enabled': False,
            'connection': False
        }

    if ('nobroadcast' in params):
        emit('vrx_list', emit_payload)
    else:
        SOCKET_IO.emit('vrx_list', emit_payload)

@SOCKET_IO.on('set_vrx_node')
def set_vrx_node(data):
    vrx_id = data['vrx_id']
    node = data['node']

    if vrx_controller:
        vrx_controller.set_node_number(serial_num=vrx_id, desired_node_num=node)
        logger.info("Set VRx {0} to node {1}".format(vrx_id, node))
    else:
        logger.error("Can't set VRx {0} to node {1}: Controller unavailable".format(vrx_id, node))

#
# Program Functions
#

def heartbeat_thread_function():
    '''Allow time for connection handshake to terminate before emitting data'''
    gevent.sleep(0.010)

    '''Emits current rssi data.'''
    while True:
        try:
            global RACE
            node_data = INTERFACE.get_heartbeat_json()

            SOCKET_IO.emit('heartbeat', node_data)
            heartbeat_thread_function.iter_tracker += 1

            # check if race timer is finished
            if RACE.timer_running:
                check_race_time_expired()

            # update displayed IMD rating after freqs changed:
            if heartbeat_thread_function.imdtabler_flag and \
                    (heartbeat_thread_function.iter_tracker % HEARTBEAT_DATA_RATE_FACTOR) == 0:
                heartbeat_thread_function.imdtabler_flag = False
                emit_imdtabler_rating()

            # emit rest of node data, but less often:
            if (heartbeat_thread_function.iter_tracker % (4*HEARTBEAT_DATA_RATE_FACTOR)) == 0:
                emit_node_data()

            # emit cluster status less often:
            if (heartbeat_thread_function.iter_tracker % (4*HEARTBEAT_DATA_RATE_FACTOR)) == (2*HEARTBEAT_DATA_RATE_FACTOR):
                CLUSTER.emitStatus()

            # collect vrx lock status
            if (heartbeat_thread_function.iter_tracker % (10*HEARTBEAT_DATA_RATE_FACTOR)) == 0:
                if vrx_controller:
                    # if vrx_controller.has_connection
                    vrx_controller.get_node_lock_status()
                    vrx_controller.request_variable_status()

            if (heartbeat_thread_function.iter_tracker % (10*HEARTBEAT_DATA_RATE_FACTOR)) == 4:
                # emit display status with offset
                if vrx_controller:
                    emit_vrx_list()

            # emit environment data less often:
            if (heartbeat_thread_function.iter_tracker % (20*HEARTBEAT_DATA_RATE_FACTOR)) == 0:
                INTERFACE.update_environmental_data()
                emit_environmental_data()

            time_now = monotonic()

            # check if race is to be started
            if RACE.scheduled:
                if time_now > RACE.scheduled_time:
                    on_stage_race()
                    RACE.scheduled = False

            # if any comm errors then log them (at defined intervals; faster if debug mode)
            if time_now > heartbeat_thread_function.last_error_rep_time + \
                        (ERROR_REPORT_INTERVAL_SECS if not Config.GENERAL['DEBUG'] \
                        else ERROR_REPORT_INTERVAL_SECS/10):
                heartbeat_thread_function.last_error_rep_time = time_now
                if INTERFACE.get_intf_total_error_count() > 0:
                    logger.info(INTERFACE.get_intf_error_report_str())

            gevent.sleep(0.500/HEARTBEAT_DATA_RATE_FACTOR)

        except KeyboardInterrupt:
            logger.info("Heartbeat thread terminated by keyboard interrupt")
            raise
        except SystemExit:
            raise
        except Exception:
            logger.exception('Exception in Heartbeat thread loop')
            gevent.sleep(0.500)

# declare/initialize variables for heartbeat functions
heartbeat_thread_function.iter_tracker = 0
heartbeat_thread_function.imdtabler_flag = False
heartbeat_thread_function.last_error_rep_time = monotonic()

def ms_from_race_start():
    '''Return milliseconds since race start.'''
    delta_time = monotonic() - RACE.start_time_monotonic
    milli_sec = delta_time * 1000.0
    return milli_sec

def ms_to_race_start():
    '''Return milliseconds since race start.'''
    if RACE.scheduled:
        delta_time = monotonic() - RACE.scheduled_time
        milli_sec = delta_time * 1000.0
        return milli_sec
    else:
        return None

def ms_from_program_start():
    '''Returns the elapsed milliseconds since the start of the program.'''
    delta_time = monotonic() - PROGRAM_START
    milli_sec = delta_time * 1000.0
    return milli_sec

def check_race_time_expired():
    race_format = getCurrentRaceFormat()
    if race_format and race_format.race_mode == 0: # count down
        if monotonic() >= RACE.start_time_monotonic + race_format.race_time_sec:
            RACE.timer_running = False # indicate race timer no longer running
            Events.trigger(Evt.RACE_FINISH)
            if race_format.win_condition == WinCondition.MOST_LAPS:  # Most Laps Wins Enabled
                check_most_laps_win()  # check if pilot or team has most laps for win

def pass_record_callback(node, lap_timestamp_absolute, source):
    '''Handles pass records from the nodes.'''

    logger.debug('Raw pass record: Node: {0}, MS Since Lap: {1}'.format(node.index+1, lap_timestamp_absolute))
    node.pass_crossing_flag = False  # clear the "synchronized" version of the crossing flag
    node.debug_pass_count += 1
    emit_node_data() # For updated triggers and peaks

    global RACE
    profile_freqs = json.loads(getCurrentProfile().frequencies)
    if profile_freqs["f"][node.index] != RHUtils.FREQUENCY_ID_NONE:
        # always count laps if race is running, otherwise test if lap should have counted before race end (RACE.duration_ms is invalid while race is in progress)
        if RACE.race_status is RaceStatus.RACING \
            or (RACE.race_status is RaceStatus.DONE and \
                lap_timestamp_absolute < RACE.end_time):

            # Get the current pilot id on the node
            pilot_id = Database.HeatNode.query.filter_by( \
                heat_id=RACE.current_heat, node_index=node.index).one().pilot_id

            # reject passes before race start and with disabled (no-pilot) nodes
            if pilot_id != Database.PILOT_ID_NONE:
                if lap_timestamp_absolute >= RACE.start_time_monotonic:

                    lap_time_stamp = (lap_timestamp_absolute - RACE.start_time_monotonic)
                    lap_time_stamp *= 1000 # store as milliseconds

                    lap_number = len(RACE.get_active_laps()[node.index])

                    if lap_number: # This is a normal completed lap
                        # Find the time stamp of the last lap completed
                        last_lap_time_stamp = RACE.get_active_laps()[node.index][-1]['lap_time_stamp']

                        # New lap time is the difference between the current time stamp and the last
                        lap_time = lap_time_stamp - last_lap_time_stamp

                    else: # No previous laps, this is the first pass
                        # Lap zero represents the time from the launch pad to flying through the gate
                        lap_time = lap_time_stamp
                        node.first_cross_flag = True  # indicate first crossing completed

                    race_format = getCurrentRaceFormat()
                    min_lap = int(Options.get("MinLapSec"))
                    min_lap_behavior = int(Options.get("MinLapBehavior"))

                    lap_ok_flag = True
                    if lap_number != 0:  # if initial lap then always accept and don't check lap time; else:
                        if lap_time < (min_lap * 1000):  # if lap time less than minimum
                            node.under_min_lap_count += 1
                            logger.info('Pass record under lap minimum ({3}): Node={0}, Lap={1}, LapTime={2}, Count={4}' \
                                       .format(node.index+1, lap_number, RHUtils.time_format(lap_time), min_lap, node.under_min_lap_count))
                            if min_lap_behavior != 0:  # if behavior is 'Discard New Short Laps'
                                lap_ok_flag = False

                    if lap_ok_flag:
                        SOCKET_IO.emit('pass_record', {
                            'node': node.index,
                            'frequency': node.frequency,
                            'timestamp': lap_time_stamp + monotonic_to_milliseconds(RACE.start_time_monotonic)
                        })
                        # Add the new lap to the database
                        RACE.node_laps[node.index].append({
                            'lap_number': lap_number,
                            'lap_time_stamp': lap_time_stamp,
                            'lap_time': lap_time,
                            'lap_time_formatted': RHUtils.time_format(lap_time),
                            'source': source,
                            'deleted': False
                        })

                        RACE.results = Results.calc_leaderboard(DB, current_race=RACE, current_profile=getCurrentProfile())
                        RACE.cacheStatus = Results.CacheStatus.VALID

                        Events.trigger(Evt.RACE_LAP_RECORDED, {
                            'race': RACE,
                            'node_index': node.index,
                            })

                        #logger.info('Pass record: Node: {0}, Lap: {1}, Lap time: {2}' \
                        #    .format(node.index+1, lap_number, RHUtils.time_format(lap_time)))
                        emit_current_laps() # update all laps on the race page
                        emit_current_leaderboard() # update leaderboard

                        if race_format.team_racing_mode: # team racing mode enabled

                            # if win condition is first-to-x-laps and x is valid
                            #  then check if a team has enough laps to win
                            if race_format.win_condition == WinCondition.FIRST_TO_LAP_X and race_format.number_laps_win > 0:
                                t_laps_dict, team_name, pilot_team_dict = \
                                    get_team_laps_info(pilot_id, race_format.number_laps_win)
                                team_laps = t_laps_dict[team_name][0]
                                check_team_laps_win(t_laps_dict, race_format.number_laps_win, pilot_team_dict, node.index)
                            else:
                                t_laps_dict, team_name, pilot_team_dict = get_team_laps_info(pilot_id, RACE.winning_lap_id)
                                team_laps = t_laps_dict[team_name][0]
                            check_emit_team_racing_status(t_laps_dict)

                            if lap_number > 0:   # send phonetic data to be spoken
                                emit_phonetic_data(pilot_id, lap_number, lap_time, team_name, team_laps)

                                # if Most Laps Wins race is tied then check for winner
                                if race_format.win_condition == WinCondition.MOST_LAPS:
                                    if RACE.laps_winner_name is RACE.status_tied_str or \
                                                RACE.laps_winner_name is RACE.status_crossing:
                                        check_most_laps_win(node.index, t_laps_dict, pilot_team_dict)

                                # if a team has won the race and this is the winning lap
                                elif RACE.laps_winner_name is not None and \
                                            team_name == RACE.laps_winner_name and \
                                            team_laps >= race_format.number_laps_win:
                                    emit_phonetic_text('Winner is team ' + RACE.laps_winner_name, 'race_winner')
                            elif lap_number == 0:
                                emit_first_pass_registered(node.index) # play first-pass sound

                        else:  # not team racing mode
                            if lap_number > 0:
                                                # send phonetic data to be spoken
                                if race_format.win_condition != WinCondition.FIRST_TO_LAP_X or race_format.number_laps_win <= 0:
                                    emit_phonetic_data(pilot_id, lap_number, lap_time, None, None)

                                                     # if Most Laps Wins race is tied then check for winner
                                    if race_format.win_condition == WinCondition.MOST_LAPS:
                                        if RACE.laps_winner_name is RACE.status_tied_str or \
                                                    RACE.laps_winner_name is RACE.status_crossing:
                                            check_most_laps_win(node.index)

                                else:           # need to check if any pilot has enough laps to win
                                    if race_format.win_condition == WinCondition.FIRST_TO_LAP_X:
                                        win_pilot_id = check_pilot_laps_win(node.index, race_format.number_laps_win)
                                        if win_pilot_id >= 0:  # a pilot has won the race
                                            win_callsign = Database.Pilot.query.get(win_pilot_id).callsign
                                            emit_team_racing_status('Winner is ' + win_callsign)
                                            emit_phonetic_data(pilot_id, lap_number, lap_time, None, None)

                                            if RACE.laps_winner_name is None:
                                                    # a pilot has won the race and has not yet been announced
                                                win_phon_name = Database.Pilot.query.get(win_pilot_id).phonetic
                                                if len(win_phon_name) <= 0:  # if no phonetic then use callsign
                                                    win_phon_name = win_callsign
                                                RACE.laps_winner_name = win_callsign  # call out winner (once)
                                                emit_phonetic_text('Winner is ' + win_phon_name, 'race_winner')

                                        else:  # no pilot has won the race; send phonetic data to be spoken
                                            emit_phonetic_data(pilot_id, lap_number, lap_time, None, None)
                                    else:  # other win conditions
                                            emit_phonetic_data(pilot_id, lap_number, lap_time, None, None)
                            elif lap_number == 0:
                                emit_first_pass_registered(node.index) # play first-pass sound
                    else:
                        RACE.node_laps[node.index].append({
                            'lap_number': lap_number,
                            'lap_time_stamp': lap_time_stamp,
                            'lap_time': lap_time,
                            'lap_time_formatted': RHUtils.time_format(lap_time),
                            'source': source,
                            'deleted': True
                        })
                else:
                    logger.debug('Pass record dismissed: Node: {0}, Race not started' \
                        .format(node.index+1))
            else:
                logger.debug('Pass record dismissed: Node: {0}, Pilot not defined' \
                    .format(node.index+1))
    else:
        logger.debug('Pass record dismissed: Node: {0}, Frequency not defined' \
            .format(node.index+1))

def new_enter_or_exit_at_callback(node, is_enter_at_flag):
    if is_enter_at_flag:
        logger.info('Finished capture of enter-at level for node {0}, level={1}, count={2}'.format(node.index+1, node.enter_at_level, node.cap_enter_at_count))
        on_set_enter_at_level({
            'node': node.index,
            'enter_at_level': node.enter_at_level
        })
        emit_enter_at_level(node)
    else:
        logger.info('Finished capture of exit-at level for node {0}, level={1}, count={2}'.format(node.index+1, node.exit_at_level, node.cap_exit_at_count))
        on_set_exit_at_level({
            'node': node.index,
            'exit_at_level': node.exit_at_level
        })
        emit_exit_at_level(node)

def node_crossing_callback(node):
    emit_node_crossing_change(node)
    # handle LED gate-status indicators:

    if led_manager.isEnabled() and RACE.race_status == RaceStatus.RACING:  # if race is in progress
        # if pilot assigned to node and first crossing is complete
        if node.current_pilot_id != Database.PILOT_ID_NONE and node.first_cross_flag:
            # first crossing has happened; if 'enter' then show indicator,
            #  if first event is 'exit' then ignore (because will be end of first crossing)
            if node.crossing_flag:
                Events.trigger(Evt.CROSSING_ENTER, {
                    'nodeIndex': node.index,
                    'color': hexToColor(Options.get('colorNode_' + str(node.index), '#ffffff'))
                    })
                node.show_crossing_flag = True
            else:
                if node.show_crossing_flag:
                    Events.trigger(Evt.CROSSING_EXIT, {
                        'nodeIndex': node.index,
                        'color': hexToColor(Options.get('colorNode_' + str(node.index), '#ffffff'))
                        })
                else:
                    node.show_crossing_flag = True

def default_frequencies():
    '''Set node frequencies, R1367 for 4, IMD6C+ for 5+.'''
    if RACE.num_nodes < 5:
        freqs = [5658, 5732, 5843, 5880, RHUtils.FREQUENCY_ID_NONE, RHUtils.FREQUENCY_ID_NONE, RHUtils.FREQUENCY_ID_NONE, RHUtils.FREQUENCY_ID_NONE]
    else:
        freqs = [5658, 5695, 5760, 5800, 5880, 5917, RHUtils.FREQUENCY_ID_NONE, RHUtils.FREQUENCY_ID_NONE]
    return freqs

def assign_frequencies():
    '''Assign frequencies to nodes'''
    profile = getCurrentProfile()
    freqs = json.loads(profile.frequencies)

    for idx in range(RACE.num_nodes):
        INTERFACE.set_frequency(idx, freqs["f"][idx])
        Events.trigger(Evt.FREQUENCY_SET, {
            'nodeIndex': idx,
            'frequency': freqs["f"][idx],
            })

        logger.info('Frequency set: Node {0} Frequency {1}'.format(idx+1, freqs["f"][idx]))
    DB.session.commit()

def emit_current_log_file_to_socket():
    if Current_log_path_name:
        try:
            with io.open(Current_log_path_name, 'r') as f:
                SOCKET_IO.emit("hardware_log_init", f.read())
        except Exception:
            logger.exception("Error sending current log file to socket")
    log.start_socket_forward_handler()

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
    Events.trigger(Evt.DATABASE_INITIALIZE)
    logger.info('Database initialized')

def db_reset():
    '''Resets database.'''
    db_reset_pilots()
    db_reset_heats()
    db_reset_current_laps()
    db_reset_saved_races()
    db_reset_profile()
    db_reset_race_formats()
    assign_frequencies()
    logger.info('Database reset')

def db_reset_pilots():
    '''Resets database pilots to default.'''
    DB.session.query(Database.Pilot).delete()
    for node in range(RACE.num_nodes):
        DB.session.add(Database.Pilot(callsign='Callsign {0}'.format(node+1), \
            name='Pilot {0} Name'.format(node+1), team=DEF_TEAM_NAME, phonetic=''))
    DB.session.commit()
    logger.info('Database pilots reset')

def db_reset_heats():
    '''Resets database heats to default.'''
    DB.session.query(Database.Heat).delete()
    DB.session.query(Database.HeatNode).delete()
    on_add_heat()
    DB.session.commit()
    RACE.current_heat = 1
    logger.info('Database heats reset')

def db_reset_classes():
    '''Resets database race classes to default.'''
    DB.session.query(Database.RaceClass).delete()
    DB.session.commit()
    logger.info('Database race classes reset')

def db_reset_current_laps():
    '''Resets database current laps to default.'''
    RACE.node_laps = {}
    for idx in range(RACE.num_nodes):
        RACE.node_laps[idx] = []

    RACE.cacheStatus = Results.CacheStatus.INVALID
    logger.debug('Database current laps reset')

def db_reset_saved_races():
    '''Resets database saved races to default.'''
    DB.session.query(Database.SavedRaceMeta).delete()
    DB.session.query(Database.SavedPilotRace).delete()
    DB.session.query(Database.SavedRaceLap).delete()
    DB.session.commit()
    logger.info('Database saved races reset')

def db_reset_profile():
    '''Set default profile'''
    DB.session.query(Database.Profiles).delete()

    new_freqs = {}
    new_freqs["f"] = default_frequencies()

    template = {}
    template["v"] = [None, None, None, None, None, None, None, None]

    DB.session.add(Database.Profiles(name=__("Default"),
                             frequencies = json.dumps(new_freqs),
                             enter_ats = json.dumps(template),
                             exit_ats = json.dumps(template)))
    DB.session.commit()
    Options.set("currentProfile", 1)
    logger.info("Database set default profiles")

def db_reset_race_formats():
    DB.session.query(Database.RaceFormat).delete()
    DB.session.add(Database.RaceFormat(name=__("MultiGP Standard"),
                             race_mode=0,
                             race_time_sec=120,
                             start_delay_min=2,
                             start_delay_max=5,
                             staging_tones=2,
                             number_laps_win=0,
                             win_condition=WinCondition.MOST_LAPS,
                             team_racing_mode=False))
    DB.session.add(Database.RaceFormat(name=__("Whoop Sprint"),
                             race_mode=0,
                             race_time_sec=90,
                             start_delay_min=2,
                             start_delay_max=5,
                             staging_tones=2,
                             number_laps_win=0,
                             win_condition=WinCondition.MOST_LAPS,
                             team_racing_mode=False))
    DB.session.add(Database.RaceFormat(name=__("Limited Class"),
                             race_mode=0,
                             race_time_sec=210,
                             start_delay_min=2,
                             start_delay_max=5,
                             staging_tones=2,
                             number_laps_win=0,
                             win_condition=WinCondition.MOST_LAPS,
                             team_racing_mode=False))
    DB.session.add(Database.RaceFormat(name=__("First to 3 Laps"),
                             race_mode=1,
                             race_time_sec=0,
                             start_delay_min=2,
                             start_delay_max=5,
                             staging_tones=2,
                             number_laps_win=3,
                             win_condition=WinCondition.FIRST_TO_LAP_X,
                             team_racing_mode=False))
    DB.session.add(Database.RaceFormat(name=__("Open Practice"),
                             race_mode=1,
                             race_time_sec=0,
                             start_delay_min=0,
                             start_delay_max=0,
                             staging_tones=0,
                             number_laps_win=0,
                             win_condition=WinCondition.NONE,
                             team_racing_mode=False))
    DB.session.add(Database.RaceFormat(name=__("Team / Most Laps Wins"),
                             race_mode=0,
                             race_time_sec=120,
                             start_delay_min=2,
                             start_delay_max=5,
                             staging_tones=2,
                             number_laps_win=0,
                             win_condition=WinCondition.MOST_LAPS,
                             team_racing_mode=True))
    DB.session.add(Database.RaceFormat(name=__("Team / First to 7 Laps"),
                             race_mode=0,
                             race_time_sec=120,
                             start_delay_min=2,
                             start_delay_max=5,
                             staging_tones=2,
                             number_laps_win=7,
                             win_condition=WinCondition.FIRST_TO_LAP_X,
                             team_racing_mode=True))
    DB.session.commit()
    setCurrentRaceFormat(Database.RaceFormat.query.first())
    logger.info("Database reset race formats")

def db_reset_options_defaults():
    DB.session.query(Database.GlobalSettings).delete()
    Options.set("server_api", SERVER_API)
    # group identifiers
    Options.set("timerName", __("RotorHazard"))
    Options.set("timerLogo", "")
    # group colors
    Options.set("hue_0", "212")
    Options.set("sat_0", "55")
    Options.set("lum_0_low", "29.2")
    Options.set("lum_0_high", "46.7")
    Options.set("contrast_0_low", "#ffffff")
    Options.set("contrast_0_high", "#ffffff")

    Options.set("hue_1", "25")
    Options.set("sat_1", "85.3")
    Options.set("lum_1_low", "37.6")
    Options.set("lum_1_high", "54.5")
    Options.set("contrast_1_low", "#ffffff")
    Options.set("contrast_1_high", "#000000")
    # timer state
    Options.set("currentLanguage", "")
    Options.set("currentProfile", "1")
    setCurrentRaceFormat(Database.RaceFormat.query.first())
    Options.set("calibrationMode", "1")
    # minimum lap
    Options.set("MinLapSec", "10")
    Options.set("MinLapBehavior", "0")
    # event information
    Options.set("eventName", __("FPV Race"))
    Options.set("eventDescription", "")
    # LED settings
    Options.set("ledBrightness", "32")
    # LED colors
    Options.set("colorNode_0", "#001fff")
    Options.set("colorNode_1", "#ff3f00")
    Options.set("colorNode_2", "#7fff00")
    Options.set("colorNode_3", "#ffff00")
    Options.set("colorNode_4", "#7f00ff")
    Options.set("colorNode_5", "#ff007f")
    Options.set("colorNode_6", "#3fff3f")
    Options.set("colorNode_7", "#00bfff")
    # Event results cache
    Options.set("eventResults_cacheStatus", Results.CacheStatus.INVALID)

    logger.info("Reset global settings")

def backup_db_file(copy_flag):
    DB.session.close()
    try:     # generate timestamp from last-modified time of database file
        time_str = datetime.fromtimestamp(os.stat(DB_FILE_NAME).st_mtime).strftime('%Y%m%d_%H%M%S')
    except:  # if error then use 'now' timestamp
        time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    try:
        (dbname, dbext) = os.path.splitext(DB_FILE_NAME)
        bkp_name = DB_BKP_DIR_NAME + '/' + dbname + '_' + time_str + dbext
        if not os.path.exists(DB_BKP_DIR_NAME):
            os.makedirs(DB_BKP_DIR_NAME)
        if os.path.isfile(bkp_name):  # if target file exists then use 'now' timestamp
            time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            bkp_name = DB_BKP_DIR_NAME + '/' + dbname + '_' + time_str + dbext
        if copy_flag:
            shutil.copy2(DB_FILE_NAME, bkp_name);
            logger.info('Copied database file to:  ' + bkp_name)
        else:
            os.renames(DB_FILE_NAME, bkp_name);
            logger.info('Moved old database file to:  ' + bkp_name)
    except Exception:
        logger.exception('Error backing up database file')
    return bkp_name

def get_legacy_table_data(metadata, table_name, filter_crit=None, filter_value=None):
    try:
        table = Table(table_name, metadata, autoload=True)
        if filter_crit is None:
            return table.select().execute().fetchall()
        return table.select().execute().filter(filter_crit==filter_value).fetchall()
    except Exception as ex:
        logger.warn('Unable to read "{0}" table from previous database: {1}'.format(table_name, ex))

def restore_table(class_type, table_query_data, **kwargs):
    if table_query_data:
        try:
            for row_data in table_query_data:
                if (class_type is not Database.Pilot) or getattr(row_data, 'callsign', '') != '-' or \
                                              getattr(row_data, 'name', '') != '-None-':
                    if 'id' in class_type.__table__.columns.keys() and \
                        'id' in row_data.keys():
                        db_update = class_type.query.filter(getattr(class_type,'id')==row_data['id']).first()
                    else:
                        db_update = None

                    if db_update is None:
                        new_data = class_type()
                        for col in class_type.__table__.columns.keys():
                            if col in row_data.keys():
                                if col != 'id':
                                    setattr(new_data, col, row_data[col])
                            else:
                                if col != 'id':
                                    setattr(new_data, col, kwargs['defaults'][col])

                        #logger.info('DEBUG row_data add:  ' + str(getattr(new_data, match_name)))
                        DB.session.add(new_data)
                    else:
                        #logger.info('DEBUG row_data update:  ' + str(getattr(row_data, match_name)))
                        for col in class_type.__table__.columns.keys():
                            if col in row_data.keys():
                                setattr(db_update, col, row_data[col])
                            else:
                                if col != 'id':
                                    setattr(db_update, col, kwargs['defaults'][col])

                    DB.session.flush()
            logger.info('Database table "{0}" restored'.format(class_type.__name__))
        except Exception as ex:
            logger.warn('Error restoring "{0}" table from previous database: {1}'.format(class_type.__name__, ex))
            logger.debug(traceback.format_exc())

def recover_database():
    try:
        logger.info('Recovering data from previous database')

        # load file directly
        engine = create_engine('sqlite:///%s' % DB_FILE_NAME, convert_unicode=True)
        metadata = MetaData(bind=engine)
        pilot_query_data = get_legacy_table_data(metadata, 'pilot')
        heat_query_data = get_legacy_table_data(metadata, 'heat')
        heatnode_query_data = get_legacy_table_data(metadata, 'heatnode')
        raceFormat_query_data = get_legacy_table_data(metadata, 'race_format')
        profiles_query_data = get_legacy_table_data(metadata, 'profiles')
        raceClass_query_data = get_legacy_table_data(metadata, 'race_class')
        raceMeta_query_data = get_legacy_table_data(metadata, 'saved_race_meta')
        racePilot_query_data = get_legacy_table_data(metadata, 'saved_pilot_race')
        raceLap_query_data = get_legacy_table_data(metadata, 'saved_race_lap')

        engine.dispose() # close connection after loading

        migrate_db_api = int(Options.get('server_api'))

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
            "calibrationMode",
            "MinLapSec",
            "MinLapBehavior",
            "ledBrightness",
            "colorNode_0",
            "colorNode_1",
            "colorNode_2",
            "colorNode_3",
            "colorNode_4",
            "colorNode_5",
            "colorNode_6",
            "colorNode_7",
            "osd_lapHeader",
            "osd_positionHeader"
        ]
        carryOver = {}
        for opt in carryoverOpts:
            val = Options.get(opt, None)
            if val is not None:
                carryOver[opt] = val

        # RSSI reduced by half for 2.0.0
        if migrate_db_api < 23:
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
        logger.warn('Error reading data from previous database:  ' + str(ex))

    backup_db_file(False)  # rename and move DB file
    db_init()

    # primary data recovery
    try:
        if pilot_query_data:
            DB.session.query(Database.Pilot).delete()
            restore_table(Database.Pilot, pilot_query_data, defaults={
                    'name': 'New Pilot',
                    'callsign': 'New Callsign',
                    'team': DEF_TEAM_NAME,
                    'phonetic': ''
                })

        if migrate_db_api < 27:
            # old heat DB structure; migrate node 0 to heat table

            # build list of heat meta
            heat_extracted_meta = []
            for row in heat_query_data:
                if row['node_index'] == 0:
                    heat_extracted_meta.append(row)

            restore_table(Database.Heat, heat_extracted_meta, defaults={
                    'class_id': Database.CLASS_ID_NONE,
                    'results': None,
                    'cacheStatus': Results.CacheStatus.INVALID
                })

            # extract pilots from hets and load into heatnode
            heatnode_extracted_data = []
            for row in heat_query_data:
                heatnode_row = {}
                heatnode_row['heat_id'] = int(row['heat_id'])
                heatnode_row['node_index'] = int(row['node_index'])
                heatnode_row['pilot_id'] = int(row['pilot_id'])
                heatnode_extracted_data.append(heatnode_row)

            DB.session.query(Database.HeatNode).delete()
            restore_table(Database.HeatNode, heatnode_extracted_data, defaults={
                    'pilot_id': Database.PILOT_ID_NONE
                })
        else:
            # current heat structure; use basic migration
            restore_table(Database.Heat, heat_query_data, defaults={
                    'class_id': Database.CLASS_ID_NONE,
                    'results': None,
                    'cacheStatus': Results.CacheStatus.INVALID
                })
            restore_table(Database.HeatNode, heatnode_query_data, defaults={
                    'pilot_id': Database.PILOT_ID_NONE
                })

        restore_table(Database.RaceFormat, raceFormat_query_data, defaults={
                'name': __("Migrated Format"),
                'race_mode': 0,
                'race_time_sec': 120,
                'start_delay_min': 2,
                'start_delay_max': 5,
                'staging_tones': 2,
                'number_laps_win': 0,
                'win_condition': WinCondition.MOST_LAPS,
                'team_racing_mode': False
            })
        restore_table(Database.Profiles, profiles_query_data, defaults={
                'name': __("Migrated Profile"),
                'frequencies': json.dumps(default_frequencies()),
                'enter_ats': json.dumps({'v': [None, None, None, None, None, None, None, None]}),
                'exit_ats': json.dumps({'v': [None, None, None, None, None, None, None, None]})
            })
        restore_table(Database.RaceClass, raceClass_query_data, defaults={
                'name': 'New class',
                'format_id': 0,
                'results': None,
                'cacheStatus': Results.CacheStatus.INVALID
            })

        for opt in carryOver:
            Options.set(opt, carryOver[opt])
        logger.info('UI Options restored')

    except Exception as ex:
        logger.warn('Error while writing data from previous database:  ' + str(ex))
        logger.debug(traceback.format_exc())

    # secondary data recovery

    try:
        if migrate_db_api < 23:
            # don't attempt to migrate race data older than 2.0
            pass
        else:
            restore_table(Database.SavedRaceMeta, raceMeta_query_data, defaults={
                'results': None,
                'cacheStatus': Results.CacheStatus.INVALID
            })
            restore_table(Database.SavedPilotRace, racePilot_query_data, defaults={
                'history_values': None,
                'history_times': None,
                'penalty_time': None,
                'penalty_desc': None,
                'enter_at': None,
                'exit_at': None
            })
            restore_table(Database.SavedRaceLap, raceLap_query_data, defaults={
                'source': None,
                'deleted': False
            })

    except Exception as ex:
        logger.warn('Error while writing data from previous database:  ' + str(ex))
        logger.debug(traceback.format_exc())

    DB.session.commit()

    Events.trigger(Evt.DATABASE_RECOVER)

def expand_heats():
    for heat_ids in Database.Heat.query.all():
        for node in range(RACE.num_nodes):
            heat_row = Database.HeatNode.query.filter_by(heat_id=heat_ids.id, node_index=node)
            if not heat_row.count():
                DB.session.add(Database.HeatNode(heat_id=heat_ids.id, node_index=node, pilot_id=Database.PILOT_ID_NONE))

    DB.session.commit()

def init_LED_effects():
    # start with defaults
    effects = {
        Evt.RACE_STAGE: "stripColorOrange2_1",
        Evt.RACE_START: "stripColorGreenSolid",
        Evt.RACE_FINISH: "stripColorWhite4_4",
        Evt.RACE_STOP: "stripColorRedSolid",
        Evt.LAPS_CLEAR: "clear",
        Evt.CROSSING_ENTER: "stripColorSolid",
        Evt.CROSSING_EXIT: "stripColor1_1_4s",
        Evt.STARTUP: "rainbowCycle",
        Evt.SHUTDOWN: "clear"
    }
    # update with DB values (if any)
    effect_opt = Options.get('ledEffects')
    if effect_opt:
        effects.update(json.loads(effect_opt))
    # set effects
    led_manager.setEventEffect("manualColor", "stripColor")
    for item in effects:
        led_manager.setEventEffect(item, effects[item])

def initVRxController():
    try:
        vrx_config = Config.VRX_CONTROL
        try:
            vrx_enabled = vrx_config["ENABLED"]
            if vrx_enabled:
                try:
                    from VRxController import VRxController
                except ImportError as e:
                    logger.error("VRxController unable to be imported")
                    logger.error(e)
                    return None
            else:
                logger.info('VRxController disabled by config option')
                return None
        except KeyError:
            logger.error('VRxController disabled: config needs "ENABLED" key.')
            return None
    except AttributeError:
        logger.info('VRxController disabled: No VRX_CONTROL config option')
        return None

    # If got through import success, create the VRxController object
    vrx_config = Config.VRX_CONTROL
    return VRxController(Events,
       vrx_config,
       [node.frequency for node in INTERFACE.nodes])

def killVRxController(*args):
    logger.info('Killing VRxController')
    vrx_controller = None

#
# Program Initialize
#

logger.info('Release: {0} / Server API: {1} / Latest Node API: {2}'.format(RELEASE_VERSION, SERVER_API, NODE_API_BEST))
idAndLogSystemInfo()

# log results of module initializations
Config.logInitResultMessage()
Language.logInitResultMessage()

# check if current log file owned by 'root' and change owner to 'pi' user if so
if Current_log_path_name and checkSetFileOwnerPi(Current_log_path_name):
    logger.debug("Changed log file owner from 'root' to 'pi' (file: '{0}')".format(Current_log_path_name))
logger.info("Using log file: {0}".format(Current_log_path_name))

interface_type = os.environ.get('RH_INTERFACE', 'RH')
try:
    interfaceModule = importlib.import_module(interface_type + 'Interface')
    INTERFACE = interfaceModule.get_hardware_interface(config=Config)
except (ImportError, RuntimeError, IOError) as ex:
    logger.info('Unable to initialize nodes via ' + interface_type + 'Interface:  ' + str(ex))
if not INTERFACE or not INTERFACE.nodes or len(INTERFACE.nodes) <= 0:
    if not Config.SERIAL_PORTS or len(Config.SERIAL_PORTS) <= 0:
        interfaceModule = importlib.import_module('MockInterface')
        INTERFACE = interfaceModule.get_hardware_interface(config=Config)
    else:
        try:
            importlib.import_module('serial')
            print 'Unable to initialize specified serial node(s): {0}'.format(Config.SERIAL_PORTS)
        except ImportError:
            print "Unable to import library for serial node(s) - is 'pyserial' installed?"
        sys.exit()

CLUSTER = Cluster()
hasMirrors = False
for index, slave_info in enumerate(Config.GENERAL['SLAVES']):
    if isinstance(slave_info, basestring):
        slave_info = {'address': slave_info, 'mode': Slave.TIMER_MODE}
    if 'timeout' not in slave_info:
        slave_info['timeout'] = Config.GENERAL['SLAVE_TIMEOUT']
    if 'mode' in slave_info and slave_info['mode'] == Slave.MIRROR_MODE:
        hasMirrors = True
    elif hasMirrors:
        print '** Mirror slaves must be last - ignoring remaining slave config **'
        break
    slave = Slave(index, slave_info)
    CLUSTER.addSlave(slave)

# set callback functions invoked by interface module
INTERFACE.pass_record_callback = pass_record_callback
INTERFACE.new_enter_or_exit_at_callback = new_enter_or_exit_at_callback
INTERFACE.node_crossing_callback = node_crossing_callback

# Save number of nodes found
RACE.num_nodes = len(INTERFACE.nodes)
if RACE.num_nodes == 0:
    logger.warning('*** WARNING: NO RECEIVER NODES FOUND ***')
else:
    logger.info('Number of nodes found: {0}'.format(RACE.num_nodes))

# Delay to get I2C addresses through interface class initialization
gevent.sleep(0.500)

# if no DB file then create it now (before "__()" fn used in 'buildServerInfo()')
db_inited_flag = False
if not os.path.exists(DB_FILE_NAME):
    logger.info('No database.db file found; creating initial database')
    db_init()
    db_inited_flag = True

# check if DB file owned by 'root' and change owner to 'pi' user if so
if checkSetFileOwnerPi(DB_FILE_NAME):
    logger.debug("Changed DB-file owner from 'root' to 'pi' (file: '{0}')".format(DB_FILE_NAME))

Options.primeGlobalsCache()

# collect server info for About panel
serverInfo = buildServerInfo()
if serverInfo['node_api_match'] is False:
    logger.info('** WARNING: Node API mismatch. **')

if RACE.num_nodes > 0:
    if serverInfo['node_api_lowest'] < NODE_API_SUPPORTED:
        logger.info('** WARNING: Node firmware is out of date and may not function properly **')
    elif serverInfo['node_api_lowest'] < NODE_API_BEST:
        logger.info('** NOTICE: Node firmware update is available **')
    elif serverInfo['node_api_lowest'] > NODE_API_BEST:
        logger.warn('** WARNING: Node firmware is newer than this server version supports **')

if not db_inited_flag:
    try:
        if int(Options.get('server_api')) < SERVER_API:
            logger.info('Old server API version; recovering database')
            recover_database()
        elif not Database.Heat.query.count():
            logger.info('Heats are empty; recovering database')
            recover_database()
        elif not Database.Profiles.query.count():
            logger.info('Profiles are empty; recovering database')
            recover_database()
        elif not Database.RaceFormat.query.count():
            logger.info('Formats are empty; recovering database')
            recover_database()
    except Exception as ex:
        logger.warn('Clearing all data after recovery failure:  ' + str(ex))
        db_reset()

# Expand heats (if number of nodes increases)
expand_heats()

# internal slave race format for LiveTime (needs to be created after initial DB setup)
global SLAVE_RACE_FORMAT
SLAVE_RACE_FORMAT = RHRaceFormat(name=__("Slave"),
                         race_mode=1,
                         race_time_sec=0,
                         start_delay_min=0,
                         start_delay_max=0,
                         staging_tones=0,
                         number_laps_win=0,
                         win_condition=WinCondition.NONE,
                         team_racing_mode=False)

# Import IMDTabler
if os.path.exists(IMDTABLER_JAR_NAME):  # if 'IMDTabler.jar' is available
    try:
        java_ver = subprocess.check_output('java -version', stderr=subprocess.STDOUT, shell=True)
        logger.debug('Found installed: ' + java_ver.split('\n')[0].strip())
    except:
        java_ver = None
        logger.info('Unable to find java; for IMDTabler functionality try:')
        logger.info('sudo apt-get install openjdk-8-jdk')
    if java_ver:
        try:
            imdtabler_ver = subprocess.check_output( \
                        'java -jar ' + IMDTABLER_JAR_NAME + ' -v', \
                        stderr=subprocess.STDOUT, shell=True).rstrip()
            Use_imdtabler_jar_flag = True  # indicate IMDTabler.jar available
            logger.debug('Found installed: ' + imdtabler_ver)
        except Exception:
            logger.exception('Error checking IMDTabler:  ')
else:
    logger.info('IMDTabler lib not found at: ' + IMDTABLER_JAR_NAME)

# Clear any current laps from the database on each program start
# DB session commit needed to prevent 'application context' errors
db_reset_current_laps()

# Send initial profile values to nodes
current_profile = int(Options.get("currentProfile"))
on_set_profile({'profile': current_profile}, False)

# Set current heat on startup
if Database.Heat.query.first():
    RACE.current_heat = Database.Heat.query.first().id
    RACE.node_pilots = {}
    RACE.node_teams = {}
    for heatNode in Database.HeatNode.query.filter_by(heat_id=RACE.current_heat):
        RACE.node_pilots[heatNode.node_index] = heatNode.pilot_id

        if heatNode.pilot_id is not Database.PILOT_ID_NONE:
            RACE.node_teams[heatNode.node_index] = Database.Pilot.query.get(heatNode.pilot_id).team
        else:
            RACE.node_teams[heatNode.node_index] = None

# Normalize results caches
Results.normalize_cache_status(DB)

# Create LED object with appropriate configuration
strip = None
if Config.LED['LED_COUNT'] > 0:
    led_type = os.environ.get('RH_LEDS', 'ws281x')
    # note: any calls to 'Options.get()' need to happen after the DB initialization,
    #       otherwise it causes problems when run with no existing DB file
    led_brightness = int(Options.get("ledBrightness"))
    try:
        ledModule = importlib.import_module(led_type + '_leds')
        strip = ledModule.get_pixel_interface(config=Config.LED, brightness=led_brightness)
    except ImportError:
        try:
            ledModule = importlib.import_module('ANSI_leds')
            strip = ledModule.get_pixel_interface(config=Config.LED, brightness=led_brightness)
        except ImportError:
            ledModule = None
            logger.info('LED: disabled (no modules available)')
else:
    logger.debug('LED: disabled (configured LED_COUNT is <= 0)')
if strip:
    # Initialize the library (must be called once before other functions).
    strip.begin()
    led_manager = LEDEventManager(Events, strip)
    led_effects = Plugins(prefix='led_handler')
    led_effects.discover()
    for led_effect in led_effects:
        led_manager.registerEffect(led_effect)
    init_LED_effects()
else:
    led_manager = NoLEDManager()

# start up VRx Control
vrx_controller = initVRxController()

if vrx_controller:
    Events.on(Evt.CLUSTER_JOIN, 'VRx', killVRxController)

def start(port_val = Config.GENERAL['HTTP_PORT']):
    if not Options.get("secret_key"):
        Options.set("secret_key", unicode(os.urandom(50), errors='ignore'))

    APP.config['SECRET_KEY'] = Options.get("secret_key")

    logger.info("Running http server at port " + str(port_val))

    Events.trigger(Evt.STARTUP)

    try:
        # the following fn does not return until the server is shutting down
        SOCKET_IO.run(APP, host='0.0.0.0', port=port_val, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("Server terminated by keyboard interrupt")
    except SystemExit:
        logger.info("Server terminated by system exit")
    except Exception:
        logger.exception("Server exception:  ")

    Events.trigger(Evt.SHUTDOWN)
    print INTERFACE.get_intf_error_report_str(True)

# Start HTTP server
if __name__ == '__main__':
    start()
