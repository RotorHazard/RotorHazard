#
# RaceData
# Provides abstraction for database and results page caches
#

import logging
import RHUtils
import copy

class RHData():

    def __init__(self, Database, PageCache):
        self._Database = Database
        self._PageCache = PageCache

    def get_pilot(self, pilot_id):
        return self._Database.Pilot.query.get(pilot_id)

    def get_pilots(self):
        return self._Database.Pilot.query.all()

    def get_heat(self, heat_id):
        return self._Database.Heat.query.get(heat_id)

    def get_heats(self):
        return self._Database.Heat.query.all()

    def get_heatNode_by_heat(self, heat_id):
        return self._Database.HeatNode.query.filter_by(heat_id=heat_id).order_by(self._Database.HeatNode.node_index).all()

    def get_raceClass(self, raceClass_id):
        return self._Database.RaceClass.query.get(raceClass_id)

    def get_raceClasses(self):
        return self._Database.RaceClass.query.all()

    def get_profile(self, profile_id):
        return self._Database.Profiles.query.get(profile_id)

    def get_profiles(self):
        return self._Database.Profiles.query.all()

    def get_raceFormat(self, raceFormat_id):
        return self._Database.RaceFormat.query.get(raceFormat_id)

    def get_raceFormats(self):
        return self._Database.RaceFormat.query.all()

    def get_pageCache(self):
        return copy.deepcopy(self._PageCache)
