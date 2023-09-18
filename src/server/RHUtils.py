'''
RotorHazard Helper and utility functions
'''

import os
import sys
import re
import logging
import platform
import subprocess
import glob
import socket
import random
import json

logger = logging.getLogger(__name__)

DEF_TEAM_NAME = 'A'  # default team
PILOT_ID_NONE = 0  # indicator value for no pilot configured
HEAT_ID_NONE = 0  # indicator value for practice heat
CLASS_ID_NONE = 0  # indicator value for unclassified heat
FORMAT_ID_NONE = 0  # indicator value for unformatted class
FREQUENCY_ID_NONE = 0       # indicator value for node disabled
IS_SYS_RASPBERRY_PI = True  # set by 'idAndLogSystemInfo()'

def time_format(millis, timeformat='{m}:{s}.{d}'):
    '''Convert milliseconds to 00:00.000'''
    if millis is None:
        return ''

    millis = int(round(millis, 0))
    minutes = millis // 60000
    over = millis % 60000
    seconds = over // 1000
    over = over % 1000
    milliseconds = over

    if not timeformat:
        timeformat = '{m}:{s}.{d}'

    return timeformat.format(m=str(minutes), s=str(seconds).zfill(2), d=str(milliseconds).zfill(3))

def split_time_format(millis, timeformat='{m}:{s}.{d}'):
    '''Convert milliseconds to 00:00.000 with leading zeros removed'''
    if millis is None:
        return ''
    s = time_format(millis, timeformat)
    if len(s) > 3 and s.startswith("0:"):
        p = 3 if s[2] == '0' else 2
        s = s[p:]
    return s

def phonetictime_format(millis, timeformat='{m} {s}.{d}'):
    '''Convert milliseconds to phonetic'''
    if millis is None:
        return ''

    millis = int(millis + 50)  # round to nearest tenth of a second
    minutes = millis // 60000
    over = millis % 60000
    seconds = over // 1000
    over = over % 1000
    tenths = over // 100

    if not timeformat:
        timeformat = '{m} {s}.{d}'

    if minutes <= 0:
        return timeformat.format(m='', s=str(seconds), d=str(tenths))
    else:
        return timeformat.format(m=str(minutes), s=str(seconds).zfill(2), d=str(tenths))

def getPythonVersionStr():
    return sys.version.split()[0]

def checkVersionStr(verStr, majorVer, minorVer):
    verList = verStr.split('.')
    return int(verList[0]) >= int(majorVer) and int(verList[1]) >= int(minorVer)

def idAndLogSystemInfo():
    global IS_SYS_RASPBERRY_PI
    IS_SYS_RASPBERRY_PI = False
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
        logger.info("Host OS: {} {}".format(platform.system(), platform.release()))
        logger.info("Python version: {}".format(getPythonVersionStr()))
    except Exception:
        logger.exception("Error in 'idAndLogSystemInfo()'")

def isSysRaspberryPi():
    return IS_SYS_RASPBERRY_PI

# Returns "primary" IP address for local host.  Based on:
#  https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
#  and https://stackoverflow.com/questions/24196932/how-can-i-get-the-ip-address-from-nic-in-python
def getLocalIPAddress():
    try:
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        finally:
            if s:
                s.close()
    except:
        IP = None
    if IP:
        return IP
    # use alternate method that does not rely on internet access
    ips = subprocess.check_output(['hostname', '--all-ip-addresses']).decode("utf-8").rstrip()
    logger.debug("Result of 'hostname --all-ip-addresses': " + str(ips))
    if ips:
        for IP in ips.split(' '):
            if IP.find('.') > 0 and not IP.startswith("127."):
                return IP
    raise RuntimeError("Unable to determine IP address via 'hostname' command")

# Substitutes asterisks in the IP address 'destAddrStr' with values from the IP address
#  fetched via the given 'determineHostAddressFn' function.
def substituteAddrWildcards(determineHostAddressFn, destAddrStr):
    try:
        if determineHostAddressFn and destAddrStr and destAddrStr.find('*') >= 0:
            colonPos = destAddrStr.find(':')  # find position of port specifier (i.e., ":5000")
            if colonPos <= 0:
                colonPos = len(destAddrStr)
            sourceAddrStr = determineHostAddressFn()
            # single "*" == full substitution
            if destAddrStr[:colonPos] == "*":
                return sourceAddrStr + destAddrStr[colonPos:]
            sourceParts = sourceAddrStr.split('.')
            destParts = destAddrStr.split('.')
            # ("192.168.0.130", "*.*.*.97") => "192.168.0.97"
            if len(sourceParts) == len(destParts):
                for i in range(len(destParts)):
                    if destParts[i] == "*":
                        destParts[i] = sourceParts[i]
                return '.'.join(destParts)
            # ("192.168.0.130", "*.97") => "192.168.0.97"
            elif len(destParts) == 2 and len(sourceParts) == 4 and destParts[0] == "*":
                return '.'.join(sourceParts[:-1]) + '.' + destParts[1]
    except Exception:
        logger.exception("Error in 'substituteAddrWildcards()'")
    return destAddrStr

# Checks if given file or directory is owned by 'root' and changes owner to 'pi' user if so.
# Returns True if owner changed to 'pi' user; False if not.
def checkSetFileOwnerPi(fileNameStr):
    try:
        if IS_SYS_RASPBERRY_PI:
            # check that 'pi' user exists, file/dir exists, and owner is 'root'
            if os.path.isdir("/home/pi") and os.path.exists(fileNameStr) and os.stat(fileNameStr).st_uid == 0:
                subprocess.check_call(["sudo", "chown", "pi:pi", fileNameStr])
                if os.stat(fileNameStr).st_uid != 0:
                    if os.path.isdir(fileNameStr):  # if dir then also apply to files in dir
                        file_list = list(filter(os.path.isfile, glob.glob(fileNameStr + "/*.*")))
                        for chk_path in file_list:
                            checkSetFileOwnerPi(chk_path)
                    return True
                logger.info("Unable to change owner in 'checkSetFileOwnerPi()': " + fileNameStr)
    except Exception:
        logger.exception("Error in 'checkSetFileOwnerPi()'")
    return False

# Scans the given binary-data string for a "prefixed" substring and returns the substring.
#  dataStr format:  b'PREFIXSTR: substr\0'
def findPrefixedSubstring(dataStr, prefixStr, maxTextSize):
    sPos = dataStr.find(prefixStr.encode())
    if sPos >= 0:
        sPos += len(prefixStr)
        ePos = dataStr.find(b'\0', sPos)
        if ePos < 0:
            ePos = len(dataStr)
        if ePos > sPos and ePos - sPos <= maxTextSize:
            return dataStr[sPos:ePos].decode()
    return None

# Wrapper to be used as a decorator on thread functions, etc, so their exception
# details are sent to the log file (instead of 'stderr').
def catchLogExceptionsWrapper(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.exception("Exception via catchLogExceptionsWrapper")
    return wrapper

# Modifies a name with a human-readable suffix (name 2, name 3, etc.)
# guaranteed to be unique within supplied list of selections
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

# Appends the given string to the "base" part of the given filename.
def appendToBaseFilename(fileNameStr, addStr):
    sList = fileNameStr.rsplit('.', 1)
    retStr = sList[0] + addStr
    if len(sList) > 1:
        retStr += '.' + sList[1]
    return retStr

# Converts Hue/Saturation/Lightness color to hexadecimal
def hslToHex(h, s, l):
    if not h:
        h = random.randint(0, 359)
    if not s:
        s = random.randint(0, 100)
    if not l:
        l = random.randint(0, 100)

    h = h / 360.0
    s = s / 100.0
    l = l / 100.0

    if s == 0:
        r = g = b = l
    else:
        def hue2rgb(p, q, t):
            if t < 0:
                t += 1
            if t > 1:
                t -= 1
            if t < 1 / 6:
                return p + (q - p) * 6 * t
            if t < 1 / 2:
                return q
            if t < 2 / 3:
                return p + (q - p) * (2 / 3 - t) * 6
            return p

        if l < 0.5:
            q = l * (1 + s)
        else:
            q = l + s - l * s

        p = 2 * l - q
        r = int(round(hue2rgb(p, q, h + 1 / 3) * 255))
        g = int(round(hue2rgb(p, q, h) * 255))
        b = int(round(hue2rgb(p, q, h - 1 / 3) * 255))

    return '#{0:02x}{1:02x}{2:02x}'.format(r, g, b)

# converts hexadecimal to int color
def hexToColor(hexColor):
    return int(hexColor.replace('#', ''), 16)

# Attempts to launch a web browser on host system
def launchBrowser(hostStr, httpPortNum=0, pageNameStr=None, launchCmdStr=None):
    try:
        urlStr = hostStr
        if httpPortNum:
            urlStr += ':' + str(httpPortNum)
        if pageNameStr and len(pageNameStr) > 0:
            if pageNameStr.startswith('/'):
                urlStr += pageNameStr
            else:
                urlStr += '/' +  pageNameStr
        if launchCmdStr and len(launchCmdStr) > 0:
            logger.info("Launching browser via command: \"{}\" {}".format(launchCmdStr, urlStr))
            if sys.platform.startswith('win'):
                os.spawnl(os.P_NOWAIT, launchCmdStr, ('"' + launchCmdStr + '"'), urlStr)
            else:
                os.spawnl(os.P_NOWAIT, launchCmdStr, launchCmdStr, urlStr)
        else:
            import webbrowser
            logger.info("Launching browser to view URL: " + urlStr)
            webbrowser.open(urlStr)
    except Exception:
        logger.exception("Error launching browser")

# Auto-frequency algorithm prioritizing minimum channel changes
def find_best_slot_node_basic(available_seats):
    # if only one match has priority
    for an_idx, node in enumerate(available_seats):
        num_priority = 0
        best_match = 0
        for idx, option in enumerate(node['matches']):
            if option['priority']:
                num_priority += 1
                best_match = idx

        if num_priority == 1:
            return node, node['matches'][best_match]['slot'], an_idx

    # if any match has priority
    for an_idx, node in enumerate(available_seats):
        order = list(range(len(node['matches'])))
        random.shuffle(order)
        for idx in order:
            if node['matches'][idx]['priority']:
                return node, node['matches'][idx]['slot'], an_idx

    # if only match
    for an_idx, node in enumerate(available_seats):
        if len(node['matches']) == 1:
            return node, node['matches'][0]['slot'], an_idx

    # if any match
    for an_idx, node in enumerate(available_seats):
        if len(node['matches']):
            idx = random.randint(0, len(node['matches']) - 1)
            return node, node['matches'][idx]['slot'], an_idx

    return None, None, None

# Auto-frequency algorithm suitable for Adaptive Calibration
def find_best_slot_node_adaptive(available_seats):
    # if only match has priority
    for an_idx, node in enumerate(available_seats):
        if len(node['matches']) == 1:
            if node['matches'][0]['priority']:
                return node, node['matches'][0]['slot'], an_idx

    # if only match
    for an_idx, node in enumerate(available_seats):
        if len(node['matches']) == 1:
            return node, node['matches'][0]['slot'], an_idx

    # if one match has priority
    for an_idx, node in enumerate(available_seats):
        num_priority = 0
        best_match = 0
        for idx, option in enumerate(node['matches']):
            if option['priority']:
                num_priority += 1
                best_match = idx

        if num_priority == 1:
            return node, node['matches'][best_match]['slot'], an_idx

    # if any match has priority
    for an_idx, node in enumerate(available_seats):
        order = list(range(len(node['matches'])))
        random.shuffle(order)
        for idx in order:
            if node['matches'][idx]['priority']:
                return node, node['matches'][idx]['slot'], an_idx

    # if any match
    for an_idx, node in enumerate(available_seats):
        if len(node['matches']):
            idx = random.randint(0, len(node['matches']) - 1)
            return node, node['matches'][idx]['slot'], an_idx

    return None, None, None

# Text replacer
def doReplace(rhapi, text, args, spoken_flag=False):
    if '%' in text:
        # %HEAT%
        if 'heat_id' in args:
            heat = rhapi.db.heat_by_id(args['heat_id'])
        else:
            heat = rhapi.db.heat_by_id(rhapi.race.heat)
        text = text.replace('%HEAT%', heat.display_name if heat and heat.display_name else rhapi.__('None'))

        if 'pilot_id' in args or 'node_index' in args:
            if 'pilot_id' in args:
                pilot = rhapi.db.pilot_by_id(args['pilot_id'])
            else:
                pilot = rhapi.db.pilot_by_id(rhapi.race.pilots[args['node_index']])
            text = text.replace('%PILOT%', pilot.spoken_callsign if spoken_flag else pilot.display_callsign)

        race_results = rhapi.race.results
        leaderboard = None
        if 'node_index' in args and '%' in text:
            lboard_name = race_results.get('meta', {}).get('primary_leaderboard', '')
            leaderboard = race_results.get(lboard_name, [])

            for result in leaderboard:
                if result['node'] == args['node_index']:
                    # %LAP_COUNT%
                    text = text.replace('%LAP_COUNT%', str(result['laps']))

                    # %TOTAL_TIME%
                    text = text.replace('%TOTAL_TIME%', phonetictime_format( \
                                result['total_time_raw'], rhapi.db.option('timeFormatPhonetic')) \
                                if spoken_flag else result['total_time'])

                    # %TOTAL_TIME_LAPS%
                    text = text.replace('%TOTAL_TIME_LAPS%', phonetictime_format( \
                                result['total_time_laps_raw'], rhapi.db.option('timeFormatPhonetic')) \
                                if spoken_flag else result['total_time_laps'])

                    # %LAST_LAP%
                    text = text.replace('%LAST_LAP%', phonetictime_format( \
                                result['last_lap_raw'], rhapi.db.option('timeFormatPhonetic')) \
                                if spoken_flag else result['last_lap'])

                    # %AVERAGE_LAP%
                    text = text.replace('%AVERAGE_LAP%', phonetictime_format( \
                                result['average_lap_raw'], rhapi.db.option('timeFormatPhonetic')) \
                                if spoken_flag else result['average_lap'])

                    # %FASTEST_LAP%
                    text = text.replace('%FASTEST_LAP%', phonetictime_format( \
                                result['fastest_lap_raw'], rhapi.db.option('timeFormatPhonetic')) \
                                if spoken_flag else result['fastest_lap'])

                    # %CONSECUTIVE%
                    if result['consecutives_base'] == int(rhapi.db.option('consecutivesCount', 3)):
                        text = text.replace('%CONSECUTIVE%', phonetictime_format( \
                                result['consecutives_raw'], rhapi.db.option('timeFormatPhonetic')) \
                                if spoken_flag else result['consecutives'])
                    else:
                        text = text.replace('%CONSECUTIVE%', rhapi.__('None'))

                    # %POSITION%
                    text = text.replace('%POSITION%', str(result['position']))

                    break

        if '%FASTEST_RACE_LAP' in text:
            fastest_race_lap_data = race_results.get('meta', {}).get('fastest_race_lap_data')
            if fastest_race_lap_data:
                if spoken_flag:
                    fastest_str = "{}, {}".format(fastest_race_lap_data['phonetic'][0],  # pilot name
                                                  fastest_race_lap_data['phonetic'][1])  # lap time
                else:
                    fastest_str = "{} {}".format(fastest_race_lap_data['text'][0],  # pilot name
                                                 fastest_race_lap_data['text'][1])  # lap time
            else:
                fastest_str = ""
            # %FASTEST_RACE_LAP% : Pilot/time for fastest lap in race
            text = text.replace('%FASTEST_RACE_LAP%', fastest_str)
            # %FASTEST_RACE_LAP_CALL% : Pilot/time for fastest lap in race (with prompt)
            if len(fastest_str) > 0:
                fastest_str = "{} {}".format(rhapi.__('Fastest lap'), fastest_str)
            text = text.replace('%FASTEST_RACE_LAP_CALL%', fastest_str)

        if '%PILOTS%' in text:
            text = text.replace('%PILOTS%', getPilotsListStr(rhapi, ' . ', spoken_flag))
        if '%LINEUP%' in text:
            text = text.replace('%LINEUP%', getPilotsListStr(rhapi, ' , ', spoken_flag))
        if '%FREQS%' in text:
            text = text.replace('%FREQS%', getPilotFreqsStr(rhapi, ' . ', spoken_flag))

        if '%LEADER' in text:
            if not leaderboard:
                lboard_name = race_results.get('meta', {}).get('primary_leaderboard', '')
                leaderboard = race_results.get(lboard_name, [])
            name_str = ""
            if len(leaderboard) > 1:
                result = leaderboard[0]
                if 'pilot_id' in result and result.get('laps', 0) > 0:
                    pilot = rhapi.db.pilot_by_id(result['pilot_id'])
                    name_str = pilot.spoken_callsign if spoken_flag else pilot.display_callsign
            # %LEADER% : Callsign of pilot currently leading race
            text = text.replace('%LEADER%', name_str)
            if len(name_str) > 0:
                name_str = "{} {}".format(name_str, rhapi.__('is leading'))
            # %LEADER_CALL% : Callsign of pilot currently leading race, in the form "NAME is leading"
            text = text.replace('%LEADER_CALL%', name_str)

    return text

def heatNodeSorter( x):
    if not x.node_index:
        return -1
    return x.node_index

def getPilotsListStr(rhapi, sep_str, spoken_flag):
    pilots_str = ''
    first_flag = True
    heat_nodes = rhapi.db.slots_by_heat(rhapi.race.heat)
    heat_nodes.sort(key=heatNodeSorter)
    for heat_node in heat_nodes:
        pilot = rhapi.db.pilot_by_id(heat_node.pilot_id)
        if pilot:
            text = pilot.spoken_callsign if spoken_flag else pilot.display_callsign
            if text:
                if first_flag:
                    first_flag = False
                else:
                    pilots_str += sep_str
                pilots_str += text
    return pilots_str

def getPilotFreqsStr(rhapi, sep_str, spoken_flag):
    pilots_str = ''
    first_flag = True
    heat_nodes = rhapi.db.slots_by_heat(rhapi.race.heat)
    heat_nodes.sort(key=heatNodeSorter)
    for heat_node in heat_nodes:
        pilot = rhapi.db.pilot_by_id(heat_node.pilot_id)
        if pilot:
            text = pilot.spoken_callsign if spoken_flag else pilot.display_callsign
            if text:
                profile_freqs = json.loads(rhapi.race.frequencyset.frequencies)
                if profile_freqs:
                    freq = str(profile_freqs["b"][heat_node.node_index]) + str(profile_freqs["c"][heat_node.node_index])
                    if freq:
                        if first_flag:
                            first_flag = False
                        else:
                            pilots_str += sep_str
                        pilots_str += text + ': ' + freq
    return pilots_str

def cleanVarName(varStr): 
    return re.sub('\W|^(?=\d)','_', varStr)

def checkPythonVersion(majorVer, minorVer):
    try:
        verStr = getPythonVersionStr()
        if not checkVersionStr(verStr, majorVer, minorVer):
            logger.warning("WARNING: The Python version in use ({}) is lower than the minimum required ({}.{})".\
                        format(verStr, majorVer, minorVer))
    except Exception as ex:
        logger.debug("Error in 'checkRepPythonVersionStr': {}".format(ex))
