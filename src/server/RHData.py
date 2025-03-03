#
# RaceData
# Provides abstraction for database and results page caches
#

import logging
logger = logging.getLogger(__name__)

import sqlalchemy
from sqlalchemy import create_engine, MetaData, Table, inspect
from sqlalchemy.exc import NoSuchTableError
from datetime import datetime
import os
import traceback
import shutil
import json
import glob
import RHUtils
import Database
import Results
from time import monotonic
from eventmanager import Evt
from filtermanager import Flt
from RHRace import RaceStatus, WinCondition, RacingMode, StagingTones
from Database import ProgramMethod, HeatAdvanceType, RoundType, HeatStatus

from FlaskAppObj import APP
APP.app_context().push()

Position_place_strings = None

class RHData():
    _OptionsCache = {} # Local Python cache for global settings
    TEAM_NAMES_LIST = [str(chr(i)) for i in range(65, 91)]  # list of 'A' to 'Z' strings

    def __init__(self, Events, RaceContext, SERVER_API, DB_FILE_NAME, DB_BKP_DIR_NAME):
        self._Events = Events
        self._racecontext = RaceContext
        self._SERVER_API = SERVER_API
        self._DB_FILE_NAME = DB_FILE_NAME
        self._DB_BKP_DIR_NAME = DB_BKP_DIR_NAME
        self._filters = RaceContext.filters

    def __(self, *args, **kwargs):
        return self._racecontext.language.__(*args, **kwargs)

    # Integrity Checking
    def check_integrity(self):
        try:
            if self.get_optionInt('server_api') < self._SERVER_API:
                logger.info('Old server API version; recovering database')
                return False
            if not Database.Profiles.query.count():
                logger.info('Profiles are empty; recovering database')
                return False
            if not Database.RaceFormat.query.count():
                logger.info('Formats are empty; recovering database')
                return False
            try:  # make sure no problems reading 'Heat' table data
                Database.Heat.query.all()
            except Exception as ex:
                logger.warning('Error reading Heat data; recovering database; err: ' + str(ex))
                return False
            if self.get_optionInt('server_api') > self._SERVER_API:
                logger.warning('Database API version ({}) is newer than server version ({})'.\
                               format(self.get_optionInt('server_api'), self._SERVER_API))
            return True
        except Exception as ex:
            logger.error('Error checking database integrity; err: ' + str(ex))
            return False

    # Caching
    def primeCache(self):
        settings = Database.GlobalSettings.query.all()
        self._OptionsCache = {} # empty cache
        for setting in settings:
            self._OptionsCache[setting.option_name] = setting.option_value

    # General
    def db_init(self, nofill=False, migrateDbApi=None):
        # Creates tables from database classes/models
        try:
            Database.initialize()
            Database.create_db_all()
            self.reset_all(nofill, migrateDbApi) # Fill with defaults
            return True
        except Exception as ex:
            logger.error('Error creating database: ' + str(ex))
            return False

    def do_reset_all(self, nofill, migrateDbApi):
        self.reset_pilots()
        if nofill:
            self.reset_heats(nofill=True)
        else:
            self.reset_heats()
        self.clear_race_data()
        self.reset_profiles()
        # (if older DB then co-op race formats will be added after recovery)
        self.reset_raceFormats(migrateDbApi is None or migrateDbApi >= 46)
        self.reset_raceClasses()
        self.reset_options()

    def reset_all(self, nofill=False, migrateDbApi=None):
        try:
            self.do_reset_all(nofill, migrateDbApi)
        except Exception as ex:
            logger.warning("Doing DB session rollback and retry after error: {}".format(ex))
            Database.DB_session.rollback()
            self.do_reset_all(nofill, migrateDbApi)

    def commit(self):
        try:
            Database.DB_session.commit()
            return True
        except Exception as ex:
            logger.error('Error writing to database: ' + str(ex))
            return False

    def rollback(self):
        try:
            Database.DB_session.rollback()
            return True
        except Exception as ex:
            logger.error('Error rolling back to database: ' + str(ex))
            return False

    def close(self):
        try:
            Database.DB_session.close()
            return True
        except Exception as ex:
            logger.error('Error closing to database: ' + str(ex))
            return False

    def clean(self):
        try:
            with Database.DB_engine.begin() as conn:
                conn.execute(sqlalchemy.text("VACUUM"))
            return True
        except Exception as ex:
            logger.error('Error cleaning database: ' + str(ex))
            return False

    def get_db_session_handle(self):
        return Database.DB_session()

    # Logs status of database connections; will be at 'debug' level unless # of connections gets large
    def check_log_db_conns(self):
        try:
            num_conns = Database.DB_engine.pool.checkedout()
            num_over = Database.DB_engine.pool.overflow()
            num_pool = Database.DB_engine.pool.checkedin()
            pool_size = Database.DB_engine.pool.size()
            if num_over <= 0 or num_conns <= pool_size:
                logger.debug("Database num_conns={}, num_over={}, num_in_pool={}, size={}".\
                            format(num_conns, num_over, num_pool, pool_size))
            elif num_over <= Database.DB_MAX_OVERFLOW / 5:
                logger.info("Database connections into overflow, num_conns={}, num_over={}, num_in_pool={}, size={}".\
                            format(num_conns, num_over, num_pool, pool_size))
            elif num_over < Database.DB_MAX_OVERFLOW:
                logger.warning("Database connections growing too large, num_conns={}, num_over={}, num_in_pool={}, size={}". \
                            format(num_conns, num_over, num_pool, pool_size))
            else:
                logger.error("Database connections overran overflow ({}), num_conns={}, num_over={}, num_in_pool={}, size={}". \
                               format(Database.DB_MAX_OVERFLOW, num_conns, num_over, num_pool, pool_size))
        except Exception as ex:
            logger.error("Error checking database connections: " + str(ex))

    # File Handling

    def backup_db_file(self, copy_flag, prefix_str=None, use_filename=None):
        self.close()
        self.clean()
        if not copy_flag:
            Database.close_database()
        try:     # generate timestamp from last-modified time of database file
            time_str = datetime.fromtimestamp(os.stat(self._DB_FILE_NAME).st_mtime).strftime('%Y%m%d_%H%M%S')
        except:  # if error then use 'now' timestamp
            time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        try:
            (dbname, dbext) = os.path.splitext(self._DB_FILE_NAME)
            if prefix_str:
                dbname = prefix_str + dbname
            bkp_name = self._DB_BKP_DIR_NAME + '/' + dbname + '_' + time_str + dbext
            if use_filename:
                bkp_name = self._DB_BKP_DIR_NAME + '/' + use_filename + dbext

            if not os.path.exists(self._DB_BKP_DIR_NAME):
                os.makedirs(self._DB_BKP_DIR_NAME)
            RHUtils.checkSetFileOwnerPi(self._DB_BKP_DIR_NAME)
            if os.path.isfile(bkp_name):  # if target file exists then use 'now' timestamp
                time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                bkp_name = self._DB_BKP_DIR_NAME + '/' + dbname + '_' + time_str + dbext
            if copy_flag:
                shutil.copy2(self._DB_FILE_NAME, bkp_name)
                logger.info('Copied database file to:  ' + bkp_name)
            else:
                Database.close_database()
                os.renames(self._DB_FILE_NAME, bkp_name)
                logger.info('Moved old database file to:  ' + bkp_name)
            RHUtils.checkSetFileOwnerPi(bkp_name)
        except Exception:
            logger.exception('Error backing up database file')
        return bkp_name

    def delete_old_db_autoBkp_files(self, num_keep_val, prefix_str, DB_AUTOBKP_NUM_KEEP_STR):
        num_del = 0
        try:
            num_keep_val = int(num_keep_val)  # make sure this is numeric
            if num_keep_val > 0:
                (dbname, dbext) = os.path.splitext(self._DB_FILE_NAME)
                if prefix_str:
                    dbname = prefix_str + dbname
                file_list = list(filter(os.path.isfile, glob.glob(self._DB_BKP_DIR_NAME + \
                                                        '/' + dbname + '*' + dbext)))
                file_list.sort(key=os.path.getmtime)  # sort by last-modified time
                if len(file_list) > num_keep_val:
                    if num_keep_val > 0:
                        file_list = file_list[:(-num_keep_val)]
                    for del_path in file_list:
                        os.remove(del_path)
                        num_del += 1
            elif num_keep_val < 0:
                raise ValueError("Negative value")
            if num_del > 0:
                logger.info("Removed {} old DB-autoBkp file(s)".format(num_del))
        except ValueError:
            logger.error("Value for '{}' in configuration is invalid: {}".\
                            format(DB_AUTOBKP_NUM_KEEP_STR, num_keep_val))
        except Exception as ex:
            logger.error("Error removing old DB-autoBkp files: " + str(ex))

    # Migration

    def get_legacy_table_data(self, engine, metadata, table_name):
        try:
            output = []
            with engine.begin() as conn:
                if not table_name in metadata.tables:
                    raise NoSuchTableError
                table = Table(table_name, metadata, autoload=True)
                data = conn.execute(sqlalchemy.text("SELECT * from {}".format(table_name))).all()
                for row in data:
                    d = {}
                    cnt = 0
                    for item in row:  # create dict of {columnName:columnValue} items for row
                        d[table.columns[cnt].key] = item
                        cnt += 1
                    output.append(d)  # one for each row in table
            return output
        except NoSuchTableError:
            logger.debug('Table "{}" not found in previous database'.format(table_name))
        except Exception as ex:
            logger.warning('Unable to read "{0}" table from previous database: {1}'.format(table_name, ex))
        return None

    def restore_table(self, class_type, table_query_data, **kwargs):
        if table_query_data:
            mapped_instance = inspect(class_type)
            table_name_str = "???"
            was_empty_flag = len(class_type.query.all()) <= 0
            try:
                table_name_str = getattr(class_type, '__name__', '???')
                logger.debug("Restoring database table '{}' (len={})".format(table_name_str, len(table_query_data)))
                restored_row_count = 0
                last_table_row_id = -1
                for table_query_row in table_query_data:  # for each row of data queried from previous database
                    try:
                        # check if row is 'Pilot' entry that should be ignored
                        if (class_type is not Database.Pilot) or getattr(table_query_row, 'callsign', '') != '-' or \
                                                      getattr(table_query_row, 'name', '') != '-None-':

                            # check if row with matching 'id' value already exists in new DB table
                            if (not was_empty_flag) and 'id' in mapped_instance.attrs.keys() and 'id' in table_query_row.keys():
                                table_row_id = table_query_row['id']
                                if table_row_id != last_table_row_id:
                                    matching_row = class_type.query.filter(getattr(class_type,'id')==table_row_id).first()
                                    last_table_row_id = table_row_id
                                else:  # if source table row 'id' value same as last row then create new row
                                    table_row_id = None
                                    matching_row = None
                            else:
                                table_row_id = None
                                matching_row = None

                            # if row with matching 'id' value was found then update it; otherwise create new row data
                            db_row_update = matching_row if matching_row is not None else class_type()

                            columns_list = mapped_instance.columns
                            columns_keys = columns_list.keys()
                            for col_key in columns_keys:  # for each column in new database table
                                col_obj = columns_list.get(col_key)
                                col_name = getattr(col_obj, 'name', col_key)
                                if col_name in table_query_row.keys() and table_query_row[col_name] is not None:  # matching column exists in previous DB table
                                    col_val = table_query_row[col_name]
                                    try:  # get column type in new database table
                                        if str(col_obj.type) != 'BLOB':
                                            table_col_type = col_obj.type.python_type
                                        else:
                                            table_col_type = None
                                            if logger.getEffectiveLevel() <= logging.DEBUG and len(table_query_data) <= 25:
                                                logger.debug("restore_table ('{}'): colkey={}, colname={}, coltype=BLOB, valtype={}". \
                                                        format(table_name_str, col_key, col_name, getattr(type(col_val), '__name__', '???')))
                                    except Exception as ex:
                                        logger.debug("Unable to determine type for column '{}' in 'restore_table' ('{}'): {}".\
                                                     format(col_key, table_name_str, getattr(type(ex), '__name__', '????')))
                                        table_col_type = None
                                    if table_col_type is not None and col_val is not None:
                                        col_val_str = str(col_val)
                                        if len(col_val_str) >= 50:
                                            col_val_str = col_val_str[:50] + "..."
                                        if logger.getEffectiveLevel() <= logging.DEBUG and len(table_query_data) <= 25:
                                            logger.debug("restore_table ('{}'): colkey={}, colname={}, coltype={}, val={}, valtype={}".\
                                                         format(table_name_str, col_key, col_name, getattr(table_col_type, '__name__', '???'), \
                                                                col_val_str, getattr(type(col_val), '__name__', '???')))
                                        try:
                                            col_val = table_col_type(col_val)  # explicitly cast value to new-DB column type
                                        except:
                                            logger.warning("Using default because of mismatched type in 'restore_table' ('{}'): col={}, coltype={}, newval={}, newtype={}".\
                                                           format(table_name_str, col_key, getattr(table_col_type, '__name__', '???'), \
                                                                  col_val_str, getattr(type(col_val), '__name__', '???')))
                                            col_val = kwargs['defaults'].get(col_key)
                                else:  # matching column does not exist in previous DB table; use default value
                                    col_val = kwargs['defaults'].get(col_key) if col_key != 'id' else None

                                if col_val is not None:
                                    setattr(db_row_update, col_key, col_val)

                            if matching_row is None:  # if new row data then add to table
                                Database.DB_session.add(db_row_update)
                                if logger.getEffectiveLevel() <= logging.DEBUG and len(table_query_data) <= 25:
                                    logger.debug("restore_table: added new row to table '{}'".format(table_name_str))
                            else:
                                if logger.getEffectiveLevel() <= logging.DEBUG and len(table_query_data) <= 25:
                                    logger.debug("restore_table: updated row in table '{}', id={}".format(table_name_str, table_row_id))

                            Database.DB_session.flush()
                            restored_row_count += 1

                    except Exception as ex:
                        logger.warning("Error restoring row for '{}' table from previous database: {}".\
                                       format(table_name_str, getattr(type(ex), '__name__', '????')))
                        logger.debug(traceback.format_exc())

                if restored_row_count > 0:
                    logger.info("Database table '{}' restored (rowcount={})".format(table_name_str, restored_row_count))
                else:
                    logger.info("No rows restored for database table '{}'".format(table_name_str))

            except Exception as ex:
                logger.warning('Error restoring "{}" table from previous database: {}'.format(table_name_str, getattr(type(ex), '__name__', '????')))
                logger.debug(traceback.format_exc())
        else:
            logger.debug('Unable to restore "{}" table: no data'.format(getattr(class_type, '__name__', '???')))

    def recover_database(self, dbfile, **kwargs):
        recover_status = {
            'stage_0': False,
            'stage_1': False,
            'stage_2': False,
        }

        migrate_db_api = 0  # default to delta5 or very old RH versions
        options_query_data = None
        pilot_query_data = None
        heat_query_data = None
        heatNode_query_data = None
        raceFormat_query_data = None
        profiles_query_data = None
        raceClass_query_data = None

        # stage 0: collect data from file
        try:
            logger.info('Recovering data from previous database')

            # load file directly
            engine = create_engine('sqlite:///%s' % dbfile)
            metadata = MetaData()
            metadata.reflect(engine)

            options_query_data = self.get_legacy_table_data(engine, metadata, 'global_settings')

            if options_query_data:
                for row in options_query_data:
                    if row['option_name'] == 'server_api':
                        migrate_db_api = int(row['option_value'])
                        break

            if migrate_db_api > self._SERVER_API:
                raise ValueError('Database version is newer than server version')

            pilot_query_data = self.get_legacy_table_data(engine, metadata, 'pilot')
            heat_query_data = self.get_legacy_table_data(engine, metadata, 'heat')
            heatNode_query_data = self.get_legacy_table_data(engine, metadata, 'heat_node')
            raceFormat_query_data = self.get_legacy_table_data(engine, metadata, 'race_format')
            profiles_query_data = self.get_legacy_table_data(engine, metadata, 'profiles')
            raceClass_query_data = self.get_legacy_table_data(engine, metadata, 'race_class')
            raceMeta_query_data = self.get_legacy_table_data(engine, metadata, 'saved_race_meta')
            racePilot_query_data = self.get_legacy_table_data(engine, metadata, 'saved_pilot_race')
            raceLap_query_data = self.get_legacy_table_data(engine, metadata, 'saved_race_lap')
            pilotAttribute_query_data = self.get_legacy_table_data(engine, metadata, 'pilot_attribute')
            heatAttribute_query_data = self.get_legacy_table_data(engine, metadata, 'heat_attribute')
            raceClassAttribute_query_data = self.get_legacy_table_data(engine, metadata, 'race_class_attribute')
            savedRaceAttribute_query_data = self.get_legacy_table_data(engine, metadata, 'saved_race_meta_attribute')
            raceFormatAttribute_query_data = self.get_legacy_table_data(engine, metadata, 'race_format_attribute')

            engine.dispose() # close connection after loading

            carryoverOpts = [
                "timerName",
                "timerLogo",
                "hue_0",
                "sat_0",
                "lum_0_low",
                "lum_0_high",
                "contrast_0_low",
                "contrast_0_high",
                "hue_1",
                "sat_1",
                "lum_1_low",
                "lum_1_high",
                "contrast_1_low",
                "contrast_1_high",
                "currentLanguage",
                "timeFormat",
                "timeFormatPhonetic",
                "currentProfile",
                "currentFormat",
                "currentHeat",
                "calibrationMode",
                "MinLapSec",
                "MinLapBehavior",
                "eventName",
                "eventDescription",
                "ledEffects",
                "ledBrightness",
                "ledColorNodes",
                "ledColorFreqs",
                "startThreshLowerAmount",
                "startThreshLowerDuration",
                "voiceCallouts",
                "actions",
                "consecutivesCount"
            ]

            # Carry over registered plugin options
            for field in self._racecontext.rhui.general_settings:
                carryoverOpts.append(field.name)

            # RSSI reduced by half for 2.0.0
            if migrate_db_api < 23:
                for profile in profiles_query_data:
                    if 'enter_ats' in profile and profile['enter_ats']:
                        enter_ats = json.loads(profile['enter_ats'])
                        enter_ats["v"] = [(val/2 if val else None) for val in enter_ats["v"]]
                        profile['enter_ats'] = json.dumps(enter_ats)
                    if 'exit_ats' in profile and profile['exit_ats']:
                        exit_ats = json.loads(profile['exit_ats'])
                        exit_ats["v"] = [(val/2 if val else None) for val in exit_ats["v"]]
                        profile['exit_ats'] = json.dumps(exit_ats)

            # Convert frequencies
            if migrate_db_api < 30:
                for profile in profiles_query_data:
                    if 'frequencies' in profile and profile['frequencies']:
                        freqs = json.loads(profile['frequencies'])
                        freqs["b"] = [None for _i in range(max(self._racecontext.race.num_nodes,8))]
                        freqs["c"] = [None for _i in range(max(self._racecontext.race.num_nodes,8))]
                        profile['frequencies'] = json.dumps(freqs)

            recover_status['stage_0'] = True
        except Exception as ex:
            logger.warning('Error reading data from previous database (stage 0):  ' + str(ex))
            logger.debug(traceback.format_exc())

        if "startup" in kwargs:
            self.backup_db_file(False)  # rename and move DB file

        self.db_init(nofill=True, migrateDbApi=migrate_db_api)

        # stage 1: recover pilots, heats, heatnodes, format, profile, class, options
        if recover_status['stage_0'] == True:
            try:
                if pilot_query_data:
                    Database.DB_session.query(Database.Pilot).delete()
                    self.restore_table(Database.Pilot, pilot_query_data, defaults={
                            'name': 'New Pilot',
                            'callsign': 'New Callsign',
                            'team': RHUtils.DEF_TEAM_NAME,
                            'phonetic': '',
                            'color': None,
                            'used_frequencies': None
                        })
                    for pilot in Database.Pilot.query.all():
                        if not pilot.color:
                            pilot.color = RHUtils.hslToHex(False, 100, 50)
                else:
                    self.reset_pilots()

                if migrate_db_api < 27:
                    # old heat DB structure; migrate node 0 to heat table

                    # build list of heat meta
                    heat_extracted_meta = []
                    if heat_query_data and len(heat_query_data):
                        for row in heat_query_data:
                            if 'node_index' in row:
                                if row['node_index'] == 0:
                                    new_row = {}
                                    new_row['id'] = row['heat_id']
                                    if 'note' in row:
                                        new_row['name'] = row['note']
                                    if 'class_id' in row:
                                        new_row['class_id'] = row['class_id']

                        self.restore_table(Database.Heat, heat_extracted_meta, defaults={
                                'name': None,
                                'class_id': RHUtils.CLASS_ID_NONE,
                                'results': None,
                                '_cache_status': json.dumps({
                                    'data_ver': monotonic(),
                                    'build_ver': None
                                }),
                                'order': None,
                                'status': 0,
                                'auto_frequency': False
                            })

                        # extract pilots from heats and load into heatnode
                        heatnode_extracted_data = []
                        heatnode_dummy_id = 0
                        for row in heat_query_data:
                            heatnode_row = {}
                            heatnode_row['id'] = heatnode_dummy_id
                            heatnode_row['heat_id'] = int(row['heat_id'])
                            heatnode_row['node_index'] = int(row['node_index'])
                            heatnode_row['pilot_id'] = int(row['pilot_id'])
                            heatnode_row['method'] = 0
                            heatnode_row['seed_rank'] = None
                            heatnode_row['seed_id'] = None
                            heatnode_extracted_data.append(heatnode_row)
                            heatnode_dummy_id += 1

                        Database.DB_session.query(Database.HeatNode).delete()
                        self.restore_table(Database.HeatNode, heatnode_extracted_data, defaults={
                                'pilot_id': RHUtils.PILOT_ID_NONE,
                                'color': None
                            })
                    else:
                        self.reset_heats()
                else:
                    # current heat structure; use basic migration

                    if heat_query_data:
                        self.restore_table(Database.Heat, heat_query_data, defaults={
                                'class_id': RHUtils.CLASS_ID_NONE,
                                'results': None,
                                '_cache_status': json.dumps({
                                    'data_ver': monotonic(),
                                    'build_ver': None
                                }),
                                'order': None,
                                'status': 0,
                                'group_id': 0,
                                'auto_frequency': False
                            })
                        self.restore_table(Database.HeatNode, heatNode_query_data, defaults={
                                'pilot_id': RHUtils.PILOT_ID_NONE,
                                'color': None,
                                'method': 0,
                                'seed_rank': None,
                                'seed_id': None
                            })

                        self._racecontext.race.current_heat = self.get_first_heat().id
                    else:
                        self.reset_heats()

                if raceFormat_query_data:
                    # Convert old staging
                    if migrate_db_api < 33:
                        for raceFormat in raceFormat_query_data:
                            if 'staging_tones' in raceFormat and raceFormat['staging_tones'] == StagingTones.TONES_ONE:
                                raceFormat['staging_fixed_tones'] = 1

                                if 'start_delay_min' in raceFormat and raceFormat['start_delay_min']:
                                    raceFormat['start_delay_min_ms'] = raceFormat['start_delay_min'] * 1000
                                    del raceFormat['start_delay_min']

                                if 'start_delay_max' in raceFormat and raceFormat['start_delay_max']:
                                    if 'start_delay_min_ms' in raceFormat:
                                        raceFormat['start_delay_max_ms'] = (raceFormat['start_delay_max'] * 1000) - raceFormat['start_delay_min_ms']
                                        if raceFormat['start_delay_max_ms'] < 0:
                                            raceFormat['start_delay_max_ms'] = 0
                                    del raceFormat['start_delay_max']

                            elif 'staging_tones' in raceFormat and raceFormat['staging_tones'] == StagingTones.TONES_ALL:
                                raceFormat['staging_tones'] = StagingTones.TONES_ALL

                                if 'start_delay_min' in raceFormat and raceFormat['start_delay_min']:
                                    raceFormat['staging_fixed_tones'] = raceFormat['start_delay_min']
                                    raceFormat['start_delay_min_ms'] = 1000
                                    del raceFormat['start_delay_min']

                                if 'start_delay_max' in raceFormat and raceFormat['start_delay_max']:
                                    if 'staging_fixed_tones' in raceFormat:
                                        raceFormat['start_delay_max_ms'] = (raceFormat['start_delay_max'] * 1000) - (raceFormat['staging_fixed_tones'] * 1000)
                                        if raceFormat['start_delay_max_ms'] < 0:
                                            raceFormat['start_delay_max_ms'] = 0
                                    del raceFormat['start_delay_max']

                            else: # None or unsupported
                                raceFormat['staging_fixed_tones'] = 0
                                raceFormat['staging_tones'] = StagingTones.TONES_NONE

                                if 'start_delay_min' in raceFormat and raceFormat['start_delay_min']:
                                    raceFormat['start_delay_min_ms'] = raceFormat['start_delay_min'] * 1000
                                    del raceFormat['start_delay_min']

                                if 'start_delay_max' in raceFormat and raceFormat['start_delay_max']:
                                    raceFormat['start_delay_max_ms'] = (raceFormat['start_delay_max'] * 1000) - raceFormat['start_delay_min_ms']
                                    if raceFormat['start_delay_max_ms'] < 0:
                                        raceFormat['start_delay_max_ms'] = 0
                                    del raceFormat['start_delay_max']

                    self.restore_table(Database.RaceFormat, raceFormat_query_data, defaults={
                        'name': self.__("Migrated Format"),
                        'unlimited_time': 0,
                        'race_time_sec': 120,
                        'lap_grace_sec': -1,
                        'staging_fixed_tones': 3,
                        'start_delay_min_ms': 1000,
                        'start_delay_max_ms': 0,
                        'staging_delay_tones': 0,
                        'number_laps_win': 0,
                        'win_condition': WinCondition.MOST_LAPS,
                        'team_racing_mode': RacingMode.INDIVIDUAL,
                        'points_method': None
                    })
                    if migrate_db_api < 46:
                        self.add_coopRaceFormats()
                        logger.info("Added co-op race formats")
                else:
                    self.reset_raceFormats()

                if profiles_query_data:
                    self.restore_table(Database.Profiles, profiles_query_data, defaults={
                            'name': self.__("Migrated Profile"),
                            'frequencies': json.dumps(self.default_frequencies()),
                            'enter_ats': json.dumps({'v': [None for _i in range(max(self._racecontext.race.num_nodes,8))]}),
                            'exit_ats': json.dumps({'v': [None for _i in range(max(self._racecontext.race.num_nodes,8))]}),
                            'f_ratio': None
                        })
                else:
                    self.reset_profiles()

                self.restore_table(Database.RaceClass, raceClass_query_data, defaults={
                        'name': 'New class',
                        'format_id': 0,
                        'results': None,
                        '_cache_status': json.dumps({
                            'data_ver': monotonic(),
                            'build_ver': None
                        }),
                        'ranking': None,
                        'rank_settings': None,
                        '_rank_status': json.dumps({
                            'data_ver': monotonic(),
                            'build_ver': None
                        }),
                        'win_condition': 0,
                        'rounds': 0,
                        'heat_advance_type': 1,
                        'round_type': 0,
                        'order': None,
                    })

                self.reset_options()
                if options_query_data:
                    if migrate_db_api == self._SERVER_API:
                        for opt in options_query_data:
                            self.set_option(opt['option_name'], opt['option_value'])
                    else:
                        for opt in options_query_data:
                            if opt['option_name'] in carryoverOpts:
                                self.set_option(opt['option_name'], opt['option_value'])

                logger.info('UI Options restored')

                self.restore_table(Database.PilotAttribute, pilotAttribute_query_data, defaults={
                        'name': '',
                        'value': None
                    })

                self.restore_table(Database.HeatAttribute, heatAttribute_query_data, defaults={
                        'name': '',
                        'value': None
                    })

                self.restore_table(Database.RaceClassAttribute, raceClassAttribute_query_data, defaults={
                        'name': '',
                        'value': None
                    })

                self.restore_table(Database.SavedRaceMetaAttribute, savedRaceAttribute_query_data, defaults={
                        'name': '',
                        'value': None
                    })

                self.restore_table(Database.RaceFormatAttribute, raceFormatAttribute_query_data, defaults={
                        'name': '',
                        'value': None
                    })

                # Many options migrated to serverconfig in 4.1
                if "startup" in kwargs and migrate_db_api < 44:
                    self._racecontext.serverconfig.migrate_legacy_db_keys()

                recover_status['stage_1'] = True
            except Exception as ex:
                logger.warning('Error while writing data from previous database (stage 1):  ' + str(ex))
                logger.debug(traceback.format_exc())
                # failed recovery, db reset
                try:
                    self.reset_all()
                    self.commit()
                    self.primeCache() # refresh Options cache
                    self._Events.trigger(Evt.DATABASE_RECOVER)
                except:
                    logger.exception("Exception performing db reset in 'recover_database()'")
                return recover_status

            # stage 2: recover race result data
            if recover_status['stage_1'] == True:
                try:
                    if migrate_db_api < 23:
                        # don't attempt to migrate race data older than 2.0
                        logger.warning('Race data older than v2.0; skipping results migration')
                    else:
                        self.restore_table(Database.SavedRaceMeta, raceMeta_query_data, defaults={
                            'results': None,
                            '_cache_status': json.dumps({
                                'data_ver': monotonic(),
                                'build_ver': None
                            })
                        })
                        self.restore_table(Database.SavedPilotRace, racePilot_query_data, defaults={
                            'history_values': None,
                            'history_times': None,
                            'penalty_time': None,
                            'penalty_desc': None,
                            'enter_at': None,
                            'exit_at': None,
                            'frequency': None,
                        })

                        for lap in raceLap_query_data:
                            if 'lap_time' in lap and (type(lap['lap_time']) == str or lap['lap_time'] is None):
                                lap['lap_time'] = 0

                        self.restore_table(Database.SavedRaceLap, raceLap_query_data, defaults={
                            'source': None,
                            'deleted': False
                        })

                    recover_status['stage_2'] = True
                except Exception as ex:
                    logger.warning('Error while writing data from previous database (stage 2):  ' + str(ex))
                    logger.debug(traceback.format_exc())

        self.commit()

        self.primeCache() # refresh Options cache

        self._Events.trigger(Evt.DATABASE_RECOVER)

        return recover_status

    def default_frequencies(self):
        '''Set node frequencies, R1367 for 4, IMD6C+ for 5+.'''
        if self._racecontext.race.num_nodes < 5:
            freqs = {
                'b': ['R', 'R', 'R', 'R'],
                'c': [1, 3, 6, 7],
                'f': [5658, 5732, 5843, 5880]
            }
        else:
            freqs = {
                'b': ['R', 'R', 'F', 'F', 'R', 'R'],
                'c': [1, 2, 2, 4, 7, 8],
                'f': [5658, 5695, 5760, 5800, 5880, 5917]
            }

        while self._racecontext.race.num_nodes > len(freqs['f']):
            freqs['b'].append(None)
            freqs['c'].append(None)
            freqs['f'].append(RHUtils.FREQUENCY_ID_NONE)

        return freqs

    # Pilots
    def resolve_pilot_from_pilot_or_id(self, pilot_or_id):
        if isinstance(pilot_or_id, Database.Pilot):
            return pilot_or_id
        else:
            return Database.Pilot.query.get(pilot_or_id)

    def resolve_id_from_pilot_or_id(self, pilot_or_id):
        if isinstance(pilot_or_id, Database.Pilot):
            return pilot_or_id.id
        else:
            return pilot_or_id

    def get_pilot(self, pilot_id):
        if pilot_id:
            return Database.Pilot.query.get(pilot_id)
        return None

    def get_pilots(self):
        return Database.Pilot.query.all()

    def get_pilot_for_callsign(self, callsign):
        pilots = self.get_pilots()
        if pilots:
            for pilot in pilots:
                if pilot.callsign == callsign:
                    return pilot
        return None

    def add_pilot(self, init=None):
        color = RHUtils.hslToHex(False, 100, 50)

        new_pilot = Database.Pilot(
            name='',
            callsign='',
            team=RHUtils.DEF_TEAM_NAME,
            phonetic='',
            color=color,
            used_frequencies=None)

        Database.DB_session.add(new_pilot)
        Database.DB_session.flush()

        new_pilot.name=self.__('~Pilot %d Name') % (new_pilot.id)
        new_pilot.callsign=self.__('~Callsign %d') % (new_pilot.id)

        if init:
            if 'name' in init:
                new_pilot.name = init['name']
            if 'callsign' in init:
                new_pilot.callsign = init['callsign']
            if 'team' in init:
                new_pilot.team = init['team']
            if 'phonetic' in init:
                new_pilot.phonetic = init['phonetic']
            if 'color' in init:
                new_pilot.color = init['color']

        new_pilot = self._filters.run_filters(Flt.PILOT_ADD, new_pilot)

        self.commit()

        # ensure clean attributes on creation
        for attr in self.get_pilot_attributes(new_pilot):
            Database.DB_session.delete(attr)

        self.commit()

        self._Events.trigger(Evt.PILOT_ADD, {
            'pilot_id': new_pilot.id,
            })

        logger.info('Pilot added: Pilot {0}'.format(new_pilot.id))

        return new_pilot

    def alter_pilot(self, data):
        pilot_id = data['pilot_id']
        pilot = Database.Pilot.query.get(pilot_id)
        if 'callsign' in data:
            pilot.callsign = data['callsign']
        if 'team_name' in data:
            pilot.team = data['team_name']
        if 'phonetic' in data:
            pilot.phonetic = data['phonetic']
        if 'name' in data:
            pilot.name = data['name']
        if 'color' in data:
            pilot.color = data['color']

        if 'pilot_attr' in data and 'value' in data:
            attribute = Database.PilotAttribute.query.filter_by(id=pilot_id, name=data['pilot_attr']).one_or_none()
            if attribute:
                attribute.value = data['value']
            else:
                Database.DB_session.add(Database.PilotAttribute(id=pilot_id, name=data['pilot_attr'], value=data['value']))

        pilot = self._filters.run_filters(Flt.PILOT_ALTER, pilot)

        self.commit()

        self._racecontext.race.clear_results()  # refresh current leaderboard

        self._Events.trigger(Evt.PILOT_ALTER, {
            'pilot_id': pilot_id,
            })

        logger.info('Altered pilot {0} to {1}'.format(pilot_id, data))

        race_list = []
        if 'callsign' in data or 'team_name' in data:
            heatnodes = Database.HeatNode.query.filter_by(pilot_id=pilot_id).all()
            if heatnodes:
                for heatnode in heatnodes:
                    heat = self.get_heat(heatnode.heat_id)
                    self.clear_results_heat(heat)

                    if heat.class_id != RHUtils.CLASS_ID_NONE:
                        self.clear_results_raceClass(heat.class_id)

                    for race in Database.SavedRaceMeta.query.filter_by(heat_id=heatnode.heat_id).all():
                        race_list.append(race)

            if len(race_list):
                self._racecontext.pagecache.set_valid(False)
                self.clear_results_event()

                for race in race_list:
                    self.clear_results_savedRaceMeta(race)

                self.commit()

        return pilot, race_list

    def set_pilot_used_frequency(self, pilot_or_id, frequency):
        pilot = self.resolve_pilot_from_pilot_or_id(pilot_or_id) 
        if pilot:
            if pilot.used_frequencies:
                used_freqs = json.loads(pilot.used_frequencies)
            else:
                used_freqs = []

            for idx, freq in enumerate(used_freqs):
                if freq['f'] == frequency['f'] and \
                    freq['b'] == frequency['b'] and \
                    freq['c'] == frequency['c']:

                    del used_freqs[idx]

            used_freqs.append(frequency)

            pilot.used_frequencies = json.dumps(used_freqs)
            self.commit()
            return pilot
        return False

    def reset_pilot_used_frequencies(self):
        for pilot in self.get_pilots():
            pilot.used_frequencies = ""
        self.commit()
        return True

    def delete_pilot(self, pilot_or_id):
        pilot = self.resolve_pilot_from_pilot_or_id(pilot_or_id)

        if pilot:
            if self.savedPilotRaces_has_pilot(pilot.id):
                logger.info('Refusing to delete pilot {0}: is in use'.format(pilot.id))
                return False
            else:
                deleted_pilot_id = pilot.id

                for attr in self.get_pilot_attributes(pilot_or_id):
                    Database.DB_session.delete(attr)

                Database.DB_session.delete(pilot)
                for heatNode in Database.HeatNode.query.all():
                    if heatNode.pilot_id == pilot.id:
                        heatNode.pilot_id = RHUtils.PILOT_ID_NONE
                self.commit()

                self._Events.trigger(Evt.PILOT_DELETE, {
                    'pilot_id': deleted_pilot_id,
                    })

                logger.info('Pilot {0} deleted'.format(deleted_pilot_id))

                self._racecontext.race.clear_results() # refresh leaderboard

                return True
        else:
            logger.info("No pilot to delete")
            return False
    def get_recent_pilot_node(self, pilot_id):
        return Database.HeatNode.query.filter_by(pilot_id=pilot_id).order_by(Database.HeatNode.id.desc()).first()

    def clear_pilots(self):
        Database.DB_session.query(Database.Pilot).delete()
        Database.DB_session.query(Database.PilotAttribute).delete()
        self.commit()

    def reset_pilots(self):
        self.clear_pilots()
        logger.info('Database pilots reset')
        return True

    #Pilot Attributes
    def get_pilot_attribute(self, pilot_or_id, name):
        pilot_id = self.resolve_id_from_pilot_or_id(pilot_or_id)
        return Database.PilotAttribute.query.filter_by(id=pilot_id, name=name).one_or_none()

    def get_pilot_attribute_value(self, pilot_or_id, name, default_value=None):
        pilot_id = self.resolve_id_from_pilot_or_id(pilot_or_id)
        attr = Database.PilotAttribute.query.filter_by(id=pilot_id, name=name).one_or_none()

        if attr is not None:
            return attr.value
        else:
            return default_value

    def get_pilot_attributes(self, pilot_or_id):
        pilot_id = self.resolve_id_from_pilot_or_id(pilot_or_id)
        return Database.PilotAttribute.query.filter_by(id=pilot_id).all()

    def get_pilot_id_by_attribute(self, name, value):
        attrs = Database.PilotAttribute.query.filter_by(name=name, value=value).all()
        return [attr.id for attr in attrs]

    # Heats
    def resolve_heat_from_heat_or_id(self, heat_or_id):
        if isinstance(heat_or_id, Database.Heat):
            return heat_or_id
        else:
            return Database.Heat.query.get(heat_or_id)

    def resolve_id_from_heat_or_id(self, heat_or_id):
        if isinstance(heat_or_id, Database.Heat):
            return heat_or_id.id
        else:
            return heat_or_id

    def get_heat(self, heat_id):
        return Database.Heat.query.get(heat_id)

    def get_heats(self):
        return Database.Heat.query.all()

    def get_heats_by_class(self, class_id):
        return Database.Heat.query.filter_by(class_id=class_id).all()

    def get_recent_heats_by_class(self, class_id, limit):
        return Database.Heat.query.filter_by(class_id=class_id).order_by(Database.Heat.id.desc()).limit(limit).all()

    def get_first_heat(self):
        return Database.Heat.query.first()

    def get_heat_auto_name(self, heat):
        if heat.class_id:
            race_class = self.get_raceClass(heat.class_id)

            if race_class:
                class_heats = self.get_heats_by_class(heat.class_id)
                class_heats = [h for h in class_heats if h.id != heat.id]

                if race_class.round_type == RoundType.GROUPED:
                    class_heats = [h for h in class_heats if h.group_id == heat.group_id]

                return RHUtils.unique_name_from_base(race_class.display_name,
                    [rc.auto_name for rc in class_heats])
        return None

    def regen_heat_auto_name(self, heat_or_id):
        heat = self.resolve_heat_from_heat_or_id(heat_or_id)
        heat.auto_name = self.get_heat_auto_name(heat)
        self.commit()

    def add_heat(self, init=None, initPilots=None):
        # Add new heat
        new_heat = Database.Heat(
            class_id=RHUtils.CLASS_ID_NONE,
            _cache_status=json.dumps({
                'data_ver': monotonic(),
                'build_ver': None
            }),
            order=None,
            status=HeatStatus.PLANNED,
            group_id=0,
            auto_frequency=False
            )

        if init:
            if 'class_id' in init:
                new_heat.class_id = init['class_id']
            if 'name' in init:
                new_heat.name = init['name']
            if 'auto_frequency' in init:
                new_heat.auto_frequency = init['auto_frequency']
            if 'group_id' in init:
                new_heat.group_id = init['group_id']

            defaultMethod = init['defaultMethod'] if 'defaultMethod' in init else ProgramMethod.ASSIGN
        else:
            defaultMethod = ProgramMethod.ASSIGN

        Database.DB_session.add(new_heat)
        Database.DB_session.flush()
        Database.DB_session.refresh(new_heat)

        new_heat.auto_name = self.get_heat_auto_name(new_heat)

        # Add heatnodes
        for node_index in range(self._racecontext.race.num_nodes):
            new_heatNode = Database.HeatNode(
                heat_id=new_heat.id,
                node_index=node_index,
                pilot_id=RHUtils.PILOT_ID_NONE,
                method=defaultMethod,
                seed_rank=None,
                seed_id=None
            )

            if initPilots and node_index in initPilots:
                new_heatNode.pilot_id = initPilots[node_index]

            Database.DB_session.add(new_heatNode)

        new_heat = self._filters.run_filters(Flt.HEAT_ADD, new_heat)

        self.commit()

        # ensure clean attributes on creation
        for attr in self.get_heat_attributes(new_heat):
            Database.DB_session.delete(attr)

        self.commit()

        self._Events.trigger(Evt.HEAT_ADD, {
            'heat_id': new_heat.id,
            })

        logger.info('Heat added: Heat {0}'.format(new_heat.id))

        return new_heat

    def duplicate_heat(self, source_heat_or_id, **kwargs):
        # Add new heat by duplicating an existing one
        source_heat = self.resolve_heat_from_heat_or_id(source_heat_or_id)

        if 'new_heat_name' in kwargs:
            new_heat_name = kwargs['new_heat_name']
        elif source_heat.name:
            all_heat_names = [heat.name for heat in self.get_heats()]
            new_heat_name = RHUtils.uniqueName(source_heat.name, all_heat_names)
        else:
            new_heat_name = ''

        if 'dest_class' in kwargs:
            new_class = kwargs['dest_class']
        else:
            new_class = source_heat.class_id

        if 'group_id' in kwargs:
            new_group = kwargs['group_id']
        else:
            new_group = source_heat.group_id

        new_heat = Database.Heat(
            name=new_heat_name,
            class_id=new_class,
            group_id=new_group,
            results=None,
            _cache_status=json.dumps({
                'data_ver': monotonic(),
                'build_ver': None
            }),
            status=0,
            auto_frequency=source_heat.auto_frequency
            )

        Database.DB_session.add(new_heat)
        Database.DB_session.flush()
        Database.DB_session.refresh(new_heat)

        new_heat.auto_name = self.get_heat_auto_name(new_heat)

        for source_heatnode in self.get_heatNodes_by_heat(source_heat.id):
            new_heatnode = Database.HeatNode(heat_id=new_heat.id,
                node_index=source_heatnode.node_index,
                pilot_id=source_heatnode.pilot_id,
                method=source_heatnode.method,
                seed_rank=source_heatnode.seed_rank,
                seed_id=source_heatnode.seed_id
                )
            Database.DB_session.add(new_heatnode)

        new_heat = self._filters.run_filters(Flt.HEAT_DUPLICATE, new_heat)

        self.commit()

        self._Events.trigger(Evt.HEAT_DUPLICATE, {
            'heat_id': new_heat.id,
            })

        logger.info('Heat {0} duplicated to heat {1}'.format(source_heat.id, new_heat.id))

        return new_heat

    def alter_heat(self, data, mute_event=False):
        # Alters heat. Returns heat and list of affected races
        heat_id = data['heat']
        heat = Database.Heat.query.get(heat_id)

        if 'slot_id' in data:
            slot_id = data['slot_id']
            slot = Database.HeatNode.query.get(slot_id)

        if 'name' in data:
            self._racecontext.pagecache.set_valid(False)
            heat.name = data['name']
        if 'class' in data:
            old_class_id = heat.class_id
            heat.class_id = data['class']
        if 'auto_frequency' in data:
            heat.auto_frequency = data['auto_frequency']
            if not heat.auto_frequency:
                self.resolve_slot_unset_nodes(heat)
        if 'group_id' in data:
            heat.group_id = data['group_id']
        if 'pilot' in data:
            slot.pilot_id = data['pilot']
            if slot.method == ProgramMethod.ASSIGN and data['pilot'] == RHUtils.PILOT_ID_NONE:
                slot.method = ProgramMethod.NONE
        if 'method' in data:
            slot.method = data['method']
            slot.seed_id = None
        if 'seed_heat_id' in data:
            if slot.method == ProgramMethod.HEAT_RESULT:
                slot.seed_id = data['seed_heat_id']
            else:
                logger.debug('Ignoring attempt to set (Heat) seed id: method does not match')
        if 'seed_class_id' in data:
            if slot.method == ProgramMethod.CLASS_RESULT:
                slot.seed_id = data['seed_class_id']
            else:
                logger.debug('Ignoring attempt to set (Class) seed id: method does not match')
        if 'seed_rank' in data:
            slot.seed_rank = data['seed_rank']
        if 'status' in data:
            heat.status = data['status']
        if 'active' in data:
            heat.active = data['active']
        if 'coop_best_time' in data:
            heat.coop_best_time = RHUtils.parse_duration_str_to_secs(data['coop_best_time'])
        if 'coop_num_laps' in data:
            heat.coop_num_laps = data['coop_num_laps']

        heat.auto_name = self.get_heat_auto_name(heat)

        # update source names:
        if 'name' in data:
            if heat.results:
                self._racecontext.pagecache.set_valid(False)
                new_result = Results.refresh_source_displayname(self._racecontext, heat.results, heat.id)
                heat.results = None
                Database.DB_session.flush()
                heat.results = new_result

        if 'name' in data and not 'class' in data:
            if heat.class_id != RHUtils.CLASS_ID_NONE:
                race_class = Database.RaceClass.query.get(heat.class_id)
                if race_class.results:
                    self._racecontext.pagecache.set_valid(False)
                    new_result = Results.refresh_source_displayname(self._racecontext, race_class.results, heat.id)
                    race_class.results = None
                    Database.DB_session.flush()
                    race_class.results = new_result

        if 'name' in data and not ('pilot' in data or 'class' in data):
            try:
                event_results = json.loads(self.get_option("eventResults"))
                self._racecontext.pagecache.set_valid(False)
                event_results = Results.refresh_source_displayname(self._racecontext, event_results, heat.id)
                self.set_option("eventResults", json.dumps(event_results))
            except:
                pass

        # alter existing saved races:
        race_list = Database.SavedRaceMeta.query.filter_by(heat_id=heat_id).all()

        if 'class' in data:
            if len(race_list):
                for race_meta in race_list:
                    race_meta.class_id = data['class']

                if old_class_id is not RHUtils.CLASS_ID_NONE:
                    self.clear_results_raceClass(old_class_id)

        if 'pilot' in data:
            if len(race_list):
                for race_meta in race_list:
                    for pilot_race in Database.SavedPilotRace.query.filter_by(race_id=race_meta.id).all():
                        if pilot_race.node_index == slot.node_index:
                            pilot_race.pilot_id = data['pilot']
                    for race_lap in Database.SavedRaceLap.query.filter_by(race_id=race_meta.id):
                        if race_lap.node_index == slot.node_index:
                            race_lap.pilot_id = data['pilot']

                    self.clear_results_savedRaceMeta(race_meta)

                self.clear_results_heat(heat)

        if 'pilot' in data or 'class' in data:
            if len(race_list):
                if heat.class_id is not RHUtils.CLASS_ID_NONE:
                    self.clear_results_raceClass(heat.class_id)

                self.clear_results_event()
                self._racecontext.pagecache.set_valid(False)

        if 'heat_attr' in data and 'value' in data:
            attribute = Database.HeatAttribute.query.filter_by(id=heat_id, name=data['heat_attr']).one_or_none()
            if attribute:
                attribute.value = data['value']
            else:
                Database.DB_session.add(Database.HeatAttribute(id=heat_id, name=data['heat_attr'], value=data['value']))

        heat = self._filters.run_filters(Flt.HEAT_ALTER, heat)

        self.commit()

        self._Events.trigger(Evt.HEAT_ALTER, {
            'heat_id': heat.id,
            })

        # update current race
        if heat_id == self._racecontext.race.current_heat:
            if not heat.active:
                self._racecontext.race.set_heat(RHUtils.HEAT_ID_NONE, mute_event=mute_event)
            else:
                self._racecontext.race.node_pilots = {}
                self._racecontext.race.node_teams = {}
                for heatNode in self.get_heatNodes_by_heat(heat_id):
                    self._racecontext.race.node_pilots[heatNode.node_index] = heatNode.pilot_id

                    if heatNode.pilot_id is not RHUtils.PILOT_ID_NONE:
                        self._racecontext.race.node_teams[heatNode.node_index] = self.get_pilot(heatNode.pilot_id).team
                    else:
                        self._racecontext.race.node_teams[heatNode.node_index] = None
                self._racecontext.race.clear_results() # refresh leaderboard

        logger.info('Heat {0} altered with {1}'.format(heat_id, data))

        return heat, race_list

    def delete_heat(self, heat_or_id):
        # Deletes heat. Returns True if successful, False if not
        heat = self.resolve_heat_from_heat_or_id(heat_or_id)
        if heat:
            deleted_heat_id = heat.id

            heat_count = Database.Heat.query.count()
            heatnodes = Database.HeatNode.query.filter_by(heat_id=heat.id).order_by(Database.HeatNode.node_index).all()

            has_race = self.savedRaceMetas_has_heat(heat.id)

            if has_race or (self._racecontext.race.current_heat == heat.id and self._racecontext.race.race_status != RaceStatus.READY):
                logger.info('Refusing to delete heat {0}: is in use'.format(heat.id))
                return False
            else:
                for attr in self.get_heat_attributes(heat_or_id):
                    Database.DB_session.delete(attr)

                Database.DB_session.delete(heat)
                for heatnode in heatnodes:
                    Database.DB_session.delete(heatnode)
                self.commit()

                logger.info('Heat {0} deleted'.format(deleted_heat_id))

                self._Events.trigger(Evt.HEAT_DELETE, {
                    'heat_id': deleted_heat_id,
                    })

                # if only one heat remaining then set ID to 1
                if heat_count == 2 and self._racecontext.race.race_status == RaceStatus.READY:
                    try:
                        heat = Database.Heat.query.first()
                        if heat.id != 1:
                            heatnodes = Database.HeatNode.query.filter_by(heat_id=heat.id).order_by(Database.HeatNode.node_index).all()

                            if not self.savedRaceMetas_has_heat(heat.id):
                                logger.info("Adjusting single remaining heat ({0}) to ID 1".format(heat.id))
                                heat.id = 1
                                for heatnode in heatnodes:
                                    heatnode.heat_id = heat.id
                                # self.commit()  # 'set_option()' below will do call to 'commit()'
                                self._racecontext.race.current_heat = 1
                                self.set_option('currentHeat', self._racecontext.race.current_heat)
                            else:
                                logger.warning("Not changing single remaining heat ID ({0}): is in use".format(heat.id))
                    except Exception as ex:
                        logger.warning("Error adjusting single remaining heat ID: " + str(ex))

                return True
        else:
            logger.info("No heat to delete")
            return False

    def get_initial_heat_id(self):
        heats = self.get_heats()

        sav_heat_id = self.get_optionInt('currentHeat', RHUtils.HEAT_ID_NONE)
        if sav_heat_id != RHUtils.HEAT_ID_NONE:
            for heat in heats:
                if heat.id == sav_heat_id and heat.active:
                    return sav_heat_id

        # find and return ID of first "safe" heat
        cur_heat_id = RHUtils.HEAT_ID_NONE
        for heat in heats:
            if heat.active:
                if heat.status == HeatStatus.CONFIRMED:
                    cur_heat_id = heat.id
                    break

                if not heat.auto_frequency:
                    slots = self.get_heatNodes_by_heat(heat.id)
                    is_dynamic = False
                    for slot in slots:
                        if slot.method == ProgramMethod.HEAT_RESULT or slot.method == ProgramMethod.CLASS_RESULT:
                            is_dynamic = True

                    if not is_dynamic:
                        cur_heat_id = heat.id
                        break

        if cur_heat_id != sav_heat_id:
            self.set_option('currentHeat', cur_heat_id)
        return cur_heat_id

    def get_next_class_heat_id(self, race_class_id):
        def orderSorter(x):
            if not x.order:
                return 0
            return x.order

        race_classes = self.get_raceClasses()
        race_classes.sort(key=orderSorter)

        found_class = False
        for idx, race_class in enumerate(race_classes):
            if found_class:
                heat_id = self.get_initial_heat_in_class(race_class)
                if heat_id != RHUtils.HEAT_ID_NONE:
                    return heat_id
            if race_class.id == race_class_id:
                found_class = True

        logger.debug('No next class, shifting to practice mode')
        return RHUtils.HEAT_ID_NONE

    def get_initial_heat_in_class(self, race_class_or_id):
        race_class_id = self.resolve_id_from_raceClass_or_id(race_class_or_id)
        heats = self.get_heats_by_class(race_class_id)
        first_heat_id = RHUtils.HEAT_ID_NONE
        for heat in heats:
            if heat.active:
                first_heat_id = heat.id
                break

        return first_heat_id

    def get_next_heat_id(self, current_heat_or_id, regen_heat):
        def orderSorter(x):
            if not x.order:
                return 0
            return x.order

        def groupedOrderSorter(x):
            if not x.order:
                return x.group_id, 0
            return x.group_id, x.order

        current_heat = self.resolve_heat_from_heat_or_id(current_heat_or_id)
        if not current_heat.class_id:
            return current_heat.id

        current_class = self.get_raceClass(current_heat.class_id)

        if current_class.round_type == RoundType.GROUPED:
            if current_class.heat_advance_type == HeatAdvanceType.NONE:
                return RHUtils.HEAT_ID_NONE

            if current_class.heat_advance_type == HeatAdvanceType.NEXT_ROUND:
                if regen_heat:
                    return regen_heat.id

            heats = self.get_heats_by_class(current_heat.class_id)
            heats = [h for h in heats if h.active]
            heats.sort(key=groupedOrderSorter)

            if len(heats):
                if heats[-1].id == current_heat.id:
                    self._Events.trigger(Evt.ROUNDS_COMPLETE, {'class_id': current_class.id})
                    return self.get_next_class_heat_id(current_class.id)
                else:
                    return heats[0].id
            else:
                logger.debug('No active heats, checking next class')
                return self.get_next_class_heat_id(current_class.id)

        if current_class.heat_advance_type == HeatAdvanceType.NONE:
            return current_heat.id

        if current_class.heat_advance_type == HeatAdvanceType.NEXT_ROUND:
            max_round = self.get_max_round(current_heat.id)
            if max_round < current_class.rounds:
                return current_heat.id

        heats = self.get_heats_by_class(current_heat.class_id)
        heats = [h for h in heats if h.active]
        heats.sort(key=orderSorter)

        if len(heats):
            if heats[-1].id == current_heat.id:
                if current_class.rounds:
                    max_round = self.get_max_round(current_heat.id)
                    if max_round >= current_class.rounds:
                        self._Events.trigger(Evt.ROUNDS_COMPLETE, {'class_id': current_class.id})
                        return self.get_next_class_heat_id(current_class.id)
                    else:
                        return heats[0].id
                else:
                    return heats[0].id
            else:
                next_heat_id = RHUtils.HEAT_ID_NONE
                for idx, heat in enumerate(heats):
                    if heat.id == current_heat.id:
                        next_heat_id = heats[idx + 1].id
                        break
                return next_heat_id
        else:
            logger.debug('No active heats, checking next class')
            return self.get_next_class_heat_id(current_class.id)


    def resolve_slot_unset_nodes(self, heat_or_id):
        heat_id = self.resolve_id_from_heat_or_id(heat_or_id)
        used_seats = []
        slots = self.get_heatNodes_by_heat(heat_id)
        slots.sort(key=lambda x:x.id)
        for s in slots:
            used_seats.append(s.node_index)

        seat = 0
        for s in slots:
            if s.node_index == None:
                while seat in used_seats:
                    seat += 1
                
                s.node_index = seat
                seat += 1

        self.commit()

    def get_results_heat(self, heat_or_id):
        heat = self.resolve_heat_from_heat_or_id(heat_or_id)

        if not heat:
            return False

        if len(self.get_savedRaceMetas_by_heat(heat.id)) < 1:
            # no races exist, skip calculating
            return None

        cache_invalid = False
        if heat._cache_status:
            try:
                cacheStatus = json.loads(heat._cache_status)
                token = cacheStatus['data_ver']
                if cacheStatus['data_ver'] == cacheStatus['build_ver']:
                    # cache hit
                    return heat.results
                # else: cache miss
            except ValueError:
                cache_invalid = True
        else:
            cache_invalid = True

        if cache_invalid:
            logger.error('Heat {} cache has invalid status'.format(heat.id))
            token = monotonic()
            self.clear_results_heat(heat, token)

        # cache rebuild
        logger.debug('Building Heat {} results'.format(heat.id))
        build = Results.build_leaderboard_heat(self._racecontext, heat)

        self.set_results_heat(heat, token, build)
        return build

    def set_results_heat(self, heat_or_id, token, results):
        heat = self.resolve_heat_from_heat_or_id(heat_or_id)

        if not heat:
            return False

        cacheStatus = json.loads(heat._cache_status)
        if cacheStatus['data_ver'] == token:
            cacheStatus['build_ver'] = token
            heat.results = results
            heat._cache_status = json.dumps(cacheStatus)

            self.commit()
            return heat
        else:
            logger.info('Ignoring cache write; token mismatch {} / {}'.format(cacheStatus['data_ver'], token))
            return False

    def clear_results_heat(self, heat_or_id, token=None):
        heat = self.resolve_heat_from_heat_or_id(heat_or_id)

        if not heat:
            return False

        if token is None:
            token = monotonic()

        heat._cache_status = json.dumps({
            'data_ver': token,
            'build_ver': None
        })

        self.commit()
        return heat

    def clear_results_heats(self):
        token = monotonic()

        initStatus = json.dumps({
            'data_ver': token,
            'build_ver': None
        })

        Database.Heat.query.update({
            Database.Heat._cache_status: initStatus
            })
        self.commit()

    def clear_heats(self):
        Database.DB_session.query(Database.Heat).delete()
        Database.DB_session.query(Database.HeatNode).delete()
        Database.DB_session.query(Database.HeatAttribute).delete()
        self.commit()

    def reset_heats(self, nofill=False):
        self.clear_heats()
        self._racecontext.race.current_heat = RHUtils.HEAT_ID_NONE
        self.set_option('currentHeat', self._racecontext.race.current_heat)
        logger.info('Database heats reset')

    def reset_heat_plans(self):
        for heat in self.get_heats():
            heat.status = HeatStatus.PLANNED
        self.commit()
        return True

    #Heat Attributes
    def get_heat_attribute(self, heat_or_id, name):
        heat_id = self.resolve_id_from_heat_or_id(heat_or_id)
        return Database.HeatAttribute.query.filter_by(id=heat_id, name=name).one_or_none()

    def get_heat_attribute_value(self, heat_or_id, name, default_value=None):
        heat_id = self.resolve_id_from_heat_or_id(heat_or_id)
        attr = Database.HeatAttribute.query.filter_by(id=heat_id, name=name).one_or_none()

        if attr is not None:
            return attr.value
        else:
            return default_value

    def get_heat_attributes(self, heat_or_id):
        heat_id = self.resolve_id_from_heat_or_id(heat_or_id)
        return Database.HeatAttribute.query.filter_by(id=heat_id).all()

    def get_heat_id_by_attribute(self, name, value):
        attrs = Database.HeatAttribute.query.filter_by(name=name, value=value).all()
        return [attr.id for attr in attrs]

    # HeatNodes
    #def resolve_heatNode_from_heatNode_or_id(self, heatNode_or_id):
    #    if isinstance(heatNode_or_id, Database.HeatNode):
    #        return heatNode_or_id
    #    else:
    #        return Database.HeatNode.query.get(heatNode_or_id)

    #def resolve_id_from_heatNode_or_id(self, heatNode_or_id):
    #    if isinstance(heatNode_or_id, Database.HeatNode):
    #        return heatNode_or_id.id
    #    else:
    #        return heatNode_or_id

    def get_heatNode(self, heatNode_id):
        return Database.HeatNode.query.get(heatNode_id)

    def get_heatNodes(self):
        return Database.HeatNode.query.all()

    def get_heatNodes_by_heat(self, heat_id):
        return Database.HeatNode.query.filter_by(heat_id=heat_id).order_by(Database.HeatNode.node_index).all()

    def add_heatNode(self, heat_id, node_index):
        new_heatNode = Database.HeatNode(
            heat_id=heat_id,
            node_index=node_index,
            pilot_id=RHUtils.PILOT_ID_NONE,
            method=0,
            )

        Database.DB_session.add(new_heatNode)
        self.commit()
        return True

    def get_pilot_from_heatNode(self, heat_id, node_index):
        heatNode = Database.HeatNode.query.filter_by(heat_id=heat_id, node_index=node_index).one_or_none()
        if heatNode:
            return heatNode.pilot_id
        else:
            return None

    def get_node_idx_from_heatNode(self, heat_id, pilot_id):
        heatNode = Database.HeatNode.query.filter_by(heat_id=heat_id, pilot_id=pilot_id).one_or_none()
        if heatNode:
            return heatNode.node_index
        else:
            return -1

    def alter_heatNodes_fast(self, slot_list):
        # Alters heatNodes quickly, in batch
        # !! Unsafe for general use. Intentionally light type checking,    !!
        # !! DOES NOT trigger events, clear results, or update cached data !!

        for slot_data in slot_list:
            slot_id = slot_data['slot_id']
            slot = Database.HeatNode.query.get(slot_id)

            if 'pilot' in slot_data:
                slot.pilot_id = slot_data['pilot']
            if 'method' in slot_data:
                slot.method = slot_data['method']
                slot.seed_id = None
            if 'seed_heat_id' in slot_data:
                if slot.method == ProgramMethod.HEAT_RESULT:
                    slot.seed_id = slot_data['seed_heat_id']
                else:
                    logger.warning('Rejecting attempt to set Heat seed id: method does not match')
            if 'seed_class_id' in slot_data:
                if slot.method == ProgramMethod.CLASS_RESULT:
                    slot.seed_id = slot_data['seed_class_id']
                else:
                    logger.warning('Rejecting attempt to set Class seed id: method does not match')
            if 'seed_rank' in slot_data:
                slot.seed_rank = slot_data['seed_rank']

        self.commit()

    def check_all_heat_nodes_filled(self, heat_id):
        heat_nodes = self.get_heatNodes_by_heat(heat_id)
        for node_obj in self._racecontext.interface.nodes:
            matched_flag = False
            for heat_node in heat_nodes:
                if heat_node.node_index == node_obj.index and \
                        (heat_node.pilot_id != RHUtils.PILOT_ID_NONE or node_obj.frequency <= 0):
                    matched_flag = True
                    break
            if not matched_flag:
                return False
        return True

    # Fetches co-op race values stored via heat in database and loads them into the given RHRace object
    def get_heat_coop_values(self, heat_or_id, rh_race_obj):
        heat_obj = self.resolve_heat_from_heat_or_id(heat_or_id)
        if heat_obj and rh_race_obj:
            rh_race_obj.coop_best_time = heat_obj.coop_best_time
            rh_race_obj.coop_num_laps = heat_obj.coop_num_laps

    # Update co-op race values stored via heat in database (if modified)
    def update_heat_coop_values(self, heat_or_id, coop_best_time, coop_num_laps):
        heat_obj = self.resolve_heat_from_heat_or_id(heat_or_id)
        if heat_obj and (coop_best_time != heat_obj.coop_best_time or coop_num_laps != heat_obj.coop_num_laps):
            heat_obj.coop_best_time = coop_best_time
            heat_obj.coop_num_laps = coop_num_laps
            self.commit()

    # Race Classes
    def resolve_raceClass_from_raceClass_or_id(self, raceClass_or_id):
        if isinstance(raceClass_or_id, Database.RaceClass):
            return raceClass_or_id
        else:
            return Database.RaceClass.query.get(raceClass_or_id)

    def resolve_id_from_raceClass_or_id(self, raceClass_or_id):
        if isinstance(raceClass_or_id, Database.RaceClass):
            return raceClass_or_id.id
        else:
            return raceClass_or_id
    
    def get_raceClass(self, raceClass_id):
        return Database.RaceClass.query.get(raceClass_id)

    def get_raceClasses(self):
        return Database.RaceClass.query.all()

    def add_raceClass(self, init=None):
        # Add new race class
        initStatus = json.dumps({
            'data_ver': monotonic(),
            'build_ver': None
        })

        new_race_class = Database.RaceClass(
            name='',
            description='',
            format_id=RHUtils.FORMAT_ID_NONE,
            _cache_status=initStatus,
            _rank_status=initStatus,
            win_condition="",
            rank_settings=None,
            rounds=0,
            heat_advance_type=HeatAdvanceType.NEXT_HEAT,
            round_type=RoundType.RACES_PER_HEAT,
            order=None
            )
        Database.DB_session.add(new_race_class)
        Database.DB_session.flush()

        if init:
            if 'name' in init:
                new_race_class.name = init['name']
            if 'description' in init:
                new_race_class.description = init['description']
            if 'format_id' in init:
                new_race_class.format_id = init['format_id']
            if 'win_condition' in init:
                new_race_class.win_condition = init['win_condition']
            if 'rounds' in init:
                new_race_class.rounds = init['rounds']
            if 'heat_advance_type' in init:
                new_race_class.heat_advance_type = init['heat_advance_type']
            if 'round_type' in init:
                new_race_class.round_type = init['round_type']
            if 'order' in init:
                new_race_class.order = init['order']

        new_race_class = self._filters.run_filters(Flt.CLASS_ADD, new_race_class)

        self.commit()

        # ensure clean attributes on creation
        for attr in self.get_raceclass_attributes(new_race_class):
            Database.DB_session.delete(attr)

        self.commit()

        self._Events.trigger(Evt.CLASS_ADD, {
            'class_id': new_race_class.id,
            })

        logger.info('Class added: Class {0}'.format(new_race_class))

        return new_race_class

    def duplicate_raceClass(self, source_class_or_id):
        source_class = self.resolve_raceClass_from_raceClass_or_id(source_class_or_id)

        if source_class.name:
            all_class_names = [race_class.name for race_class in self.get_raceClasses()]
            new_class_name = RHUtils.uniqueName(source_class.name, all_class_names)
        else:
            new_class_name = ''

        initStatus = json.dumps({
            'data_ver': monotonic(),
            'build_ver': None
        })

        new_class = Database.RaceClass(
            name=new_class_name,
            description=source_class.description,
            format_id=source_class.format_id,
            results=None,
            _cache_status=initStatus,
            _rank_status=initStatus,
            win_condition=source_class.win_condition,
            rounds=source_class.rounds,
            heat_advance_type=source_class.heat_advance_type,
            round_type=source_class.round_type,
            order=None
            )

        Database.DB_session.add(new_class)
        Database.DB_session.flush()
        Database.DB_session.refresh(new_class)

        for heat in Database.Heat.query.filter_by(class_id=source_class.id).all():
            self.duplicate_heat(heat, dest_class=new_class.id)

        new_class = self._filters.run_filters(Flt.CLASS_DUPLICATE, new_class)

        self.commit()

        self._Events.trigger(Evt.CLASS_DUPLICATE, {
            'class_id': new_class.id,
            })

        logger.info('Class {0} duplicated to class {1}'.format(source_class.id, new_class.id))

        return new_class

    def alter_raceClass(self, data):
        # alter existing classes
        race_class_id = data['class_id']
        race_class = Database.RaceClass.query.get(race_class_id)

        if not race_class:
            return False, False

        if 'class_name' in data:
            race_class.name = data['class_name']
        if 'class_description' in data:
            race_class.description = data['class_description']
        if 'class_format' in data:
            race_class.format_id = data['class_format']
        if 'win_condition' in data:
            race_class.win_condition = data['win_condition']
            race_class.rank_settings = None
        if 'rank_settings' in data:
            if not data['rank_settings']:
                race_class.rank_settings = None
            else:
                src_settings = json.loads(race_class.rank_settings) if race_class.rank_settings else {}
                dest_settings = data['rank_settings']
                if isinstance(dest_settings, str):
                    dest_settings = json.loads(dest_settings)
                race_class.rank_settings = json.dumps({**src_settings, **dest_settings})
        if 'rounds' in data:
            race_class.rounds = data['rounds']
        if 'heat_advance_type' in data:
            race_class.heat_advance_type = data['heat_advance_type']
        if 'round_type' in data:
            race_class.round_type = data['round_type']
        if 'order' in data:
            race_class.order = data['order']

        race_list = Database.SavedRaceMeta.query.filter_by(class_id=race_class_id).all()

        # if switching to groups, split races into individual heats
        if 'round_type' in data:
            if race_class.round_type == RoundType.GROUPED:
                self.raceclass_expand_heat_rounds(race_class, prime=True)
                if race_class.heat_advance_type == HeatAdvanceType.NONE:
                    race_class.heat_advance_type = HeatAdvanceType.NEXT_HEAT
            else:
                self.raceclass_strip_groups(race_class)

        if 'rounds' in data:
            self.raceclass_prime_groups(race_class.id)

        if 'class_name' in data:
            if len(race_list):
                self._racecontext.pagecache.set_valid(False)

        if 'class_format' in data or \
           'win_condition' in data or \
           'rank_settings' in data:
            if len(race_list):
                self._racecontext.pagecache.set_valid(False)
                self.clear_results_event()
                self.clear_results_raceClass(race_class)

            if 'class_format' in data:
                if int(data['class_format']):
                    for race_meta in race_list:
                        race_meta.format_id = data['class_format']
                        self.clear_results_savedRaceMeta(race_meta)

                    heats = Database.Heat.query.filter_by(class_id=race_class_id).all()
                    for heat in heats:
                        self.clear_results_heat(heat)

        if 'class_attr' in data and 'value' in data:
            attribute = Database.RaceClassAttribute.query.filter_by(id=race_class_id, name=data['class_attr']).one_or_none()
            if attribute:
                attribute.value = data['value']
            else:
                Database.DB_session.add(Database.RaceClassAttribute(id=race_class_id, name=data['class_attr'], value=data['value']))

        race_class = self._filters.run_filters(Flt.CLASS_ALTER, race_class)

        self.commit()

        heats = self.get_heats_by_class(race_class.id)
        [self.regen_heat_auto_name(heat.id) for heat in heats]

        self._Events.trigger(Evt.CLASS_ALTER, {
            'class_id': race_class_id,
            })

        logger.info('Altered race class {0} to {1}'.format(race_class_id, data))

        return race_class, race_list

    def delete_raceClass(self, raceClass_or_id):
        race_class = self.resolve_raceClass_from_raceClass_or_id(raceClass_or_id)

        has_race = self.savedRaceMetas_has_raceClass(race_class.id)

        if has_race:
            logger.info('Refusing to delete class {0}: is in use'.format(race_class.id))
            return False
        else:
            deleted_race_class = race_class.id

            for attr in self.get_raceclass_attributes(raceClass_or_id):
                Database.DB_session.delete(attr)

            Database.DB_session.delete(race_class)
            for heat in Database.Heat.query.all():
                if heat.class_id == race_class.id:
                    heat.class_id = RHUtils.CLASS_ID_NONE

            self.commit()

            self._Events.trigger(Evt.CLASS_DELETE, {
                'class_id': deleted_race_class,
                })

            logger.info('Class {0} deleted'.format(deleted_race_class))

            return True

    def get_results_raceClass(self, raceClass_or_id):
        race_class = self.resolve_raceClass_from_raceClass_or_id(raceClass_or_id)

        if not race_class:
            return False

        if len(self.get_savedRaceMetas_by_raceClass(race_class.id)) < 1:
            # no races exist, skip calculating
            return None

        cache_invalid = False
        if race_class._cache_status:
            try:
                cacheStatus = json.loads(race_class._cache_status)
                token = cacheStatus['data_ver']
                if cacheStatus['data_ver'] == cacheStatus['build_ver']:
                    # cache hit
                    return race_class.results
                # else: cache miss
            except ValueError:
                cache_invalid = True
        else:
            cache_invalid = True

        if cache_invalid:
            logger.error('Class {} cache has invalid status'.format(race_class.id))
            token = monotonic()
            self.clear_results_raceClass(race_class, token)

        # cache rebuild
        logger.info('Building Class {} (id: {}) results'.format(race_class.display_name, race_class.id))
        build = Results.build_leaderboard_class(self._racecontext, race_class)
        self.set_results_raceClass(race_class, token, build)
        return build

    def get_ranking_raceClass(self, raceClass_or_id):
        race_class = self.resolve_raceClass_from_raceClass_or_id(raceClass_or_id)

        if not race_class:
            return False

        if len(self.get_savedRaceMetas_by_raceClass(race_class.id)) < 1:
            # no races exist, skip calculating
            return None

        cache_invalid = False
        if race_class._rank_status:
            try:
                rankStatus = json.loads(race_class._rank_status)
                token = rankStatus['data_ver']
                if rankStatus['data_ver'] == rankStatus['build_ver']:
                    # cache hit
                    return race_class.ranking
                # else: cache miss
            except ValueError:
                cache_invalid = True
        else:
            cache_invalid = True

        if cache_invalid:
            logger.error('Class {} ranking has invalid status'.format(race_class.id))
            token = monotonic()
            self.clear_ranking_raceClass(race_class.id, token)

        # cache rebuild
        logger.debug('Building Class {} ranking'.format(race_class.id))
        build = Results.calc_class_ranking_leaderboard(self._racecontext, class_id=race_class.id)
        self.set_ranking_raceClass(race_class.id, token, build)
        return build

    def set_results_raceClass(self, raceClass_or_id, token, results):
        race_class = self.resolve_raceClass_from_raceClass_or_id(raceClass_or_id)

        if not race_class:
            return False

        if race_class._cache_status:
            cacheStatus = json.loads(race_class._cache_status)
            if cacheStatus['data_ver'] == token:
                cacheStatus['build_ver'] = token
                race_class.results = results
                race_class._cache_status = json.dumps(cacheStatus)

                self.commit()
                return race_class
            else:
                logger.info('Ignoring cache write; token mismatch {} / {}'.format(cacheStatus['data_ver'], token))
                return False
        else:
            logger.error('Ignoring cache write for class {}: status is invalid'.format(race_class.id))
            return False

    def set_ranking_raceClass(self, raceClass_or_id, token, results):
        race_class = self.resolve_raceClass_from_raceClass_or_id(raceClass_or_id)

        if not race_class:
            return False

        if race_class._rank_status:
            rankStatus = json.loads(race_class._rank_status)
            if rankStatus['data_ver'] == token:
                rankStatus['build_ver'] = token
                race_class.ranking = results
                race_class._rank_status = json.dumps(rankStatus)

                self.commit()
                return race_class
            else:
                logger.info('Ignoring ranking write; token mismatch {} / {}'.format(rankStatus['data_ver'], token))
                return False
        else:
            logger.error('Ignoring ranking write for class {}: status is invalid'.format(race_class.id))
            return False

    def clear_results_raceClass(self, raceClass_or_id, token=None):
        race_class = self.resolve_raceClass_from_raceClass_or_id(raceClass_or_id)

        if not race_class:
            return False

        if token is None:
            token = monotonic()

        initStatus = {
            'data_ver': token,
            'build_ver': None
        }
        jsonStatus = json.dumps(initStatus)
        race_class._cache_status = jsonStatus
        race_class._rank_status = jsonStatus

        self.commit()
        return race_class

    def clear_ranking_raceClass(self, raceClass_or_id, token=None):
        race_class = self.resolve_raceClass_from_raceClass_or_id(raceClass_or_id)

        if not race_class:
            return False

        if token is None:
            token = monotonic()

        initStatus = json.dumps({
            'data_ver': token,
            'build_ver': None
        })
        race_class._rank_status = initStatus

        self.commit()
        return race_class

    def clear_results_raceClasses(self):
        token = monotonic()

        initStatus = {
            'data_ver': token,
            'build_ver': None
        }
        jsonStatus = json.dumps(initStatus)

        Database.RaceClass.query.update({
            Database.RaceClass._cache_status: jsonStatus,
            Database.RaceClass._rank_status: jsonStatus
            })
        self.commit()

    def clear_raceClasses(self):
        Database.DB_session.query(Database.RaceClass).delete()
        Database.DB_session.query(Database.RaceClassAttribute).delete()
        self.commit()
        return True

    def reset_raceClasses(self):
        self.clear_raceClasses()
        logger.info('Database race classes reset')
        return True

    #RaceClass Attributes
    def get_raceclass_attribute(self, raceclass_or_id, name):
        raceclass_id = self.resolve_id_from_raceClass_or_id(raceclass_or_id)
        return Database.RaceClassAttribute.query.filter_by(id=raceclass_id, name=name).one_or_none()

    def get_raceclass_attribute_value(self, raceclass_or_id, name, default_value=None):
        raceclass_id = self.resolve_id_from_raceClass_or_id(raceclass_or_id)
        attr = Database.RaceClassAttribute.query.filter_by(id=raceclass_id, name=name).one_or_none()

        if attr is not None:
            return attr.value
        else:
            return default_value

    def get_raceclass_attributes(self, raceclass_or_id):
        raceclass_id = self.resolve_id_from_raceClass_or_id(raceclass_or_id)
        return Database.RaceClassAttribute.query.filter_by(id=raceclass_id).all()

    def get_raceclass_id_by_attribute(self, name, value):
        attrs = Database.RaceClassAttribute.query.filter_by(name=name, value=value).all()
        return [attr.id for attr in attrs]

    def raceclass_expand_heat_rounds(self, race_class_or_id, prime=False):
        race_class = self.resolve_raceClass_from_raceClass_or_id(race_class_or_id)
        if race_class.round_type == RoundType.GROUPED:
            heats = self.get_heats_by_class(race_class.id)
            for heat in heats:
                races = self.get_savedRaceMetas_by_heat(heat.id)
                if len(races) > 1:
                    for group, race in enumerate(races):
                        if group > 0:
                            new_heat = self.duplicate_heat(heat, new_heat_name=heat.name, group_id=group)
                            self.reassign_savedRaceMeta_heat(race, new_heat.id)
                    if prime:
                        self.duplicate_heat(heat, new_heat_name=heat.name, group_id=len(races))

    def raceclass_prime_groups(self, race_class_or_id):
        race_class = self.resolve_raceClass_from_raceClass_or_id(race_class_or_id)
        if race_class.round_type == RoundType.GROUPED:
            heats = self.get_heats_by_class(race_class.id)
            group_heats = []
            for heat in heats:
                while len(group_heats) <= heat.group_id:
                    group_heats.append([])
                group_heats[heat.group_id].append(heat)

            if len(group_heats) < race_class.rounds:
                next_round = len(group_heats)
                for heat in group_heats[-1]:
                    races = self.get_savedRaceMetas_by_heat(heat.id)
                    if len(races):
                        self.duplicate_heat(heat, new_heat_name=heat.name, group_id=next_round)

    def raceclass_strip_groups(self, race_class_or_id):
        race_class = self.resolve_raceClass_from_raceClass_or_id(race_class_or_id)
        heats = self.get_heats_by_class(race_class.id)
        for heat in heats:
            self.alter_heat({
                'heat': heat.id,
                'group_id': 0,
            })

    # Profiles
    def resolve_profile_from_profile_or_id(self, profile_or_id):
        if isinstance(profile_or_id, Database.Profiles):
            return profile_or_id
        else:
            return Database.Profiles.query.get(profile_or_id)

    def resolve_id_from_profile_or_id(self, profile_or_id):
        if isinstance(profile_or_id, Database.Profiles):
            return profile_or_id.id
        else:
            return profile_or_id

    def get_profile(self, profile_id):
        return Database.Profiles.query.get(profile_id)

    def get_profiles(self):
        return Database.Profiles.query.all()

    def get_first_profile(self):
        return Database.Profiles.query.first()

    def add_profile(self, init=None):
        new_profile = Database.Profiles(
            name='',
            frequencies = '',
            enter_ats = '',
            exit_ats = ''
            )

        if init:
            if 'name' in init:
                new_profile.name = init['name']
            if 'description' in init:
                new_profile.description = init['description']
            if 'frequencies' in init:
                new_profile.frequencies = init['frequencies'] if isinstance(init['frequencies'], str) else json.dumps(init['frequencies'])
            if 'enter_ats' in init:
                new_profile.enter_ats = init['enter_ats'] if isinstance(init['enter_ats'], str) else json.dumps(init['enter_ats'])
            if 'exit_ats' in init:
                new_profile.exit_ats = init['exit_ats'] if isinstance(init['exit_ats'], str) else json.dumps(init['exit_ats'])

        Database.DB_session.add(new_profile)

        new_profile = self._filters.run_filters(Flt.PROFILE_ADD, new_profile)

        self.commit()

        return new_profile

    def duplicate_profile(self, source_profile_or_id):
        source_profile = self.resolve_profile_from_profile_or_id(source_profile_or_id)

        all_profile_names = [profile.name for profile in self.get_profiles()]

        if source_profile.name:
            new_profile_name = RHUtils.uniqueName(source_profile.name, all_profile_names)
        else:
            new_profile_name = RHUtils.uniqueName(self._racecontext.language.__('New Profile'), all_profile_names)

        new_profile = Database.Profiles(
            name=new_profile_name,
            description = '',
            frequencies = source_profile.frequencies,
            enter_ats = source_profile.enter_ats,
            exit_ats = source_profile.exit_ats,
            f_ratio = 100)
        Database.DB_session.add(new_profile)

        new_profile = self._filters.run_filters(Flt.PROFILE_DUPLICATE, new_profile)

        self.commit()

        self._Events.trigger(Evt.PROFILE_ADD, {
            'profile_id': new_profile.id,
            })

        return new_profile

    def alter_profile(self, data):
        profile = Database.Profiles.query.get(data['profile_id'])

        if 'profile_name' in data:
            profile.name = data['profile_name']
        if 'profile_description' in data:
            profile.description = data['profile_description']
        if 'frequencies' in data:
            profile.frequencies = data['frequencies'] if isinstance(data['frequencies'], str) else json.dumps(data['frequencies'])
        if 'enter_ats' in data:
            profile.enter_ats = data['enter_ats'] if isinstance(data['enter_ats'], str) else json.dumps(data['enter_ats'])
        if 'exit_ats' in data:
            profile.exit_ats = data['exit_ats'] if isinstance(data['exit_ats'], str) else json.dumps(data['exit_ats'])

        profile = self._filters.run_filters(Flt.PROFILE_ALTER, profile)

        self.commit()

        self._Events.trigger(Evt.PROFILE_ALTER, {
            'profile_id': profile.id,
            })

        logger.debug('Altered profile {0} to {1}'.format(profile.id, data))

        seat_minimum = self._racecontext.race.num_nodes
        freqs = json.loads(profile.frequencies)
        if seat_minimum > len(freqs["b"]) or seat_minimum > len(freqs["c"]) or \
            seat_minimum > len(freqs["f"]):
            while seat_minimum > len(freqs["b"]):
                freqs["b"].append(RHUtils.FREQUENCY_ID_NONE)
            while seat_minimum > len(freqs["c"]):
                freqs["c"].append(RHUtils.FREQUENCY_ID_NONE)
            while seat_minimum > len(freqs["f"]):
                freqs["f"].append(RHUtils.FREQUENCY_ID_NONE)
            profile.frequencies = json.dumps(freqs)

        return profile

    def delete_profile(self, profile_or_id):
        if len(self.get_profiles()) > 1: # keep one profile
            profile = self.resolve_profile_from_profile_or_id(profile_or_id)
            deleted_profile_id = profile.id
            Database.DB_session.delete(profile)
            self.commit()

            self._Events.trigger(Evt.PROFILE_DELETE, {
                'profile_id': deleted_profile_id,
                })

            return True
        else:
            logger.info('Refusing to delete only profile')
            return False

    def clear_profiles(self):
        Database.DB_session.query(Database.Profiles).delete()
        self.commit()
        return True

    def reset_profiles(self):
        self.clear_profiles()

        new_freqs = self.default_frequencies()

        template = {}
        template["v"] = [None for _i in range(max(self._racecontext.race.num_nodes,8))]

        self.add_profile({
            'name': self.__("Default"),
            'frequencies': json.dumps(new_freqs),
            'enter_ats': json.dumps(template),
            'exit_ats': json.dumps(template)
            })

        self.set_option("currentProfile", self.get_first_profile().id)
        logger.info("Database set default profiles")
        return True

    # Formats
    def resolve_raceFormat_from_raceFormat_or_id(self, raceFormat_or_id):
        if isinstance(raceFormat_or_id, Database.RaceFormat):
            return raceFormat_or_id
        else:
            return Database.RaceFormat.query.get(raceFormat_or_id)

    def resolve_id_from_raceFormat_or_id(self, raceFormat_or_id):
        if isinstance(raceFormat_or_id, Database.RaceFormat):
            return raceFormat_or_id.id
        else:
            return raceFormat_or_id

    def get_raceFormat(self, raceFormat_id):
        return Database.RaceFormat.query.get(raceFormat_id)

    def get_raceFormats(self):
        return Database.RaceFormat.query.all()

    def get_first_raceFormat(self):
        return Database.RaceFormat.query.first()

    def add_format(self, init=None):
        race_format = Database.RaceFormat(
            name='',
            unlimited_time=1,
            race_time_sec=0,
            lap_grace_sec=-1,
            staging_fixed_tones=0,
            staging_delay_tones=0,
            start_delay_min_ms=1000,
            start_delay_max_ms=1000,
            number_laps_win=0,
            win_condition=0,
            team_racing_mode=RacingMode.INDIVIDUAL,
            start_behavior=0,
            points_method=None)

        if init:
            if 'format_name' in init:
                race_format.name = init['format_name']
            if 'unlimited_time' in init: # unlimited time
                race_format.unlimited_time = (1 if init['unlimited_time'] else 0)
            if 'race_time_sec' in init:
                race_format.race_time_sec = init['race_time_sec']
            if 'lap_grace_sec' in init:
                race_format.lap_grace_sec = init['lap_grace_sec']
            if 'staging_fixed_tones' in init:
                race_format.staging_fixed_tones = init['staging_fixed_tones']
            if 'staging_delay_tones' in init:
                race_format.staging_delay_tones = (2 if init['staging_delay_tones'] else 0)
            if 'start_delay_min_ms' in init:
                race_format.start_delay_min_ms = init['start_delay_min_ms']
            if 'start_delay_max_ms' in init:
                race_format.start_delay_max_ms = init['start_delay_max_ms']
            if 'start_behavior' in init:
                race_format.start_behavior = init['start_behavior']
            if 'win_condition' in init:
                race_format.win_condition = init['win_condition']
            if 'number_laps_win' in init:
                race_format.number_laps_win = init['number_laps_win']
            if 'team_racing_mode' in init:
                race_format.team_racing_mode = int(init['team_racing_mode']) if init['team_racing_mode'] else RacingMode.INDIVIDUAL
            if 'points_method' in init:
                race_format.points_method = init['points_method']

        Database.DB_session.add(race_format)

        race_format = self._filters.run_filters(Flt.RACE_FORMAT_ADD, race_format)

        self.commit()

        # ensure clean attributes on creation
        for attr in self.get_raceformat_attributes(race_format):
            Database.DB_session.delete(attr)

        self.commit()

        return race_format

    def duplicate_raceFormat(self, source_format_or_id):
        source_format = self.resolve_raceFormat_from_raceFormat_or_id(source_format_or_id)

        all_format_names = [raceformat.name for raceformat in self.get_raceFormats()]

        if source_format.name:
            new_format_name = RHUtils.uniqueName(source_format.name, all_format_names)
        else:
            new_format_name = RHUtils.uniqueName(self._racecontext.language.__('New Format'), all_format_names)

        new_format = Database.RaceFormat(
            name=new_format_name,
            unlimited_time=source_format.unlimited_time,
            race_time_sec=source_format.race_time_sec,
            lap_grace_sec=source_format.lap_grace_sec,
            staging_fixed_tones=source_format.staging_fixed_tones,
            start_delay_min_ms=source_format.start_delay_min_ms,
            start_delay_max_ms=source_format.start_delay_max_ms,
            staging_delay_tones=source_format.staging_delay_tones,
            number_laps_win=source_format.number_laps_win,
            win_condition=source_format.win_condition,
            team_racing_mode=source_format.team_racing_mode,
            start_behavior=source_format.start_behavior,
            points_method=source_format.points_method)
        Database.DB_session.add(new_format)

        new_format = self._filters.run_filters(Flt.RACE_FORMAT_DUPLICATE, new_format)

        self.commit()

        self._Events.trigger(Evt.RACE_FORMAT_ADD, {
            'format_id': new_format.id,
            })

        return new_format

    def alter_raceFormat(self, data):
        race_format = Database.RaceFormat.query.get(data['format_id'])

        # Prevent active race format change
        if self.get_optionInt('currentFormat') == data['format_id'] and \
            self._racecontext.race.race_status != RaceStatus.READY:
            logger.warning('Preventing race format alteration: race in progress')
            return False, False

        if 'format_name' in data:
            race_format.name = data['format_name']
        if 'unlimited_time' in data:
            race_format.unlimited_time = (1 if data['unlimited_time'] else 0)
        if 'race_time_sec' in data:
            race_format.race_time_sec = data['race_time_sec'] if isinstance(data['race_time_sec'], int) else 0
        if 'lap_grace_sec' in data:
            race_format.lap_grace_sec = data['lap_grace_sec'] if isinstance(data['lap_grace_sec'], int) else 0
        if 'staging_fixed_tones' in data:
            race_format.staging_fixed_tones = data['staging_fixed_tones'] if isinstance(data['staging_fixed_tones'], int) else 0
        if 'staging_delay_tones' in data:
            race_format.staging_delay_tones = (2 if data['staging_delay_tones'] else 0)
        if 'start_delay_min_ms' in data:
            race_format.start_delay_min_ms = data['start_delay_min_ms'] if isinstance(data['start_delay_min_ms'], int) else 0
        if 'start_delay_max_ms' in data:
            race_format.start_delay_max_ms = data['start_delay_max_ms'] if isinstance(data['start_delay_max_ms'], int) else 0
        if 'start_behavior' in data:
            race_format.start_behavior = data['start_behavior'] if isinstance(data['start_behavior'], int) else 0
        if 'win_condition' in data:
            race_format.win_condition = data['win_condition'] if isinstance(data['win_condition'], int) else 0
        if 'number_laps_win' in data:
            race_format.number_laps_win = data['number_laps_win'] if isinstance(data['number_laps_win'], int) else 0
        if 'team_racing_mode' in data:
            race_format.team_racing_mode = int(data['team_racing_mode']) if data['team_racing_mode'] else RacingMode.INDIVIDUAL
        if 'points_method' in data:
            if data['points_method']:
                if race_format.points_method:
                    pm = json.loads(race_format.points_method)
                else:
                    pm = {}

                pm['t'] = data['points_method']
                race_format.points_method = json.dumps(pm)
            else:
                race_format.points_method = None

        if 'points_settings' in data:
            if race_format.points_method:
                pm = json.loads(race_format.points_method)
                pm['s'] = data['points_settings']
                race_format.points_method = json.dumps(pm) 
            else:
                logger.warning("Adding points method settings without established type")

        if 'format_attr' in data and 'value' in data:
            attribute = Database.RaceFormatAttribute.query.filter_by(id=data['format_id'], name=data['format_attr']).one_or_none()
            if attribute:
                attribute.value = data['value']
            else:
                Database.DB_session.add(Database.RaceFormatAttribute(id=data['format_id'], name=data['format_attr'], value=data['value']))

        race_format = self._filters.run_filters(Flt.RACE_FORMAT_ALTER, race_format)

        self.commit()

        self._racecontext.race.clear_results() # refresh leaderboard

        race_list = []

        if 'win_condition' in data or 'start_behavior' in data or 'points_method' in data or 'points_settings' in data:
            race_list = Database.SavedRaceMeta.query.filter_by(format_id=race_format.id).all()

            if len(race_list):
                self._racecontext.pagecache.set_valid(False)
                self.clear_results_event()

                for race in race_list:
                    self.clear_results_savedRaceMeta(race)

                classes = Database.RaceClass.query.filter_by(format_id=race_format.id).all()

                for race_class in classes:
                    self.clear_results_raceClass(race_class)

                    heats = Database.Heat.query.filter_by(class_id=race_class.id).all()

                    for heat in heats:
                        self.clear_results_heat(heat)

                self.commit()

        self._Events.trigger(Evt.RACE_FORMAT_ALTER, {
            'race_format': race_format.id,
            })

        logger.info('Altered format {0} to {1}'.format(race_format.id, data))

        return race_format, race_list

    def delete_raceFormat(self, format_id):
        # Prevent active race format change
        if self.get_optionInt('currentFormat') == format_id and \
            self._racecontext.race.race_status != RaceStatus.READY:
            logger.warning('Preventing race format deletion: race in progress')
            return False

        if self.savedRaceMetas_has_raceFormat(format_id):
            logger.warning('Preventing race format deletion: saved race exists')
            return False

        race_format = Database.RaceFormat.query.get(format_id)
        if race_format and len(self.get_raceFormats()) > 1: # keep one format
            for attr in self.get_raceformat_attributes(format_id):
                Database.DB_session.delete(attr)

            Database.DB_session.delete(race_format)
            self.commit()

            self._Events.trigger(Evt.RACE_FORMAT_DELETE, {
                'race_format': format_id,
                })

            return True
        else:
            logger.info('Refusing to delete only format')
            return False

    def clear_raceFormats(self):
        Database.DB_session.query(Database.RaceFormat).delete()
        Database.DB_session.query(Database.RaceFormatAttribute).delete()
        for race_class in self.get_raceClasses():
            self.alter_raceClass({
                'class_id': race_class.id,
                'class_format': RHUtils.FORMAT_ID_NONE
                })

        self.commit()
        return True

    def reset_raceFormats(self, addCoopFlag=True):
        self.clear_raceFormats()
        self.add_format({
            'format_name': self.__("2:00 Standard Race"),
            'unlimited_time': 0,
            'race_time_sec': 120,
            'lap_grace_sec': -1,
            "staging_fixed_tones": 3,
            'start_delay_min_ms': 500,
            'start_delay_max_ms': 3500,
            'staging_delay_tones': 0,
            'number_laps_win': 0,
            'win_condition': WinCondition.MOST_PROGRESS,
            'team_racing_mode': RacingMode.INDIVIDUAL,
            'start_behavior': 0,
            'points_method': None
            })
        self.add_format({
            'format_name': self.__("1:30 Whoop Sprint"),
            'unlimited_time': 0,
            'race_time_sec': 90,
            'lap_grace_sec': -1,
            "staging_fixed_tones": 3,
            'start_delay_min_ms': 500,
            'start_delay_max_ms': 3500,
            'staging_delay_tones': 2,
            'number_laps_win': 0,
            'win_condition': WinCondition.MOST_PROGRESS,
            'team_racing_mode': RacingMode.INDIVIDUAL,
            'start_behavior': 0,
            'points_method': None
            })
        self.add_format({
            'format_name': self.__("3:00 Extended Race"),
            'unlimited_time': 0,
            'race_time_sec': 210,
            'lap_grace_sec': -1,
            "staging_fixed_tones": 3,
            'start_delay_min_ms': 500,
            'start_delay_max_ms': 3500,
            'staging_delay_tones': 0,
            'number_laps_win': 0,
            'win_condition': WinCondition.MOST_PROGRESS,
            'team_racing_mode': RacingMode.INDIVIDUAL,
            'start_behavior': 0,
            'points_method': None
            })
        self.add_format({
            'format_name': self.__("First to 3 Laps"),
            'unlimited_time': 1,
            'race_time_sec': 0,
            'lap_grace_sec': -1,
            "staging_fixed_tones": 3,
            'start_delay_min_ms': 1000,
            'start_delay_max_ms': 0,
            'staging_delay_tones': 0,
            'number_laps_win': 3,
            'win_condition': WinCondition.FIRST_TO_LAP_X,
            'team_racing_mode': RacingMode.INDIVIDUAL,
            'start_behavior': 0,
            'points_method': None
            })
        self.add_format({
            'format_name': self.__("Open Practice"),
            'unlimited_time': 1,
            'race_time_sec': 0,
            'lap_grace_sec': -1,
            "staging_fixed_tones": 3,
            'start_delay_min_ms': 1000,
            'start_delay_max_ms': 0,
            'staging_delay_tones': 0,
            'number_laps_win': 0,
            'win_condition': WinCondition.NONE,
            'team_racing_mode': RacingMode.INDIVIDUAL,
            'start_behavior': 0,
            'points_method': None
            })
        self.add_format({
            'format_name': self.__("Fastest Lap Qualifier"),
            'unlimited_time': 0,
            'race_time_sec': 120,
            'lap_grace_sec': 30,
            "staging_fixed_tones": 1,
            'start_delay_min_ms': 2000,
            'start_delay_max_ms': 3000,
            'staging_delay_tones': 0,
            'number_laps_win': 0,
            'win_condition': WinCondition.FASTEST_LAP,
            'team_racing_mode': RacingMode.INDIVIDUAL,
            'start_behavior': 0,
            'points_method': None
            })
        self.add_format({
            'format_name': self.__("Fastest Consecutive Laps Qualifier"),
            'unlimited_time': 0,
            'race_time_sec': 120,
            'lap_grace_sec': 30,
            "staging_fixed_tones": 1,
            'start_delay_min_ms': 2000,
            'start_delay_max_ms': 3000,
            'staging_delay_tones': 0,
            'number_laps_win': 0,
            'win_condition': WinCondition.FASTEST_CONSECUTIVE,
            'team_racing_mode': RacingMode.INDIVIDUAL,
            'start_behavior': 0,
            'points_method': None
            })
        self.add_format({
            'format_name': self.__("Lap Count Only"),
            'unlimited_time': 0,
            'race_time_sec': 120,
            'lap_grace_sec': -1,
            "staging_fixed_tones": 3,
            'start_delay_min_ms': 1000,
            'start_delay_max_ms': 0,
            'staging_delay_tones': 0,
            'number_laps_win': 0,
            'win_condition': WinCondition.MOST_LAPS,
            'team_racing_mode': RacingMode.INDIVIDUAL,
            'start_behavior': 0,
            'points_method': None
            })
        self.add_format({
            'format_name': self.__("Team / Most Laps Wins"),
            'unlimited_time': 0,
            'race_time_sec': 120,
            'lap_grace_sec': -1,
            "staging_fixed_tones": 3,
            'start_delay_min_ms': 500,
            'start_delay_max_ms': 3500,
            'staging_delay_tones': 2,
            'number_laps_win': 0,
            'win_condition': WinCondition.MOST_PROGRESS,
            'team_racing_mode': RacingMode.TEAM_ENABLED,
            'start_behavior': 0,
            'points_method': None
            })
        self.add_format({
            'format_name': self.__("Team / First to 7 Laps"),
            'unlimited_time': 0,
            'race_time_sec': 120,
            'lap_grace_sec': -1,
            "staging_fixed_tones": 3,
            'start_delay_min_ms': 500,
            'start_delay_max_ms': 3500,
            'staging_delay_tones': 2,
            'number_laps_win': 7,
            'win_condition': WinCondition.FIRST_TO_LAP_X,
            'team_racing_mode': RacingMode.TEAM_ENABLED,
            'start_behavior': 0,
            'points_method': None
            })
        self.add_format({
            'format_name': self.__("Team / Fastest Lap Average"),
            'unlimited_time': 0,
            'race_time_sec': 120,
            'lap_grace_sec': -1,
            "staging_fixed_tones": 3,
            'start_delay_min_ms': 500,
            'start_delay_max_ms': 3500,
            'staging_delay_tones': 2,
            'number_laps_win': 0,
            'win_condition': WinCondition.FASTEST_LAP,
            'team_racing_mode': RacingMode.TEAM_ENABLED,
            'start_behavior': 0,
            'points_method': None
            })
        self.add_format({
            'format_name': self.__("Team / Fastest Consecutive Average"),
            'unlimited_time': 0,
            'race_time_sec': 120,
            'lap_grace_sec': -1,
            "staging_fixed_tones": 3,
            'start_delay_min_ms': 500,
            'start_delay_max_ms': 3500,
            'staging_delay_tones': 2,
            'number_laps_win': 0,
            'win_condition': WinCondition.FASTEST_CONSECUTIVE,
            'team_racing_mode': RacingMode.TEAM_ENABLED,
            'start_behavior': 0,
            'points_method': None
            })
        if addCoopFlag:
            self.add_coopRaceFormats()

        self.commit()
        logger.info("Database reset race formats")
        return True

    def add_coopRaceFormats(self):
        self.add_format({
            'format_name': self.__("Co-op Fastest Time to 7 Laps"),
            'unlimited_time': 1,
            'race_time_sec': 0,
            'lap_grace_sec': -1,
            "staging_fixed_tones": 3,
            'start_delay_min_ms': 1000,
            'start_delay_max_ms': 0,
            'staging_delay_tones': 2,
            'number_laps_win': 7,
            'win_condition': WinCondition.FIRST_TO_LAP_X,
            'team_racing_mode': RacingMode.COOP_ENABLED,
            'start_behavior': 0,
            'points_method': None
        })
        self.add_format({
            'format_name': self.__("Co-op Most Laps in 2:30"),
            'unlimited_time': 0,
            'race_time_sec': 150,
            'lap_grace_sec': -1,
            "staging_fixed_tones": 3,
            'start_delay_min_ms': 1000,
            'start_delay_max_ms': 0,
            'staging_delay_tones': 2,
            'number_laps_win': 0,
            'win_condition': WinCondition.MOST_PROGRESS,
            'team_racing_mode': RacingMode.COOP_ENABLED,
            'start_behavior': 0,
            'points_method': None
        })

    # Race Format Attributes
    def get_raceformat_attribute(self, raceformat_or_id, name):
        raceformat_id = self.resolve_id_from_raceFormat_or_id(raceformat_or_id)
        return Database.RaceFormatAttribute.query.filter_by(id=raceformat_id, name=name).one_or_none()

    def get_raceformat_attribute_value(self, raceformat_or_id, name, default_value=None):
        raceformat_id = self.resolve_id_from_raceFormat_or_id(raceformat_or_id)
        attr = Database.RaceFormatAttribute.query.filter_by(id=raceformat_id, name=name).one_or_none()

        if attr is not None:
            return attr.value
        else:
            return default_value

    def get_raceformat_attributes(self, raceformat_or_id):
        raceformat_id = self.resolve_id_from_raceFormat_or_id(raceformat_or_id)
        return Database.RaceFormatAttribute.query.filter_by(id=raceformat_id).all()

    def get_raceformat_id_by_attribute(self, name, value):
        attrs = Database.RaceFormatAttribute.query.filter_by(name=name, value=value).all()
        return [attr.id for attr in attrs]

    # Race Meta
    def resolve_savedRaceMeta_from_savedRaceMeta_or_id(self, savedRaceMeta_or_id):
        if isinstance(savedRaceMeta_or_id, Database.SavedRaceMeta):
            return savedRaceMeta_or_id
        else:
            return Database.SavedRaceMeta.query.get(savedRaceMeta_or_id)

    def resolve_id_from_savedRaceMeta_or_id(self, savedRaceMeta_or_id):
        if isinstance(savedRaceMeta_or_id, Database.SavedRaceMeta):
            return savedRaceMeta_or_id.id
        else:
            return savedRaceMeta_or_id

    def get_savedRaceMeta(self, raceMeta_id):
        return Database.SavedRaceMeta.query.get(raceMeta_id)

    def get_savedRaceMeta_by_heat_round(self, heat_id, round_id):
        return Database.SavedRaceMeta.query.filter_by(heat_id=heat_id, round_id=round_id).one()

    def get_savedRaceMetas(self):
        return Database.SavedRaceMeta.query.all()

    def get_savedRaceMetas_by_heat(self, heat_id):
        return Database.SavedRaceMeta.query.filter_by(heat_id=heat_id).order_by(Database.SavedRaceMeta.round_id).all()

    def get_savedRaceMetas_by_raceClass(self, class_id):
        return Database.SavedRaceMeta.query.filter_by(class_id=class_id).order_by(Database.SavedRaceMeta.round_id).all()

    def savedRaceMetas_has_raceFormat(self, race_format_id):
        return bool(Database.SavedRaceMeta.query.filter_by(format_id=race_format_id).count())

    def savedRaceMetas_has_heat(self, heat_id):
        return bool(Database.SavedRaceMeta.query.filter_by(heat_id=heat_id).count())

    def savedRaceMetas_has_raceClass(self, class_id):
        return bool(Database.SavedRaceMeta.query.filter_by(class_id=class_id).count())

    def alter_savedRaceMeta(self, race_id, data):
        if 'race_attr' in data and 'value' in data:
            attribute = Database.SavedRaceMetaAttribute.query.filter_by(id=race_id, name=data['race_attr']).one_or_none()
            if attribute:
                attribute.value = data['value']
            else:
                Database.DB_session.add(Database.SavedRaceMetaAttribute(id=race_id, name=data['race_attr'], value=data['value']))

        self.commit()

    def add_savedRaceMeta(self, data):
        new_race = Database.SavedRaceMeta(
            round_id=data['round_id'],
            heat_id=data['heat_id'],
            class_id=data['class_id'],
            format_id=data['format_id'],
            start_time=data['start_time'],
            start_time_formatted=data['start_time_formatted'],
            _cache_status=json.dumps({
                'data_ver': monotonic(),
                'build_ver': None
            })
        )
        Database.DB_session.add(new_race)

        self.commit()

        # ensure clean attributes on creation
        for attr in self.get_savedrace_attributes(new_race):
            Database.DB_session.delete(attr)

        self.commit()

        logger.info('Race added: Race {0}'.format(new_race.id))

        return new_race

    def reassign_savedRaceMeta_heat(self, savedRaceMeta_or_id, new_heat_id):
        race_meta = self.resolve_savedRaceMeta_from_savedRaceMeta_or_id(savedRaceMeta_or_id)

        old_heat_id = race_meta.heat_id
        old_heat = self.get_heat(old_heat_id)
        old_class = self.get_raceClass(old_heat.class_id)
        if old_class:
            old_format_id = old_class.format_id
        else:
            old_format_id = race_meta.format_id

        new_heat = self.get_heat(new_heat_id)
        new_class = self.get_raceClass(new_heat.class_id)
        new_format_id = new_class.format_id

        # clear round ids
        heat_races = Database.SavedRaceMeta.query.filter_by(heat_id=new_heat_id).order_by(Database.SavedRaceMeta.round_id).all()
        race_meta.round_id = 0
        dummy_round_counter = -1
        for race in heat_races:
            race.round_id = dummy_round_counter
            dummy_round_counter -= 1

        # assign new heat
        race_meta.heat_id = new_heat_id
        race_meta.class_id = new_heat.class_id
        race_meta.format_id = new_format_id

        # reassign pilots to pilotRaces
        new_pilots = self.get_heatNodes_by_heat(new_heat_id)
        for np in new_pilots:
            for pilot_race in self.get_savedPilotRaces_by_savedRaceMeta(race_meta.id):
                if pilot_race.node_index == np.node_index:
                    pilot_race.pilot_id = np.pilot_id
                    for lap in self.get_savedRaceLaps_by_savedPilotRace(pilot_race.id):
                        lap.pilot_id = np.pilot_id
                    break

                if pilot_race.node_index == np.node_index:
                    pilot_race.pilot_id = np.pilot_id
                    break

        # renumber rounds
        Database.DB_session.flush()
        old_heat_races = Database.SavedRaceMeta.query.filter_by(heat_id=old_heat_id) \
            .order_by(Database.SavedRaceMeta.start_time_formatted).all()
        round_counter = 1
        for race in old_heat_races:
            race.round_id = round_counter
            round_counter += 1

        if old_heat_races and old_class:
            if old_class.round_type == RoundType.GROUPED:
                old_heat.active = False
            else:
                old_heat.active = True

        new_heat_races = Database.SavedRaceMeta.query.filter_by(heat_id=new_heat_id) \
            .order_by(Database.SavedRaceMeta.start_time_formatted).all()
        round_counter = 1
        for race in new_heat_races:
            race.round_id = round_counter
            round_counter += 1

        if new_heat_races and new_class:
            if new_class.round_type == RoundType.GROUPED:
                new_heat.active = False
            else:
                new_heat.active = True

        self.commit()

        # cache cleaning
        self._racecontext.pagecache.set_valid(False)

        self.clear_results_heat(new_heat)
        self.clear_results_heat(old_heat)

        if old_format_id != new_format_id:
            self.clear_results_savedRaceMeta(race_meta)

        if old_heat.class_id != new_heat.class_id:
            self.clear_results_raceClass(new_class)
            if old_class:
                self.clear_results_raceClass(old_class)

        self.commit()

        self._Events.trigger(Evt.RACE_ALTER, {
            'race_id': race_meta.id,
            })

        logger.info('Race {0} reassigned to heat {1}'.format(race_meta.id, new_heat_id))

        return race_meta, new_heat

    def get_results_savedRaceMeta(self, savedRaceMeta_or_id, no_rebuild_flag=False):
        race = self.resolve_savedRaceMeta_from_savedRaceMeta_or_id(savedRaceMeta_or_id)

        if not race:
            return False

        cache_invalid = False
        if race._cache_status:
            try:
                cacheStatus = json.loads(race._cache_status)
                token = cacheStatus['data_ver']
                if cacheStatus['data_ver'] == cacheStatus['build_ver']:
                    # cache hit
                    return race.results
                # else: cache miss
            except ValueError:
                cache_invalid = True
        else:
            cache_invalid = True

        if cache_invalid:
            logger.error('Race {} cache has invalid status'.format(race.id))
            token = monotonic()
            self.clear_results_savedRaceMeta(race, token)

        if no_rebuild_flag:
            return None

        # cache rebuild
        logger.debug('Building Race {} (Heat {} Round {}) results'.format(race.id, race.heat_id, race.round_id))
        build = Results.build_leaderboard_race(self._racecontext, heat_id=race.heat_id, round_id=race.round_id)

        # calc race points
        if race.format_id:
            raceformat = self.get_raceFormat(race.format_id)
            if raceformat and raceformat.points_method:
                points_method = json.loads(raceformat.points_method)
                method_type = points_method['t']
                if 's' in points_method:
                    settings = points_method['s']
                else:
                    settings = None

                build = self._racecontext.race_points_manager.assign(method_type, build, settings)
                build['meta']['primary_points'] = True

        self.set_results_savedRaceMeta(race, token, build)
        return build

    def set_results_savedRaceMeta(self, savedRaceMeta_or_id, token, results):
        race = self.resolve_savedRaceMeta_from_savedRaceMeta_or_id(savedRaceMeta_or_id)

        if not race:
            return False

        if race._cache_status:
            cacheStatus = json.loads(race._cache_status)
            if cacheStatus['data_ver'] == token:
                cacheStatus['build_ver'] = token
                race.results = results
                race._cache_status = json.dumps(cacheStatus)

                self.commit()
                return race
            else:
                logger.info('Ignoring cache write; token mismatch {} / {}'.format(cacheStatus['data_ver'], token))
                return False
        else:
            logger.error('Ignoring cache write for race {}: status is invalid'.format(race.id))
            return False

    def clear_results_savedRaceMeta(self, savedRaceMeta_or_id, token=None):
        race = self.resolve_savedRaceMeta_from_savedRaceMeta_or_id(savedRaceMeta_or_id)

        if not race:
            return False

        if token is None:
            token = monotonic()

        race._cache_status = json.dumps({
            'data_ver': token,
            'build_ver': None
        })

        self.commit()
        return race

    def clear_results_savedRaceMetas(self):
        token = monotonic()

        initStatus = json.dumps({
            'data_ver': token,
            'build_ver': None
        })

        Database.SavedRaceMeta.query.update({
            Database.SavedRaceMeta._cache_status: initStatus
            })
        self.commit()

    def get_max_round(self, heat_id):
        return int(Database.DB_session.query(
            Database.DB.func.max(
                Database.SavedRaceMeta.round_id
            )).filter_by(heat_id=heat_id).scalar() or 0)

    def get_round_num_for_heat(self, heat_id):
        if heat_id and heat_id is not RHUtils.HEAT_ID_NONE:
            round_idx = self.get_max_round(heat_id)
            if type(round_idx) is int:
                return round_idx + 1
        return 0

    #SavedRace Attributes
    def get_savedrace_attribute(self, savedrace_or_id, name):
        savedrace_id = self.resolve_id_from_savedRaceMeta_or_id(savedrace_or_id)
        return Database.SavedRaceMetaAttribute.query.filter_by(id=savedrace_id, name=name).one_or_none()

    def get_savedrace_attribute_value(self, savedrace_or_id, name, default_value=None):
        savedrace_id = self.resolve_id_from_savedRaceMeta_or_id(savedrace_or_id)
        attr = Database.SavedRaceMetaAttribute.query.filter_by(id=savedrace_id, name=name).one_or_none()

        if attr is not None:
            return attr.value
        else:
            return default_value

    def get_savedrace_attributes(self, savedrace_or_id):
        savedrace_id = self.resolve_id_from_savedRaceMeta_or_id(savedrace_or_id)
        return Database.SavedRaceMetaAttribute.query.filter_by(id=savedrace_id).all()

    def get_savedrace_id_by_attribute(self, name, value):
        attrs = Database.SavedRaceMetaAttribute.query.filter_by(name=name, value=value).all()
        return [attr.id for attr in attrs]

    # Pilot-Races
    def get_savedPilotRace(self, pilotrace_id):
        return Database.SavedPilotRace.query.get(pilotrace_id)

    def get_savedPilotRaces(self):
        return Database.SavedPilotRace.query.all()

    def get_savedPilotRaces_by_savedRaceMeta(self, race_id):
        return Database.SavedPilotRace.query.filter_by(race_id=race_id).all()

    def alter_savedPilotRace(self, data):
        pilotrace = Database.SavedPilotRace.query.get(data['pilotrace_id'])

        if 'enter_at' in data:
            pilotrace.enter_at = data['enter_at']
        if 'exit_at' in data:
            pilotrace.exit_at = data['exit_at']

        self.commit()

        return True

    def savedPilotRaces_has_pilot(self, pilot_id):
        return bool(Database.SavedPilotRace.query.filter_by(pilot_id=pilot_id).count())

    # Race Laps
    def get_savedRaceLaps(self):
        return Database.SavedRaceLap.query.all()

    def get_savedRaceLaps_by_savedPilotRace(self, pilotrace_id):
        return Database.SavedRaceLap.query.filter_by(pilotrace_id=pilotrace_id).order_by(Database.SavedRaceLap.lap_time_stamp).all()

    def get_active_savedRaceLaps(self):
        return Database.SavedRaceLap.query.filter(Database.SavedRaceLap.deleted != 1).all()

    def get_active_savedRaceLaps_by_savedPilotRace(self, pilotrace_id):
        return Database.SavedRaceLap.query.filter(Database.SavedRaceLap.deleted != 1, Database.SavedRaceLap.pilotrace_id == pilotrace_id).order_by(Database.SavedRaceLap.lap_time_stamp).all()

    # Race general
    def replace_savedRaceLaps(self, data):
        Database.SavedRaceLap.query.filter_by(pilotrace_id=data['pilotrace_id']).delete()

        for lap in data['laps']:
            Database.DB_session.add(Database.SavedRaceLap(
                race_id=data['race_id'],
                pilotrace_id=data['pilotrace_id'],
                node_index=data['node_index'],
                pilot_id=data['pilot_id'],
                lap_time_stamp=lap['lap_time_stamp'],
                lap_time=lap['lap_time'],
                lap_time_formatted=lap['lap_time_formatted'],
                source = lap['source'],
                deleted = lap['deleted']
            ))

        self.commit()
        return True

    # Race general
    def add_race_data(self, data):
        for node_index, node_data in data.items():
            new_pilotrace = Database.SavedPilotRace(
                race_id=node_data['race_id'],
                node_index=node_index,
                pilot_id=node_data['pilot_id'],
                history_values=node_data['history_values'],
                history_times=node_data['history_times'],
                penalty_time=0,
                enter_at=node_data['enter_at'],
                exit_at=node_data['exit_at'],
                frequency=node_data['frequency']
            )

            Database.DB_session.add(new_pilotrace)
            Database.DB_session.flush()
            Database.DB_session.refresh(new_pilotrace)

            for lap in node_data['laps']:
                Database.DB_session.add(Database.SavedRaceLap(
                    race_id=node_data['race_id'],
                    pilotrace_id=new_pilotrace.id,
                    node_index=node_index,
                    pilot_id=node_data['pilot_id'],
                    lap_time_stamp=lap.lap_time_stamp,
                    lap_time=lap.lap_time,
                    lap_time_formatted=lap.lap_time_formatted,
                    source=lap.source,
                    deleted=lap.deleted
                ))

        self.commit()
        return True

    def clear_race_data(self):
        Database.DB_session.query(Database.SavedRaceMeta).delete()
        Database.DB_session.query(Database.SavedRaceMetaAttribute).delete()
        Database.DB_session.query(Database.SavedPilotRace).delete()
        Database.DB_session.query(Database.SavedRaceLap).delete()
        Database.DB_session.query(Database.LapSplit).delete()
        for heat in self.get_heats():
            heat.active = True
        self.commit()
        self.reset_pilot_used_frequencies()
        self.reset_heat_plans()
        logger.info('Database saved races reset')
        return True

    # Splits
    def get_lapSplits(self):
        return Database.LapSplit.query.all()

    def get_lapSplits_by_lap(self, node_index, lap_id):
        return Database.LapSplit.query.filter_by(
            node_index=node_index,
            lap_id=lap_id
            ).all()

    def get_lapSplit_by_params(self, node_index, lap_id, split_id):
        return Database.LapSplit.query.filter_by(
            node_index=node_index,
            lap_id=lap_id,
            split_id=split_id
            ).one_or_none()

    def add_lapSplit(self, init=None):
        lap_split = Database.LapSplit(
            node_index=0,
            pilot_id=RHUtils.PILOT_ID_NONE,
            lap_id=0,
            split_id=0,
            split_time_stamp='',
            split_time=0,
            split_time_formatted=0,
            split_speed=0
        )

        if init:
            if 'node_index' in init:
                lap_split.node_index = init['node_index']
            if 'pilot_id' in init:
                lap_split.pilot_id = init['pilot_id']
            if 'lap_id' in init:
                lap_split.lap_id = init['lap_id']
            if 'split_id' in init:
                lap_split.split_id = init['split_id']
            if 'split_time_stamp' in init:
                lap_split.split_time_stamp = init['split_time_stamp']
            if 'split_time' in init:
                lap_split.split_time = init['split_time']
            if 'split_time_formatted' in init:
                lap_split.split_time_formatted = init['split_time_formatted']
            if 'split_speed' in init:
                lap_split.split_speed = init['split_speed']

        Database.DB_session.add(lap_split)
        self.commit()

    def clear_lapSplit(self, lapSplit):
        Database.DB_session.delete(lapSplit)
        self.commit()
        return True

    def clear_lapSplits(self):
        Database.DB_session.query(Database.LapSplit).delete()
        self.commit()
        return True

    # Options
    def get_options(self):
        return Database.GlobalSettings.query.all()

    def get_option(self, option, default_value=None):
        try:
            val = self._OptionsCache[option]
            if val or val == "":
                output = val
            else:
                output = default_value
        except:
            output = default_value

        return self._filters.run_filters(Flt.OPTION_GET, output)

    def set_option(self, option, value):
        value = self._filters.run_filters(Flt.OPTION_SET, value)

        if isinstance(value, bool):
            value = '1' if value else '0'

        self._OptionsCache[option] = str(value)

        settings = Database.GlobalSettings.query.filter_by(option_name=option).one_or_none()
        if settings:
            settings.option_value = value
        else:
            Database.DB_session.add(Database.GlobalSettings(option_name=option, option_value=value))
        self.commit()

    def get_optionInt(self, option, default_value=0):
        try:
            val = self._OptionsCache[option]
            if val:
                output = int(val)
            else:
                output = default_value
        except:
            output = default_value

        return self._filters.run_filters(Flt.OPTION_GET_INT, output)

    def delete_option(self, option):
        Database.GlobalSettings.query.filter_by(option_name=option).delete()
        self.commit()

    def clear_options(self):
        Database.DB_session.query(Database.GlobalSettings).delete()
        self.commit()
        return True

    def reset_options(self):
        self.clear_options()
        self.set_option("server_api", self._SERVER_API)
        # timer state
        self.set_option("currentProfile", "1")
        self.set_option("currentFormat", "1")
        self.set_option("currentHeat", "0")
        # minimum lap
        self.set_option("MinLapSec", "10")
        # event information
        self.set_option("eventName", self.generate_new_event_name())
        self.set_option("eventDescription", "")
        # Event results cache
        self.set_option("eventResults_cacheStatus", None)

        logger.info("Reset event options")

    def generate_new_event_name(self):
        return "{} {}".format(datetime.now().strftime('%Y-%m-%d'), self.__("FPV Race"))

    # Event Results (Options)
    def get_results_event(self):
        if len(self.get_savedRaceMetas()) < 1:
            # no races exist, skip calculating
            return None

        cache_invalid = False
        eventStatus = self.get_option("eventResults_cacheStatus")
        if eventStatus:
            try:
                cacheStatus = json.loads(eventStatus)
                token = cacheStatus['data_ver']
                if cacheStatus['data_ver'] == cacheStatus['build_ver']:
                    # cache hit
                    return json.loads(self.get_option("eventResults"))
                # else: cache miss
            except ValueError:
                cache_invalid = True
        else:
            cache_invalid = True

        if cache_invalid:
            logger.error('Event cache has invalid status')
            token = monotonic()
            self.clear_results_event(token)

        # cache rebuild
        logger.debug('Building Event results')
        build = Results.build_leaderboard_event(self._racecontext)
        self.set_results_event(token, build)
        return build

    def set_results_event(self, token, results):
        eventStatus = self.get_option("eventResults_cacheStatus")
        cacheStatus = json.loads(eventStatus)
        if cacheStatus['data_ver'] == token:
            cacheStatus['build_ver'] = token
            self.set_option("eventResults", json.dumps(results))
            self.set_option("eventResults_cacheStatus", json.dumps(cacheStatus))

        self.commit()
        return True

    def clear_results_event(self, token=None):
        if token is None:
            token = monotonic()

        eventStatus = json.dumps({
            'data_ver': token,
            'build_ver': None
        })

        self.set_option("eventResults_cacheStatus", eventStatus)
        return True

    def clear_results_all(self):
        ''' Check all caches and invalidate any paused builds '''
        self.clear_results_savedRaceMetas()
        self.clear_results_heats()
        self.clear_results_raceClasses()
        self.clear_results_event()

        logger.debug('All Result caches invalidated')


def getFastestSpeedStr(rhapi, spoken_flag, sel_pilot_id=None):
    fastest_str = ""
    lap_splits = rhapi.db.lap_splits()
    if lap_splits and len(lap_splits) > 0:
        pilot_obj = None
        if sel_pilot_id:  # if 'sel_pilot_id' given then only use splits from that pilot
            if rhapi.race.race_winner_lap_id > 0:  # filter out splits after race winner declared
                lap_splits = [s for s in lap_splits if s.lap_id < rhapi.race.race_winner_lap_id and \
                              s.pilot_id == sel_pilot_id]
            else:
                lap_splits = [s for s in lap_splits if s.pilot_id == sel_pilot_id]
        else:
            if rhapi.race.race_winner_lap_id > 0:  # filter out splits after race winner declared
                lap_splits = [s for s in lap_splits if s.lap_id < rhapi.race.race_winner_lap_id]
        fastest_split = max(lap_splits, default=None, key=lambda s: (s.split_speed if s.split_speed else 0.0))
        if fastest_split and fastest_split.split_speed:
            if sel_pilot_id:
                if spoken_flag:
                    fastest_str = "{:.1f}".format(fastest_split.split_speed)
                else:
                    fastest_str = "{}".format(fastest_split.split_speed)
            else:
                pilot_obj = rhapi.db.pilot_by_id(fastest_split.pilot_id)
                if pilot_obj:
                    if spoken_flag:
                        fastest_str = "{}, {}".format((pilot_obj.phonetic or pilot_obj.callsign),
                                                      "{:.1f}".format(fastest_split.split_speed))
                    else:
                        fastest_str = "{} {}".format(pilot_obj.callsign, fastest_split.split_speed)
    return fastest_str

# Text replacer
def doReplace(rhapi, text, args, spoken_flag=False, delay_sec_holder=None):
    if '%' in text:
        race_results = rhapi.race.results
        heat_data = None

        # %HEAT% : Current heat name or ID value
        if '%HEAT%' in text:
            if 'heat_id' in args:
                heat_data = rhapi.db.heat_by_id(args['heat_id'])
            else:
                heat_data = rhapi.db.heat_by_id(rhapi.race.heat)

            heat_name = None
            if heat_data:
                if spoken_flag:
                    heat_name = heat_data.display_name_short
                else:
                    heat_name = heat_data.display_name

            if not heat_name:
                heat_name = rhapi.__('None')

            text = text.replace('%HEAT%', heat_name)

        pilot_name_str = ''
        if 'pilot_id' in args or 'node_index' in args:
            if 'pilot_id' in args:
                pilot = rhapi.db.pilot_by_id(args['pilot_id'])
            else:
                pilot = rhapi.db.pilot_by_id(rhapi.race.pilots.get(args['node_index']))
            if pilot:
                pilot_name_str = pilot.spoken_callsign if spoken_flag else pilot.display_callsign
                text = text.replace('%PILOT%', pilot_name_str)

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
                fastest_str = "{} {}".format(rhapi.__('Fastest lap time'), fastest_str)
            text = text.replace('%FASTEST_RACE_LAP_CALL%', fastest_str)

        if '%FASTEST_RACE_SPEED' in text:
            fastest_str = getFastestSpeedStr(rhapi, spoken_flag)
            # %FASTEST_RACE_SPEED% : Pilot/speed for fastest speed in race
            text = text.replace('%FASTEST_RACE_SPEED%', fastest_str)
            # %FASTEST_RACE_SPEED_CALL% : Pilot/speed for fastest speed in race (with prompt)
            if len(fastest_str) > 0:
                fastest_str = "{} {}".format(rhapi.__('Fastest speed'), fastest_str)
            text = text.replace('%FASTEST_RACE_SPEED_CALL%', fastest_str)

        if '%WINNER' in text:
            winner_str = rhapi.race.race_winner_phonetic if spoken_flag else rhapi.race.race_winner_name
            # %WINNER% : Pilot callsign for winner of race
            text = text.replace('%WINNER%', winner_str)
            # %WINNER_CALL% : Pilot callsign for winner of race (with prompt)
            if len(winner_str) > 0:
                winner_str = "{} {}".format(rhapi.__('Winner is'), winner_str)
            text = text.replace('%WINNER_CALL%', winner_str)

        if '%PREVIOUS_WINNER' in text:
            prev_winner_str = rhapi.race.prev_race_winner_phonetic if spoken_flag else rhapi.race.prev_race_winner_name
            # %PREVIOUS_WINNER% : Pilot callsign for winner of previous race
            text = text.replace('%PREVIOUS_WINNER%', prev_winner_str)
            # %PREVIOUS_WINNER_CALL% : Pilot callsign for winner of previous race (with prompt)
            if len(prev_winner_str) > 0:
                prev_winner_str = "{} {}".format(rhapi.__('Previous race winner was'), prev_winner_str)
            text = text.replace('%PREVIOUS_WINNER_CALL%', prev_winner_str)

        if '%ROUND' in text:
            round_id = rhapi.race.round
            if round_id:
                round_str = str(round_id)
                # %ROUND% : Current round number
                text = text.replace('%ROUND%', round_str)
                round_str = "{} {}".format(rhapi.__('Round'), round_str)
                # %ROUND_CALL% : Current round number (with prompt)
                text = text.replace('%ROUND_CALL%', round_str)

        # %RACE_FORMAT% : Current race format
        if '%RACE_FORMAT%' in text:
            format_obj = rhapi.race.raceformat
            fmt_str = getattr(format_obj, 'name', '') if format_obj else ''
            text = text.replace('%RACE_FORMAT%', fmt_str)
            text = text.replace(':00 ', (' ' + rhapi.__('minute') + ' '))
            text = text.replace('/', ' ')

        # %PILOTS% : List of pilot callsigns (read out slower)
        if '%PILOTS%' in text:
            text = text.replace('%PILOTS%', getPilotsListStr(rhapi, ' . ', spoken_flag))
        # %LINEUP% : List of pilot callsigns (read out faster)
        if '%LINEUP%' in text:
            text = text.replace('%LINEUP%', getPilotsListStr(rhapi, ' , ', spoken_flag))
        # %FREQS% : List of pilot callsigns and frequency assignments
        if '%FREQS%' in text:
            text = text.replace('%FREQS%', getPilotFreqsStr(rhapi, ' . ', spoken_flag))

        if '%SPLIT_' in text and type(args) == dict:
            # %SPLIT_TIME% : Split time for pilot
            if '%SPLIT_TIME%' in text:
                text = text.replace('%SPLIT_TIME%', RHUtils.format_phonetic_time_to_str(args.get('split_time'), \
                                        rhapi.config.get_item('UI', 'timeFormatPhonetic')) if spoken_flag \
                                            else RHUtils.format_split_time_to_str(args.get('split_time'), \
                                                                   rhapi.config.get_item('UI', 'timeFormat')))
            # %SPLIT_SPEED% : Split speed for pilot
            if '%SPLIT_SPEED%' in text:
                text = text.replace('%SPLIT_SPEED%', \
                                        "{:.1f}".format(args.get('split_speed', 0.0)) if spoken_flag \
                                            else str(args.get('split_speed', '')))

        if '%CURRENT_TIME' in text:
            now_obj = datetime.now()
            # %CURRENT_TIME_AP% : Current time (12-hour clock)
            text = text.replace('%CURRENT_TIME_AP%', now_obj.strftime("%I:%M %p"))
            # %CURRENT_TIME_24% : Current time (24-hour clock)
            text = text.replace('%CURRENT_TIME_24%', now_obj.strftime("%H:%M"))
            # %CURRENT_TIME_SECS_AP% : Current time, with seconds (12-hour clock)
            text = text.replace('%CURRENT_TIME_SECS_AP%', now_obj.strftime("%I:%M:%S %p"))
            # %CURRENT_TIME_SECS_24% : Current time, with seconds (24-hour clock)
            text = text.replace('%CURRENT_TIME_SECS_24%', now_obj.strftime("%H:%M:%S"))

        leaderboard = None
        node_idx_val = RHUtils.getNumericEntry(args, 'node_index', -1)
        if node_idx_val >= 0 and '%' in text:
            lboard_name = race_results.get('meta', {}).get('primary_leaderboard', '')
            leaderboard = race_results.get(lboard_name, [])

            for result in leaderboard:
                if result.get('node') == node_idx_val:
                    # %LAP_COUNT% : Current lap number
                    text = text.replace('%LAP_COUNT%', str(result.get('laps')))

                    # %TOTAL_TIME% : Total time since start of race for pilot
                    text = text.replace('%TOTAL_TIME%', RHUtils.format_phonetic_time_to_str( \
                        result.get('total_time_raw'), rhapi.config.get_item('UI', 'timeFormatPhonetic')) \
                                            if spoken_flag else str(result.get('total_time', '')))

                    # %TOTAL_TIME_LAPS%: Total time since start of first lap for pilot
                    text = text.replace('%TOTAL_TIME_LAPS%', RHUtils.format_phonetic_time_to_str( \
                        result.get('total_time_laps_raw'), rhapi.config.get_item('UI', 'timeFormatPhonetic')) \
                                            if spoken_flag else str(result.get('total_time_laps', '')))

                    # %LAST_LAP% : Last lap time for pilot
                    text = text.replace('%LAST_LAP%', RHUtils.format_phonetic_time_to_str( \
                        result.get('last_lap_raw'), rhapi.config.get_item('UI', 'timeFormatPhonetic')) \
                                            if spoken_flag else str(result.get('last_lap', '')))

                    # %AVERAGE_LAP% : Average lap time for pilot
                    text = text.replace('%AVERAGE_LAP%', RHUtils.format_phonetic_time_to_str( \
                        result.get('average_lap_raw'), rhapi.config.get_item('UI', 'timeFormatPhonetic')) \
                                            if spoken_flag else str(result.get('average_lap', '')))

                    # %FASTEST_LAP% : Fastest lap time
                    text = text.replace('%FASTEST_LAP%', RHUtils.format_phonetic_time_to_str( \
                        result.get('fastest_lap_raw'), rhapi.config.get_item('UI', 'timeFormatPhonetic')) \
                                            if spoken_flag else str(result.get('fastest_lap', '')))

                    if '%TIME_BEHIND' in text:
                        behind_str = RHUtils.format_phonetic_time_to_str( \
                            result.get('time_behind_raw', ''), rhapi.config.get_item('UI', 'timeFormatPhonetic')) \
                                                if spoken_flag else str(result.get('time_behind', ''))
                        pos_bhind_str = ''
                        if behind_str:
                            # %TIME_BEHIND% : Amount of time behind race leader
                            text = text.replace('%TIME_BEHIND%', behind_str)
                            if len(behind_str) > 0:
                                behind_str = "{} {}".format(behind_str, rhapi.__('behind'))
                                pos_bhind_str = str(result.get('position', ''))
                                if pos_bhind_str == '1':  # only do %TIME_BEHIND_POS_CALL% if not first
                                    pos_bhind_str = ''
                        # %TIME_BEHIND_CALL% : Amount of time behind race leader (with prompt)
                        text = text.replace('%TIME_BEHIND_CALL%', behind_str)
                        if "%TIME_BEHIND_FINPLACE_CALL%" in text:
                            place_str = get_position_place_str(rhapi, pos_bhind_str)
                            if place_str is not None:
                                pos_bhind_str = "{} {} {} {} {}, {}".format(rhapi.__('Pilot'), \
                                                                     pilot_name_str, rhapi.__('finished in'), \
                                                                     place_str, rhapi.__('place'), behind_str)
                            elif len(pos_bhind_str) > 0:
                                pos_bhind_str = "{} {} {} {}, {}".format(rhapi.__('Pilot'), \
                                                                         pilot_name_str, rhapi.__('finished at position'), \
                                                                         pos_bhind_str, behind_str)
                            # %TIME_BEHIND_FINPLACE_CALL% : Pilot NAME finished in X place, MM:SS.SSS behind
                            text = text.replace('%TIME_BEHIND_FINPLACE_CALL%', pos_bhind_str)
                        else:
                            if len(pos_bhind_str) > 0:
                                pos_bhind_str = "{} {} {} {}, {}".format(rhapi.__('Pilot'), \
                                                                         pilot_name_str, rhapi.__('finished at position'), \
                                                                         pos_bhind_str, behind_str)
                            # %TIME_BEHIND_FINPOS_CALL% : Pilot NAME finished at position X, MM:SS.SSS behind
                            text = text.replace('%TIME_BEHIND_FINPOS_CALL%', pos_bhind_str)

                    # %FASTEST_SPEED% : Fastest speed for pilot
                    text = text.replace('%FASTEST_SPEED%', getFastestSpeedStr(rhapi, spoken_flag, \
                                                                              result.get('pilot_id')))

                    # %CONSECUTIVE% : Fastest consecutive laps for pilot
                    if result.get('consecutives_base') == int(rhapi.db.option('consecutivesCount', 3)):
                        text = text.replace('%CONSECUTIVE%', RHUtils.format_phonetic_time_to_str( \
                            result.get('consecutives_raw'), rhapi.config.get_item('UI', 'timeFormatPhonetic')) \
                            if spoken_flag else str(result.get('consecutives', '')))
                    else:
                        text = text.replace('%CONSECUTIVE%', rhapi.__('None'))

                    if '%POSITION' in text:
                        position_str = str(result.get('position', ''))
                        if '%POSITION_PLACE' in text:
                            place_str = get_position_place_str(rhapi, position_str)
                            if place_str is not None:
                                # %POSITION_PLACE% : Race position (first, second, etc) for pilot
                                text = text.replace('%POSITION_PLACE%', place_str)
                                # %POSITION_PLACE_CALL% : Race position (first, second, etc) for pilot (with prompt)
                                if len(place_str) > 0:
                                    place_str = "{} {}".format(place_str, rhapi.__('place'))
                                text = text.replace('%POSITION_PLACE_CALL%', place_str)
                            else:
                                text = text.replace('%POSITION_PLACE%', position_str)
                                if len(position_str) > 0:
                                    position_str = "{} {}".format(rhapi.__('Position'), position_str)
                                text = text.replace('%POSITION_PLACE_CALL%', position_str)
                        else:
                            # %POSITION% : Race position for pilot
                            text = text.replace('%POSITION%', position_str)
                            # %POSITION_CALL% : Race position for pilot (with prompt)
                            if len(position_str) > 0:
                                position_str = "{} {}".format(rhapi.__('Position'), position_str)
                            text = text.replace('%POSITION_CALL%', position_str)

                    break

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

        # %DELAY_#_SECS% : Delay callout by given number of seconds
        if '%DELAY_' in text:
            num_str = text[7:]
            pos = num_str.find('_SECS%')
            vlen = 13
            if pos < 0:
                pos = num_str.find('_SEC%')
                vlen -= 1
            if pos > 0:
                num_str = num_str[:pos]
                if num_str.replace('.','',1).isdigit():
                    if isinstance(delay_sec_holder, list):
                        delay_sec_holder.clear()
                        delay_sec_holder.append(float(num_str))
                    text = text[(len(num_str)+vlen):].strip()

        # %COOP_RACE_INFO% : Co-op race mode information (target time or laps)
        if '%COOP_RACE_INFO%' in text:
            format_obj = rhapi.race.raceformat
            info_str = ''
            if format_obj and format_obj.team_racing_mode == RacingMode.COOP_ENABLED:
                if not heat_data:
                    if 'heat_id' in args:
                        heat_data = rhapi.db.heat_by_id(args['heat_id'])
                    else:
                        heat_data = rhapi.db.heat_by_id(rhapi.race.heat)
                if heat_data:
                    if format_obj.win_condition == WinCondition.FIRST_TO_LAP_X:
                        if heat_data.coop_best_time and heat_data.coop_best_time > 0.001:
                            c_time_ms = int(round(heat_data.coop_best_time,1)*1000)
                            c_time_str = RHUtils.format_phonetic_time_to_str(c_time_ms, \
                                        rhapi.config.get_item('UI', 'timeFormatPhonetic')) \
                                        if spoken_flag else RHUtils.format_time_to_str(c_time_ms, \
                                                            rhapi.config.get_item('UI', 'timeFormat'))
                            info_str = rhapi.__('target time is') + ' ' + c_time_str
                        else:
                            info_str = rhapi.__('benchmark race')
                    else:
                        if heat_data.coop_num_laps and heat_data.coop_num_laps > 0:
                            info_str = rhapi.__('target laps is') + ' ' + str(heat_data.coop_num_laps)
                        else:
                            info_str = rhapi.__('benchmark race')
            text = text.replace('%COOP_RACE_INFO%', info_str)

        # %COOP_RACE_LAP_TOTALS% : Pilot lap counts for race in co-op mode
        if '%COOP_RACE_LAP_TOTALS%' in text:
            format_obj = rhapi.race.raceformat
            totals_str = ''
            if format_obj and format_obj.team_racing_mode == RacingMode.COOP_ENABLED:
                if not leaderboard:
                    lboard_name = race_results.get('meta', {}).get('primary_leaderboard', '')
                    leaderboard = race_results.get(lboard_name, [])
                totals_str = getPilotLapsStr(rhapi, ' , ', spoken_flag, leaderboard)
            text = text.replace('%COOP_RACE_LAP_TOTALS%', totals_str)

        # %RACE_RESULT% : Race result status message (race winner or co-op result)
        if '%RACE_RESULT%' in text:
            result_str = rhapi.race.phonetic_status_msg if spoken_flag else rhapi.race.status_message
            text = text.replace('%RACE_RESULT%', result_str if result_str else '')

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

def getPilotLapsStr(rhapi, sep_str, spoken_flag, leaderboard):
    pilots_str = ''
    first_flag = True
    for result in leaderboard:
        pilot_obj = rhapi.db.pilot_by_id(result.get('pilot_id'))
        if pilot_obj:
            text = pilot_obj.spoken_callsign if spoken_flag else pilot_obj.display_callsign
            if text:
                lap_count = result.get('laps')
                if lap_count:
                    if first_flag:
                        first_flag = False
                    else:
                        pilots_str += sep_str
                    pilots_str += text + ' ' + rhapi.__('had') + ' ' + str(lap_count) + ' ' + \
                                      (rhapi.__('laps') if str(lap_count) != '1' else rhapi.__('lap'))
    return pilots_str

def get_position_place_str(rhapi, pos_str):
    global Position_place_strings
    if type(Position_place_strings) is not list:
        Position_place_strings = rhapi.__("first,second,third,fourth,fifth,sixth,seventh,eighth,ninth,tenth,eleventh,\
            twelfth,thirteenth,fourteenth,fifteenth,sixteenth,seventeenth,eighteenth,nineteenth,twentieth").split(',')
    try:
        pos_val = int(pos_str) - 1
        if pos_val >= 0 and pos_val < len(Position_place_strings):
            return Position_place_strings[pos_val]
    except:
        pass
    return None
