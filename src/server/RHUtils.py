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

def isVersionPython2():
    return sys.version.startswith("2.")

def getPythonVersionStr():
    return sys.version.split()[0]

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

def hslToHex(h, s, l):
    if not h:
        h = random.randint(0, 359)
    if not s:
        s = random.randint(0, 100)
    if not l:
        l = random.randint(0, 100)

    h = h / 360.0;
    s = s / 100.0;
    l = l / 100.0;

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
                return q;
            if t < 2 / 3:
                return p + (q - p) * (2 / 3 - t) * 6
            return p

        if l < 0.5:
            q = l * (1 + s)
        else:
            q = l + s - l * s;

        p = 2 * l - q;
        r = int(round(hue2rgb(p, q, h + 1 / 3) * 255))
        g = int(round(hue2rgb(p, q, h) * 255))
        b = int(round(hue2rgb(p, q, h - 1 / 3) * 255))

    return '#{0:02x}{1:02x}{2:02x}'.format(r, g, b)
