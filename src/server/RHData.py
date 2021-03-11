#
# RaceData
# Provides abstraction for database and results page caches
#

import logging
logger = logging.getLogger(__name__)

import json
import RHUtils
import Results
from eventmanager import Evt
from RHRace import RaceStatus

class RHData():
    _OptionsCache = {} # Local Python cache for global settings

    class _Decorators():
        @classmethod
        def getter_parameters(cls, func):
            def wrapper(*args, **kwargs):
                db_obj = func(*args, **kwargs)
                db_query = db_obj.query

                if 'filter_by' in kwargs:
                    db_query = db_query.filter_by(**kwargs['filter_by'])

                if 'order_by' in kwargs:
                    order = []
                    for key, val in kwargs['order_by'].items():
                        if val == 'desc':
                            order.append(getattr(db_obj, key).desc())
                        else:
                            order.append(getattr(db_obj, key))

                    db_query = db_query.order_by(*order)

                if 'return_type' in kwargs:
                    if kwargs['return_type'] in [
                        'all',
                        'first',
                        'one',
                        'one_or_none',
                        'count'
                        ]:
                        return getattr(db_query, kwargs['return_type'])()

                return db_query.all()
            return wrapper

    def __init__(self, Database, Events, RACE):
        self._Database = Database
        self._Events = Events
        self._RACE = RACE

    def late_init(self, PageCache, Language):
        self._PageCache = PageCache
        self._Language = Language

    # Integrity Checking
    def check_integrity(self, server_api_value):
        if self.get_optionInt('server_api') < server_api_value:
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


    # Pilots
    def get_pilot(self, pilot_id):
        return self._Database.Pilot.query.get(pilot_id)

    @_Decorators.getter_parameters
    def get_pilots(self, **kwargs):
        return self._Database.Pilot

    def add_pilot(self, init=None):
        new_pilot = self._Database.Pilot(
            name='',
            callsign='',
            team=RHUtils.DEF_TEAM_NAME,
            phonetic = '')

        if init:
            if 'name' in init:
                new_pilot.name = init['name']
            if 'callsign' in init:
                new_pilot.callsign = init['callsign']
            if 'team' in init:
                new_pilot.team = init['team']
            if 'phonetic' in init:
                new_pilot.phonetic = init['phonetic']

        self._Database.DB.session.add(new_pilot)
        self._Database.DB.session.flush()

        new_pilot.name=self._Language.__('~Pilot %d Name') % (new_pilot.id)
        new_pilot.callsign=self._Language.__('~Callsign %d') % (new_pilot.id)

        self._Database.DB.session.commit()

        self._Events.trigger(Evt.PILOT_ADD, {
            'pilot_id': new_pilot.id,
            })

        logger.info('Pilot added: Pilot {0}'.format(new_pilot.id))

        return new_pilot

    def alter_pilot(self, data):
        pilot_id = data['pilot_id']
        pilot = self.get_pilot(pilot_id)
        if 'callsign' in data:
            pilot.callsign = data['callsign']
        if 'team_name' in data:
            pilot.team = data['team_name']
        if 'phonetic' in data:
            pilot.phonetic = data['phonetic']
        if 'name' in data:
            pilot.name = data['name']

        self._Database.DB.session.commit()

        self._RACE.cacheStatus = Results.CacheStatus.INVALID  # refresh current leaderboard

        self._Events.trigger(Evt.PILOT_ALTER, {
            'pilot_id': pilot_id,
            })

        logger.info('Altered pilot {0} to {1}'.format(pilot_id, data))

        race_list = []
        if 'callsign' in data or 'team_name' in data:
            heatnodes = self.get_heatNodes(filter_by={"pilot_id": pilot_id})
            if heatnodes:
                for heatnode in heatnodes:
                    heat = self.get_heat(heatnode.heat_id)
                    heat.cacheStatus = Results.CacheStatus.INVALID
                    if heat.class_id != RHUtils.CLASS_ID_NONE:
                        race_class = self.get_raceClass(heat.class_id)
                        race_class.cacheStatus = Results.CacheStatus.INVALID
                    for race in self.get_savedRaceMetas(
                        filter_by={"heat_id": heatnode.heat_id}
                        ):
                        race_list.append(race)

            if len(race_list):
                self._PageCache.set_valid(False)
                self.set_option("eventResults_cacheStatus", Results.CacheStatus.INVALID)

                for race in race_list:
                    race.cacheStatus = Results.CacheStatus.INVALID

                self._Database.DB.session.commit()

        return pilot, race_list

    def delete_pilot(self, pilot_id):
        pilot = self.get_pilot(pilot_id)

        has_race = self.get_savedPilotRaces(
            filter_by={"pilot_id": pilot.id},
            return_type='first'
            )

        if has_race:
            logger.info('Refusing to delete pilot {0}: is in use'.format(pilot.id))
            return False
        else:
            self._Database.DB.session.delete(pilot)
            for heatNode in self.get_heatNodes():
                if heatNode.pilot_id == pilot.id:
                    heatNode.pilot_id = RHUtils.PILOT_ID_NONE
            self._Database.DB.session.commit()

            logger.info('Pilot {0} deleted'.format(pilot.id))

            self._RACE.cacheStatus = Results.CacheStatus.INVALID  # refresh leaderboard

            return True

    def get_recent_pilot_node(self, pilot_id):
        return self._Database.HeatNode.query.filter_by(pilot_id=pilot_id).order_by(self._Database.HeatNode.id.desc()).first()

    def clear_pilots(self):
        self._Database.DB.session.query(self._Database.Pilot).delete()
        self._Database.DB.session.commit()
        return True

    # Heats
    def get_heat(self, heat_id):
        return self._Database.Heat.query.get(heat_id)

    @_Decorators.getter_parameters
    def get_heats(self, **kwargs):
        return self._Database.Heat

    def get_first_heat(self):
        return self._Database.Heat.query.first()

    def add_heat(self, init=None, initPilots=None):
        # Add new heat
        new_heat = self._Database.Heat(
            class_id=RHUtils.CLASS_ID_NONE,
            cacheStatus=Results.CacheStatus.INVALID
            )

        if init:
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

            if initPilots and node_index in initPilots:
                new_heatNode.pilot_id = initPilots[node_index]

            self._Database.DB.session.add(new_heatNode)

        self._Database.DB.session.commit()

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
            cacheStatus=Results.CacheStatus.INVALID)

        self._Database.DB.session.add(new_heat)
        self._Database.DB.session.flush()
        self._Database.DB.session.refresh(new_heat)

        for source_heatnode in self.get_heatNodes(filter_by={'heat_id': source_heat.id}):
            new_heatnode = self._Database.HeatNode(heat_id=new_heat.id,
                node_index=source_heatnode.node_index,
                pilot_id=source_heatnode.pilot_id)
            self._Database.DB.session.add(new_heatnode)

        self._Database.DB.session.commit()

        self._Events.trigger(Evt.HEAT_DUPLICATE, {
            'heat_id': new_heat.id,
            })

        logger.info('Heat {0} duplicated to heat {1}'.format(source, new_heat.id))

        return new_heat

    def alter_heat(self, data):
        # Alters heat. Returns heat and list of affected races
        heat_id = data['heat']
        heat = self.get_heat(heat_id)

        if 'note' in data:
            self._PageCache.set_valid(False)
            heat.note = data['note']
        if 'class' in data:
            old_class_id = heat.class_id
            heat.class_id = data['class']
        if 'pilot' in data:
            node_index = data['node']
            heatnode = self.get_heatNodes(
                filter_by={'heat_id': heat.id, 'node_index':node_index},
                return_type='one')
            heatnode.pilot_id = data['pilot']

        # alter existing saved races:
        race_list = self.get_savedRaceMetas(filter_by={"heat_id":heat_id})

        if 'class' in data:
            if len(race_list):
                for race_meta in race_list:
                    race_meta.class_id = data['class']

                if old_class_id is not RHUtils.CLASS_ID_NONE:
                    old_class = self.get_raceClass(old_class_id)
                    old_class.cacheStatus = Results.CacheStatus.INVALID

        if 'pilot' in data:
            if len(race_list):
                for race_meta in race_list:
                    for pilot_race in self.get_savedPilotRaces(
                        filter_by={"race_id": race_meta.id}):
                        if pilot_race.node_index == data['node']:
                            pilot_race.pilot_id = data['pilot']
                    for race_lap in self.get_savedRaceLaps(
                        filter_by={"race_id": race_meta.id}):
                        if race_lap.node_index == data['node']:
                            race_lap.pilot_id = data['pilot']

                    race_meta.cacheStatus = Results.CacheStatus.INVALID

                heat.cacheStatus = Results.CacheStatus.INVALID

        if 'pilot' in data or 'class' in data:
            if len(race_list):
                if heat.class_id is not RHUtils.CLASS_ID_NONE:
                    new_class = self.get_raceClass(heat.class_id)
                    new_class.cacheStatus = Results.CacheStatus.INVALID

                self.set_option("eventResults_cacheStatus", Results.CacheStatus.INVALID)
                self._PageCache.set_valid(False)

        self._Database.DB.session.commit()

        self._Events.trigger(Evt.HEAT_ALTER, {
            'heat_id': heat.id,
            })

        # update current race
        if heat_id == self._RACE.current_heat:
            self._RACE.node_pilots = {}
            self._RACE.node_teams = {}
            for heatNode in self.get_heatNodes(filter_by={'heat_id': heat_id}):
                self._RACE.node_pilots[heatNode.node_index] = heatNode.pilot_id

                if heatNode.pilot_id is not RHUtils.PILOT_ID_NONE:
                    self._RACE.node_teams[heatNode.node_index] = self.get_pilot(heatNode.pilot_id).team
                else:
                    self._RACE.node_teams[heatNode.node_index] = None
            self._RACE.cacheStatus = Results.CacheStatus.INVALID  # refresh leaderboard

        logger.info('Heat {0} altered with {1}'.format(heat_id, data))

        return heat, race_list

    def delete_heat(self, heat_id):
        # Deletes heat. Returns True/False success
        heat_count = self.get_heats(return_type='count')
        heat = self.get_heat(heat_id)
        if heat and heat_count > 1: # keep at least one heat
            heatnodes = self.get_heatNodes(filter_by={'heat_id': heat.id})

            has_race = self.get_savedRaceMetas(
                filter_by={"heat_id": heat.id}, return_type='first')

            if has_race or (self._RACE.current_heat == heat.id and self._RACE.race_status != RaceStatus.READY):
                logger.info('Refusing to delete heat {0}: is in use'.format(heat.id))
                return False
            else:
                self._Database.DB.session.delete(heat)
                for heatnode in heatnodes:
                    self._Database.DB.session.delete(heatnode)
                self._Database.DB.session.commit()

                logger.info('Heat {0} deleted'.format(heat.id))

                self._Events.trigger(Evt.HEAT_DELETE, {
                    'heat_id': heat_id,
                    })

                # if only one heat remaining then set ID to 1
                if heat_count == 2 and self._RACE.race_status == RaceStatus.READY:
                    try:
                        heat_obj = self._Database.Heat.query.first()
                        if heat_obj.id != 1:
                            heatnodes = self.get_heatNodes(filter_by={'heat_id': heat_obj.id})
                            has_race = self.get_savedRaceMetas(
                                filter_by={"heat_id": heat_obj.id}, return_type='first')

                            if not has_race:
                                logger.info("Adjusting single remaining heat ({0}) to ID 1".format(heat_obj.id))
                                heat_obj.id = 1
                                for heatnode in heatnodes:
                                    heatnode.heat_id = heat_obj.id
                                self._Database.DB.session.commit()
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

    def clear_heats(self):
        self._Database.DB.session.query(self._Database.Heat).delete()
        self._Database.DB.session.query(self._Database.HeatNode).delete()
        self._Database.DB.session.commit()
        return True

    # HeatNodes
    @_Decorators.getter_parameters
    def get_heatNodes(self, **kwargs):
        return self._Database.HeatNode

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

    @_Decorators.getter_parameters
    def get_raceClasses(self, **kwargs):
        return self._Database.RaceClass

    def add_raceClass(self):
        # Add new race class
        new_race_class = self._Database.RaceClass(
            name='',
            description='',
            format_id=RHUtils.FORMAT_ID_NONE,
            cacheStatus=Results.CacheStatus.INVALID
            )
        self._Database.DB.session.add(new_race_class)
        self._Database.DB.session.commit()

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
            cacheStatus=Results.CacheStatus.INVALID)

        self._Database.DB.session.add(new_class)
        self._Database.DB.session.flush()
        self._Database.DB.session.refresh(new_class)

        for heat in self.get_heats(filter_by={"class_id": source_class_id}):
            self.duplicate_heat(heat.id, dest_class=new_class.id)

        self._Database.DB.session.commit()

        self._Events.trigger(Evt.CLASS_DUPLICATE, {
            'class_id': new_class.id,
            })

        logger.info('Class {0} duplicated to class {1}'.format(source_class.id, new_class.id))

        return new_class

    def alter_raceClass(self, data):
        # alter existing classes
        race_class_id = data['class_id']
        race_class = self.get_raceClass(race_class_id)

        if not race_class:
            return False, False

        if 'class_name' in data:
            race_class.name = data['class_name']
        if 'class_format' in data:
            race_class.format_id = data['class_format']
        if 'class_description' in data:
            race_class.description = data['class_description']

        race_list = self.get_savedRaceMetas(filter_by={"class_id": race_class_id})

        if 'class_name' in data:
            if len(race_list):
                self._PageCache.set_valid(False)

        if 'class_format' in data:
            if len(race_list):
                self._PageCache.set_valid(False)
                self.set_option("eventResults_cacheStatus", Results.CacheStatus.INVALID)
                race_class.cacheStatus = Results.CacheStatus.INVALID

            for race_meta in race_list:
                race_meta.format_id = data['class_format']
                race_meta.cacheStatus = Results.CacheStatus.INVALID

            heats = self.get_heats(filter_by={"class_id": race_class_id})
            for heat in heats:
                heat.cacheStatus = Results.CacheStatus.INVALID

        self._Database.DB.session.commit()

        self._Events.trigger(Evt.CLASS_ALTER, {
            'class_id': race_class_id,
            })

        logger.info('Altered race class {0} to {1}'.format(race_class_id, data))

        return race_class, race_list

    def delete_raceClass(self, class_id):
        race_class = self.get_raceClass(class_id)

        has_race = self.get_savedRaceMetas(
            filter_by={"class_id": race_class.id},
            return_type='first'
            )

        if has_race:
            logger.info('Refusing to delete class {0}: is in use'.format(race_class.id))
            return False
        else:
            self._Database.DB.session.delete(race_class)
            for heat in self.get_heats():
                if heat.class_id == race_class.id:
                    heat.class_id = RHUtils.CLASS_ID_NONE

            self._Database.DB.session.commit()

            self._Events.trigger(Evt.CLASS_DELETE, {
                'class_id': race_class.id,
                })

            logger.info('Class {0} deleted'.format(race_class.id))

            return True

    def clear_raceClasses(self):
        self._Database.DB.session.query(self._Database.RaceClass).delete()
        self._Database.DB.session.commit()
        return True

    # Profiles
    def get_profile(self, profile_id):
        return self._Database.Profiles.query.get(profile_id)

    @_Decorators.getter_parameters
    def get_profiles(self, **kwargs):
        return self._Database.Profiles

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
            if 'frequencies' in init:
                new_profile.frequencies = init['frequencies']
            if 'enter_ats' in init:
                new_profile.enter_ats = init['enter_ats']
            if 'exit_ats' in init:
                new_profile.exit_ats = init['exit_ats']

        self._Database.DB.session.add(new_profile)
        self._Database.DB.session.commit()

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
        self._Database.DB.session.commit()

        self._Events.trigger(Evt.PROFILE_ADD, {
            'profile_id': new_profile.id,
            })

        return new_profile

    def alter_profile(self, data):
        profile = self.get_profile(data['profile_id'])

        if 'profile_name' in data:
            profile.name = data['profile_name']
        if 'profile_description' in data:
            profile.description = data['profile_description']
        if 'enter_ats' in data:
            profile.enter_ats = json.dumps(data['enter_ats'])
        if 'exit_ats' in data:
            profile.exit_ats = json.dumps(data['exit_ats'])

        self._Database.DB.session.commit()

        self._Events.trigger(Evt.PROFILE_ALTER, {
            'profile_id': profile.id,
            })

        logger.info('Altered profile {0} to {1}'.format(profile.id, data))

        return profile

    def delete_profile(self, profile_id):
        profile_count = self.get_heats(return_type='count')
        if profile_count > 1: # keep one profile
            profile = self.get_profile(profile_id)
            self._Database.DB.session.delete(profile)
            self._Database.DB.session.commit()

            self._Events.trigger(Evt.PROFILE_DELETE, {
                'profile_id': profile_id,
                })

            return True
        else:
            logger.info('Refusing to delete only profile')
            return False

    def clear_profiles(self):
        self._Database.DB.session.query(self._Database.Profiles).delete()
        self._Database.DB.session.commit()
        return True

    # Formats
    def get_raceFormat(self, raceFormat_id):
        return self._Database.RaceFormat.query.get(raceFormat_id)

    @_Decorators.getter_parameters
    def get_raceFormats(self, **kwargs):
        return self._Database.RaceFormat

    def get_first_raceFormat(self):
        return self._Database.RaceFormat.query.first()

    def add_format(self, init=None):
        race_format = self._Database.RaceFormat(
            name='',
            race_mode=0,
            race_time_sec=0,
            start_delay_min=0,
            start_delay_max=0,
            staging_tones=0,
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
        self._Database.DB.session.commit()

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
        self._Database.DB.session.commit()

        self._Events.trigger(Evt.RACE_FORMAT_ADD, {
            'format_id': new_format.id,
            })

        return new_format

    def alter_raceFormat(self, data):
        race_format = self.get_raceFormat(data['format_id'])

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

        self._Database.DB.session.commit()

        self._RACE.cacheStatus = Results.CacheStatus.INVALID  # refresh leaderboard

        race_list = []

        if 'win_condition' in data or 'start_behavior' in data:
            race_list = self.get_savedRaceMetas(
                filter_by={"format_id": race_format.id})

            if len(race_list):
                self._PageCache.set_valid(False)
                self.set_option("eventResults_cacheStatus", Results.CacheStatus.INVALID)

                for race in race_list:
                    race.cacheStatus = Results.CacheStatus.INVALID

                classes = self.get_raceClasses(
                    filter_by={"format_id": race_format.id})

                for race_class in classes:
                    race_class.cacheStatus = Results.CacheStatus.INVALID

                    heats = self.get_heats(
                        filter_by={"class_id": race_class.id})

                    for heat in heats:
                        heat.cacheStatus = Results.CacheStatus.INVALID

                self._Database.DB.session.commit()

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

        if self.get_savedRaceMetas(filter_by={"format_id": format_id}):
            logger.warning('Preventing race format deletion: saved race exists')
            return False

        format_count = self.get_raceFormats(return_type='count')
        race_format = self.get_raceFormat(format_id)
        if race_format and format_count > 1: # keep one format
            self._Database.DB.session.delete(race_format)
            self._Database.DB.session.commit()

            self._Events.trigger(Evt.RACE_FORMAT_DELETE, {
                'race_format': format_id,
                })

            # *** first_raceFormat = self.get_raceFormats(return_type="first")
            # *** self._RACE.set_raceFormat(first_raceFormat)

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

        self._Database.DB.session.commit()
        return True

    # Race Meta
    def get_savedRaceMeta(self, raceMeta_id):
        return self._Database.SavedRaceMeta.query.get(raceMeta_id)

    def get_savedRaceMeta_by_heat_round(self, heat_id, round_id):
        return self._Database.SavedRaceMeta.query.filter_by(heat_id=heat_id, round_id=round_id).one()

    @_Decorators.getter_parameters
    def get_savedRaceMetas(self, **kwargs):
        return self._Database.SavedRaceMeta

    def get_savedRaceMetas_by_heat(self, heat_id):
        return self._Database.SavedRaceMeta.query.filter_by(heat_id=heat_id).order_by(self._Database.SavedRaceMeta.round_id).all()

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
            cacheStatus=Results.CacheStatus.INVALID
        )
        self._Database.DB.session.add(new_race)
        self._Database.DB.session.commit()

        logger.info('Race added: Race {0}'.format(new_race.id))

        return new_race

    def reassign_savedRaceMeta_heat(self, race_id, new_heat_id):
        race_meta = self.get_savedRaceMeta(race_id)

        old_heat_id = race_meta.heat_id
        old_heat = self.get_heat(old_heat_id)
        old_class = self.get_raceClass(old_heat.class_id)
        old_format_id = old_class.format_id

        new_heat = self.get_heat(new_heat_id)
        new_class = self.get_raceClass(new_heat.class_id)
        new_format_id = new_class.format_id

        # clear round ids
        heat_races = self.get_savedRaceMetas(filter_by={"heat_id": new_heat_id})
        race_meta.round_id = 0
        dummy_round_counter = -1
        for race in heat_races:
            race.round_id = dummy_round_counter
            dummy_round_counter -= 1

        # assign new heat
        race_meta.heat_id = new_heat_id
        race_meta.class_id = new_heat.class_id
        race_meta.format_id = new_format_id

        # renumber rounds
        self._Database.DB.session.flush()
        old_heat_races = self.get_savedRaceMetas(
            filter_by={"heat_id": old_heat_id},
            order_by={"start_time_formatted": None}
            )
        round_counter = 1
        for race in old_heat_races:
            race.round_id = round_counter
            round_counter += 1

        new_heat_races = self.get_savedRaceMetas(
            filter_by={"heat_id": new_heat_id},
            order_by={"start_time_formatted": None}
            )
        round_counter = 1
        for race in new_heat_races:
            race.round_id = round_counter
            round_counter += 1

        self._Database.DB.session.commit()

        # cache cleaning
        self._PageCache.set_valid(False)

        new_heat.cacheStatus = Results.CacheStatus.INVALID
        old_heat.cacheStatus = Results.CacheStatus.INVALID

        if old_format_id != new_format_id:
            race_meta.cacheStatus = Results.CacheStatus.INVALID

        if old_heat.class_id != new_heat.class_id:
            new_class.cacheStatus = Results.CacheStatus.INVALID
            old_class.cacheStatus = Results.CacheStatus.INVALID

        self._Database.DB.session.commit()

        self._Events.trigger(Evt.RACE_ALTER, {
            'race_id': race_id,
            })

        logger.info('Race {0} reaasigned to heat {1}'.format(race_id, new_heat_id))

        return race_meta, new_heat

    def get_max_round(self, heat_id):
        return self._Database.DB.session.query(
            self._Database.DB.func.max(
                self._Database.SavedRaceMeta.round_id
            )).filter_by(heat_id=heat_id).scalar()

    # Pilot-Races
    def get_savedPilotRace(self, race_id):
        return self._Database.SavedPilotRace.query.get(race_id)

    @_Decorators.getter_parameters
    def get_savedPilotRaces(self, **kwargs):
        return self._Database.SavedPilotRace

    def get_savedPilotRaces_by_savedRaceMeta(self, race_id):
        return self._Database.SavedPilotRace.query.filter_by(race_id=race_id).all()

    def alter_savedPilotRace(self, data):
        pilotrace = self.get_savedPilotRace(data['pilotrace_id'])

        if 'enter_at' in data:
            pilotrace.enter_at = data['enter_at']
        if 'exit_at' in data:
            pilotrace.exit_at = data['exit_at']

        self._Database.DB.session.commit()

        return True

    def savedPilotRaces_has_pilot(self, pilot_id):
        return bool(self._Database.SavedPilotRace.query.filter_by(pilot_id=pilot_id).count())

    # Race Laps
    @_Decorators.getter_parameters
    def get_savedRaceLaps(self, **kwargs):
        return self._Database.SavedRaceLap

    def get_savedRaceLaps_by_savedPilotRace(self, pilotrace_id):
        return self._Database.SavedRaceLap.query.filter_by(pilotrace_id=pilotrace_id).order_by(self._Database.SavedRaceLap.lap_time_stamp).all()

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

        self._Database.DB.session.commit()
        return True

    # Race general
    def add_race_data(self, data):
        for node_index, node_data  in data.items():
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
                    source = lap['source'],
                    deleted = lap['deleted']
                ))

        self._Database.DB.session.commit()
        return True

    def clear_race_data(self):
        self._Database.DB.session.query(self._Database.SavedRaceMeta).delete()
        self._Database.DB.session.query(self._Database.SavedPilotRace).delete()
        self._Database.DB.session.query(self._Database.SavedRaceLap).delete()
        self._Database.DB.session.commit()
        return True

    # Splits
    @_Decorators.getter_parameters
    def get_lapSplits(self, **kwargs):
        return self._Database.LapSplit

    def clear_lapSplits(self):
        self._Database.DB.session.query(self._Database.LapSplit).delete()
        self._Database.DB.session.commit()
        return True

    # Options
    @_Decorators.getter_parameters
    def get_options(self, **kwargs):
        return self._Database.GlobalSettings

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
        self._Database.DB.session.commit()

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
        self._Database.DB.session.commit()
        return True
