'''
Global configurations
'''
import logging
import random
import json

logger = logging.getLogger(__name__)

class Config():
    def __init__(self, filename='config.json'):
        self.filename = filename

        self.config = {
            'GENERAL': {},
            'HARDWARE': {},
            'LED': {},
            'VRX_CONTROL': {},
            'LOGGING': {},
            'SENSORS': {},
            'SERIAL_PORTS': [],
        }

        # LED strip configuration:
        self.config['LED']['LED_COUNT'] = 0  # Number of LED pixels.
        self.config['LED']['LED_GPIO'] = 10  # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
        self.config['LED']['LED_FREQ_HZ'] = 800000  # LED signal frequency in hertz (usually 800khz)
        self.config['LED']['LED_DMA'] = 10  # DMA channel to use for generating signal (try 10)
        self.config['LED']['LED_INVERT'] = False  # True to invert the signal (when using NPN transistor level shift)
        self.config['LED']['LED_CHANNEL'] = 0  # set to '1' for GPIOs 13, 19, 41, 45 or 53
        self.config['LED']['LED_STRIP'] = 'GRB'  # Strip type and colour ordering
        self.config['LED']['LED_ROWS'] = 1  # Number of rows in LED array
        self.config['LED']['PANEL_ROTATE'] = 0
        self.config['LED']['INVERTED_PANEL_ROWS'] = False

        # Video Receiver Configuration
        self.config['VRX_CONTROL']['HOST'] = 'localhost'  # MQTT broker IP Address
        self.config['VRX_CONTROL']['ENABLED'] = False
        self.config['VRX_CONTROL']['OSD_LAP_HEADER'] = 'L'

        # hardware default configurations
        self.config['HARDWARE']['I2C_BUS'] = 1

        # other default configurations
        self.config['GENERAL']['HTTP_PORT'] = 5000
        self.config['GENERAL']['SECRET_KEY'] = random.random()
        self.config['GENERAL']['ADMIN_USERNAME'] = ''
        self.config['GENERAL']['ADMIN_PASSWORD'] = ''
        self.config['GENERAL']['SECONDARIES'] = []
        self.config['GENERAL']['SECONDARY_TIMEOUT'] = 300  # seconds
        self.config['GENERAL']['DEBUG'] = False
        self.config['GENERAL']['CORS_ALLOWED_HOSTS'] = '*'
        self.config['GENERAL']['FORCE_S32_BPILL_FLAG'] = False
        self.config['GENERAL']['DEF_NODE_FWUPDATE_URL'] = ''
        self.config['GENERAL']['SHUTDOWN_BUTTON_GPIOPIN'] = 18
        self.config['GENERAL']['SHUTDOWN_BUTTON_DELAYMS'] = 2500
        self.config['GENERAL']['DB_AUTOBKP_NUM_KEEP'] = 30
        self.config['GENERAL']['RACE_START_DELAY_EXTRA_SECS'] = 0.9  # amount of extra time added to prestage time
        self.config['GENERAL']['LOG_SENSORS_DATA_RATE'] = 300  # rate at which to log sensor data

        self.InitResultStr = None
        self.InitResultLogLevel = logging.INFO

        # override defaults above with config from file
        try:
            with open(self.filename, 'r') as f:
                ExternalConfig = json.load(f)

            self.config['GENERAL'].update(ExternalConfig['GENERAL'])

            # if auth fields set to empty strings then allow open access to all pages
            if ExternalConfig['GENERAL'].get('ADMIN_USERNAME') == "" and \
                        ExternalConfig['GENERAL'].get('ADMIN_PASSWORD') == "":
                self.config['GENERAL']['ADMIN_USERNAME'] = ''
                self.config['GENERAL']['ADMIN_PASSWORD'] = ''

            if 'HARDWARE' in ExternalConfig:
                self.config['HARDWARE'].update(ExternalConfig['HARDWARE'])
            if 'LOGGING' in ExternalConfig:
                self.config['LOGGING'].update(ExternalConfig['LOGGING'])
            if 'LED' in ExternalConfig:
                self.config['LED'].update(ExternalConfig['LED'])
            if 'VRX_CONTROL' in ExternalConfig:
                self.config['VRX_CONTROL'].update(ExternalConfig['VRX_CONTROL'])
            if 'SENSORS' in ExternalConfig:
                self.config['SENSORS'].update(ExternalConfig['SENSORS'])
            if 'SERIAL_PORTS' in ExternalConfig:
                self.config['SERIAL_PORTS'].extend(ExternalConfig['SERIAL_PORTS'])
            self.config_file_status = 1
            self.InitResultStr = "Using configuration file '{0}'".format(self.filename)
            self.InitResultLogLevel = logging.INFO
        except IOError:
            self.config_file_status = 0
            self.InitResultStr = "No configuration file found, using defaults"
            self.InitResultLogLevel = logging.WARN
        except ValueError as ex:
            self.config_file_status = -1
            self.InitResultStr = "Configuration file invalid, using defaults; error is: " + str(ex)
            self.InitResultLogLevel = logging.ERROR

        # Apply legacy config options for backward compatibility

        if 'SERIAL_PORTS' in self.config:
            if not self.config['GENERAL'].get('SERIAL_PORTS'):
                self.config['GENERAL']['SERIAL_PORTS'] = self.config['SERIAL_PORTS']
            del self.config['SERIAL_PORTS']

        if 'SLAVES' in self.config['GENERAL']:
            if self.config['GENERAL']['SLAVES'] and not self.config['GENERAL'].get('SECONDARIES'):
                self.config['GENERAL']['SECONDARIES'] = self.config['GENERAL']['SLAVES']
            del self.config['GENERAL']['SLAVES']

        if 'SLAVE_TIMEOUT' in self.config['GENERAL']:
            if self.config['GENERAL']['SLAVE_TIMEOUT'] and not self.config['GENERAL'].get('SECONDARY_TIMEOUT'):
                self.config['GENERAL']['SECONDARY_TIMEOUT'] = self.config['GENERAL']['SLAVE_TIMEOUT']
            del self.config['GENERAL']['SLAVE_TIMEOUT']

        if 'LED_PIN' in self.config['LED']:
            if self.config['LED']['LED_PIN'] and not self.config['LED'].get('LED_GPIO'):
                self.config['LED']['LED_GPIO'] = self.config['LED']['LED_PIN']
            del self.config['LED']['LED_PIN']

    # Writes a log message describing the result of the module initialization.
    def logInitResultMessage(self):
        if self.InitResultStr:
            logger.log(self.InitResultLogLevel, self.InitResultStr)

    def get_item(self, section, item):
        try:
            return self.config[section][item]
        except:
            return False

    def get_section(self, section):
        try:
            return self.config[section]
        except:
            return False

    def set_item(self, section, item, value):
        try:
            self.config[section][item] = value
            self.save_config()
        except:
            return False
        return True

    def save_config(self):
        with open(self.filename, 'w') as f:
            f.write(json.dumps(self.config, indent=2))
