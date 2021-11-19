import logging
import random
import json
import jsonschema

logger = logging.getLogger(__name__)

class Config:
    FILE_NAME = 'config.json'
    SCHEMA_FILE_NAME = 'config.schema.json'
    DB_FILE_NAME = 'database.db'

    def __init__(self):
        self.GENERAL = {}
        self.HARDWARE = {}
        self.SENSORS = {}
        self.LED = {}
        self.MQTT = {}
        self.SERIAL_PORTS = []
        self.SOCKET_PORTS = []
        self.LOGGING = {}
        self.VRX_CONTROL = {}
        self.AUDIO = {}
        self.LAPRF = {}
        self.CHORUS = {}
        self.apply_defaults()
        with open(Config.SCHEMA_FILE_NAME, 'r') as f:
            self.schema = json.load(f)

    def apply_defaults(self):
        # LED strip configuration:
        self.LED['LED_COUNT']      = 0       # Number of LED pixels.
        self.LED['LED_PIN']        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
        self.LED['LED_FREQ_HZ']    = 800000  # LED signal frequency in hertz (usually 800khz)
        self.LED['LED_DMA']        = 10      # DMA channel to use for generating signal (try 10)
        self.LED['LED_INVERT']     = False   # True to invert the signal (when using NPN transistor level shift)
        self.LED['LED_CHANNEL']    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
        self.LED['LED_STRIP']      = 'GRB'   # Strip type and colour ordering
        self.LED['LED_ROWS']       = 1       # Number of rows in LED array
        self.LED['PANEL_ROTATE']   = 0
        self.LED['INVERTED_PANEL_ROWS'] = False

        # MQTT configuration
        self.MQTT['TIMER_ANN_TOPIC'] = 'timer/ann'
        self.MQTT['TIMER_CTRL_TOPIC'] = 'timer/ctrl'
        self.MQTT['RACE_ANN_TOPIC'] = 'race/ann'

        # Video Receiver configuration
        self.VRX_CONTROL['HOST']    = 'localhost'     # MQTT broker IP Address
        self.VRX_CONTROL['ENABLED'] = False
        self.VRX_CONTROL['OSD_LAP_HEADER'] = 'L'

        # hardware default configurations
        self.HARDWARE['I2C_BUSES'] = [1]

        # other default configurations
        self.GENERAL['HTTP_PORT'] = 5000
        self.GENERAL['DATABASE'] = ''
        self.GENERAL['SECRET_KEY'] = random.random()
        self.GENERAL['ADMIN_USERNAME'] = 'admin'
        self.GENERAL['ADMIN_PASSWORD'] = 'rotorhazard'
        self.GENERAL['SECONDARIES'] = []
        self.GENERAL['SECONDARY_TIMEOUT'] = 300 # seconds
        self.GENERAL['DEBUG'] = False
        self.GENERAL['CORS_ALLOWED_HOSTS'] = '*'
        self.GENERAL['FORCE_S32_BPILL_FLAG'] = False
        self.GENERAL['DEF_NODE_FWUPDATE_URL'] = ''
        self.GENERAL['SHUTDOWN_BUTTON_GPIOPIN'] = 18
        self.GENERAL['SHUTDOWN_BUTTON_DELAYMS'] = 2500
        self.GENERAL['DB_AUTOBKP_NUM_KEEP'] = 30

    def load(self, file=FILE_NAME):
        # override defaults above with config from file
        try:
            with open(file, 'r') as f:
                externalConfig = json.load(f)

            jsonschema.validate(instance=externalConfig, schema=self.schema)

            self.GENERAL.update(externalConfig['GENERAL'])

            if 'HARDWARE' in externalConfig:
                self.HARDWARE.update(externalConfig['HARDWARE'])
            if 'LOGGING' in externalConfig:
                self.LOGGING.update(externalConfig['LOGGING'])
            if 'LED' in externalConfig:
                self.LED.update(externalConfig['LED'])
            if 'MQTT' in externalConfig:
                self.MQTT.update(externalConfig['MQTT'])
            if 'AUDIO' in externalConfig:
                self.AUDIO.update(externalConfig['AUDIO'])
            if 'VRX_CONTROL' in externalConfig:
                self.VRX_CONTROL.update(externalConfig['VRX_CONTROL'])
            if 'LAPRF' in externalConfig:
                self.LAPRF.update(externalConfig['LAPRF'])
            if 'CHORUS' in externalConfig:
                self.CHORUS.update(externalConfig['CHORUS'])
        
            '''
            # Subtree updating
            try:
                bitmaptree = LED['BITMAPS']
                LED'].update(ExternalLED'])
                LED['BITMAPS'] = bitmaptree
                LED['BITMAPS'].update(ExternalLED['BITMAPS'])
            except KeyError:
                if 'LED' in externalConfig:
                    LED'].update(ExternalLED'])
                else:
                    print "No 'LED' entry found in configuration file "
            '''
        
            if 'SENSORS' in externalConfig:
                self.SENSORS.update(externalConfig['SENSORS'])
            if 'SERIAL_PORTS' in externalConfig:
                self.SERIAL_PORTS.extend(externalConfig['SERIAL_PORTS'])
            if 'SOCKET_PORTS' in externalConfig:
                self.SOCKET_PORTS.extend(externalConfig['SOCKET_PORTS'])

            # Apply legacy config options for backward compatibility
            if not self.GENERAL['SECONDARIES'] and 'SLAVES' in self.GENERAL and self.GENERAL['SLAVES']:
                    self.GENERAL['SECONDARIES'] = self.GENERAL['SLAVES']

            if not self.GENERAL['SECONDARY_TIMEOUT'] and 'SLAVE_TIMEOUT' in self.GENERAL and self.GENERAL['SLAVE_TIMEOUT']:
                    self.GENERAL['SECONDARY_TIMEOUT'] = self.GENERAL['SLAVE_TIMEOUT']

            self.GENERAL['configFile'] = 'loaded'
            logger.info("Using configuration file '{0}'".format(file))
        except IOError:
            self.GENERAL['configFile'] = 'defaults'
            logger.warn("No configuration file found, using defaults")
        except ValueError as ex:
            self.GENERAL['configFile'] = 'error'
            logger.error("Configuration file invalid, using defaults; error is: {}".format(ex))
