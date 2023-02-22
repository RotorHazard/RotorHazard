'''
Page Cache

Stores cached results objects assembled via the Results module and database
lap lists. If valid, served directly to results without rebuilding.
buildToken is a monotonic timestamp so in-progress builds can be interrupted
if new data becomes available during the build process.

'''

import logging
from monotonic import monotonic
from eventmanager import Evt
import Results
import RHUtils
import gevent

logger = logging.getLogger(__name__)

from flask_sqlalchemy import SQLAlchemy
DB = SQLAlchemy()

class PageCache:
    _CACHE_TIMEOUT = 10

    def __init__(self, RHData, Events):
        self._RHData = RHData
        self._Events = Events
        self._cache = {} # Cache of complete results page
        self._buildToken = False # Time of result generation or false if no results are being calculated
        self._valid = False # Whether cache is valid

    def get_cache(self):
        if self.get_valid(): # Output existing calculated results
            logger.debug('Getting results from cache')
            return self._cache
        else:
            self.update_cache()
            return self._cache

    def get_buildToken(self):
        return self._buildToken

    def get_valid(self):
        return self._valid

    def set_cache(self, cache):
        self._cache = cache

    def set_buildToken(self, buildToken):
        self._buildToken = buildToken

    def set_valid(self, valid):
        self._valid = valid

    def check_buildToken(self, timing):
        if self.get_buildToken():
            while True: # Pause this thread until calculations are completed
                gevent.idle()
                if self.get_buildToken() is False:
                    break
                elif monotonic() > self.get_buildToken() + self._CACHE_TIMEOUT:
                    logger.warning('T%d: Timed out waiting for other cache build thread', timing['start'])
                    self.set_buildToken(False)
                    break


    def update_cache(self):
        '''Builds any invalid atomic result caches and creates final output'''
        timing = {
            'start': monotonic()
        }
        logger.debug('T%d: Result data build started', timing['start'])

        error_flag = False
        results = None

        self.check_buildToken(timing) # Don't restart calculation if another calculation thread exists

        if self.get_valid(): # Output existing calculated results
            logger.info('T%d: Returning valid cache', timing['start'])

        else:
            timing['build_start'] = monotonic()
            self.set_buildToken(monotonic())

            heats = {}
            for heat in self._RHData.get_heats():
                if self._RHData.savedRaceMetas_has_heat(heat.id):
                    rounds = []
                    for race in self._RHData.get_savedRaceMetas_by_heat(heat.id):    
                        pilotraces = []
                        for pilotrace in self._RHData.get_savedPilotRaces_by_savedRaceMeta(race.id):
                            gevent.sleep()
                            laps = []
                            for lap in self._RHData.get_savedRaceLaps_by_savedPilotRace(pilotrace.id):
                                laps.append({
                                    'id': lap.id,
                                    'lap_time_stamp': lap.lap_time_stamp,
                                    'lap_time': lap.lap_time,
                                    'lap_time_formatted': lap.lap_time_formatted,
                                    'source': lap.source,
                                    'deleted': lap.deleted
                                })

                            pilot_data = self._RHData.get_pilot(pilotrace.pilot_id)
                            if pilot_data:
                                nodepilot = pilot_data.callsign
                            else:
                                nodepilot = None

                            pilotraces.append({
                                'callsign': nodepilot,
                                'pilot_id': pilotrace.pilot_id,
                                'node_index': pilotrace.node_index,
                                'laps': laps
                            })

                        output = self._RHData.get_results_savedRaceMeta(race)
                        results = output['data']
                        if not output['result']:
                            error_flag = True
                            logger.warning('T%d: Cache build timed out: Heat %d Round %d', timing['start'], heat.id, race.round_id)

                        rounds.append({
                            'id': race.round_id,
                            'start_time_formatted': race.start_time_formatted,
                            'nodes': pilotraces,
                            'leaderboard': results
                        })

                    output = self._RHData.get_results_heat(heat)
                    results = output['data']
                    if not output['result']:
                        error_flag = True
                        logger.warning('T%d: Cache build timed out: Heat %d', timing['start'], heat.id)

                    heats[heat.id] = {
                        'heat_id': heat.id,
                        'displayname': heat.displayname(),
                        'rounds': rounds,
                        'leaderboard': results
                    }

            timing['round_results'] = monotonic()
            logger.debug('T%d: heat_round results assembled in %.3fs', timing['start'], timing['round_results'] - timing['build_start'])

            gevent.sleep()
            heats_by_class = {}
            heats_by_class[RHUtils.CLASS_ID_NONE] = [heat.id for heat in self._RHData.get_heats_by_class(RHUtils.CLASS_ID_NONE)]
            for race_class in self._RHData.get_raceClasses():
                heats_by_class[race_class.id] = [heat.id for heat in self._RHData.get_heats_by_class(race_class.id)]

            timing['by_class'] = monotonic()

            gevent.sleep()
            current_classes = {}
            for race_class in self._RHData.get_raceClasses():
                output = self._RHData.get_results_raceClass(race_class)
                results = output['data']
                if not output['result']:
                    error_flag = True
                    logger.warning('T%d: Cache build timed out: Class Summary %d', timing['start'], race_class.id)

                output = self._RHData.get_ranking_raceClass(race_class)
                ranking = output['data']
                if not output['result']:
                    error_flag = True
                    logger.warning('T{}: Rebuild timed out: Class Ranking {}'.format(timing['start'], race_class.id))

                current_class = {}
                current_class['id'] = race_class.id
                current_class['name'] = race_class.name
                current_class['description'] = race_class.description
                current_class['leaderboard'] = results
                current_class['ranking'] = ranking

                current_classes[race_class.id] = current_class

            timing['event'] = monotonic()
            logger.debug('T%d: results by class assembled in %.3fs', timing['start'], timing['event'] - timing['by_class'])

            gevent.sleep()
            output = self._RHData.get_results_event()
            results = output['data']
            if not output['result']:
                error_flag = True

            timing['event_end'] = monotonic()
            logger.debug('T%d: event results assembled in %.3fs', timing['start'], timing['event_end'] - timing['event'])

            payload = {
                'heats': heats,
                'heats_by_class': heats_by_class,
                'classes': current_classes,
                'event_leaderboard': results
            }

            self.set_cache(payload)
            self.set_buildToken(False)

            if error_flag:
                logger.warning('T%d: Cache results build failed; leaving page cache invalid', timing['start'])
                # *** emit_priority_message(__("Results did not load completely. Please try again."), False)
                self._Events.trigger(Evt.CACHE_FAIL)
            else:
                self.set_valid(True)
                self._Events.trigger(Evt.CACHE_READY)

            logger.debug('T%d: Page cache built in: %fs', timing['start'], monotonic() - timing['build_start'])

        timing['end'] = monotonic()

        logger.info('T%d: Built results data in: %fs', timing['start'], timing['end'] - timing['start'])

