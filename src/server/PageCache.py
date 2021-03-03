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
import json
import Results
import RHUtils
import gevent

logger = logging.getLogger(__name__)

import Database
from flask_sqlalchemy import SQLAlchemy
DB = SQLAlchemy()

class PageCache:
    def __init__(self, RHData, Events):
        self._RHData = RHData
        self._Events = Events
        self._cache = {} # Cache of complete results page
        self._buildToken = False # Time of result generation or false if no results are being calculated
        self._valid = False # Whether cache is valid

    def get_cache(self):
        if self._valid: # Output existing calculated results
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

    def update_cache(self):
        '''Builds any invalid atomic result caches and creates final output'''
        timing = {
            'start': monotonic()
        }
        logger.debug('T%d: Result data build started', timing['start'])

        CACHE_TIMEOUT = 10
        expires = monotonic() + CACHE_TIMEOUT
        error_flag = False

        if self._buildToken: # Don't restart calculation if another calculation thread exists
            while True: # Pause this thread until calculations are completed
                gevent.idle()
                if self._buildToken is False:
                    break
                elif monotonic() > self._buildToken + CACHE_TIMEOUT:
                    logger.warning('T%d: Timed out waiting for other cache build thread', timing['start'])
                    self._buildToken = False
                    break

        if self._valid: # Output existing calculated results
            logger.info('T%d: Returning valid cache', timing['start'])

        else:
            timing['build_start'] = monotonic()
            self._buildToken = monotonic()

            heats = {}
            for heat in Database.SavedRaceMeta.query.with_entities(Database.SavedRaceMeta.heat_id).distinct().order_by(Database.SavedRaceMeta.heat_id):
                heatdata = self._RHData.get_heat(heat.heat_id)

                rounds = []
                for round in Database.SavedRaceMeta.query.distinct().filter_by(heat_id=heat.heat_id).order_by(Database.SavedRaceMeta.round_id):

                    if Database.SavedRaceLap.query.filter_by(race_id=round.id).first() is not None:
                        pilotraces = []
                        for pilotrace in Database.SavedPilotRace.query.filter_by(race_id=round.id).all():
                            gevent.sleep()
                            laps = []
                            for lap in Database.SavedRaceLap.query.filter_by(pilotrace_id=pilotrace.id).all():
                                laps.append({
                                    'id': lap.id,
                                    'lap_time_stamp': lap.lap_time_stamp,
                                    'lap_time': lap.lap_time,
                                    'lap_time_formatted': lap.lap_time_formatted,
                                    'source': lap.source,
                                    'deleted': lap.deleted
                                })

                            pilot_data = Database.Pilot.query.filter_by(id=pilotrace.pilot_id).first()
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
                        if round.cacheStatus == Results.CacheStatus.INVALID:
                            logger.info('Rebuilding Heat %d Round %d cache', heat.heat_id, round.round_id)
                            results = Results.calc_leaderboard(self._RHData, heat_id=heat.heat_id, round_id=round.round_id)
                            round.results = results
                            round.cacheStatus = Results.CacheStatus.VALID
                            DB.session.commit()
                        else:
                            expires = monotonic() + CACHE_TIMEOUT
                            while True:
                                gevent.idle()
                                if round.cacheStatus == Results.CacheStatus.VALID:
                                    results = round.results
                                    break
                                elif monotonic() > expires:
                                    logger.warning('T%d: Cache build timed out: Heat %d Round %d', timing['start'], heat.heat_id, round.round_id)
                                    results = None
                                    error_flag = True
                                    break

                        rounds.append({
                            'id': round.round_id,
                            'start_time_formatted': round.start_time_formatted,
                            'nodes': pilotraces,
                            'leaderboard': results
                        })

                if heatdata.cacheStatus == Results.CacheStatus.INVALID:
                    logger.info('Rebuilding Heat %d cache', heat.heat_id)
                    results = Results.calc_leaderboard(self._RHData, heat_id=heat.heat_id)
                    heatdata.results = results
                    heatdata.cacheStatus = Results.CacheStatus.VALID
                    DB.session.commit()
                else:
                    checkStatus = True
                    expires = monotonic() + CACHE_TIMEOUT
                    while True:
                        gevent.idle()
                        if heatdata.cacheStatus == Results.CacheStatus.VALID:
                            results = heatdata.results
                            break
                        elif monotonic() > expires:
                            logger.warning('T%d: Cache build timed out: Heat Summary %d', timing['start'], heat.heat_id)
                            results = None
                            error_flag = True
                            break

                heats[heat.heat_id] = {
                    'heat_id': heat.heat_id,
                    'note': heatdata.note,
                    'rounds': rounds,
                    'leaderboard': results
                }

            timing['round_results'] = monotonic()
            logger.debug('T%d: round results assembled in %.3fs', timing['start'], timing['round_results'] - timing['build_start'])

            gevent.sleep()
            heats_by_class = {}
            heats_by_class[RHUtils.CLASS_ID_NONE] = [heat.id for heat in Database.Heat.query.filter_by(class_id=RHUtils.CLASS_ID_NONE).all()]
            for race_class in self._RHData.get_raceClasses():
                heats_by_class[race_class.id] = [heat.id for heat in Database.Heat.query.filter_by(class_id=race_class.id).all()]

            timing['by_class'] = monotonic()

            gevent.sleep()
            current_classes = {}
            for race_class in self._RHData.get_raceClasses():
                if race_class.cacheStatus == Results.CacheStatus.INVALID:
                    logger.info('Rebuilding Class %d cache', race_class.id)
                    results = Results.calc_leaderboard(self._RHData, class_id=race_class.id)
                    race_class.results = results
                    race_class.cacheStatus = Results.CacheStatus.VALID
                    DB.session.commit()
                else:
                    checkStatus = True
                    expires = monotonic() + CACHE_TIMEOUT
                    while True:
                        gevent.idle()
                        if race_class.cacheStatus == Results.CacheStatus.VALID:
                            results = race_class.results
                            break
                        elif monotonic() > expires:
                            logger.warning('T%d: Cache build timed out: Class Summary %d', timing['start'], race_class.id)
                            results = None
                            error_flag = True
                            break

                current_class = {}
                current_class['id'] = race_class.id
                current_class['name'] = race_class.name
                current_class['description'] = race_class.name
                current_class['leaderboard'] = results
                current_classes[race_class.id] = current_class

            timing['event'] = monotonic()
            logger.debug('T%d: results by class assembled in %.3fs', timing['start'], timing['event'] - timing['by_class'])

            gevent.sleep()
            if self._RHData.get_option("eventResults_cacheStatus") == Results.CacheStatus.INVALID:
                logger.info('Rebuilding Event cache')
                results = Results.calc_leaderboard(self._RHData)
                self._RHData.set_option("eventResults", json.dumps(results))
                self._RHData.set_option("eventResults_cacheStatus", Results.CacheStatus.VALID)
                DB.session.commit()
            else:
                expires = monotonic() + CACHE_TIMEOUT
                while True:
                    gevent.idle()
                    status = self._RHData.get_option("eventResults_cacheStatus")
                    if status == Results.CacheStatus.VALID:
                        results = json.loads(self._RHData.get_option("eventResults"))
                        break
                    elif monotonic() > expires:
                        logger.warning('Cache build timed out: Event Summary')
                        results = None
                        error_flag = True
                        break

            timing['event_end'] = monotonic()
            logger.debug('T%d: event results assembled in %.3fs', timing['start'], timing['event_end'] - timing['event'])

            payload = {
                'heats': heats,
                'heats_by_class': heats_by_class,
                'classes': current_classes,
                'event_leaderboard': results
            }

            self._cache = payload
            self._buildToken = False

            if error_flag:
                logger.warning('T%d: Cache results build failed; leaving page cache invalid', timing['start'])
                # *** emit_priority_message(__("Results did not load completely. Please try again."), False)
                self._Events.trigger(Evt.CACHE_FAIL)
            else:
                self._valid = True
                self._Events.trigger(Evt.CACHE_READY)

            logger.debug('T%d: Page cache built in: %fs', timing['start'], monotonic() - timing['build_start'])

        timing['end'] = monotonic()

        logger.info('T%d: Built results data in: %fs', timing['start'], timing['end'] - timing['start'])

