'''
Global configurations
'''
import copy
import logging
import random
import json

logger = logging.getLogger(__name__)

class Config():
    def __init__(self, racecontext, filename='config.json'):
        self._racecontext = racecontext
        self.filename = filename

        self.config = {
            'SECRETS': {},
            'GENERAL': {},
            'HARDWARE': {},
            'LED': {},
            'VRX_CONTROL': {},
            'LOGGING': {},
            'SENSORS': {},
        }

        # server secrets:
        self.config['SECRETS']['ADMIN_USERNAME'] = ''
        self.config['SECRETS']['ADMIN_PASSWORD'] = ''
        self.config['SECRETS']['SECRET_KEY'] = ''

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

        # LED effect configuration
        self.config['LED']['ledEffects'] = ''
        self.config['LED']['ledBrightness'] = '32'
        self.config['LED']['ledColorNodes'] = ''
        self.config['LED']['ledColorFreqs'] = ''

        # Video Receiver Configuration
        self.config['VRX_CONTROL']['HOST'] = 'localhost'  # MQTT broker IP Address
        self.config['VRX_CONTROL']['ENABLED'] = False
        self.config['VRX_CONTROL']['OSD_LAP_HEADER'] = 'L'

        # hardware default configurations
        self.config['HARDWARE']['I2C_BUS'] = 1

        # other default configurations
        self.config['GENERAL']['HTTP_PORT'] = 5000
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
        self.config['GENERAL']['SERIAL_PORTS'] = []

        # timer UI options
        self.config['GENERAL']['timerName'] = "RotorHazard"
        self.config['GENERAL']['timerLogo'] = ''
        self.config['GENERAL']['hue_0'] = '212'
        self.config['GENERAL']['sat_0'] = '55'
        self.config['GENERAL']['lum_0_low'] = '29.2'
        self.config['GENERAL']['lum_0_high'] = '46.7'
        self.config['GENERAL']['contrast_0_low'] = '#ffffff'
        self.config['GENERAL']['contrast_0_high'] = '#ffffff'
        self.config['GENERAL']['hue_1'] = '25'
        self.config['GENERAL']['sat_1'] = '85.3'
        self.config['GENERAL']['lum_1_low'] = '37.6'
        self.config['GENERAL']['lum_1_high'] = '54.5'
        self.config['GENERAL']['contrast_1_low'] = '#ffffff'
        self.config['GENERAL']['contrast_1_high'] = '#000000'
        self.config['GENERAL']['currentLanguage'] = ''
        self.config['GENERAL']['timeFormat'] = '{m}:{s}.{d}'
        self.config['GENERAL']['timeFormatPhonetic'] = '{m} {s}.{d}'
        self.config['GENERAL']['startThreshLowerAmount'] = '0'
        self.config['GENERAL']['startThreshLowerDuration'] = '0'
        self.config['GENERAL']['voiceCallouts'] = ''
        self.config['GENERAL']['actions'] = '' 

        # logging defaults
        self.config['LOGGING']['CONSOLE_LEVEL'] = "INFO"
        self.config['LOGGING']['SYSLOG_LEVEL'] = "NONE"
        self.config['LOGGING']['FILELOG_LEVEL'] = "INFO"
        self.config['LOGGING']['FILELOG_NUM_KEEP'] = 30
        self.config['LOGGING']['CONSOLE_STREAM'] = "stdout"

        self.InitResultStr = None
        self.InitResultLogLevel = logging.INFO

        # override defaults above with config from file
        try:
            with open(self.filename, 'r') as f:
                ExternalConfig = json.load(f)

            for key in ExternalConfig.keys():
                self.config[key].update(ExternalConfig[key])

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

        self.migrate_legacy_config()
        self.save_config()

    def migrate_legacy_config(self):
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

        if 'ADMIN_USERNAME' in self.config['GENERAL']:
            if self.config['SECRETS'].get('ADMIN_USERNAME'):
                self.config['SECRETS']['ADMIN_USERNAME'] = self.config['GENERAL']['ADMIN_USERNAME']
            del self.config['GENERAL']['ADMIN_USERNAME']

        if 'ADMIN_PASSWORD' in self.config['GENERAL']:
            if self.config['SECRETS'].get('ADMIN_PASSWORD'):
                self.config['SECRETS']['ADMIN_PASSWORD'] = self.config['GENERAL']['ADMIN_PASSWORD']
            del self.config['GENERAL']['ADMIN_PASSWORD']

        if 'SECRET_KEY' in self.config['GENERAL']:
            del self.config['GENERAL']['SECRET_KEY']

    def migrate_legacy_db_keys(self):
        class migrateItem():
            def __init__(self, source, section='GENERAL', dest=None):
                self.source = source
                self.section = section
                self.dest = dest

            @property
            def dest(self):
                return self.dest if self.dest else self.source

        migrations = [
            migrateItem('timerName'),
            migrateItem('timerLogo'),
            migrateItem('hue_0'),
            migrateItem('sat_0'),
            migrateItem('lum_0_low'),
            migrateItem('lum_0_high'),
            migrateItem('contrast_0_low'),
            migrateItem('contrast_0_high'),
            migrateItem('hue_1'),
            migrateItem('sat_1'),
            migrateItem('lum_1_low'),
            migrateItem('lum_1_high'),
            migrateItem('contrast_1_low'),
            migrateItem('contrast_1_high'),
            migrateItem('currentLanguage'),
            migrateItem('timeFormat'),
            migrateItem('timeFormatPhonetic'),
            migrateItem('ledEffects', 'LED'),
            migrateItem('ledBrightness', 'LED'),
            migrateItem('ledColorNodes', 'LED'),
            migrateItem('ledColorFreqs', 'LED'),
            migrateItem('startThreshLowerAmount'),
            migrateItem('startThreshLowerDuration'),
            migrateItem('voiceCallouts'),
            migrateItem('actions'),
        ]

        for item in migrations:
            self._racecontext.serverconfig.set_item(
                item.dest,
                item.section,
                self._racecontext.rhdata.get_option(item.source)
            )

    # Writes a log message describing the result of the module initialization.
    def logInitResultMessage(self):
        if self.InitResultStr:
            logger.log(self.InitResultLogLevel, self.InitResultStr)

    def get_item(self, section, key, returntype=None):
        try:
            return self.config[section][key]
        except:
            return False

    def get_item_int(self, section, key, default_value=0):
        try:
            val = self.config[section][key]
            if val:
                return int(val)
            else:
                return default_value
        except:
            return default_value

    def get_section(self, section):
        try:
            return self.config[section]
        except:
            return False

    def set_item(self, section, key, value):
        try:
            self.config[section][key] = value
            self.save_config()
        except:
            return False
        return True

    def save_config(self):
        with open(self.filename, 'w') as f:
            f.write(json.dumps(self.config, indent=2))

    def get_sharable_config(self):
        sharable_config = copy.deepcopy(self.config)
        del sharable_config['SECRETS']
        return sharable_config
