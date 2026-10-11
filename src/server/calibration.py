'''Seat calibration adjustment'''

import logging
import json
import math
import RHUtils
from eventmanager import Evt
from RHUtils import catchLogExceptionsWrapper
from filtermanager import Flt

logger = logging.getLogger(__name__)

# Automatic EnterAt/ExitAt calibration from a seat's RSSI history.
#  'compute_laps' is the Marshal page's crossing algorithm ('computeLaps' in marshal.js); the
#  two must give the same laps for the same inputs.

AUTO_CAL = {
    'MIN_SPAN': 15,             # RSSI span below which the history holds no usable signal
    'BAND_MARGIN': 2,           # lowest EnterAt tried is this far above the trace minimum
    'SCAN_EXIT_FRACTION': 0.25, # provisional ExitAt, as a fraction of the way from EnterAt to the minimum
    'MIN_BAND': 3,              # a steady band narrower than this (or the fraction below) is not a gate
    'MIN_BAND_FRACTION': 0.05,
    'WIDE_FRACTION': 0.75,      # bands at least this wide, relative to the widest, compete on pass count
    'BAND_POSITION': 2 / 3,     # EnterAt placed this far up the steady band
    'EXIT_GAP_FRACTION': 0.24,  # usual ExitAt gap below EnterAt, as a fraction of the way to the trace minimum
    'MAX_CROSSING_S': 20,       # a crossing longer than this is not a gate pass
    'HOLESHOT_WINDOW_S': 20,    # a crossing this soon after the start is the holeshot
    'HOLESHOT_SEARCH': 12,      # how far below the band to look for a weak holeshot
    'DEFAULT_MIN_LAP_MS': 5000, # gap between crossings treated as one pass when no minimum lap is set
    'NOISE_PENALTY': 3,         # per crossing too close to the previous one
    'OPEN_PENALTY': 8,          # a crossing left open or overlong
    'MERGED_RATIO': 1.9,        # a lap this many times the median is two passes merged
    'MERGED_PENALTY': 6,
    'CURRENT_COUNT_WEIGHT': 0.5,  # per lap of difference from the laps currently recorded
}

class NoSuggestion:
    '''Why no EnterAt/ExitAt could be suggested.'''
    NOT_FOUND = 'not_found'            # no such pilot run or seat
    NO_HISTORY = 'no_history'          # no RSSI history recorded
    PASS_PEAK_ONLY = 'pass_peak_only'  # the node records only pass peaks, not an RSSI trace
    WEAK_SIGNAL = 'weak_signal'        # the trace is too flat to hold gate passes
    NO_GATE_PASSES = 'no_gate_passes'  # no steady band, so no gate passes stand out
    NO_CLEAN_EXIT = 'no_clean_exit'    # no ExitAt gives a usable set of laps

def _pass_peak_only(marshal_type):
    from BaseHardwareInterface import MarshalType  # the interface path is added after this module loads
    return marshal_type == MarshalType.PASS_PEAK_ONLY

def _js_round(value):
    # JavaScript's Math.round, which rounds halves up
    return math.floor(value + 0.5)

def compute_laps(values, times, start_time, enter_at, exit_at, unlimited_time, race_time_sec,
                 min_lap_ms, min_lap_behavior, min_first_crossing_ms):
    '''Laps the crossing algorithm gives for the history with these thresholds.'''
    last_lap_time_stamp = -math.inf
    laps = []
    crossing = False
    crossing_start = 0
    peak_rssi = 0
    peak_first = 0
    peak_last = 0
    time = 0
    for rssi, time in zip(values, times):
        if not crossing and rssi > enter_at:
            crossing = True
            crossing_start = time
        if rssi >= peak_rssi:
            peak_last = time
            if rssi > peak_rssi:
                peak_first = time
                peak_rssi = rssi
        if crossing and rssi < exit_at:
            lap_time_stamp = ((peak_last + peak_first) / 2 - start_time) * 1000  # zero stamp within race
            if lap_time_stamp > 0:  # reject passes before race start
                lap = {'crossingStart': crossing_start, 'crossingEnd': time, 'lap_time_stamp': lap_time_stamp,
                       'source': 2, 'peak_rssi': peak_rssi, 'deleted': False}  # source 2 is recalc
                if lap_time_stamp < min_first_crossing_ms:
                    lap['deleted'] = True
                    lap['noise'] = True
                elif min_lap_behavior and lap_time_stamp < last_lap_time_stamp + min_lap_ms:
                    lap['deleted'] = True
                    lap['noise'] = True
                else:
                    last_lap_time_stamp = lap_time_stamp
                laps.append(lap)
            crossing = False
            peak_rssi = 0
    if crossing:  # crossing at data end
        laps.append({'crossingStart': crossing_start, 'crossingEnd': time,
                     'lap_time_stamp': ((peak_last + peak_first) / 2 - start_time) * 1000,
                     'source': 2, 'deleted': False, 'open': True})
    # auto-delete late laps
    finished = False
    for lap in laps:
        if finished:
            lap['deleted'] = True
            lap['late'] = True
        elif not unlimited_time and lap['lap_time_stamp'] > race_time_sec * 1000:
            finished = True
    return laps

def _crossings_usable(laps):
    # a crossing that never closes, or that lasts far longer than a gate pass, is the threshold
    #  sitting in the ripple or the noise
    return not any(lap.get('open') or lap['crossingEnd'] - lap['crossingStart'] > AUTO_CAL['MAX_CROSSING_S']
                   for lap in laps)

def _count_noise_crossings(laps, min_lap_ms):
    # crossings within the minimum lap time of the previous one, plus any already deleted as such
    min_gap = min_lap_ms or AUTO_CAL['DEFAULT_MIN_LAP_MS']
    noise = 0
    last_stamp = None
    for lap in laps:
        if lap.get('noise'):
            noise += 1
        elif not lap['deleted']:
            if last_stamp is not None and lap['lap_time_stamp'] - last_stamp < min_gap:
                noise += 1
            last_stamp = lap['lap_time_stamp']
    return noise

def _has_early_crossing(laps):
    return any(not lap['deleted'] and lap['lap_time_stamp'] <= AUTO_CAL['HOLESHOT_WINDOW_S'] * 1000
               for lap in laps)

def _score_calibration(laps, min_lap_ms, current_lap_count):
    # lower is better: crossings too close together to be laps, a crossing left open or overlong,
    #  merged passes, and (lightly) a lap count away from the laps currently recorded
    score = AUTO_CAL['NOISE_PENALTY'] * _count_noise_crossings(laps, min_lap_ms)
    stamps = []
    for lap in laps:
        if lap.get('open') or lap['crossingEnd'] - lap['crossingStart'] > AUTO_CAL['MAX_CROSSING_S']:
            score += AUTO_CAL['OPEN_PENALTY']
        elif not lap['deleted']:
            stamps.append(lap['lap_time_stamp'])
    lap_times = [stamps[i] - stamps[i - 1] for i in range(1, len(stamps))]
    if len(lap_times) >= 3:
        median = sorted(lap_times)[len(lap_times) // 2]
        score += AUTO_CAL['MERGED_PENALTY'] * sum(1 for t in lap_times if t > median * AUTO_CAL['MERGED_RATIO'])
    score += AUTO_CAL['CURRENT_COUNT_WEIGHT'] * abs(len(stamps) - current_lap_count)
    return score

def suggest_calibration(values, times, start_time, unlimited_time, race_time_sec, min_lap_ms,
                        min_lap_behavior, min_first_crossing_ms, current_lap_count=0):
    '''EnterAt/ExitAt from the RSSI history: the widest run of EnterAt values over which the pass
       count holds steady is the gate band, between the weakest pass and the ripple. Returns
       {'enter_at', 'exit_at', 'laps', 'lap_count', 'band'} or None when no band stands out.'''
    return suggest_calibration_with_reason(values, times, start_time, unlimited_time, race_time_sec,
                                           min_lap_ms, min_lap_behavior, min_first_crossing_ms,
                                           current_lap_count)[0]

def suggest_calibration_with_reason(values, times, start_time, unlimited_time, race_time_sec, min_lap_ms,
                                    min_lap_behavior, min_first_crossing_ms, current_lap_count=0):
    '''As suggest_calibration(), returning (suggestion, None) or (None, NoSuggestion reason).'''
    if len(values) < 3 or len(values) != len(times):
        return None, NoSuggestion.NO_HISTORY
    lo = min(values)
    hi = max(values)
    if hi - lo < AUTO_CAL['MIN_SPAN']:
        return None, NoSuggestion.WEAK_SIGNAL
    def laps_for(enter, exit_at):
        return compute_laps(values, times, start_time, enter, exit_at, unlimited_time, race_time_sec,
                            min_lap_ms, min_lap_behavior, min_first_crossing_ms)
    def pass_count(laps):
        return len([lap for lap in laps if not lap.get('late')]) - _count_noise_crossings(laps, min_lap_ms)
    scan = {}
    plateaus = []
    run = None
    for enter in range(hi - 1, lo + AUTO_CAL['BAND_MARGIN'], -1):
        # a wide provisional ExitAt, so the bumps after a pass stay inside its crossing
        laps = laps_for(enter, enter - max(1, _js_round((enter - lo) * AUTO_CAL['SCAN_EXIT_FRACTION'])))
        scan[enter] = laps
        if not laps or not _crossings_usable(laps):
            run = None
            continue
        # passes and merged crossings must both hold for the band to continue; laps after the
        #  race come and go with the landing, so they are left out
        noise = _count_noise_crossings(laps, min_lap_ms)
        count = len([lap for lap in laps if not lap.get('late')]) - noise
        if run and run['count'] == count and run['noise'] == noise:
            run['low'] = enter
        else:
            run = {'count': count, 'noise': noise, 'high': enter, 'low': enter}
            plateaus.append(run)
    # among the bands nearly as wide as the widest, the one with the most passes: a wide lower
    #  band holds weaker real passes, since ripple would have broken it up
    widest = max((p['high'] - p['low'] for p in plateaus), default=0)
    band = None
    for p in plateaus:
        if p['high'] - p['low'] >= widest * AUTO_CAL['WIDE_FRACTION'] and (band is None or p['count'] > band['count']):
            band = p  # the first found at a count is the higher, keeping more margin over the noise
    if band is None or band['high'] - band['low'] < max(AUTO_CAL['MIN_BAND'], (hi - lo) * AUTO_CAL['MIN_BAND_FRACTION']):
        return None, NoSuggestion.NO_GATE_PASSES
    enter = band['low'] + _js_round((band['high'] - band['low']) * AUTO_CAL['BAND_POSITION'])
    # a weak holeshot peaks at the top of the ripple; with no early crossing in the band, step
    #  down to the first EnterAt that adds exactly one, early, and keeps the set clean
    if not _has_early_crossing(scan[enter]):
        base_score = _score_calibration(scan[enter], min_lap_ms, current_lap_count)
        for e in range(band['low'] - 1, band['low'] - AUTO_CAL['HOLESHOT_SEARCH'] - 1, -1):
            if e not in scan:
                break
            if pass_count(scan[e]) == band['count'] + 1 and _has_early_crossing(scan[e]) and \
                    _crossings_usable(scan[e]) and _score_calibration(scan[e], min_lap_ms, current_lap_count) <= base_score:
                enter = e
                break
    # ExitAt: of the values giving the cleanest laps (clear of the valleys within a crossing and
    #  above the lowest point of any lap), the one nearest the usual gap below EnterAt
    cleanest = []
    best_score = math.inf
    for exit_at in range(enter - 1, lo, -1):
        laps = laps_for(enter, exit_at)
        if not _crossings_usable(laps):
            continue
        score = _score_calibration(laps, min_lap_ms, current_lap_count)
        if score < best_score:
            best_score = score
            cleanest = []
        if score == best_score:
            cleanest.append(exit_at)
    if not cleanest:
        return None, NoSuggestion.NO_CLEAN_EXIT
    target = enter - _js_round((enter - lo) * AUTO_CAL['EXIT_GAP_FRACTION'])
    exit_at = cleanest[0]
    for candidate in cleanest[1:]:
        if abs(candidate - target) < abs(exit_at - target):
            exit_at = candidate
    laps = laps_for(enter, exit_at)
    return {'enter_at': enter, 'exit_at': exit_at, 'laps': laps,
            'lap_count': len([lap for lap in laps if not lap['deleted']]), 'band': [band['low'], band['high']]}, None

class Calibration:
    def __init__(self, racecontext):
        self._racecontext = racecontext

    @catchLogExceptionsWrapper
    def set_enter_at_level(self, seat_index, enter_at_level_input, emit_levels=True):
        '''Set node enter-at level.'''
        enter_at_level = int(enter_at_level_input or 0)

        if seat_index < 0 or seat_index >= self._racecontext.race.num_nodes:
            logger.info('Unable to set enter-at ({0}) on node {1}; node index out of range'.format(enter_at_level, seat_index+1))
            return

        if not enter_at_level:
            logger.info('Node enter-at set null; getting from node: Node {0}'.format(seat_index+1))
            enter_at_level = self._racecontext.interface.nodes[seat_index].enter_at_level

        profile = self._racecontext.race.profile
        enter_ats = json.loads(profile.enter_ats)

        # handle case where more nodes were added
        while seat_index >= len(enter_ats["v"]):
            enter_ats["v"].append(None)

        enter_ats["v"][seat_index] = enter_at_level

        profile = self._racecontext.rhdata.alter_profile({
            'profile_id': profile.id,
            'enter_ats': enter_ats
            })
        self._racecontext.race.profile = profile

        self._racecontext.interface.set_enter_at_level(seat_index, enter_at_level)

        self._racecontext.events.trigger(Evt.ENTER_AT_LEVEL_SET, {
            'nodeIndex': seat_index,
            'enter_at_level': enter_at_level,
            })

        logger.info('Node enter-at set: Node {0} Level {1}'.format(seat_index+1, enter_at_level))
        if emit_levels:
            self._racecontext.rhui.emit_enter_and_exit_at_levels()

    @catchLogExceptionsWrapper
    def set_exit_at_level(self, seat_index, exit_at_level_input, emit_levels=True):
        '''Set node exit-at level.'''
        exit_at_level = int(exit_at_level_input or 0)

        if seat_index < 0 or seat_index >= self._racecontext.race.num_nodes:
            logger.info('Unable to set exit-at ({0}) on node {1}; node index out of range'.format(exit_at_level, seat_index+1))
            return

        if not exit_at_level:
            logger.info('Node exit-at set null; getting from node: Node {0}'.format(seat_index+1))
            exit_at_level = self._racecontext.interface.nodes[seat_index].exit_at_level

        profile = self._racecontext.race.profile
        exit_ats = json.loads(profile.exit_ats)

        # handle case where more nodes were added
        while seat_index >= len(exit_ats["v"]):
            exit_ats["v"].append(None)

        exit_ats["v"][seat_index] = exit_at_level

        profile = self._racecontext.rhdata.alter_profile({
            'profile_id': profile.id,
            'exit_ats': exit_ats
            })
        self._racecontext.race.profile = profile

        self._racecontext.interface.set_exit_at_level(seat_index, exit_at_level)

        self._racecontext.events.trigger(Evt.EXIT_AT_LEVEL_SET, {
            'nodeIndex': seat_index,
            'exit_at_level': exit_at_level,
            })

        logger.info('Node exit-at set: Node {0} Level {1}'.format(seat_index+1, exit_at_level))
        if emit_levels:
            self._racecontext.rhui.emit_enter_and_exit_at_levels()

    def hardware_set_all_enter_ats(self, enter_at_levels):
        '''send update to nodes'''
        logger.debug("Sending enter-at values to nodes: " + str(enter_at_levels))
        for idx in range(self._racecontext.race.num_nodes):
            if enter_at_levels[idx]:
                self._racecontext.interface.set_enter_at_level(idx, enter_at_levels[idx])
            else:
                self.set_enter_at_level(idx, self._racecontext.interface.nodes[idx].enter_at_level)

    def hardware_set_all_exit_ats(self, exit_at_levels):
        '''send update to nodes'''
        logger.debug("Sending exit-at values to nodes: " + str(exit_at_levels))
        for idx in range(self._racecontext.race.num_nodes):
            if exit_at_levels[idx]:
                self._racecontext.interface.set_exit_at_level(idx, exit_at_levels[idx])
            else:
                self.set_exit_at_level(idx, self._racecontext.interface.nodes[idx].exit_at_level)

    def auto_calibrate(self):
        ''' Apply best tuning values to nodes '''
        if self._racecontext.race.current_heat == RHUtils.HEAT_ID_NONE:
            logger.debug('Skipping auto calibration; server in practice mode')
            return None

        for seat_index, node in enumerate(self._racecontext.interface.nodes):
            calibration = self.find_best_calibration_values(node, seat_index)

            if node.enter_at_level is not calibration['enter_at_level']:
                self.set_enter_at_level(seat_index, calibration['enter_at_level'], emit_levels=False)

            if node.exit_at_level is not calibration['exit_at_level']:
                self.set_exit_at_level(seat_index, calibration['exit_at_level'], emit_levels=False)

        logger.info('Updated calibration with best discovered values')
        self._racecontext.rhui.emit_enter_and_exit_at_levels()  # one broadcast for all nodes

    def find_best_calibration_values(self, node, seat_index):
        ''' Search race history for best tuning values '''

        # get commonly used values
        heat = self._racecontext.rhdata.get_heat(self._racecontext.race.current_heat)
        pilot = self._racecontext.rhdata.get_pilot_from_heatNode(self._racecontext.race.current_heat, seat_index)
        current_class = heat.class_id
        races = self._racecontext.rhdata.get_savedRaceMetas()
        races.sort(key=lambda x: x.id, reverse=True)
        pilotRaces = self._racecontext.rhdata.get_savedPilotRaces()
        pilotRaces.sort(key=lambda x: x.id, reverse=True)

        # test for disabled node
        if pilot is RHUtils.PILOT_ID_NONE or node.frequency is RHUtils.FREQUENCY_ID_NONE:
            logger.debug('Node {0} calibration: skipping disabled node'.format(node.index+1))
            return {
                'enter_at_level': node.enter_at_level,
                'exit_at_level': node.exit_at_level
            }

        # test for same heat, same node
        for race in races:
            if race.heat_id == heat.id:
                for pilotRace in pilotRaces:
                    if pilotRace.race_id == race.id and \
                        pilotRace.node_index == seat_index and \
                        pilotRace.frequency == node.frequency:
                        logger.debug('Node {0} calibration: found same pilot+node in same heat'.format(node.index+1))
                        return {
                            'enter_at_level': pilotRace.enter_at,
                            'exit_at_level': pilotRace.exit_at
                        }
                break

        # test for same class, same pilot, same node
        for race in races:
            if race.class_id == current_class:
                for pilotRace in pilotRaces:
                    if pilotRace.race_id == race.id and \
                        pilotRace.node_index == seat_index and \
                        pilotRace.pilot_id == pilot and \
                        pilotRace.frequency == node.frequency:
                        logger.debug('Node {0} calibration: found same pilot+node in other heat with same class'.format(node.index+1))
                        return {
                            'enter_at_level': pilotRace.enter_at,
                            'exit_at_level': pilotRace.exit_at
                        }
                break

        # test for same pilot, same node
        for pilotRace in pilotRaces:
            if pilotRace.node_index == seat_index and \
                pilotRace.pilot_id == pilot and \
                pilotRace.frequency == node.frequency:
                logger.debug('Node {0} calibration: found same pilot+node in other heat with other class'.format(node.index+1))
                return {
                    'enter_at_level': pilotRace.enter_at,
                    'exit_at_level': pilotRace.exit_at
                }

        # test for same node
        for pilotRace in pilotRaces:
            if pilotRace.node_index == seat_index and \
                pilotRace.frequency == node.frequency:
                logger.debug('Node {0} calibration: found same node in other heat'.format(node.index+1))
                return {
                    'enter_at_level': pilotRace.enter_at,
                    'exit_at_level': pilotRace.exit_at
                }

        # fallback
        logger.debug('Node {0} calibration: no calibration hints found, no change'.format(node.index+1))
        context = {
            'seat_index': seat_index,
            'pilot': pilot,
            'enter_at_level': node.enter_at_level,
            'exit_at_level': node.exit_at_level
        }
        context = self._racecontext.filters.run_filters(Flt.CALIBRATION_FALLBACK, context, {
            'heat_id': heat.id,
            'pilot_id': pilot,
            'class_id': heat.class_id
        })
        return {
            'enter_at_level': context['enter_at_level'],
            'exit_at_level': context['exit_at_level']
        }
    

    def suggest_for_pilotrun(self, pilotrace_id):
        '''Suggested EnterAt/ExitAt for a saved pilot run: (suggestion, None) or (None, NoSuggestion reason).'''
        rhdata = self._racecontext.rhdata
        pilotrace = rhdata.get_savedPilotRace(pilotrace_id)
        race_meta = rhdata.get_savedRaceMeta(pilotrace.race_id) if pilotrace else None
        if not race_meta:
            return None, NoSuggestion.NOT_FOUND
        if _pass_peak_only(pilotrace.marshal_type):
            return None, NoSuggestion.PASS_PEAK_ONLY
        if not pilotrace.history_values:
            return None, NoSuggestion.NO_HISTORY
        # a secondary timer saves its races with no format
        race_format = rhdata.get_raceFormat(race_meta.format_id)
        laps = rhdata.get_active_savedRaceLaps_by_savedPilotRace(pilotrace_id)
        return self._suggest(json.loads(pilotrace.history_values), json.loads(pilotrace.history_times),
                             race_meta.start_time, race_format, len(laps))

    def suggest_for_seat(self, seat_index):
        '''Suggested EnterAt/ExitAt for a seat in the current (stopped, unsaved) race: (suggestion, None) or (None, reason).'''
        race = self._racecontext.race
        if seat_index < 0 or seat_index >= race.num_nodes:
            return None, NoSuggestion.NOT_FOUND
        node = self._racecontext.interface.nodes[seat_index]
        if _pass_peak_only(self._racecontext.interface.node_map[seat_index].interface.marshal_type):
            return None, NoSuggestion.PASS_PEAK_ONLY
        laps = [lap for lap in race.node_laps.get(seat_index, []) if not lap.deleted]
        return self._suggest(node.history_values, node.history_times, race.start_time_monotonic,
                             race.format, len(laps))

    def _suggest(self, values, times, start_time, race_format, current_lap_count):
        rhdata = self._racecontext.rhdata
        # with no format there is no race time, so no laps count as late
        unlimited_time = race_format.unlimited_time if race_format else True
        race_time_sec = race_format.race_time_sec if race_format else 0
        result, reason = suggest_calibration_with_reason(values, times, start_time, unlimited_time, race_time_sec,
                                     rhdata.get_optionInt('MinLapSec') * 1000,
                                     self._racecontext.serverconfig.get_item_int('TIMING', 'MinLapBehavior'),
                                     rhdata.get_optionInt('MinFirstCrossingSec') * 1000,
                                     current_lap_count)
        if result:
            logger.debug('Calibration suggestion: EnterAt {}, ExitAt {}, band {}-{}, {} laps'.format(
                result['enter_at'], result['exit_at'], result['band'][0], result['band'][1], result['lap_count']))
        else:
            logger.debug('No calibration suggestion: {}'.format(reason))
        return result, reason
