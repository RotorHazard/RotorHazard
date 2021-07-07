'''RotorHazard server script'''
RELEASE_VERSION = "3.1.0-dev.8" # Public release version code
SERVER_API = 32 # Server API version
NODE_API_SUPPORTED = 18 # Minimum supported node version
NODE_API_BEST = 35 # Most recent node API
JSON_API = 3 # JSON API version

# This must be the first import for the time being. It is
# necessary to set up logging *before* anything else
# because there is a lot of code run through imports, and
# we would miss messages otherwise.
import logging
import log
from datetime import datetime
from monotonic import monotonic
import RHTimeFns

log.early_stage_setup()
logger = logging.getLogger(__name__)

EPOCH_START = RHTimeFns.getEpochStartTime()

# program-start time, in milliseconds since 1970-01-01
PROGRAM_START_EPOCH_TIME = int((RHTimeFns.getUtcDateTimeNow() - EPOCH_START).total_seconds() * 1000)

# program-start time (in milliseconds, starting at zero)
PROGRAM_START_MTONIC = monotonic()

# offset for converting 'monotonic' time to epoch milliseconds since 1970-01-01
MTONIC_TO_EPOCH_MILLIS_OFFSET = PROGRAM_START_EPOCH_TIME - 1000.0*PROGRAM_START_MTONIC

logger.info('RotorHazard v{0}'.format(RELEASE_VERSION))

# Normal importing resumes here
import gevent.monkey
gevent.monkey.patch_all()

import io
import os
import sys
import base64
import subprocess
import importlib
import copy
from functools import wraps
from collections import OrderedDict
from six import unichr, string_types

from flask import Flask, send_file, request, Response, session, templating, redirect
from flask_socketio import SocketIO, emit

import socket
import random
import string
import json

import Config
import Database
import Results
import Language
import RHData
import RHUtils
from RHUtils import catchLogExceptionsWrapper
from ClusterNodeSet import SecondaryNode, ClusterNodeSet
import PageCache
from util.SendAckQueue import SendAckQueue
import RHGPIO
from util.ButtonInputHandler import ButtonInputHandler
import util.stm32loader as stm32loader

# Events manager
from eventmanager import Evt, EventManager

Events = EventManager()

# LED imports
from led_event_manager import LEDEventManager, NoLEDManager, ClusterLEDManager, LEDEvent, Color, ColorVal, ColorPattern, hexToColor

sys.path.append('../interface')
sys.path.append('/home/pi/RotorHazard/src/interface')  # Needed to run on startup

from Plugins import Plugins, search_modules  #pylint: disable=import-error
from Sensors import Sensors  #pylint: disable=import-error
import RHRace
from RHRace import StartBehavior, WinCondition, WinStatus, RaceStatus
from data_export import DataExportManager

APP = Flask(__name__, static_url_path='/static')

HEARTBEAT_THREAD = None
BACKGROUND_THREADS_ENABLED = True
HEARTBEAT_DATA_RATE_FACTOR = 5

ERROR_REPORT_INTERVAL_SECS = 600  # delay between comm-error reports to log

DB_FILE_NAME = 'database.db'
DB_BKP_DIR_NAME = 'db_bkp'
IMDTABLER_JAR_NAME = 'static/IMDTabler.jar'
NODE_FW_PATHNAME = "firmware/RH_S32_BPill_node.bin"

# check if 'log' directory owned by 'root' and change owner to 'pi' user if so
if RHUtils.checkSetFileOwnerPi(log.LOG_DIR_NAME):
    logger.info("Changed '{0}' dir owner from 'root' to 'pi'".format(log.LOG_DIR_NAME))

# command-line arguments:
CMDARG_VERSION_LONG_STR = '--version'    # show program version and exit
CMDARG_VERSION_SHORT_STR = '-v'          # show program version and exit
CMDARG_ZIP_LOGS_STR = '--ziplogs'        # create logs .zip file
CMDARG_JUMP_TO_BL_STR = '--jumptobl'     # send jump-to-bootloader command to node
CMDARG_FLASH_BPILL_STR = '--flashbpill'  # flash firmware onto S32_BPill processor

if __name__ == '__main__' and len(sys.argv) > 1:
    if CMDARG_VERSION_LONG_STR in sys.argv or CMDARG_VERSION_SHORT_STR in sys.argv:
        sys.exit(0)
    if CMDARG_ZIP_LOGS_STR in sys.argv:
        log.create_log_files_zip(logger, Config.CONFIG_FILE_NAME, DB_FILE_NAME)
        sys.exit(0)
    if CMDARG_JUMP_TO_BL_STR not in sys.argv:  # handle jump-to-bootloader argument later
        if CMDARG_FLASH_BPILL_STR in sys.argv:
            flashPillArgIdx = sys.argv.index(CMDARG_FLASH_BPILL_STR) + 1
            flashPillPortStr = Config.SERIAL_PORTS[0] if Config.SERIAL_PORTS and \
                                                len(Config.SERIAL_PORTS) > 0 else None
            flashPillSrcStr = sys.argv[flashPillArgIdx] if flashPillArgIdx < len(sys.argv) else None
            if flashPillSrcStr and flashPillSrcStr.startswith("--"):  # use next arg as src file (optional)
                flashPillSrcStr = None                       #  unless arg is switch param
            flashPillSuccessFlag = stm32loader.flash_file_to_stm32(flashPillPortStr, flashPillSrcStr)
            sys.exit(0 if flashPillSuccessFlag else 1)
        print("Unrecognized command-line argument(s): {0}".format(sys.argv[1:]))
        sys.exit(1)

TEAM_NAMES_LIST = [str(unichr(i)) for i in range(65, 91)]  # list of 'A' to 'Z' strings

BASEDIR = os.getcwd()
APP.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASEDIR, DB_FILE_NAME)
APP.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
Database.DB.init_app(APP)
Database.DB.app = APP

# start SocketIO service
SOCKET_IO = SocketIO(APP, async_mode='gevent', cors_allowed_origins=Config.GENERAL['CORS_ALLOWED_HOSTS'])

# this is the moment where we can forward log-messages to the frontend, and
# thus set up logging for good.
Current_log_path_name = log.later_stage_setup(Config.LOGGING, SOCKET_IO)

INTERFACE = None  # initialized later
SENSORS = Sensors()
CLUSTER = None    # initialized later
ClusterSendAckQueueObj = None
serverInfo = None
serverInfoItems = None
Use_imdtabler_jar_flag = False  # set True if IMDTabler.jar is available
vrx_controller = None
server_ipaddress_str = None
ShutdownButtonInputHandler = None
Server_secondary_mode = None

RACE = RHRace.RHRace() # For storing race management variables
LAST_RACE = None
SECONDARY_RACE_FORMAT = None
RHData = RHData.RHData(Database, Events, RACE, SERVER_API, DB_FILE_NAME, DB_BKP_DIR_NAME) # Primary race data storage
PageCache = PageCache.PageCache(RHData, Events) # For storing page cache
Language = Language.Language(RHData) # initialize language
__ = Language.__ # Shortcut to translation function
RHData.late_init(PageCache, Language) # Give RHData additional references

TONES_NONE = 0
TONES_ONE = 1
TONES_ALL = 2

ui_server_messages = {}
def set_ui_message(mainclass, message, header=None, subclass=None):
    item = {}
    item['message'] = message
    if header:
        item['header'] = __(header)
    if subclass:
        item['subclass'] = subclass
    ui_server_messages[mainclass] = item

# convert 'monotonic' time to epoch milliseconds since 1970-01-01
def monotonic_to_epoch_millis(secs):
    return 1000.0*secs + MTONIC_TO_EPOCH_MILLIS_OFFSET

# Wrapper to be used as a decorator on callback functions that do database calls,
#  so their exception details are sent to the log file (instead of 'stderr')
#  and the database session is closed on thread exit (prevents DB-file handles left open).
def catchLogExcDBCloseWrapper(func):
    def wrapper(*args, **kwargs):
        try:
            retVal = func(*args, **kwargs)
            RHData.close()
            return retVal
        except:
            logger.exception("Exception via catchLogExcDBCloseWrapper")
            try:
                RHData.close()
            except:
                logger.exception("Error closing DB session in catchLogExcDBCloseWrapper-catch")
    return wrapper

# Return 'DEF_NODE_FWUPDATE_URL' config value; if not set in 'config.json'
#  then return default value based on BASEDIR and server RELEASE_VERSION
def getDefNodeFwUpdateUrl():
    try:
        if Config.GENERAL['DEF_NODE_FWUPDATE_URL']:
            return Config.GENERAL['DEF_NODE_FWUPDATE_URL']
        if RELEASE_VERSION.lower().find("dev") > 0:  # if "dev" server version then
            retStr = stm32loader.DEF_BINSRC_STR      # use current "dev" firmware at URL
        else:
            # return path that is up two levels from BASEDIR, and then NODE_FW_PATHNAME
            retStr = os.path.abspath(os.path.join(os.path.join(os.path.join(BASEDIR, os.pardir), \
                                                             os.pardir), NODE_FW_PATHNAME))
        # check if file with better-matching processor type (i.e., STM32F4) is available
        try:
            curTypStr = INTERFACE.nodes[0].firmware_proctype_str if len(INTERFACE.nodes) else None
            if curTypStr:
                fwTypStr = getFwfileProctypeStr(retStr)
                if fwTypStr and curTypStr != fwTypStr:
                    altFwFNameStr = RHUtils.appendToBaseFilename(retStr, ('_'+curTypStr))
                    altFwTypeStr = getFwfileProctypeStr(altFwFNameStr)
                    if curTypStr == altFwTypeStr:
                        logger.debug("Using better-matching node-firmware file: " + altFwFNameStr)
                        return altFwFNameStr
        except Exception as ex:
            logger.debug("Error checking fw type vs current type: " + str(ex))
        return retStr
    except:
        logger.exception("Error determining value for 'DEF_NODE_FWUPDATE_URL'")
    return "/home/pi/RotorHazard/" + NODE_FW_PATHNAME

# Returns the processor-type string from the given firmware file, or None if not found
def getFwfileProctypeStr(fileStr):
    dataStr = None
    try:
        dataStr = stm32loader.load_source_file(fileStr, False)
        if dataStr:
            return RHUtils.findPrefixedSubstring(dataStr, INTERFACE.FW_PROCTYPE_PREFIXSTR, \
                                                 INTERFACE.FW_TEXT_BLOCK_SIZE)
    except Exception as ex:
        logger.debug("Error processing file '{}' in 'getFwfileProctypeStr()': {}".format(fileStr, ex))
    return None

def getCurrentProfile():
    current_profile = RHData.get_optionInt('currentProfile')
    return RHData.get_profile(current_profile)

def getCurrentRaceFormat():
    if RACE.format is None:
        val = RHData.get_optionInt('currentFormat')
        if val:
            race_format = RHData.get_raceFormat(val)
            if not race_format:
                race_format = RHData.get_first_raceFormat()
                RHData.set_option('currentFormat', race_format.id)
        else:
            race_format = RHData.get_first_raceFormat()

        # create a shared instance
        RACE.format = RHRaceFormat.copy(race_format)
        RACE.format.id = race_format.id  #pylint: disable=attribute-defined-outside-init
    return RACE.format

def getCurrentDbRaceFormat():
    if RACE.format is None or RHRaceFormat.isDbBased(RACE.format):
        val = RHData.get_optionInt('currentFormat')
        return RHData.get_raceFormat(val)
    else:
        return None

def setCurrentRaceFormat(race_format, **kwargs):
    if RHRaceFormat.isDbBased(race_format): # stored in DB, not internal race format
        RHData.set_option('currentFormat', race_format.id)
        # create a shared instance
        RACE.format = RHRaceFormat.copy(race_format)
        RACE.format.id = race_format.id  #pylint: disable=attribute-defined-outside-init
        RACE.cacheStatus = Results.CacheStatus.INVALID  # refresh leaderboard
        RACE.team_cacheStatus = Results.CacheStatus.INVALID
    else:
        RACE.format = race_format

    if 'silent' not in kwargs:
        emit_current_laps()

class RHRaceFormat():
    def __init__(self, name, race_mode, race_time_sec, start_delay_min, start_delay_max, staging_tones, number_laps_win, win_condition, team_racing_mode, start_behavior):
        self.name = name
        self.race_mode = race_mode
        self.race_time_sec = race_time_sec
        self.start_delay_min = start_delay_min
        self.start_delay_max = start_delay_max
        self.staging_tones = staging_tones
        self.number_laps_win = number_laps_win
        self.win_condition = win_condition
        self.team_racing_mode = team_racing_mode
        self.start_behavior = start_behavior

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
                            team_racing_mode=race_format.team_racing_mode,
                            start_behavior=race_format.start_behavior)

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
def render_index():
    '''Route to home page.'''
    return render_template('home.html', serverInfo=serverInfo,
                           getOption=RHData.get_option, __=__, Debug=Config.GENERAL['DEBUG'])

@APP.route('/event')
def render_event():
    '''Route to heat summary page.'''
    return render_template('event.html', num_nodes=RACE.num_nodes, serverInfo=serverInfo, getOption=RHData.get_option, __=__)

@APP.route('/results')
def render_results():
    '''Route to round summary page.'''
    return render_template('results.html', serverInfo=serverInfo, getOption=RHData.get_option, __=__, Debug=Config.GENERAL['DEBUG'])

@APP.route('/run')
@requires_auth
def render_run():
    '''Route to race management page.'''
    frequencies = [node.frequency for node in INTERFACE.nodes]
    nodes = []
    for idx, freq in enumerate(frequencies):
        if freq:
            nodes.append({
                'freq': freq,
                'index': idx
            })

    return render_template('run.html', serverInfo=serverInfo, getOption=RHData.get_option, __=__,
        led_enabled=(led_manager.isEnabled() or (CLUSTER and CLUSTER.hasRecEventsSecondaries())),
        vrx_enabled=vrx_controller!=None,
        num_nodes=RACE.num_nodes,
        nodes=nodes,
        cluster_has_secondaries=(CLUSTER and CLUSTER.hasSecondaries()))

@APP.route('/current')
def render_current():
    '''Route to race management page.'''
    frequencies = [node.frequency for node in INTERFACE.nodes]
    nodes = []
    for idx, freq in enumerate(frequencies):
        if freq:
            nodes.append({
                'freq': freq,
                'index': idx
            })

    return render_template('current.html', serverInfo=serverInfo, getOption=RHData.get_option, __=__,
        num_nodes=RACE.num_nodes,
        nodes=nodes,
        cluster_has_secondaries=(CLUSTER and CLUSTER.hasSecondaries()))

@APP.route('/marshal')
@requires_auth
def render_marshal():
    '''Route to race management page.'''
    return render_template('marshal.html', serverInfo=serverInfo, getOption=RHData.get_option, __=__,
        num_nodes=RACE.num_nodes)

@APP.route('/settings')
@requires_auth
def render_settings():
    '''Route to settings page.'''
    server_messages_formatted = ''
    if len(ui_server_messages):
        for key, item in ui_server_messages.items():
            message = '<li class="' + key
            if 'subclass' in item and item['subclass']:
                message += ' ' + key + '-' + item['subclass']
            if 'header' in item and item['header']:
                message += ' ' + item['header'].lower()
            message += '">'
            if 'header' in item and item['header']:
                message += '<strong>' + item['header'] + ':</strong> '
            message += item['message']
            message += '</li>'
            server_messages_formatted += message
    if Config.GENERAL['configFile'] == -1:
        server_messages_formatted += '<li class="config config-bad warning"><strong>' + __('Warning') + ': ' + '</strong>' + __('The config.json file is invalid. Falling back to default configuration.') + '<br />' + __('See <a href="/docs?d=User Guide.md#set-up-config-file">User Guide</a> for more information.') + '</li>'
    elif Config.GENERAL['configFile'] == 0:
        server_messages_formatted += '<li class="config config-none warning"><strong>' + __('Warning') + ': ' + '</strong>' + __('No configuration file was loaded. Falling back to default configuration.') + '<br />' + __('See <a href="/docs?d=User Guide.md#set-up-config-file">User Guide</a> for more information.') +'</li>'

    return render_template('settings.html', serverInfo=serverInfo, getOption=RHData.get_option, __=__,
        led_enabled=(led_manager.isEnabled() or (CLUSTER and CLUSTER.hasRecEventsSecondaries())),
        led_events_enabled=led_manager.isEnabled(),
        vrx_enabled=vrx_controller!=None,
        num_nodes=RACE.num_nodes,
        server_messages=server_messages_formatted,
        cluster_has_secondaries=(CLUSTER and CLUSTER.hasSecondaries()),
        node_fw_updatable=(INTERFACE.get_fwupd_serial_name()!=None),
        is_raspberry_pi=RHUtils.isSysRaspberryPi(),
        Debug=Config.GENERAL['DEBUG'])

@APP.route('/streams')
def render_stream():
    '''Route to stream index.'''
    return render_template('streams.html', serverInfo=serverInfo, getOption=RHData.get_option, __=__,
        num_nodes=RACE.num_nodes)

@APP.route('/stream/results')
def render_stream_results():
    '''Route to current race leaderboard stream.'''
    return render_template('streamresults.html', serverInfo=serverInfo, getOption=RHData.get_option, __=__,
        num_nodes=RACE.num_nodes)

@APP.route('/stream/node/<int:node_id>')
def render_stream_node(node_id):
    '''Route to single node overlay for streaming.'''
    if node_id <= RACE.num_nodes:
        return render_template('streamnode.html', serverInfo=serverInfo, getOption=RHData.get_option, __=__,
            node_id=node_id-1
        )
    else:
        return False

@APP.route('/stream/class/<int:class_id>')
def render_stream_class(class_id):
    '''Route to class leaderboard display for streaming.'''
    return render_template('streamclass.html', serverInfo=serverInfo, getOption=RHData.get_option, __=__,
        class_id=class_id
    )

@APP.route('/stream/heat/<int:heat_id>')
def render_stream_heat(heat_id):
    '''Route to heat display for streaming.'''
    return render_template('streamheat.html', serverInfo=serverInfo, getOption=RHData.get_option, __=__,
        num_nodes=RACE.num_nodes,
        heat_id=heat_id
    )

@APP.route('/scanner')
@requires_auth
def render_scanner():
    '''Route to scanner page.'''

    return render_template('scanner.html', serverInfo=serverInfo, getOption=RHData.get_option, __=__,
        num_nodes=RACE.num_nodes)

@APP.route('/decoder')
@requires_auth
def render_decoder():
    '''Route to race management page.'''
    return render_template('decoder.html', serverInfo=serverInfo, getOption=RHData.get_option, __=__,
        num_nodes=RACE.num_nodes)

@APP.route('/imdtabler')
def render_imdtabler():
    '''Route to IMDTabler page.'''
    return render_template('imdtabler.html', serverInfo=serverInfo, getOption=RHData.get_option, __=__)

@APP.route('/updatenodes')
@requires_auth
def render_updatenodes():
    '''Route to update nodes page.'''
    return render_template('updatenodes.html', serverInfo=serverInfo, getOption=RHData.get_option, __=__, \
                           fw_src_str=getDefNodeFwUpdateUrl())

# Debug Routes

@APP.route('/hardwarelog')
@requires_auth
def render_hardwarelog():
    '''Route to hardware log page.'''
    return render_template('hardwarelog.html', serverInfo=serverInfo, getOption=RHData.get_option, __=__)

@APP.route('/database')
@requires_auth
def render_database():
    '''Route to database page.'''
    return render_template('database.html', serverInfo=serverInfo, getOption=RHData.get_option, __=__,
        pilots=RHData.get_pilots(),
        heats=RHData.get_heats(),
        heatnodes=RHData.get_heatNodes(),
        race_class=RHData.get_raceClasses(),
        savedraceMeta=RHData.get_savedRaceMetas(),
        savedraceLap=RHData.get_savedRaceLaps(),
        profiles=RHData.get_profiles(),
        race_format=RHData.get_raceFormats(),
        globalSettings=RHData.get_options())

@APP.route('/vrxstatus')
@requires_auth
def render_vrxstatus():
    '''Route to VRx status debug page.'''
    return render_template('vrxstatus.html', serverInfo=serverInfo, getOption=RHData.get_option, __=__)

# Documentation Viewer

@APP.route('/docs')
def render_viewDocs():
    '''Route to doc viewer.'''

    folderBase = '../../doc/'

    try:
        docfile = request.args.get('d')

        while docfile[0:2] == '../':
            docfile = docfile[3:]

        docPath = folderBase + docfile

        language = RHData.get_option("currentLanguage")
        if language:
            translated_path = folderBase + language + '/' + docfile
            if os.path.isfile(translated_path):
                docPath = translated_path

        with io.open(docPath, 'r', encoding="utf-8") as f:
            doc = f.read()

        return templating.render_template('viewdocs.html',
            serverInfo=serverInfo,
            getOption=RHData.get_option,
            __=__,
            doc=doc
            )
    except Exception:
        logger.exception("Exception in render_template")
    return "Error rendering documentation"

@APP.route('/img/<path:imgfile>')
def render_viewImg(imgfile):
    '''Route to img called within doc viewer.'''

    folderBase = '../../doc/'
    folderImg = 'img/'

    while imgfile[0:2] == '../':
        imgfile = imgfile[3:]

    imgPath = folderBase + folderImg + imgfile

    language = RHData.get_option("currentLanguage")
    if language:
        translated_path = folderBase + language + '/' + folderImg + imgfile
        if os.path.isfile(translated_path):
            imgPath = translated_path

    return send_file(imgPath)

# Redirect routes (Previous versions/Delta 5)
@APP.route('/race')
def redirect_race():
    return redirect("/run", code=301)

@APP.route('/heats')
def redirect_heats():
    return redirect("/event", code=301)

def start_background_threads(forceFlag=False):
    global BACKGROUND_THREADS_ENABLED
    if BACKGROUND_THREADS_ENABLED or forceFlag:
        BACKGROUND_THREADS_ENABLED = True
        INTERFACE.start()
        global HEARTBEAT_THREAD
        if HEARTBEAT_THREAD is None:
            HEARTBEAT_THREAD = gevent.spawn(heartbeat_thread_function)
            logger.debug('Heartbeat thread started')
        start_shutdown_button_thread()

def stop_background_threads():
    try:
        stop_shutdown_button_thread()
        if CLUSTER:
            CLUSTER.shutdown()
        global BACKGROUND_THREADS_ENABLED
        BACKGROUND_THREADS_ENABLED = False
        global HEARTBEAT_THREAD
        if HEARTBEAT_THREAD:
            logger.info('Stopping heartbeat thread')
            HEARTBEAT_THREAD.kill(block=True, timeout=0.5)
            HEARTBEAT_THREAD = None
        INTERFACE.stop()
    except Exception:
        logger.error("Error stopping background threads")

#
# Socket IO Events
#

@SOCKET_IO.on('connect')
@catchLogExceptionsWrapper
def connect_handler():
    '''Starts the interface and a heartbeat thread for rssi.'''
    logger.debug('Client connected')
    start_background_threads()
    # push initial data
    emit_frontend_load(nobroadcast=True)

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
    setCurrentRaceFormat(SECONDARY_RACE_FORMAT)
    emit_race_format()
    on_stage_race()

# Cluster events

def emit_cluster_msg_to_primary(messageType, messagePayload, waitForAckFlag=True):
    '''Emits cluster message to primary timer.'''
    global ClusterSendAckQueueObj
    if not ClusterSendAckQueueObj:
        ClusterSendAckQueueObj = SendAckQueue(20, SOCKET_IO, logger)
    ClusterSendAckQueueObj.put(messageType, messagePayload, waitForAckFlag)

def emit_join_cluster_response():
    '''Emits 'join_cluster_response' message to primary timer.'''
    payload = {
        'server_info': json.dumps(serverInfoItems)
    }
    emit_cluster_msg_to_primary('join_cluster_response', payload, False)

def has_joined_cluster():
    return True if ClusterSendAckQueueObj else False

@SOCKET_IO.on('join_cluster')
@catchLogExceptionsWrapper
def on_join_cluster():
    setCurrentRaceFormat(SECONDARY_RACE_FORMAT)
    emit_race_format()
    logger.info("Joined cluster")
    Events.trigger(Evt.CLUSTER_JOIN, {
                'message': __('Joined cluster')
                })

@SOCKET_IO.on('join_cluster_ex')
@catchLogExceptionsWrapper
def on_join_cluster_ex(data=None):
    global Server_secondary_mode
    prev_mode = Server_secondary_mode
    Server_secondary_mode = str(data.get('mode', SecondaryNode.SPLIT_MODE)) if data else None
    logger.info("Joined cluster" + ((" as '" + Server_secondary_mode + "' timer") \
                                    if Server_secondary_mode else ""))
    if Server_secondary_mode != SecondaryNode.MIRROR_MODE:  # mode is split timer
        try:  # if first time joining and DB contains races then backup DB and clear races
            if prev_mode is None and len(RHData.get_savedRaceMetas()) > 0:
                logger.info("Making database autoBkp and clearing races on split timer")
                RHData.backup_db_file(True, "autoBkp_")
                RHData.clear_race_data()
                reset_current_laps()
                emit_current_laps()
                emit_result_data()
                RHData.delete_old_db_autoBkp_files(Config.GENERAL['DB_AUTOBKP_NUM_KEEP'], \
                                                   "autoBkp_", "DB_AUTOBKP_NUM_KEEP")
        except:
            logger.exception("Error making db-autoBkp / clearing races on split timer")
        setCurrentRaceFormat(SECONDARY_RACE_FORMAT)
        emit_race_format()
    Events.trigger(Evt.CLUSTER_JOIN, {
                'message': __('Joined cluster')
                })
    emit_join_cluster_response()

@SOCKET_IO.on('check_secondary_query')
@catchLogExceptionsWrapper
def on_check_secondary_query(data):
    ''' Check-query received from primary; return response. '''
    payload = {
        'timestamp': monotonic_to_epoch_millis(monotonic())
    }
    SOCKET_IO.emit('check_secondary_response', payload)

@SOCKET_IO.on('cluster_event_trigger')
@catchLogExceptionsWrapper
def on_cluster_event_trigger(data):
    ''' Received event trigger from primary. '''

    evtName = data['evt_name']
    evtArgs = json.loads(data['evt_args']) if 'evt_args' in data else None

    # set mirror timer state
    if Server_secondary_mode == SecondaryNode.MIRROR_MODE:
        if evtName == Evt.RACE_STAGE:
            RACE.race_status = RaceStatus.STAGING
            RACE.results = None
            if led_manager.isEnabled():
                if 'race_node_colors' in evtArgs and isinstance(evtArgs['race_node_colors'], list):
                    led_manager.setDisplayColorCache(evtArgs['race_node_colors'])
                else:
                    RHData.set_option('ledColorMode', 0)
        elif evtName == Evt.RACE_START:
            RACE.race_status = RaceStatus.RACING
        elif evtName == Evt.RACE_STOP:
            RACE.race_status = RaceStatus.DONE
        elif evtName == Evt.LAPS_CLEAR:
            RACE.race_status = RaceStatus.READY
        elif evtName == Evt.RACE_LAP_RECORDED:
            RACE.results = evtArgs['results']

    evtArgs.pop('RACE', None) # remove race if exists

    if evtName not in [Evt.STARTUP, Evt.LED_SET_MANUAL]:
        Events.trigger(evtName, evtArgs)
    # special handling for LED Control via primary timer
    elif 'effect' in evtArgs and led_manager.isEnabled():
        led_manager.setEventEffect(Evt.LED_MANUAL, evtArgs['effect'])


@SOCKET_IO.on('cluster_message_ack')
@catchLogExceptionsWrapper
def on_cluster_message_ack(data):
    ''' Received message acknowledgement from primary. '''
    if ClusterSendAckQueueObj:
        messageType = str(data.get('messageType')) if data else None
        messagePayload = data.get('messagePayload') if data else None
        ClusterSendAckQueueObj.ack(messageType, messagePayload)
    else:
        logger.warning("Received 'on_cluster_message_ack' message with no ClusterSendAckQueueObj setup")

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
        elif load_type == 'result_data':
            emit_result_data(nobroadcast=True)
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
        elif load_type == 'backups_list':
            on_list_backups()
        elif load_type == 'exporter_list':
            emit_exporter_list()
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
    if CLUSTER:
        CLUSTER.emitToSplits('set_frequency', data)
    if isinstance(data, string_types): # LiveTime compatibility
        data = json.loads(data)
    node_index = data['node']
    frequency = int(data['frequency'])
    band = str(data['band']) if 'band' in data and data['band'] != None else None
    channel = int(data['channel']) if 'channel' in data and data['channel'] != None else None

    if node_index < 0 or node_index >= RACE.num_nodes:
        logger.info('Unable to set frequency ({0}) on node {1}; node index out of range'.format(frequency, node_index+1))
        return

    profile = getCurrentProfile()
    freqs = json.loads(profile.frequencies)

    # handle case where more nodes were added
    while node_index >= len(freqs["f"]):
        freqs["b"].append(None)
        freqs["c"].append(None)
        freqs["f"].append(RHUtils.FREQUENCY_ID_NONE)

    freqs["b"][node_index] = band
    freqs["c"][node_index] = channel
    freqs["f"][node_index] = frequency
    logger.info('Frequency set: Node {0} B:{1} Ch:{2} Freq:{3}'.format(node_index+1, band, channel, frequency))

    RHData.alter_profile({
        'profile_id': profile.id,
        'frequencies': freqs
        })

    INTERFACE.set_frequency(node_index, frequency)

    Events.trigger(Evt.FREQUENCY_SET, {
        'nodeIndex': node_index,
        'frequency': frequency,
        'band': band,
        'channel': channel
        })

    emit_frequency_data()

@SOCKET_IO.on('set_frequency_preset')
@catchLogExceptionsWrapper
def on_set_frequency_preset(data):
    ''' Apply preset frequencies '''
    if CLUSTER:
        CLUSTER.emitToSplits('set_frequency_preset', data)
    bands = []
    channels = []
    freqs = []
    if data['preset'] == 'All-N1':
        profile = getCurrentProfile()
        profile_freqs = json.loads(profile.frequencies)
        for _idx in range(RACE.num_nodes):
            bands.append(profile_freqs["b"][0])
            channels.append(profile_freqs["c"][0])
            freqs.append(profile_freqs["f"][0])
    else:
        if data['preset'] == 'RB-4':
            bands = ['R', 'R', 'R', 'R']
            channels = [1, 3, 6, 7]
            freqs = [5658, 5732, 5843, 5880]
        elif data['preset'] == 'RB-8':
            bands = ['R', 'R', 'R', 'R', 'R', 'R', 'R', 'R']
            channels = [1, 2, 3, 4, 5, 6, 7, 8]
            freqs = [5658, 5695, 5732, 5769, 5806, 5843, 5880, 5917]
        elif data['preset'] == 'IMD5C':
            bands = ['R', 'R', 'F', 'F', 'E']
            channels = [1, 2, 2, 4, 5]
            freqs = [5658, 5695, 5760, 5800, 5885]
        else: #IMD6C is default
            bands = ['R', 'R', 'F', 'F', 'R', 'R']
            channels = [1, 2, 2, 4, 7, 8]
            freqs = [5658, 5695, 5760, 5800, 5880, 5917]
        while RACE.num_nodes > len(bands):
            bands.append(RHUtils.FREQUENCY_ID_NONE)
        while RACE.num_nodes > len(channels):
            channels.append(RHUtils.FREQUENCY_ID_NONE)
        while RACE.num_nodes > len(freqs):
            freqs.append(RHUtils.FREQUENCY_ID_NONE)

    payload = {
        "b": bands,
        "c": channels,
        "f": freqs
    }
    set_all_frequencies(payload)
    emit_frequency_data()
    hardware_set_all_frequencies(payload)

def set_all_frequencies(freqs):
    ''' Set frequencies for all nodes (but do not update hardware) '''
    # Set DB
    profile = getCurrentProfile()
    profile_freqs = json.loads(profile.frequencies)

    for idx in range(RACE.num_nodes):
        profile_freqs["b"][idx] = freqs["b"][idx]
        profile_freqs["c"][idx] = freqs["c"][idx]
        profile_freqs["f"][idx] = freqs["f"][idx]
        logger.info('Frequency set: Node {0} B:{1} Ch:{2} Freq:{3}'.format(idx+1, freqs["b"][idx], freqs["c"][idx], freqs["f"][idx]))

    RHData.alter_profile({
        'profile_id': profile.id,
        'frequencies': profile_freqs
        })

def hardware_set_all_frequencies(freqs):
    '''do hardware update for frequencies'''
    logger.debug("Sending frequency values to nodes: " + str(freqs["f"]))
    for idx in range(RACE.num_nodes):
        INTERFACE.set_frequency(idx, freqs["f"][idx])

        Events.trigger(Evt.FREQUENCY_SET, {
            'nodeIndex': idx,
            'frequency': freqs["f"][idx],
            'band': freqs["b"][idx],
            'channel': freqs["c"][idx]
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

    if node_index < 0 or node_index >= RACE.num_nodes:
        logger.info('Unable to set enter-at ({0}) on node {1}; node index out of range'.format(enter_at_level, node_index+1))
        return

    if not enter_at_level:
        logger.info('Node enter-at set null; getting from node: Node {0}'.format(node_index+1))
        enter_at_level = INTERFACE.nodes[node_index].enter_at_level

    profile = getCurrentProfile()
    enter_ats = json.loads(profile.enter_ats)

    # handle case where more nodes were added
    while node_index >= len(enter_ats["v"]):
        enter_ats["v"].append(None)

    enter_ats["v"][node_index] = enter_at_level

    RHData.alter_profile({
        'profile_id': profile.id,
        'enter_ats': enter_ats
        })

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

    if node_index < 0 or node_index >= RACE.num_nodes:
        logger.info('Unable to set exit-at ({0}) on node {1}; node index out of range'.format(exit_at_level, node_index+1))
        return

    if not exit_at_level:
        logger.info('Node exit-at set null; getting from node: Node {0}'.format(node_index+1))
        exit_at_level = INTERFACE.nodes[node_index].exit_at_level

    profile = getCurrentProfile()
    exit_ats = json.loads(profile.exit_ats)

    # handle case where more nodes were added
    while node_index >= len(exit_ats["v"]):
        exit_ats["v"].append(None)

    exit_ats["v"][node_index] = exit_at_level

    RHData.alter_profile({
        'profile_id': profile.id,
        'exit_ats': exit_ats
        })

    INTERFACE.set_exit_at_level(node_index, exit_at_level)

    Events.trigger(Evt.EXIT_AT_LEVEL_SET, {
        'nodeIndex': node_index,
        'exit_at_level': exit_at_level,
        })

    logger.info('Node exit-at set: Node {0} Level {1}'.format(node_index+1, exit_at_level))

def hardware_set_all_enter_ats(enter_at_levels):
    '''send update to nodes'''
    logger.debug("Sending enter-at values to nodes: " + str(enter_at_levels))
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
    logger.debug("Sending exit-at values to nodes: " + str(exit_at_levels))
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
    RHData.set_option("startThreshLowerAmount", start_thresh_lower_amount)
    logger.info("set start_thresh_lower_amount to %s percent" % start_thresh_lower_amount)
    emit_start_thresh_lower_amount(noself=True)

@SOCKET_IO.on("set_start_thresh_lower_duration")
@catchLogExceptionsWrapper
def on_set_start_thresh_lower_duration(data):
    start_thresh_lower_duration = data['start_thresh_lower_duration']
    RHData.set_option("startThreshLowerDuration", start_thresh_lower_duration)
    logger.info("set start_thresh_lower_duration to %s seconds" % start_thresh_lower_duration)
    emit_start_thresh_lower_duration(noself=True)

@SOCKET_IO.on('set_language')
@catchLogExceptionsWrapper
def on_set_language(data):
    '''Set interface language.'''
    RHData.set_option('currentLanguage', data['language'])

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
    global HEARTBEAT_DATA_RATE_FACTOR
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
    RHData.add_heat()
    emit_heat_data()

@SOCKET_IO.on('duplicate_heat')
@catchLogExceptionsWrapper
def on_duplicate_heat(data):
    RHData.duplicate_heat(data['heat'])
    emit_heat_data()

@SOCKET_IO.on('alter_heat')
@catchLogExceptionsWrapper
def on_alter_heat(data):
    '''Update heat.'''
    heat, altered_race_list = RHData.alter_heat(data)
    if RACE.current_heat == heat.id:  # if current heat was altered then update heat data
        set_current_heat_data(heat.id)
    emit_heat_data(noself=True)
    if ('pilot' in data or 'class' in data) and len(altered_race_list):
        emit_result_data() # live update rounds page
        message = __('Alterations made to heat: {0}').format(heat.note)
        emit_priority_message(message, False)

@SOCKET_IO.on('delete_heat')
@catchLogExceptionsWrapper
def on_delete_heat(data):
    '''Delete heat.'''
    heat_id = data['heat']
    result = RHData.delete_heat(heat_id)
    if result is not None:
        if RACE.current_heat == result:  # if current heat was deleted then load new heat data
            heat_id = RHData.get_first_heat().id
            if RACE.current_heat != heat_id:
                logger.info('Changing current heat to Heat {0}'.format(heat_id))
                RACE.current_heat = heat_id
            set_current_heat_data(heat_id)
        emit_heat_data()

@SOCKET_IO.on('add_race_class')
@catchLogExceptionsWrapper
def on_add_race_class():
    '''Adds the next available pilot id number in the database.'''
    RHData.add_raceClass()
    emit_class_data()
    emit_heat_data() # Update class selections in heat displays

@SOCKET_IO.on('duplicate_race_class')
@catchLogExceptionsWrapper
def on_duplicate_race_class(data):
    '''Adds new race class by duplicating an existing one.'''
    RHData.duplicate_raceClass(data['class'])
    emit_class_data()
    emit_heat_data()

@SOCKET_IO.on('alter_race_class')
@catchLogExceptionsWrapper
def on_alter_race_class(data):
    '''Update race class.'''
    race_class, altered_race_list = RHData.alter_raceClass(data)

    if ('class_format' in data or 'class_name' in data) and len(altered_race_list):
        emit_result_data() # live update rounds page
        message = __('Alterations made to race class: {0}').format(race_class.name)
        emit_priority_message(message, False)

    emit_class_data(noself=True)
    if 'class_name' in data:
        emit_heat_data() # Update class names in heat displays
    if 'class_format' in data:
        emit_current_heat(noself=True) # in case race operator is a different client, update locked format dropdown

@SOCKET_IO.on('delete_class')
@catchLogExceptionsWrapper
def on_delete_class(data):
    '''Delete class.'''
    result = RHData.delete_raceClass(data['class'])
    if result:
        emit_class_data()
        emit_heat_data()

@SOCKET_IO.on('add_pilot')
@catchLogExceptionsWrapper
def on_add_pilot():
    '''Adds the next available pilot id number in the database.'''
    RHData.add_pilot()
    emit_pilot_data()

@SOCKET_IO.on('alter_pilot')
@catchLogExceptionsWrapper
def on_alter_pilot(data):
    '''Update pilot.'''
    _pilot, race_list = RHData.alter_pilot(data)

    emit_pilot_data(noself=True) # Settings page, new pilot settings

    if 'callsign' in data or 'team_name' in data:
        emit_heat_data() # Settings page, new pilot callsign in heats
        if len(race_list):
            emit_result_data() # live update rounds page
    if 'phonetic' in data:
        emit_heat_data() # Settings page, new pilot phonetic in heats. Needed?

    RACE.cacheStatus = Results.CacheStatus.INVALID  # refresh current leaderboard
    RACE.team_cacheStatus = Results.CacheStatus.INVALID

@SOCKET_IO.on('delete_pilot')
@catchLogExceptionsWrapper
def on_delete_pilot(data):
    '''Delete heat.'''
    result = RHData.delete_pilot(data['pilot'])

    if result:
        emit_pilot_data()
        emit_heat_data()

@SOCKET_IO.on('add_profile')
@catchLogExceptionsWrapper
def on_add_profile():
    '''Adds new profile (frequency set) in the database.'''
    source_profile = getCurrentProfile()
    new_profile = RHData.duplicate_profile(source_profile.id)

    on_set_profile({ 'profile': new_profile.id })

@SOCKET_IO.on('alter_profile')
@catchLogExceptionsWrapper
def on_alter_profile(data):
    ''' update profile '''
    profile = getCurrentProfile()
    data['profile_id'] = profile.id
    profile = RHData.alter_profile(data)

    emit_node_tuning(noself=True)

@SOCKET_IO.on('delete_profile')
@catchLogExceptionsWrapper
def on_delete_profile():
    '''Delete profile'''
    profile = getCurrentProfile()
    result = RHData.delete_profile(profile.id)

    if result:
        first_profile_id = RHData.get_first_profile().id
        RHData.set_option("currentProfile", first_profile_id)
        on_set_profile({ 'profile': first_profile_id })

@SOCKET_IO.on("set_profile")
@catchLogExceptionsWrapper
def on_set_profile(data, emit_vals=True):
    ''' set current profile '''
    profile_val = int(data['profile'])
    profile = RHData.get_profile(profile_val)
    if profile:
        RHData.set_option("currentProfile", data['profile'])
        logger.info("Set Profile to '%s'" % profile_val)
        # set freqs, enter_ats, and exit_ats
        freqs = json.loads(profile.frequencies)
        while RACE.num_nodes > len(freqs["b"]):
            freqs["b"].append(RHUtils.FREQUENCY_ID_NONE)
        while RACE.num_nodes > len(freqs["c"]):
            freqs["c"].append(RHUtils.FREQUENCY_ID_NONE)
        while RACE.num_nodes > len(freqs["f"]):
            freqs["f"].append(RHUtils.FREQUENCY_ID_NONE)

        if profile.enter_ats:
            enter_ats_loaded = json.loads(profile.enter_ats)
            enter_ats = enter_ats_loaded["v"]
            while RACE.num_nodes > len(enter_ats):
                enter_ats.append(None)
        else: #handle null data by copying in hardware values
            enter_at_levels = {}
            enter_at_levels["v"] = [node.enter_at_level for node in INTERFACE.nodes]
            RHData.alter_profile({'enter_ats': enter_at_levels})
            enter_ats = enter_at_levels["v"]

        if profile.exit_ats:
            exit_ats_loaded = json.loads(profile.exit_ats)
            exit_ats = exit_ats_loaded["v"]
            while RACE.num_nodes > len(exit_ats):
                exit_ats.append(None)
        else: #handle null data by copying in hardware values
            exit_at_levels = {}
            exit_at_levels["v"] = [node.exit_at_level for node in INTERFACE.nodes]
            RHData.alter_profile({'exit_ats': exit_at_levels})
            exit_ats = exit_at_levels["v"]

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
        logger.warning('Invalid set_profile value: ' + str(profile_val))

@SOCKET_IO.on('alter_race')
@catchLogExceptionsWrapper
def on_alter_race(data):
    '''Update race (retroactively via marshaling).'''

    _race_meta, new_heat = RHData.reassign_savedRaceMeta_heat(data['race_id'], data['heat_id'])

    heatnote = new_heat.note
    if heatnote:
        name = heatnote
    else:
        name = new_heat.id

    message = __('A race has been reassigned to {0}').format(name)
    emit_priority_message(message, False)

    emit_race_list(nobroadcast=True)
    emit_result_data()

@SOCKET_IO.on('backup_database')
@catchLogExceptionsWrapper
def on_backup_database():
    '''Backup database.'''
    bkp_name = RHData.backup_db_file(True)  # make copy of DB file

    # read DB data and convert to Base64
    with open(bkp_name, mode='rb') as file_obj:
        file_content = file_obj.read()
    if hasattr(base64, "encodebytes"):
        file_content = base64.encodebytes(file_content).decode()
    else:
        file_content = base64.encodestring(file_content)  #pylint: disable=deprecated-method

    emit_payload = {
        'file_name': os.path.basename(bkp_name),
        'file_data' : file_content
    }

    Events.trigger(Evt.DATABASE_BACKUP, {
        'file_name': emit_payload['file_name'],
        })

    emit('database_bkp_done', emit_payload)
    on_list_backups()

@SOCKET_IO.on('list_backups')
@catchLogExceptionsWrapper
def on_list_backups():
    '''List database files in db_bkp'''

    if not os.path.exists(DB_BKP_DIR_NAME):
        emit_payload = {
            'backup_files': None
        }
    else:
        files = []
        for (_, _, filenames) in os.walk(DB_BKP_DIR_NAME):
            files.extend(filenames)
            break

        emit_payload = {
            'backup_files': files
        }

    emit('backups_list', emit_payload)

@SOCKET_IO.on('restore_database')
@catchLogExceptionsWrapper
def on_restore_database(data):
    '''Restore database.'''
    global RACE
    global LAST_RACE
    success = None
    if 'backup_file' in data:
        backup_file = data['backup_file']
        backup_path = DB_BKP_DIR_NAME + '/' + backup_file

        if os.path.exists(backup_path):
            logger.info('Found {0}: starting restoration...'.format(backup_file))
            RHData.close()

            RACE = RHRace.RHRace() # Reset all RACE values
            LAST_RACE = RACE
            try:
                RHData.recover_database(DB_BKP_DIR_NAME + '/' + backup_file)
                clean_results_cache()
                expand_heats()
                raceformat_id = RHData.get_optionInt('currentFormat')
                race_format = RHData.get_raceFormat(raceformat_id)
                setCurrentRaceFormat(race_format)

                success = True
            except Exception as ex:
                logger.warning('Clearing all data after recovery failure:  ' + str(ex))
                db_reset()
                success = False

            init_race_state()
            init_interface_state()

            Events.trigger(Evt.DATABASE_RESTORE, {
                'file_name': backup_file,
                })

            SOCKET_IO.emit('database_restore_done')
        else:
            logger.warning('Unable to restore {0}: File does not exist'.format(backup_file))
            success = False

    if success == False:
        message = __('Database recovery failed for: {0}').format(backup_file)
        emit_priority_message(message, False, nobroadcast=True)

@SOCKET_IO.on('delete_database')
@catchLogExceptionsWrapper
def on_delete_database_file(data):
    '''Restore database.'''
    if 'backup_file' in data:
        backup_file = data['backup_file']
        backup_path = DB_BKP_DIR_NAME + '/' + backup_file

        if os.path.exists(backup_path):
            logger.info('Deleting backup file {0}'.format(backup_file))
            os.remove(backup_path)

            emit_payload = {
                'file_name': backup_file
            }

            Events.trigger(Evt.DATABASE_DELETE_BACKUP, {
                'file_name': backup_file,
                })

            SOCKET_IO.emit('database_delete_done', emit_payload)
            on_list_backups()
        else:
            logger.warning('Unable to delete {0}: File does not exist'.format(backup_file))

@SOCKET_IO.on('reset_database')
@catchLogExceptionsWrapper
def on_reset_database(data):
    '''Reset database.'''
    PageCache.set_valid(False)

    reset_type = data['reset_type']
    if reset_type == 'races':
        RHData.clear_race_data()
        reset_current_laps()
    elif reset_type == 'heats':
        RHData.reset_heats()
        RHData.clear_race_data()
        reset_current_laps()
    elif reset_type == 'classes':
        RHData.reset_heats()
        RHData.reset_raceClasses()
        RHData.clear_race_data()
        reset_current_laps()
    elif reset_type == 'pilots':
        RHData.reset_pilots()
        RHData.reset_heats()
        RHData.clear_race_data()
        reset_current_laps()
    elif reset_type == 'all':
        RHData.reset_pilots()
        RHData.reset_heats()
        RHData.reset_raceClasses()
        RHData.clear_race_data()
        reset_current_laps()
    elif reset_type == 'formats':
        RHData.clear_race_data()
        reset_current_laps()
        RHData.reset_raceFormats()
        setCurrentRaceFormat(RHData.get_first_raceFormat())
    emit_heat_data()
    emit_pilot_data()
    emit_race_format()
    emit_class_data()
    emit_current_laps()
    emit_result_data()
    emit('reset_confirm')

    Events.trigger(Evt.DATABASE_RESET)

@SOCKET_IO.on('export_database')
@catchLogExceptionsWrapper
def on_export_database_file(data):
    '''Run the selected Exporter'''
    exporter = data['exporter']

    if export_manager.hasExporter(exporter):
        # do export
        logger.info('Exporting data via {0}'.format(exporter))
        export_result = export_manager.export(exporter)

        if export_result != False:
            try:
                emit_payload = {
                    'filename': 'RotorHazard Export ' + datetime.now().strftime('%Y%m%d_%H%M%S') + ' ' + exporter + '.' + export_result['ext'],
                    'encoding': export_result['encoding'],
                    'data' : export_result['data']
                }
                emit('exported_data', emit_payload)

                Events.trigger(Evt.DATABASE_EXPORT)
            except Exception:
                logger.exception("Error downloading export file")
                emit_priority_message(__('Data export failed. (See log)'), False, nobroadcast=True)
        else:
            logger.warning('Failed exporting data: exporter returned no data')
            emit_priority_message(__('Data export failed. (See log)'), False, nobroadcast=True)

        return

    logger.error('Data exporter "{0}" not found'.format(exporter))
    emit_priority_message(__('Data export failed. (See log)'), False, nobroadcast=True)

@SOCKET_IO.on('shutdown_pi')
@catchLogExceptionsWrapper
def on_shutdown_pi():
    '''Shutdown the raspberry pi.'''
    if  INTERFACE.send_shutdown_started_message():
        gevent.sleep(0.25)  # give shutdown-started message a chance to transmit to node
    if CLUSTER:
        CLUSTER.emit('shutdown_pi')
    emit_priority_message(__('Server has shut down.'), True, caller='shutdown')
    logger.info('Performing system shutdown')
    Events.trigger(Evt.SHUTDOWN)
    stop_background_threads()
    gevent.sleep(0.5)
    gevent.spawn(SOCKET_IO.stop)  # shut down flask http server
    if RHUtils.isSysRaspberryPi():
        gevent.sleep(0.1)
        logger.debug("Executing system command:  sudo shutdown now")
        log.wait_for_queue_empty()
        log.close_logging()
        os.system("sudo shutdown now")
    else:
        logger.warning("Not executing system shutdown command because not RPi")

@SOCKET_IO.on('reboot_pi')
@catchLogExceptionsWrapper
def on_reboot_pi():
    '''Reboot the raspberry pi.'''
    if CLUSTER:
        CLUSTER.emit('reboot_pi')
    emit_priority_message(__('Server is rebooting.'), True, caller='shutdown')
    logger.info('Performing system reboot')
    Events.trigger(Evt.SHUTDOWN)
    stop_background_threads()
    gevent.sleep(0.5)
    gevent.spawn(SOCKET_IO.stop)  # shut down flask http server
    if RHUtils.isSysRaspberryPi():
        gevent.sleep(0.1)
        logger.debug("Executing system command:  sudo reboot now")
        log.wait_for_queue_empty()
        log.close_logging()
        os.system("sudo reboot now")
    else:
        logger.warning("Not executing system reboot command because not RPi")

@SOCKET_IO.on('kill_server')
@catchLogExceptionsWrapper
def on_kill_server():
    '''Shutdown this server.'''
    if CLUSTER:
        CLUSTER.emit('kill_server')
    emit_priority_message(__('Server has stopped.'), True, caller='shutdown')
    logger.info('Killing RotorHazard server')
    Events.trigger(Evt.SHUTDOWN)
    stop_background_threads()
    gevent.sleep(0.5)
    gevent.spawn(SOCKET_IO.stop)  # shut down flask http server

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
                file_content = file_obj.read()
            if hasattr(base64, "encodebytes"):
                file_content = base64.encodebytes(file_content).decode()
            else:
                file_content = base64.encodestring(file_content)  #pylint: disable=deprecated-method

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
    RHData.set_option("MinLapSec", data['min_lap'])

    Events.trigger(Evt.MIN_LAP_TIME_SET, {
        'min_lap': min_lap,
        })

    logger.info("set min lap time to %s seconds" % min_lap)
    emit_min_lap(noself=True)

@SOCKET_IO.on("set_min_lap_behavior")
@catchLogExceptionsWrapper
def on_set_min_lap_behavior(data):
    min_lap_behavior = int(data['min_lap_behavior'])
    RHData.set_option("MinLapBehavior", min_lap_behavior)

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
        race_format = RHData.get_raceFormat(race_format_val)
        setCurrentRaceFormat(race_format)

        Events.trigger(Evt.RACE_FORMAT_SET, {
            'race_format': race_format_val,
            })

        emit_race_format()
        logger.info("set race format to '%s' (%s)" % (race_format.name, race_format.id))
    else:
        emit_priority_message(__('Format change prevented by active race: Stop and save/discard laps'), False, nobroadcast=True)
        logger.info("Format change prevented by active race")
        emit_race_format()

@SOCKET_IO.on('add_race_format')
@catchLogExceptionsWrapper
def on_add_race_format():
    '''Adds new format in the database by duplicating an existing one.'''
    source_format = getCurrentRaceFormat()
    new_format = RHData.duplicate_raceFormat(source_format.id)

    on_set_race_format(data={ 'race_format': new_format.id })

@SOCKET_IO.on('alter_race_format')
@catchLogExceptionsWrapper
def on_alter_race_format(data):
    ''' update race format '''
    race_format = getCurrentDbRaceFormat()
    data['format_id'] = race_format.id
    race_format, race_list = RHData.alter_raceFormat(data)

    if race_format != False:
        setCurrentRaceFormat(race_format)

        if 'format_name' in data:
            emit_race_format()
            emit_class_data()

        if len(race_list):
            emit_result_data()
            message = __('Alterations made to race format: {0}').format(race_format.name)
            emit_priority_message(message, False)
    else:
        emit_priority_message(__('Format alteration prevented by active race: Stop and save/discard laps'), False, nobroadcast=True)

@SOCKET_IO.on('delete_race_format')
@catchLogExceptionsWrapper
def on_delete_race_format():
    '''Delete profile'''
    raceformat = getCurrentDbRaceFormat()
    result = RHData.delete_raceFormat(raceformat.id)

    if result:
        first_raceFormat = RHData.get_first_raceFormat()
        setCurrentRaceFormat(first_raceFormat)
        emit_race_format()
    else:
        if RACE.race_status == RaceStatus.READY:
            emit_priority_message(__('Format deletion prevented: saved race exists with this format'), False, nobroadcast=True)
        else:
            emit_priority_message(__('Format deletion prevented by active race: Stop and save/discard laps'), False, nobroadcast=True)

@SOCKET_IO.on("set_next_heat_behavior")
@catchLogExceptionsWrapper
def on_set_next_heat_behavior(data):
    next_heat_behavior = int(data['next_heat_behavior'])
    RHData.set_option("nextHeatBehavior", next_heat_behavior)
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

            effect_list_recommended = []
            effect_list_normal = []

            for effect in effects:

                if event['event'] in effects[effect]['validEvents'].get('include', []) or (
                    event['event'] not in [Evt.SHUTDOWN, LEDEvent.IDLE_DONE, LEDEvent.IDLE_RACING, LEDEvent.IDLE_READY]
                    and event['event'] not in effects[effect]['validEvents'].get('exclude', [])
                    and Evt.ALL not in effects[effect]['validEvents'].get('exclude', [])):

                    if event['event'] in effects[effect]['validEvents'].get('recommended', []) or \
                        Evt.ALL in effects[effect]['validEvents'].get('recommended', []):
                        effect_list_recommended.append({
                            'name': effect,
                            'label': '* ' + __(effects[effect]['label'])
                        })
                    else:
                        effect_list_normal.append({
                            'name': effect,
                            'label': __(effects[effect]['label'])
                        })

            effect_list_recommended.sort(key=lambda x: x['label'])
            effect_list_normal.sort(key=lambda x: x['label'])

            emit_payload['events'].append({
                'event': event["event"],
                'label': __(event["label"]),
                'selected': selectedEffect,
                'effects': effect_list_recommended + effect_list_normal
            })

        # never broadcast
        emit('led_effect_setup_data', emit_payload)

def emit_led_effects(**params):
    if led_manager.isEnabled() or (CLUSTER and CLUSTER.hasRecEventsSecondaries()):
        effects = led_manager.getRegisteredEffects()

        effect_list = []
        if effects:
            for effect in effects:
                if effects[effect]['validEvents'].get('manual', True):
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
    if 'event' in data and 'effect' in data:
        if led_manager.isEnabled():
            led_manager.setEventEffect(data['event'], data['effect'])

        effect_opt = RHData.get_option('ledEffects')
        if effect_opt:
            effects = json.loads(effect_opt)
        else:
            effects = {}

        effects[data['event']] = data['effect']
        RHData.set_option('ledEffects', json.dumps(effects))

        Events.trigger(Evt.LED_EFFECT_SET, {
            'effect': data['event'],
            })

        logger.info('Set LED event {0} to effect {1}'.format(data['event'], data['effect']))

@SOCKET_IO.on('use_led_effect')
@catchLogExceptionsWrapper
def on_use_led_effect(data):
    '''Activate arbitrary LED Effect.'''
    if 'effect' in data:
        if led_manager.isEnabled():
            led_manager.setEventEffect(Evt.LED_MANUAL, data['effect'])
        Events.trigger(Evt.LED_SET_MANUAL, data)  # setup manual effect on mirror timers

        args = {}
        if 'args' in data:
            args = data['args']
        if 'color' in data:
            args['color'] = hexToColor(data['color'])

        Events.trigger(Evt.LED_MANUAL, args)

# Race management socket io events

@SOCKET_IO.on('schedule_race')
@catchLogExceptionsWrapper
def on_schedule_race(data):
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
    global LAST_RACE
    valid_pilots = False
    heat_data = RHData.get_heat(RACE.current_heat)
    heatNodes = RHData.get_heatNodes_by_heat(RACE.current_heat)
    for heatNode in heatNodes:
        if heatNode.node_index < RACE.num_nodes:
            if heatNode.pilot_id != RHUtils.PILOT_ID_NONE:
                valid_pilots = True
                break

    if request and valid_pilots is False:
        emit_priority_message(__('No valid pilots in race'), True, nobroadcast=True)

    if CLUSTER:
        CLUSTER.emitToSplits('stage_race')
    race_format = getCurrentRaceFormat()

    if RACE.race_status != RaceStatus.READY:
        if race_format is SECONDARY_RACE_FORMAT:  # if running as secondary timer
            if RACE.race_status == RaceStatus.RACING:
                return  # if race in progress then leave it be
            # if missed stop/discard message then clear current race
            logger.info("Forcing race clear/restart because running as secondary timer")
            on_discard_laps()
        elif RACE.race_status == RaceStatus.DONE and not RACE.any_laps_recorded():
            on_discard_laps()  # if no laps then allow restart

    if RACE.race_status == RaceStatus.READY: # only initiate staging if ready
        # common race start events (do early to prevent processing delay when start is called)
        INTERFACE.enable_calibration_mode() # Nodes reset triggers on next pass

        if heat_data.class_id != RHUtils.CLASS_ID_NONE:
            class_format_id = RHData.get_raceClass(heat_data.class_id).format_id
            if class_format_id != RHUtils.FORMAT_ID_NONE:
                class_format = RHData.get_raceFormat(class_format_id)
                setCurrentRaceFormat(class_format)
                logger.info("Forcing race format from class setting: '{0}' ({1})".format(class_format.name, class_format_id))

        clear_laps() # Clear laps before race start
        init_node_cross_fields()  # set 'cur_pilot_id' and 'cross' fields on nodes
        LAST_RACE = None # clear all previous race data
        RACE.timer_running = False # indicate race timer not running
        RACE.race_status = RaceStatus.STAGING
        RACE.win_status = WinStatus.NONE
        RACE.status_message = ''
        RACE.any_races_started = True

        RACE.node_has_finished = {}
        for heatNode in heatNodes:
            if heatNode.node_index < RACE.num_nodes:
                if heatNode.pilot_id != RHUtils.PILOT_ID_NONE:
                    RACE.node_has_finished[heatNode.node_index] = False
                else:
                    RACE.node_has_finished[heatNode.node_index] = None

        INTERFACE.set_race_status(RaceStatus.STAGING)
        emit_current_laps() # Race page, blank laps to the web client
        emit_current_leaderboard() # Race page, blank leaderboard to the web client
        emit_race_status()
        emit_race_format()

        MIN = min(race_format.start_delay_min, race_format.start_delay_max) # in case values are reversed
        MAX = max(race_format.start_delay_min, race_format.start_delay_max)
        RACE.start_time_delay_secs = random.randint(MIN, MAX) + RHRace.RACE_START_DELAY_EXTRA_SECS

        RACE.start_time_monotonic = monotonic() + RACE.start_time_delay_secs
        RACE.start_time_epoch_ms = monotonic_to_epoch_millis(RACE.start_time_monotonic)
        RACE.start_token = random.random()
        gevent.spawn(race_start_thread, RACE.start_token)

        eventPayload = {
            'hide_stage_timer': MIN != MAX,
            'pi_starts_at_s': RACE.start_time_monotonic,
            'color': ColorVal.ORANGE,
        }

        if led_manager.isEnabled():
            eventPayload['race_node_colors'] = led_manager.getNodeColors(RACE.num_nodes)
        else:
            eventPayload['race_node_colors'] = None

        Events.trigger(Evt.RACE_STAGE, eventPayload)

        SOCKET_IO.emit('stage_ready', {
            'hide_stage_timer': MIN != MAX,
            'delay': RACE.start_time_delay_secs,
            'race_mode': race_format.race_mode,
            'race_time_sec': race_format.race_time_sec,
            'pi_starts_at_s': RACE.start_time_monotonic
        }) # Announce staging with chosen delay

    else:
        logger.info("Attempted to stage race while status is not 'ready'")

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
    heat = RHData.get_heat(RACE.current_heat)
    pilot = RHData.get_pilot_from_heatNode(RACE.current_heat, node_index)
    current_class = heat.class_id
    races = RHData.get_savedRaceMetas()
    races.sort(key=lambda x: x.id, reverse=True)
    pilotRaces = RHData.get_savedPilotRaces()
    pilotRaces.sort(key=lambda x: x.id, reverse=True)

    # test for disabled node
    if pilot is RHUtils.PILOT_ID_NONE or node.frequency is RHUtils.FREQUENCY_ID_NONE:
        logger.debug('Node {0} calibration: skipping disabled node'.format(node.index+1))
        return {
            'enter_at_level': node.enter_at_level,
            'exit_at_level': node.exit_at_level
        }

    # test for same heat, same node
    for race in races:
        if race.heat_id == heat.id:
            for pilotRace in pilotRaces:
                if pilotRace.race_id == race.id and \
                    pilotRace.node_index == node_index:
                    logger.debug('Node {0} calibration: found same pilot+node in same heat'.format(node.index+1))
                    return {
                        'enter_at_level': pilotRace.enter_at,
                        'exit_at_level': pilotRace.exit_at
                    }
            break

    # test for same class, same pilot, same node
    for race in races:
        if race.class_id == current_class:
            for pilotRace in pilotRaces:
                if pilotRace.race_id == race.id and \
                    pilotRace.node_index == node_index and \
                    pilotRace.pilot_id == pilot:
                    logger.debug('Node {0} calibration: found same pilot+node in other heat with same class'.format(node.index+1))
                    return {
                        'enter_at_level': pilotRace.enter_at,
                        'exit_at_level': pilotRace.exit_at
                    }
            break

    # test for same pilot, same node
    for pilotRace in pilotRaces:
        if pilotRace.node_index == node_index and \
            pilotRace.pilot_id == pilot:
            logger.debug('Node {0} calibration: found same pilot+node in other heat with other class'.format(node.index+1))
            return {
                'enter_at_level': pilotRace.enter_at,
                'exit_at_level': pilotRace.exit_at
            }

    # test for same node
    for pilotRace in pilotRaces:
        if pilotRace.node_index == node_index:
            logger.debug('Node {0} calibration: found same node in other heat'.format(node.index+1))
            return {
                'enter_at_level': pilotRace.enter_at,
                'exit_at_level': pilotRace.exit_at
            }

    # fallback
    logger.debug('Node {0} calibration: no calibration hints found, no change'.format(node.index+1))
    return {
        'enter_at_level': node.enter_at_level,
        'exit_at_level': node.exit_at_level
    }

@catchLogExceptionsWrapper
def race_start_thread(start_token):

    # clear any lingering crossings at staging (if node rssi < enterAt)
    for node in INTERFACE.nodes:
        if node.crossing_flag and node.frequency > 0 and \
            (getCurrentRaceFormat() is SECONDARY_RACE_FORMAT or
            (node.current_pilot_id != RHUtils.PILOT_ID_NONE and node.current_rssi < node.enter_at_level)):
            logger.info("Forcing end crossing for node {0} at staging (rssi={1}, enterAt={2}, exitAt={3})".\
                       format(node.index+1, node.current_rssi, node.enter_at_level, node.exit_at_level))
            INTERFACE.force_end_crossing(node.index)

    if CLUSTER and CLUSTER.hasSecondaries():
        CLUSTER.doClusterRaceStart()

    # set lower EnterAt/ExitAt values if configured
    if RHData.get_optionInt('startThreshLowerAmount') > 0 and RHData.get_optionInt('startThreshLowerDuration') > 0:
        lower_amount = RHData.get_optionInt('startThreshLowerAmount')
        logger.info("Lowering EnterAt/ExitAt values at start of race, amount={0}%, duration={1} secs".\
                    format(lower_amount, RHData.get_optionInt('startThreshLowerDuration')))
        lower_end_time = RACE.start_time_monotonic + RHData.get_optionInt('startThreshLowerDuration')
        for node in INTERFACE.nodes:
            if node.frequency > 0 and (getCurrentRaceFormat() is SECONDARY_RACE_FORMAT or node.current_pilot_id != RHUtils.PILOT_ID_NONE):
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

        # !!! RACE STARTS NOW !!!

        # do time-critical tasks
        Events.trigger(Evt.RACE_START, {
            'race': RACE,
            'color': ColorVal.GREEN
            })

        # do secondary start tasks (small delay is acceptable)
        RACE.start_time = datetime.now() # record standard-formatted time

        for node in INTERFACE.nodes:
            node.history_values = [] # clear race history
            node.history_times = []
            node.under_min_lap_count = 0
            # clear any lingering crossing (if rssi>enterAt then first crossing starts now)
            if node.crossing_flag and node.frequency > 0 and (
                getCurrentRaceFormat() is SECONDARY_RACE_FORMAT or node.current_pilot_id != RHUtils.PILOT_ID_NONE):
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
        logger.info('Race started at {:.3f} ({:.0f})'.format(RACE.start_time_monotonic, RACE.start_time_epoch_ms))

@catchLogExceptionsWrapper
def race_expire_thread(start_token):
    race_format = getCurrentRaceFormat()
    if race_format and race_format.race_mode == 0: # count down
        gevent.sleep(race_format.race_time_sec)
        # if race still in progress and is still same race
        if RACE.race_status == RaceStatus.RACING and RACE.start_token == start_token:
            logger.info("Race count-down timer reached expiration")
            RACE.timer_running = False # indicate race timer no longer running
            Events.trigger(Evt.RACE_FINISH)
            check_win_condition(at_finish=True, start_token=start_token)
            emit_current_leaderboard()
        else:
            logger.debug("Finished unused race-time-expire thread")

@SOCKET_IO.on('stop_race')
@catchLogExceptionsWrapper
def on_stop_race():
    '''Stops the race and stops registering laps.'''
    if CLUSTER:
        CLUSTER.emitToSplits('stop_race')
    # clear any crossings still in progress
    any_forced_flag = False
    for node in INTERFACE.nodes:
        if node.crossing_flag and node.frequency > 0 and \
                        node.current_pilot_id != RHUtils.PILOT_ID_NONE:
            logger.info("Forcing end crossing for node {} at race stop (rssi={}, enterAt={}, exitAt={})".\
                        format(node.index+1, node.current_rssi, node.enter_at_level, node.exit_at_level))
            INTERFACE.force_end_crossing(node.index)
            any_forced_flag = True
    if any_forced_flag:  # give forced end-crossings a chance to complete before stopping race
        gevent.spawn_later(0.5, do_stop_race_actions)
    else:
        do_stop_race_actions()

@catchLogExceptionsWrapper
def do_stop_race_actions():
    if RACE.race_status == RaceStatus.RACING:
        RACE.end_time = monotonic() # Update the race end time stamp
        delta_time = RACE.end_time - RACE.start_time_monotonic
        milli_sec = delta_time * 1000.0
        RACE.duration_ms = milli_sec

        logger.info('Race stopped at {:.3f} ({:.0f}), duration {:.3f}ms'.format(RACE.end_time, monotonic_to_epoch_millis(RACE.end_time), RACE.duration_ms))

        min_laps_list = []  # show nodes with laps under minimum (if any)
        for node in INTERFACE.nodes:
            if node.under_min_lap_count > 0:
                min_laps_list.append('Node {0} Count={1}'.format(node.index+1, node.under_min_lap_count))
        if len(min_laps_list) > 0:
            logger.info('Nodes with laps under minimum:  ' + ', '.join(min_laps_list))

        RACE.race_status = RaceStatus.DONE # To stop registering passed laps, waiting for laps to be cleared
        INTERFACE.set_race_status(RaceStatus.DONE)
        Events.trigger(Evt.RACE_STOP, {
            'color': ColorVal.RED
        })
        check_win_condition()

        if CLUSTER and CLUSTER.hasSecondaries():
            CLUSTER.doClusterRaceStop()

    else:
        logger.debug('No active race to stop')
        RACE.race_status = RaceStatus.READY # Go back to ready state
        INTERFACE.set_race_status(RaceStatus.READY)
        Events.trigger(Evt.LAPS_CLEAR)
        delta_time = 0

    # check if nodes may be set to temporary lower EnterAt/ExitAt values (and still have them)
    if RHData.get_optionInt('startThreshLowerAmount') > 0 and \
            delta_time < RHData.get_optionInt('startThreshLowerDuration'):
        for node in INTERFACE.nodes:
            # if node EnterAt/ExitAt values need to be restored then do it soon
            if node.frequency > 0 and (
                getCurrentRaceFormat() is SECONDARY_RACE_FORMAT or (
                    node.current_pilot_id != RHUtils.PILOT_ID_NONE and \
                    node.start_thresh_lower_flag)):
                node.start_thresh_lower_time = RACE.end_time + 0.1

    RACE.timer_running = False # indicate race timer not running
    RACE.scheduled = False # also stop any deferred start

    SOCKET_IO.emit('stop_timer') # Loop back to race page to start the timer counting up
    emit_race_status() # Race page, to set race button states
    emit_current_leaderboard()

@SOCKET_IO.on('save_laps')
@catchLogExceptionsWrapper
def on_save_laps():
    '''Save current laps data to the database.'''

    # Determine if race is empty
    # race_has_laps = False
    # for node_index in RACE.node_laps:
    #    if RACE.node_laps[node_index]:
    #        race_has_laps = True
    #        break

    # if race_has_laps == True:
    if CLUSTER:
        CLUSTER.emitToSplits('save_laps')
    PageCache.set_valid(False)
    heat = RHData.get_heat(RACE.current_heat)
    # Get the last saved round for the current heat
    max_round = RHData.get_max_round(RACE.current_heat)

    if max_round is None:
        max_round = 0
    # Loop through laps to copy to saved races
    profile = getCurrentProfile()
    profile_freqs = json.loads(profile.frequencies)

    new_race_data = {
        'round_id': max_round+1,
        'heat_id': RACE.current_heat,
        'class_id': heat.class_id,
        'format_id': RHData.get_option('currentFormat'),
        'start_time': RACE.start_time_monotonic,
        'start_time_formatted': RACE.start_time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    new_race = RHData.add_savedRaceMeta(new_race_data)

    race_data = {}

    for node_index in range(RACE.num_nodes):
        if profile_freqs["f"][node_index] != RHUtils.FREQUENCY_ID_NONE:
            pilot_id = RHData.get_pilot_from_heatNode(RACE.current_heat, node_index)

            race_data[node_index] = {
                'race_id': new_race.id,
                'pilot_id': pilot_id,
                'history_values': json.dumps(INTERFACE.nodes[node_index].history_values),
                'history_times': json.dumps(INTERFACE.nodes[node_index].history_times),
                'enter_at': INTERFACE.nodes[node_index].enter_at_level,
                'exit_at': INTERFACE.nodes[node_index].exit_at_level,
                'laps': RACE.node_laps[node_index]
                }

    RHData.add_race_data(race_data)

    # spawn thread for updating results caches
    cache_params = {
        'race_id': new_race.id,
        'heat_id': RACE.current_heat,
        'round_id': new_race.round_id,
    }
    gevent.spawn(build_atomic_result_caches, cache_params)

    Events.trigger(Evt.LAPS_SAVE, {
        'race_id': new_race.id,
        })

    logger.info('Current laps saved: Heat {0} Round {1}'.format(RACE.current_heat, max_round+1))
    on_discard_laps(saved=True) # Also clear the current laps
    # else:
    #    on_discard_laps()
    #    message = __('Discarding empty race')
    #    emit_priority_message(message, False, nobroadcast=True)

@SOCKET_IO.on('resave_laps')
@catchLogExceptionsWrapper
def on_resave_laps(data):
    PageCache.set_valid(False)

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

    pilotrace_data = {
        'pilotrace_id': pilotrace_id,
        'enter_at': enter_at,
        'exit_at': exit_at
        }

    RHData.alter_savedPilotRace(pilotrace_data)

    new_racedata = {
            'race_id': race_id,
            'pilotrace_id': pilotrace_id,
            'node_index': node,
            'pilot_id': pilot_id,
            'laps': []
        }

    for lap in laps:
        tmp_lap_time_formatted = lap['lap_time']
        if isinstance(lap['lap_time'], float):
            tmp_lap_time_formatted = RHUtils.time_format(lap['lap_time'], RHData.get_option('timeFormat'))

        new_racedata['laps'].append({
            'lap_time_stamp': lap['lap_time_stamp'],
            'lap_time': lap['lap_time'],
            'lap_time_formatted': tmp_lap_time_formatted,
            'source': lap['source'],
            'deleted': lap['deleted']
            })

    RHData.replace_savedRaceLaps(new_racedata)

    message = __('Race times adjusted for: Heat {0} Round {1} / {2}').format(heat_id, round_id, callsign)
    emit_priority_message(message, False)
    logger.info(message)

    # run adaptive calibration
    if RHData.get_optionInt('calibrationMode'):
        autoUpdateCalibration()

    # spawn thread for updating results caches
    params = {
        'race_id': race_id,
        'heat_id': heat_id,
        'round_id': round_id,
    }
    gevent.spawn(build_atomic_result_caches, params)

    Events.trigger(Evt.LAPS_RESAVE, {
        'race_id': race_id,
        'pilot_id': pilot_id,
        })

@catchLogExceptionsWrapper
def build_atomic_result_caches(params):
    PageCache.set_valid(False)
    Results.build_atomic_results_caches(RHData, params)
    emit_result_data()

@SOCKET_IO.on('discard_laps')
@catchLogExceptionsWrapper
def on_discard_laps(**kwargs):
    '''Clear the current laps without saving.'''
    clear_laps()
    RACE.race_status = RaceStatus.READY # Flag status as ready to start next race
    INTERFACE.set_race_status(RaceStatus.READY)
    RACE.win_status = WinStatus.NONE
    RACE.status_message = ''
    emit_current_laps() # Race page, blank laps to the web client
    emit_current_leaderboard() # Race page, blank leaderboard to the web client
    emit_race_status() # Race page, to set race button states

    if 'saved' in kwargs and kwargs['saved'] == True:
        # discarding follows a save action
        pass
    else:
        # discarding does not follow a save action
        Events.trigger(Evt.LAPS_DISCARD)
        if CLUSTER:
            CLUSTER.emitToSplits('discard_laps')

    Events.trigger(Evt.LAPS_CLEAR)

def clear_laps():
    '''Clear the current laps table.'''
    global LAST_RACE
    LAST_RACE = copy.deepcopy(RACE)
    RACE.laps_winner_name = None  # clear winner in first-to-X-laps race
    RACE.winning_lap_id = 0
    reset_current_laps() # Clear out the current laps table
    RHData.clear_lapSplits()
    logger.info('Current laps cleared')

def init_node_cross_fields():
    '''Sets the 'current_pilot_id' and 'cross' values on each node.'''
    heatnodes = RHData.get_heatNodes_by_heat(RACE.current_heat)

    for node in INTERFACE.nodes:
        node.current_pilot_id = RHUtils.PILOT_ID_NONE
        if node.frequency and node.frequency > 0:
            for heatnode in heatnodes:
                if heatnode.node_index == node.index:
                    node.current_pilot_id = heatnode.pilot_id
                    break

        node.first_cross_flag = False
        node.show_crossing_flag = False
    
def set_current_heat_data(new_heat_id):
    RACE.node_pilots = {}
    RACE.node_teams = {}
    for idx in range(RACE.num_nodes):
        RACE.node_pilots[idx] = RHUtils.PILOT_ID_NONE
        RACE.node_teams[idx] = None

    for heatNode in RHData.get_heatNodes_by_heat(new_heat_id):
        RACE.node_pilots[heatNode.node_index] = heatNode.pilot_id

        if heatNode.pilot_id is not RHUtils.PILOT_ID_NONE:
            RACE.node_teams[heatNode.node_index] = RHData.get_pilot(heatNode.pilot_id).team
        else:
            RACE.node_teams[heatNode.node_index] = None

    heat_data = RHData.get_heat(new_heat_id)

    if heat_data.class_id != RHUtils.CLASS_ID_NONE:
        class_format_id = RHData.get_raceClass(heat_data.class_id).format_id
        if class_format_id != RHUtils.FORMAT_ID_NONE:
            class_format = RHData.get_raceFormat(class_format_id)
            setCurrentRaceFormat(class_format)
            logger.info("Forcing race format from class setting: '{0}' ({1})".format(class_format.name, class_format_id))

    if RHData.get_optionInt('calibrationMode'):
        autoUpdateCalibration()

    Events.trigger(Evt.HEAT_SET, {
        'heat_id': new_heat_id,
        })

    RACE.cacheStatus = Results.CacheStatus.INVALID  # refresh leaderboard
    RACE.team_cacheStatus = Results.CacheStatus.INVALID
    emit_current_heat() # Race page, to update heat selection button
    emit_current_leaderboard() # Race page, to update callsigns in leaderboard
    emit_race_format()

@SOCKET_IO.on('set_current_heat')
@catchLogExceptionsWrapper
def on_set_current_heat(data):
    '''Update the current heat variable and data.'''
    new_heat_id = data['heat']
    logger.info('Setting current heat to Heat {0}'.format(new_heat_id))
    RACE.current_heat = new_heat_id
    set_current_heat_data(new_heat_id)

@SOCKET_IO.on('generate_heats')
def on_generate_heats(data):
    '''Spawn heat generator thread'''
    gevent.spawn(generate_heats, data)

@catchLogExceptionsWrapper
def generate_heats(data):
    '''Generate heats from qualifying class'''
    RESULTS_TIMEOUT = 30 # maximum time to wait for results to generate

    input_class = int(data['input_class'])
    output_class = int(data['output_class'])
    suffix = data['suffix']
    pilots_per_heat = int(data['pilots_per_heat'])

    if input_class == RHUtils.CLASS_ID_NONE:
        results = {
            'by_race_time': []
        }
        for pilot in RHData.get_pilots():
            # *** if pilot is active
            entry = {}
            entry['pilot_id'] = pilot.id

            pilot_node = RHData.get_recent_pilot_node(pilot.id)

            if pilot_node:
                entry['node'] = pilot_node.node_index
            else:
                entry['node'] = -1

            results['by_race_time'].append(entry)

        win_condition = WinCondition.NONE
        cacheStatus = Results.CacheStatus.VALID
    else:
        race_class = RHData.get_raceClass(input_class)
        race_format = RHData.get_raceFormat(race_class.format_id)
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
        RHData.set_results_raceClass(race_class.id,
            Results.build_atomic_result_cache(RHData, class_id=race_class.id)
            )

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
            new_heat = RHData.add_heat({
                'class_id': output_class,
                'note': ladder + ' ' + suffix
                }, heat)

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
        db_next['lap_time_formatted'] = RHUtils.time_format(db_next['lap_time'], RHData.get_option('timeFormat'))
    elif db_next:
        db_next['lap_time'] = db_next['lap_time_stamp']
        db_next['lap_time_formatted'] = RHUtils.time_format(db_next['lap_time'], RHData.get_option('timeFormat'))

    try:  # delete any split laps for deleted lap
        lap_splits = RHData.get_lapSplits_by_lap(node_index, lap_number)
        if lap_splits and len(lap_splits) > 0:
            for lap_split in lap_splits:
                RHData.clear_lapSplit(lap_split)
    except:
        logger.exception("Error deleting split laps")

    Events.trigger(Evt.LAP_DELETE, {
        #'race': RACE,  # TODO this causes exceptions via 'json.loads()', so leave out for now
        'node_index': node_index,
        })

    logger.info('Lap deleted: Node {0} Lap {1}'.format(node_index+1, lap_index))
    RACE.cacheStatus = Results.CacheStatus.INVALID  # refresh leaderboard
    RACE.team_cacheStatus = Results.CacheStatus.INVALID
    emit_current_laps() # Race page, update web client
    emit_current_leaderboard() # Race page, update web client

@SOCKET_IO.on('simulate_lap')
@catchLogExceptionsWrapper
def on_simulate_lap(data):
    '''Simulates a lap (for debug testing).'''
    node_index = data['node']
    logger.info('Simulated lap: Node {0}'.format(node_index+1))
    Events.trigger(Evt.CROSSING_EXIT, {
        'nodeIndex': node_index,
        'color': led_manager.getDisplayColor(node_index)
        })
    INTERFACE.intf_simulate_lap(node_index, 0)

@SOCKET_IO.on('LED_solid')
@catchLogExceptionsWrapper
def on_LED_solid(data):
    '''LED Solid Color'''
    if 'off' in data and data['off']:
        led_manager.clear()
    else:
        led_red = data['red']
        led_green = data['green']
        led_blue = data['blue']

        on_use_led_effect({
            'effect': "stripColor",
            'args': {
                'color': Color(led_red,led_green,led_blue),
                'pattern': ColorPattern.SOLID,
                'preventIdle': True
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
    RHData.set_option("ledBrightness", brightness)
    Events.trigger(Evt.LED_BRIGHTNESS_SET, {
        'level': brightness,
        })

@SOCKET_IO.on('set_option')
@catchLogExceptionsWrapper
def on_set_option(data):
    RHData.set_option(data['option'], data['value'])
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
    RHData.set_option('voiceCallouts', callouts)
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
    ''' wipe all results caches '''
    Results.invalidate_all_caches(RHData)
    PageCache.set_valid(False)

# Socket io emit functions

def emit_frontend_load(**params):
    '''Emits reload command.'''
    if ('nobroadcast' in params):
        emit('load_all')
    else:
        SOCKET_IO.emit('load_all')

def emit_priority_message(message, interrupt=False, caller=False, **params):
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
                'interrupt': interrupt,
                'caller': caller
                })
        else:
            Events.trigger(Evt.MESSAGE_STANDARD, {
                'message': message,
                'interrupt': interrupt,
                'caller': caller
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

    fdata = []
    for idx in range(RACE.num_nodes):
        fdata.append({
                'band': profile_freqs["b"][idx],
                'channel': profile_freqs["c"][idx],
                'frequency': profile_freqs["f"][idx]
            })

    emit_payload = {
            'fdata': fdata
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
    if CLUSTER:
        if ('nobroadcast' in params):
            emit('cluster_status', CLUSTER.getClusterStatusInfo())
        else:
            SOCKET_IO.emit('cluster_status', CLUSTER.getClusterStatusInfo())

def emit_start_thresh_lower_amount(**params):
    '''Emits current start_thresh_lower_amount.'''
    emit_payload = {
        'start_thresh_lower_amount': RHData.get_option('startThreshLowerAmount'),
    }
    if ('nobroadcast' in params):
        emit('start_thresh_lower_amount', emit_payload)
    elif ('noself' in params):
        emit('start_thresh_lower_amount', emit_payload, broadcast=True, include_self=False)
    else:
        SOCKET_IO.emit('start_thresh_lower_amount', emit_payload)

def emit_start_thresh_lower_duration(**params):
    '''Emits current start_thresh_lower_duration.'''
    emit_payload = {
        'start_thresh_lower_duration': RHData.get_option('startThreshLowerDuration'),
    }
    if ('nobroadcast' in params):
        emit('start_thresh_lower_duration', emit_payload)
    elif ('noself' in params):
        emit('start_thresh_lower_duration', emit_payload, broadcast=True, include_self=False)
    else:
        SOCKET_IO.emit('start_thresh_lower_duration', emit_payload)

def emit_node_tuning(**params):
    '''Emits node tuning values.'''
    tune_val = getCurrentProfile()
    emit_payload = {
        'profile_ids': [profile.id for profile in RHData.get_profiles()],
        'profile_names': [profile.name for profile in RHData.get_profiles()],
        'current_profile': RHData.get_optionInt('currentProfile'),
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
            'language': RHData.get_option("currentLanguage"),
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
        'min_lap': RHData.get_option('MinLapSec'),
        'min_lap_behavior': RHData.get_optionInt("MinLapBehavior")
    }
    if ('nobroadcast' in params):
        emit('min_lap', emit_payload)
    else:
        SOCKET_IO.emit('min_lap', emit_payload)

def emit_race_format(**params):
    '''Emits race format values.'''
    race_format = getCurrentRaceFormat()
    is_db_race_format = RHRaceFormat.isDbBased(race_format)
    locked = not is_db_race_format or RHData.savedRaceMetas_has_raceFormat(race_format.id)
    raceFormats = RHData.get_raceFormats()

    emit_payload = {
        'format_ids': [raceformat.id for raceformat in raceFormats],
        'format_names': [raceformat.name for raceformat in raceFormats],
        'current_format': race_format.id if is_db_race_format else None,
        'format_name': race_format.name,
        'race_mode': race_format.race_mode,
        'race_time_sec': race_format.race_time_sec,
        'start_delay_min': race_format.start_delay_min,
        'start_delay_max': race_format.start_delay_max,
        'staging_tones': race_format.staging_tones,
        'number_laps_win': race_format.number_laps_win,
        'win_condition': race_format.win_condition,
        'start_behavior': race_format.start_behavior,
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
    formats = RHData.get_raceFormats()
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
            'start_behavior': race_format.start_behavior,
            'team_racing_mode': 1 if race_format.team_racing_mode else 0,
        }

        has_race = RHData.savedRaceMetas_has_raceFormat(race_format.id)

        if has_race:
            format_copy['locked'] = True
        else:
            format_copy['locked'] = False

        emit_payload[race_format.id] = format_copy

    if ('nobroadcast' in params):
        emit('race_formats', emit_payload)
    else:
        SOCKET_IO.emit('race_formats', emit_payload)

def build_laps_list(active_race=RACE):
    current_laps = []
    for node in range(active_race.num_nodes):
        node_laps = []
        fastest_lap_time = float("inf")
        fastest_lap_index = None
        last_lap_id = -1
        for idx, lap in enumerate(active_race.node_laps[node]):
            if not lap['deleted']:
                lap_number = lap['lap_number']
                if active_race.format and active_race.format.start_behavior == StartBehavior.FIRST_LAP:
                    lap_number += 1

                splits = get_splits(node, lap['lap_number'], True)
                node_laps.append({
                    'lap_index': idx,
                    'lap_number': lap_number,
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

        if len(active_race.node_pilots) and active_race.node_pilots[node]:
            pilot = RHData.get_pilot(active_race.node_pilots[node])
            pilot_data = {
                'id': pilot.id,
                'name': pilot.name,
                'callsign': pilot.callsign
            }
        else:
            pilot_data = None

        current_laps.append({
            'laps': node_laps,
            'fastest_lap_index': fastest_lap_index,
            'pilot': pilot_data
        })
    current_laps = {
        'node_index': current_laps
    }
    return current_laps

def emit_current_laps(**params):
    '''Emits current laps.'''
    emit_payload = {
        'current': {}
    }
    emit_payload['current'] = build_laps_list(RACE)

    if LAST_RACE is not None:
        emit_payload['last_race'] = build_laps_list(LAST_RACE)

    if ('nobroadcast' in params):
        emit('current_laps', emit_payload)
    else:
        SOCKET_IO.emit('current_laps', emit_payload)

def get_splits(node, lap_id, lapCompleted):
    splits = []
    if CLUSTER:
        for secondary_index in range(len(CLUSTER.secondaries)):
            if CLUSTER.isSplitSecondaryAvailable(secondary_index):
                split = RHData.get_lapSplit_by_params(node, lap_id, secondary_index)
                if split:
                    split_payload = {
                        'split_id': secondary_index,
                        'split_raw': split.split_time,
                        'split_time': split.split_time_formatted,
                        'split_speed': '{0:.2f}'.format(split.split_speed) if split.split_speed is not None else None
                    }
                elif lapCompleted:
                    split_payload = {
                        'split_id': secondary_index,
                        'split_time': '-'
                    }
                else:
                    break
                splits.append(split_payload)
    return splits

def emit_race_list(**params):
    '''Emits race listing'''
    heats = {}
    for heat in RHData.get_heats():
        if RHData.savedRaceMetas_has_heat(heat.id):
            heatnote = RHData.get_heat(heat.id).note
            rounds = {}
            for race in RHData.get_savedRaceMetas_by_heat(heat.id):
                pilotraces = []
                for pilotrace in RHData.get_savedPilotRaces_by_savedRaceMeta(race.id):
                    laps = []
                    for lap in RHData.get_savedRaceLaps_by_savedPilotRace(pilotrace.id):
                        laps.append({
                                'id': lap.id,
                                'lap_time_stamp': lap.lap_time_stamp,
                                'lap_time': lap.lap_time,
                                'lap_time_formatted': lap.lap_time_formatted,
                                'source': lap.source,
                                'deleted': lap.deleted
                            })

                    pilot_data = RHData.get_pilot(pilotrace.pilot_id)
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
                rounds[race.round_id] = {
                    'race_id': race.id,
                    'class_id': race.class_id,
                    'format_id': race.format_id,
                    'start_time': race.start_time,
                    'start_time_formatted': race.start_time_formatted,
                    'pilotraces': pilotraces
                }
            heats[heat.id] = {
                'heat_id': heat.id,
                'note': heatnote,
                'rounds': rounds,
            }

    emit_payload = {
        'heats': heats,
        # 'heats_by_class': heats_by_class,
        # 'classes': current_classes,
    }

    if ('nobroadcast' in params):
        emit('race_list', emit_payload)
    else:
        SOCKET_IO.emit('race_list', emit_payload)

def emit_result_data(**params):
    ''' kick off non-blocking thread to generate data'''
    if request:
        gevent.spawn(emit_result_data_thread, params, request.sid)
    else:
        gevent.spawn(emit_result_data_thread, params)

@catchLogExceptionsWrapper
def emit_result_data_thread(params, sid=None):
    with APP.test_request_context():

        emit_payload = PageCache.get_cache()

        if 'nobroadcast' in params and sid != None:
            emit('result_data', emit_payload, namespace='/', room=sid)
        else:
            SOCKET_IO.emit('result_data', emit_payload, namespace='/')

def emit_current_leaderboard(**params):
    '''Emits leaderboard.'''

    emit_payload = {
        'current': {}
    }

    # current
    emit_payload['current']['heat'] = RACE.current_heat
    emit_payload['current']['heat_note'] = RHData.get_heat(RACE.current_heat).note
    emit_payload['current']['status_msg'] = RACE.status_message

    if RACE.cacheStatus == Results.CacheStatus.VALID:
        emit_payload['current']['leaderboard'] = RACE.results
    else:
        results = Results.calc_leaderboard(RHData, current_race=RACE, current_profile=getCurrentProfile())
        RACE.results = results
        RACE.cacheStatus = Results.CacheStatus.VALID
        emit_payload['current']['leaderboard'] = results

    if RACE.format.team_racing_mode:
        if RACE.team_cacheStatus == Results.CacheStatus.VALID:
            emit_payload['current']['team_leaderboard'] = RACE.team_results
        else:
            team_results = Results.calc_team_leaderboard(RACE, RHData)
            RACE.team_results = team_results
            RACE.team_cacheStatus = Results.CacheStatus.VALID
            emit_payload['current']['team_leaderboard'] = team_results

    # cache
    if LAST_RACE is not None:
        emit_payload['last_race'] = {}
        emit_payload['last_race']['status_msg'] = LAST_RACE.status_message

        if LAST_RACE.cacheStatus == Results.CacheStatus.VALID:
            emit_payload['last_race']['leaderboard'] = LAST_RACE.results
            emit_payload['last_race']['heat'] = LAST_RACE.current_heat
            emit_payload['last_race']['heat_note'] = RHData.get_heat(LAST_RACE.current_heat).note

        if LAST_RACE.team_cacheStatus == Results.CacheStatus.VALID and LAST_RACE.format.team_racing_mode:
            emit_payload['last_race']['team_leaderboard'] = LAST_RACE.team_results

    if ('nobroadcast' in params):
        emit('leaderboard', emit_payload)
    else:
        SOCKET_IO.emit('leaderboard', emit_payload)

def emit_heat_data(**params):
    '''Emits heat data.'''
    current_heats = {}
    for heat in RHData.get_heats():
        heat_id = heat.id
        note = heat.note
        race_class = heat.class_id

        heatnodes = RHData.get_heatNodes_by_heat(heat.id)
        pilots = []
        for heatnode in heatnodes:
            pilots.append(heatnode.pilot_id)

        has_race = RHData.savedRaceMetas_has_heat(heat.id)

        if has_race:
            locked = True
        else:
            locked = False

        current_heats[heat_id] = {
            'pilots': pilots,
            'note': note,
            'heat_id': heat_id,
            'class_id': race_class,
            'locked': locked}

    current_classes = []
    for race_class in RHData.get_raceClasses():
        current_class = {}
        current_class['id'] = race_class.id
        current_class['name'] = race_class.name
        current_class['description'] = race_class.description
        current_classes.append(current_class)

    pilots = []
    for pilot in RHData.get_pilots():
        pilots.append({
            'pilot_id': pilot.id,
            'callsign': pilot.callsign,
            'name': pilot.name
            })

    if RHData.get_option('pilotSort') == 'callsign':
        pilots.sort(key=lambda x: (x['callsign'], x['name']))
    else:
        pilots.sort(key=lambda x: (x['name'], x['callsign']))

    emit_payload = {
        'heats': current_heats,
        'pilot_data': pilots,
        'classes': current_classes,
        'pilotSort': RHData.get_option('pilotSort'),
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
    for race_class in RHData.get_raceClasses():
        current_class = {}
        current_class['id'] = race_class.id
        current_class['name'] = race_class.name
        current_class['description'] = race_class.description
        current_class['format'] = race_class.format_id
        current_class['locked'] = RHData.savedRaceMetas_has_raceClass(race_class.id)

        current_classes.append(current_class)

    formats = []
    for race_format in RHData.get_raceFormats():
        raceformat = {}
        raceformat['id'] = race_format.id
        raceformat['name'] = race_format.name
        raceformat['race_mode'] = race_format.race_mode
        raceformat['race_time_sec'] = race_format.race_time_sec
        raceformat['start_delay_min'] = race_format.start_delay_min
        raceformat['start_delay_max'] = race_format.start_delay_max
        raceformat['staging_tones'] = race_format.staging_tones
        raceformat['number_laps_win'] = race_format.number_laps_win
        raceformat['win_condition'] = race_format.win_condition
        raceformat['team_racing_mode'] = race_format.team_racing_mode
        raceformat['start_behavior'] = race_format.start_behavior
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
    for pilot in RHData.get_pilots():
        opts_str = '' # create team-options string for each pilot, with current team selected
        for name in TEAM_NAMES_LIST:
            opts_str += '<option value="' + name + '"'
            if name == pilot.team:
                opts_str += ' selected'
            opts_str += '>' + name + '</option>'

        locked = RHData.savedPilotRaces_has_pilot(pilot.id)

        pilot_data = {
            'pilot_id': pilot.id,
            'callsign': pilot.callsign,
            'team': pilot.team,
            'phonetic': pilot.phonetic,
            'name': pilot.name,
            'team_options': opts_str,
            'locked': locked,
        }

        if led_manager.isEnabled():
            pilot_data['color'] = pilot.color

        pilots_list.append(pilot_data)

        if RHData.get_option('pilotSort') == 'callsign':
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

    heat_data = RHData.get_heat(RACE.current_heat)

    heatNode_data = {}
    for heatNode in RHData.get_heatNodes_by_heat(RACE.current_heat):
        heatNode_data[heatNode.node_index] = {
            'pilot_id': heatNode.pilot_id,
            'callsign': None,
            'heatNodeColor': heatNode.color,
            'pilotColor': None,
            'activeColor': None
            }
        pilot = RHData.get_pilot(heatNode.pilot_id)
        if pilot:
            heatNode_data[heatNode.node_index]['callsign'] = pilot.callsign
            heatNode_data[heatNode.node_index]['pilotColor'] = pilot.color

        if led_manager.isEnabled():
            heatNode_data[heatNode.node_index]['activeColor'] = led_manager.getDisplayColor(heatNode.node_index)

    heat_format = None
    if heat_data.class_id != RHUtils.CLASS_ID_NONE:
        heat_format = RHData.get_raceClass(heat_data.class_id).format_id

    emit_payload = {
        'current_heat': RACE.current_heat,
        'heatNodes': heatNode_data,
        'callsign': callsigns,
        'pilot_ids': pilot_ids,
        'heat_note': heat_data.note,
        'heat_format': heat_format,
        'heat_class': heat_data.class_id
    }
    if ('nobroadcast' in params):
        emit('current_heat', emit_payload)
    else:
        SOCKET_IO.emit('current_heat', emit_payload)

def emit_phonetic_data(pilot_id, lap_id, lap_time, team_name, team_laps, leader_flag=False, **params):
    '''Emits phonetic data.'''
    raw_time = lap_time
    phonetic_time = RHUtils.phonetictime_format(lap_time, RHData.get_option('timeFormatPhonetic'))
    pilot = RHData.get_pilot(pilot_id)
    emit_payload = {
        'pilot': pilot.phonetic,
        'callsign': pilot.callsign,
        'pilot_id': pilot.id,
        'lap': lap_id,
        'raw_time': raw_time,
        'phonetic': phonetic_time,
        'team_name' : team_name,
        'team_laps' : team_laps,
        'leader_flag' : leader_flag
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

def emit_phonetic_text(text_str, domain=False, winner_flag=False, **params):
    '''Emits given phonetic text.'''
    emit_payload = {
        'text': text_str,
        'domain': domain,
        'winner_flag': winner_flag
    }
    if ('nobroadcast' in params):
        emit('phonetic_text', emit_payload)
    else:
        SOCKET_IO.emit('phonetic_text', emit_payload)

def emit_phonetic_split(pilot_id, split_id, split_time, **params):
    '''Emits phonetic split-pass data.'''
    pilot = RHData.get_pilot(pilot_id)
    phonetic_name = pilot.phonetic or pilot.callsign
    phonetic_time = RHUtils.phonetictime_format(split_time, RHData.get_option('timeFormatPhonetic'))
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

def emit_cluster_connect_change(connect_flag, **params):
    '''Emits connect/disconnect tone for cluster timer.'''
    emit_payload = {
        'connect_flag': connect_flag
    }
    if ('nobroadcast' in params):
        emit('cluster_connect_change', emit_payload)
    else:
        SOCKET_IO.emit('cluster_connect_change', emit_payload)

def emit_callouts():
    callouts = RHData.get_option('voiceCallouts')
    if callouts:
        emit('callouts', json.loads(callouts))

def emit_imdtabler_page(**params):
    '''Emits IMDTabler page, using current profile frequencies.'''
    if Use_imdtabler_jar_flag:
        try:                          # get IMDTabler version string
            imdtabler_ver = subprocess.check_output( \
                                'java -jar ' + IMDTABLER_JAR_NAME + ' -v', shell=True).decode("utf-8").rstrip()
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
                        'java -jar ' + IMDTABLER_JAR_NAME + ' -t ' + ' '.join(fs_list), shell=True).decode("utf-8")
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
                        'java -jar ' + IMDTABLER_JAR_NAME + ' -r ' + ' '.join(fs_list), shell=True).decode("utf-8").rstrip()
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

@SOCKET_IO.on('check_bpillfw_file')
@catchLogExceptionsWrapper
def check_bpillfw_file(data):
    fileStr = data['src_file_str']
    logger.debug("Checking node firmware file: " + fileStr)
    dataStr = None
    try:
        dataStr = stm32loader.load_source_file(fileStr, False)
    except Exception as ex:
        SOCKET_IO.emit('upd_set_info_text', "Error reading firmware file: {}<br><br><br><br>".format(ex))
        logger.debug("Error reading file '{}' in 'check_bpillfw_file()': {}".format(fileStr, ex))
        return
    try:  # find version, processor-type and build-timestamp strings in firmware '.bin' file
        rStr = RHUtils.findPrefixedSubstring(dataStr, INTERFACE.FW_VERSION_PREFIXSTR, \
                                             INTERFACE.FW_TEXT_BLOCK_SIZE)
        fwVerStr = rStr if rStr else "(unknown)"
        fwRTypStr = RHUtils.findPrefixedSubstring(dataStr, INTERFACE.FW_PROCTYPE_PREFIXSTR, \
                                             INTERFACE.FW_TEXT_BLOCK_SIZE)
        fwTypStr = (fwRTypStr + ", ") if fwRTypStr else ""
        rStr = RHUtils.findPrefixedSubstring(dataStr, INTERFACE.FW_BUILDDATE_PREFIXSTR, \
                                             INTERFACE.FW_TEXT_BLOCK_SIZE)
        if rStr:
            fwTimStr = rStr
            rStr = RHUtils.findPrefixedSubstring(dataStr, INTERFACE.FW_BUILDTIME_PREFIXSTR, \
                                                 INTERFACE.FW_TEXT_BLOCK_SIZE)
            if rStr:
                fwTimStr += " " + rStr
        else:
            fwTimStr = "unknown"
        fileSize = len(dataStr)
        logger.debug("Node update firmware file size={}, version={}, {}build timestamp: {}".\
                     format(fileSize, fwVerStr, fwTypStr, fwTimStr))
        infoStr = "Firmware update file size = {}<br>".format(fileSize) + \
                  "Firmware update version: {} ({}Build timestamp: {})<br><br>".\
                  format(fwVerStr, fwTypStr, fwTimStr)
        info_node = INTERFACE.get_info_node_obj()
        curNodeStr = info_node.firmware_version_str if info_node else None
        if curNodeStr:
            tsStr = info_node.firmware_timestamp_str
            if tsStr:
                curRTypStr = info_node.firmware_proctype_str
                ptStr = (curRTypStr + ", ") if curRTypStr else ""
                curNodeStr += " ({}Build timestamp: {})".format(ptStr, tsStr)
        else:
            curRTypStr = None
            curNodeStr = "(unknown)"
        infoStr += "Current firmware version: " + curNodeStr
        if fwRTypStr and curRTypStr and fwRTypStr != curRTypStr:
            infoStr += "<br><br><b>Warning</b>: Firmware file processor type ({}) does not match current ({})".\
                        format(fwRTypStr, curRTypStr)
        SOCKET_IO.emit('upd_set_info_text', infoStr)
        SOCKET_IO.emit('upd_enable_update_button')
    except Exception as ex:
        SOCKET_IO.emit('upd_set_info_text', "Error processing firmware file: {}<br><br><br><br>".format(ex))
        logger.exception("Error processing file '{}' in 'check_bpillfw_file()'".format(fileStr))

@SOCKET_IO.on('do_bpillfw_update')
@catchLogExceptionsWrapper
def do_bpillfw_update(data):
    srcStr = data['src_file_str']
    portStr = INTERFACE.get_fwupd_serial_name()
    msgStr = "Performing S32_BPill update, port='{}', file: {}".format(portStr, srcStr)
    logger.info(msgStr)
    SOCKET_IO.emit('upd_messages_init', (msgStr + "\n"))
    stop_background_threads()
    gevent.sleep(0.1)
    try:
        jump_to_node_bootloader()
        INTERFACE.close_fwupd_serial_port()
        s32Logger = logging.getLogger("stm32loader")
        def doS32Log(msgStr):  # send message to update-messages window and log file
            SOCKET_IO.emit('upd_messages_append', msgStr)
            gevent.idle()  # do thread yield to allow display updates
            s32Logger.info(msgStr)
            gevent.idle()  # do thread yield to allow display updates
            log.wait_for_queue_empty()
        stm32loader.set_console_output_fn(doS32Log)
        successFlag = stm32loader.flash_file_to_stm32(portStr, srcStr)
        msgStr = "Node update " + ("succeeded; restarting interface" \
                                   if successFlag else "failed")
        logger.info(msgStr)
        SOCKET_IO.emit('upd_messages_append', ("\n" + msgStr))
    except:
        logger.exception("Error in 'do_bpillfw_update()'")
    stm32loader.set_console_output_fn(None)
    gevent.sleep(0.2)
    logger.info("Reinitializing RH interface")
    ui_server_messages.clear()
    initialize_rh_interface()
    if RACE.num_nodes <= 0:
        SOCKET_IO.emit('upd_messages_append', "\nWarning: No receiver nodes found")
    buildServerInfo()
    reportServerInfo()
    init_race_state()
    start_background_threads(True)
    SOCKET_IO.emit('upd_messages_finish')  # show 'Close' button

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
    '''Emits 'pass_record' message (will be consumed by primary timer in cluster, livetime, etc).'''
    payload = {
        'node': node.index,
        'frequency': node.frequency,
        'timestamp': lap_time_stamp + RACE.start_time_epoch_ms
    }
    emit_cluster_msg_to_primary('pass_record', payload)


def emit_exporter_list():
    '''List Database Exporters'''

    emit_payload = {
        'exporters': []
    }

    for name, exp in export_manager.getExporters().items():
        emit_payload['exporters'].append({
            'name': name,
            'label': exp.label
        })

    emit('exporter_list', emit_payload)

#
# Program Functions
#

def heartbeat_thread_function():
    '''Emits current rssi data, etc'''
    gevent.sleep(0.010)  # allow time for connection handshake to terminate before emitting data

    while True:
        try:
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

@catchLogExceptionsWrapper
def clock_check_thread_function():
    ''' Monitor system clock and adjust PROGRAM_START_EPOCH_TIME if significant jump detected.
        (This can happen if NTP synchronization occurs after server starts up.) '''
    global PROGRAM_START_EPOCH_TIME
    global MTONIC_TO_EPOCH_MILLIS_OFFSET
    global serverInfoItems
    try:
        while True:
            gevent.sleep(10)
            if RACE.any_races_started:  # stop monitoring after any race started
                break
            time_now = monotonic()
            epoch_now = int((RHTimeFns.getUtcDateTimeNow() - EPOCH_START).total_seconds() * 1000)
            diff_ms = epoch_now - monotonic_to_epoch_millis(time_now)
            if abs(diff_ms) > 30000:
                PROGRAM_START_EPOCH_TIME += diff_ms
                MTONIC_TO_EPOCH_MILLIS_OFFSET = epoch_now - 1000.0*time_now
                logger.info("Adjusting PROGRAM_START_EPOCH_TIME for shift in system clock ({0:.1f} secs) to: {1:.0f}".\
                            format(diff_ms/1000, PROGRAM_START_EPOCH_TIME))
                # update values that will be reported if running as cluster timer
                serverInfoItems['prog_start_epoch'] = "{0:.0f}".format(PROGRAM_START_EPOCH_TIME)
                serverInfoItems['prog_start_time'] = str(datetime.utcfromtimestamp(PROGRAM_START_EPOCH_TIME/1000.0))
                if has_joined_cluster():
                    logger.debug("Emitting 'join_cluster_response' message with updated 'prog_start_epoch'")
                    emit_join_cluster_response()
    except KeyboardInterrupt:
        logger.info("clock_check_thread terminated by keyboard interrupt")
        raise
    except SystemExit:
        raise
    except Exception:
        logger.exception('Exception in clock_check_thread')

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

@catchLogExcDBCloseWrapper
def pass_record_callback(node, lap_timestamp_absolute, source):
    '''Handles pass records from the nodes.'''

    node.pass_crossing_flag = False  # clear the "synchronized" version of the crossing flag
    node.debug_pass_count += 1
    emit_node_data() # For updated triggers and peaks

    profile_freqs = json.loads(getCurrentProfile().frequencies)
    if profile_freqs["f"][node.index] != RHUtils.FREQUENCY_ID_NONE:
        # always count laps if race is running, otherwise test if lap should have counted before race end (RACE.duration_ms is invalid while race is in progress)
        if RACE.race_status is RaceStatus.RACING \
            or (RACE.race_status is RaceStatus.DONE and \
                lap_timestamp_absolute < RACE.end_time):

            # Get the current pilot id on the node
            pilot_id = RHData.get_pilot_from_heatNode(RACE.current_heat, node.index)

            # reject passes before race start and with disabled (no-pilot) nodes
            if getCurrentRaceFormat() is SECONDARY_RACE_FORMAT or pilot_id != RHUtils.PILOT_ID_NONE:
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
                    if race_format is SECONDARY_RACE_FORMAT:
                        min_lap = 0  # don't enforce min-lap time if running as secondary timer
                        min_lap_behavior = 0
                    else:
                        min_lap = RHData.get_optionInt("MinLapSec")
                        min_lap_behavior = RHData.get_optionInt("MinLapBehavior")

                    if RACE.timer_running is False:
                        RACE.node_has_finished[node.index] = True

                    lap_time_fmtstr = RHUtils.time_format(lap_time, RHData.get_option('timeFormat'))
                    lap_ts_fmtstr = RHUtils.time_format(lap_time_stamp, RHData.get_option('timeFormat'))
                    pilot_namestr = RHData.get_pilot(pilot_id).callsign

                    lap_ok_flag = True
                    if lap_number != 0:  # if initial lap then always accept and don't check lap time; else:
                        if lap_time < (min_lap * 1000):  # if lap time less than minimum
                            node.under_min_lap_count += 1
                            logger.info('Pass record under lap minimum ({}): Node={}, lap={}, lapTime={}, sinceStart={}, count={}, source={}, pilot: {}' \
                                       .format(min_lap, node.index+1, lap_number, \
                                               lap_time_fmtstr, lap_ts_fmtstr, \
                                               node.under_min_lap_count, INTERFACE.get_lap_source_str(source), \
                                               pilot_namestr))
                            if min_lap_behavior != 0:  # if behavior is 'Discard New Short Laps'
                                lap_ok_flag = False

                    if lap_ok_flag:

                        if logger.getEffectiveLevel() <= logging.DEBUG:  # if DEBUG msgs actually being logged
                            enter_fmtstr = RHUtils.time_format((node.enter_at_timestamp-RACE.start_time_monotonic)*1000, \
                                                               RHData.get_option('timeFormat')) \
                                           if node.enter_at_timestamp else "0"
                            exit_fmtstr = RHUtils.time_format((node.exit_at_timestamp-RACE.start_time_monotonic)*1000, \
                                                              RHData.get_option('timeFormat')) \
                                           if node.exit_at_timestamp else "0"
                            logger.debug('Lap pass: Node={}, lap={}, lapTime={}, sinceStart={}, abs_ts={:.3f}, source={}, enter={}, exit={}, dur={:.0f}ms, pilot: {}' \
                                        .format(node.index+1, lap_number, lap_time_fmtstr, lap_ts_fmtstr, \
                                                lap_timestamp_absolute, INTERFACE.get_lap_source_str(source), \
                                                enter_fmtstr, exit_fmtstr, \
                                                (node.exit_at_timestamp-node.enter_at_timestamp)*1000, pilot_namestr))

                        # emit 'pass_record' message (to primary timer in cluster, livetime, etc).
                        emit_pass_record(node, lap_time_stamp)

                        # Add the new lap to the database
                        lap_data = {
                            'lap_number': lap_number,
                            'lap_time_stamp': lap_time_stamp,
                            'lap_time': lap_time,
                            'lap_time_formatted': lap_time_fmtstr,
                            'source': source,
                            'deleted': False
                        }
                        RACE.node_laps[node.index].append(lap_data)

                        RACE.results = Results.calc_leaderboard(RHData, current_race=RACE, current_profile=getCurrentProfile())
                        RACE.cacheStatus = Results.CacheStatus.VALID

                        if RACE.format.team_racing_mode:
                            RACE.team_results = Results.calc_team_leaderboard(RACE, RHData)
                            RACE.team_cacheStatus = Results.CacheStatus.VALID

                        Events.trigger(Evt.RACE_LAP_RECORDED, {
                            'node_index': node.index,
                            'color': led_manager.getDisplayColor(node.index),
                            'lap': lap_data,
                            'results': RACE.results
                            })

                        emit_current_laps() # update all laps on the race page
                        emit_current_leaderboard() # generate and update leaderboard

                        if lap_number == 0:
                            emit_first_pass_registered(node.index) # play first-pass sound

                        if race_format and race_format.start_behavior == StartBehavior.FIRST_LAP:
                            lap_number += 1

                        # announce lap
                        if lap_number > 0:
                            check_leader = race_format.win_condition != WinCondition.NONE and \
                                           RACE.win_status != WinStatus.DECLARED
                            if RACE.format.team_racing_mode:
                                team = RHData.get_pilot(pilot_id).team
                                team_laps = RACE.team_results['meta']['teams'][team]['laps']
                                logger.debug('Lap pass: Node={}, lap={}, pilot={} -> Team {} lap {}' \
                                        .format(node.index+1, lap_number, pilot_namestr, team, team_laps))
                                emit_phonetic_data(pilot_id, lap_number, lap_time, team, team_laps, \
                                                (check_leader and \
                                                 team == Results.get_leading_team_name(RACE.team_results)))
                            else:
                                emit_phonetic_data(pilot_id, lap_number, lap_time, None, None, \
                                                (check_leader and \
                                                 pilot_id == Results.get_leading_pilot_id(RACE.results)))

                            check_win_condition() # check for and announce possible winner
                            if RACE.win_status != WinStatus.NONE:
                                emit_current_leaderboard()  # show current race status on leaderboard

                    else:
                        # record lap as 'deleted'
                        RACE.node_laps[node.index].append({
                            'lap_number': lap_number,
                            'lap_time_stamp': lap_time_stamp,
                            'lap_time': lap_time,
                            'lap_time_formatted': lap_time_fmtstr,
                            'source': source,
                            'deleted': True
                        })
                else:
                    logger.debug('Pass record dismissed: Node {}, Race not started (abs_ts={:.3f}, source={})' \
                        .format(node.index+1, lap_timestamp_absolute, INTERFACE.get_lap_source_str(source)))
            else:
                logger.debug('Pass record dismissed: Node {}, Pilot not defined (abs_ts={:.3f}, source={})' \
                    .format(node.index+1, lap_timestamp_absolute, INTERFACE.get_lap_source_str(source)))
    else:
        logger.debug('Pass record dismissed: Node {}, Frequency not defined (abs_ts={:.3f}, source={})' \
            .format(node.index+1, lap_timestamp_absolute, INTERFACE.get_lap_source_str(source)))

def check_win_condition(**kwargs):
    previous_win_status = RACE.win_status

    win_status = Results.check_win_condition(RACE, RHData, INTERFACE, **kwargs)

    if win_status is not None:
        race_format = RACE.format
        RACE.win_status = win_status['status']

        if win_status['status'] == WinStatus.DECLARED:
            # announce winner
            if race_format.team_racing_mode:
                win_str = win_status['data']['name']
                RACE.status_message = __('Winner is') + ' ' + __('Team') + ' ' + win_str
                logger.info("Race status msg:  Winner is Team " + win_str)
                emit_phonetic_text(RACE.status_message, 'race_winner', True)
            else:
                win_str = win_status['data']['callsign']
                RACE.status_message = __('Winner is') + ' ' + win_str
                logger.info("Race status msg:  Winner is " + win_str)
                win_phon_name = RHData.get_pilot(win_status['data']['pilot_id']).phonetic
                if len(win_phon_name) <= 0:  # if no phonetic then use callsign
                    win_phon_name = win_status['data']['callsign']
                emit_phonetic_text(__('Winner is') + ' ' + win_phon_name, 'race_winner', True)

            Events.trigger(Evt.RACE_WIN, {
                'win_status': win_status,
                'message': RACE.status_message,
                'node_index': win_status['data']['node'] if 'node' in win_status['data'] else None,
                'color': led_manager.getDisplayColor(win_status['data']['node']) if 'node' in win_status['data'] else None,
                'results': RACE.results
                })

        elif win_status['status'] == WinStatus.TIE:
            # announce tied
            if win_status['status'] != previous_win_status:
                RACE.status_message = __('Race Tied')
                logger.info("Race status msg:  Race Tied")
                emit_phonetic_text(RACE.status_message, 'race_winner')
        elif win_status['status'] == WinStatus.OVERTIME:
            # announce overtime
            if win_status['status'] != previous_win_status:
                RACE.status_message = __('Race Tied: Overtime')
                logger.info("Race status msg:  Race Tied: Overtime")
                emit_phonetic_text(RACE.status_message, 'race_winner')

        if 'max_consideration' in win_status:
            logger.info("Waiting {0}ms to declare winner.".format(win_status['max_consideration']))
            gevent.sleep(win_status['max_consideration'] / 1000)
            if 'start_token' in kwargs and RACE.start_token == kwargs['start_token']:
                logger.info("Maximum win condition consideration time has expired.")
                check_win_condition(forced=True)

    return win_status

@catchLogExcDBCloseWrapper
def new_enter_or_exit_at_callback(node, is_enter_at_flag):
    gevent.sleep(0.025)  # delay to avoid potential I/O error
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

@catchLogExcDBCloseWrapper
def node_crossing_callback(node):
    emit_node_crossing_change(node)
    # handle LED gate-status indicators:

    if RACE.race_status == RaceStatus.RACING:  # if race is in progress
        # if pilot assigned to node and first crossing is complete
        if getCurrentRaceFormat() is SECONDARY_RACE_FORMAT or (
            node.current_pilot_id != RHUtils.PILOT_ID_NONE and node.first_cross_flag):
            # first crossing has happened; if 'enter' then show indicator,
            #  if first event is 'exit' then ignore (because will be end of first crossing)
            if node.crossing_flag:
                Events.trigger(Evt.CROSSING_ENTER, {
                    'nodeIndex': node.index,
                    'color': led_manager.getDisplayColor(node.index)
                    })
                node.show_crossing_flag = True
            else:
                if node.show_crossing_flag:
                    Events.trigger(Evt.CROSSING_EXIT, {
                        'nodeIndex': node.index,
                        'color': led_manager.getDisplayColor(node.index)
                        })
                else:
                    node.show_crossing_flag = True

def default_frequencies():
    '''Set node frequencies, R1367 for 4, IMD6C+ for 5+.'''
    if RACE.num_nodes < 5:
        freqs = {
            'b': ['R', 'R', 'R', 'R', None, None, None, None],
            'c': [1, 3, 6, 7, None, None, None, None],
            'f': [5658, 5732, 5843, 5880, RHUtils.FREQUENCY_ID_NONE, RHUtils.FREQUENCY_ID_NONE, RHUtils.FREQUENCY_ID_NONE, RHUtils.FREQUENCY_ID_NONE]
        }
    else:
        freqs = {
            'b': ['R', 'R', 'F', 'F', 'R', 'R', None, None],
            'c': [1, 2, 2, 4, 7, 8, None, None],
            'f': [5658, 5695, 5760, 5800, 5880, 5917, RHUtils.FREQUENCY_ID_NONE, RHUtils.FREQUENCY_ID_NONE]
        }

        while RACE.num_nodes > len(freqs['f']):
            freqs['b'].append(None)
            freqs['c'].append(None)
            freqs['f'].append(RHUtils.FREQUENCY_ID_NONE)

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
            'band': freqs["b"][idx],
            'channel': freqs["c"][idx]
            })

        logger.info('Frequency set: Node {0} B:{1} Ch:{2} Freq:{3}'.format(idx+1, freqs["b"][idx], freqs["c"][idx], freqs["f"][idx]))

def emit_current_log_file_to_socket():
    if Current_log_path_name:
        try:
            with io.open(Current_log_path_name, 'r') as f:
                SOCKET_IO.emit("hardware_log_init", f.read())
        except Exception:
            logger.exception("Error sending current log file to socket")
    log.start_socket_forward_handler()

def db_init(nofill=False):
    '''Initialize database.'''
    RHData.db_init(nofill)
    reset_current_laps()
    setCurrentRaceFormat(RHData.get_first_raceFormat())
    assign_frequencies()
    Events.trigger(Evt.DATABASE_INITIALIZE)
    logger.info('Database initialized')

def db_reset():
    '''Resets database.'''
    RHData.reset_all()
    reset_current_laps()
    setCurrentRaceFormat(RHData.get_first_raceFormat())
    assign_frequencies()
    logger.info('Database reset')

def reset_current_laps():
    '''Resets database current laps to default.'''
    RACE.node_laps = {}
    for idx in range(RACE.num_nodes):
        RACE.node_laps[idx] = []

    RACE.cacheStatus = Results.CacheStatus.INVALID
    RACE.team_cacheStatus = Results.CacheStatus.INVALID
    logger.debug('Database current laps reset')

def expand_heats():
    ''' ensure loaded data includes enough slots for current nodes '''
    heatNode_data = {}
    for heatNode in RHData.get_heatNodes():
        if heatNode.heat_id not in heatNode_data:
            heatNode_data[heatNode.heat_id] = []

        heatNode_data[heatNode.heat_id].append(heatNode.node_index)

    for heat_id, nodes in heatNode_data.items():
        for node_index in range(RACE.num_nodes):
            if node_index not in nodes:
                RHData.add_heatNode(heat_id, node_index)

def init_race_state():
    expand_heats()

    # Send profile values to nodes
    on_set_profile({'profile': getCurrentProfile().id}, False)

    # Set current heat
    first_heat = RHData.get_first_heat()
    if first_heat:
        RACE.current_heat = first_heat.id
        RACE.node_pilots = {}
        RACE.node_teams = {}
        for heatNode in RHData.get_heatNodes_by_heat(RACE.current_heat):
            RACE.node_pilots[heatNode.node_index] = heatNode.pilot_id

            if heatNode.pilot_id is not RHUtils.PILOT_ID_NONE:
                RACE.node_teams[heatNode.node_index] = RHData.get_pilot(heatNode.pilot_id).team
            else:
                RACE.node_teams[heatNode.node_index] = None

    # Set race format
    raceformat_id = RHData.get_optionInt('currentFormat')
    race_format = RHData.get_raceFormat(raceformat_id)
    setCurrentRaceFormat(race_format, silent=True)

    # Normalize results caches
    Results.normalize_cache_status(RHData)
    PageCache.set_valid(False)

def init_interface_state(startup=False):
    # Cancel current race
    if startup:
        RACE.race_status = RaceStatus.READY # Go back to ready state
        INTERFACE.set_race_status(RaceStatus.READY)
        Events.trigger(Evt.LAPS_CLEAR)
        RACE.timer_running = False # indicate race timer not running
        RACE.scheduled = False # also stop any deferred start
        SOCKET_IO.emit('stop_timer')
    else:
        on_stop_race()
    # Reset laps display
    reset_current_laps()

def init_LED_effects():
    # start with defaults
    effects = {
        Evt.RACE_STAGE: "stripColor2_1",
        Evt.RACE_START: "stripColorSolid",
        Evt.RACE_FINISH: "stripColor4_4",
        Evt.RACE_STOP: "stripColorSolid",
        Evt.LAPS_CLEAR: "clear",
        Evt.CROSSING_ENTER: "stripSparkle",
        Evt.CROSSING_EXIT: "none",
        Evt.RACE_LAP_RECORDED: "none",
        Evt.RACE_WIN: "none",
        Evt.MESSAGE_STANDARD: "none",
        Evt.MESSAGE_INTERRUPT: "none",
        Evt.STARTUP: "rainbowCycle",
        Evt.SHUTDOWN: "clear",
        LEDEvent.IDLE_DONE: "clear",
        LEDEvent.IDLE_READY: "clear",
        LEDEvent.IDLE_RACING: "clear",
    }
    if "bitmapRHLogo" in led_manager.getRegisteredEffects() and Config.LED['LED_ROWS'] > 1:
        effects[Evt.STARTUP] = "bitmapRHLogo"
        effects[Evt.RACE_STAGE] = "bitmapOrangeEllipsis"
        effects[Evt.RACE_START] = "bitmapGreenArrow"
        effects[Evt.RACE_FINISH] = "bitmapCheckerboard"
        effects[Evt.RACE_STOP] = "bitmapRedX"

    # update with DB values (if any)
    effect_opt = RHData.get_option('ledEffects')
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
    return VRxController(
        RHData,
        Events,
        vrx_config,
        RACE,
        [node.frequency for node in INTERFACE.nodes],
        Language)

def killVRxController(*args):
    global vrx_controller
    logger.info('Killing VRxController')
    vrx_controller = None

def determineHostAddress(maxRetrySecs=10):
    ''' Determines local host IP address.  Will wait and retry to get valid IP, in
        case system is starting up and needs time to connect to network and DHCP. '''
    global server_ipaddress_str
    if server_ipaddress_str:
        return server_ipaddress_str  # if previously determined then return value
    sTime = monotonic()
    while True:
        try:
            ipAddrStr = RHUtils.getLocalIPAddress()
            if ipAddrStr and ipAddrStr != "127.0.0.1":  # don't accept default-localhost IP
                server_ipaddress_str = ipAddrStr
                break
            logger.debug("Querying of host IP address returned " + ipAddrStr)
        except Exception as ex:
            logger.debug("Error querying host IP address: " + str(ex))
        if monotonic() > sTime + maxRetrySecs:
            ipAddrStr = "0.0.0.0"
            logger.warning("Unable to determine IP address for host machine")
            break
        gevent.sleep(1)
    try:
        hNameStr = socket.gethostname()
    except Exception as ex:
        logger.info("Error querying hostname: " + str(ex))
        hNameStr = "UNKNOWN"
    logger.info("Host machine is '{0}' at {1}".format(hNameStr, ipAddrStr))
    return ipAddrStr

def jump_to_node_bootloader():
    try:
        INTERFACE.jump_to_bootloader()
    except Exception:
        logger.error("Error executing jump to node bootloader")

def shutdown_button_thread_fn():
    try:
        logger.debug("Started shutdown-button-handler thread")
        idleCntr = 0
        while True:
            gevent.sleep(0.050)
            if not ShutdownButtonInputHandler.isEnabled():  # if button handler disabled
                break                                       #  then exit thread
            # poll button input and invoke callbacks
            bStatFlg = ShutdownButtonInputHandler.pollProcessInput(monotonic())
            # while background thread not started and button not pressed
            #  send periodic server-idle messages to node
            if (HEARTBEAT_THREAD is None) and BACKGROUND_THREADS_ENABLED and INTERFACE:
                idleCntr += 1
                if idleCntr >= 74:
                    if idleCntr >= 80:
                        idleCntr = 0    # show pattern on node LED via messages
                    if (not bStatFlg) and (idleCntr % 2 == 0):
                        INTERFACE.send_server_idle_message()
    except KeyboardInterrupt:
        logger.info("shutdown_button_thread_fn terminated by keyboard interrupt")
        raise
    except SystemExit:
        raise
    except Exception:
        logger.exception("Exception error in 'shutdown_button_thread_fn()'")
    logger.debug("Exited shutdown-button-handler thread")

def start_shutdown_button_thread():
    if ShutdownButtonInputHandler and not ShutdownButtonInputHandler.isEnabled():
        ShutdownButtonInputHandler.setEnabled(True)
        gevent.spawn(shutdown_button_thread_fn)

def stop_shutdown_button_thread():
    if ShutdownButtonInputHandler:
        ShutdownButtonInputHandler.setEnabled(False)

def shutdown_button_pressed():
    logger.debug("Detected shutdown button pressed")
    INTERFACE.send_shutdown_button_state(1)

def shutdown_button_released(longPressReachedFlag):
    logger.debug("Detected shutdown button released, longPressReachedFlag={}".\
                format(longPressReachedFlag))
    if not longPressReachedFlag:
        INTERFACE.send_shutdown_button_state(0)

def shutdown_button_long_press():
    logger.info("Detected shutdown button long press; performing shutdown now")
    on_shutdown_pi()

def _do_init_rh_interface():
    try:
        global INTERFACE
        rh_interface_name = os.environ.get('RH_INTERFACE', 'RH') + "Interface"
        try:
            logger.debug("Initializing interface module: " + rh_interface_name)
            interfaceModule = importlib.import_module(rh_interface_name)
            INTERFACE = interfaceModule.get_hardware_interface(config=Config, \
                            isS32BPillFlag=RHGPIO.isS32BPillBoard(), **hardwareHelpers)
            # if no nodes detected, system is RPi, not S32_BPill, and no serial port configured
            #  then check if problem is 'smbus2' or 'gevent' lib not installed
            if INTERFACE and ((not INTERFACE.nodes) or len(INTERFACE.nodes) <= 0) and \
                        RHUtils.isSysRaspberryPi() and (not RHGPIO.isS32BPillBoard()) and \
                        ((not Config.SERIAL_PORTS) or len(Config.SERIAL_PORTS) <= 0):
                try:
                    importlib.import_module('smbus2')
                    importlib.import_module('gevent')
                except ImportError:
                    logger.warning("Unable to import libraries for I2C nodes; try:  " +\
                                   "sudo pip install --upgrade --no-cache-dir -r requirements.txt")
                    set_ui_message(
                        'i2c',
                        __("Unable to import libraries for I2C nodes. Try: <code>sudo pip install --upgrade --no-cache-dir -r requirements.txt</code>"),
                        header='Warning',
                        subclass='no-library'
                        )
                RACE.num_nodes = 0
                INTERFACE.pass_record_callback = pass_record_callback
                INTERFACE.new_enter_or_exit_at_callback = new_enter_or_exit_at_callback
                INTERFACE.node_crossing_callback = node_crossing_callback
                return True
        except (ImportError, RuntimeError, IOError) as ex:
            logger.info('Unable to initialize nodes via ' + rh_interface_name + ':  ' + str(ex))
        if (not INTERFACE) or (not INTERFACE.nodes) or len(INTERFACE.nodes) <= 0:
            if (not Config.SERIAL_PORTS) or len(Config.SERIAL_PORTS) <= 0:
                interfaceModule = importlib.import_module('MockInterface')
                INTERFACE = interfaceModule.get_hardware_interface(config=Config, **hardwareHelpers)
                for node in INTERFACE.nodes:  # put mock nodes at latest API level
                    node.api_level = NODE_API_BEST
                set_ui_message(
                    'mock',
                    __("Server is using simulated (mock) nodes"),
                    header='Notice',
                    subclass='in-use'
                    )
            else:
                try:
                    importlib.import_module('serial')
                    if INTERFACE:
                        if not (getattr(INTERFACE, "get_info_node_obj") and INTERFACE.get_info_node_obj()):
                            logger.info("Unable to initialize serial node(s): {0}".format(Config.SERIAL_PORTS))
                            logger.info("If an S32_BPill board is connected, its processor may need to be flash-updated")
                            # enter serial port name so it's available for node firmware update
                            if getattr(INTERFACE, "set_mock_fwupd_serial_obj"):
                                INTERFACE.set_mock_fwupd_serial_obj(Config.SERIAL_PORTS[0])
                                set_ui_message('stm32', \
                                     __("Server is unable to communicate with node processor") + ". " + \
                                          __("If an S32_BPill board is connected, you may attempt to") + \
                                          " <a href=\"/updatenodes\">" + __("flash-update") + "</a> " + \
                                          __("its processor."), \
                                    header='Warning', subclass='no-comms')
                    else:
                        logger.info("Unable to initialize specified serial node(s): {0}".format(Config.SERIAL_PORTS))
                        return False  # unable to open serial port
                except ImportError:
                    logger.info("Unable to import library for serial node(s) - is 'pyserial' installed?")
                    return False

        RACE.num_nodes = len(INTERFACE.nodes)  # save number of nodes found
        # set callback functions invoked by interface module
        INTERFACE.pass_record_callback = pass_record_callback
        INTERFACE.new_enter_or_exit_at_callback = new_enter_or_exit_at_callback
        INTERFACE.node_crossing_callback = node_crossing_callback
        return True
    except:
        logger.exception("Error initializing RH interface")
        return False

def initialize_rh_interface():
    if not _do_init_rh_interface():
        return False
    if RACE.num_nodes == 0:
        logger.warning('*** WARNING: NO RECEIVER NODES FOUND ***')
        set_ui_message(
            'node',
            __("No receiver nodes found"),
            header='Warning',
            subclass='none'
            )
    return True

# Create and save server/node information
def buildServerInfo():
    global serverInfo
    global serverInfoItems
    try:
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
        node_api_level = 0
        serverInfo['node_api_match'] = True

        serverInfo['node_api_lowest'] = 0
        serverInfo['node_api_levels'] = [None]

        info_node = INTERFACE.get_info_node_obj()
        if info_node:
            if info_node.api_level:
                node_api_level = info_node.api_level
                serverInfo['node_api_lowest'] = node_api_level
                if len(INTERFACE.nodes):
                    serverInfo['node_api_levels'] = []
                    for node in INTERFACE.nodes:
                        serverInfo['node_api_levels'].append(node.api_level)
                        if node.api_level != node_api_level:
                            serverInfo['node_api_match'] = False
                        if node.api_level < serverInfo['node_api_lowest']:
                            serverInfo['node_api_lowest'] = node.api_level
                    # if multi-node and all api levels same then only include one entry
                    if serverInfo['node_api_match'] and INTERFACE.nodes[0].multi_node_index >= 0:
                        serverInfo['node_api_levels'] = serverInfo['node_api_levels'][0:1]
                else:
                    serverInfo['node_api_levels'] = [node_api_level]

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

        # Node firmware versions
        node_fw_version = None
        serverInfo['node_version_match'] = True
        serverInfo['node_fw_versions'] = [None]
        if info_node:
            if info_node.firmware_version_str:
                node_fw_version = info_node.firmware_version_str
                if len(INTERFACE.nodes):
                    serverInfo['node_fw_versions'] = []
                    for node in INTERFACE.nodes:
                        serverInfo['node_fw_versions'].append(\
                                node.firmware_version_str if node.firmware_version_str else "0")
                        if node.firmware_version_str != node_fw_version:
                            serverInfo['node_version_match'] = False
                    # if multi-node and all versions same then only include one entry
                    if serverInfo['node_version_match'] and INTERFACE.nodes[0].multi_node_index >= 0:
                        serverInfo['node_fw_versions'] = serverInfo['node_fw_versions'][0:1]
                else:
                    serverInfo['node_fw_versions'] = [node_fw_version]
        if node_fw_version:
            serverInfo['about_html'] += "<li>" + __("Node Version") + ": "
            if serverInfo['node_version_match']:
                serverInfo['about_html'] += str(node_fw_version)
            else:
                serverInfo['about_html'] += "[ "
                for idx, ver in enumerate(serverInfo['node_fw_versions']):
                    serverInfo['about_html'] += str(idx+1) + ":" + str(ver) + " "
                serverInfo['about_html'] += "]"
            serverInfo['about_html'] += "</li>"

        serverInfo['node_api_best'] = NODE_API_BEST
        if serverInfo['node_api_match'] is False or node_api_level < NODE_API_BEST:
            # Show Recommended API notice
            serverInfo['about_html'] += "<li><strong>" + __("Node Update Available") + ": " + str(NODE_API_BEST) + "</strong></li>"

        serverInfo['about_html'] += "</ul>"

        # create version of 'serverInfo' without 'about_html' entry
        serverInfoItems = serverInfo.copy()
        serverInfoItems.pop('about_html', None)
        serverInfoItems['prog_start_epoch'] = "{0:.0f}".format(PROGRAM_START_EPOCH_TIME)
        serverInfoItems['prog_start_time'] = str(datetime.utcfromtimestamp(PROGRAM_START_EPOCH_TIME/1000.0))

        return serverInfo

    except:
        logger.exception("Error in 'buildServerInfo()'")

# Log server/node information
def reportServerInfo():
    logger.debug("Server info:  " + json.dumps(serverInfoItems))
    if serverInfo['node_api_match'] is False:
        logger.info('** WARNING: Node API mismatch **')
        set_ui_message('node-match',
            __("Node versions do not match and may not function similarly"), header='Warning')
    if RACE.num_nodes > 0:
        if serverInfo['node_api_lowest'] < NODE_API_SUPPORTED:
            logger.info('** WARNING: Node firmware is out of date and may not function properly **')
            msgStr = __("Node firmware is out of date and may not function properly")
            if INTERFACE.get_fwupd_serial_name() != None:
                msgStr += ". " + __("If an S32_BPill board is connected, you should") + \
                          " <a href=\"/updatenodes\">" + __("flash-update") + "</a> " + \
                          __("its processor.")
            set_ui_message('node-obs', msgStr, header='Warning', subclass='api-not-supported')
        elif serverInfo['node_api_lowest'] < NODE_API_BEST:
            logger.info('** NOTICE: Node firmware update is available **')
            msgStr = __("Node firmware update is available")
            if INTERFACE.get_fwupd_serial_name() != None:
                msgStr += ". " + __("If an S32_BPill board is connected, you should") + \
                          " <a href=\"/updatenodes\">" + __("flash-update") + "</a> " + \
                          __("its processor.")
            set_ui_message('node-old', msgStr, header='Notice', subclass='api-low')
        elif serverInfo['node_api_lowest'] > NODE_API_BEST:
            logger.warning('** WARNING: Node firmware is newer than this server version supports **')
            set_ui_message('node-newer',
                __("Node firmware is newer than this server version and may not function properly"),
                header='Warning', subclass='api-high')

#
# Program Initialize
#

logger.info('Release: {0} / Server API: {1} / Latest Node API: {2}'.format(RELEASE_VERSION, SERVER_API, NODE_API_BEST))
logger.debug('Program started at {0:.0f}'.format(PROGRAM_START_EPOCH_TIME))
RHUtils.idAndLogSystemInfo()

if RHUtils.isVersionPython2():
    logger.warning("Python version is obsolete: " + RHUtils.getPythonVersionStr())
    set_ui_message('python',
        (__("Python version") + " (" + RHUtils.getPythonVersionStr() + ") " + \
         __("is obsolete and no longer supported; see") + \
         " <a href=\"docs?d=Software Setup.md#python\">Software Settings</a> " + \
         __("doc for upgrade instructions")),
        header='Warning', subclass='old-python')

determineHostAddress(2)  # attempt to determine IP address, but don't wait too long for it

if (not RHGPIO.isS32BPillBoard()) and Config.GENERAL['FORCE_S32_BPILL_FLAG']:
    RHGPIO.setS32BPillBoardFlag()
    logger.info("Set S32BPillBoardFlag in response to FORCE_S32_BPILL_FLAG in config")

logger.debug("isRPi={}, isRealGPIO={}, isS32BPill={}".format(RHUtils.isSysRaspberryPi(), \
                                        RHGPIO.isRealRPiGPIO(), RHGPIO.isS32BPillBoard()))
if RHUtils.isSysRaspberryPi() and not RHGPIO.isRealRPiGPIO():
    logger.warning("Unable to access real GPIO on Pi; try:  sudo pip install RPi.GPIO")
    set_ui_message(
        'gpio',
        __("Unable to access real GPIO on Pi. Try: <code>sudo pip install RPi.GPIO</code>"),
        header='Warning',
        subclass='no-access'
        )

# log results of module initializations
Config.logInitResultMessage()
Language.logInitResultMessage()

# check if current log file owned by 'root' and change owner to 'pi' user if so
if Current_log_path_name and RHUtils.checkSetFileOwnerPi(Current_log_path_name):
    logger.debug("Changed log file owner from 'root' to 'pi' (file: '{0}')".format(Current_log_path_name))
    RHUtils.checkSetFileOwnerPi(log.LOG_DIR_NAME)  # also make sure 'log' dir not owned by 'root'

logger.info("Using log file: {0}".format(Current_log_path_name))

if RHUtils.isSysRaspberryPi() and RHGPIO.isS32BPillBoard():
    try:
        if Config.GENERAL['SHUTDOWN_BUTTON_GPIOPIN']:
            logger.debug("Configuring shutdown-button handler, pin={}, delayMs={}".format(\
                         Config.GENERAL['SHUTDOWN_BUTTON_GPIOPIN'], \
                         Config.GENERAL['SHUTDOWN_BUTTON_DELAYMS']))
            ShutdownButtonInputHandler = ButtonInputHandler(
                            Config.GENERAL['SHUTDOWN_BUTTON_GPIOPIN'], logger, \
                            shutdown_button_pressed, shutdown_button_released, \
                            shutdown_button_long_press,
                            Config.GENERAL['SHUTDOWN_BUTTON_DELAYMS'], False)
            start_shutdown_button_thread()
    except Exception:
        logger.exception("Error setting up shutdown-button handler")

    logger.debug("Resetting S32_BPill processor")
    s32logger = logging.getLogger("stm32loader")
    stm32loader.set_console_output_fn(s32logger.info)
    stm32loader.reset_to_run()
    stm32loader.set_console_output_fn(None)

hardwareHelpers = {}
for helper in search_modules(suffix='helper'):
    try:
        hardwareHelpers[helper.__name__] = helper.create(Config)
    except Exception as ex:
        logger.warning("Unable to create hardware helper '{0}':  {1}".format(helper.__name__, ex))

resultFlag = initialize_rh_interface()
if not resultFlag:
    log.wait_for_queue_empty()
    sys.exit(1)

if len(sys.argv) > 0 and CMDARG_JUMP_TO_BL_STR in sys.argv:
    stop_background_threads()
    jump_to_node_bootloader()
    if CMDARG_FLASH_BPILL_STR in sys.argv:
        bootJumpArgIdx = sys.argv.index(CMDARG_FLASH_BPILL_STR) + 1
        bootJumpPortStr = Config.SERIAL_PORTS[0] if Config.SERIAL_PORTS and \
                                            len(Config.SERIAL_PORTS) > 0 else None
        bootJumpSrcStr = sys.argv[bootJumpArgIdx] if bootJumpArgIdx < len(sys.argv) else None
        if bootJumpSrcStr and bootJumpSrcStr.startswith("--"):  # use next arg as src file (optional)
            bootJumpSrcStr = None                       #  unless arg is switch param
        bootJumpSuccessFlag = stm32loader.flash_file_to_stm32(bootJumpPortStr, bootJumpSrcStr)
        sys.exit(0 if bootJumpSuccessFlag else 1)
    sys.exit(0)

CLUSTER = ClusterNodeSet(Language, Events)
hasMirrors = False
try:
    for sec_idx, secondary_info in enumerate(Config.GENERAL['SECONDARIES']):
        if isinstance(secondary_info, string_types):
            secondary_info = {'address': secondary_info, 'mode': SecondaryNode.SPLIT_MODE}
        if 'address' not in secondary_info:
            raise RuntimeError("Secondary 'address' item not specified")
        # substitute asterisks in given address with values from host IP address
        secondary_info['address'] = RHUtils.substituteAddrWildcards(determineHostAddress, \
                                                                secondary_info['address'])
        if 'timeout' not in secondary_info:
            secondary_info['timeout'] = Config.GENERAL['SECONDARY_TIMEOUT']
        if 'mode' in secondary_info and str(secondary_info['mode']) == SecondaryNode.MIRROR_MODE:
            hasMirrors = True
        elif hasMirrors:
            logger.warning('** Mirror secondaries must be last - ignoring remaining secondary config **')
            set_ui_message(
                'secondary',
                __("Mirror secondaries must be last; ignoring part of secondary configuration"),
                header='Notice',
                subclass='mirror'
                )
            break
        secondary = SecondaryNode(sec_idx, secondary_info, RACE, RHData, getCurrentProfile, \
                          emit_split_pass_info, monotonic_to_epoch_millis, \
                          emit_cluster_connect_change, RELEASE_VERSION)
        CLUSTER.addSecondary(secondary)
except:
    logger.exception("Error adding secondary to cluster")
    set_ui_message(
        'secondary',
        __('Secondary configuration is invalid.'),
        header='Error',
        subclass='error'
        )

if CLUSTER and CLUSTER.hasRecEventsSecondaries():
    CLUSTER.init_repeater()

if RACE.num_nodes > 0:
    logger.info('Number of nodes found: {0}'.format(RACE.num_nodes))
    # if I2C nodes then only report comm errors if > 1.0%
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
    RHData.primeCache() # Ready the Options cache

# check if DB file owned by 'root' and change owner to 'pi' user if so
if RHUtils.checkSetFileOwnerPi(DB_FILE_NAME):
    logger.debug("Changed DB-file owner from 'root' to 'pi' (file: '{0}')".format(DB_FILE_NAME))

# check if directories owned by 'root' and change owner to 'pi' user if so
if RHUtils.checkSetFileOwnerPi(DB_BKP_DIR_NAME):
    logger.info("Changed '{0}' dir owner from 'root' to 'pi'".format(DB_BKP_DIR_NAME))
if RHUtils.checkSetFileOwnerPi(log.LOGZIP_DIR_NAME):
    logger.info("Changed '{0}' dir owner from 'root' to 'pi'".format(log.LOGZIP_DIR_NAME))

# collect server info for About panel, etc
buildServerInfo()
reportServerInfo()

# Do data consistency checks
if not db_inited_flag:
    try:
        RHData.primeCache() # Ready the Options cache

        if not RHData.check_integrity():
            RHData.recover_database(DB_FILE_NAME, startup=True)
            clean_results_cache()

    except Exception as ex:
        logger.warning('Clearing all data after recovery failure:  ' + str(ex))
        db_reset()

# Initialize internal state with database
# DB session commit needed to prevent 'application context' errors
try:
    init_race_state()
except Exception:
    logger.exception("Exception in 'init_race_state()'")
    log.wait_for_queue_empty()
    sys.exit(1)

# internal secondary race format for LiveTime (needs to be created after initial DB setup)
SECONDARY_RACE_FORMAT = RHRaceFormat(name=__("Secondary"),
                         race_mode=1,
                         race_time_sec=0,
                         start_delay_min=0,
                         start_delay_max=0,
                         staging_tones=0,
                         number_laps_win=0,
                         win_condition=WinCondition.NONE,
                         team_racing_mode=False,
                         start_behavior=0)

# Import IMDTabler
if os.path.exists(IMDTABLER_JAR_NAME):  # if 'IMDTabler.jar' is available
    try:
        java_ver = subprocess.check_output('java -version', stderr=subprocess.STDOUT, shell=True).decode("utf-8")
        logger.debug('Found installed: ' + java_ver.split('\n')[0].strip())
    except:
        java_ver = None
        logger.info('Unable to find java; for IMDTabler functionality try:')
        logger.info('sudo apt install default-jdk-headless')
    if java_ver:
        try:
            chk_imdtabler_ver = subprocess.check_output( \
                        'java -jar ' + IMDTABLER_JAR_NAME + ' -v', \
                        stderr=subprocess.STDOUT, shell=True).decode("utf-8").rstrip()
            Use_imdtabler_jar_flag = True  # indicate IMDTabler.jar available
            logger.debug('Found installed: ' + chk_imdtabler_ver)
        except Exception:
            logger.exception('Error checking IMDTabler:  ')
else:
    logger.info('IMDTabler lib not found at: ' + IMDTABLER_JAR_NAME)

# Create LED object with appropriate configuration
strip = None
if Config.LED['LED_COUNT'] > 0:
    led_type = os.environ.get('RH_LEDS', 'ws281x')
    # note: any calls to 'RHData.get_option()' need to happen after the DB initialization,
    #       otherwise it causes problems when run with no existing DB file
    led_brightness = RHData.get_optionInt("ledBrightness")
    try:
        ledModule = importlib.import_module(led_type + '_leds')
        strip = ledModule.get_pixel_interface(config=Config.LED, brightness=led_brightness)
    except ImportError:
        # No hardware LED handler, the OpenCV emulation
        try:
            ledModule = importlib.import_module('cv2_leds')
            strip = ledModule.get_pixel_interface(config=Config.LED, brightness=led_brightness)
        except ImportError:
            # No OpenCV emulation, try console output
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
    try:
        strip.begin()
        led_manager = LEDEventManager(Events, strip, RHData, RACE, Language, INTERFACE)
        led_effects = Plugins(prefix='led_handler')
        led_effects.discover()
        for led_effect in led_effects:
            led_manager.registerEffect(led_effect)
        init_LED_effects()
    except:
        logger.exception("Error initializing LED support")
        led_manager = NoLEDManager()
elif CLUSTER and CLUSTER.hasRecEventsSecondaries():
    led_manager = ClusterLEDManager()
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

# data exporters
export_manager = DataExportManager(RHData, PageCache, Language)

gevent.spawn(clock_check_thread_function)  # start thread to monitor system clock

# register endpoints
import json_endpoints

APP.register_blueprint(json_endpoints.createBlueprint(RHData, Results, RACE, serverInfo, getCurrentProfile))

def start(port_val = Config.GENERAL['HTTP_PORT']):
    if not RHData.get_option("secret_key"):
        RHData.set_option("secret_key", ''.join(random.choice(string.ascii_letters) for i in range(50)))

    APP.config['SECRET_KEY'] = RHData.get_option("secret_key")
    logger.info("Running http server at port " + str(port_val))
    init_interface_state(startup=True)
    Events.trigger(Evt.STARTUP, {
        'color': ColorVal.ORANGE,
        'message': 'RotorHazard ' + RELEASE_VERSION
        })

    try:
        # the following fn does not return until the server is shutting down
        SOCKET_IO.run(APP, host='0.0.0.0', port=port_val, debug=True, use_reloader=False)
        logger.info("Server is shutting down")
    except KeyboardInterrupt:
        logger.info("Server terminated by keyboard interrupt")
    except SystemExit:
        logger.info("Server terminated by system exit")
    except Exception:
        logger.exception("Server exception")

    Events.trigger(Evt.SHUTDOWN, {
        'color': ColorVal.RED
        })
    rep_str = INTERFACE.get_intf_error_report_str(True)
    if rep_str:
        logger.log((logging.INFO if INTERFACE.get_intf_total_error_count() else logging.DEBUG), rep_str)
    stop_background_threads()
    log.wait_for_queue_empty()
    gevent.sleep(2)  # allow system shutdown command to run before program exit
    log.close_logging()

# Start HTTP server
if __name__ == '__main__':
    start()
