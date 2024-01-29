'''RotorHazard server script'''
RELEASE_VERSION = "4.1.0-dev.5" # Public release version code
SERVER_API = 43 # Server API version
NODE_API_SUPPORTED = 18 # Minimum supported node version
NODE_API_BEST = 35 # Most recent node API
JSON_API = 3 # JSON API version
MIN_PYTHON_MAJOR_VERSION = 3 # minimum python version (3.8)
MIN_PYTHON_MINOR_VERSION = 8

# This must be the first import for the time being. It is
# necessary to set up logging *before* anything else
# because there is a lot of code run through imports, and
# we would miss messages otherwise.
import logging
import log
from datetime import datetime
from time import monotonic
import RHTimeFns

log.early_stage_setup()
logger = logging.getLogger(__name__)

EPOCH_START = RHTimeFns.getEpochStartTime()

_prog_start_epoch1 = (RHTimeFns.getUtcDateTimeNow() - EPOCH_START).total_seconds()

# program start time (in time.monotonic seconds)
_program_start_mtonic = monotonic()

# do average of before and after to exact timing match between _program_start_epoch_time and _program_start_mtonic
_prog_start_epoch2 = (RHTimeFns.getUtcDateTimeNow() - EPOCH_START).total_seconds()

# program-start time, in milliseconds since 1970-01-01
_program_start_epoch_time = int((_prog_start_epoch1 + _prog_start_epoch2) * 500.0 + 0.5)   # *1000/2.0

logger.info('RotorHazard v{0}'.format(RELEASE_VERSION))

# Normal importing resumes here
import RHUtils  # need to import this early to get RH_GPIO initialized before gevent, etc
from RHUtils import catchLogExceptionsWrapper

import gevent.monkey
gevent.monkey.patch_all()

import io
import os
import sys
import base64
import subprocess
import importlib
# import copy
from functools import wraps

from flask import Flask, send_file, request, Response, templating, redirect, abort, copy_current_request_context
from flask_socketio import SocketIO, emit

import socket
import random
import string
import json

import Config

RHUtils.checkPythonVersion(MIN_PYTHON_MAJOR_VERSION, MIN_PYTHON_MINOR_VERSION)

import Database
import Results
import Language
import json_endpoints
import EventActions
import RaceContext
import RHData
import RHUI
import calibration
import heat_automation
import RHAPI
from ClusterNodeSet import SecondaryNode, ClusterNodeSet
import PageCache
from util.ButtonInputHandler import ButtonInputHandler
import util.stm32loader as stm32loader

# Events manager
from eventmanager import Evt, EventManager

# LED imports
from led_event_manager import LEDEventManager, NoLEDManager, ClusterLEDManager, LEDEvent, Color, ColorVal, ColorPattern

sys.path.append('../interface')
sys.path.append('/home/pi/RotorHazard/src/interface')  # Needed to run on startup

from Plugins import search_modules  #pylint: disable=import-error
from Sensors import Sensors  #pylint: disable=import-error
import RHRace
from RHRace import WinCondition, RaceStatus
from data_export import DataExportManager
from data_import import DataImportManager
from VRxControl import VRxControlManager
from HeatGenerator import HeatGeneratorManager

# Create shared context
RaceContext = RaceContext.RaceContext()
RHAPI = RHAPI.RHAPI(RaceContext)

RaceContext.serverstate.program_start_epoch_time = _program_start_epoch_time
RaceContext.serverstate.program_start_mtonic = _program_start_mtonic
RaceContext.serverstate.mtonic_to_epoch_millis_offset = RaceContext.serverstate.program_start_epoch_time - \
                                                        1000.0*RaceContext.serverstate.program_start_mtonic

Events = EventManager(RHAPI)
RaceContext.events = Events
EventActionsObj = None

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
CMDARG_VIEW_DB_STR = '--viewdb'          # load and view given database file
CMDARG_LAUNCH_B_STR = '--launchb'        # launch browser on local computer

if __name__ == '__main__' and len(sys.argv) > 1:
    if CMDARG_VERSION_LONG_STR in sys.argv or CMDARG_VERSION_SHORT_STR in sys.argv:
        sys.exit(0)
    if CMDARG_ZIP_LOGS_STR in sys.argv:
        log.create_log_files_zip(logger, Config.CONFIG_FILE_NAME, DB_FILE_NAME)
        sys.exit(0)
    if CMDARG_VIEW_DB_STR in sys.argv:
        viewdbArgIdx = sys.argv.index(CMDARG_VIEW_DB_STR) + 1
        if viewdbArgIdx < len(sys.argv):
            if not os.path.exists(sys.argv[viewdbArgIdx]):
                print("Unable to find given DB file: {0}".format(sys.argv[viewdbArgIdx]))
                sys.exit(1)
        else:
            print("Usage: python server.py {0} dbFileName.db [pagename] [browsercmd]".format(CMDARG_VIEW_DB_STR))
            sys.exit(1)
    elif CMDARG_JUMP_TO_BL_STR not in sys.argv:  # handle jump-to-bootloader argument later
        if CMDARG_FLASH_BPILL_STR in sys.argv:
            flashPillArgIdx = sys.argv.index(CMDARG_FLASH_BPILL_STR) + 1
            flashPillPortStr = Config.SERIAL_PORTS[0] if Config.SERIAL_PORTS and \
                                                len(Config.SERIAL_PORTS) > 0 else None
            flashPillSrcStr = sys.argv[flashPillArgIdx] if flashPillArgIdx < len(sys.argv) else None
            if flashPillSrcStr and flashPillSrcStr.startswith("--"):  # use next arg as src file (optional)
                flashPillSrcStr = None                       #  unless arg is switch param
            flashPillSuccessFlag = stm32loader.flash_file_to_stm32(flashPillPortStr, flashPillSrcStr)
            sys.exit(0 if flashPillSuccessFlag else 1)
        elif CMDARG_LAUNCH_B_STR not in sys.argv:
            print("Unrecognized command-line argument(s): {0}".format(sys.argv[1:]))
            sys.exit(1)

BASEDIR = os.getcwd()
APP.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASEDIR, DB_FILE_NAME)
APP.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
Database.DB.init_app(APP)
Database.DB.app = APP

# start SocketIO service
SOCKET_IO = SocketIO(APP, async_mode='gevent', cors_allowed_origins=Config.GENERAL['CORS_ALLOWED_HOSTS'], max_http_buffer_size=5e7)

# this is the moment where we can forward log-messages to the frontend, and
# thus set up logging for good.
Current_log_path_name = log.later_stage_setup(Config.LOGGING, SOCKET_IO)

RaceContext.sensors = Sensors()
RaceContext.cluster = None
Use_imdtabler_jar_flag = False  # set True if IMDTabler.jar is available
server_ipaddress_str = None
ShutdownButtonInputHandler = None
Server_secondary_mode = None

RaceContext.rhdata = RHData.RHData(Database, Events, RaceContext, SERVER_API, DB_FILE_NAME, DB_BKP_DIR_NAME) # Primary race data storage

RaceContext.pagecache = PageCache.PageCache(RaceContext, Events) # For storing page cache

RaceContext.language = Language.Language(RaceContext.rhdata) # initialize language
__ = RaceContext.language.__ # Shortcut to translation function
Database.__ = __ # Pass language to Database module

RaceContext.race = RHRace.RHRace(RaceContext) # Current race variables

RaceContext.rhui = RHUI.RHUI(APP, SOCKET_IO, RaceContext, Events) # User Interface Manager
RaceContext.rhui.__ = RaceContext.language.__ # Pass translation shortcut

RaceContext.calibration = calibration.Calibration(RaceContext)
RaceContext.heatautomator = heat_automation.HeatAutomator(RaceContext)

ui_server_messages = {}
def set_ui_message(mainclass, message, header=None, subclass=None):
    item = {}
    item['message'] = message
    if header:
        item['header'] = __(header)
    if subclass:
        item['subclass'] = subclass
    ui_server_messages[mainclass] = item

# Wrapper to be used as a decorator on callback functions that do database calls,
#  so their exception details are sent to the log file (instead of 'stderr')
#  and the database session is closed on thread exit (prevents DB-file handles left open).
def catchLogExcDBCloseWrapper(func):
    def wrapper(*args, **kwargs):
        try:
            retVal = func(*args, **kwargs)
            RaceContext.rhdata.close()
            return retVal
        except:
            logger.exception("Exception via catchLogExcDBCloseWrapper")
            try:
                RaceContext.rhdata.close()
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
            curTypStr = RaceContext.interface.nodes[0].firmware_proctype_str if len(RaceContext.interface.nodes) else None
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
            return RHUtils.findPrefixedSubstring(dataStr, RaceContext.interface.FW_PROCTYPE_PREFIXSTR, \
                                                 RaceContext.interface.FW_TEXT_BLOCK_SIZE)
    except Exception as ex:
        logger.debug("Error processing file '{}' in 'getFwfileProctypeStr()': {}".format(fileStr, ex))
    return None


#
# Authentication
#

def check_auth(username, password):
    '''Check if a username password combination is valid.'''
    return username == Config.GENERAL.get('ADMIN_USERNAME') and password == Config.GENERAL.get('ADMIN_PASSWORD')

def authenticate():
    '''Sends a 401 response that enables basic auth.'''
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    if Config.GENERAL.get('ADMIN_USERNAME') != "" or \
                            Config.GENERAL.get('ADMIN_PASSWORD') != "":
        @wraps(f)
        def decorated_auth(*args, **kwargs):
            auth = request.authorization
            if not auth or not check_auth(auth.username, auth.password):
                return authenticate()
            return f(*args, **kwargs)
        return decorated_auth
    # allow open access if both ADMIN fields set to empty string:
    @wraps(f)
    def decorated_noauth(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_noauth

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
    return render_template('home.html', serverInfo=RaceContext.serverstate.template_info_dict,
                           getOption=RaceContext.rhdata.get_option, __=__, Debug=Config.GENERAL['DEBUG'])

@APP.route('/event')
def render_event():
    '''Route to heat summary page.'''
    return render_template('event.html', num_nodes=RaceContext.race.num_nodes, serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__)

@APP.route('/results')
def render_results():
    '''Route to round summary page.'''
    return render_template('results.html', serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__, Debug=Config.GENERAL['DEBUG'])

@APP.route('/run')
@requires_auth
def render_run():
    '''Route to race management page.'''
    frequencies = [node.frequency for node in RaceContext.interface.nodes]
    nodes = []
    for idx, freq in enumerate(frequencies):
        if freq:
            nodes.append({
                'freq': freq,
                'index': idx
            })

    return render_template('run.html', serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__,
        led_enabled=(RaceContext.led_manager.isEnabled() or (RaceContext.cluster and RaceContext.cluster.hasRecEventsSecondaries())),
        vrx_enabled=RaceContext.vrx_manager.isEnabled(),
        num_nodes=RaceContext.race.num_nodes,
        nodes=nodes,
        cluster_has_secondaries=(RaceContext.cluster and RaceContext.cluster.hasSecondaries()))

@APP.route('/current')
def render_current():
    '''Route to race management page.'''
    frequencies = [node.frequency for node in RaceContext.interface.nodes]
    nodes = []
    for idx, freq in enumerate(frequencies):
        if freq:
            nodes.append({
                'freq': freq,
                'index': idx
            })

    return render_template('current.html', serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__,
        num_nodes=RaceContext.race.num_nodes,
        nodes=nodes,
        cluster_has_secondaries=(RaceContext.cluster and RaceContext.cluster.hasSecondaries()))

@APP.route('/marshal')
@requires_auth
def render_marshal():
    '''Route to race management page.'''
    return render_template('marshal.html', serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__,
        num_nodes=RaceContext.race.num_nodes)

@APP.route('/format')
@requires_auth
def render_format():
    '''Route to settings page.'''
    return render_template('format.html', serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__,
        num_nodes=RaceContext.race.num_nodes, Debug=Config.GENERAL['DEBUG'])

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

    return render_template('settings.html', serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__,
                           led_enabled=(RaceContext.led_manager.isEnabled() or (RaceContext.cluster and RaceContext.cluster.hasRecEventsSecondaries())),
                           led_events_enabled=RaceContext.led_manager.isEnabled(),
                           vrx_enabled=RaceContext.vrx_manager.isEnabled(),
                           num_nodes=RaceContext.race.num_nodes,
                           server_messages=server_messages_formatted,
                           cluster_has_secondaries=(RaceContext.cluster and RaceContext.cluster.hasSecondaries()),
                           node_fw_updatable=(RaceContext.interface.get_fwupd_serial_name()!=None),
                           is_raspberry_pi=RHUtils.is_sys_raspberry_pi(),
                           Debug=Config.GENERAL['DEBUG'])

@APP.route('/streams')
def render_stream():
    '''Route to stream index.'''
    return render_template('streams.html', serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__,
        num_nodes=RaceContext.race.num_nodes)

@APP.route('/stream/results')
def render_stream_results():
    '''Route to current race leaderboard stream.'''
    return render_template('streamresults.html', serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__,
        num_nodes=RaceContext.race.num_nodes)

@APP.route('/stream/node/<int:node_id>')
def render_stream_node(node_id):
    '''Route to single node overlay for streaming.'''
    use_inactive_nodes = 'true' if request.args.get('use_inactive_nodes') else 'false'
    return render_template('streamnode.html', serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__,
        node_id=node_id-1, use_inactive_nodes=use_inactive_nodes
    )

@APP.route('/stream/class/<int:class_id>')
def render_stream_class(class_id):
    '''Route to class leaderboard display for streaming.'''
    return render_template('streamclass.html', serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__,
        class_id=class_id
    )

@APP.route('/stream/heat/<int:heat_id>')
def render_stream_heat(heat_id):
    '''Route to heat display for streaming.'''
    return render_template('streamheat.html', serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__,
        num_nodes=RaceContext.race.num_nodes,
        heat_id=heat_id
    )

@APP.route('/scanner')
@requires_auth
def render_scanner():
    '''Route to scanner page.'''

    return render_template('scanner.html', serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__,
        num_nodes=RaceContext.race.num_nodes)

@APP.route('/decoder')
@requires_auth
def render_decoder():
    '''Route to race management page.'''
    return render_template('decoder.html', serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__,
        num_nodes=RaceContext.race.num_nodes)

@APP.route('/imdtabler')
def render_imdtabler():
    '''Route to IMDTabler page.'''
    return render_template('imdtabler.html', serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__)

@APP.route('/updatenodes')
@requires_auth
def render_updatenodes():
    '''Route to update nodes page.'''
    return render_template('updatenodes.html', serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__, \
                           fw_src_str=getDefNodeFwUpdateUrl())

# Debug Routes

@APP.route('/hardwarelog')
@requires_auth
def render_hardwarelog():
    '''Route to hardware log page.'''
    return render_template('hardwarelog.html', serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__)

@APP.route('/database')
@requires_auth
def render_database():
    '''Route to database page.'''
    return render_template('database.html', serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__,
        pilots=RaceContext.rhdata.get_pilots(),
        heats=RaceContext.rhdata.get_heats(),
        heatnodes=RaceContext.rhdata.get_heatNodes(),
        race_class=RaceContext.rhdata.get_raceClasses(),
        savedraceMeta=RaceContext.rhdata.get_savedRaceMetas(),
        savedraceLap=RaceContext.rhdata.get_savedRaceLaps(),
        profiles=RaceContext.rhdata.get_profiles(),
        race_format=RaceContext.rhdata.get_raceFormats(),
        globalSettings=RaceContext.rhdata.get_options())

@APP.route('/vrxstatus')
@requires_auth
def render_vrxstatus():
    '''Route to VRx status debug page.'''
    return render_template('vrxstatus.html', serverInfo=RaceContext.serverstate.template_info_dict, getOption=RaceContext.rhdata.get_option, __=__)

# Documentation Viewer

@APP.route('/docs')
def render_viewDocs():
    '''Route to doc viewer.'''

    folderBase = '../../doc/'

    try:
        docfile = request.args.get('d')

        docfile = docfile.replace('../', '')

        docPath = folderBase + docfile

        language = RaceContext.rhdata.get_option("currentLanguage")
        if language:
            translated_path = folderBase + language + '/' + docfile
            if os.path.isfile(translated_path):
                docPath = translated_path

        with io.open(docPath, 'r', encoding="utf-8") as f:
            doc = f.read()

        return templating.render_template('viewdocs.html',
            serverInfo=RaceContext.serverstate.template_info_dict,
            getOption=RaceContext.rhdata.get_option,
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

    imgfile = imgfile.replace('../', '')

    imgPath = folderBase + folderImg + imgfile

    language = RaceContext.rhdata.get_option("currentLanguage")
    if language:
        translated_path = folderBase + language + '/' + folderImg + imgfile
        if os.path.isfile(translated_path):
            imgPath = translated_path

    if os.path.isfile(imgPath):
        return send_file(imgPath)
    else:
        abort(404)

# Redirect routes (Previous versions/Delta 5)
@APP.route('/race')
def redirect_race():
    return redirect("/run", code=301)

@APP.route('/heats')
def redirect_heats():
    return redirect("/event", code=301)

#
# Background threads
#

def start_background_threads(forceFlag=False):
    global BACKGROUND_THREADS_ENABLED
    if BACKGROUND_THREADS_ENABLED or forceFlag:
        BACKGROUND_THREADS_ENABLED = True
        RaceContext.interface.start()
        global HEARTBEAT_THREAD
        if HEARTBEAT_THREAD is None:
            HEARTBEAT_THREAD = gevent.spawn(heartbeat_thread_function)
            logger.debug('Heartbeat thread started')
        start_shutdown_button_thread()

def stop_background_threads():
    try:
        stop_shutdown_button_thread()
        if RaceContext.cluster:
            RaceContext.cluster.shutdown()
        RaceContext.led_manager.clear()  # stop any LED effect in progress
        global BACKGROUND_THREADS_ENABLED
        BACKGROUND_THREADS_ENABLED = False
        global HEARTBEAT_THREAD
        if HEARTBEAT_THREAD:
            logger.info('Stopping heartbeat thread')
            HEARTBEAT_THREAD.kill(block=True, timeout=0.5)
            HEARTBEAT_THREAD = None
        RaceContext.interface.stop()
    except:
        logger.exception("Error stopping background threads")

#
# Socket IO Events
#

@SOCKET_IO.on('connect')
@catchLogExceptionsWrapper
def connect_handler(auth):
    '''Starts the interface and a heartbeat thread for rssi.'''
    logger.debug('Client connected')
    start_background_threads()
    #
    @catchLogExceptionsWrapper
    @copy_current_request_context
    def finish_connect_handler():
        # push initial data
        RaceContext.rhui.emit_frontend_load(nobroadcast=True)
    # pause and spawn to make sure connection to browser is established
    gevent.spawn_later(0.050, finish_connect_handler)

@SOCKET_IO.on('disconnect')
def disconnect_handler():
    '''Emit disconnect event.'''
    logger.debug('Client disconnected')

# Cluster events

@SOCKET_IO.on('join_cluster')
@catchLogExceptionsWrapper
def on_join_cluster():
    RaceContext.race.format = RaceContext.serverstate.secondary_race_format
    RaceContext.rhui.emit_current_laps()
    RaceContext.rhui.emit_race_status()
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
            if prev_mode is None and len(RaceContext.rhdata.get_savedRaceMetas()) > 0:
                logger.info("Making database autoBkp and clearing races on split timer")
                RaceContext.rhdata.backup_db_file(True, "autoBkp_")
                RaceContext.rhdata.clear_race_data()
                RaceContext.race.reset_current_laps()
                RaceContext.rhui.emit_current_laps()
                RaceContext.rhui.emit_result_data()
                RaceContext.rhdata.delete_old_db_autoBkp_files(Config.GENERAL['DB_AUTOBKP_NUM_KEEP'], \
                                                   "autoBkp_", "DB_AUTOBKP_NUM_KEEP")
        except:
            logger.exception("Error making db-autoBkp / clearing races on split timer")
        RaceContext.race.format = RaceContext.serverstate.secondary_race_format
        RaceContext.rhui.emit_current_laps()
        RaceContext.rhui.emit_race_status()
    Events.trigger(Evt.CLUSTER_JOIN, {
                'message': __('Joined cluster')
                })
    RaceContext.cluster.emit_join_cluster_response(SOCKET_IO, RaceContext.serverstate.info_dict)

@SOCKET_IO.on('check_secondary_query')
@catchLogExceptionsWrapper
def on_check_secondary_query(_data):
    ''' Check-query received from primary; return response. '''
    payload = {
        'timestamp': RaceContext.serverstate.monotonic_to_epoch_millis(monotonic())
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
            RaceContext.race.race_status = RaceStatus.STAGING
            RaceContext.race.results = None
            RaceContext.race.external_flag = True
            if 'race_node_colors' in evtArgs and isinstance(evtArgs['race_node_colors'], list):
                RaceContext.race.seat_colors = evtArgs['race_node_colors']
            else:
                RaceContext.race.updateSeatColors(mode_override=0)
        elif evtName == Evt.RACE_START:
            RaceContext.race.race_status = RaceStatus.RACING
        elif evtName == Evt.RACE_STOP:
            RaceContext.race.race_status = RaceStatus.DONE
        elif evtName == Evt.LAPS_CLEAR:
            RaceContext.race.race_status = RaceStatus.READY
        elif evtName == Evt.RACE_LAP_RECORDED:
            RaceContext.race.results = evtArgs['results']

    evtArgs.pop('RACE', None) # remove race if exists

    if evtName not in [Evt.STARTUP, Evt.LED_SET_MANUAL]:
        Events.trigger(evtName, evtArgs)
    # special handling for LED Control via primary timer
    elif 'effect' in evtArgs and RaceContext.led_manager.isEnabled():
        RaceContext.led_manager.setEventEffect(Evt.LED_MANUAL, evtArgs['effect'])

@SOCKET_IO.on('cluster_message_ack')
@catchLogExceptionsWrapper
def on_cluster_message_ack(data):
    ''' Received message acknowledgement from primary. '''
    messageType = str(data.get('messageType')) if data else None
    messagePayload = data.get('messagePayload') if data else None
    RaceContext.cluster.emit_cluster_ack_to_primary(messageType, messagePayload)

@SOCKET_IO.on('dispatch_event')
@catchLogExceptionsWrapper
def dispatch_event(evtArgs):
    '''Dispatch generic event.'''
    Events.trigger(Evt.UI_DISPATCH, evtArgs)

@SOCKET_IO.on('load_data')
@catchLogExceptionsWrapper
def on_load_data(data):
    '''Allow pages to load needed data'''
    load_types = data['load_types']
    for load_type in load_types:
        if isinstance(load_type, dict):
            if load_type['type'] == 'ui':
                RaceContext.rhui.emit_ui(load_type['value'], nobroadcast=True)
        elif load_type == 'node_data':
            RaceContext.rhui.emit_node_data(nobroadcast=True)
        elif load_type == 'environmental_data':
            RaceContext.rhui.emit_environmental_data(nobroadcast=True)
        elif load_type == 'frequency_data':
            RaceContext.rhui.emit_frequency_data(nobroadcast=True)
            if Use_imdtabler_jar_flag:
                heartbeat_thread_function.imdtabler_flag = True
        elif load_type == 'heat_data':
            RaceContext.rhui.emit_heat_data(nobroadcast=True)
        elif load_type == 'class_data':
            RaceContext.rhui.emit_class_data(nobroadcast=True)
        elif load_type == 'format_data':
            RaceContext.rhui.emit_format_data(nobroadcast=True)
        elif load_type == 'pilot_data':
            RaceContext.rhui.emit_pilot_data(nobroadcast=True)
        elif load_type == 'result_data':
            RaceContext.rhui.emit_result_data(nobroadcast=True)
        elif load_type == 'node_tuning':
            RaceContext.rhui.emit_node_tuning(nobroadcast=True)
        elif load_type == 'enter_and_exit_at_levels':
            RaceContext.rhui.emit_enter_and_exit_at_levels(nobroadcast=True)
        elif load_type == 'start_thresh_lower_amount':
            RaceContext.rhui.emit_start_thresh_lower_amount(nobroadcast=True)
        elif load_type == 'start_thresh_lower_duration':
            RaceContext.rhui.emit_start_thresh_lower_duration(nobroadcast=True)
        elif load_type == 'min_lap':
            RaceContext.rhui.emit_min_lap(nobroadcast=True)
        elif load_type == 'action_setup':
            RaceContext.rhui.emit_action_setup(EventActionsObj, nobroadcast=True)
        elif load_type == 'event_actions':
            RaceContext.rhui.emit_event_actions(nobroadcast=True)
        elif load_type == 'leaderboard':
            RaceContext.rhui.emit_current_leaderboard(nobroadcast=True)
        elif load_type == 'current_laps':
            RaceContext.rhui.emit_current_laps(nobroadcast=True)
        elif load_type == 'race_status':
            RaceContext.rhui.emit_race_status(nobroadcast=True)
        elif load_type == 'current_heat':
            RaceContext.rhui.emit_current_heat(nobroadcast=True)
        elif load_type == 'race_list':
            RaceContext.rhui.emit_race_list(nobroadcast=True)
        elif load_type == 'language':
            RaceContext.rhui.emit_language(nobroadcast=True)
        elif load_type == 'all_languages':
            RaceContext.rhui.emit_all_languages(nobroadcast=True)
        elif load_type == 'led_effect_setup':
            emit_led_effect_setup()
        elif load_type == 'led_effects':
            emit_led_effects()
        elif load_type == 'callouts':
            RaceContext.rhui.emit_callouts()
        elif load_type == 'imdtabler_page':
            RaceContext.rhui.emit_imdtabler_page(IMDTABLER_JAR_NAME, Use_imdtabler_jar_flag, nobroadcast=True)
        elif load_type == 'vrx_list':
            RaceContext.rhui.emit_vrx_list(nobroadcast=True)
        elif load_type == 'backups_list':
            on_list_backups()
        elif load_type == 'exporter_list':
            RaceContext.rhui.emit_exporter_list()
        elif load_type == 'importer_list':
            RaceContext.rhui.emit_importer_list()
        elif load_type == 'heatgenerator_list':
            RaceContext.rhui.emit_heatgenerator_list()
        elif load_type == 'raceclass_rank_method_list':
            RaceContext.rhui.emit_raceclass_rank_method_list()
        elif load_type == 'race_points_method_list':
            RaceContext.rhui.emit_race_points_method_list()
        elif load_type == 'plugin_list':
            RaceContext.rhui.emit_plugin_list(nobroadcast=True)
        elif load_type == 'cluster_status':
            RaceContext.rhui.emit_cluster_status()
        elif load_type == 'hardware_log_init':
            emit_current_log_file_to_socket()
        else:
            logger.warning('Called undefined load type: {}'.format(load_type))

@SOCKET_IO.on('broadcast_message')
@catchLogExceptionsWrapper
def on_broadcast_message(data):
    RaceContext.rhui.emit_priority_message(data['message'], data['interrupt'])

# Settings socket io events

@SOCKET_IO.on('set_frequency')
@catchLogExceptionsWrapper
def on_set_frequency(data):
    '''Set node frequency.'''
    if RaceContext.cluster:
        RaceContext.cluster.emitToSplits('set_frequency', data)
    if isinstance(data, str): # LiveTime compatibility
        data = json.loads(data)
    node_index = data['node']
    frequency = int(data['frequency'])
    band = str(data['band']) if 'band' in data and data['band'] != None else None
    channel = int(data['channel']) if 'channel' in data and data['channel'] != None else None

    if node_index < 0 or node_index >= RaceContext.race.num_nodes:
        logger.info('Unable to set frequency ({0}) on node {1}; node index out of range'.format(frequency, node_index+1))
        return

    profile = RaceContext.race.profile
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

    profile = RaceContext.rhdata.alter_profile({
        'profile_id': profile.id,
        'frequencies': freqs
        })
    RaceContext.race.profile = profile

    RaceContext.interface.set_frequency(node_index, frequency)

    RaceContext.race.clear_results()

    Events.trigger(Evt.FREQUENCY_SET, {
        'nodeIndex': node_index,
        'frequency': frequency,
        'band': band,
        'channel': channel
        })

    RaceContext.rhui.emit_frequency_data()
    if Use_imdtabler_jar_flag:
        heartbeat_thread_function.imdtabler_flag = True

@SOCKET_IO.on('set_frequency_preset')
@catchLogExceptionsWrapper
def on_set_frequency_preset(data):
    ''' Apply preset frequencies '''
    if RaceContext.cluster:
        RaceContext.cluster.emitToSplits('set_frequency_preset', data)
    bands = []
    channels = []
    freqs = []
    if data['preset'] == 'All-N1':
        profile_freqs = json.loads(RaceContext.race.profile.frequencies)
        for _idx in range(RaceContext.race.num_nodes):
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
        while RaceContext.race.num_nodes > len(bands):
            bands.append(RHUtils.FREQUENCY_ID_NONE)
        while RaceContext.race.num_nodes > len(channels):
            channels.append(RHUtils.FREQUENCY_ID_NONE)
        while RaceContext.race.num_nodes > len(freqs):
            freqs.append(RHUtils.FREQUENCY_ID_NONE)

    payload = {
        "b": bands,
        "c": channels,
        "f": freqs
    }

    set_all_frequencies(payload)
    RaceContext.rhui.emit_frequency_data()
    if Use_imdtabler_jar_flag:
        heartbeat_thread_function.imdtabler_flag = True
    hardware_set_all_frequencies(payload)

def set_all_frequencies(freqs):
    ''' Set frequencies for all nodes (but do not update hardware) '''
    # Set DB
    profile = RaceContext.race.profile
    profile_freqs = json.loads(profile.frequencies)

    for idx in range(RaceContext.race.num_nodes):
        profile_freqs["b"][idx] = freqs["b"][idx]
        profile_freqs["c"][idx] = freqs["c"][idx]
        profile_freqs["f"][idx] = freqs["f"][idx]
        logger.info('Frequency set: Node {0} B:{1} Ch:{2} Freq:{3}'.format(idx+1, freqs["b"][idx], freqs["c"][idx], freqs["f"][idx]))

    profile = RaceContext.rhdata.alter_profile({
        'profile_id': profile.id,
        'frequencies': profile_freqs
        })
    RaceContext.race.profile = profile

def hardware_set_all_frequencies(freqs):
    '''do hardware update for frequencies'''
    logger.debug("Sending frequency values to nodes: " + str(freqs["f"]))
    for idx in range(RaceContext.race.num_nodes):
        RaceContext.interface.set_frequency(idx, freqs["f"][idx])

        RaceContext.race.clear_results()

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
    profile_freqs = json.loads(RaceContext.race.profile.frequencies)
    freq = profile_freqs["f"][node_index]
    RaceContext.interface.set_frequency(node_index, freq)
    logger.info('Frequency restored: Node {0} Frequency {1}'.format(node_index+1, freq))

@SOCKET_IO.on('set_enter_at_level')
@catchLogExceptionsWrapper
def on_set_enter_at_level(data):
    '''Set node enter-at level.'''
    seat_index = data['node']
    enter_at_level = data['enter_at_level']
    RaceContext.calibration.set_enter_at_level(seat_index, enter_at_level)

@SOCKET_IO.on('set_exit_at_level')
@catchLogExceptionsWrapper
def on_set_exit_at_level(data):
    '''Set node exit-at level.'''
    seat_index = data['node']
    exit_at_level = data['exit_at_level']
    RaceContext.calibration.set_exit_at_level(seat_index, exit_at_level)

@SOCKET_IO.on("set_start_thresh_lower_amount")
@catchLogExceptionsWrapper
def on_set_start_thresh_lower_amount(data):
    start_thresh_lower_amount = data['start_thresh_lower_amount']
    RaceContext.rhdata.set_option("startThreshLowerAmount", start_thresh_lower_amount)
    logger.info("set start_thresh_lower_amount to %s percent" % start_thresh_lower_amount)
    RaceContext.rhui.emit_start_thresh_lower_amount(noself=True)

@SOCKET_IO.on("set_start_thresh_lower_duration")
@catchLogExceptionsWrapper
def on_set_start_thresh_lower_duration(data):
    start_thresh_lower_duration = data['start_thresh_lower_duration']
    RaceContext.rhdata.set_option("startThreshLowerDuration", start_thresh_lower_duration)
    logger.info("set start_thresh_lower_duration to %s seconds" % start_thresh_lower_duration)
    RaceContext.rhui.emit_start_thresh_lower_duration(noself=True)

@SOCKET_IO.on('set_language')
@catchLogExceptionsWrapper
def on_set_language(data):
    '''Set interface language.'''
    RaceContext.rhdata.set_option('currentLanguage', data['language'])

@SOCKET_IO.on('cap_enter_at_btn')
@catchLogExceptionsWrapper
def on_cap_enter_at_btn(data):
    '''Capture enter-at level.'''
    node_index = data['node_index']
    if RaceContext.interface.start_capture_enter_at_level(node_index):
        logger.info('Starting capture of enter-at level for node {0}'.format(node_index+1))

@SOCKET_IO.on('cap_exit_at_btn')
@catchLogExceptionsWrapper
def on_cap_exit_at_btn(data):
    '''Capture exit-at level.'''
    node_index = data['node_index']
    if RaceContext.interface.start_capture_exit_at_level(node_index):
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
    node = RaceContext.interface.nodes[node_index]
    node.set_scan_interval(minScanFreq, maxScanFreq, maxScanInterval, minScanInterval, scanZoom)
    if node.scan_enabled:
        HEARTBEAT_DATA_RATE_FACTOR = 50
    else:
        HEARTBEAT_DATA_RATE_FACTOR = 5
        gevent.sleep(0.100)  # pause/spawn to get clear of heartbeat actions for scanner
        gevent.spawn(restore_node_frequency, node_index)

@SOCKET_IO.on('add_heat')
@catchLogExceptionsWrapper
def on_add_heat(data=None):
    '''Adds the next available heat number to the database.'''
    if data and 'class' in data:
        RaceContext.rhdata.add_heat(init={'class_id': data['class']})
    else:
        RaceContext.rhdata.add_heat()
    RaceContext.rhui.emit_heat_data()

@SOCKET_IO.on('duplicate_heat')
@catchLogExceptionsWrapper
def on_duplicate_heat(data):
    RaceContext.rhdata.duplicate_heat(data['heat'])
    RaceContext.rhui.emit_heat_data()

@SOCKET_IO.on('alter_heat')
@catchLogExceptionsWrapper
def on_alter_heat(data):
    '''Update heat.'''
    heat, altered_race_list = RaceContext.rhdata.alter_heat(data)
    if RaceContext.race.current_heat == heat.id:  # if current heat was altered then update heat data
        RaceContext.race.set_heat(heat.id, silent=True)
    RaceContext.rhui.emit_heat_data(noself=True)
    if ('name' in data or 'pilot' in data or 'class' in data) and len(altered_race_list):
        RaceContext.rhui.emit_result_data() # live update rounds page
        message = __('Alterations made to heat: {0}').format(heat.display_name)
        RaceContext.rhui.emit_priority_message(message, False)

@SOCKET_IO.on('delete_heat')
@catchLogExceptionsWrapper
def on_delete_heat(data):
    '''Delete heat.'''
    heat_id = data['heat']
    result = RaceContext.rhdata.delete_heat(heat_id)
    if result:
        if RaceContext.last_race and RaceContext.last_race.current_heat == heat_id:
            RaceContext.last_race = None  # if last-race heat deleted then clear last race
        if RaceContext.race.current_heat == heat_id:  # if current heat was deleted then drop to practice mode (avoids dynamic heat calculation)
            RaceContext.race.set_heat(RHUtils.HEAT_ID_NONE)
        RaceContext.rhui.emit_heat_data()

@SOCKET_IO.on('add_race_class')
@catchLogExceptionsWrapper
def on_add_race_class():
    '''Adds the next available pilot id number in the database.'''
    RaceContext.rhdata.add_raceClass()
    RaceContext.rhui.emit_class_data()
    RaceContext.rhui.emit_heat_data() # Update class selections in heat displays

@SOCKET_IO.on('duplicate_race_class')
@catchLogExceptionsWrapper
def on_duplicate_race_class(data):
    '''Adds new race class by duplicating an existing one.'''
    RaceContext.rhdata.duplicate_raceClass(data['class'])
    RaceContext.rhui.emit_class_data()
    RaceContext.rhui.emit_heat_data()

@SOCKET_IO.on('alter_race_class')
@catchLogExceptionsWrapper
def on_alter_race_class(data):
    '''Update race class.'''
    race_class, altered_race_list = RaceContext.rhdata.alter_raceClass(data)

    if ('class_format' in data or \
        'class_name' in data or \
        'win_condition' in data or \
        'rank_settings' in data) and len(altered_race_list):
        RaceContext.rhui.emit_result_data() # live update rounds page
        message = __('Alterations made to race class: {0}').format(race_class.display_name)
        RaceContext.rhui.emit_priority_message(message, False)

    RaceContext.rhui.emit_class_data(noself=True)
    if 'class_name' in data:
        RaceContext.rhui.emit_heat_data() # Update class names in heat displays
    if 'class_format' in data:
        RaceContext.rhui.emit_current_heat(noself=True) # in case race operator is a different client, update locked format dropdown

@SOCKET_IO.on('delete_class')
@catchLogExceptionsWrapper
def on_delete_class(data):
    '''Delete class.'''
    result = RaceContext.rhdata.delete_raceClass(data['class'])
    if result:
        RaceContext.rhui.emit_class_data()
        RaceContext.rhui.emit_heat_data()

@SOCKET_IO.on('add_pilot')
@catchLogExceptionsWrapper
def on_add_pilot():
    '''Adds the next available pilot id number in the database.'''
    RaceContext.rhdata.add_pilot()
    RaceContext.rhui.emit_pilot_data()

@SOCKET_IO.on('alter_pilot')
@catchLogExceptionsWrapper
def on_alter_pilot(data):
    '''Update pilot.'''
    _pilot, race_list = RaceContext.rhdata.alter_pilot(data)

    RaceContext.rhui.emit_pilot_data(noself=True) # Settings page, new pilot settings

    if 'callsign' in data or 'team_name' in data:
        RaceContext.rhui.emit_heat_data() # Settings page, new pilot callsign in heats
        if len(race_list):
            RaceContext.rhui.emit_result_data() # live update rounds page
    if 'phonetic' in data:
        RaceContext.rhui.emit_heat_data() # Settings page, new pilot phonetic in heats. Needed?

    RaceContext.race.clear_results() # refresh current leaderboard

@SOCKET_IO.on('delete_pilot')
@catchLogExceptionsWrapper
def on_delete_pilot(data):
    '''Delete pilot.'''
    result = RaceContext.rhdata.delete_pilot(data['pilot'])

    if result:
        RaceContext.rhui.emit_pilot_data()
        RaceContext.rhui.emit_heat_data()

@SOCKET_IO.on('add_profile')
@catchLogExceptionsWrapper
def on_add_profile():
    '''Adds new profile (frequency set) in the database.'''
    source_profile = RaceContext.race.profile
    new_profile = RaceContext.rhdata.duplicate_profile(source_profile)

    on_set_profile({ 'profile': new_profile.id })

@SOCKET_IO.on('alter_profile')
@catchLogExceptionsWrapper
def on_alter_profile(data):
    ''' update profile '''
    profile = RaceContext.race.profile
    data['profile_id'] = profile.id
    profile = RaceContext.rhdata.alter_profile(data)
    RaceContext.race.profile = profile

    RaceContext.rhui.emit_node_tuning(noself=True)

@SOCKET_IO.on('delete_profile')
@catchLogExceptionsWrapper
def on_delete_profile():
    '''Delete profile'''
    profile = RaceContext.race.profile
    result = RaceContext.rhdata.delete_profile(profile)

    if result:
        first_profile_id = RaceContext.rhdata.get_first_profile().id
        RaceContext.rhdata.set_option("currentProfile", first_profile_id)
        on_set_profile({ 'profile': first_profile_id })

@SOCKET_IO.on("set_profile")
@catchLogExceptionsWrapper
def on_set_profile(data, emit_vals=True):
    ''' set current profile '''
    profile_val = int(data['profile'])
    profile = RaceContext.rhdata.get_profile(profile_val)
    if profile:
        RaceContext.rhdata.set_option("currentProfile", data['profile'])
        logger.info("Set Profile to '%s'" % profile_val)
        RaceContext.race.profile = profile
        # set freqs, enter_ats, and exit_ats
        freqs = json.loads(profile.frequencies)
        moreNodesFlag = False
        if RaceContext.race.num_nodes > len(freqs["b"]) or RaceContext.race.num_nodes > len(freqs["c"]) or \
                                        RaceContext.race.num_nodes > len(freqs["f"]):
            moreNodesFlag = True
            while RaceContext.race.num_nodes > len(freqs["b"]):
                freqs["b"].append(RHUtils.FREQUENCY_ID_NONE)
            while RaceContext.race.num_nodes > len(freqs["c"]):
                freqs["c"].append(RHUtils.FREQUENCY_ID_NONE)
            while RaceContext.race.num_nodes > len(freqs["f"]):
                freqs["f"].append(RHUtils.FREQUENCY_ID_NONE)

        if profile.enter_ats:
            enter_ats_loaded = json.loads(profile.enter_ats)
            enter_ats = enter_ats_loaded["v"]
            if RaceContext.race.num_nodes > len(enter_ats):
                moreNodesFlag = True
                while RaceContext.race.num_nodes > len(enter_ats):
                    enter_ats.append(None)
        else: #handle null data by copying in hardware values
            enter_at_levels = {}
            enter_at_levels["v"] = [node.enter_at_level for node in RaceContext.interface.nodes]
            RaceContext.rhdata.alter_profile({'profile_id': profile_val, 'enter_ats': enter_at_levels})
            enter_ats = enter_at_levels["v"]

        if profile.exit_ats:
            exit_ats_loaded = json.loads(profile.exit_ats)
            exit_ats = exit_ats_loaded["v"]
            if RaceContext.race.num_nodes > len(exit_ats):
                moreNodesFlag = True
                while RaceContext.race.num_nodes > len(exit_ats):
                    exit_ats.append(None)
        else: #handle null data by copying in hardware values
            exit_at_levels = {}
            exit_at_levels["v"] = [node.exit_at_level for node in RaceContext.interface.nodes]
            RaceContext.rhdata.alter_profile({'profile_id': profile_val,'exit_ats': exit_at_levels})
            exit_ats = exit_at_levels["v"]

        # if added nodes detected then update profile values in database
        if moreNodesFlag:
            logger.info("Updating profile '%s' in DB to account for added nodes" % profile_val)
            RaceContext.rhdata.alter_profile({'profile_id': profile_val, 'frequencies': freqs,
                                  'enter_ats': enter_ats_loaded, 'exit_ats': exit_ats_loaded})

        RaceContext.race.profile = profile
        Events.trigger(Evt.PROFILE_SET, {
            'profile_id': profile_val,
            })

        if emit_vals:
            RaceContext.rhui.emit_node_tuning()
            RaceContext.rhui.emit_enter_and_exit_at_levels()
            RaceContext.rhui.emit_frequency_data()
            if Use_imdtabler_jar_flag:
                heartbeat_thread_function.imdtabler_flag = True

        hardware_set_all_frequencies(freqs)
        RaceContext.calibration.hardware_set_all_enter_ats(enter_ats)
        RaceContext.calibration.hardware_set_all_exit_ats(exit_ats)

    else:
        logger.warning('Invalid set_profile value: ' + str(profile_val))

RHAPI.race._frequencyset_set = on_set_profile # TODO: Refactor management functions

@SOCKET_IO.on('alter_race')
@catchLogExceptionsWrapper
def on_alter_race(data):
    '''Update race (retroactively via marshaling).'''

    _race_meta, new_heat = RaceContext.rhdata.reassign_savedRaceMeta_heat(data['race_id'], data['heat_id'])

    message = __('A race has been reassigned to {0}').format(new_heat.display_name)
    RaceContext.rhui.emit_priority_message(message, False)

    RaceContext.rhui.emit_race_list(nobroadcast=True)
    RaceContext.rhui.emit_result_data()

@SOCKET_IO.on('backup_database')
@catchLogExceptionsWrapper
def on_backup_database():
    '''Backup database.'''
    bkp_name = RaceContext.rhdata.backup_db_file(True)  # make copy of DB file

    # read DB data and convert to Base64
    with open(bkp_name, mode='rb') as file_obj:
        file_content = file_obj.read()
    file_content = base64.encodebytes(file_content).decode()

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

        files.sort(key=str.casefold)

        files = list(filter(lambda x: x.endswith(".db"), files))

        emit_payload = {
            'backup_files': files
        }

    emit('backups_list', emit_payload)

def restore_database_file(db_file_name):
    stop_background_threads()
    gevent.sleep(0.1)
    try:
        RaceContext.rhdata.close()
        RaceContext.race = RHRace.RHRace(RaceContext) # Reset all RACE values
        RaceContext.race.num_nodes = len(RaceContext.interface.nodes)  # restore number of nodes
        RaceContext.last_race = None
        try:
            RaceContext.rhdata.recover_database(db_file_name)
            gevent.sleep(1)  # pause/yield to allow changes to be committed
            RaceContext.race.reset_current_laps()
            clean_results_cache()
            RaceContext.race.current_heat = RaceContext.rhdata.get_optionInt('currentHeat')
            expand_heats()
            raceformat_id = RaceContext.rhdata.get_optionInt('currentFormat')
            RaceContext.race.format = RaceContext.rhdata.get_raceFormat(raceformat_id)
            RaceContext.rhui.emit_current_laps()
            success = True
        except Exception as ex:
            logger.warning('Clearing all data after recovery failure:  ' + str(ex))
            db_reset()
            success = False
        init_race_state()
        init_interface_state()
    except Exception:
        logger.exception("Unexpected error in 'restore_database_file()'")
        success = False
    start_background_threads(True)
    return success

@SOCKET_IO.on('restore_database')
@catchLogExceptionsWrapper
def on_restore_database(data):
    '''Restore database.'''
    success = None
    if 'backup_file' in data:
        backup_file = data['backup_file']
        backup_path = DB_BKP_DIR_NAME + '/' + backup_file

        if os.path.exists(backup_path):
            logger.info('Found {0}: starting restoration...'.format(backup_file))
            success = restore_database_file(backup_path)
            Events.trigger(Evt.DATABASE_RESTORE, {
                'file_name': backup_file,
                })

            SOCKET_IO.emit('database_restore_done')
        else:
            logger.warning('Unable to restore {0}: File does not exist'.format(backup_file))
            success = False

    if success == False:
        message = __('Database recovery failed for: {0}').format(backup_file)
        RaceContext.rhui.emit_priority_message(message, False, nobroadcast=True)

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
    RaceContext.pagecache.set_valid(False)

    on_stop_race()
    on_discard_laps()
    RaceContext.rhdata.clear_lapSplits()

    if data.get('with_archive'):
        RaceContext.rhdata.backup_db_file(True, use_filename=RaceContext.rhdata.get_option('eventName'))
        on_list_backups()

    reset_type = data['reset_type']
    if reset_type == 'races':
        RaceContext.rhdata.clear_race_data()
        RaceContext.race.reset_current_laps()
    elif reset_type == 'heats':
        RaceContext.rhdata.reset_heats()
        RaceContext.rhdata.clear_race_data()
        RaceContext.race.reset_current_laps()
    elif reset_type == 'classes':
        RaceContext.rhdata.reset_heats()
        RaceContext.rhdata.reset_raceClasses()
        RaceContext.rhdata.clear_race_data()
        RaceContext.race.reset_current_laps()
    elif reset_type == 'pilots':
        RaceContext.rhdata.reset_pilots()
        RaceContext.rhdata.reset_heats()
        RaceContext.rhdata.clear_race_data()
        RaceContext.race.reset_current_laps()
    elif reset_type == 'all':
        RaceContext.rhdata.reset_pilots()
        RaceContext.rhdata.reset_heats()
        RaceContext.rhdata.reset_raceClasses()
        RaceContext.rhdata.clear_race_data()
        RaceContext.race.reset_current_laps()
    elif reset_type == 'formats':
        RaceContext.rhdata.clear_race_data()
        RaceContext.race.reset_current_laps()
        RaceContext.rhdata.reset_raceFormats()
        RaceContext.race.format = RaceContext.rhdata.get_first_raceFormat()
    RaceContext.race.set_heat(RaceContext.rhdata.get_initial_heat_id(), force=True)
    RaceContext.rhui.emit_heat_data()
    RaceContext.rhui.emit_pilot_data()
    RaceContext.rhui.emit_format_data()
    RaceContext.rhui.emit_class_data()
    RaceContext.rhui.emit_current_laps()
    RaceContext.rhui.emit_result_data()
    emit('reset_confirm')

    Events.trigger(Evt.DATABASE_RESET)

@SOCKET_IO.on('export_database')
@catchLogExceptionsWrapper
def on_export_database_file(data):
    '''Run the selected Exporter'''
    exporter = data['exporter']

    if exporter in RaceContext.export_manager.exporters:
        # do export
        logger.info('Exporting data via {0}'.format(exporter))
        export_result = RaceContext.export_manager.export(exporter)

        if export_result != False:
            try:
                emit_payload = {
                    'filename': 'RotorHazard Export ' + datetime.now().strftime('%Y%m%d_%H%M%S') + ' ' + exporter + '.' + export_result['ext'],
                    'encoding': export_result['encoding'],
                    'data' : export_result['data']
                }
                emit('exported_data', emit_payload)

            except Exception:
                logger.exception("Error downloading export file")
                RaceContext.rhui.emit_priority_message(__('Data export failed. (See log)'), False, nobroadcast=True)
        else:
            RaceContext.rhui.emit_priority_message(__('Data export failed. (See log)'), False, nobroadcast=True)

        return

    logger.error('Data exporter "{0}" not found'.format(exporter))
    RaceContext.rhui.emit_priority_message(__('Data export failed. (See log)'), False, nobroadcast=True)

@SOCKET_IO.on('import_data')
@catchLogExceptionsWrapper
def on_import_file(data):
    '''Run the selected Importer'''
    importer = data['importer']

    if importer in RaceContext.import_manager.importers:
        if 'source_data' in data and data['source_data']:
            import_args = {}
            if 'params' in data:
                for param, value in data['params'].items():
                    import_args[param] = value

            # do import
            logger.info('Importing data via {0}'.format(importer))
            import_result = RaceContext.import_manager.run_import(importer, data['source_data'], import_args)

            if import_result != False:
                clean_results_cache()
                SOCKET_IO.emit('database_restore_done')
            else:
                RaceContext.rhui.emit_priority_message(__('Data import failed. (See log)'), True, nobroadcast=True)

            return
        else:
            RaceContext.rhui.emit_priority_message(__('Data import failed. No source data.'), True, nobroadcast=True)

    logger.error('Data importer "{0}" not found'.format(importer))
    RaceContext.rhui.emit_priority_message(__('Data import failed. (See log)'), True, nobroadcast=True)

@SOCKET_IO.on('generate_heats_v2')
@catchLogExceptionsWrapper
def on_generate_heats_v2(data):
    '''Run the selected Generator'''
    available_seats = 0
    profile_freqs = json.loads(RaceContext.race.profile.frequencies)
    for node_index in range(RaceContext.race.num_nodes):
        if profile_freqs["f"][node_index] != RHUtils.FREQUENCY_ID_NONE:
            available_seats += 1

    generate_args = {
        'input_class': data['input_class'],
        'output_class': data['output_class'],
        'available_seats': available_seats
        }
    if 'params' in data:
        for param, value in data['params'].items():
            generate_args[param] = value

    generator = data['generator']

    if generator in RaceContext.heat_generate_manager.generators:
        generatorObj = RaceContext.heat_generate_manager.generators[generator]

        # do generation
        logger.info('Generating heats via {0}'.format(generatorObj.label))
        generate_result = RaceContext.heat_generate_manager.generate(generator, generate_args)

        if generate_result != False:
            RaceContext.rhui.emit_priority_message(__('Generated heats via {0}'.format(generatorObj.label)), False, nobroadcast=True)
            RaceContext.rhui.emit_heat_data()
            RaceContext.rhui.emit_class_data()
        else:
            RaceContext.rhui.emit_priority_message(__('Heat generation failed. (See log)'), False, nobroadcast=True)

        return

    logger.error('Heat generator "{0}" not found'.format(generator))
    RaceContext.rhui.emit_priority_message(__('Heat generation failed. (See log)'), False, nobroadcast=True)

@SOCKET_IO.on('shutdown_pi')
@catchLogExceptionsWrapper
def on_shutdown_pi():
    '''Shutdown the raspberry pi.'''
    if  RaceContext.interface.send_shutdown_started_message():
        gevent.sleep(0.25)  # give shutdown-started message a chance to transmit to node
    if RaceContext.cluster:
        RaceContext.cluster.emit('shutdown_pi')
    RaceContext.rhui.emit_priority_message(__('Server has shut down.'), True, caller='shutdown')
    logger.info('Performing system shutdown')
    Events.trigger(Evt.SHUTDOWN)
    stop_background_threads()
    gevent.sleep(0.5)
    gevent.spawn(SOCKET_IO.stop)  # shut down flask http server
    if RHUtils.is_sys_raspberry_pi():
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
    if RaceContext.cluster:
        RaceContext.cluster.emit('reboot_pi')
    RaceContext.rhui.emit_priority_message(__('Server is rebooting.'), True, caller='shutdown')
    logger.info('Performing system reboot')
    Events.trigger(Evt.SHUTDOWN)
    stop_background_threads()
    gevent.sleep(0.5)
    gevent.spawn(SOCKET_IO.stop)  # shut down flask http server
    if RHUtils.is_sys_raspberry_pi():
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
    if RaceContext.cluster:
        RaceContext.cluster.emit('kill_server')
    RaceContext.rhui.emit_priority_message(__('Server has stopped.'), True, caller='shutdown')
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
            file_content = base64.encodebytes(file_content).decode()

            emit_payload = {
                'file_name': os.path.basename(zip_path_name),
                'file_data' : file_content
            }

            SOCKET_IO.emit(data['emit_fn_name'], emit_payload)
        except Exception:
            logger.exception("Error downloading logs-zip file")

@SOCKET_IO.on("set_min_lap")
@catchLogExceptionsWrapper
def on_set_min_lap(data):
    min_lap = data['min_lap']
    RaceContext.rhdata.set_option("MinLapSec", data['min_lap'])

    Events.trigger(Evt.MIN_LAP_TIME_SET, {
        'min_lap': min_lap,
        })

    logger.info("set min lap time to %s seconds" % min_lap)
    RaceContext.rhui.emit_min_lap(noself=True)

@SOCKET_IO.on("set_min_lap_behavior")
@catchLogExceptionsWrapper
def on_set_min_lap_behavior(data):
    min_lap_behavior = int(data['min_lap_behavior'])
    RaceContext.rhdata.set_option("MinLapBehavior", min_lap_behavior)

    Events.trigger(Evt.MIN_LAP_BEHAVIOR_SET, {
        'min_lap_behavior': min_lap_behavior,
        })

    logger.info("set min lap behavior to %s" % min_lap_behavior)
    RaceContext.rhui.emit_min_lap(noself=True)

@SOCKET_IO.on("set_race_format")
@catchLogExceptionsWrapper
def on_set_race_format(data):
    ''' set current race_format '''
    if RaceContext.race.race_status == RaceStatus.READY: # prevent format change if race running
        race_format_val = data['race_format']
        RaceContext.race.format = RaceContext.rhdata.get_raceFormat(race_format_val)

        Events.trigger(Evt.RACE_FORMAT_SET, {
            'race_format': race_format_val,
            })

        if request:
            RaceContext.rhui.emit_current_laps()
            RaceContext.rhui.emit_current_leaderboard() # Run page, to update leaderboard if changing to/from team racing
            RaceContext.rhui.emit_race_status()
        logger.info("set race format to '%s' (%s)" % (RaceContext.race.format.name, RaceContext.race.format.id))
    else:
        if request:
            RaceContext.rhui.emit_priority_message(__('Format change prevented by active race: Stop and save/discard laps'), False, nobroadcast=True)
            RaceContext.rhui.emit_race_status()
        logger.info("Format change prevented by active race")

RHAPI.race._raceformat_set = on_set_race_format # TODO: Refactor management functions

@SOCKET_IO.on('add_race_format')
@catchLogExceptionsWrapper
def on_add_race_format(data):
    '''Adds new format in the database by duplicating an existing one.'''
    source_format_id = data['source_format_id']
    _new_format = RaceContext.rhdata.duplicate_raceFormat(source_format_id)
    RaceContext.rhui.emit_format_data()

@SOCKET_IO.on('alter_race_format')
@catchLogExceptionsWrapper
def on_alter_race_format(data):
    ''' update race format '''
    race_format, race_list = RaceContext.rhdata.alter_raceFormat(data)

    if race_format != False:
        RaceContext.race.format = race_format
        RaceContext.rhui.emit_current_laps()

        if 'format_name' in data:
            RaceContext.rhui.emit_format_data()
            RaceContext.rhui.emit_class_data()

        if len(race_list):
            RaceContext.rhui.emit_result_data()
            message = __('Alterations made to race format: {0}').format(RaceContext.race.format.name)
            RaceContext.rhui.emit_priority_message(message, False)
    else:
        RaceContext.rhui.emit_priority_message(__('Format alteration prevented by active race: Stop and save/discard laps'), False, nobroadcast=True)

@SOCKET_IO.on('delete_race_format')
@catchLogExceptionsWrapper
def on_delete_race_format(data):
    '''Delete race format'''
    format_id = data['format_id']
    result = RaceContext.rhdata.delete_raceFormat(format_id)

    if result:
        first_raceFormat = RaceContext.rhdata.get_first_raceFormat()
        RaceContext.race.format = first_raceFormat
        RaceContext.rhui.emit_current_laps()
        RaceContext.rhui.emit_format_data()
    else:
        if RaceContext.race.race_status == RaceStatus.READY:
            RaceContext.rhui.emit_priority_message(__('Format deletion prevented: saved race exists with this format'), False, nobroadcast=True)
        else:
            RaceContext.rhui.emit_priority_message(__('Format deletion prevented by active race: Stop and save/discard laps'), False, nobroadcast=True)

# LED Effects

def emit_led_effect_setup(**_params):
    '''Emits LED event/effect wiring options.'''
    if RaceContext.led_manager.isEnabled():
        effects = RaceContext.led_manager.getRegisteredEffects()

        emit_payload = {
            'events': []
        }

        for event in LEDEvent.configurable_events:
            selectedEffect = RaceContext.led_manager.getEventEffect(event['event'])

            effect_list_recommended = []
            effect_list_normal = []

            for effect in effects:

                if event['event'] in effects[effect].valid_events.get('include', []) or (
                    event['event'] not in [Evt.SHUTDOWN, LEDEvent.IDLE_DONE, LEDEvent.IDLE_RACING, LEDEvent.IDLE_READY]
                    and event['event'] not in effects[effect].valid_events.get('exclude', [])
                    and Evt.ALL not in effects[effect].valid_events.get('exclude', [])):

                    if event['event'] in effects[effect].valid_events.get('recommended', []) or \
                        Evt.ALL in effects[effect].valid_events.get('recommended', []):
                        effect_list_recommended.append({
                            'name': effect,
                            'label': '* ' + __(effects[effect].label)
                        })
                    else:
                        effect_list_normal.append({
                            'name': effect,
                            'label': __(effects[effect].label)
                        })

            effect_list_recommended.sort(key=lambda x: x['label'])
            effect_list_normal.sort(key=lambda x: x['label'])

            emit_payload['events'].append({
                'event': event['event'],
                'label': __(event['label']),
                'selected': selectedEffect,
                'effects': effect_list_recommended + effect_list_normal
            })

        # never broadcast
        emit('led_effect_setup_data', emit_payload)

def emit_led_effects(**_params):
    if RaceContext.led_manager.isEnabled() or (RaceContext.cluster and RaceContext.cluster.hasRecEventsSecondaries()):
        effects = RaceContext.led_manager.getRegisteredEffects()

        effect_list = []
        if effects:
            for effect in effects:
                if effects[effect].valid_events.get('manual', True):
                    effect_list.append({
                        'name': effect,
                        'label': __(effects[effect].label)
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
        if RaceContext.led_manager.isEnabled():
            RaceContext.led_manager.setEventEffect(data['event'], data['effect'])

        effect_opt = RaceContext.rhdata.get_option('ledEffects')
        if effect_opt:
            effects = json.loads(effect_opt)
        else:
            effects = {}

        effects[data['event']] = data['effect']
        RaceContext.rhdata.set_option('ledEffects', json.dumps(effects))

        Events.trigger(Evt.LED_EFFECT_SET, {
            'effect': data['event'],
            })

        logger.info('Set LED event {0} to effect {1}'.format(data['event'], data['effect']))

@SOCKET_IO.on('use_led_effect')
@catchLogExceptionsWrapper
def on_use_led_effect(data):
    '''Activate arbitrary LED Effect.'''
    if 'effect' in data:
        if RaceContext.led_manager.isEnabled():
            RaceContext.led_manager.setEventEffect(Evt.LED_MANUAL, data['effect'])
        Events.trigger(Evt.LED_SET_MANUAL, data)  # setup manual effect on mirror timers

        args = {}
        if 'args' in data:
            args = data['args']
        if 'color' in data:
            args['color'] = RHUtils.hexToColor(data['color'])

        Events.trigger(Evt.LED_MANUAL, args)

# Race management socket io events

# TODO: Remove
@SOCKET_IO.on('get_pi_time')
@catchLogExceptionsWrapper
def on_get_pi_time():
    # never broadcasts to all (client must make request)
    emit('pi_time', {
        'pi_time_s': monotonic()
    })

@SOCKET_IO.on('get_server_time')
@catchLogExceptionsWrapper
def on_get_server_time():
    return {'server_time_s': monotonic()}

@SOCKET_IO.on('schedule_race')
@catchLogExceptionsWrapper
def on_schedule_race(data):
    RaceContext.race.schedule(data['s'], data['m'])

@SOCKET_IO.on('cancel_schedule_race')
@catchLogExceptionsWrapper
def cancel_schedule_race():
    RaceContext.race.schedule(None)

@SOCKET_IO.on('stage_race')
def on_stage_race(*args):
    RaceContext.race.stage(*args)

@SOCKET_IO.on('stop_race')
def on_stop_race(*args):
    RaceContext.race.stop(*args)

@SOCKET_IO.on('save_laps')
def on_save_race(*args):
    RaceContext.race.save(*args)

@SOCKET_IO.on('resave_laps')
@catchLogExceptionsWrapper
def on_resave_laps(data):
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

    # Clear caches
    heat = RaceContext.rhdata.get_heat(heat_id)
    RaceContext.rhdata.clear_results_heat(heat)
    RaceContext.rhdata.clear_results_raceClass(heat.class_id)
    RaceContext.rhdata.clear_results_savedRaceMeta(race_id)

    RaceContext.rhdata.alter_savedPilotRace(pilotrace_data)

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
            tmp_lap_time_formatted = RHUtils.time_format(lap['lap_time'], RaceContext.rhdata.get_option('timeFormat'))

        new_racedata['laps'].append({
            'lap_time_stamp': lap['lap_time_stamp'],
            'lap_time': lap['lap_time'],
            'lap_time_formatted': tmp_lap_time_formatted,
            'source': lap['source'],
            'deleted': lap['deleted']
            })

    RaceContext.rhdata.replace_savedRaceLaps(new_racedata)

    message = __('Race times adjusted for: Heat {0} Round {1} / {2}').format(heat_id, round_id, callsign)
    RaceContext.rhui.emit_priority_message(message, False)
    logger.info(message)

    # run adaptive calibration
    if RaceContext.rhdata.get_optionInt('calibrationMode'):
        RaceContext.calibration.auto_calibrate()

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
    RaceContext.pagecache.set_valid(False)
    Results.build_atomic_results(RaceContext.rhdata, params)
    RaceContext.rhui.emit_result_data()

@SOCKET_IO.on('discard_laps')
@catchLogExceptionsWrapper
def on_discard_laps(**kwargs):
    RaceContext.race.discard_laps(**kwargs)

@SOCKET_IO.on('calc_pilots')
@catchLogExceptionsWrapper
def on_calc_pilots(data):
    heat_id = data['heat']
    RaceContext.heatautomator.calc_heat(heat_id)

@SOCKET_IO.on('calc_reset')
@catchLogExceptionsWrapper
def on_calc_reset(data):
    data['status'] = Database.HeatStatus.PLANNED
    on_alter_heat(data)
    RaceContext.rhui.emit_heat_data()

@SOCKET_IO.on('confirm_heat_plan')
@catchLogExceptionsWrapper
def on_confirm_heat(data):
    if 'heat_id' in data:
        RaceContext.rhdata.alter_heat({
            'heat': data['heat_id'],
            'status': Database.HeatStatus.CONFIRMED
            }
        )
        RaceContext.rhdata.resolve_slot_unset_nodes(data['heat_id'])
        RaceContext.rhui.emit_heat_data()

        if RaceContext.race.race_status == RaceStatus.READY:
            RaceContext.race.set_heat(data['heat_id'], force=True)

@SOCKET_IO.on('set_current_heat')
@catchLogExceptionsWrapper
def on_set_current_heat(data):
    '''Update the current heat variable and data.'''
    RaceContext.race.set_heat(data['heat'])

@SOCKET_IO.on('delete_lap')
def on_delete_lap(data):
    RaceContext.race.delete_lap(data)

@SOCKET_IO.on('restore_deleted_lap')
def on_restore_deleted_lap(data):
    RaceContext.race.restore_deleted_lap(data)


@SOCKET_IO.on('simulate_lap')
@catchLogExceptionsWrapper
def on_simulate_lap(data):
    '''Simulates a lap (for debug testing).'''
    node_index = data['node']
    logger.info('Simulated lap: Node {0}'.format(node_index+1))
    Events.trigger(Evt.CROSSING_EXIT, {
        'nodeIndex': node_index,
        'color': RaceContext.race.seat_colors[node_index]
        })
    RaceContext.interface.intf_simulate_lap(node_index, 0)

@SOCKET_IO.on('LED_solid')
@catchLogExceptionsWrapper
def on_LED_solid(data):
    '''LED Solid Color'''
    if 'off' in data and data['off']:
        RaceContext.led_manager.clear()
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

@SOCKET_IO.on('LED_brightness')
@catchLogExceptionsWrapper
def on_LED_brightness(data):
    '''Change LED Brightness'''
    brightness = data['brightness']
    strip.setBrightness(brightness)
    strip.show()
    RaceContext.rhdata.set_option("ledBrightness", brightness)
    Events.trigger(Evt.LED_BRIGHTNESS_SET, {
        'level': brightness,
        })

@SOCKET_IO.on('set_option')
@catchLogExceptionsWrapper
def on_set_option(data):
    RaceContext.rhdata.set_option(data['option'], data['value'])
    Events.trigger(Evt.OPTION_SET, {
        'option': data['option'],
        'value': data['value'],
        })

@SOCKET_IO.on('set_consecutives_count')
@catchLogExceptionsWrapper
def on_set_consecutives_count(data):
    RaceContext.rhdata.set_option('consecutivesCount', data['count'])
    RaceContext.rhdata.clear_results_all()
    RaceContext.pagecache.set_valid(False)
    Events.trigger(Evt.OPTION_SET, {
        'option': 'consecutivesCount',
        'value': data['count'],
        })

@SOCKET_IO.on('get_race_scheduled')
@catchLogExceptionsWrapper
def get_race_elapsed():
    # get current race status; never broadcasts to all
    emit('race_scheduled', {
        'scheduled': RaceContext.race.scheduled,
        'scheduled_at': RaceContext.race.scheduled_time
    })

@SOCKET_IO.on('save_callouts')
@catchLogExceptionsWrapper
def save_callouts(data):
    # save callouts to Options
    callouts = json.dumps(data['callouts'])
    RaceContext.rhdata.set_option('voiceCallouts', callouts)
    logger.info('Set all voice callouts')
    logger.debug('Voice callouts set to: {0}'.format(callouts))

@SOCKET_IO.on('reload_callouts')
@catchLogExceptionsWrapper
def reload_callouts():
    RaceContext.rhui.emit_callouts()

@SOCKET_IO.on('play_callout_text')
@catchLogExceptionsWrapper
def play_callout_text(data):
    message = RHUtils.doReplace(RHAPI, data['callout'], {}, True)
    RaceContext.rhui.emit_phonetic_text(message)

@SOCKET_IO.on('imdtabler_update_freqs')
@catchLogExceptionsWrapper
def imdtabler_update_freqs(data):
    ''' Update IMDTabler page with new frequencies list '''
    RaceContext.rhui.emit_imdtabler_data(IMDTABLER_JAR_NAME, data['freq_list'].replace(',',' ').split())

@SOCKET_IO.on('clean_cache')
@catchLogExceptionsWrapper
def clean_results_cache():
    ''' wipe all results caches '''
    Events.trigger(Evt.CACHE_CLEAR)
    RaceContext.rhdata.clear_results_all()
    RaceContext.pagecache.set_valid(False)

@SOCKET_IO.on('retry_secondary')
@catchLogExceptionsWrapper
def on_retry_secondary(data):
    '''Retry connection to secondary timer.'''
    RaceContext.cluster.retrySecondary(data['secondary_id'])
    RaceContext.rhui.emit_cluster_status()

@SOCKET_IO.on('get_pilotrace')
@catchLogExceptionsWrapper
def get_pilotrace(data):
    # get single race detail
    if 'pilotrace_id' in data:
        pilotrace = RaceContext.rhdata.get_savedPilotRace(data['pilotrace_id'])

        laps = []
        for lap in RaceContext.rhdata.get_savedRaceLaps_by_savedPilotRace(pilotrace.id):
            laps.append({
                    'id': lap.id,
                    'lap_time_stamp': lap.lap_time_stamp,
                    'lap_time': lap.lap_time,
                    'lap_time_formatted': lap.lap_time_formatted,
                    'source': lap.source,
                    'deleted': lap.deleted
                })

        pilot_data = RaceContext.rhdata.get_pilot(pilotrace.pilot_id)
        if pilot_data:
            nodepilot = pilot_data.callsign
        else:
            nodepilot = None

        emit('race_details', {
            'pilotrace_id': data['pilotrace_id'],
            'callsign': nodepilot,
            'pilot_id': pilotrace.pilot_id,
            'node_index': pilotrace.node_index,
            'history_values': json.loads(pilotrace.history_values),
            'history_times': json.loads(pilotrace.history_times),
            'laps': laps,
            'enter_at': pilotrace.enter_at,
            'exit_at': pilotrace.exit_at,
        })

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
        rStr = RHUtils.findPrefixedSubstring(dataStr, RaceContext.interface.FW_VERSION_PREFIXSTR, \
                                             RaceContext.interface.FW_TEXT_BLOCK_SIZE)
        fwVerStr = rStr if rStr else "(unknown)"
        fwRTypStr = RHUtils.findPrefixedSubstring(dataStr, RaceContext.interface.FW_PROCTYPE_PREFIXSTR, \
                                             RaceContext.interface.FW_TEXT_BLOCK_SIZE)
        fwTypStr = (fwRTypStr + ", ") if fwRTypStr else ""
        rStr = RHUtils.findPrefixedSubstring(dataStr, RaceContext.interface.FW_BUILDDATE_PREFIXSTR, \
                                             RaceContext.interface.FW_TEXT_BLOCK_SIZE)
        if rStr:
            fwTimStr = rStr
            rStr = RHUtils.findPrefixedSubstring(dataStr, RaceContext.interface.FW_BUILDTIME_PREFIXSTR, \
                                                 RaceContext.interface.FW_TEXT_BLOCK_SIZE)
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
        info_node = RaceContext.interface.get_info_node_obj()
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
    portStr = RaceContext.interface.get_fwupd_serial_name()
    msgStr = "Performing S32_BPill update, port='{}', file: {}".format(portStr, srcStr)
    logger.info(msgStr)
    SOCKET_IO.emit('upd_messages_init', (msgStr + "\n"))
    stop_background_threads()
    gevent.sleep(0.1)
    try:
        jump_to_node_bootloader()
        RaceContext.interface.close_fwupd_serial_port()
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
    if RaceContext.race.num_nodes <= 0:
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

    if RaceContext.vrx_manager.isEnabled():
        # TODO: RaceContext.vrx_manager.setDeviceMethod(device_id, method)
        # TODO: RaceContext.vrx_manager.setDevicePilot(device_id, pilot_id)

        RaceContext.vrx_manager.setDeviceSeat(vrx_id, node)

        # vrx_controller.set_seat_number(serial_num=vrx_id, desired_seat_num=node)
        logger.info("Set VRx {0} to node {1}".format(vrx_id, node))
    else:
        logger.error("Can't set VRx {0} to node {1}: Controller unavailable".format(vrx_id, node))

#
# Program Functions
#

def heartbeat_thread_function():
    '''Emits current rssi data, etc'''
    gevent.sleep(0.010)  # allow time for connection handshake to terminate before emitting data

    while True:
        try:
            node_data = RaceContext.interface.get_heartbeat_json()

            SOCKET_IO.emit('heartbeat', node_data)
            heartbeat_thread_function.iter_tracker += 1

            # update displayed IMD rating after freqs changed:
            if heartbeat_thread_function.imdtabler_flag and \
                    (heartbeat_thread_function.iter_tracker % HEARTBEAT_DATA_RATE_FACTOR) == 0:
                heartbeat_thread_function.imdtabler_flag = False
                RaceContext.rhui.emit_imdtabler_rating(IMDTABLER_JAR_NAME)

            # emit rest of node data, but less often:
            if (heartbeat_thread_function.iter_tracker % (4*HEARTBEAT_DATA_RATE_FACTOR)) == 0:
                RaceContext.rhui.emit_node_data()

            # emit cluster status less often:
            if (heartbeat_thread_function.iter_tracker % (4*HEARTBEAT_DATA_RATE_FACTOR)) == (2*HEARTBEAT_DATA_RATE_FACTOR):
                RaceContext.rhui.emit_cluster_status()

            # collect vrx lock status
            if (heartbeat_thread_function.iter_tracker % (10*HEARTBEAT_DATA_RATE_FACTOR)) == 0:
                if RaceContext.vrx_manager.isEnabled():
                    RaceContext.vrx_manager.updateStatus()

            if (heartbeat_thread_function.iter_tracker % (10*HEARTBEAT_DATA_RATE_FACTOR)) == 4:
                # emit display status with offset
                if RaceContext.vrx_manager.isEnabled():
                    RaceContext.rhui.emit_vrx_list()

            # emit environment data less often:
            if (heartbeat_thread_function.iter_tracker % (20*HEARTBEAT_DATA_RATE_FACTOR)) == 0:
                RaceContext.sensors.update_environmental_data()
                RaceContext.rhui.emit_environmental_data()

            # log environment data occasionally:
            if (heartbeat_thread_function.iter_tracker % (Config.GENERAL['LOG_SENSORS_DATA_RATE']*HEARTBEAT_DATA_RATE_FACTOR)) == 0:
                if RaceContext.sensors.sensors_dict:
                    logger.info("Sensor snapshot:")
                    for name, obj in RaceContext.sensors.sensors_dict.items():
                        logger.info(f"{name}: {obj.getReadings()}")

            time_now = monotonic()

            # check if race is to be started
            if RaceContext.race.scheduled:
                if time_now > RaceContext.race.scheduled_time:
                    on_stage_race()
                    RaceContext.race.scheduled = False

            # if any comm errors then log them (at defined intervals; faster if debug mode)
            if time_now > heartbeat_thread_function.last_error_rep_time + \
                        (ERROR_REPORT_INTERVAL_SECS if not Config.GENERAL['DEBUG'] \
                        else ERROR_REPORT_INTERVAL_SECS/10):
                heartbeat_thread_function.last_error_rep_time = time_now
                rep_str = RaceContext.interface.get_intf_error_report_str()
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
    ''' Monitor system clock and adjust 'program_start_epoch_time' if significant jump detected.
        (This can happen if NTP synchronization occurs after server starts up.) '''
    try:
        while True:
            gevent.sleep(10)
            if RaceContext.race.any_races_started:  # stop monitoring after any race started
                break
            epoch_now = int((RHTimeFns.getUtcDateTimeNow() - EPOCH_START).total_seconds() * 1000)
            diff_ms = epoch_now - RaceContext.serverstate.monotonic_to_epoch_millis(monotonic())
            if abs(diff_ms) > 30000:
                _epoch1 = (RHTimeFns.getUtcDateTimeNow() - EPOCH_START).total_seconds()
                time_now = monotonic()
                # do average of before and after to exact timing match
                _epoch2 = (RHTimeFns.getUtcDateTimeNow() - EPOCH_START).total_seconds()
                # current time, in milliseconds since 1970-01-01
                epoch_now = int((_epoch1 + _epoch2) * 500.0 + 0.5)   # *1000/2.0
                diff_ms = epoch_now - RaceContext.serverstate.monotonic_to_epoch_millis(time_now)
                RaceContext.serverstate.program_start_epoch_time += diff_ms
                RaceContext.serverstate.mtonic_to_epoch_millis_offset = RaceContext.serverstate.program_start_epoch_time - \
                                                                        1000.0*RaceContext.serverstate.program_start_mtonic
                logger.info("Adjusting 'program_start_epoch_time' for shift in system clock ({:.1f} secs) to: {:.0f}, time={}".\
                            format(diff_ms/1000, RaceContext.serverstate.program_start_epoch_time, \
                                   RHTimeFns.epochMsToFormattedStr(RaceContext.serverstate.program_start_epoch_time)))
                # update values that will be reported if running as cluster timer
                if RaceContext.cluster.has_joined_cluster():
                    logger.debug("Emitting 'join_cluster_response' message with updated 'prog_start_epoch'")
                    RaceContext.cluster.emit_join_cluster_response(SOCKET_IO, RaceContext.serverstate.info_dict)
    except KeyboardInterrupt:
        logger.info("clock_check_thread terminated by keyboard interrupt")
        raise
    except SystemExit:
        raise
    except Exception:
        logger.exception('Exception in clock_check_thread')

def ms_from_race_start():
    '''Return milliseconds since race start.'''
    delta_time = monotonic() - RaceContext.race.start_time_monotonic
    milli_sec = delta_time * 1000.0
    return milli_sec

def ms_to_race_start():
    '''Return milliseconds since race start.'''
    if RaceContext.race.scheduled:
        delta_time = monotonic() - RaceContext.race.scheduled_time
        milli_sec = delta_time * 1000.0
        return milli_sec
    else:
        return None

def ms_from_program_start():
    '''Returns the elapsed milliseconds since the start of the program.'''
    delta_time = monotonic() - RaceContext.serverstate.program_start_mtonic
    milli_sec = delta_time * 1000.0
    return milli_sec

def pass_record_callback(node, lap_timestamp_absolute, source):
    RaceContext.race.pass_invoke_func_queue_obj.put(RaceContext.race.add_lap, node, lap_timestamp_absolute, source)

@catchLogExcDBCloseWrapper
def new_enter_or_exit_at_callback(node, is_enter_at_flag):
    gevent.sleep(0.025)  # delay to avoid potential I/O error
    if is_enter_at_flag:
        logger.info('Finished capture of enter-at level for node {0}, level={1}, count={2}'.format(node.index+1, node.enter_at_level, node.cap_enter_at_count))
        RaceContext.calibration.set_enter_at_level(node.index, node.enter_at_level)
        RaceContext.rhui.emit_enter_at_level(node)
    else:
        logger.info('Finished capture of exit-at level for node {0}, level={1}, count={2}'.format(node.index+1, node.exit_at_level, node.cap_exit_at_count))
        RaceContext.calibration.set_exit_at_level(node.index, node.exit_at_level)
        RaceContext.rhui.emit_exit_at_level(node)

@catchLogExcDBCloseWrapper
def node_crossing_callback(node):
    RaceContext.rhui.emit_node_crossing_change(node)
    # handle LED gate-status indicators:

    if RaceContext.race.race_status == RaceStatus.RACING:  # if race is in progress
        # if pilot assigned to node and first crossing is complete
        if RaceContext.race.format is RaceContext.serverstate.secondary_race_format or (
            node.current_pilot_id != RHUtils.PILOT_ID_NONE and node.first_cross_flag):
            # first crossing has happened; if 'enter' then show indicator,
            #  if first event is 'exit' then ignore (because will be end of first crossing)
            if node.crossing_flag:
                Events.trigger(Evt.CROSSING_ENTER, {
                    'nodeIndex': node.index,
                    'color': RaceContext.race.seat_colors[node.index]
                    })
                node.show_crossing_flag = True
            else:
                if node.show_crossing_flag:
                    Events.trigger(Evt.CROSSING_EXIT, {
                        'nodeIndex': node.index,
                        'color': RaceContext.race.seat_colors[node.index]
                        })
                else:
                    node.show_crossing_flag = True

def default_frequencies():
    '''Set node frequencies, R1367 for 4, IMD6C+ for 5+.'''
    if RaceContext.race.num_nodes < 5:
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

        while RaceContext.race.num_nodes > len(freqs['f']):
            freqs['b'].append(None)
            freqs['c'].append(None)
            freqs['f'].append(RHUtils.FREQUENCY_ID_NONE)

    return freqs

def assign_frequencies():
    '''Assign frequencies to nodes'''
    profile = RaceContext.race.profile
    freqs = json.loads(profile.frequencies)

    for idx in range(RaceContext.race.num_nodes):
        RaceContext.interface.set_frequency(idx, freqs["f"][idx])
        RaceContext.race.clear_results()
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
    RaceContext.rhdata.db_init(nofill)
    RaceContext.race.reset_current_laps()
    RaceContext.race.format = RaceContext.rhdata.get_first_raceFormat()
    RaceContext.rhui.emit_current_laps()
    assign_frequencies()
    Events.trigger(Evt.DATABASE_INITIALIZE)
    logger.info('Database initialized')

def db_reset():
    '''Resets database.'''
    RaceContext.rhdata.reset_all()
    RaceContext.race.reset_current_laps()
    RaceContext.race.format = RaceContext.rhdata.get_first_raceFormat()
    RaceContext.rhui.emit_current_laps()
    assign_frequencies()
    logger.info('Database reset')

def expand_heats():
    ''' ensure loaded data includes enough slots for current nodes '''
    for heat in RaceContext.rhdata.get_heats():
        heatNodes = RaceContext.rhdata.get_heatNodes_by_heat(heat.id)
        while len(heatNodes) < RaceContext.race.num_nodes:
            heatNodes = RaceContext.rhdata.get_heatNodes_by_heat(heat.id)
            RaceContext.rhdata.add_heatNode(heat.id, None)

def init_race_state():
    expand_heats()

    # Send profile values to nodes
    on_set_profile({'profile': RaceContext.race.profile.id}, False)

    # Init laps
    RaceContext.race.reset_current_laps()

    # Set current heat
    RaceContext.race.set_heat(RaceContext.rhdata.get_initial_heat_id(), force=True)

    # Normalize results caches
    RaceContext.pagecache.set_valid(False)

def init_interface_state(startup=False):
    # Cancel current race
    if startup:
        RaceContext.race.race_status = RaceStatus.READY # Go back to ready state
        RaceContext.interface.set_race_status(RaceStatus.READY)
        Events.trigger(Evt.LAPS_CLEAR)
        RaceContext.race.timer_running = False # indicate race timer not running
        RaceContext.race.scheduled = False # also stop any deferred start
        SOCKET_IO.emit('stop_timer')
    else:
        on_discard_laps()
    # Reset laps display
    RaceContext.race.reset_current_laps()

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
    if "bitmapRHLogo" in RaceContext.led_manager.getRegisteredEffects() and Config.LED['LED_ROWS'] > 1:
        effects[Evt.STARTUP] = "bitmapRHLogo"
        effects[Evt.RACE_STAGE] = "bitmapOrangeEllipsis"
        effects[Evt.RACE_START] = "bitmapGreenArrow"
        effects[Evt.RACE_FINISH] = "bitmapCheckerboard"
        effects[Evt.RACE_STOP] = "bitmapRedX"

    # update with DB values (if any)
    effect_opt = RaceContext.rhdata.get_option('ledEffects')
    if effect_opt:
        effects.update(json.loads(effect_opt))
    # set effects
    RaceContext.led_manager.setEventEffect("manualColor", "stripColor")
    for item in effects:
        RaceContext.led_manager.setEventEffect(item, effects[item])


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
        RaceContext.interface.jump_to_bootloader()
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
            if (HEARTBEAT_THREAD is None) and BACKGROUND_THREADS_ENABLED and RaceContext.interface:
                idleCntr += 1
                if idleCntr >= 74:
                    if idleCntr >= 80:
                        idleCntr = 0    # show pattern on node LED via messages
                    if (not bStatFlg) and (idleCntr % 2 == 0):
                        RaceContext.interface.send_server_idle_message()
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
    RaceContext.interface.send_shutdown_button_state(1)

def shutdown_button_released(longPressReachedFlag):
    logger.debug("Detected shutdown button released, longPressReachedFlag={}".\
                format(longPressReachedFlag))
    if not longPressReachedFlag:
        RaceContext.interface.send_shutdown_button_state(0)

def shutdown_button_long_press():
    logger.info("Detected shutdown button long press; performing shutdown now")
    on_shutdown_pi()

def _do_init_rh_interface():
    try:
        rh_interface_name = os.environ.get('RH_INTERFACE', 'RH') + "Interface"
        try:
            logger.debug("Initializing interface module: " + rh_interface_name)
            interfaceModule = importlib.import_module(rh_interface_name)
            RaceContext.interface = interfaceModule.get_hardware_interface(config=Config, \
                            isS32BPillFlag=RHUtils.is_S32_BPill_board(), **hardwareHelpers)
            # if no nodes detected, system is RPi, not S32_BPill, and no serial port configured
            #  then check if problem is 'smbus2' or 'gevent' lib not installed
            if RaceContext.interface and ((not RaceContext.interface.nodes) or len(RaceContext.interface.nodes) <= 0) and \
                        RHUtils.is_sys_raspberry_pi() and (not RHUtils.is_S32_BPill_board()) and \
                        ((not Config.SERIAL_PORTS) or len(Config.SERIAL_PORTS) <= 0):
                try:
                    importlib.import_module('smbus2')
                    importlib.import_module('gevent')
                except ImportError:
                    logger.warning("Unable to import libraries for I2C nodes; try:  " +\
                                   "pip install --upgrade --no-cache-dir -r requirements.txt")
                    set_ui_message(
                        'i2c',
                        __("Unable to import libraries for I2C nodes. Try: <code>pip install --upgrade --no-cache-dir -r requirements.txt</code>"),
                        header='Warning',
                        subclass='no-library'
                        )
                RaceContext.race.num_nodes = 0
                RaceContext.interface.pass_record_callback = pass_record_callback
                RaceContext.interface.new_enter_or_exit_at_callback = new_enter_or_exit_at_callback
                RaceContext.interface.node_crossing_callback = node_crossing_callback
                return True
        except (ImportError, RuntimeError, IOError) as ex:
            logger.info('Unable to initialize nodes via ' + rh_interface_name + ':  ' + str(ex))
        if (not RaceContext.interface) or (not RaceContext.interface.nodes) or len(RaceContext.interface.nodes) <= 0:
            if (not Config.SERIAL_PORTS) or len(Config.SERIAL_PORTS) <= 0:
                interfaceModule = importlib.import_module('MockInterface')
                RaceContext.interface = interfaceModule.get_hardware_interface(config=Config, **hardwareHelpers)
                for node in RaceContext.interface.nodes:  # put mock nodes at latest API level
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
                    if RaceContext.interface:
                        if not (getattr(RaceContext.interface, "get_info_node_obj") and RaceContext.interface.get_info_node_obj()):
                            logger.info("Unable to initialize serial node(s): {0}".format(Config.SERIAL_PORTS))
                            logger.info("If an S32_BPill board is connected, its processor may need to be flash-updated")
                            # enter serial port name so it's available for node firmware update
                            if getattr(RaceContext.interface, "set_mock_fwupd_serial_obj"):
                                RaceContext.interface.set_mock_fwupd_serial_obj(Config.SERIAL_PORTS[0])
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

        RaceContext.race.num_nodes = len(RaceContext.interface.nodes)  # save number of nodes found
        # set callback functions invoked by interface module
        RaceContext.interface.pass_record_callback = pass_record_callback
        RaceContext.interface.new_enter_or_exit_at_callback = new_enter_or_exit_at_callback
        RaceContext.interface.node_crossing_callback = node_crossing_callback
        RaceContext.rhui._interface = RaceContext.interface  #pylint: disable=protected-access
        return True
    except:
        logger.exception("Error initializing RH interface")
        return False

def initialize_rh_interface():
    if not _do_init_rh_interface():
        return False
    if RaceContext.race.num_nodes == 0:
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
    RaceContext.serverstate.release_version = RELEASE_VERSION
    RaceContext.serverstate.server_api_version = SERVER_API
    RaceContext.serverstate.json_api_version = JSON_API
    RaceContext.serverstate.node_api_best = NODE_API_BEST
    RaceContext.serverstate.build_info()

# Log server/node information
def reportServerInfo():
    logger.debug("Server info:  " + json.dumps(RaceContext.serverstate.info_dict))
    if RaceContext.serverstate.node_api_match is False:
        logger.info('** WARNING: Node API mismatch **')
        set_ui_message('node-match',
            __("Node versions do not match and may not function similarly"), header='Warning')
    if RaceContext.race.num_nodes > 0:
        if RaceContext.serverstate.node_api_lowest < NODE_API_SUPPORTED:
            logger.info('** WARNING: Node firmware is out of date and may not function properly **')
            msgStr = __("Node firmware is out of date and may not function properly")
            if RaceContext.interface.get_fwupd_serial_name() != None:
                msgStr += ". " + __("If an S32_BPill board is connected, you should") + \
                          " <a href=\"/updatenodes\">" + __("flash-update") + "</a> " + \
                          __("its processor.")
            set_ui_message('node-obs', msgStr, header='Warning', subclass='api-not-supported')
        elif RaceContext.serverstate.node_api_lowest < NODE_API_BEST:
            logger.info('** NOTICE: Node firmware update is available **')
            msgStr = __("Node firmware update is available")
            if RaceContext.interface.get_fwupd_serial_name() != None:
                msgStr += ". " + __("If an S32_BPill board is connected, you should") + \
                          " <a href=\"/updatenodes\">" + __("flash-update") + "</a> " + \
                          __("its processor.")
            set_ui_message('node-old', msgStr, header='Notice', subclass='api-low')
        elif RaceContext.serverstate.node_api_lowest > NODE_API_BEST:
            logger.warning('** WARNING: Node firmware is newer than this server version supports **')
            set_ui_message('node-newer',
                __("Node firmware is newer than this server version and may not function properly"),
                header='Warning', subclass='api-high')

def check_req_entry(req_line, module_name):
    installed_ver = importlib.metadata.version(module_name)
    required_ver = req_line[req_line.index('==')+2 : req_line.rindex('.')]
    if not installed_ver.startswith(required_ver):
        logger.warning(__("Package '{}' version mismatch: Required {}, but {} installed").format( \
                                                module_name, required_ver, installed_ver))
        return 1
    return 0

def check_requirements():
    try:
        import importlib.metadata  # @UnusedImport pylint: disable=redefined-outer-name
        chk_list = [['Flask==','flask'], ['Flask-SocketIO==','flask_socketio'], \
                    ['Flask_SocketIO==','flask_socketio'], \
                    ['flask_sqlalchemy==','flask_sqlalchemy'], ['gevent==','gevent'], \
                    ['gevent-websocket==','gevent-websocket'], ['monotonic==','monotonic'], \
                    ['requests==','requests']]
        num_mismatched = 0
        with open('requirements.txt') as rf:
            for line in rf.readlines():
                for entry in chk_list:
                    if line.startswith(entry[0]):
                        num_mismatched += check_req_entry(line, entry[1])
        if num_mismatched > 0:
            if RHUtils.is_sys_raspberry_pi():
                logger.warning(__('Try "pip install --upgrade --no-cache-dir -r requirements.txt"'))
            set_ui_message('check_reqs',
                __("Package-version mismatches detected. Try: <code>pip install --upgrade --no-cache-dir -r requirements.txt</code>"),
                header='Warning', subclass='none')
    except ModuleNotFoundError as ex:
        logger.debug("Unable to check package requirements: {}".format(ex))
    except:
        logger.exception("Error checking package requirements")

#
# Program Initialize
#

logger.info('Release: {0} / Server API: {1} / Latest Node API: {2}'.format(RELEASE_VERSION, SERVER_API, NODE_API_BEST))
logger.debug('Program started at {:.0f}, time={}'.format(RaceContext.serverstate.program_start_epoch_time,
                                                         RHTimeFns.epochMsToFormattedStr(RaceContext.serverstate.program_start_epoch_time)))
RHUtils.idAndLogSystemInfo()

check_requirements()

determineHostAddress(2)  # attempt to determine IP address, but don't wait too long for it

# RotorHazard events dispatch
Events.on(Evt.UI_DISPATCH, 'ui_dispatch_event', RaceContext.rhui.dispatch_quickbuttons, {}, 50)

# Plugin handling
class plugin():
    def __init__(self, name):
        self.name = name
        self.module = None
        self.meta = None
        self.enabled = True #TODO: remove temporary default-enable of all plugins
        self.loaded = False
        self.load_issue = None
        self.load_issue_detail = None

plugin_modules = []
if os.path.isdir('./plugins'):
    dirs = [f.name for f in os.scandir('./plugins') if f.is_dir()]
    for name in dirs:
        plugin_modules.append(plugin(name))
else:
    logger.warning('No plugins directory found.')

def load_plugin(plugin):
    if not plugin.enabled:
        plugin.load_issue = "disabled"
        return False

    try:
        with open(F'plugins/{plugin.name}/manifest.json', 'r') as f:
            meta = json.load(f)

        if isinstance(meta, dict):
            plugin.meta = meta
    except:
        logger.info('No plugin metadata found for {}'.format(plugin.name))

    try:
        plugin.module = importlib.import_module('plugins.' + plugin.name)
        if not plugin.module.__file__:
            plugin.load_issue = "unable to load file"
            return False
    except ModuleNotFoundError as ex1:
        plugin.load_issue = str(ex1)
        return False
    except Exception as ex2:
        plugin.load_issue = "not supported or may require additional dependencies"
        plugin.load_issue_detail = ex2
        return False

    version_major = 1
    version_minor = 0

    if plugin.meta:
        try:
            version = plugin.meta.get('required_rhapi_version').split('.')
            version_major = int(version[0])
            version_minor = int(version[1])
        except:
            logger.debug("Can't parse API declaration for plugin '{}', assuming 1.0".format(plugin.name))

    if version_major > RHAPI.API_VERSION_MAJOR:
        plugin.load_issue = "required RHAPI version is newer than this server"
        return False

    if version_major == RHAPI.API_VERSION_MAJOR and version_minor > RHAPI.API_VERSION_MINOR:
        plugin.load_issue = "required RHAPI version is newer than this server"
        return False

    if 'initialize' not in dir(plugin.module) or not callable(getattr(plugin.module, 'initialize')):
        plugin.load_issue = "no initialize function"
        return False

    plugin.module.initialize(RHAPI)
    return True

for plugin in plugin_modules:
    if load_plugin(plugin):
        logger.info("Loaded plugin '{}'".format(plugin.name))
        plugin.loaded = True
    else:
        if plugin.load_issue_detail:
            logger.info("Plugin '{}' not loaded ({}; Ex: {})".format(plugin.name, plugin.load_issue, plugin.load_issue_detail))
        else:
            logger.info("Plugin '{}' not loaded ({})".format(plugin.name, plugin.load_issue))

RaceContext.serverstate.plugins = plugin_modules

if (not RHUtils.is_S32_BPill_board()) and Config.GENERAL['FORCE_S32_BPILL_FLAG']:
    RHUtils.set_S32_BPill_boardFlag()
    logger.info("Set S32BPillBoardFlag in response to FORCE_S32_BPILL_FLAG in config")

logger.debug("isRPi={}, isRealGPIO={}, isS32BPill={}".format(RHUtils.is_sys_raspberry_pi(), \
                                         RHUtils.get_GPIO_type_str(), RHUtils.is_S32_BPill_board()))
if RHUtils.is_sys_raspberry_pi() and not RHUtils.is_real_hw_GPIO():
    logger.warning("Unable to access real GPIO on Pi; libraries may need to be installed")
    set_ui_message(
        'gpio',
        __("Unable to access real GPIO on Pi libraries may need to be installed"),
        header='Warning',
        subclass='no-access'
        )

# log results of module initializations
Config.logInitResultMessage()
RaceContext.language.logInitResultMessage()

# check if current log file owned by 'root' and change owner to 'pi' user if so
if Current_log_path_name and RHUtils.checkSetFileOwnerPi(Current_log_path_name):
    logger.debug("Changed log file owner from 'root' to 'pi' (file: '{0}')".format(Current_log_path_name))
    RHUtils.checkSetFileOwnerPi(log.LOG_DIR_NAME)  # also make sure 'log' dir not owned by 'root'

logger.info("Using log file: {0}".format(Current_log_path_name))

if RHUtils.is_sys_raspberry_pi() and RHUtils.is_S32_BPill_board():
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

initRhResultFlag = initialize_rh_interface()
if not initRhResultFlag:
    log.wait_for_queue_empty()
    sys.exit(1)

if len(sys.argv) > 0:
    if CMDARG_JUMP_TO_BL_STR in sys.argv:
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
    if CMDARG_VIEW_DB_STR in sys.argv:
        try:
            viewdbArgIdx = sys.argv.index(CMDARG_VIEW_DB_STR) + 1
            RaceContext.rhdata.backup_db_file(True)
            logger.info("Loading given database file: {}".format(sys.argv[viewdbArgIdx]))
            restoreDbResultFlag = restore_database_file(sys.argv[viewdbArgIdx])
        except Exception as ex:
            logger.error("Error loading database file: {}".format(ex))
            restoreDbResultFlag = False
        if not restoreDbResultFlag:
            sys.exit(1)

RaceContext.cluster = ClusterNodeSet(RaceContext.language, Events)
hasMirrors = False
secondary = None
try:
    for sec_idx, secondary_info in enumerate(Config.GENERAL['SECONDARIES']):
        if isinstance(secondary_info, str):
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
        secondary = SecondaryNode(sec_idx, secondary_info, RaceContext, RaceContext.serverstate.monotonic_to_epoch_millis,
                                  RELEASE_VERSION, secondary)
        RaceContext.cluster.addSecondary(secondary)
except:
    logger.exception("Error adding secondary to cluster")
    set_ui_message(
        'secondary',
        __('Secondary configuration is invalid.'),
        header='Error',
        subclass='error'
        )

if RaceContext.cluster and RaceContext.cluster.hasRecEventsSecondaries():
    RaceContext.cluster.init_repeater()

if RaceContext.race.num_nodes > 0:
    logger.info('Number of nodes found: {0}'.format(RaceContext.race.num_nodes))
    # if I2C nodes then only report comm errors if > 1.0%
    if hasattr(RaceContext.interface.nodes[0], 'i2c_addr'):
        RaceContext.interface.set_intf_error_report_percent_limit(1.0)

# Delay to get I2C addresses through interface class initialization
gevent.sleep(0.500)

try:
    RaceContext.sensors.discover(config=Config.SENSORS, **hardwareHelpers)
except Exception:
    logger.exception("Exception while discovering sensors")

# if no DB file then create it now (before "__()" fn used in 'buildServerInfo()')
db_inited_flag = False
if not os.path.exists(DB_FILE_NAME):
    logger.info("No '{0}' file found; creating initial database".format(DB_FILE_NAME))
    db_init()
    db_inited_flag = True
    RaceContext.rhdata.primeCache() # Ready the Options cache

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
RHAPI.server_info = RaceContext.serverstate.info_dict

# Do data consistency checks
if not db_inited_flag:
    try:
        RaceContext.rhdata.primeCache() # Ready the Options cache

        if not RaceContext.rhdata.check_integrity():
            RaceContext.rhdata.recover_database(DB_FILE_NAME, startup=True)
            clean_results_cache()

    except Exception as ex:
        logger.warning('Clearing all data after recovery failure:  ' + str(ex))
        db_reset()

# Create LED object with appropriate configuration
strip = None
if Config.LED['LED_COUNT'] > 0:
    led_type = os.environ.get('RH_LEDS', 'ws281x')
    # note: any calls to 'RaceContext.rhdata.get_option()' need to happen after the DB initialization,
    #       otherwise it causes problems when run with no existing DB file
    led_brightness = RaceContext.rhdata.get_optionInt("ledBrightness")
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
        RaceContext.led_manager = LEDEventManager(Events, strip, RaceContext, RHAPI)
        init_LED_effects()
    except:
        logger.exception("Error initializing LED support")
        RaceContext.led_manager = NoLEDManager()
elif RaceContext.cluster and RaceContext.cluster.hasRecEventsSecondaries():
    RaceContext.led_manager = ClusterLEDManager(Events)
    init_LED_effects()
else:
    RaceContext.led_manager = NoLEDManager()

# leaderboard ranking managers
RaceContext.race_points_manager = Results.RacePointsManager(RHAPI, Events)
RaceContext.raceclass_rank_manager = Results.RaceClassRankManager(RHAPI, Events)

# Initialize internal state with database
# DB session commit needed to prevent 'application context' errors
try:
    init_race_state()
except Exception:
    logger.exception("Exception in 'init_race_state()'")
    log.wait_for_queue_empty()
    sys.exit(1)

# internal secondary race format for LiveTime (needs to be created after initial DB setup)
RaceContext.serverstate.secondary_race_format = RHRace.RHRaceFormat(name=__("Secondary"),
                         unlimited_time=1,
                         race_time_sec=0,
                         lap_grace_sec=-1,
                         staging_fixed_tones=0,
                         start_delay_min_ms=0,
                         start_delay_max_ms=0,
                         staging_delay_tones=0,
                         number_laps_win=0,
                         win_condition=WinCondition.NONE,
                         team_racing_mode=False,
                         start_behavior=0,
                         points_method=None)

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

# VRx Controllers
RaceContext.vrx_manager = VRxControlManager(Events, RaceContext, RHAPI, legacy_config=Config.VRX_CONTROL)
Events.on(Evt.CLUSTER_JOIN, 'VRx', RaceContext.vrx_manager.kill)

# data exporters
RaceContext.export_manager = DataExportManager(RHAPI, Events)
RaceContext.import_manager = DataImportManager(RHAPI, RaceContext, Events)

# heat generators
RaceContext.heat_generate_manager = HeatGeneratorManager(RaceContext, RHAPI, Events)

gevent.spawn(clock_check_thread_function)  # start thread to monitor system clock

# register endpoints
APP.register_blueprint(json_endpoints.createBlueprint(RaceContext, RaceContext.serverstate.info_dict))

#register event actions
EventActionsObj = EventActions.EventActions(Events, RaceContext)

# make event actions available to cluster/secondary timers
RaceContext.cluster.setEventActionsObj(EventActionsObj)

@catchLogExceptionsWrapper
def start(port_val=Config.GENERAL['HTTP_PORT'], argv_arr=None):
    if not RaceContext.rhdata.get_option("secret_key"):
        RaceContext.rhdata.set_option("secret_key", ''.join(random.choice(string.ascii_letters) for _ in range(50)))

    APP.config['SECRET_KEY'] = RaceContext.rhdata.get_option("secret_key")
    logger.info("Running http server at port " + str(port_val))
    init_interface_state(startup=True)
    Events.trigger(Evt.STARTUP, {
        'color': ColorVal.ORANGE,
        'message': 'RotorHazard ' + RELEASE_VERSION
        })

    # handle launch-browser arguments ("... [pagename] [browsercmd]")
    if argv_arr and len(argv_arr) > 0:
        launchbIdx = 0
        if CMDARG_VIEW_DB_STR in argv_arr:
            vArgIdx = argv_arr.index(CMDARG_VIEW_DB_STR) + 1
            if len(argv_arr) > vArgIdx + 1 and (not argv_arr[vArgIdx+1].startswith("--")):
                launchbIdx = vArgIdx         # if 'pagename' arg given then launch browser (below)
        if launchbIdx == 0 and CMDARG_LAUNCH_B_STR in argv_arr:
            launchbIdx = argv_arr.index(CMDARG_LAUNCH_B_STR)
        if launchbIdx > 0:
            if len(argv_arr) > launchbIdx + 1 and (not argv_arr[launchbIdx+1].startswith("--")):
                pageStr = argv_arr[launchbIdx+1]
                if not pageStr.startswith('/'):
                    pageStr = '/' +  pageStr
            else:
                pageStr = None
            cmdStr = argv_arr[launchbIdx+2] if len(argv_arr) > launchbIdx+2 and \
                            (not argv_arr[launchbIdx+2].startswith("--")) else None
            start_background_threads(True)
            RaceContext.pagecache.update_cache()
            gevent.spawn_later(2, RHUtils.launchBrowser, "http://localhost", \
                               port_val, pageStr, cmdStr)

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
    rep_str = RaceContext.interface.get_intf_error_report_str(True)
    if rep_str:
        logger.log((logging.INFO if RaceContext.interface.get_intf_total_error_count() else logging.DEBUG), rep_str)
    stop_background_threads()
    log.wait_for_queue_empty()
    gevent.sleep(2)  # allow system shutdown command to run before program exit
    log.close_logging()

# Start HTTP server
if __name__ == '__main__':
    start(argv_arr=sys.argv)