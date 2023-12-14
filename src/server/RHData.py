#
# RaceData
# Provides abstraction for database and results page caches
#

import logging
logger = logging.getLogger(__name__)

from sqlalchemy import create_engine, MetaData, Table, inspect
from datetime import datetime
import os
import traceback
import shutil
import json
import glob
import RHUtils
import Database
import Results
from monotonic import monotonic
from eventmanager import Evt
from RHRace import RaceStatus, WinCondition, StagingTones
from Database import ProgramMethod, HeatAdvanceType, HeatStatus

class RHData():
    _OptionsCache = {} # Local Python cache for global settings
    TEAM_NAMES_LIST = [str(chr(i)) for i in range(65, 91)]  # list of 'A' to 'Z' strings

    def __init__(self, DBObj, Events, RaceContext, SERVER_API, DB_FILE_NAME, DB_BKP_DIR_NAME):
        self._Database = DBObj
        self._Events = Events
        self._racecontext = RaceContext
        self._SERVER_API = SERVER_API
        self._DB_FILE_NAME = DB_FILE_NAME
        self._DB_BKP_DIR_NAME = DB_BKP_DIR_NAME

    def __(self, *args, **kwargs):
        return self._racecontext.language.__(*args, **kwargs)

    # Integrity Checking
    def check_integrity(self):
        try:
            if self.get_optionInt('server_api') < self._SERVER_API:
                logger.info('Old server API version; recovering database')
                return False
            if not self._Database.Profiles.query.count():
                logger.info('Profiles are empty; recovering database')
                return False
            if not self._Database.RaceFormat.query.count():
                logger.info('Formats are empty; recovering database')
                return False
            try:  # make sure no problems reading 'Heat' table data
                self._Database.Heat.query.all()
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
        settings = self._Database.GlobalSettings.query.all()
        self._OptionsCache = {} # empty cache
        for setting in settings:
            self._OptionsCache[setting.option_name] = setting.option_value

    # General
    def db_init(self, nofill=False):
        # Creates tables from database classes/models
        try:
            self._Database.DB.create_all()
            self.reset_all(nofill) # Fill with defaults
            return True
        except Exception as ex:
            logger.error('Error creating database: ' + str(ex))
            return False

    def do_reset_all(self, nofill):
        self.reset_pilots()
        if nofill:
            self.reset_heats(nofill=True)
        else:
            self.reset_heats()
        self.clear_race_data()
        self.reset_profiles()
        self.reset_raceFormats()
        self.reset_raceClasses()
        self.reset_options()

    def reset_all(self, nofill=False):
        try:
            self.do_reset_all(nofill)
        except Exception as ex:
            logger.warning("Doing DB session rollback and retry after error: {}".format(ex))
            self._Database.DB.session.rollback()
            self.do_reset_all(nofill)

    def commit(self):
        try:
            self._Database.DB.session.commit()
            return True
        except Exception as ex:
            logger.error('Error writing to database: ' + str(ex))
            return False

    def rollback(self):
        try:
            self._Database.DB.session.rollback()
            return True
        except Exception as ex:
            logger.error('Error rolling back to database: ' + str(ex))
            return False

    def close(self):
        try:
            self._Database.DB.session.close()
            return True
        except Exception as ex:
            logger.error('Error closing to database: ' + str(ex))
            return False

    def clean(self):
        try:
            with self._Database.DB.engine.begin() as conn:
                conn.execute("VACUUM")
            return True
        except Exception as ex:
            logger.error('Error cleaning database: ' + str(ex))
            return False

    # File Handling

    def backup_db_file(self, copy_flag, prefix_str=None):
        self.close()
        self.clean()
        try:     # generate timestamp from last-modified time of database file
            time_str = datetime.fromtimestamp(os.stat(self._DB_FILE_NAME).st_mtime).strftime('%Y%m%d_%H%M%S')
        except:  # if error then use 'now' timestamp
            time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        try:
            (dbname, dbext) = os.path.splitext(self._DB_FILE_NAME)
            if prefix_str:
                dbname = prefix_str + dbname
            bkp_name = self._DB_BKP_DIR_NAME + '/' + dbname + '_' + time_str + dbext
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

    def get_legacy_table_data(self, metadata, table_name, filter_crit=None, filter_value=None):
        try:
            table = Table(table_name, metadata, autoload=True)
            if filter_crit is None:
                data = table.select().execute().fetchall()
            else:
                data = table.select().execute().filter(filter_crit==filter_value).fetchall()

            output = []
            for row in data:
                d = dict(row.items())
                output.append(d)

            return output

        except Exception as ex:
            logger.warning('Unable to read "{0}" table from previous database: {1}'.format(table_name, ex))

    def restore_table(self, class_type, table_query_data, **kwargs):
        if table_query_data:
            mapped_instance = inspect(class_type)
            table_name_str = "???"
            try:
                table_name_str = getattr(class_type, '__name__', '???')
                logger.debug("Restoring database table '{}' (len={})".format(table_name_str, len(table_query_data)))
                restored_row_count = 0
                for table_query_row in table_query_data:  # for each row of data queried from previous database
                    try:
                        # check if row is 'Pilot' entry that should be ignored
                        if (class_type is not self._Database.Pilot) or getattr(table_query_row, 'callsign', '') != '-' or \
                                                      getattr(table_query_row, 'name', '') != '-None-':

                            # check if row with matching 'id' value already exists in new DB table
                            if 'id' in mapped_instance.attrs.keys() and 'id' in table_query_row.keys():
                                table_row_id = table_query_row['id']
                                matching_row = class_type.query.filter(getattr(class_type,'id')==table_row_id).first()
                            else:
                                table_row_id = None
                                matching_row = None

                            # if row with matching 'id' value was found then update it; otherwise create new row data
                            db_row_update = matching_row if matching_row is not None else class_type()

                            for col in mapped_instance.attrs.keys():  # for each column in new database table
                                if col in table_query_row.keys() and table_query_row[col] is not None:  # matching column exists in previous DB table
                                    col_val = table_query_row[col]
                                    try:  # get column type in new database table
                                        table_col_type = class_type.__table__.columns[col].type.python_type
                                    except Exception as ex:
                                        logger.debug("Unable to determine type for column '{}' in 'restore_table' ('{}'): {}".\
                                                     format(col, table_name_str, getattr(type(ex), '__name__', '????')))
                                        table_col_type = None
                                    if table_col_type is not None and col_val is not None:
                                        col_val_str = str(col_val)
                                        if len(col_val_str) >= 50:
                                            col_val_str = col_val_str[:50] + "..."
                                        if logger.getEffectiveLevel() <= logging.DEBUG and len(table_query_data) <= 25:
                                            logger.debug("restore_table ('{}'): col={}, coltype={}, val={}, valtype={}".\
                                                         format(table_name_str, col, getattr(table_col_type, '__name__', '???'), \
                                                                col_val_str, getattr(type(col_val), '__name__', '???')))
                                        try:
                                            col_val = table_col_type(col_val)  # explicitly cast value to new-DB column type
                                        except:
                                            logger.warning("Using default because of mismatched type in 'restore_table' ('{}'): col={}, coltype={}, newval={}, newtype={}".\
                                                           format(table_name_str, col, getattr(table_col_type, '__name__', '???'), \
                                                                  col_val_str, getattr(type(col_val), '__name__', '???')))
                                            col_val = kwargs['defaults'].get(col)
                                else:  # matching column does not exist in previous DB table; use default value
                                    col_val = kwargs['defaults'].get(col) if col != 'id' else None

                                if col_val is not None:
                                    setattr(db_row_update, col, col_val)

                            if matching_row is None:  # if new row data then add to table
                                self._Database.DB.session.add(db_row_update)
                                if logger.getEffectiveLevel() <= logging.DEBUG and len(table_query_data) <= 25:
                                    logger.debug("restore_table: added new row to table '{}'".format(table_name_str))
                            else:
                                if logger.getEffectiveLevel() <= logging.DEBUG and len(table_query_data) <= 25:
                                    logger.debug("restore_table: updated row in table '{}', id={}".format(table_name_str, table_row_id))

                            self._Database.DB.session.flush()
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

        # stage 0: collect data from file
        try:
            logger.info('Recovering data from previous database')

            # load file directly
            engine = create_engine('sqlite:///%s' % dbfile, convert_unicode=True)
            metadata = MetaData(bind=engine)

            options_query_data = self.get_legacy_table_data(metadata, 'global_settings')

            migrate_db_api = 0 # delta5 or very old RH versions
            if options_query_data:
                for row in options_query_data:
                    if row['option_name'] == 'server_api':
                        migrate_db_api = int(row['option_value'])
                        break

            if migrate_db_api > self._SERVER_API:
                raise ValueError('Database version is newer than server version')

            pilot_query_data = self.get_legacy_table_data(metadata, 'pilot')
            heat_query_data = self.get_legacy_table_data(metadata, 'heat')
            heatNode_query_data = self.get_legacy_table_data(metadata, 'heat_node')
            raceFormat_query_data = self.get_legacy_table_data(metadata, 'race_format')
            profiles_query_data = self.get_legacy_table_data(metadata, 'profiles')
            raceClass_query_data = self.get_legacy_table_data(metadata, 'race_class')
            raceMeta_query_data = self.get_legacy_table_data(metadata, 'saved_race_meta')
            racePilot_query_data = self.get_legacy_table_data(metadata, 'saved_pilot_race')
            raceLap_query_data = self.get_legacy_table_data(metadata, 'saved_race_lap')

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
                "ledEffects",
                "ledBrightness",
                "ledColorNodes",
                "ledColorFreqs",
                "startThreshLowerAmount",
                "startThreshLowerDuration",
                "nextHeatBehavior",
                "voiceCallouts",
                "actions",
                "consecutivesCount"
            ]

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

        self.db_init(nofill=True)

        # stage 1: recover pilots, heats, heatnodes, format, profile, class, options
        if recover_status['stage_0'] == True:
            try:
                if pilot_query_data:
                    self._Database.DB.session.query(self._Database.Pilot).delete()
                    self.restore_table(self._Database.Pilot, pilot_query_data, defaults={
                            'name': 'New Pilot',
                            'callsign': 'New Callsign',
                            'team': RHUtils.DEF_TEAM_NAME,
                            'phonetic': '',
                            'color': None,
                            'used_frequencies': None
                        })
                    for pilot in self._Database.Pilot.query.all():
                        if not pilot.color:
                            pilot.color = RHUtils.hslToHex(False, 100, 50)
                else:
                    self.reset_pilots()

                if migrate_db_api < 27:
                    # old heat DB structure; migrate node 0 to heat table

                    # build list of heat meta
                    heat_extracted_meta = []
                    if len(heat_query_data):
                        for row in heat_query_data:
                            if 'node_index' in row:
                                if row['node_index'] == 0:
                                    new_row = {}
                                    new_row['id'] = row['heat_id']
                                    if 'note' in row:
                                        new_row['name'] = row['note']
                                    if 'class_id' in row:
                                        new_row['class_id'] = row['class_id']

                        self.restore_table(self._Database.Heat, heat_extracted_meta, defaults={
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

                        self._Database.DB.session.query(self._Database.HeatNode).delete()
                        self.restore_table(self._Database.HeatNode, heatnode_extracted_data, defaults={
                                'pilot_id': RHUtils.PILOT_ID_NONE,
                                'color': None
                            })
                    else:
                        self.reset_heats()
                else:
                    # current heat structure; use basic migration

                    if heat_query_data:
                        for row in heat_query_data:
                            if 'note' in row:
                                row['name'] = row['note']
                                del row['note']
                            if 'cacheStatus' in row:
                                row['_cache_status'] = row['cacheStatus']
                                del row['cacheStatus']

                        self.restore_table(self._Database.Heat, heat_query_data, defaults={
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
                        self.restore_table(self._Database.HeatNode, heatNode_query_data, defaults={
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
                            if 'unlimited_time' in row:
                                raceFormat['unlimited_time'] = raceFormat['race_mode']
                                del raceFormat['race_mode']

                            if 'staging_tones' in row:
                                raceFormat['staging_delay_tones'] = raceFormat['staging_tones']
                                del raceFormat['staging_tones']

                            if 'staging_delay_tones' in raceFormat and raceFormat['staging_delay_tones'] == StagingTones.TONES_ONE:
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

                            elif 'staging_delay_tones' in raceFormat and raceFormat['staging_delay_tones'] == StagingTones.TONES_ALL:
                                raceFormat['staging_delay_tones'] = StagingTones.TONES_ALL

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
                                raceFormat['staging_delay_tones'] = StagingTones.TONES_NONE

                                if 'start_delay_min' in raceFormat and raceFormat['start_delay_min']:
                                    raceFormat['start_delay_min_ms'] = raceFormat['start_delay_min'] * 1000
                                    del raceFormat['start_delay_min']

                                if 'start_delay_max' in raceFormat and raceFormat['start_delay_max']:
                                    raceFormat['start_delay_max_ms'] = (raceFormat['start_delay_max'] * 1000) - raceFormat['start_delay_min_ms']
                                    if raceFormat['start_delay_max_ms'] < 0:
                                        raceFormat['start_delay_max_ms'] = 0
                                    del raceFormat['start_delay_max']

                    self.restore_table(self._Database.RaceFormat, raceFormat_query_data, defaults={
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
                        'team_racing_mode': False,
                        'points_method': None
                    })
                else:
                    self.reset_raceFormats()

                if profiles_query_data:
                    self.restore_table(self._Database.Profiles, profiles_query_data, defaults={
                            'name': self.__("Migrated Profile"),
                            'frequencies': json.dumps(self.default_frequencies()),
                            'enter_ats': json.dumps({'v': [None for _i in range(max(self._racecontext.race.num_nodes,8))]}),
                            'exit_ats': json.dumps({'v': [None for _i in range(max(self._racecontext.race.num_nodes,8))]}),
                            'f_ratio': None
                        })
                else:
                    self.reset_profiles()

                for row in raceClass_query_data:
                    if 'cacheStatus' in row:
                        row['_cache_status'] = row['cacheStatus']
                        del row['cacheStatus']
                    if 'rankStatus' in row:
                        row['_rank_status'] = row['rankStatus']
                        del row['rankStatus']
                    if 'heatAdvanceType' in row:
                        row['heat_advance_type'] = row['heatAdvanceType']
                        del row['heatAdvanceType']

                self.restore_table(self._Database.RaceClass, raceClass_query_data, defaults={
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
                        'order': None,
                    })

                self.reset_options()
                if options_query_data:
                    for opt in options_query_data:
                        if opt['option_name'] in carryoverOpts:
                            self.set_option(opt['option_name'], opt['option_value'])

                logger.info('UI Options restored')

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
                        self.restore_table(self._Database.SavedRaceMeta, raceMeta_query_data, defaults={
                            'results': None,
                            '_cache_status': json.dumps({
                                'data_ver': monotonic(),
                                'build_ver': None
                            })
                        })
                        self.restore_table(self._Database.SavedPilotRace, racePilot_query_data, defaults={
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

                        self.restore_table(self._Database.SavedRaceLap, raceLap_query_data, defaults={
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
            return self._Database.Pilot.query.get(pilot_or_id)

    def resolve_id_from_pilot_or_id(self, pilot_or_id):
        if isinstance(pilot_or_id, Database.Pilot):
            return pilot_or_id.id
        else:
            return pilot_or_id

    def get_pilot(self, pilot_id):
        return self._Database.Pilot.query.get(pilot_id)

    def get_pilots(self):
        return self._Database.Pilot.query.all()

    def get_pilot_for_callsign(self, callsign):
        pilots = self.get_pilots()
        if pilots:
            for pilot in pilots:
                if pilot.callsign == callsign:
                    return pilot
        return None

    def add_pilot(self, init=None):
        color = RHUtils.hslToHex(False, 100, 50)

        new_pilot = self._Database.Pilot(
            name='',
            callsign='',
            team=RHUtils.DEF_TEAM_NAME,
            phonetic='',
            color=color,
            used_frequencies=None)

        self._Database.DB.session.add(new_pilot)
        self._Database.DB.session.flush()

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

        self.commit()

        self._Events.trigger(Evt.PILOT_ADD, {
            'pilot_id': new_pilot.id,
            })

        logger.info('Pilot added: Pilot {0}'.format(new_pilot.id))

        return new_pilot

    def alter_pilot(self, data):
        pilot_id = data['pilot_id']
        pilot = self._Database.Pilot.query.get(pilot_id)
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
            attribute = self._Database.PilotAttribute.query.filter_by(id=pilot_id, name=data['pilot_attr']).one_or_none()
            if attribute:
                attribute.value = data['value']
            else:
                self._Database.DB.session.add(self._Database.PilotAttribute(id=pilot_id, name=data['pilot_attr'], value=data['value']))

        self.commit()

        self._racecontext.race.clear_results()  # refresh current leaderboard

        self._Events.trigger(Evt.PILOT_ALTER, {
            'pilot_id': pilot_id,
            })

        logger.info('Altered pilot {0} to {1}'.format(pilot_id, data))

        race_list = []
        if 'callsign' in data or 'team_name' in data:
            heatnodes = self._Database.HeatNode.query.filter_by(pilot_id=pilot_id).all()
            if heatnodes:
                for heatnode in heatnodes:
                    heat = self.get_heat(heatnode.heat_id)
                    self.clear_results_heat(heat)

                    if heat.class_id != RHUtils.CLASS_ID_NONE:
                        self.clear_results_raceClass(heat.class_id)

                    for race in self._Database.SavedRaceMeta.query.filter_by(heat_id=heatnode.heat_id).all():
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

        if self.savedPilotRaces_has_pilot(pilot.id):
            logger.info('Refusing to delete pilot {0}: is in use'.format(pilot.id))
            return False
        else:
            self._Database.DB.session.delete(pilot)
            for heatNode in self._Database.HeatNode.query.all():
                if heatNode.pilot_id == pilot.id:
                    heatNode.pilot_id = RHUtils.PILOT_ID_NONE
            self.commit()

            logger.info('Pilot {0} deleted'.format(pilot.id))

            self._racecontext.race.clear_results() # refresh leaderboard

            return True

    def get_recent_pilot_node(self, pilot_id):
        return self._Database.HeatNode.query.filter_by(pilot_id=pilot_id).order_by(self._Database.HeatNode.id.desc()).first()

    def clear_pilots(self):
        self._Database.DB.session.query(self._Database.Pilot).delete()
        self.commit()

    def reset_pilots(self):
        self.clear_pilots()
        logger.info('Database pilots reset')
        return True

    #Pilot Attributes
    def get_pilot_attribute(self, pilot_or_id, name):
        pilot_id = self.resolve_id_from_pilot_or_id(pilot_or_id)
        return self._Database.PilotAttribute.query.filter_by(id=pilot_id, name=name).one_or_none()

    def get_pilot_attribute_value(self, pilot_or_id, name, default_value=None):
        attr = self._Database.PilotAttribute.query.filter_by(id=pilot_or_id, name=name).one_or_none()

        if attr is not None:
            return attr.value
        else:
            return default_value

    def get_pilot_attributes(self, pilot_or_id):
        pilot_id = self.resolve_id_from_pilot_or_id(pilot_or_id)
        return self._Database.PilotAttribute.query.filter_by(id=pilot_id).all()

    def get_pilot_id_by_attribute(self, name, value):
        attrs = self._Database.PilotAttribute.query.filter_by(name=name, value=value).all()
        return [attr.id for attr in attrs]

    # Heats
    def resolve_heat_from_heat_or_id(self, heat_or_id):
        if isinstance(heat_or_id, Database.Heat):
            return heat_or_id
        else:
            return self._Database.Heat.query.get(heat_or_id)

    def resolve_id_from_heat_or_id(self, heat_or_id):
        if isinstance(heat_or_id, Database.Heat):
            return heat_or_id.id
        else:
            return heat_or_id

    def get_heat(self, heat_id):
        return self._Database.Heat.query.get(heat_id)

    def get_heats(self):
        return self._Database.Heat.query.all()

    def get_heats_by_class(self, class_id):
        return self._Database.Heat.query.filter_by(class_id=class_id).all()

    def get_first_heat(self):
        return self._Database.Heat.query.first()

    def add_heat(self, init=None, initPilots=None):
        # Add new heat
        new_heat = self._Database.Heat(
            class_id=RHUtils.CLASS_ID_NONE,
            _cache_status=json.dumps({
                'data_ver': monotonic(),
                'build_ver': None
            }),
            order=None,
            status=HeatStatus.PLANNED,
            auto_frequency=False
            )

        if init:
            if 'class_id' in init:
                new_heat.class_id = init['class_id']
            if 'name' in init:
                new_heat.name = init['name']
            if 'auto_frequency' in init:
                new_heat.auto_frequency = init['auto_frequency']

            defaultMethod = init['defaultMethod'] if 'defaultMethod' in init else ProgramMethod.ASSIGN
        else:
            defaultMethod = ProgramMethod.ASSIGN

        self._Database.DB.session.add(new_heat)
        self._Database.DB.session.flush()
        self._Database.DB.session.refresh(new_heat)

        # Add heatnodes
        for node_index in range(self._racecontext.race.num_nodes):
            new_heatNode = self._Database.HeatNode(
                heat_id=new_heat.id,
                node_index=node_index,
                pilot_id=RHUtils.PILOT_ID_NONE,
                method=defaultMethod,
                seed_rank=None,
                seed_id=None
            )

            if initPilots and node_index in initPilots:
                new_heatNode.pilot_id = initPilots[node_index]

            self._Database.DB.session.add(new_heatNode)

        self.commit()

        self._Events.trigger(Evt.HEAT_ADD, {
            'heat_id': new_heat.id,
            })

        logger.info('Heat added: Heat {0}'.format(new_heat.id))

        return new_heat

    def duplicate_heat(self, source_heat_or_id, **kwargs):
        # Add new heat by duplicating an existing one
        source_heat = self.resolve_heat_from_heat_or_id(source_heat_or_id)

        if source_heat.name:
            all_heat_names = [heat.name for heat in self.get_heats()]
            new_heat_name = RHUtils.uniqueName(source_heat.name, all_heat_names)
        else:
            new_heat_name = ''

        if 'dest_class' in kwargs:
            new_class = kwargs['dest_class']
        else:
            new_class = source_heat.class_id

        new_heat = self._Database.Heat(
            name=new_heat_name,
            class_id=new_class,
            results=None,
            _cache_status=json.dumps({
                'data_ver': monotonic(),
                'build_ver': None
            }),
            status=0,
            auto_frequency=source_heat.auto_frequency
            )

        self._Database.DB.session.add(new_heat)
        self._Database.DB.session.flush()
        self._Database.DB.session.refresh(new_heat)

        for source_heatnode in self.get_heatNodes_by_heat(source_heat.id):
            new_heatnode = self._Database.HeatNode(heat_id=new_heat.id,
                node_index=source_heatnode.node_index,
                pilot_id=source_heatnode.pilot_id,
                method=source_heatnode.method,
                seed_rank=source_heatnode.seed_rank,
                seed_id=source_heatnode.seed_id
                )
            self._Database.DB.session.add(new_heatnode)

        self.commit()

        self._Events.trigger(Evt.HEAT_DUPLICATE, {
            'heat_id': new_heat.id,
            })

        logger.info('Heat {0} duplicated to heat {1}'.format(source_heat.id, new_heat.id))

        return new_heat

    def alter_heat(self, data):
        # Alters heat. Returns heat and list of affected races
        heat_id = data['heat']
        heat = self._Database.Heat.query.get(heat_id)

        if 'slot_id' in data:
            slot_id = data['slot_id']
            slot = self._Database.HeatNode.query.get(slot_id)

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

        # alter existing saved races:
        race_list = self._Database.SavedRaceMeta.query.filter_by(heat_id=heat_id).all()

        if 'class' in data:
            if len(race_list):
                for race_meta in race_list:
                    race_meta.class_id = data['class']

                if old_class_id is not RHUtils.CLASS_ID_NONE:
                    self.clear_results_raceClass(old_class_id)

        if 'pilot' in data:
            if len(race_list):
                for race_meta in race_list:
                    for pilot_race in self._Database.SavedPilotRace.query.filter_by(race_id=race_meta.id).all():
                        if pilot_race.node_index == slot.node_index:
                            pilot_race.pilot_id = data['pilot']
                    for race_lap in self._Database.SavedRaceLap.query.filter_by(race_id=race_meta.id):
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

        self.commit()

        self._Events.trigger(Evt.HEAT_ALTER, {
            'heat_id': heat.id,
            })

        # update current race
        if heat_id == self._racecontext.race.current_heat:
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
            heat_count = self._Database.Heat.query.count()
            heatnodes = self._Database.HeatNode.query.filter_by(heat_id=heat.id).order_by(self._Database.HeatNode.node_index).all()

            has_race = self.savedRaceMetas_has_heat(heat.id)

            if has_race or (self._racecontext.race.current_heat == heat.id and self._racecontext.race.race_status != RaceStatus.READY):
                logger.info('Refusing to delete heat {0}: is in use'.format(heat.id))
                return False
            else:
                self._Database.DB.session.delete(heat)
                for heatnode in heatnodes:
                    self._Database.DB.session.delete(heatnode)
                self.commit()

                logger.info('Heat {0} deleted'.format(heat.id))

                self._Events.trigger(Evt.HEAT_DELETE, {
                    'heat_id': heat.id,
                    })

                # if only one heat remaining then set ID to 1
                if heat_count == 2 and self._racecontext.race.race_status == RaceStatus.READY:
                    try:
                        heat = self._Database.Heat.query.first()
                        if heat.id != 1:
                            heatnodes = self._Database.HeatNode.query.filter_by(heat_id=heat.id).order_by(self._Database.HeatNode.node_index).all()

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
                if heat.id == sav_heat_id:
                    return sav_heat_id

        # find and return ID of first "safe" heat
        cur_heat_id = RHUtils.HEAT_ID_NONE
        for heat in heats:
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

    def get_next_heat_id(self, current_heat_or_id):
        current_heat = self.resolve_heat_from_heat_or_id(current_heat_or_id)
        if current_heat.class_id:
            current_class = self.get_raceClass(current_heat.class_id)
            heats = self.get_heats_by_class(current_heat.class_id)

            if current_class.heat_advance_type == HeatAdvanceType.NONE:
                return current_heat.id

            if current_class.heat_advance_type == HeatAdvanceType.NEXT_ROUND:
                max_round = self.get_max_round(current_heat.id)
                if max_round < current_class.rounds:
                    return current_heat.id

            def orderSorter(x):
                if not x.order:
                    return 0
                return x.order
            heats.sort(key=orderSorter)

            if len(heats):
                next_heat_id = None
                if heats[-1].id == current_heat.id:
                    next_heat_id = heats[0].id
                    if current_class.rounds:
                        max_round = self.get_max_round(current_heat.id)
                        if max_round >= current_class.rounds:
                            self._Events.trigger(Evt.ROUNDS_COMPLETE, {'class_id': current_class.id})

                            race_classes = self.get_raceClasses()
                            race_classes.sort(key=orderSorter)
                            if race_classes[-1].id == current_heat.class_id:
                                next_class_id = RHUtils.HEAT_ID_NONE
                                logger.debug('Completed last heat of last class, shifting to practice mode')
                            else:
                                for idx, race_class in enumerate(race_classes):
                                    if race_class.id == current_heat.class_id:
                                        next_class_id = race_classes[idx + 1].id
                                        break

                            if next_class_id:
                                next_heats = self.get_heats_by_class(next_class_id)
                                next_heat_id = next_heats[0].id
                            else:
                                next_heat_id = RHUtils.HEAT_ID_NONE
                                logger.debug('No next class, shifting to practice mode')

                else:
                    for idx, heat in enumerate(heats):
                        if heat.id == current_heat.id:
                            next_heat_id = heats[idx + 1].id
                            break

            return next_heat_id

        return current_heat.id

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

        if heat is False:
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
        build = Results.calc_leaderboard(self, heat_id=heat.id)

        self.set_results_heat(heat, token, build)
        return build

    def set_results_heat(self, heat_or_id, token, results):
        heat = self.resolve_heat_from_heat_or_id(heat_or_id)

        if heat is False:
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

        if heat is False:
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

        self._Database.Heat.query.update({
            self._Database.Heat._cache_status: initStatus
            })
        self.commit()

    def clear_heats(self):
        self._Database.DB.session.query(self._Database.Heat).delete()
        self._Database.DB.session.query(self._Database.HeatNode).delete()
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

    # HeatNodes
    #def resolve_heatNode_from_heatNode_or_id(self, heatNode_or_id):
    #    if isinstance(heatNode_or_id, Database.HeatNode):
    #        return heatNode_or_id
    #    else:
    #        return self._Database.HeatNode.query.get(heatNode_or_id)

    #def resolve_id_from_heatNode_or_id(self, heatNode_or_id):
    #    if isinstance(heatNode_or_id, Database.HeatNode):
    #        return heatNode_or_id.id
    #    else:
    #        return heatNode_or_id

    def get_heatNode(self, heatNode_id):
        return self._Database.HeatNode.query.get(heatNode_id)

    def get_heatNodes(self):
        return self._Database.HeatNode.query.all()

    def get_heatNodes_by_heat(self, heat_id):
        return self._Database.HeatNode.query.filter_by(heat_id=heat_id).order_by(self._Database.HeatNode.node_index).all()

    def add_heatNode(self, heat_id, node_index):
        new_heatNode = self._Database.HeatNode(
            heat_id=heat_id,
            node_index=node_index,
            pilot_id=RHUtils.PILOT_ID_NONE,
            method=0,
            )

        self._Database.DB.session.add(new_heatNode)
        self.commit()
        return True

    def get_pilot_from_heatNode(self, heat_id, node_index):
        heatNode = self._Database.HeatNode.query.filter_by(heat_id=heat_id, node_index=node_index).one_or_none()
        if heatNode:
            return heatNode.pilot_id
        else:
            return None

    def alter_heatNodes_fast(self, slot_list):
        # Alters heatNodes quickly, in batch
        # !! Unsafe for general use. Intentionally light type checking,    !!
        # !! DOES NOT trigger events, clear results, or update cached data !!

        for slot_data in slot_list:
            slot_id = slot_data['slot_id']
            slot = self._Database.HeatNode.query.get(slot_id)

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

    # Race Classes
    def resolve_raceClass_from_raceClass_or_id(self, raceClass_or_id):
        if isinstance(raceClass_or_id, Database.RaceClass):
            return raceClass_or_id
        else:
            return self._Database.RaceClass.query.get(raceClass_or_id)

    def resolve_id_from_raceClass_or_id(self, raceClass_or_id):
        if isinstance(raceClass_or_id, Database.RaceClass):
            return raceClass_or_id.id
        else:
            return raceClass_or_id
    
    def get_raceClass(self, raceClass_id):
        return self._Database.RaceClass.query.get(raceClass_id)

    def get_raceClasses(self):
        return self._Database.RaceClass.query.all()

    def add_raceClass(self, init=None):
        # Add new race class
        initStatus = json.dumps({
            'data_ver': monotonic(),
            'build_ver': None
        })

        new_race_class = self._Database.RaceClass(
            name='',
            description='',
            format_id=RHUtils.FORMAT_ID_NONE,
            _cache_status=initStatus,
            _rank_status=initStatus,
            win_condition="",
            rank_settings=None,
            rounds=0,
            heat_advance_type=HeatAdvanceType.NEXT_HEAT,
            order=None
            )
        self._Database.DB.session.add(new_race_class)
        self._Database.DB.session.flush()

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
            if 'order' in init:
                new_race_class.order = init['order']

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

        new_class = self._Database.RaceClass(
            name=new_class_name,
            description=source_class.description,
            format_id=source_class.format_id,
            results=None,
            _cache_status=initStatus,
            _rank_status=initStatus,
            win_condition=source_class.win_condition,
            rounds=source_class.rounds,
            heat_advance_type=source_class.heat_advance_type,
            order=None
            )

        self._Database.DB.session.add(new_class)
        self._Database.DB.session.flush()
        self._Database.DB.session.refresh(new_class)

        for heat in self._Database.Heat.query.filter_by(class_id=source_class.id).all():
            self.duplicate_heat(heat, dest_class=new_class.id)

        self.commit()

        self._Events.trigger(Evt.CLASS_DUPLICATE, {
            'class_id': new_class.id,
            })

        logger.info('Class {0} duplicated to class {1}'.format(source_class.id, new_class.id))

        return new_class

    def alter_raceClass(self, data):
        # alter existing classes
        race_class_id = data['class_id']
        race_class = self._Database.RaceClass.query.get(race_class_id)

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
        if 'order' in data:
            race_class.order = data['order']

        race_list = self._Database.SavedRaceMeta.query.filter_by(class_id=race_class_id).all()

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

                    heats = self._Database.Heat.query.filter_by(class_id=race_class_id).all()
                    for heat in heats:
                        self.clear_results_heat(heat)

        self.commit()

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
            self._Database.DB.session.delete(race_class)
            for heat in self._Database.Heat.query.all():
                if heat.class_id == race_class.id:
                    heat.class_id = RHUtils.CLASS_ID_NONE

            self.commit()

            self._Events.trigger(Evt.CLASS_DELETE, {
                'class_id': race_class.id,
                })

            logger.info('Class {0} deleted'.format(race_class.id))

            return True

    def get_results_raceClass(self, raceClass_or_id):
        race_class = self.resolve_raceClass_from_raceClass_or_id(raceClass_or_id)

        if race_class is False:
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
        logger.info('Building Class {} results'.format(race_class.id))
        build = Results.calc_leaderboard(self, class_id=race_class.id)
        self.set_results_raceClass(race_class, token, build)
        return build

    def get_ranking_raceClass(self, raceClass_or_id):
        race_class = self.resolve_raceClass_from_raceClass_or_id(raceClass_or_id)

        if race_class is False:
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
            self.clear_ranking_raceClass(race_class, token)

        # cache rebuild
        logger.debug('Building Class {} ranking'.format(race_class.id))
        build = Results.calc_class_ranking_leaderboard(self._racecontext, class_id=race_class.id)
        self.set_ranking_raceClass(race_class, token, build)
        return build

    def set_results_raceClass(self, raceClass_or_id, token, results):
        race_class = self.resolve_raceClass_from_raceClass_or_id(raceClass_or_id)

        if race_class is False:
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

        if race_class is False:
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

        if race_class is False:
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

        self._Database.RaceClass.query.update({
            self._Database.RaceClass._cache_status: jsonStatus,
            self._Database.RaceClass._rank_status: jsonStatus
            })
        self.commit()

    def clear_raceClasses(self):
        self._Database.DB.session.query(self._Database.RaceClass).delete()
        self.commit()
        return True

    def reset_raceClasses(self):
        self.clear_raceClasses()
        logger.info('Database race classes reset')
        return True

    # Profiles
    def resolve_profile_from_profile_or_id(self, profile_or_id):
        if isinstance(profile_or_id, Database.Profiles):
            return profile_or_id
        else:
            return self._Database.Profiles.query.get(profile_or_id)

    def resolve_id_from_profile_or_id(self, profile_or_id):
        if isinstance(profile_or_id, Database.Profiles):
            return profile_or_id.id
        else:
            return profile_or_id

    def get_profile(self, profile_id):
        return self._Database.Profiles.query.get(profile_id)

    def get_profiles(self):
        return self._Database.Profiles.query.all()

    def get_first_profile(self):
        return self._Database.Profiles.query.first()

    def add_profile(self, init=None):
        new_profile = self._Database.Profiles(
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

        self._Database.DB.session.add(new_profile)
        self.commit()

        return new_profile

    def duplicate_profile(self, source_profile_or_id):
        source_profile = self.resolve_profile_from_profile_or_id(source_profile_or_id)

        all_profile_names = [profile.name for profile in self.get_profiles()]

        if source_profile.name:
            new_profile_name = RHUtils.uniqueName(source_profile.name, all_profile_names)
        else:
            new_profile_name = RHUtils.uniqueName(self._racecontext.language.__('New Profile'), all_profile_names)

        new_profile = self._Database.Profiles(
            name=new_profile_name,
            description = '',
            frequencies = source_profile.frequencies,
            enter_ats = source_profile.enter_ats,
            exit_ats = source_profile.exit_ats,
            f_ratio = 100)
        self._Database.DB.session.add(new_profile)
        self.commit()

        self._Events.trigger(Evt.PROFILE_ADD, {
            'profile_id': new_profile.id,
            })

        return new_profile

    def alter_profile(self, data):
        profile = self._Database.Profiles.query.get(data['profile_id'])

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
            self._Database.DB.session.delete(profile)
            self.commit()

            self._Events.trigger(Evt.PROFILE_DELETE, {
                'profile_id': profile.id,
                })

            return True
        else:
            logger.info('Refusing to delete only profile')
            return False

    def clear_profiles(self):
        self._Database.DB.session.query(self._Database.Profiles).delete()
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
            return self._Database.RaceFormat.query.get(raceFormat_or_id)

    def resolve_id_from_raceFormat_or_id(self, raceFormat_or_id):
        if isinstance(raceFormat_or_id, Database.RaceFormat):
            return raceFormat_or_id.id
        else:
            return raceFormat_or_id

    def get_raceFormat(self, raceFormat_id):
        return self._Database.RaceFormat.query.get(raceFormat_id)

    def get_raceFormats(self):
        return self._Database.RaceFormat.query.all()

    def get_first_raceFormat(self):
        return self._Database.RaceFormat.query.first()

    def add_format(self, init=None):
        race_format = self._Database.RaceFormat(
            name='',
            unlimited_time=0,
            race_time_sec=0,
            lap_grace_sec=-1,
            staging_fixed_tones=0,
            staging_delay_tones=0,
            start_delay_min_ms=1000,
            start_delay_max_ms=1000,
            number_laps_win=0,
            win_condition=0,
            team_racing_mode=False,
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
                race_format.team_racing_mode = (True if init['team_racing_mode'] else False)
            if 'points_method' in init:
                race_format.points_method = init['points_method']

        self._Database.DB.session.add(race_format)
        self.commit()

        return race_format

    def duplicate_raceFormat(self, source_format_or_id):
        source_format = self.resolve_raceFormat_from_raceFormat_or_id(source_format_or_id)

        all_format_names = [raceformat.name for raceformat in self.get_raceFormats()]

        if source_format.name:
            new_format_name = RHUtils.uniqueName(source_format.name, all_format_names)
        else:
            new_format_name = RHUtils.uniqueName(self._racecontext.language.__('New Format'), all_format_names)

        new_format = self._Database.RaceFormat(
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
        self._Database.DB.session.add(new_format)
        self.commit()

        self._Events.trigger(Evt.RACE_FORMAT_ADD, {
            'format_id': new_format.id,
            })

        return new_format

    def alter_raceFormat(self, data):
        race_format = self._Database.RaceFormat.query.get(data['format_id'])

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
            race_format.team_racing_mode = True if data['team_racing_mode'] else False
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

        self.commit()

        self._racecontext.race.clear_results() # refresh leaderboard

        race_list = []

        if 'win_condition' in data or 'start_behavior' in data or 'points_method' in data or 'points_settings' in data:
            race_list = self._Database.SavedRaceMeta.query.filter_by(format_id=race_format.id).all()

            if len(race_list):
                self._racecontext.pagecache.set_valid(False)
                self.clear_results_event()

                for race in race_list:
                    self.clear_results_savedRaceMeta(race)

                classes = self._Database.RaceClass.query.filter_by(format_id=race_format.id).all()

                for race_class in classes:
                    self.clear_results_raceClass(race_class)

                    heats = self._Database.Heat.query.filter_by(class_id=race_class.id).all()

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

        race_format = self._Database.RaceFormat.query.get(format_id)
        if race_format and len(self.get_raceFormats()) > 1: # keep one format
            self._Database.DB.session.delete(race_format)
            self.commit()

            self._Events.trigger(Evt.RACE_FORMAT_DELETE, {
                'race_format': format_id,
                })

            return True
        else:
            logger.info('Refusing to delete only format')
            return False

    def clear_raceFormats(self):
        self._Database.DB.session.query(self._Database.RaceFormat).delete()
        for race_class in self.get_raceClasses():
            self.alter_raceClass({
                'class_id': race_class.id,
                'class_format': RHUtils.FORMAT_ID_NONE
                })

        self.commit()
        return True

    def reset_raceFormats(self):
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
            'team_racing_mode': False,
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
            'team_racing_mode': False,
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
            'team_racing_mode': False,
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
            'team_racing_mode': False,
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
            'team_racing_mode': False,
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
            'team_racing_mode': False,
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
            'team_racing_mode': False,
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
            'team_racing_mode': False,
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
            'team_racing_mode': True,
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
            'team_racing_mode': True,
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
            'team_racing_mode': True,
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
            'team_racing_mode': True,
            'start_behavior': 0,
            'points_method': None
            })

        self.commit()
        logger.info("Database reset race formats")
        return True

    # Race Meta
    def resolve_savedRaceMeta_from_savedRaceMeta_or_id(self, savedRaceMeta_or_id):
        if isinstance(savedRaceMeta_or_id, Database.SavedRaceMeta):
            return savedRaceMeta_or_id
        else:
            return self._Database.SavedRaceMeta.query.get(savedRaceMeta_or_id)

    def resolve_id_from_savedRaceMeta_or_id(self, savedRaceMeta_or_id):
        if isinstance(savedRaceMeta_or_id, Database.SavedRaceMeta):
            return savedRaceMeta_or_id.id
        else:
            return savedRaceMeta_or_id

    def get_savedRaceMeta(self, raceMeta_id):
        return self._Database.SavedRaceMeta.query.get(raceMeta_id)

    def get_savedRaceMeta_by_heat_round(self, heat_id, round_id):
        return self._Database.SavedRaceMeta.query.filter_by(heat_id=heat_id, round_id=round_id).one()

    def get_savedRaceMetas(self):
        return self._Database.SavedRaceMeta.query.all()

    def get_savedRaceMetas_by_heat(self, heat_id):
        return self._Database.SavedRaceMeta.query.filter_by(heat_id=heat_id).order_by(self._Database.SavedRaceMeta.round_id).all()

    def get_savedRaceMetas_by_raceClass(self, class_id):
        return self._Database.SavedRaceMeta.query.filter_by(class_id=class_id).order_by(self._Database.SavedRaceMeta.round_id).all()

    def savedRaceMetas_has_raceFormat(self, race_format_id):
        return bool(self._Database.SavedRaceMeta.query.filter_by(format_id=race_format_id).count())

    def savedRaceMetas_has_heat(self, heat_id):
        return bool(self._Database.SavedRaceMeta.query.filter_by(heat_id=heat_id).count())

    def savedRaceMetas_has_raceClass(self, class_id):
        return bool(self._Database.SavedRaceMeta.query.filter_by(class_id=class_id).count())

    def add_savedRaceMeta(self, data):
        new_race = self._Database.SavedRaceMeta(
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
        self._Database.DB.session.add(new_race)
        self.commit()

        logger.info('Race added: Race {0}'.format(new_race.id))

        return new_race

    def reassign_savedRaceMeta_heat(self, savedRaceMeta_or_id, new_heat_id):
        race_meta = self.resolve_savedRaceMeta_from_savedRaceMeta_or_id(savedRaceMeta_or_id)

        old_heat_id = race_meta.heat_id
        old_heat = self.get_heat(old_heat_id)
        old_class = self.get_raceClass(old_heat.class_id)
        old_format_id = old_class.format_id

        new_heat = self.get_heat(new_heat_id)
        new_class = self.get_raceClass(new_heat.class_id)
        new_format_id = new_class.format_id

        # clear round ids
        heat_races = self._Database.SavedRaceMeta.query.filter_by(heat_id=new_heat_id).order_by(self._Database.SavedRaceMeta.round_id).all()
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
        self._Database.DB.session.flush()
        old_heat_races = self._Database.SavedRaceMeta.query.filter_by(heat_id=old_heat_id) \
            .order_by(self._Database.SavedRaceMeta.start_time_formatted).all()
        round_counter = 1
        for race in old_heat_races:
            race.round_id = round_counter
            round_counter += 1

        new_heat_races = self._Database.SavedRaceMeta.query.filter_by(heat_id=new_heat_id) \
            .order_by(self._Database.SavedRaceMeta.start_time_formatted).all()
        round_counter = 1
        for race in new_heat_races:
            race.round_id = round_counter
            round_counter += 1

        self.commit()

        # cache cleaning
        self._racecontext.pagecache.set_valid(False)

        self.clear_results_heat(new_heat)
        self.clear_results_heat(old_heat)

        if old_format_id != new_format_id:
            self.clear_results_savedRaceMeta(race_meta)

        if old_heat.class_id != new_heat.class_id:
            self.clear_results_raceClass(new_class)
            self.clear_results_raceClass(old_class)

        self.commit()

        self._Events.trigger(Evt.RACE_ALTER, {
            'race_id': race_meta.id,
            })

        logger.info('Race {0} reassigned to heat {1}'.format(race_meta.id, new_heat_id))

        return race_meta, new_heat

    def get_results_savedRaceMeta(self, savedRaceMeta_or_id):
        race = self.resolve_savedRaceMeta_from_savedRaceMeta_or_id(savedRaceMeta_or_id)

        if race is False:
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

        # cache rebuild
        logger.debug('Building Race {} (Heat {} Round {}) results'.format(race.id, race.heat_id, race.round_id))
        build = Results.calc_leaderboard(self, heat_id=race.heat_id, round_id=race.round_id)

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

        if race is False:
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

        if race is False:
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

        self._Database.SavedRaceMeta.query.update({
            self._Database.SavedRaceMeta._cache_status: initStatus
            })
        self.commit()

    def get_max_round(self, heat_id):
        return int(self._Database.DB.session.query(
            self._Database.DB.func.max(
                self._Database.SavedRaceMeta.round_id
            )).filter_by(heat_id=heat_id).scalar() or 0)

    # Pilot-Races
    def get_savedPilotRace(self, pilotrace_id):
        return self._Database.SavedPilotRace.query.get(pilotrace_id)

    def get_savedPilotRaces(self):
        return self._Database.SavedPilotRace.query.all()

    def get_savedPilotRaces_by_savedRaceMeta(self, race_id):
        return self._Database.SavedPilotRace.query.filter_by(race_id=race_id).all()

    def alter_savedPilotRace(self, data):
        pilotrace = self._Database.SavedPilotRace.query.get(data['pilotrace_id'])

        if 'enter_at' in data:
            pilotrace.enter_at = data['enter_at']
        if 'exit_at' in data:
            pilotrace.exit_at = data['exit_at']

        self.commit()

        return True

    def savedPilotRaces_has_pilot(self, pilot_id):
        return bool(self._Database.SavedPilotRace.query.filter_by(pilot_id=pilot_id).count())

    # Race Laps
    def get_savedRaceLaps(self):
        return self._Database.SavedRaceLap.query.all()

    def get_savedRaceLaps_by_savedPilotRace(self, pilotrace_id):
        return self._Database.SavedRaceLap.query.filter_by(pilotrace_id=pilotrace_id).order_by(self._Database.SavedRaceLap.lap_time_stamp).all()

    def get_active_savedRaceLaps(self):
        return self._Database.SavedRaceLap.query.filter(self._Database.SavedRaceLap.deleted != 1).all()

    # Race general
    def replace_savedRaceLaps(self, data):
        self._Database.SavedRaceLap.query.filter_by(pilotrace_id=data['pilotrace_id']).delete()

        for lap in data['laps']:
            self._Database.DB.session.add(self._Database.SavedRaceLap(
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
            new_pilotrace = self._Database.SavedPilotRace(
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

            self._Database.DB.session.add(new_pilotrace)
            self._Database.DB.session.flush()
            self._Database.DB.session.refresh(new_pilotrace)

            for lap in node_data['laps']:
                self._Database.DB.session.add(self._Database.SavedRaceLap(
                    race_id=node_data['race_id'],
                    pilotrace_id=new_pilotrace.id,
                    node_index=node_index,
                    pilot_id=node_data['pilot_id'],
                    lap_time_stamp=lap['lap_time_stamp'],
                    lap_time=lap['lap_time'],
                    lap_time_formatted=lap['lap_time_formatted'],
                    source=lap['source'],
                    deleted=lap['deleted']
                ))

        self.commit()
        return True

    def clear_race_data(self):
        self._Database.DB.session.query(self._Database.SavedRaceMeta).delete()
        self._Database.DB.session.query(self._Database.SavedPilotRace).delete()
        self._Database.DB.session.query(self._Database.SavedRaceLap).delete()
        self._Database.DB.session.query(self._Database.LapSplit).delete()
        self.commit()
        self.reset_pilot_used_frequencies()
        self.reset_heat_plans()
        logger.info('Database saved races reset')
        return True

    # Splits
    def get_lapSplits(self):
        return self._Database.LapSplit.query.all()

    def get_lapSplits_by_lap(self, node_index, lap_id):
        return self._Database.LapSplit.query.filter_by(
            node_index=node_index,
            lap_id=lap_id
            ).all()

    def get_lapSplit_by_params(self, node_index, lap_id, split_id):
        return self._Database.LapSplit.query.filter_by(
            node_index=node_index,
            lap_id=lap_id,
            split_id=split_id
            ).one_or_none()

    def add_lapSplit(self, init=None):
        lap_split = self._Database.LapSplit(
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

        self._Database.DB.session.add(lap_split)
        self.commit()

    def clear_lapSplit(self, lapSplit):
        self._Database.DB.session.delete(lapSplit)
        self.commit()
        return True

    def clear_lapSplits(self):
        self._Database.DB.session.query(self._Database.LapSplit).delete()
        self.commit()
        return True

    # Options
    def get_options(self):
        return self._Database.GlobalSettings.query.all()

    def get_option(self, option, default_value=None):
        try:
            val = self._OptionsCache[option]
            if val or val == "":
                return val
            else:
                return default_value
        except:
            return default_value

    def set_option(self, option, value):
        if isinstance(value, bool):
            value = '1' if value else '0'

        self._OptionsCache[option] = str(value)

        settings = self._Database.GlobalSettings.query.filter_by(option_name=option).one_or_none()
        if settings:
            settings.option_value = value
        else:
            self._Database.DB.session.add(self._Database.GlobalSettings(option_name=option, option_value=value))
        self.commit()

    def get_optionInt(self, option, default_value=0):
        try:
            val = self._OptionsCache[option]
            if val:
                return int(val)
            else:
                return default_value
        except:
            return default_value

    def clear_options(self):
        self._Database.DB.session.query(self._Database.GlobalSettings).delete()
        self.commit()
        return True

    def reset_options(self):
        self.clear_options()
        self.set_option("server_api", self._SERVER_API)
        # group identifiers
        self.set_option("timerName", self.__("RotorHazard"))
        self.set_option("timerLogo", "")
        # group colors
        self.set_option("hue_0", "212")
        self.set_option("sat_0", "55")
        self.set_option("lum_0_low", "29.2")
        self.set_option("lum_0_high", "46.7")
        self.set_option("contrast_0_low", "#ffffff")
        self.set_option("contrast_0_high", "#ffffff")

        self.set_option("hue_1", "25")
        self.set_option("sat_1", "85.3")
        self.set_option("lum_1_low", "37.6")
        self.set_option("lum_1_high", "54.5")
        self.set_option("contrast_1_low", "#ffffff")
        self.set_option("contrast_1_high", "#000000")
        # timer state
        self.set_option("currentLanguage", "")
        self.set_option("timeFormat", "{m}:{s}.{d}")
        self.set_option("timeFormatPhonetic", "{m} {s}.{d}")
        self.set_option("currentProfile", "1")
        self.set_option("calibrationMode", "1")
        # minimum lap
        self.set_option("MinLapSec", "10")
        self.set_option("MinLapBehavior", "0")
        # event information
        self.set_option("eventName", self.__("FPV Race"))
        self.set_option("eventDescription", "")
        # LED settings
        self.set_option("ledBrightness", "32")
        # Event results cache
        self.set_option("eventResults_cacheStatus", None)

        self.set_option("startThreshLowerAmount", "0")
        self.set_option("startThreshLowerDuration", "0")
        self.set_option("nextHeatBehavior", "0")
        self.set_option("currentFormat", "1")
        self.set_option("currentHeat", "0")

        logger.info("Reset global settings")

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
        build = Results.calc_leaderboard(self)
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
