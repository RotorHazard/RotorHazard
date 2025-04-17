'''
Global configurations
'''
import copy
import logging
import json
import shutil
import filecmp
import time
import os
import glob
from datetime import datetime

logger = logging.getLogger(__name__)

class Config:
    def __init__(self, racecontext, config_file_name, cfg_bkp_dir_name):
        self._racecontext = racecontext
        self.config_file_name = config_file_name
        self.cfg_bkp_dir_name = cfg_bkp_dir_name
        self.config_file_status = None

        self.config_sections = {
            'SECRETS': {},
            'GENERAL': {},
            'TIMING': {},
            'UI': {},
            'USER': {},
            'HARDWARE': {},
            'LED': {},
            'LOGGING': {},
            'SENSORS': {},
            'PLUGINS': {},
        }

        self.config = copy.copy(self.config_sections)

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
        self.config['LED']['SERIAL_CTRLR_PORT'] = None      # Serial port for LED-controller module
        self.config['LED']['SERIAL_CTRLR_BAUD'] = 115200    # Serial baud rate for LED-controller module

        # LED effect configuration
        self.config['LED']['ledEffects'] = ''
        self.config['LED']['ledBrightness'] = 32
        self.config['LED']['ledColorMode'] = ''
        self.config['LED']['seatColors'] = [
            "#0022ff",  # Blue
            "#ff5500",  # Orange
            "#00ff22",  # Green
            "#ff0055",  # Magenta
            "#ddff00",  # Yellow
            "#7700ff",  # Purple
            "#00ffdd",  # Teal
            "#aaaaaa",  # White
        ]

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
        self.config['GENERAL']['LAST_MODIFIED_TIME'] = 0

        self.config['SECRETS']['ADMIN_USERNAME'] = 'admin'
        self.config['SECRETS']['ADMIN_PASSWORD'] = 'rotorhazard'

        # UI
        self.config['UI']['timerName'] = "RotorHazard"
        self.config['UI']['timerLogo'] = ''
        self.config['UI']['hue_0'] = '212'
        self.config['UI']['sat_0'] = '55'
        self.config['UI']['lum_0_low'] = '29.2'
        self.config['UI']['lum_0_high'] = '46.7'
        self.config['UI']['contrast_0_low'] = '#ffffff'
        self.config['UI']['contrast_0_high'] = '#ffffff'
        self.config['UI']['hue_1'] = '25'
        self.config['UI']['sat_1'] = '85.3'
        self.config['UI']['lum_1_low'] = '37.6'
        self.config['UI']['lum_1_high'] = '54.5'
        self.config['UI']['contrast_1_low'] = '#ffffff'
        self.config['UI']['contrast_1_high'] = '#000000'
        self.config['UI']['currentLanguage'] = ''
        self.config['UI']['timeFormat'] = '{m}:{s}.{d}'
        self.config['UI']['timeFormatPhonetic'] = '{m} {s}.{d}'
        self.config['UI']['pilotSort'] = 'name'

        # timing
        self.config['TIMING']['startThreshLowerAmount'] = '0'
        self.config['TIMING']['startThreshLowerDuration'] = '0'
        self.config['TIMING']['calibrationMode'] = 1
        self.config['TIMING']['MinLapBehavior'] = 0

        # user-specified behavior
        self.config['USER']['voiceCallouts'] = ''
        self.config['USER']['actions'] = '[]'

        # logging defaults
        self.config['LOGGING']['CONSOLE_LEVEL'] = "INFO"
        self.config['LOGGING']['SYSLOG_LEVEL'] = "NONE"
        self.config['LOGGING']['FILELOG_LEVEL'] = "INFO"
        self.config['LOGGING']['FILELOG_NUM_KEEP'] = 30
        self.config['LOGGING']['CONSOLE_STREAM'] = "stdout"
        self.config['LOGGING']['EVENTS'] = 1

        # plugin defaults
        self.config['PLUGINS']['REMOTE_DATA_URI'] = None
        self.config['PLUGINS']['REMOTE_CATEGORIES_URI'] = None

        self.InitResultStr = None
        self.InitResultLogLevel = logging.INFO

        self.migrations = [
            migrateItem('timerName', 'UI'),
            migrateItem('timerLogo', 'UI'),
            migrateItem('hue_0', 'UI'),
            migrateItem('sat_0', 'UI'),
            migrateItem('lum_0_low', 'UI'),
            migrateItem('lum_0_high', 'UI'),
            migrateItem('contrast_0_low', 'UI'),
            migrateItem('contrast_0_high', 'UI'),
            migrateItem('hue_1', 'UI'),
            migrateItem('sat_1', 'UI'),
            migrateItem('lum_1_low', 'UI'),
            migrateItem('lum_1_high', 'UI'),
            migrateItem('contrast_1_low', 'UI'),
            migrateItem('contrast_1_high', 'UI'),
            migrateItem('currentLanguage', 'UI'),
            migrateItem('timeFormat', 'UI'),
            migrateItem('timeFormatPhonetic', 'UI'),
            migrateItem('pilotSort', 'UI'),
            migrateItem('ledEffects', 'LED'),
            migrateItem('ledBrightness', 'LED'),
            migrateItem('startThreshLowerAmount', 'TIMING'),
            migrateItem('startThreshLowerDuration', 'TIMING'),
            migrateItem('calibrationMode', 'TIMING'),
            migrateItem('MinLapBehavior', 'TIMING'),
            migrateItem('voiceCallouts', 'USER'),
            migrateItem('actions', 'USER'),
        ]

        self._restart_required_keys = {
            'LED': [
                'LED_COUNT',
                'LED_GPIO',
                'LED_FREQ_HZ',
                'LED_DMA',
                'LED_INVERT',
                'LED_CHANNEL',
                'LED_STRIP',
                'LED_ROWS',
                'SERIAL_CTRLR_PORT',
                'SERIAL_CTRLR_BAUD'
            ],
            'HARDWARE': [
                'I2C_BUS'
            ],
            'GENERAL' : [
                'HTTP_PORT',
                'SECONDARIES',
                'CORS_ALLOWED_HOSTS',
                'FORCE_S32_BPILL_FLAG',
                'SHUTDOWN_BUTTON_GPIOPIN',
                'SHUTDOWN_BUTTON_DELAYMS',
                'DB_AUTOBKP_NUM_KEEP',
                'SERIAL_PORTS',
            ],
            'SECRETS': [
                'ADMIN_USERNAME',
                'ADMIN_PASSWORD'
            ],
            'LOGGING': [
                'CONSOLE_LEVEL',
                'SYSLOG_LEVEL',
                'FILELOG_LEVEL',
                'FILELOG_NUM_KEEP',
                'CONSOLE_STREAM'
            ],
            'PLUGINS': [
                'REMOTE_DATA_URI',
                'REMOTE_CATEGORIES_URI'
            ],
            'SENSORS': []
        }

        # override defaults above with config from file
        try:
            with open(self.config_file_name, 'r') as f:
                external_config = json.load(f)

            self.migrate_legacy_config_early(external_config)
            for key in external_config.keys():
                if key in self.config:
                    self.config[key].update(external_config[key])
                else:
                    self.config.update({key:external_config[key]})

            self.config_file_status = 1
            self.InitResultStr = "Using configuration file '{0}'".format(self.config_file_name)
            self.InitResultLogLevel = logging.INFO
        except IOError:
            self.config_file_status = 0
            self.InitResultStr = "No configuration file found, starting up in first-run mode"
            self.InitResultLogLevel = logging.INFO
        except ValueError as ex:
            self.config_file_status = -1
            self.InitResultStr = "Configuration file invalid, using defaults; error is: " + str(ex)
            self.InitResultLogLevel = logging.ERROR

        self.check_backup_config_file(True)
        self.migrate_legacy_config()

    def migrate_legacy_config_early(self, external_config):
        for key in list(external_config.keys()):
            if key == 'SERIAL_PORTS':
                if not self.config['GENERAL'].get('SERIAL_PORTS'):
                    self.config['GENERAL']['SERIAL_PORTS'] = external_config[key]
                del external_config[key]

    def migrate_legacy_config(self):
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
            if self.config['SECRETS'].get('ADMIN_USERNAME') is None:
                self.config['SECRETS']['ADMIN_USERNAME'] = self.config['GENERAL']['ADMIN_USERNAME']
            del self.config['GENERAL']['ADMIN_USERNAME']

        if 'ADMIN_PASSWORD' in self.config['GENERAL']:
            if self.config['SECRETS'].get('ADMIN_PASSWORD') is None:
                self.config['SECRETS']['ADMIN_PASSWORD'] = self.config['GENERAL']['ADMIN_PASSWORD']
            del self.config['GENERAL']['ADMIN_PASSWORD']

        if 'SECRET_KEY' in self.config['GENERAL']:
            del self.config['GENERAL']['SECRET_KEY']

    def migrate_legacy_db_keys(self):
        for item in self.migrations:
            if self._racecontext.rhdata.get_option(item.source):
                self.set_item(
                    item.section,
                    item.dest,
                    self._racecontext.rhdata.get_option(item.source)
                )
            self._racecontext.rhdata.delete_option(item.source)

        logger.info('Migrated legacy server config from event database')

    # Writes a log message describing the result of the module initialization.
    def logInitResultMessage(self):
        if self.InitResultStr:
            logger.log(self.InitResultLogLevel, self.InitResultStr)

    def flag_restart_key(self, section, key):
        if section not in self._restart_required_keys:
            self._restart_required_keys[section] = []
        if key not in self._restart_required_keys[section]:
            self._restart_required_keys[section].append(key)

    def check_restart_flag(self, section, key=None):
        if key:
            try:
                if key in self._restart_required_keys[section]:
                    self._racecontext.serverstate.set_restart_required()
            except:
                pass
        else:
            if section in self._restart_required_keys:
                self._racecontext.serverstate.set_restart_required()

    def item_exists(self, section, key):
        return True if section in self.config and key in self.config[section] else False

    def get_item(self, section, key):
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
            self.check_restart_flag(section, key)
            self.save_config()
        except:
            return False
        return True

    def set_section(self, section, value):
        try:
            self.config[section] = value
            self.check_restart_flag(section)
            self.save_config()
        except:
            return False
        return True

    def register_section(self, section):
        self.config_sections[section] = {}
        if section not in self.config:
            self.config[section] = {}

    def clean_config(self):
        try:
            if self.config.keys() == self.config_sections.keys():
                # if LAST_MODIFIED_TIME does not match timestamp on file then trigger save to synchronize them
                last_modified_time = self.get_item_int('GENERAL', 'LAST_MODIFIED_TIME')
                file_modified_time = int(os.path.getmtime(self.config_file_name)) \
                                             if os.path.exists(self.config_file_name) else 0
                if file_modified_time > 0 and abs(file_modified_time - last_modified_time) > 5:
                    logger.debug("Configuration LAST_MODIFIED_TIME does not match timestamp on file; triggering config save")
                    return True
                return False
            logger.info("Change in registered configuration sections detected")
            self.check_backup_config_file()
            config_cleaned = {}
            for item in self.config_sections:
                if item in self.config:
                    config_cleaned[item] = copy.deepcopy(self.config[item])
            self.config = config_cleaned
            return True
        except:
            logger.exception("Error in 'clean_config()'")
            return False

    def save_config(self):
        self.config['GENERAL']['LAST_MODIFIED_TIME'] = int(time.time())
        with open(self.config_file_name, 'w') as f:
            f.write(json.dumps(self.config, indent=2))

    # if 'initial_chk_flag'==True and config file does not contain 'LAST_MODIFIED_TIME' item
    #   or time does not match file-modified timestamp then create backup of file
    # if 'initial_chk_flag'==False and a backup file matching current settings does not exist
    #   then create one
    def check_backup_config_file(self, initial_chk_flag=False):
        try:
            if os.path.exists(self.config_file_name):
                last_modified_time = self.get_item_int('GENERAL', 'LAST_MODIFIED_TIME')
                file_modified_time = int(os.path.getmtime(self.config_file_name))
                time_str = datetime.fromtimestamp(file_modified_time).strftime('%Y%m%d_%H%M%S')
                (fname_str, fext_str) = os.path.splitext(self.config_file_name)
                bkp_file_name = "{}_bkp_{}{}".format(fname_str, time_str, fext_str)
                # put backup file in 'cfg_bkp' directory (create it if needed)
                if not os.path.exists(self.cfg_bkp_dir_name):
                    os.makedirs(self.cfg_bkp_dir_name)
                bkp_file_path = os.path.join(self.cfg_bkp_dir_name, bkp_file_name)
                if initial_chk_flag:
                    if file_modified_time > 0 and abs(file_modified_time - last_modified_time) > 5:
                        logger.info("External configuration file modification detected")
                        self.backup_config_file(bkp_file_path)
                        return
                # only save if backup with same date/time and content not already present
                if (not os.path.exists(bkp_file_path)) or (not self.compare_config_file(bkp_file_path)):
                    if initial_chk_flag:
                        # don't back up config (at startup) if backup-config file(s) with same date
                        #  is already present (to prevent having too many auto-generated backup files)
                        date_str = datetime.fromtimestamp(file_modified_time).strftime('%Y%m%d')
                        f_name = "{}_bkp_{}*{}".format(fname_str, date_str, fext_str)
                        chk_file_path = os.path.join(self.cfg_bkp_dir_name, f_name)
                        if len(glob.glob(chk_file_path)) > 0:
                            logger.debug("Not backing up config (at startup) because backup-config file(s) with same date already present")
                            return
                    self.backup_config_file(bkp_file_path)
                else:
                    logger.debug("Not backing up config because backup-config file with same date/time already present")
                return bkp_file_name
        except Exception as ex:
            logger.warning("Error in 'check_backup_config_file()':  {}".format(ex))
        return ""

    def backup_config_file(self, bkp_file_path):
        try:
            logger.info("Making backup of configuration file, name: {}".format(bkp_file_path))
            shutil.copy2(self.config_file_name, bkp_file_path)
        except Exception as ex:
            logger.warning("Error in 'backup_config_file()':  {}".format(ex))

    def restore_config_file(self, bkp_file_path):
        try:
            logger.info("Restoring configuration file, name: {}".format(bkp_file_path))
            shutil.copy2(bkp_file_path, self.config_file_name)
        except Exception as ex:
            logger.warning("Error in 'restore_config_file()':  {}".format(ex))

    def compare_config_file(self, bkp_file_path):
        try:
            return filecmp.cmp(self.config_file_name, bkp_file_path)
        except Exception as ex:
            logger.warning("Error in 'compare_config_file()':  {}".format(ex))
            return False

    def get_sharable_config(self):
        sharable_config = copy.deepcopy(self.config)
        del sharable_config['SECRETS']
        return sharable_config


class migrateItem:
    def __init__(self, source, section='GENERAL', dest=None):
        self.source = source
        self.section = section
        self._dest = dest

    @property
    def dest(self):
        return self._dest if self._dest else self.source