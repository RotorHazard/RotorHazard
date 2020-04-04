'''
Global configurations
'''

import random
import json

CONFIG_FILE_NAME = 'config.json'

GENERAL = {}
SENSORS = {}
LED = {}
SERIAL_PORTS = []

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

# other default configurations
GENERAL['HTTP_PORT'] = 5000
GENERAL['SECRET_KEY'] = random.random()
GENERAL['ADMIN_USERNAME'] = 'admin'
GENERAL['ADMIN_PASSWORD'] = 'rotorhazard'
GENERAL['SLAVES'] = []
GENERAL['SLAVE_TIMEOUT'] = 300 # seconds
GENERAL['DEBUG'] = False
GENERAL['CORS_ALLOWED_HOSTS'] = '*'

# override defaults above with config from file
try:
    with open(CONFIG_FILE_NAME, 'r') as f:
        ExternalConfig = json.load(f)
    GENERAL.update(ExternalConfig['GENERAL'])

    if 'LED' in ExternalConfig:
        LED.update(ExternalConfig['LED'])

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
    print 'Configuration file imported'
except IOError:
    GENERAL['configFile'] = 0
    print 'No configuration file found, using defaults'
except ValueError as ex:
    GENERAL['configFile'] = -1
    print 'Configuration file invalid, using defaults; error is: ' + str(ex)
