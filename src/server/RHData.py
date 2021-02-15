#
# RaceData
# Provides abstraction for database and results page caches
#

import logging
logger = logging.getLogger(__name__)

import RHUtils
import copy

class RHData():
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
                    return db_query.kwargs['return_type']()

                return db_query.all()
            return wrapper

    def __init__(self, Database):
        self._Database = Database

    def get_pilot(self, pilot_id):
        return self._Database.Pilot.query.get(pilot_id)

    @_Decorators.getter_parameters
    def get_pilots(self, **kwargs):
        return self._Database.Pilot

    def get_heat(self, heat_id):
        return self._Database.Heat.query.get(heat_id)

    @_Decorators.getter_parameters
    def get_heats(self, **kwargs):
        return self._Database.Heat

    @_Decorators.getter_parameters
    def get_heatNodes(self, **kwargs):
        return self._Database.HeatNode

    def get_raceClass(self, raceClass_id):
        return self._Database.RaceClass.query.get(raceClass_id)

    @_Decorators.getter_parameters
    def get_raceClasses(self, **kwargs):
        return self._Database.RaceClass

    def get_profile(self, profile_id):
        return self._Database.Profiles.query.get(profile_id)

    @_Decorators.getter_parameters
    def get_profiles(self, **kwargs):
        return self._Database.Profiles

    def get_raceFormat(self, raceFormat_id):
        return self._Database.RaceFormat.query.get(raceFormat_id)

    @_Decorators.getter_parameters
    def get_raceFormats(self, **kwargs):
        return self._Database.RaceFormat

