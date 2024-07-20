'''
Page Cache

Stores cached results objects assembled via the Results module and database
lap lists. If valid, served directly to results without rebuilding.
buildToken is a monotonic timestamp so in-progress builds can be interrupted
if new data becomes available during the build process.

'''

import logging
from time import monotonic
from eventmanager import Evt
import RHUtils
import gevent

logger = logging.getLogger(__name__)

import FlaskAppObj
FlaskAppObj.APP.app_context().push()

class PageCache:
    _CACHE_TIMEOUT = 100

    def __init__(self, RaceContext, Events):
        self._racecontext = RaceContext
        self._Events = Events
        self._cache = {} # Cache of complete results page
        self._buildToken = False # Time of result generation or false if no results are being calculated
        self._valid = False # Whether cache is valid
        self._inUpdateCacheFlag = False

    def get_cache(self):
        if self.get_valid(): # Output existing calculated results
            logger.debug('Getting results from cache')
            return self._cache
        else:
            with self._racecontext.rhdata.get_db_session_handle():
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
            gevent.sleep(0.001)
            if self.get_buildToken() is True:
                while True: # Pause this thread until calculations are completed
                    gevent.sleep(0.25)
                    if self.get_buildToken() is False:
                        break
                    elif monotonic() > self.get_buildToken() + self._CACHE_TIMEOUT:
                        logger.warning('T%d: Timed out waiting for other cache build thread', timing['start'])
                        self.set_buildToken(False)
                        break

    def update_cache(self):
        dbg_trace_str = ""
        if logger.getEffectiveLevel() <= logging.DEBUG:  # if DEBUG msgs actually being logged
            dbg_trace_str = RHUtils.getFnTracebackMsgStr("update_cache")
            logger.debug("Entered 'update_cache()', called from: {}".format(dbg_trace_str))
            dbg_trace_str = " (called from: {})".format(dbg_trace_str)
        if self._inUpdateCacheFlag:
            logger.info("Waiting for previous invocation of 'update_cache()' to finish{}".format(dbg_trace_str))
            wait_count = 0
            while True:
                gevent.sleep(0.05)
                if not self._inUpdateCacheFlag:
                    logger.info("Previous invocation of 'update_cache()' finished; continuing{}".format(dbg_trace_str))
                    break
                wait_count += 1
                if wait_count > 6000:
                    logger.error("Timeout waiting for previous invocation of 'update_cache()' to finish{}".format(dbg_trace_str))
                    break
        self._inUpdateCacheFlag = True
        try:
            uc_result = self._do_update_cache()
        finally:
            self._inUpdateCacheFlag = False
        if logger.getEffectiveLevel() <= logging.DEBUG:  # if DEBUG msgs actually being logged
            logger.debug("Exiting 'update_cache()'{}".format(dbg_trace_str))
        return uc_result

    def _do_update_cache(self):
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
            for heat in self._racecontext.rhdata.get_heats():
                if self._racecontext.rhdata.savedRaceMetas_has_heat(heat.id):
                    rounds = []
                    for race in self._racecontext.rhdata.get_savedRaceMetas_by_heat(heat.id):    
                        pilotraces = []
                        for pilotrace in self._racecontext.rhdata.get_savedPilotRaces_by_savedRaceMeta(race.id):
                            gevent.sleep(0.001)
                            laps = []
                            for lap in self._racecontext.rhdata.get_savedRaceLaps_by_savedPilotRace(pilotrace.id):
                                laps.append({
                                    'id': lap.id,
                                    'lap_time_stamp': lap.lap_time_stamp,
                                    'lap_time': lap.lap_time,
                                    'lap_time_formatted': lap.lap_time_formatted,
                                    'source': lap.source,
                                    'deleted': lap.deleted
                                })

                            pilot_data = self._racecontext.rhdata.get_pilot(pilotrace.pilot_id)
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

                        results = self._racecontext.rhdata.get_results_savedRaceMeta(race)
                        rounds.append({
                            'id': race.round_id,
                            'start_time_formatted': race.start_time_formatted,
                            'nodes': pilotraces,
                            'leaderboard': results
                        })

                    results = self._racecontext.rhdata.get_results_heat(heat)
                    heats[heat.id] = {
                        'heat_id': heat.id,
                        'displayname': heat.display_name,
                        'rounds': rounds,
                        'leaderboard': results
                    }

            timing['round_results'] = monotonic()
            logger.debug('T%d: heat_round results assembled in %.3fs', timing['start'], timing['round_results'] - timing['build_start'])

            gevent.sleep(0.001)
            heats_by_class = {}
            heats_by_class[RHUtils.CLASS_ID_NONE] = [heat.id for heat in self._racecontext.rhdata.get_heats_by_class(RHUtils.CLASS_ID_NONE)]
            for race_class in self._racecontext.rhdata.get_raceClasses():
                heats_by_class[race_class.id] = [heat.id for heat in self._racecontext.rhdata.get_heats_by_class(race_class.id)]

            timing['by_class'] = monotonic()

            gevent.sleep(0.001)
            current_classes = {}
            for race_class in self._racecontext.rhdata.get_raceClasses():
                results = self._racecontext.rhdata.get_results_raceClass(race_class)
                ranking = self._racecontext.rhdata.get_ranking_raceClass(race_class)
                current_class = {}
                current_class['id'] = race_class.id
                current_class['name'] = race_class.name
                current_class['description'] = race_class.description
                current_class['leaderboard'] = results
                current_class['ranking'] = ranking

                current_classes[race_class.id] = current_class

            timing['event'] = monotonic()
            logger.debug('T%d: results by class assembled in %.3fs', timing['start'], timing['event'] - timing['by_class'])

            gevent.sleep(0.001)
            results = self._racecontext.rhdata.get_results_event()

            timing['event_end'] = monotonic()
            logger.debug('T%d: event results assembled in %.3fs', timing['start'], timing['event_end'] - timing['event'])

            payload = {
                'heats': heats,
                'heats_by_class': heats_by_class,
                'classes': current_classes,
                'event_leaderboard': results,
                'consecutives_count': self._racecontext.rhdata.get_optionInt('consecutivesCount', 3)
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

        timing['end'] = monotonic()

        logger.info('T%d: Built results data in: %fs', timing['start'], timing['end'] - timing['start'])
        return not error_flag
