'''RotorHazard server script'''
RELEASE_VERSION = "2.3.0-dev.4" # Public release version code
SERVER_API = 28 # Server API version
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

# program-start time, in milliseconds since 1970-01-01
PROGRAM_START_EPOCH_TIME = int((datetime.now() - EPOCH_START).total_seconds() * 1000)

logger.info('RotorHazard v{0}'.format(RELEASE_VERSION))

# Normal importing resumes here
import gevent
import gevent.monkey
gevent.monkey.patch_all()
GEVENT_SUPPORT = True   # For Python Debugger

import io
import os
import sys
import traceback
import re
import shutil
import base64
import subprocess
import importlib
from monotonic import monotonic
from functools import wraps
from collections import OrderedDict
from six import unichr, string_types

from flask import Flask, send_file, request, Response, session, templating
from flask_socketio import SocketIO, emit
from sqlalchemy import create_engine, MetaData, Table

import random
import string
import json

import Config
import Options
import Database
import Results
import Language
import RHUtils
from RHUtils import catchLogExceptionsWrapper
from Language import __
from ClusterNodeSet import SlaveNode, ClusterNodeSet

# Events manager
from eventmanager import Evt, EventManager

Events = EventManager()

# LED imports
from led_event_manager import LEDEventManager, NoLEDManager, LEDEvent, Color, ColorPattern, hexToColor

sys.path.append('../interface')
sys.path.append('/home/pi/RotorHazard/src/interface')  # Needed to run on startup

from Plugins import Plugins, search_modules
from Sensors import Sensors
import RHRace
from RHRace import WinCondition, WinStatus, RaceStatus

APP = Flask(__name__, static_url_path='/static')

HEARTBEAT_THREAD = None
HEARTBEAT_DATA_RATE_FACTOR = 5

ERROR_REPORT_INTERVAL_SECS = 600  # delay between comm-error reports to log

FULL_RESULTS_CACHE = {} # Cache of complete results page
FULL_RESULTS_CACHE_BUILDING = False # Whether results are being calculated
FULL_RESULTS_CACHE_VALID = False # Whether cache is valid (False = regenerate cache)

DB_FILE_NAME = 'database.db'
DB_BKP_DIR_NAME = 'db_bkp'
IMDTABLER_JAR_NAME = 'static/IMDTabler.jar'

# check if 'log' directory owned by 'root' and change owner to 'pi' user if so
if RHUtils.checkSetFileOwnerPi(log.LOG_DIR_NAME):
    logger.info("Changed '{0}' dir owner from 'root' to 'pi'".format(log.LOG_DIR_NAME))

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
SENSORS = Sensors()
CLUSTER = None    # initialized later
Use_imdtabler_jar_flag = False  # set True if IMDTabler.jar is available
vrx_controller = None

RACE = RHRace.RHRace() # For storing race management variables

# program-start time (in milliseconds, starting at zero)
PROGRAM_START_MTONIC = monotonic()

# offset for converting 'monotonic' time to epoch milliseconds since 1970-01-01
MTONIC_TO_EPOCH_MILLIS_OFFSET = PROGRAM_START_EPOCH_TIME - 1000.0*PROGRAM_START_MTONIC

TONES_NONE = 0
TONES_ONE = 1
TONES_ALL = 2

# convert 'monotonic' time to epoch milliseconds since 1970-01-01
def monotonic_to_epoch_millis(secs):
    return 1000.0*secs + MTONIC_TO_EPOCH_MILLIS_OFFSET

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

def getCurrentProfile():
    current_profile = Options.getInt('currentProfile')
    return Database.Profiles.query.get(current_profile)

def getCurrentRaceFormat():
    if RACE.format is None:
        val = Options.getInt('currentFormat')
        race_format = Database.RaceFormat.query.get(val)
        # create a shared instance
        RACE.format = RHRaceFormat.copy(race_format)
        RACE.format.id = race_format.id
    return RACE.format

def getCurrentDbRaceFormat():
    if RACE.format is None or RHRaceFormat.isDbBased(RACE.format):
        val = Options.getInt('currentFormat')
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

    emit_current_laps()

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

# Flask template render with exception catch, so exception
# details are sent to the log file (instead of 'stderr').
def render_template(template_name_or_list, **context):
    try:
        return templating.render_template(template_name_or_list, **context)
    except Exception:
        logger.exception("Exception in render_template")
    return "Error rendering template"

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
        nodes=nodes,
        cluster_has_slaves=(CLUSTER and CLUSTER.hasSlaves()))

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
        nodes=nodes,
        cluster_has_slaves=(CLUSTER and CLUSTER.hasSlaves()))

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
        cluster_has_slaves=(CLUSTER and CLUSTER.hasSlaves()),
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
    try:
        docfile = request.args.get('d')

        language = Options.get("currentLanguage")
        if language:
            translation = language + '-' + docfile
            if os.path.isfile('../../doc/' + translation):
                docfile = translation

        with io.open('../../doc/' + docfile, 'r', encoding="utf-8") as f:
            doc = f.read()

        return templating.render_template('viewdocs.html',
            serverInfo=serverInfo,
            getOption=Options.get,
            __=__,
            doc=doc
            )
    except Exception:
        logger.exception("Exception in render_template")
    return "Error rendering documentation"

@APP.route('/img/<path:imgfile>')
def viewImg(imgfile):
    '''Route to img called within doc viewer.'''
    return send_file('../../doc/img/' + imgfile)


def start_background_threads():
    INTERFACE.start()
    global HEARTBEAT_THREAD
    if HEARTBEAT_THREAD is None:
        HEARTBEAT_THREAD = gevent.spawn(heartbeat_thread_function)
        logger.debug('Heartbeat thread started')

#
# Socket IO Events
#

@SOCKET_IO.on('connect')
@catchLogExceptionsWrapper
def connect_handler():
    '''Starts the interface and a heartbeat thread for rssi.'''
    logger.debug('Client connected')
    start_background_threads()
    emit_heat_data(nobroadcast=True)

@SOCKET_IO.on('disconnect')
def disconnect_handler():
    '''Emit disconnect event.'''
    logger.debug('Client disconnected')

# LiveTime compatible events

@SOCKET_IO.on('get_version')
@catchLogExceptionsWrapper
def on_get_version():
    session['LiveTime'] = True
    ver_parts = RELEASE_VERSION.split('.')
    return {'major': ver_parts[0], 'minor': ver_parts[1]}

@SOCKET_IO.on('get_timestamp')
@catchLogExceptionsWrapper
def on_get_timestamp():
    if RACE.race_status == RaceStatus.STAGING:
        now = RACE.start_time_monotonic
    else:
        now = monotonic()
    return {'timestamp': monotonic_to_epoch_millis(now)}

@SOCKET_IO.on('get_settings')
@catchLogExceptionsWrapper
def on_get_settings():
    return {'nodes': [{
        'frequency': node.frequency,
        'trigger_rssi': node.enter_at_level
        } for node in INTERFACE.nodes
    ]}

@SOCKET_IO.on('reset_auto_calibration')
@catchLogExceptionsWrapper
def on_reset_auto_calibration(data):
    on_stop_race()
    on_discard_laps()
    setCurrentRaceFormat(SLAVE_RACE_FORMAT)
    emit_race_format()
    on_stage_race()

# Cluster events

@SOCKET_IO.on('join_cluster')
@catchLogExceptionsWrapper
def on_join_cluster():
    setCurrentRaceFormat(SLAVE_RACE_FORMAT)
    emit_race_format()
    logger.info('Joined cluster')
    Events.trigger(Evt.CLUSTER_JOIN)

@SOCKET_IO.on('check_slave_query')
@catchLogExceptionsWrapper
def on_check_slave_query(data):
    ''' Check-query received from master; return response. '''
    payload = {
        'timestamp': monotonic_to_epoch_millis(monotonic())
    }
    SOCKET_IO.emit('check_slave_response', payload)

# RotorHazard events

@SOCKET_IO.on('load_data')
@catchLogExceptionsWrapper
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
        elif load_type == 'start_thresh_lower_amount':
            emit_start_thresh_lower_amount(nobroadcast=True)
        elif load_type == 'start_thresh_lower_duration':
            emit_start_thresh_lower_duration(nobroadcast=True)
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
            emit_cluster_status()
        elif load_type == 'hardware_log_init':
            emit_current_log_file_to_socket()

@SOCKET_IO.on('broadcast_message')
@catchLogExceptionsWrapper
def on_broadcast_message(data):
    emit_priority_message(data['message'], data['interrupt'])

# Settings socket io events

@SOCKET_IO.on('set_frequency')
@catchLogExceptionsWrapper
def on_set_frequency(data):
    '''Set node frequency.'''
    CLUSTER.emit('set_frequency', data)
    if isinstance(data, string_types): # LiveTime compatibility
        data = json.loads(data)
    node_index = data['node']
    frequency = data['frequency']

    if node_index < 0 or node_index >= RACE.num_nodes:
        logger.info('Unable to set frequency ({0}) on node {1}; node index out of range'.format(frequency, node_index+1))
        return

    profile = getCurrentProfile()
    freqs = json.loads(profile.frequencies)
    freqs["f"][node_index] = frequency
    profile.frequencies = json.dumps(freqs)
    logger.info('Frequency set: Node {0} Frequency {1}'.format(node_index+1, frequency))

    update_heat_flag = False
    try:  # if running as slave timer and no pilot is set for node then set one now
        if frequency and getCurrentRaceFormat() is SLAVE_RACE_FORMAT:
            heat_node = Database.HeatNode.query.filter_by(heat_id=RACE.current_heat, node_index=node_index).one_or_none()
            if heat_node and heat_node.pilot_id == Database.PILOT_ID_NONE:
                pilot = Database.Pilot.query.get(node_index+1)
                if pilot:
                    heat_node.pilot_id = pilot.id
                    update_heat_flag = True
                    logger.info("Set node {0} pilot to '{1}' for slave-timer operation".format(node_index+1, pilot.callsign))
                else:
                    logger.info("Unable to set node {0} pilot for slave-timer operation".format(node_index+1))
    except:
        logger.exception("Error checking/setting pilot for node {0} in 'on_set_frequency()'".format(node_index+1))

    DB.session.commit()

    INTERFACE.set_frequency(node_index, frequency)

    Events.trigger(Evt.FREQUENCY_SET, {
        'nodeIndex': node_index,
        'frequency': frequency,
        })

    emit_frequency_data()
    if update_heat_flag:
        emit_heat_data()

@SOCKET_IO.on('set_frequency_preset')
@catchLogExceptionsWrapper
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

@catchLogExceptionsWrapper
def restore_node_frequency(node_index):
    ''' Restore frequency for given node index (update hardware) '''
    gevent.sleep(0.250)  # pause to get clear of heartbeat actions for scanner
    profile = getCurrentProfile()
    profile_freqs = json.loads(profile.frequencies)
    freq = profile_freqs["f"][node_index]
    INTERFACE.set_frequency(node_index, freq)
    logger.info('Frequency restored: Node {0} Frequency {1}'.format(node_index+1, freq))

@SOCKET_IO.on('set_enter_at_level')
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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

@SOCKET_IO.on("set_start_thresh_lower_amount")
@catchLogExceptionsWrapper
def on_set_start_thresh_lower_amount(data):
    start_thresh_lower_amount = data['start_thresh_lower_amount']
    Options.set("startThreshLowerAmount", start_thresh_lower_amount)
    logger.info("set start_thresh_lower_amount to %s percent" % start_thresh_lower_amount)
    emit_start_thresh_lower_amount(noself=True)

@SOCKET_IO.on("set_start_thresh_lower_duration")
@catchLogExceptionsWrapper
def on_set_start_thresh_lower_duration(data):
    start_thresh_lower_duration = data['start_thresh_lower_duration']
    Options.set("startThreshLowerDuration", start_thresh_lower_duration)
    logger.info("set start_thresh_lower_duration to %s seconds" % start_thresh_lower_duration)
    emit_start_thresh_lower_duration(noself=True)

@SOCKET_IO.on('set_language')
@catchLogExceptionsWrapper
def on_set_language(data):
    '''Set interface language.'''
    Options.set('currentLanguage', data['language'])
    DB.session.commit()

@SOCKET_IO.on('cap_enter_at_btn')
@catchLogExceptionsWrapper
def on_cap_enter_at_btn(data):
    '''Capture enter-at level.'''
    node_index = data['node_index']
    if INTERFACE.start_capture_enter_at_level(node_index):
        logger.info('Starting capture of enter-at level for node {0}'.format(node_index+1))

@SOCKET_IO.on('cap_exit_at_btn')
@catchLogExceptionsWrapper
def on_cap_exit_at_btn(data):
    '''Capture exit-at level.'''
    node_index = data['node_index']
    if INTERFACE.start_capture_exit_at_level(node_index):
        logger.info('Starting capture of exit-at level for node {0}'.format(node_index+1))

@SOCKET_IO.on('set_scan')
@catchLogExceptionsWrapper
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
        gevent.spawn(restore_node_frequency, node_index)

@SOCKET_IO.on('add_heat')
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
        FULL_RESULTS_CACHE_VALID = False
        emit_round_data_notify() # live update rounds page
        emit_heat_data() # Settings page, new pilot callsign in heats
    if 'phonetic' in data:
        emit_heat_data() # Settings page, new pilot phonetic in heats. Needed?

@SOCKET_IO.on('delete_pilot')
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
def on_set_profile(data, emit_vals=True):
    ''' set current profile '''
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
def on_shutdown_pi():
    '''Shutdown the raspberry pi.'''
    Events.trigger(Evt.SHUTDOWN)
    CLUSTER.emit('shutdown_pi')
    emit_priority_message(__('Server has shut down.'), True)
    logger.info('Shutdown pi')
    gevent.sleep(1);
    os.system("sudo shutdown now")

@SOCKET_IO.on('reboot_pi')
@catchLogExceptionsWrapper
def on_reboot_pi():
    '''Reboot the raspberry pi.'''
    Events.trigger(Evt.SHUTDOWN)
    CLUSTER.emit('reboot_pi')
    emit_priority_message(__('Server is rebooting.'), True)
    logger.info('Rebooting pi')
    gevent.sleep(1);
    os.system("sudo reboot now")

@SOCKET_IO.on('download_logs')
@catchLogExceptionsWrapper
def on_download_logs(data):
    '''Download logs (as .zip file).'''
    zip_path_name = log.create_log_files_zip(logger, Config.CONFIG_FILE_NAME, DB_FILE_NAME)
    RHUtils.checkSetFileOwnerPi(log.LOGZIP_DIR_NAME)
    if zip_path_name:
        RHUtils.checkSetFileOwnerPi(zip_path_name)
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
@catchLogExceptionsWrapper
def on_set_min_lap(data):
    min_lap = data['min_lap']
    Options.set("MinLapSec", data['min_lap'])

    Events.trigger(Evt.MIN_LAP_TIME_SET, {
        'min_lap': min_lap,
        })

    logger.info("set min lap time to %s seconds" % min_lap)
    emit_min_lap(noself=True)

@SOCKET_IO.on("set_min_lap_behavior")
@catchLogExceptionsWrapper
def on_set_min_lap_behavior(data):
    min_lap_behavior = int(data['min_lap_behavior'])
    Options.set("MinLapBehavior", min_lap_behavior)

    Events.trigger(Evt.MIN_LAP_BEHAVIOR_SET, {
        'min_lap_behavior': min_lap_behavior,
        })

    logger.info("set min lap behavior to %s" % min_lap_behavior)
    emit_min_lap(noself=True)

@SOCKET_IO.on("set_race_format")
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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

@SOCKET_IO.on("set_next_heat_behavior")
@catchLogExceptionsWrapper
def on_set_next_heat_behavior(data):
    next_heat_behavior = int(data['next_heat_behavior'])
    Options.set("nextHeatBehavior", next_heat_behavior)
    logger.info("set next heat behavior to %s" % next_heat_behavior)

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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
def cancel_schedule_race():
    global RACE

    RACE.scheduled = False

    Events.trigger(Evt.RACE_SCHEDULE_CANCEL)

    SOCKET_IO.emit('race_scheduled', {
        'scheduled': RACE.scheduled,
        'scheduled_at': RACE.scheduled_time
        })

    emit_priority_message(__("Scheduled race cancelled"), False)

@SOCKET_IO.on('get_pi_time')
@catchLogExceptionsWrapper
def on_get_pi_time():
    # never broadcasts to all (client must make request)
    emit('pi_time', {
        'pi_time_s': monotonic()
    })

@SOCKET_IO.on('stage_race')
@catchLogExceptionsWrapper
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
        RACE.win_status = WinStatus.NONE
        RACE.status_message = ''

        RACE.node_has_finished = {}
        for heatNode in heatNodes:
            if heatNode.node_index < RACE.num_nodes:
                if heatNode.pilot_id != Database.PILOT_ID_NONE:
                    RACE.node_has_finished[heatNode.node_index] = False
                else:
                    RACE.node_has_finished[heatNode.node_index] = None

        INTERFACE.set_race_status(RaceStatus.STAGING)
        emit_current_laps() # Race page, blank laps to the web client
        emit_current_leaderboard() # Race page, blank leaderboard to the web client
        emit_race_status()
        check_emit_race_status_message(RACE) # Update race status message

        race_format = getCurrentRaceFormat()
        MIN = min(race_format.start_delay_min, race_format.start_delay_max) # in case values are reversed
        MAX = max(race_format.start_delay_min, race_format.start_delay_max)
        RACE.start_time_delay_secs = random.randint(MIN, MAX) + RHRace.RACE_START_DELAY_EXTRA_SECS

        RACE.start_time_monotonic = monotonic() + RACE.start_time_delay_secs
        RACE.start_time_epoch_ms = monotonic_to_epoch_millis(RACE.start_time_monotonic)
        RACE.start_token = random.random()
        gevent.spawn(race_start_thread, RACE.start_token)

        SOCKET_IO.emit('stage_ready', {
            'hide_stage_timer': MIN != MAX,
            'delay': RACE.start_time_delay_secs,
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

@catchLogExceptionsWrapper
def race_start_thread(start_token):
    global RACE

    # clear any lingering crossings at staging (if node rssi < enterAt)
    for node in INTERFACE.nodes:
        if node.crossing_flag and node.frequency > 0 and node.current_pilot_id != Database.PILOT_ID_NONE and \
                    node.current_rssi < node.enter_at_level:
            logger.info("Forcing end crossing for node {0} at staging (rssi={1}, enterAt={2}, exitAt={3})".\
                       format(node.index+1, node.current_rssi, node.enter_at_level, node.exit_at_level))
            INTERFACE.force_end_crossing(node.index)

    if CLUSTER and CLUSTER.hasSlaves():
        CLUSTER.doClusterRaceStart()

    # set lower EnterAt/ExitAt values if configured
    if Options.getInt('startThreshLowerAmount') > 0 and Options.getInt('startThreshLowerDuration') > 0:
        lower_amount = Options.getInt('startThreshLowerAmount')
        logger.info("Lowering EnterAt/ExitAt values at start of race, amount={0}%, duration={1} secs".\
                    format(lower_amount, Options.getInt('startThreshLowerDuration')))
        lower_end_time = RACE.start_time_monotonic + Options.getInt('startThreshLowerDuration')
        for node in INTERFACE.nodes:
            if node.frequency > 0 and node.current_pilot_id != Database.PILOT_ID_NONE:
                if node.current_rssi < node.enter_at_level:
                    diff_val = int((node.enter_at_level-node.exit_at_level)*lower_amount/100)
                    if diff_val > 0:
                        new_enter_at = node.enter_at_level - diff_val
                        new_exit_at = max(node.exit_at_level - diff_val, 0)
                        if node.api_valid_flag and node.is_valid_rssi(new_enter_at):
                            logger.info("For node {0} lowering EnterAt from {1} to {2} and ExitAt from {3} to {4}"\
                                    .format(node.index+1, node.enter_at_level, new_enter_at, node.exit_at_level, new_exit_at))
                            node.start_thresh_lower_time = lower_end_time  # set time when values will be restored
                            node.start_thresh_lower_flag = True
                            # use 'transmit_' instead of 'set_' so values are not saved in node object
                            INTERFACE.transmit_enter_at_level(node, new_enter_at)
                            INTERFACE.transmit_exit_at_level(node, new_exit_at)
                    else:
                        logger.info("Not lowering EnterAt/ExitAt values for node {0} because EnterAt value ({1}) unchanged"\
                                .format(node.index+1, node.enter_at_level))
                else:
                    logger.info("Not lowering EnterAt/ExitAt values for node {0} because current RSSI ({1}) >= EnterAt ({2})"\
                            .format(node.index+1, node.current_rssi, node.enter_at_level))

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

        # kick off race expire processing
        race_format = getCurrentRaceFormat()
        if race_format and race_format.race_mode == 0: # count down
            gevent.spawn(race_expire_thread, start_token)

        emit_race_status() # Race page, to set race button states
        logger.info('Race started at {0} ({1:.1f})'.format(RACE.start_time_monotonic, RACE.start_time_epoch_ms))

def race_expire_thread(start_token):
    global RACE
    race_format = getCurrentRaceFormat()
    if race_format and race_format.race_mode == 0: # count down
        gevent.sleep(race_format.race_time_sec)

        if RACE.start_token == start_token:
            logger.info("Race time has exprired.")

            RACE.timer_running = False # indicate race timer no longer running
            Events.trigger(Evt.RACE_FINISH)
            check_win_condition(RACE, INTERFACE, at_finish=True, start_token=start_token)
        else:
            logger.debug("Killing unused time expires thread")

@SOCKET_IO.on('stop_race')
@catchLogExceptionsWrapper
def on_stop_race():
    '''Stops the race and stops registering laps.'''
    global RACE

    CLUSTER.emit('stop_race')
    if RACE.race_status == RaceStatus.RACING:
        RACE.end_time = monotonic() # Update the race end time stamp
        delta_time = RACE.end_time - RACE.start_time_monotonic
        milli_sec = delta_time * 1000.0
        RACE.duration_ms = milli_sec

        logger.info('Race stopped at {0} ({1:.1f}), duration {2}ms'.format(RACE.end_time, monotonic_to_epoch_millis(RACE.end_time), RACE.duration_ms))

        min_laps_list = []  # show nodes with laps under minimum (if any)
        for node in INTERFACE.nodes:
            if node.under_min_lap_count > 0:
                min_laps_list.append('Node {0} Count={1}'.format(node.index+1, node.under_min_lap_count))
        if len(min_laps_list) > 0:
            logger.info('Nodes with laps under minimum:  ' + ', '.join(min_laps_list))

        RACE.race_status = RaceStatus.DONE # To stop registering passed laps, waiting for laps to be cleared
        INTERFACE.set_race_status(RaceStatus.DONE)
        Events.trigger(Evt.RACE_STOP)
        check_win_condition(RACE, INTERFACE)

    else:
        logger.info('No active race to stop')
        RACE.race_status = RaceStatus.READY # Go back to ready state
        INTERFACE.set_race_status(RaceStatus.READY)
        led_manager.clear()
        delta_time = 0

    # check if nodes may be set to temporary lower EnterAt/ExitAt values (and still have them)
    if Options.getInt('startThreshLowerAmount') > 0 and \
            delta_time < Options.getInt('startThreshLowerDuration'):
        for node in INTERFACE.nodes:
            # if node EnterAt/ExitAt values need to be restored then do it soon
            if node.frequency > 0 and node.current_pilot_id != Database.PILOT_ID_NONE and \
                                            node.start_thresh_lower_flag:
                node.start_thresh_lower_time = RACE.end_time + 0.1

    RACE.timer_running = False # indicate race timer not running
    RACE.scheduled = False # also stop any deferred start

    SOCKET_IO.emit('stop_timer') # Loop back to race page to start the timer counting up
    emit_race_status() # Race page, to set race button states

@SOCKET_IO.on('save_laps')
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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

    # run adaptive calibration
    if Options.getInt('calibrationMode'):
        autoUpdateCalibration()

    # spawn thread for updating results caches
    params = {
        'race_id': race_id,
        'heat_id': heat_id,
        'round_id': round_id,
    }
    gevent.spawn(update_result_caches, params)

    Events.trigger(Evt.LAPS_RESAVE, {
        'race_id': race_id,
        'pilot_id': pilot_id,
        })

def update_result_caches(params):
    Results.build_race_results_caches(DB, params)
    emit_round_data_notify()

@SOCKET_IO.on('discard_laps')
@catchLogExceptionsWrapper
def on_discard_laps(**kwargs):
    '''Clear the current laps without saving.'''
    global RACE
    CLUSTER.emit('discard_laps')
    clear_laps()
    RACE.race_status = RaceStatus.READY # Flag status as ready to start next race
    INTERFACE.set_race_status(RaceStatus.READY)
    emit_current_laps() # Race page, blank laps to the web client
    emit_current_leaderboard() # Race page, blank leaderboard to the web client
    emit_race_status() # Race page, to set race button states
    RACE.win_status = WinStatus.NONE
    RACE.status_message = ''
    check_emit_race_status_message(RACE) # Update race status message

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
@catchLogExceptionsWrapper
def on_set_current_heat(data):
    '''Update the current heat variable.'''
    global RACE
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

    if Options.getInt('calibrationMode'):
        autoUpdateCalibration()

    Events.trigger(Evt.HEAT_SET, {
        'race': RACE,
        'heat_id': new_heat_id,
        })

    RACE.cacheStatus = Results.CacheStatus.INVALID  # refresh leaderboard
    emit_current_heat() # Race page, to update heat selection button
    emit_current_leaderboard() # Race page, to update callsigns in leaderboard
    check_emit_race_status_message(RACE) # Update race status message

@SOCKET_IO.on('generate_heats')
def on_generate_heats(data):
    '''Spawn heat generator thread'''
    gevent.spawn(generate_heats, data)

@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
def on_delete_lap(data):
    '''Delete a false lap.'''

    node_index = data['node']
    lap_index = data['lap_index']

    if node_index is None or lap_index is None:
        logger.error("Bad parameter in 'on_delete_lap()':  node_index={0}, lap_index={1}".format(node_index, lap_index))
        return

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

    try:  # delete any split laps for deleted lap
        lap_splits = Database.LapSplit.query.filter_by(node_index=node_index, lap_id=lap_number).all()
        if lap_splits and len(lap_splits) > 0:
            for lap_split in lap_splits:
                DB.session.delete(lap_split)
            DB.session.commit()
    except:
        logger.exception("Error deleting split laps")

    Events.trigger(Evt.LAP_DELETE, {
        'race': RACE,
        'node_index': node_index,
        })

    logger.info('Lap deleted: Node {0} Lap {1}'.format(node_index+1, lap_index))
    RACE.cacheStatus = Results.CacheStatus.INVALID  # refresh leaderboard
    emit_current_laps() # Race page, update web client
    emit_current_leaderboard() # Race page, update web client
    check_emit_race_status_message(RACE) # Update race status message

@SOCKET_IO.on('simulate_lap')
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
def on_LED_RB():
    '''LED rainbow'''
    on_use_led_effect({
        'effect': "rainbow",
        'args': {
            'time': 5
        }
    })

@SOCKET_IO.on('LED_RBCYCLE')
@catchLogExceptionsWrapper
def on_LED_RBCYCLE():
    '''LED rainbow Cycle'''
    on_use_led_effect({
        'effect': "rainbowCycle",
        'args': {
            'time': 5
        }
    })

@SOCKET_IO.on('LED_RBCHASE')
@catchLogExceptionsWrapper
def on_LED_RBCHASE():
    '''LED Rainbow Cycle Chase'''
    on_use_led_effect({
        'effect': "rainbowCycleChase",
        'args': {
            'time': 5
        }
    })

@SOCKET_IO.on('LED_brightness')
@catchLogExceptionsWrapper
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
@catchLogExceptionsWrapper
def on_set_option(data):
    Options.set(data['option'], data['value'])
    Events.trigger(Evt.OPTION_SET, {
        'option': data['option'],
        'value': data['value'],
        })

@SOCKET_IO.on('get_race_scheduled')
@catchLogExceptionsWrapper
def get_race_elapsed():
    # get current race status; never broadcasts to all
    emit('race_scheduled', {
        'scheduled': RACE.scheduled,
        'scheduled_at': RACE.scheduled_time
    })

@SOCKET_IO.on('save_callouts')
@catchLogExceptionsWrapper
def save_callouts(data):
    # save callouts to Options
    callouts = json.dumps(data['callouts'])
    Options.set('voiceCallouts', callouts)
    logger.info('Set all voice callouts')
    logger.debug('Voice callouts set to: {0}'.format(callouts))

@SOCKET_IO.on('imdtabler_update_freqs')
@catchLogExceptionsWrapper
def imdtabler_update_freqs(data):
    ''' Update IMDTabler page with new frequencies list '''
    emit_imdtabler_data(data['freq_list'].replace(',',' ').split())

@SOCKET_IO.on('clean_cache')
@catchLogExceptionsWrapper
def clean_results_cache():
    ''' expose cach wiping for frontend debugging '''
    global FULL_RESULTS_CACHE_VALID
    Results.invalidate_all_caches(DB)
    FULL_RESULTS_CACHE_VALID = False

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
    for sensor in SENSORS:
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

def emit_cluster_status(**params):
    '''Emits cluster status information.'''
    if ('nobroadcast' in params):
        emit('cluster_status', CLUSTER.getClusterStatusInfo())
    else:
        SOCKET_IO.emit('cluster_status', CLUSTER.getClusterStatusInfo())

def emit_start_thresh_lower_amount(**params):
    '''Emits current start_thresh_lower_amount.'''
    emit_payload = {
        'start_thresh_lower_amount': Options.get('startThreshLowerAmount'),
    }
    if ('nobroadcast' in params):
        emit('start_thresh_lower_amount', emit_payload)
    else:
        SOCKET_IO.emit('start_thresh_lower_amount', emit_payload)

def emit_start_thresh_lower_duration(**params):
    '''Emits current start_thresh_lower_duration.'''
    emit_payload = {
        'start_thresh_lower_duration': Options.get('startThreshLowerDuration'),
    }
    if ('nobroadcast' in params):
        emit('start_thresh_lower_duration', emit_payload)
    else:
        SOCKET_IO.emit('start_thresh_lower_duration', emit_payload)

def emit_node_tuning(**params):
    '''Emits node tuning values.'''
    tune_val = getCurrentProfile()
    emit_payload = {
        'profile_ids': [profile.id for profile in Database.Profiles.query.all()],
        'profile_names': [profile.name for profile in Database.Profiles.query.all()],
        'current_profile': Options.getInt('currentProfile'),
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
        'min_lap_behavior': Options.getInt("MinLapBehavior")
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
                'split_speed': '{0:.2f}'.format(split.split_speed) if split.split_speed is not None else '-'
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

@catchLogExceptionsWrapper
def emit_round_data_thread(params, sid):
    with APP.test_request_context():
        '''Emits saved races to rounds page.'''
        timing = {
            'start': monotonic()
        }
        logger.debug('T%d: Round data build started', timing['start'])

        CACHE_TIMEOUT = 10
        expires = monotonic() + CACHE_TIMEOUT
        error_flag = False

        global FULL_RESULTS_CACHE
        global FULL_RESULTS_CACHE_BUILDING
        global FULL_RESULTS_CACHE_VALID

        if FULL_RESULTS_CACHE_BUILDING: # Don't restart calculation if another calculation thread exists
            while True: # Pause this thread until calculations are completed
                gevent.idle()
                if FULL_RESULTS_CACHE_BUILDING is False:
                    break
                elif monotonic() > FULL_RESULTS_CACHE_BUILDING + CACHE_TIMEOUT:
                    logger.warn('T%d: Timed out waiting for other cache build thread', timing['start'])
                    FULL_RESULTS_CACHE_BUILDING = False
                    break

        if FULL_RESULTS_CACHE_VALID: # Output existing calculated results
            emit_payload = FULL_RESULTS_CACHE

        else:
            timing['build_start'] = monotonic()
            FULL_RESULTS_CACHE_BUILDING = monotonic()

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
                        logger.info('Heat %d Round %d cache invalid; rebuilding', heat.heat_id, round.round_id)
                        results = Results.calc_leaderboard(DB, heat_id=heat.heat_id, round_id=round.round_id)
                        round.results = results
                        round.cacheStatus = Results.CacheStatus.VALID
                        DB.session.commit()
                    else:
                        expires = monotonic() + CACHE_TIMEOUT
                        while True:
                            gevent.idle()
                            if round.cacheStatus == Results.CacheStatus.VALID:
                                results = round.results
                                break
                            elif monotonic() > expires:
                                logger.warn('T%d: Cache build timed out: Heat %d Round %d', timing['start'], heat.heat_id, round.round_id)
                                error_flag = True
                                break

                    rounds.append({
                        'id': round.round_id,
                        'start_time_formatted': round.start_time_formatted,
                        'nodes': pilotraces,
                        'leaderboard': results
                    })

                if heatdata.cacheStatus == Results.CacheStatus.INVALID:
                    logger.info('Heat %d cache invalid; rebuilding', heat.heat_id)
                    results = Results.calc_leaderboard(DB, heat_id=heat.heat_id)
                    heatdata.results = results
                    heatdata.cacheStatus = Results.CacheStatus.VALID
                    DB.session.commit()
                else:
                    checkStatus = True
                    expires = monotonic() + CACHE_TIMEOUT
                    while True:
                        gevent.idle()
                        if heatdata.cacheStatus == Results.CacheStatus.VALID:
                            results = heatdata.results
                            break
                        elif monotonic() > expires:
                            logger.warn('T%d: Cache build timed out: Heat Summary %d', timing['start'], heat.heat_id)
                            error_flag = True
                            break

                heats[heat.heat_id] = {
                    'heat_id': heat.heat_id,
                    'note': heatdata.note,
                    'rounds': rounds,
                    'leaderboard': results
                }

            timing['round_results'] = monotonic()
            logger.debug('T%d: round results assembled in: %fs', timing['start'], timing['round_results'] - timing['build_start'])

            gevent.sleep()
            heats_by_class = {}
            heats_by_class[Database.CLASS_ID_NONE] = [heat.id for heat in Database.Heat.query.filter_by(class_id=Database.CLASS_ID_NONE).all()]
            for race_class in Database.RaceClass.query.all():
                heats_by_class[race_class.id] = [heat.id for heat in Database.Heat.query.filter_by(class_id=race_class.id).all()]

            timing['by_class'] = monotonic()

            gevent.sleep()
            current_classes = {}
            for race_class in Database.RaceClass.query.all():
                if race_class.cacheStatus == Results.CacheStatus.INVALID:
                    logger.info('Class %d cache invalid; rebuilding', race_class.id)
                    results = Results.calc_leaderboard(DB, class_id=race_class.id)
                    race_class.results = results
                    race_class.cacheStatus = Results.CacheStatus.VALID
                    DB.session.commit()
                else:
                    checkStatus = True
                    expires = monotonic() + CACHE_TIMEOUT
                    while True:
                        gevent.idle()
                        if race_class.cacheStatus == Results.CacheStatus.VALID:
                            results = race_class.results
                            break
                        elif monotonic() > expires:
                            logger.warn('T%d: Cache build timed out: Class Summary %d', timing['start'], race_class.id)
                            error_flag = True
                            break

                current_class = {}
                current_class['id'] = race_class.id
                current_class['name'] = race_class.name
                current_class['description'] = race_class.name
                current_class['leaderboard'] = results
                current_classes[race_class.id] = current_class

            timing['event'] = monotonic()
            logger.debug('T%d: results by class assembled in: %fs', timing['start'], timing['event'] - timing['by_class'])

            gevent.sleep()
            if Options.get("eventResults_cacheStatus") == Results.CacheStatus.INVALID:
                logger.info('Event cache invalid; rebuilding')
                results = Results.calc_leaderboard(DB)
                Options.set("eventResults", json.dumps(results))
                Options.set("eventResults_cacheStatus", Results.CacheStatus.VALID)
                DB.session.commit()
            else:
                expires = monotonic() + CACHE_TIMEOUT
                while True:
                    gevent.idle()
                    status = Options.get("eventResults_cacheStatus")
                    if status == Results.CacheStatus.VALID:
                        results = json.loads(Options.get("eventResults"))
                        break
                    elif monotonic() > expires:
                        logger.warn('Cache build timed out: Event Summary')
                        error_flag = True
                        break

            timing['event_end'] = monotonic()
            logger.debug('T%d: event results assembled in: %fs', timing['start'], timing['event_end'] - timing['event'])

            emit_payload = {
                'heats': heats,
                'heats_by_class': heats_by_class,
                'classes': current_classes,
                'event_leaderboard': results
            }

            FULL_RESULTS_CACHE_BUILDING = False
            if error_flag:
                logger.warn('T%d: Cache results build failed; leaving page cache invalid', timing['start'])
                # pass message to front-end? ***
            else:

                FULL_RESULTS_CACHE = emit_payload
                FULL_RESULTS_CACHE_VALID = True

            Events.trigger(Evt.CACHE_READY) # should this trigger if error?
            logger.debug('T%d: Page cache built in: %fs', timing['start'], monotonic() - timing['build_start'])

        timing['end'] = monotonic()

        logger.info('T%d: Results returned in: %fs', timing['start'], timing['end'] - timing['start'])

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

    emit_current_team_leaderboard()

    if ('nobroadcast' in params):
        emit('leaderboard', emit_payload)
    else:
        SOCKET_IO.emit('leaderboard', emit_payload)

def emit_current_team_leaderboard(**params):
    '''Emits team leaderboard.'''
    global RACE
    race_format = getCurrentRaceFormat()

    if race_format.team_racing_mode:
        results = Results.calc_team_leaderboard(RACE)
        RACE.team_results = results
        RACE.team_cacheStatus = Results.CacheStatus.VALID
        emit_payload = results
    else:
        emit_payload = None

    if ('nobroadcast' in params):
        emit('team_leaderboard', emit_payload)
    else:
        SOCKET_IO.emit('team_leaderboard', emit_payload)

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

def emit_race_status_message(**params):
    '''Emits given team-racing status info.'''
    global RACE
    emit_payload = {'team_laps_str': RACE.status_message}
    if ('nobroadcast' in params):
        emit('race_status_message', emit_payload)
    else:
        SOCKET_IO.emit('race_status_message', emit_payload)

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

def emit_phonetic_split(pilot_id, split_id, split_time, **params):
    '''Emits phonetic split-pass data.'''
    phonetic_name = Database.Pilot.query.get(pilot_id).phonetic or \
                    Database.Pilot.query.get(pilot_id).callsign
    phonetic_time = RHUtils.phonetictime_format(split_time)
    emit_payload = {
        'pilot_name': phonetic_name,
        'split_id': str(split_id+1),
        'split_time': phonetic_time
    }
    if ('nobroadcast' in params):
        emit('phonetic_split_call', emit_payload)
    else:
        SOCKET_IO.emit('phonetic_split_call', emit_payload)

def emit_split_pass_info(pilot_id, split_id, split_time):
    emit_current_laps()  # update all laps on the race page
    emit_phonetic_split(pilot_id, split_id, split_time)

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
                print(vrx)
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
@catchLogExceptionsWrapper
def set_vrx_node(data):
    vrx_id = data['vrx_id']
    node = data['node']

    if vrx_controller:
        vrx_controller.set_seat_number(serial_num=vrx_id, desired_seat_num=node)
        logger.info("Set VRx {0} to node {1}".format(vrx_id, node))
    else:
        logger.error("Can't set VRx {0} to node {1}: Controller unavailable".format(vrx_id, node))

@catchLogExceptionsWrapper
def emit_pass_record(node, lap_time_stamp):
    '''Emits 'pass_record' message (will be consumed by slave timers in cluster, etc).'''
    payload = {
        'node': node.index,
        'frequency': node.frequency,
        'timestamp': lap_time_stamp + RACE.start_time_epoch_ms
    }
    SOCKET_IO.emit('pass_record', payload)

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
                emit_cluster_status()

            # collect vrx lock status
            if (heartbeat_thread_function.iter_tracker % (10*HEARTBEAT_DATA_RATE_FACTOR)) == 0:
                if vrx_controller:
                    # if vrx_controller.has_connection
                    vrx_controller.get_seat_lock_status()
                    vrx_controller.request_variable_status()

            if (heartbeat_thread_function.iter_tracker % (10*HEARTBEAT_DATA_RATE_FACTOR)) == 4:
                # emit display status with offset
                if vrx_controller:
                    emit_vrx_list()

            # emit environment data less often:
            if (heartbeat_thread_function.iter_tracker % (20*HEARTBEAT_DATA_RATE_FACTOR)) == 0:
                SENSORS.update_environmental_data()
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
                rep_str = INTERFACE.get_intf_error_report_str()
                if rep_str:
                    logger.info(rep_str)

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
    delta_time = monotonic() - PROGRAM_START_MTONIC
    milli_sec = delta_time * 1000.0
    return milli_sec

def check_emit_race_status_message(RACE, **params):
    if RACE.win_status not in [WinStatus.DECLARED, WinStatus.TIE]: # don't call after declared result
        emit_race_status_message(**params)

@catchLogExceptionsWrapper
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

                    # if node EnterAt/ExitAt values need to be restored then do it soon
                    if node.start_thresh_lower_flag:
                        node.start_thresh_lower_time = monotonic()

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
                    if race_format is SLAVE_RACE_FORMAT:
                        min_lap = 0  # don't enforce min-lap time if running as slave timer
                        min_lap_behavior = 0
                    else:
                        min_lap = Options.getInt("MinLapSec")
                        min_lap_behavior = Options.getInt("MinLapBehavior")

                    if RACE.timer_running is False:
                        RACE.node_has_finished[node.index] = True

                    lap_ok_flag = True
                    if lap_number != 0:  # if initial lap then always accept and don't check lap time; else:
                        if lap_time < (min_lap * 1000):  # if lap time less than minimum
                            node.under_min_lap_count += 1
                            logger.info('Pass record under lap minimum ({3}): Node={0}, Lap={1}, LapTime={2}, Count={4}' \
                                       .format(node.index+1, lap_number, RHUtils.time_format(lap_time), min_lap, node.under_min_lap_count))
                            if min_lap_behavior != 0:  # if behavior is 'Discard New Short Laps'
                                lap_ok_flag = False

                    if lap_ok_flag:

                        # emit 'pass_record' message (via thread to make sure we're not blocked)
                        gevent.spawn(emit_pass_record, node, lap_time_stamp)

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

                        logger.debug('Pass record: Node: {0}, Lap: {1}, Lap time: {2}' \
                            .format(node.index+1, lap_number, RHUtils.time_format(lap_time)))
                        emit_current_laps() # update all laps on the race page
                        emit_current_leaderboard() # generate and update leaderboard
                        check_emit_race_status_message(RACE) # Update race status message

                        if lap_number > 0:
                            # announce lap
                            if RACE.format.team_racing_mode:
                                team = Database.Pilot.query.get(pilot_id).team
                                team_data = RACE.team_results['meta']['teams'][team]
                                emit_phonetic_data(pilot_id, lap_number, lap_time, team, team_data['laps'])
                            else:
                                emit_phonetic_data(pilot_id, lap_number, lap_time, None, None)

                            check_win_condition(RACE, INTERFACE) # check for and announce winner
                        elif lap_number == 0:
                            emit_first_pass_registered(node.index) # play first-pass sound
                    else:
                        # record lap as 'deleted'
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

def check_win_condition(RACE, INTERFACE, **kwargs):
    previous_win_status = RACE.win_status

    win_status = Results.check_win_condition(RACE, INTERFACE, **kwargs)

    if win_status is not None:
        race_format = RACE.format
        RACE.win_status = win_status['status']

        if win_status['status'] == WinStatus.DECLARED:
            # announce winner
            if race_format.team_racing_mode:
                RACE.status_message = __('Winner is') + ' ' + __('Team') + ' ' + win_status['data']['name']
                emit_race_status_message()
                emit_phonetic_text(RACE.status_message)
            else:
                RACE.status_message = __('Winner is') + ' ' + win_status['data']['callsign']
                emit_race_status_message()
                win_phon_name = Database.Pilot.query.get(win_status['data']['pilot_id']).phonetic
                if len(win_phon_name) <= 0:  # if no phonetic then use callsign
                    win_phon_name = win_status['data']['callsign']
                emit_phonetic_text(__('Winner is') + ' ' + win_phon_name, 'race_winner')
        elif win_status['status'] == WinStatus.TIE:
            # announce tied
            if win_status['status'] != previous_win_status:
                RACE.status_message = __('Race Tied')
                emit_race_status_message()
                emit_phonetic_text(RACE.status_message, 'race_winner')
        elif win_status['status'] == WinStatus.OVERTIME:
            # announce overtime
            if win_status['status'] != previous_win_status:
                RACE.status_message = __('Race Tied: Overtime')
                emit_race_status_message()
                emit_phonetic_text(RACE.status_message, 'race_winner')

        if 'max_consideration' in win_status:
            logger.debug("Waiting {0}ms to declare winner.".format(win_status['max_consideration']))
            gevent.sleep(win_status['max_consideration'] / 1000)
            if 'start_token' in kwargs and RACE.start_token == kwargs['start_token']:
                logger.debug("Maximum win condition consideration time has expired.")
                check_win_condition(RACE, INTERFACE, forced=True)

    return win_status

@catchLogExceptionsWrapper
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

@catchLogExceptionsWrapper
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
    DB.session.add(Database.RaceFormat(name=__("2:00 Standard Race"),
                             race_mode=0,
                             race_time_sec=120,
                             start_delay_min=2,
                             start_delay_max=5,
                             staging_tones=1,
                             number_laps_win=0,
                             win_condition=WinCondition.MOST_PROGRESS,
                             team_racing_mode=False))
    DB.session.add(Database.RaceFormat(name=__("1:30 Whoop Sprint"),
                             race_mode=0,
                             race_time_sec=90,
                             start_delay_min=2,
                             start_delay_max=5,
                             staging_tones=2,
                             number_laps_win=0,
                             win_condition=WinCondition.MOST_PROGRESS,
                             team_racing_mode=False))
    DB.session.add(Database.RaceFormat(name=__("3:00 Extended Race"),
                             race_mode=0,
                             race_time_sec=210,
                             start_delay_min=2,
                             start_delay_max=5,
                             staging_tones=2,
                             number_laps_win=0,
                             win_condition=WinCondition.MOST_PROGRESS,
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
    DB.session.add(Database.RaceFormat(name=__("Fastest Lap Qualifier"),
                             race_mode=0,
                             race_time_sec=120,
                             start_delay_min=2,
                             start_delay_max=5,
                             staging_tones=1,
                             number_laps_win=0,
                             win_condition=WinCondition.FASTEST_LAP,
                             team_racing_mode=False))
    DB.session.add(Database.RaceFormat(name=__("Fastest 3 Laps Qualifier"),
                             race_mode=0,
                             race_time_sec=120,
                             start_delay_min=2,
                             start_delay_max=5,
                             staging_tones=1,
                             number_laps_win=0,
                             win_condition=WinCondition.FASTEST_3_CONSECUTIVE,
                             team_racing_mode=False))
    DB.session.add(Database.RaceFormat(name=__("Lap Count Only"),
                             race_mode=0,
                             race_time_sec=120,
                             start_delay_min=2,
                             start_delay_max=5,
                             staging_tones=1,
                             number_laps_win=0,
                             win_condition=WinCondition.MOST_LAPS,
                             team_racing_mode=False))
    DB.session.add(Database.RaceFormat(name=__("Team / Most Laps Wins"),
                             race_mode=0,
                             race_time_sec=120,
                             start_delay_min=2,
                             start_delay_max=5,
                             staging_tones=2,
                             number_laps_win=0,
                             win_condition=WinCondition.MOST_PROGRESS,
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
    DB.session.add(Database.RaceFormat(name=__("Team / Fastest Lap Average"),
                             race_mode=0,
                             race_time_sec=120,
                             start_delay_min=2,
                             start_delay_max=5,
                             staging_tones=2,
                             number_laps_win=0,
                             win_condition=WinCondition.FASTEST_LAP,
                             team_racing_mode=True))
    DB.session.add(Database.RaceFormat(name=__("Team / Fastest 3 Consecutive Average"),
                             race_mode=0,
                             race_time_sec=120,
                             start_delay_min=2,
                             start_delay_max=5,
                             staging_tones=2,
                             number_laps_win=0,
                             win_condition=WinCondition.FASTEST_3_CONSECUTIVE,
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

    Options.set("startThreshLowerAmount", "0")
    Options.set("startThreshLowerDuration", "0")
    Options.set("nextHeatBehavior", "0")

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
        RHUtils.checkSetFileOwnerPi(DB_BKP_DIR_NAME)
        if os.path.isfile(bkp_name):  # if target file exists then use 'now' timestamp
            time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            bkp_name = DB_BKP_DIR_NAME + '/' + dbname + '_' + time_str + dbext
        if copy_flag:
            shutil.copy2(DB_FILE_NAME, bkp_name);
            logger.info('Copied database file to:  ' + bkp_name)
        else:
            os.renames(DB_FILE_NAME, bkp_name);
            logger.info('Moved old database file to:  ' + bkp_name)
        RHUtils.checkSetFileOwnerPi(bkp_name)
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
                                setattr(new_data, col, row_data[col])
                            else:
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
        heatNode_query_data = get_legacy_table_data(metadata, 'heat_node')
        raceFormat_query_data = get_legacy_table_data(metadata, 'race_format')
        profiles_query_data = get_legacy_table_data(metadata, 'profiles')
        raceClass_query_data = get_legacy_table_data(metadata, 'race_class')
        raceMeta_query_data = get_legacy_table_data(metadata, 'saved_race_meta')
        racePilot_query_data = get_legacy_table_data(metadata, 'saved_pilot_race')
        raceLap_query_data = get_legacy_table_data(metadata, 'saved_race_lap')

        engine.dispose() # close connection after loading

        migrate_db_api = Options.getInt('server_api')

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
            "osd_positionHeader",
            "startThreshLowerAmount",
            "startThreshLowerDuration",
            "nextHeatBehavior"
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
            restore_table(Database.HeatNode, heatNode_query_data, defaults={
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

    clean_results_cache()

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
                logger.debug('VRxController disabled by config option')
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
    global vrx_controller
    logger.info('Killing VRxController')
    vrx_controller = None

#
# Program Initialize
#

logger.info('Release: {0} / Server API: {1} / Latest Node API: {2}'.format(RELEASE_VERSION, SERVER_API, NODE_API_BEST))
logger.debug('Program started at {0:.1f}'.format(PROGRAM_START_EPOCH_TIME))
RHUtils.idAndLogSystemInfo()

# log results of module initializations
Config.logInitResultMessage()
Language.logInitResultMessage()

# check if current log file owned by 'root' and change owner to 'pi' user if so
if Current_log_path_name and RHUtils.checkSetFileOwnerPi(Current_log_path_name):
    logger.debug("Changed log file owner from 'root' to 'pi' (file: '{0}')".format(Current_log_path_name))
    RHUtils.checkSetFileOwnerPi(log.LOG_DIR_NAME)  # also make sure 'log' dir not owned by 'root'

logger.info("Using log file: {0}".format(Current_log_path_name))

hardwareHelpers = {}
for helper in search_modules(suffix='helper'):
    hardwareHelpers[helper.__name__] = helper.create()

interface_type = os.environ.get('RH_INTERFACE', 'RH')
try:
    interfaceModule = importlib.import_module(interface_type + 'Interface')
    INTERFACE = interfaceModule.get_hardware_interface(config=Config, **hardwareHelpers)
except (ImportError, RuntimeError, IOError) as ex:
    logger.info('Unable to initialize nodes via ' + interface_type + 'Interface:  ' + str(ex))
if not INTERFACE or not INTERFACE.nodes or len(INTERFACE.nodes) <= 0:
    if not Config.SERIAL_PORTS or len(Config.SERIAL_PORTS) <= 0:
        interfaceModule = importlib.import_module('MockInterface')
        INTERFACE = interfaceModule.get_hardware_interface(config=Config, **hardwareHelpers)
    else:
        try:
            importlib.import_module('serial')
            logger.info('Unable to initialize specified serial node(s): {0}'.format(Config.SERIAL_PORTS))
        except ImportError:
            logger.info("Unable to import library for serial node(s) - is 'pyserial' installed?")
        log.wait_for_queue_empty()
        sys.exit()

CLUSTER = ClusterNodeSet()
hasMirrors = False
try:
    for index, slave_info in enumerate(Config.GENERAL['SLAVES']):
        if isinstance(slave_info, string_types):
            slave_info = {'address': slave_info, 'mode': SlaveNode.TIMER_MODE}
        if 'timeout' not in slave_info:
            slave_info['timeout'] = Config.GENERAL['SLAVE_TIMEOUT']
        if 'mode' in slave_info and slave_info['mode'] == SlaveNode.MIRROR_MODE:
            hasMirrors = True
        elif hasMirrors:
            logger.info('** Mirror slaves must be last - ignoring remaining slave config **')
            break
        slave = SlaveNode(index, slave_info, RACE, DB, getCurrentProfile, \
                          emit_split_pass_info, monotonic_to_epoch_millis)
        CLUSTER.addSlave(slave)
except:
    logger.exception("Error adding slave to cluster")

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
    # if I2C nodes then only report comm errors if >= 1.0%
    if hasattr(INTERFACE.nodes[0], 'i2c_addr'):
        INTERFACE.set_intf_error_report_percent_limit(1.0)

# Delay to get I2C addresses through interface class initialization
gevent.sleep(0.500)

SENSORS.discover(config=Config.SENSORS, **hardwareHelpers)

# if no DB file then create it now (before "__()" fn used in 'buildServerInfo()')
db_inited_flag = False
if not os.path.exists(DB_FILE_NAME):
    logger.info("No '{0}' file found; creating initial database".format(DB_FILE_NAME))
    db_init()
    db_inited_flag = True

# check if DB file owned by 'root' and change owner to 'pi' user if so
if RHUtils.checkSetFileOwnerPi(DB_FILE_NAME):
    logger.debug("Changed DB-file owner from 'root' to 'pi' (file: '{0}')".format(DB_FILE_NAME))

# check if directories owned by 'root' and change owner to 'pi' user if so
if RHUtils.checkSetFileOwnerPi(DB_BKP_DIR_NAME):
    logger.info("Changed '{0}' dir owner from 'root' to 'pi'".format(DB_BKP_DIR_NAME))
if RHUtils.checkSetFileOwnerPi(log.LOGZIP_DIR_NAME):
    logger.info("Changed '{0}' dir owner from 'root' to 'pi'".format(log.LOGZIP_DIR_NAME))

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
        if Options.getInt('server_api') < SERVER_API:
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
current_profile = Options.getInt("currentProfile")
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
    led_brightness = Options.getInt("ledBrightness")
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

# register endpoints
import json_endpoints

APP.register_blueprint(json_endpoints.createBlueprint(Database, Options, Results, RACE, serverInfo, getCurrentProfile))


def start(port_val = Config.GENERAL['HTTP_PORT']):
    if not Options.get("secret_key"):
        Options.set("secret_key", ''.join(random.choice(string.ascii_letters) for i in range(50)))

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
    rep_str = INTERFACE.get_intf_error_report_str(True)
    if rep_str:
        logger.info(rep_str)
    log.wait_for_queue_empty()

# Start HTTP server
if __name__ == '__main__':
    start()
