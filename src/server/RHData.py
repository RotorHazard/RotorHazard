#
# RaceData
# Provides abstraction for database and results page caches
#

import logging
logger = logging.getLogger(__name__)

from sqlalchemy import create_engine, MetaData, Table
from datetime import datetime
import os
import traceback
import shutil
import json
from . import RHUtils
from .eventmanager import Evt
from .RHRace import RaceStatus, WinCondition, StagingTones
from .Results import CacheStatus

class RHData():
    _OptionsCache = {} # Local Python cache for global settings

    def __init__(self, Database, Events, RACE, SERVER_API, DB_FILE_NAME, DB_BKP_DIR_NAME):
        self._Database = Database
        self._Events = Events
        self._RACE = RACE
        self._SERVER_API = SERVER_API
        self._DB_FILE_NAME = DB_FILE_NAME
        self._DB_BKP_DIR_NAME = DB_BKP_DIR_NAME
        self._PageCache = None
        self._Language = None

    def late_init(self, PageCache, Language):
        self._PageCache = PageCache
        self._Language = Language

    def __(self, *args, **kwargs):
        return self._Language.__(*args, **kwargs)

    # Integrity Checking
    def check_integrity(self):
        if self.get_optionInt('server_api') < self._SERVER_API:
            logger.info('Old server API version; recovering database')
            return False
        if not self._Database.Heat.query.count():
            logger.info('Heats are empty; recovering database')
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

        return True

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

    def reset_all(self, nofill=False):
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

    def commit(self):
        try:
            self._Database.DB.session.commit()
            return True
        except Exception as ex:
            logger.error('Error writing to database: ' + str(ex))
            return False

    def close(self):
        try:
            self._Database.DB.session.close()
            return True
        except Exception as ex:
            logger.error('Error closing to database: ' + str(ex))
            return False

    # File Handling

    def backup_db_file(self, copy_flag):
        self.close()
        try:     # generate timestamp from last-modified time of database file
            time_str = datetime.fromtimestamp(os.stat(self._DB_FILE_NAME).st_mtime).strftime('%Y%m%d_%H%M%S')
        except:  # if error then use 'now' timestamp
            time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        try:
            (dbname, dbext) = os.path.splitext(self._DB_FILE_NAME)
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
            try:
                for row_data in table_query_data:
                    if (class_type is not self._Database.Pilot) or getattr(row_data, 'callsign', '') != '-' or \
                                                  getattr(row_data, 'name', '') != '-None-':
                        if 'id' in class_type.__table__.columns.keys() and \
                            'id' in row_data.keys():
                            db_update = class_type.query.filter(getattr(class_type,'id')==row_data['id']).first()
                        else:
                            db_update = None

                        if db_update is None:
                            new_data = class_type()
                            for col in class_type.__table__.columns:
                                colName = col.name
                                if colName in row_data.keys():
                                    setattr(new_data, colName, row_data[colName])
                                elif colName in kwargs['defaults']:
                                    setattr(new_data, colName, kwargs['defaults'][colName])

                            #logger.info('DEBUG row_data add:  ' + str(getattr(new_data, match_name)))
                            self._Database.DB.session.add(new_data)
                        else:
                            #logger.info('DEBUG row_data update:  ' + str(getattr(row_data, match_name)))
                            for col in class_type.__table__.columns:
                                colName = col.name
                                if colName in row_data.keys():
                                    setattr(db_update, colName, row_data[colName])
                                elif colName in kwargs['defaults']:
                                    if colName != 'id':
                                        setattr(db_update, colName, kwargs['defaults'][colName])

                        self._Database.DB.session.flush()
                logger.info('Database table "{0}" restored'.format(class_type.__name__))
            except Exception as ex:
                logger.warning('Error restoring "{0}" table from previous database: {1}'.format(class_type.__name__, ex))
                logger.debug(traceback.format_exc())
        else:
            logger.debug('Error restoring "{0}" table: no data'.format(class_type.__name__))

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
                "calibrationMode",
                "MinLapSec",
                "MinLapBehavior",
                "ledEffects",
                "ledBrightness",
                "ledColorNodes",
                "ledColorFreqs",
                "osd_lapHeader",
                "osd_positionHeader",
                "startThreshLowerAmount",
                "startThreshLowerDuration",
                "nextHeatBehavior"
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
                        freqs["b"] = [None for _i in range(self._RACE.num_nodes)]
                        freqs["c"] = [None for _i in range(self._RACE.num_nodes)]
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
                            'color': None
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
                                        new_row['note'] = row['note']
                                    if 'class_id' in row:
                                        new_row['class_id'] = row['class_id']
                                    heat_extracted_meta.append(new_row)

                        self.restore_table(self._Database.Heat, heat_extracted_meta, defaults={
                                'note': None,
                                'class_id': RHUtils.CLASS_ID_NONE,
                                'results': None,
                                'cacheStatus': CacheStatus.INVALID
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
                        self.restore_table(self._Database.Heat, heat_query_data, defaults={
                                'class_id': RHUtils.CLASS_ID_NONE,
                                'results': None,
                                'cacheStatus': CacheStatus.INVALID
                            })
                        self.restore_table(self._Database.HeatNode, heatNode_query_data, defaults={
                                'pilot_id': RHUtils.PILOT_ID_NONE,
                                'color': None
                            })

                        self._RACE.current_heat = self.get_first_heat().id
                    else:
                        self.reset_heats()

                if raceFormat_query_data:
                    self.restore_table(self._Database.RaceFormat, raceFormat_query_data, defaults={
                        'name': self.__("Migrated Format"),
                        'race_mode': 0,
                        'race_time_sec': 120,
                        'start_delay_min': 2,
                        'start_delay_max': 5,
                        'staging_tones': StagingTones.TONES_ALL,
                        'number_laps_win': 0,
                        'win_condition': WinCondition.MOST_LAPS,
                        'team_racing_mode': False,
                        'start_behavior': 0
                    })
                else:
                    self.reset_raceFormats()

                if profiles_query_data:
                    self.restore_table(self._Database.Profiles, profiles_query_data, defaults={
                            'name': self.__("Migrated Profile"),
                            'frequencies': json.dumps(self.default_frequencies()),
                            'enter_ats': json.dumps({'v': [None for _i in range(self._RACE.num_nodes)]}),
                            'exit_ats': json.dumps({'v': [None for _i in range(self._RACE.num_nodes)]}),
                            'f_ratio': None
                        })
                else:
                    self.reset_profiles()

                self.restore_table(self._Database.RaceClass, raceClass_query_data, defaults={
                        'name': 'New class',
                        'format_id': 0,
                        'results': None,
                        'cacheStatus': CacheStatus.INVALID
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
                self.reset_all()
                self.commit()
                self.primeCache() # refresh Options cache
                self._Events.trigger(Evt.DATABASE_RECOVER)
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
                            'cacheStatus': CacheStatus.INVALID
                        })
                        self.restore_table(self._Database.SavedPilotRace, racePilot_query_data, defaults={
                            'history_values': None,
                            'history_times': None,
                            'penalty_time': None,
                            'penalty_desc': None,
                            'enter_at': None,
                            'exit_at': None
                        })
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
        if self._RACE.num_nodes < 5:
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

        while self._RACE.num_nodes > len(freqs['f']):
            freqs['b'].append(None)
            freqs['c'].append(None)
            freqs['f'].append(RHUtils.FREQUENCY_ID_NONE)

        return freqs

    # Pilots
    def get_pilot(self, pilot_id):
        return self._Database.Pilot.query.get(pilot_id)

    def get_pilots(self):
        return self._Database.Pilot.query.all()

    def add_pilot(self, init={}):
        default_color = RHUtils.hslToHex(False, 100, 50)

        new_pilot = self._Database.Pilot(
            name=init['name'] if 'name' in init else '',
            callsign=init['callsign'] if 'callsign' in init else '',
            team=init['team'] if 'team' in init else RHUtils.DEF_TEAM_NAME,
            phonetic=init['phonetic'] if 'phonetic' in init else '',
            color=init['color'] if init and 'color' in init else default_color,
            url=init['url'] if init and 'url' in init else None)

        self._Database.DB.session.add(new_pilot)
        self._Database.DB.session.flush()

        if not new_pilot.name:
            new_pilot.name=self.__('~Pilot %d Name') % (new_pilot.id)
        if not new_pilot.callsign:
            new_pilot.callsign=self.__('~Callsign %d') % (new_pilot.id)

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
        if 'url' in data:
            pilot.url = data['url']

        self.commit()

        self._RACE.cacheStatus = CacheStatus.INVALID  # refresh current leaderboard

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
                    self.clear_results_heat(heat.id)

                    if heat.class_id != RHUtils.CLASS_ID_NONE:
                        self.clear_results_raceClass(heat.class_id)

                    for race in self._Database.SavedRaceMeta.query.filter_by(heat_id=heatnode.heat_id).all():
                        race_list.append(race)

            if len(race_list):
                self._PageCache.set_valid(False)
                self.clear_results_event()

                for race in race_list:
                    self.clear_results_savedRaceMeta(race.id)

                self.commit()

        return pilot, race_list

    def delete_pilot(self, pilot_id):
        pilot = self._Database.Pilot.query.get(pilot_id)

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

            self._RACE.cacheStatus = CacheStatus.INVALID  # refresh leaderboard

            return True

    def get_recent_pilot_node(self, pilot_id):
        return self._Database.HeatNode.query.filter_by(pilot_id=pilot_id).order_by(self._Database.HeatNode.id.desc()).first()

    def clear_pilots(self):
        self._Database.DB.session.query(self._Database.Pilot).delete()
        self.commit()
        return True

    def reset_pilots(self):
        self.clear_pilots()
        for node in range(self._RACE.num_nodes):
            self.add_pilot({
                'callsign': 'Callsign {0}'.format(node+1),
                'name': 'Pilot {0} Name'.format(node+1)
                })
        logger.info('Database pilots reset')
        return True

    # Heats
    def get_heat(self, heat_id):
        return self._Database.Heat.query.get(heat_id)

    def get_heats(self):
        return self._Database.Heat.query.all()

    def get_heats_by_class(self, class_id):
        return self._Database.Heat.query.filter_by(class_id=class_id).all()

    def get_first_heat(self):
        return self._Database.Heat.query.first()

    def add_heat(self, init={}, initPilots={}):
        # Add new heat
        new_heat = self._Database.Heat(
            class_id=RHUtils.CLASS_ID_NONE,
            cacheStatus=CacheStatus.INVALID
            )

        if 'class_id' in init:
            new_heat.class_id = init['class_id']
        if 'note' in init:
            new_heat.note = init['note']

        self._Database.DB.session.add(new_heat)
        self._Database.DB.session.flush()
        self._Database.DB.session.refresh(new_heat)

        # Add heatnodes
        for node_index in range(self._RACE.num_nodes):
            new_heatNode = self._Database.HeatNode(
                heat_id=new_heat.id,
                node_index=node_index,
                pilot_id=RHUtils.PILOT_ID_NONE
            )

            if node_index in initPilots:
                new_heatNode.pilot_id = initPilots[node_index]

            self._Database.DB.session.add(new_heatNode)

        self.commit()

        self._Events.trigger(Evt.HEAT_DUPLICATE, {
            'heat_id': new_heat.id,
            })

        logger.info('Heat added: Heat {0}'.format(new_heat.id))

        return new_heat

    def duplicate_heat(self, source, **kwargs):
        # Add new heat by duplicating an existing one
        source_heat = self.get_heat(source)

        if source_heat.note:
            all_heat_notes = [heat.note for heat in self.get_heats()]
            new_heat_note = RHUtils.uniqueName(source_heat.note, all_heat_notes)
        else:
            new_heat_note = ''

        if 'dest_class' in kwargs:
            new_class = kwargs['dest_class']
        else:
            new_class = source_heat.class_id

        new_heat = self._Database.Heat(note=new_heat_note,
            class_id=new_class,
            results=None,
            cacheStatus=CacheStatus.INVALID)

        self._Database.DB.session.add(new_heat)
        self._Database.DB.session.flush()
        self._Database.DB.session.refresh(new_heat)

        for source_heatnode in self.get_heatNodes_by_heat(source_heat.id):
            new_heatnode = self._Database.HeatNode(heat_id=new_heat.id,
                node_index=source_heatnode.node_index,
                pilot_id=source_heatnode.pilot_id)
            self._Database.DB.session.add(new_heatnode)

        self.commit()

        self._Events.trigger(Evt.HEAT_DUPLICATE, {
            'heat_id': new_heat.id,
            })

        logger.info('Heat {0} duplicated to heat {1}'.format(source, new_heat.id))

        return new_heat

    def alter_heat(self, data):
        # Alters heat. Returns heat and list of affected races
        heat_id = data['heat']
        heat = self._Database.Heat.query.get(heat_id)

        if 'note' in data:
            self._PageCache.set_valid(False)
            heat.note = data['note']
        if 'class' in data:
            old_class_id = heat.class_id
            heat.class_id = data['class']
        if 'pilot' in data:
            node_index = data['node']
            heatnode = self._Database.HeatNode.query.filter_by(
                heat_id=heat_id, node_index=node_index).one()
            heatnode.pilot_id = data['pilot']

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
                        if pilot_race.node_index == data['node']:
                            pilot_race.pilot_id = data['pilot']
                    for race_lap in self._Database.SavedRaceLap.query.filter_by(race_id=race_meta.id):
                        if race_lap.node_index == data['node']:
                            race_lap.pilot_id = data['pilot']

                    self.clear_results_savedRaceMeta(race_meta.id)

                self.clear_results_heat(heat.id)

        if 'pilot' in data or 'class' in data:
            if len(race_list):
                if heat.class_id is not RHUtils.CLASS_ID_NONE:
                    self.clear_results_raceClass(heat.class_id)

                self.clear_results_event()
                self._PageCache.set_valid(False)

        self.commit()

        self._Events.trigger(Evt.HEAT_ALTER, {
            'heat_id': heat.id,
            })

        # update current race
        if heat_id == self._RACE.current_heat:
            self._RACE.node_pilots = {}
            self._RACE.node_teams = {}
            for heatNode in self.get_heatNodes_by_heat(heat_id):
                self._RACE.node_pilots[heatNode.node_index] = heatNode.pilot_id

                if heatNode.pilot_id is not RHUtils.PILOT_ID_NONE:
                    self._RACE.node_teams[heatNode.node_index] = self.get_pilot(heatNode.pilot_id).team
                else:
                    self._RACE.node_teams[heatNode.node_index] = None
            self._RACE.cacheStatus = CacheStatus.INVALID  # refresh leaderboard

        logger.info('Heat {0} altered with {1}'.format(heat_id, data))

        return heat, race_list

    def delete_heat(self, heat_id):
        # Deletes heat. Returns True/False success
        heat_count = self._Database.Heat.query.count()
        heat = self._Database.Heat.query.get(heat_id)
        if heat and heat_count > 1: # keep at least one heat
            heatnodes = self._Database.HeatNode.query.filter_by(heat_id=heat.id).order_by(self._Database.HeatNode.node_index).all()

            has_race = self.savedRaceMetas_has_heat(heat.id)

            if has_race or (self._RACE.current_heat == heat.id and self._RACE.race_status != RaceStatus.READY):
                logger.info('Refusing to delete heat {0}: is in use'.format(heat.id))
                return False
            else:
                self._Database.DB.session.delete(heat)
                for heatnode in heatnodes:
                    self._Database.DB.session.delete(heatnode)
                self.commit()

                logger.info('Heat {0} deleted'.format(heat.id))

                self._Events.trigger(Evt.HEAT_DELETE, {
                    'heat_id': heat_id,
                    })

                # if only one heat remaining then set ID to 1
                if heat_count == 2 and self._RACE.race_status == RaceStatus.READY:
                    try:
                        heat_obj = self._Database.Heat.query.first()
                        if heat_obj.id != 1:
                            heatnodes = self._Database.HeatNode.query.filter_by(heat_id=heat_obj.id).order_by(self._Database.HeatNode.node_index).all()

                            if not self.savedRaceMetas_has_heat(heat_obj.id):
                                logger.info("Adjusting single remaining heat ({0}) to ID 1".format(heat_obj.id))
                                heat_obj.id = 1
                                for heatnode in heatnodes:
                                    heatnode.heat_id = heat_obj.id
                                self.commit()
                                self._RACE.current_heat = 1
                                heat_id = 1  # set value so heat data is updated below
                            else:
                                logger.warning("Not changing single remaining heat ID ({0}): is in use".format(heat_obj.id))
                    except Exception as ex:
                        logger.warning("Error adjusting single remaining heat ID: " + str(ex))

                return True
        else:
            logger.info('Refusing to delete only heat')
            return False

    def set_results_heat(self, heat_id, data):
        heat = self._Database.Heat.query.get(heat_id)

        if not heat:
            return False

        if 'results' in data:
            heat.results = data['results']
        if 'cacheStatus' in data:
            heat.cacheStatus = data['cacheStatus']

        self.commit()
        return heat

    def clear_results_heat(self, heat_id):
        self._Database.Heat.query.filter_by(id=heat_id).update({
            self._Database.Heat.cacheStatus: CacheStatus.INVALID
            })
        self.commit()

    def clear_results_heats(self):
        self._Database.Heat.query.update({
            self._Database.Heat.cacheStatus: CacheStatus.INVALID
            })
        self.commit()

    def clear_heats(self):
        self._Database.DB.session.query(self._Database.Heat).delete()
        self._Database.DB.session.query(self._Database.HeatNode).delete()
        self.commit()
        return True

    def reset_heats(self, nofill=False):
        self.clear_heats()
        if not nofill:
            self.add_heat()
            self._RACE.current_heat = self.get_first_heat().id
        logger.info('Database heats reset')

    # HeatNodes
    def get_heatNodes(self):
        return self._Database.HeatNode.query.all()

    def get_heatNodes_by_heat(self, heat_id):
        return self._Database.HeatNode.query.filter_by(heat_id=heat_id).order_by(self._Database.HeatNode.node_index).all()

    def add_heatNode(self, heat_id, node_index):
        new_heatNode = self._Database.HeatNode(
            heat_id=heat_id,
            node_index=node_index,
            pilot_id=RHUtils.PILOT_ID_NONE
            )

        self._Database.DB.session.add(new_heatNode)
        return True

    def get_pilot_from_heatNode(self, heat_id, node_index):
        heatNode = self._Database.HeatNode.query.filter_by(heat_id=heat_id, node_index=node_index).one_or_none()
        if heatNode:
            return heatNode.pilot_id
        else:
            return None

    # Race Classes
    def get_raceClass(self, raceClass_id):
        return self._Database.RaceClass.query.get(raceClass_id)

    def get_raceClasses(self):
        return self._Database.RaceClass.query.all()

    def add_raceClass(self):
        # Add new race class
        new_race_class = self._Database.RaceClass(
            name='',
            description='',
            format_id=RHUtils.FORMAT_ID_NONE,
            cacheStatus=CacheStatus.INVALID
            )
        self._Database.DB.session.add(new_race_class)
        self.commit()

        self._Events.trigger(Evt.CLASS_ADD, {
            'class_id': new_race_class.id,
            })

        logger.info('Class added: Class {0}'.format(new_race_class))

        return new_race_class

    def duplicate_raceClass(self, source_class_id):
        source_class = self.get_raceClass(source_class_id)

        if source_class.name:
            all_class_names = [race_class.name for race_class in self.get_raceClasses()]
            new_class_name = RHUtils.uniqueName(source_class.name, all_class_names)
        else:
            new_class_name = ''

        new_class = self._Database.RaceClass(name=new_class_name,
            description=source_class.description,
            format_id=source_class.format_id,
            results=None,
            cacheStatus=CacheStatus.INVALID)

        self._Database.DB.session.add(new_class)
        self._Database.DB.session.flush()
        self._Database.DB.session.refresh(new_class)

        for heat in self._Database.Heat.query.filter_by(class_id=source_class_id).all():
            self.duplicate_heat(heat.id, dest_class=new_class.id)

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
        if 'class_format' in data:
            race_class.format_id = data['class_format']
        if 'class_description' in data:
            race_class.description = data['class_description']

        race_list = self._Database.SavedRaceMeta.query.filter_by(class_id=race_class_id).all()

        if 'class_name' in data:
            if len(race_list):
                self._PageCache.set_valid(False)

        if 'class_format' in data:
            if len(race_list):
                self._PageCache.set_valid(False)
                self.clear_results_event()
                self.clear_results_raceClass(race_class.id)

            for race_meta in race_list:
                race_meta.format_id = data['class_format']
                self.clear_results_savedRaceMeta(race_meta.id)

            heats = self._Database.Heat.query.filter_by(class_id=race_class_id).all()
            for heat in heats:
                self.clear_results_heat(heat.id)

        self.commit()

        self._Events.trigger(Evt.CLASS_ALTER, {
            'class_id': race_class_id,
            })

        logger.info('Altered race class {0} to {1}'.format(race_class_id, data))

        return race_class, race_list

    def delete_raceClass(self, class_id):
        race_class = self._Database.RaceClass.query.get(class_id)

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

    def set_results_raceClass(self, class_id, data):
        race_class = self._Database.RaceClass.query.get(class_id)

        if not race_class:
            return False

        if 'results' in data:
            race_class.results = data['results']
        if 'cacheStatus' in data:
            race_class.cacheStatus = data['cacheStatus']

        self.commit()
        return race_class

    def clear_results_raceClass(self, class_id):
        self._Database.RaceClass.query.filter_by(id=class_id).update({
            self._Database.RaceClass.cacheStatus: CacheStatus.INVALID
            })
        self.commit()

    def clear_results_raceClasses(self):
        self._Database.RaceClass.query.update({
            self._Database.RaceClass.cacheStatus: CacheStatus.INVALID
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
    def get_profile(self, profile_id):
        return self._Database.Profiles.query.get(profile_id)

    def get_profiles(self):
        return self._Database.Profiles.query.all()

    def get_first_profile(self):
        return self._Database.Profiles.query.first()

    def add_profile(self, init={}):
        new_profile = self._Database.Profiles(
            name = init['profile_name'] if 'profile_name' in init else '',
            frequencies = json.dumps(init['frequencies']) if 'frequencies' in init else '',
            enter_ats = json.dumps(init['enter_ats']) if 'enter_ats' in init else '',
            exit_ats = json.dumps(init['exit_ats']) if 'exit_ats' in init else ''
            )

        self._Database.DB.session.add(new_profile)
        self.commit()
        return new_profile

    def duplicate_profile(self, source_profile_id):
        source_profile = self.get_profile(source_profile_id)

        all_profile_names = [profile.name for profile in self.get_profiles()]

        if source_profile.name:
            new_profile_name = RHUtils.uniqueName(source_profile.name, all_profile_names)
        else:
            new_profile_name = RHUtils.uniqueName(self._Language.__('New Profile'), all_profile_names)

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
            profile.frequencies = json.dumps(data['frequencies'])
        if 'enter_ats' in data:
            profile.enter_ats = json.dumps(data['enter_ats'])
        if 'exit_ats' in data:
            profile.exit_ats = json.dumps(data['exit_ats'])

        self.commit()

        self._Events.trigger(Evt.PROFILE_ALTER, {
            'profile_id': profile.id,
            })

        logger.debug('Altered profile {0} to {1}'.format(profile.id, data))

        return profile

    def delete_profile(self, profile_id):
        if len(self.get_profiles()) > 1: # keep one profile
            profile = self._Database.Profiles.query.get(profile_id)
            self._Database.DB.session.delete(profile)
            self.commit()

            self._Events.trigger(Evt.PROFILE_DELETE, {
                'profile_id': profile_id,
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
        template["v"] = [None for _i in range(self._RACE.num_nodes)]

        self.add_profile({
            'profile_name': self.__("Default"),
            'frequencies': new_freqs,
            'enter_ats': template,
            'exit_ats': template
            })

        self.set_option("currentProfile", self.get_first_profile().id)
        logger.info("Database set default profiles")
        return True

    # Formats
    def get_raceFormat(self, raceFormat_id):
        return self._Database.RaceFormat.query.get(raceFormat_id)

    def get_raceFormats(self):
        return self._Database.RaceFormat.query.all()

    def get_first_raceFormat(self):
        return self._Database.RaceFormat.query.first()

    def add_format(self, init=None):
        race_format = self._Database.RaceFormat(
            name='',
            race_mode=0,
            race_time_sec=0,
            start_delay_min=0,
            start_delay_max=0,
            staging_tones=StagingTones.TONES_NONE,
            number_laps_win=0,
            win_condition=0,
            team_racing_mode=False,
            start_behavior=0)

        if init:
            if 'format_name' in init:
                race_format.name = init['format_name']
            if 'race_mode' in init:
                race_format.race_mode = init['race_mode']
            if 'race_time' in init:
                race_format.race_time_sec = init['race_time']
            if 'start_delay_min' in init:
                race_format.start_delay_min = init['start_delay_min']
            if 'start_delay_max' in init:
                race_format.start_delay_max = init['start_delay_max']
            if 'staging_tones' in init:
                race_format.staging_tones = init['staging_tones']
            if 'number_laps_win' in init:
                race_format.number_laps_win = init['number_laps_win']
            if 'start_behavior' in init:
                race_format.start_behavior = init['start_behavior']
            if 'win_condition' in init:
                race_format.win_condition = init['win_condition']
            if 'team_racing_mode' in init:
                race_format.team_racing_mode = (True if init['team_racing_mode'] else False)

        self._Database.DB.session.add(race_format)
        self.commit()

    def duplicate_raceFormat(self, source_format_id):
        source_format = self.get_raceFormat(source_format_id)

        all_format_names = [raceformat.name for raceformat in self.get_raceFormats()]

        if source_format.name:
            new_format_name = RHUtils.uniqueName(source_format.name, all_format_names)
        else:
            new_format_name = RHUtils.uniqueName(self._Language.__('New Format'), all_format_names)

        new_format = self._Database.RaceFormat(
            name=new_format_name,
            race_mode=source_format.race_mode,
            race_time_sec=source_format.race_time_sec ,
            start_delay_min=source_format.start_delay_min,
            start_delay_max=source_format.start_delay_max,
            staging_tones=source_format.staging_tones,
            number_laps_win=source_format.number_laps_win,
            win_condition=source_format.win_condition,
            team_racing_mode=source_format.team_racing_mode,
            start_behavior=source_format.start_behavior)
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
            self._RACE.race_status != RaceStatus.READY:
            logger.warning('Preventing race format alteration: race in progress')
            return False, False

        if 'format_name' in data:
            race_format.name = data['format_name']
        if 'race_mode' in data:
            race_format.race_mode = data['race_mode']
        if 'race_time' in data:
            race_format.race_time_sec = data['race_time']
        if 'start_delay_min' in data:
            race_format.start_delay_min = data['start_delay_min']
        if 'start_delay_max' in data:
            race_format.start_delay_max = data['start_delay_max']
        if 'staging_tones' in data:
            race_format.staging_tones = data['staging_tones']
        if 'number_laps_win' in data:
            race_format.number_laps_win = data['number_laps_win']
        if 'start_behavior' in data:
            race_format.start_behavior = data['start_behavior']
        if 'win_condition' in data:
            race_format.win_condition = data['win_condition']
        if 'team_racing_mode' in data:
            race_format.team_racing_mode = (True if data['team_racing_mode'] else False)

        self.commit()

        self._RACE.cacheStatus = CacheStatus.INVALID  # refresh leaderboard

        race_list = []

        if 'win_condition' in data or 'start_behavior' in data:
            race_list = self._Database.SavedRaceMeta.query.filter_by(format_id=race_format.id).all()

            if len(race_list):
                self._PageCache.set_valid(False)
                self.clear_results_event()

                for race in race_list:
                    self.clear_results_savedRaceMeta(race.id)

                classes = self._Database.RaceClass.query.filter_by(format_id=race_format.id).all()

                for race_class in classes:
                    self.clear_results_raceClass(race_class.id)

                    heats = self._Database.Heat.query.filter_by(class_id=race_class.id).all()

                    for heat in heats:
                        self.clear_results_heat(heat.id)

                self.commit()

        self._Events.trigger(Evt.RACE_FORMAT_ALTER, {
            'race_format': race_format.id,
            })

        logger.info('Altered format {0} to {1}'.format(race_format.id, data))

        return race_format, race_list

    def delete_raceFormat(self, format_id):
        # Prevent active race format change
        if self.get_optionInt('currentFormat') == format_id and \
            self._RACE.race_status != RaceStatus.READY:
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
            'race_mode': 0,
            'race_time_sec': 120,
            'start_delay_min': 2,
            'start_delay_max': 5,
            'staging_tones': StagingTones.TONES_ONE,
            'number_laps_win': 0,
            'win_condition': WinCondition.MOST_PROGRESS,
            'team_racing_mode': False,
            'start_behavior': 0
            })
        self.add_format({
            'format_name': self.__("1:30 Whoop Sprint"),
            'race_mode': 0,
            'race_time_sec': 90,
            'start_delay_min': 2,
            'start_delay_max': 5,
            'staging_tones': StagingTones.TONES_ALL,
            'number_laps_win': 0,
            'win_condition': WinCondition.MOST_PROGRESS,
            'team_racing_mode': False,
            'start_behavior': 0
            })
        self.add_format({
            'format_name': self.__("3:00 Extended Race"),
            'race_mode': 0,
            'race_time_sec': 210,
            'start_delay_min': 2,
            'start_delay_max': 5,
            'staging_tones': StagingTones.TONES_ALL,
            'number_laps_win': 0,
            'win_condition': WinCondition.MOST_PROGRESS,
            'team_racing_mode': False,
            'start_behavior': 0
            })
        self.add_format({
            'format_name': self.__("First to 3 Laps"),
            'race_mode': 1,
            'race_time_sec': 0,
            'start_delay_min': 2,
            'start_delay_max': 5,
            'staging_tones': StagingTones.TONES_ALL,
            'number_laps_win': 3,
            'win_condition': WinCondition.FIRST_TO_LAP_X,
            'team_racing_mode': False,
            'start_behavior': 0
            })
        self.add_format({
            'format_name': self.__("Open Practice"),
            'race_mode': 1,
            'race_time_sec': 0,
            'start_delay_min': 0,
            'start_delay_max': 0,
            'staging_tones': StagingTones.TONES_NONE,
            'number_laps_win': 0,
            'win_condition': WinCondition.NONE,
            'team_racing_mode': False,
            'start_behavior': 0
            })
        self.add_format({
            'format_name': self.__("Fastest Lap Qualifier"),
            'race_mode': 0,
            'race_time_sec': 120,
            'start_delay_min': 2,
            'start_delay_max': 5,
            'staging_tones': StagingTones.TONES_ONE,
            'number_laps_win': 0,
            'win_condition': WinCondition.FASTEST_LAP,
            'team_racing_mode': False,
            'start_behavior': 0
            })
        self.add_format({
            'format_name': self.__("Fastest 3 Laps Qualifier"),
            'race_mode': 0,
            'race_time_sec': 120,
            'start_delay_min': 2,
            'start_delay_max': 5,
            'staging_tones': StagingTones.TONES_ONE,
            'number_laps_win': 0,
            'win_condition': WinCondition.FASTEST_3_CONSECUTIVE,
            'team_racing_mode': False,
            'start_behavior': 0
            })
        self.add_format({
            'format_name': self.__("Lap Count Only"),
            'race_mode': 0,
            'race_time_sec': 120,
            'start_delay_min': 2,
            'start_delay_max': 5,
            'staging_tones': StagingTones.TONES_ONE,
            'number_laps_win': 0,
            'win_condition': WinCondition.MOST_LAPS,
            'team_racing_mode': False,
            'start_behavior': 0
            })
        self.add_format({
            'format_name': self.__("Team / Most Laps Wins"),
            'race_mode': 0,
            'race_time_sec': 120,
            'start_delay_min': 2,
            'start_delay_max': 5,
            'staging_tones': StagingTones.TONES_ALL,
            'number_laps_win': 0,
            'win_condition': WinCondition.MOST_PROGRESS,
            'team_racing_mode': True,
            'start_behavior': 0
            })
        self.add_format({
            'format_name': self.__("Team / First to 7 Laps"),
            'race_mode': 0,
            'race_time_sec': 120,
            'start_delay_min': 2,
            'start_delay_max': 5,
            'staging_tones': StagingTones.TONES_ALL,
            'number_laps_win': 7,
            'win_condition': WinCondition.FIRST_TO_LAP_X,
            'team_racing_mode': True,
            'start_behavior': 0
            })
        self.add_format({
            'format_name': self.__("Team / Fastest Lap Average"),
            'race_mode': 0,
            'race_time_sec': 120,
            'start_delay_min': 2,
            'start_delay_max': 5,
            'staging_tones': StagingTones.TONES_ALL,
            'number_laps_win': 0,
            'win_condition': WinCondition.FASTEST_LAP,
            'team_racing_mode': True,
            'start_behavior': 0
            })
        self.add_format({
            'format_name': self.__("Team / Fastest 3 Consecutive Average"),
            'race_mode': 0,
            'race_time_sec': 120,
            'start_delay_min': 2,
            'start_delay_max': 5,
            'staging_tones': StagingTones.TONES_ALL,
            'number_laps_win': 0,
            'win_condition': WinCondition.FASTEST_3_CONSECUTIVE,
            'team_racing_mode': True,
            'start_behavior': 0
            })

        self.commit()
        logger.info("Database reset race formats")
        return True

    # Race Meta
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
            cacheStatus=CacheStatus.INVALID
        )
        self._Database.DB.session.add(new_race)
        self.commit()

        logger.info('Race added: Race {0}'.format(new_race.id))

        return new_race

    def reassign_savedRaceMeta_heat(self, race_id, new_heat_id):
        race_meta = self._Database.SavedRaceMeta.query.get(race_id)

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
            for pilot_race in self.get_savedPilotRaces_by_savedRaceMeta(race_id):
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
        self._PageCache.set_valid(False)

        self.clear_results_heat(new_heat.id)
        self.clear_results_heat(old_heat.id)

        if old_format_id != new_format_id:
            race_meta.cacheStatus = CacheStatus.INVALID

        if old_heat.class_id != new_heat.class_id:
            self.clear_results_raceClass(new_class.id)
            self.clear_results_raceClass(old_class.id)

        self.commit()

        self._Events.trigger(Evt.RACE_ALTER, {
            'race_id': race_id,
            })

        logger.info('Race {0} reaasigned to heat {1}'.format(race_id, new_heat_id))

        return race_meta, new_heat

    def set_results_savedRaceMeta(self, race_id, data):
        race = self._Database.SavedRaceMeta.query.get(race_id)

        if not race:
            return False

        if 'results' in data:
            race.results = data['results']
        if 'cacheStatus' in data:
            race.cacheStatus = data['cacheStatus']

        self.commit()
        return race

    def clear_results_savedRaceMeta(self, race_id):
        self._Database.SavedRaceMeta.query.filter_by(id=race_id).update({
            self._Database.SavedRaceMeta.cacheStatus: CacheStatus.INVALID
            })
        self.commit()

    def clear_results_savedRaceMetas(self):
        self._Database.SavedRaceMeta.query.update({
            self._Database.SavedRaceMeta.cacheStatus: CacheStatus.INVALID
            })
        self.commit()

    def get_max_round(self, heat_id):
        return self._Database.DB.session.query(
            self._Database.DB.func.max(
                self._Database.SavedRaceMeta.round_id
            )).filter_by(heat_id=heat_id).scalar()

    # Pilot-Races
    def get_savedPilotRace(self, race_id):
        return self._Database.SavedPilotRace.query.get(race_id)

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
                exit_at=node_data['exit_at']
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

    def get_option(self, option, default_value=False):
        try:
            val = self._OptionsCache[option]
            if val or val == "":
                return val
            else:
                return default_value
        except:
            return default_value

    def set_option(self, option, value):
        self._OptionsCache[option] = value

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
        self.set_option("eventResults_cacheStatus", CacheStatus.INVALID)

        self.set_option("startThreshLowerAmount", "0")
        self.set_option("startThreshLowerDuration", "0")
        self.set_option("nextHeatBehavior", "0")

        logger.info("Reset global settings")

    # Event Results (Options)
    def set_results_event(self, data):
        if 'results' in data:
            self.set_option("eventResults_cacheStatus", data['results'])
        if 'cacheStatus' in data:
            self.set_option("eventResults_cacheStatus", data['cacheStatus'])

        return self.get_results_event()

    def get_results_event(self):
        return {
            'results': self.get_option("eventResults"),
            'cacheStatus': self.get_option("eventResults_cacheStatus")
        }

    def clear_results_event(self):
        self.set_option("eventResults_cacheStatus", CacheStatus.INVALID)
        return True
