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

    # Pilots
    def get_pilot(self, pilot_id):
        return self._Database.Pilot.query.get(pilot_id)

    @_Decorators.getter_parameters
    def get_pilots(self, **kwargs):
        return self._Database.Pilot

    def add_pilot(self):
        new_pilot = self._Database.Pilot(
            name=self.Language.__('~Pilot %d Name') % (new_pilot.id),
            callsign=self.Language.__('~Callsign %d') % (new_pilot.id),
            team=DEF_TEAM_NAME,
            phonetic = '')

        self._DB.session.add(new_pilot)
        self._DB.session.commit()

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

        Events.trigger(Evt.PILOT_ALTER, {
            'pilot_id': pilot_id,
            })

        logger.info('Altered pilot {0} to {1}'.format(pilot_id, data))

        if 'callsign' in data or 'team_name' in data:
            race_list = []

            heatnodes = self.get_heatNodes(filter_by={"pilot_id": pilot_id})
            if heatnodes:
                for heatnode in heatnodes:
                    heat = self.get_heat(heatnode.heat_id)
                    heat.cacheStatus = Results.CacheStatus.INVALID
                    if heat.class_id != RHUtils.CLASS_ID_NONE:
                        race_class = self.get_raceClass(heat.class_id)
                        race_class.cacheStatus = Results.CacheStatus.INVALID
                    race_list.append(self.get_savedRaceMetas(
                        filter_by={"heat_id": heatnode.heat_id}
                        ))

            if len(race_list):
                self._PageCache.set_valid(False)
                self.set_option("eventResults_cacheStatus", Results.CacheStatus.INVALID)

                for race in race_list:
                    race.cacheStatus = Results.CacheStatus.INVALID

                self._Database.DB.session.commit()

        return pilot, race_list

    def delete_pilot(self, pilot_id):
        pilot = self.get_pilot(pilot_id)

        has_race = Database.SavedPilotRace.query.filter_by(pilot_id=pilot.id).first()
        self.get_savedRaceMetas(
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

    # Heats
    def get_heat(self, heat_id):
        return self._Database.Heat.query.get(heat_id)

    @_Decorators.getter_parameters
    def get_heats(self, **kwargs):
        return self._Database.Heat

    def add_heat(self):
        # Add new (empty) heat
        new_heat = self._Database.Heat(
            class_id=RHUtils.CLASS_ID_NONE,
            cacheStatus=Results.CacheStatus.INVALID
            )
        self._Database.DB.session.add(new_heat)
        self._Database.DB.session.flush()
        self._Database.DB.session.refresh(new_heat)

        for node in range(self._RACE.num_nodes): # Add next heat with empty pilots
            self._Database.DB.session.add(self._Database.HeatNode(heat_id=new_heat.id, node_index=node, pilot_id=RHUtils.PILOT_ID_NONE))

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
            _PageCache.set_valid(False)
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
                    new_class = RHData.get_raceClass(heat.class_id)
                    new_class.cacheStatus = Results.CacheStatus.INVALID

                self.set_option("eventResults_cacheStatus", Results.CacheStatus.INVALID)
                _PageCache.set_valid(False)

        self._Database.DB.session.commit()

        self._Events.trigger(Evt.HEAT_ALTER, {
            'heat_id': heat.id,
            })

        # update current race
        if heat_id == self._RACE.current_heat:
            RACE.node_pilots = {}
            RACE.node_teams = {}
            for heatNode in self.get_heatNodes(filter_by={'heat_id': heat_id}):
                RACE.node_pilots[heatNode.node_index] = heatNode.pilot_id

                if heatNode.pilot_id is not RHUtils.PILOT_ID_NONE:
                    RACE.node_teams[heatNode.node_index] = self.get_pilot(heatNode.pilot_id).team
                else:
                    RACE.node_teams[heatNode.node_index] = None
            self._RACE.cacheStatus = Results.CacheStatus.INVALID  # refresh leaderboard

        logger.info('Heat {0} altered with {1}'.format(heat_id, data))

        return heat, race_list

    def delete_heat(self, heat_id):
        # Deletes heat. Returns True/False success
        heat_count = self.get_heats(return_type='count')
        if heat_count > 1: # keep at least one heat
            heat = self.get_heat(heat_id)
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
                                RACE.current_heat = 1
                                heat_id = 1  # set value so heat data is updated below
                            else:
                                logger.warning("Not changing single remaining heat ID ({0}): is in use".format(heat_obj.id))
                    except Exception as ex:
                        logger.warning("Error adjusting single remaining heat ID: " + str(ex))

                return True
        else:
            logger.info('Refusing to delete only heat')
            return False

    # HeatNodes
    @_Decorators.getter_parameters
    def get_heatNodes(self, **kwargs):
        return self._Database.HeatNode

    # Race Classes
    def get_raceClass(self, raceClass_id):
        return self._Database.RaceClass.query.get(raceClass_id)

    @_Decorators.getter_parameters
    def get_raceClasses(self, **kwargs):
        return self._Database.RaceClass

    def add_raceClass(self):
        # Add new race class
        new_class = self._Database.RaceClass(
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

        return new_class

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
        race_class_id = data['class_id']
        race_class = self.get_raceClass(race_class_id)

        if 'class_name' in data:
            self._PageCache.set_valid(False)
            race_class.name = data['class_name']
        if 'class_format' in data:
            race_class.format_id = data['class_format']
        if 'class_description' in data:
            race_class.description = data['class_description']

        # alter existing classes
        if 'class_format' in data:
            self._PageCache.set_valid(False)
            self.set_option("eventResults_cacheStatus", Results.CacheStatus.INVALID)
            race_class.cacheStatus = Results.CacheStatus.INVALID

            race_list = self.get_savedRaceMetas(filter_by={"class_id": race_class_id})
            for race_meta in race_list:
                race_meta.format_id = data['class_format']
                race_meta.cacheStatus = Results.CacheStatus.INVALID

            heats = self.get_heats(filter_by={"class_id": race_class_id})
            for heat in heats:
                heat.cacheStatus = Results.CacheStatus.INVALID

        self._DB.session.commit()

        self._Events.trigger(Evt.CLASS_ALTER, {
            'class_id': race_class_id,
            })

        logger.info('Altered race class {0} to {1}'.format(race_class_id, data))

        return race_class, race_list

    def delete_raceClass(self, class_id):
        race_class = RHData.get_raceClass(class_id)

        has_race = self.get_savedRaceMetas(
            filter_by={"class_id": race_class.id},
            return_type='first'
            )

        if has_race:
            logger.info('Refusing to delete class {0}: is in use'.format(race_class.id))
            return False
        else:
            self._Database.DB.session.delete(race_class)
            for heat in RHData.get_heats():
                if heat.class_id == race_class.id:
                    heat.class_id = RHUtils.CLASS_ID_NONE

            self._Database.DB.session.commit()

            self._Events.trigger(Evt.CLASS_DELETE, {
                'class_id': race_class_id,
                })

            logger.info('Class {0} deleted'.format(race_class.id))

            return True

    # Profiles
    def get_profile(self, profile_id):
        return self._Database.Profiles.query.get(profile_id)

    @_Decorators.getter_parameters
    def get_profiles(self, **kwargs):
        return self._Database.Profiles

    def duplicate_profile(self, source_profile_id):
        source_profile = self.get_profile(source_profile_id)

        if source_profile.name:
            all_profile_names = [profile.name for profile in self.get_profiles()]
            new_profile_name = RHUtils.uniqueName(source_profile.name, all_profile_names)
        else:
            new_profile_name = ''

        new_profile = self._Database.Profiles(name=new_profile_name,
            description = '',
            frequencies = profile.frequencies,
            enter_ats = profile.enter_ats,
            exit_ats = profile.exit_ats,
            f_ratio = 100)
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

        Events.trigger(Evt.PROFILE_ALTER, {
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

            Events.trigger(Evt.PROFILE_DELETE, {
                'profile_id': profile_id,
                })

            return True
        else:
            logger.info('Refusing to delete only profile')
            return False

    # Formats
    def get_raceFormat(self, raceFormat_id):
        return self._Database.RaceFormat.query.get(raceFormat_id)

    @_Decorators.getter_parameters
    def get_raceFormats(self, **kwargs):
        return self._Database.RaceFormat

    # Race Meta
    @_Decorators.getter_parameters
    def get_savedRaceMetas(self, **kwargs):
        return self._Database.SavedRaceMeta

    # Pilot-Races
    @_Decorators.getter_parameters
    def get_savedPilotRaces(self, **kwargs):
        return self._Database.SavedPilotRace

    # Race Laps
    @_Decorators.getter_parameters
    def get_savedRaceLaps(self, **kwargs):
        return self._Database.SavedRaceLap

    # Splits
    @_Decorators.getter_parameters
    def get_lapSplits(self, **kwargs):
        return self._Database.LapSplit

    # Options
    @_Decorators.getter_parameters
    def get_options(self, **kwargs):
        return self._Database.GlobalSettings

    def primeOptionsCache(self):
        settings = self._Database.GlobalSettings.query.all()
        self._OptionsCache = {} # empty cache
        for setting in settings:
            self._OptionsCache[setting.option_name] = setting.option_value

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
