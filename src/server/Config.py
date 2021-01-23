'''
Global configurations
'''
import logging
import random
import json

logger = logging.getLogger(__name__)

CONFIG_FILE_NAME = 'config.json'

GENERAL = {}
HARDWARE = {}
SENSORS = {}
LED = {}
SERIAL_PORTS = []
LOGGING = {}
VRX_CONTROL = {}

# LED strip configuration:
LED['LED_COUNT']      = 0       # Number of LED pixels.
LED['LED_PIN']        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED['LED_FREQ_HZ']    = 800000  # LED signal frequency in hertz (usually 800khz)
LED['LED_DMA']        = 10      # DMA channel to use for generating signal (try 10)
LED['LED_INVERT']     = False   # True to invert the signal (when using NPN transistor level shift)
LED['LED_CHANNEL']    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
LED['LED_STRIP']      = 'GRB'   # Strip type and colour ordering
LED['LED_ROWS']       = 1       # Number of rows in LED array
LED['PANEL_ROTATE']   = 0
LED['INVERTED_PANEL_ROWS'] = False

# Video Receiver Configuration
VRX_CONTROL['HOST']    = 'localhost'     # MQTT broker IP Address
VRX_CONTROL['ENABLED'] = False
VRX_CONTROL['OSD_LAP_HEADER'] = 'L'

# hardware default configurations
HARDWARE['I2C_BUS'] = 1

# other default configurations
GENERAL['HTTP_PORT'] = 5000
GENERAL['SECRET_KEY'] = random.random()
GENERAL['ADMIN_USERNAME'] = 'admin'
GENERAL['ADMIN_PASSWORD'] = 'rotorhazard'
GENERAL['SECONDARIES'] = []
GENERAL['SECONDARY_TIMEOUT'] = 300 # seconds
GENERAL['DEBUG'] = False
GENERAL['CORS_ALLOWED_HOSTS'] = '*'

InitResultStr = None
InitResultLogLevel = logging.INFO

# override defaults above with config from file
try:
    with open(CONFIG_FILE_NAME, 'r') as f:
        ExternalConfig = json.load(f)

    GENERAL.update(ExternalConfig['GENERAL'])

    if 'HARDWARE' in ExternalConfig:
        HARDWARE.update(ExternalConfig['HARDWARE'])
    if 'LOGGING' in ExternalConfig:
        LOGGING.update(ExternalConfig['LOGGING'])
    if 'LED' in ExternalConfig:
        LED.update(ExternalConfig['LED'])
    if 'VRX_CONTROL' in ExternalConfig:
        VRX_CONTROL.update(ExternalConfig['VRX_CONTROL'])


    '''
    # Subtree updating
    try:
        bitmaptree = LED['BITMAPS']
        LED'].update(ExternalLED'])
        LED['BITMAPS'] = bitmaptree
        LED['BITMAPS'].update(ExternalLED['BITMAPS'])
    except KeyError:
        if 'LED' in ExternalConfig:
            LED'].update(ExternalLED'])
        else:
            print "No 'LED' entry found in configuration file "
    '''

    if 'SENSORS' in ExternalConfig:
        SENSORS.update(ExternalConfig['SENSORS'])
    if 'SERIAL_PORTS' in ExternalConfig:
        SERIAL_PORTS.extend(ExternalConfig['SERIAL_PORTS'])
    GENERAL['configFile'] = 1
    InitResultStr = "Using configuration file '{0}'".format(CONFIG_FILE_NAME)
    InitResultLogLevel = logging.INFO
except IOError:
    GENERAL['configFile'] = 0
    InitResultStr = "No configuration file found, using defaults"
    InitResultLogLevel = logging.WARN
except ValueError as ex:
    GENERAL['configFile'] = -1
    InitResultStr = "Configuration file invalid, using defaults; error is: " + str(ex)
    InitResultLogLevel = logging.ERROR

# Apply legacy config options for backward compatibility
if not GENERAL['SECONDARIES']:
    if GENERAL['SLAVES']:
        GENERAL['SECONDARIES'] = GENERAL['SLAVES']

if not GENERAL['SECONDARY_TIMEOUT']:
    if GENERAL['SLAVE_TIMEOUT']:
        GENERAL['SECONDARY_TIMEOUT'] = GENERAL['SLAVE_TIMEOUT']

# Writes a log message describing the result of the module initialization.
def logInitResultMessage():
    if InitResultStr:
        logger.log(InitResultLogLevel, InitResultStr)
