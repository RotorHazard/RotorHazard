'''Seat calibration adjustment'''

import logging
import json
import bisect
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
    'MIN_REGULAR_BAND_FRACTION': 0.04,  # or of the way from the band to the trace minimum, for passes at a regular pace
    'NARROW_BAND_NOISE_FRACTION': 0.05,  #  with noise crossings at most this fraction of its passes
    'WIDE_FRACTION': 0.75,      # bands at least this wide, relative to the widest, compete on pass count
    'BAND_POSITION': 2 / 3,     # EnterAt placed this far up the steady band,
    'PEAK_MARGIN_FRACTION': 0.1,  #  but at least this fraction of the weakest pass's peak below it,
    'PEAK_MARGIN_SPAN_FRACTION': 0.2,  #  or this fraction of the way from that peak to the minimum, if less
    'MIN_EXIT_GAP': 3,          # smallest gap of ExitAt below EnterAt
    'MIN_EXIT_GAP_FRACTION': 0.1,  # or this fraction of the way from EnterAt to the trace minimum
    'EXIT_TOP_MARGIN_FRACTION': 0.05,  # ExitAt this fraction of the way to the trace minimum below the top of the clean range
    'EXIT_GAP_FRACTION': 0.3,   # but at least this fraction of the way from EnterAt to the trace minimum, within the clean range
    'EXIT_SPAN_FRACTION': 0.19, # or this fraction of the trace span,
    'EXIT_SPAN_CAP_FRACTION': 0.4,  # up to this fraction of the way from EnterAt to the trace minimum
    'MIN_EXIT_GAP_OF_ENTER': 0.1,   # ExitAt at least this fraction of EnterAt below it, within the clean range,
    'MIN_EXIT_GAP_OF_ENTER_FALLBACK': 0.05,  #  or this fraction when the clean range cannot hold that,
    'FALLBACK_MIN_SPAN': 30,    #  on a trace spanning at least this much
    'MAX_CROSSING_S': 20,       # a crossing longer than this is not a gate pass
    'MAX_PASS_CROSSING_S': 3,   # with no pass crossing shorter than this, there is no suggestion
    'CUT_ROUNDS': 20,           # most times bad crossings below the band are cut out and the suggestion found again
    'STEP_SPACING_FRACTION': 0.75,  # a pass a step below the band adds is at least this fraction of a typical lap from the others
    'EARLY_END_S': 1,               # a recording ending this long before the race time was stopped early
    'STEP_REACH_FRACTION': 0.5,     # steps below the band are taken when they reach this fraction of its width below it
    'HOLESHOT_WINDOW_S': 20,    # a crossing this soon after the start is the holeshot
    'HOLESHOT_SEARCH': 12,      # how far below the band to look for a weak holeshot
    'HOLESHOT_MATCH_S': 1,      # the passes after a stepped-down holeshot stay this close to the band's
    'DEFAULT_MIN_LAP_MS': 5000, # gap between crossings treated as one pass when no minimum lap is set,
                                #  and the least gap for noise at the end of the recording
    'NOISE_PENALTY': 3,         # per crossing too close to the previous one
    'OPEN_PENALTY': 8,          # a crossing left open or overlong
    'MERGED_RATIO': 1.9,        # a lap this many times the median is two passes merged
    'MERGED_PENALTY': 6,
    'TYPICAL_LAP_MIN_CROSSINGS': 8,     # crossings needed to estimate the typical lap,
    'TYPICAL_LAP_SPREAD': 2,            #  with the longer quartile lap at most this many times the shorter
    'MIN_LAP_TOO_LONG_FRACTION': 0.75,  # a minimum lap longer than this fraction of the typical lap is
                                        #  replaced by half the typical lap
    'CLEAN_PEAK_WINDOW_S': 1,   # around a crossing, the signal should rise past halfway to its peak only once
    'BELL_DROP_FRACTION': 0.2,  # with no band, a peak above halfway up the trace that falls this fraction of the way
    'BELL_SIDE_S': 2,           #  to the minimum on both sides within this time,
    'BELL_TOLERANCE_FRACTION': 0.1,  #  without rising again by more than this fraction, is a clean peak;
    'BELL_PASS_FRACTION': 0.9,  #  clean peaks this far up to their median are the passes,
    'BELL_ENTER_FRACTION': 0.015,  #  and EnterAt is this fraction of the weakest of them below it,
    'BELL_ENTER_MIN': 2,        #  and at least this much; EnterAt then goes lower while it only adds clean peaks,
    'BELL_PASS_LOSS_FRACTION': 0.05,  #  and a lower ExitAt may lose at most this fraction of the passes
    'DOUBLE_WINDOW_S': 1.0,     # a crossing this close to a stronger one is a second bump of the same pass
    'TRAILING_NOISE_WINDOW_S': 5,  # noise crossings after the last pass this close to the end of the recording are ignored
    'LANDING_SHORT_RATIO': 0.6, # in a race with no time limit, trailing laps shorter than this many medians,
    'LANDING_LONG_RATIO': 2.5,  #  or longer than this many, are the landing after the race
    'DURATION_WEIGHT': 1.0,     # per second of crossing time over all counted crossings
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

def _lap_limit(race_format):
    # in an individual first-to-laps race the pilot is done at the winning lap, counted from the
    #  holeshot unless the format starts on the first lap
    from RHRace import RacingMode, StartBehavior, WinCondition  # imported here as RHRace imports much of the server
    if not race_format or race_format.team_racing_mode != RacingMode.INDIVIDUAL or \
            race_format.win_condition != WinCondition.FIRST_TO_LAP_X or not race_format.number_laps_win:
        return 0
    return race_format.number_laps_win + (0 if race_format.start_behavior == StartBehavior.FIRST_LAP else 1)

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

def _regular_lap_times(stamps):
    # (median lap, whether the longer quartile lap is within the spread of the shorter)
    lap_times = sorted(b - a for a, b in zip(stamps, stamps[1:]))
    if len(lap_times) < AUTO_CAL['TYPICAL_LAP_MIN_CROSSINGS'] - 1:
        return None, False
    return (lap_times[len(lap_times) // 2],
            lap_times[len(lap_times) * 3 // 4] <= lap_times[len(lap_times) // 4] * AUTO_CAL['TYPICAL_LAP_SPREAD'])

def _without_doubles(laps):
    # a crossing this close to a stronger one is a second bump of the same pass
    window = AUTO_CAL['DOUBLE_WINDOW_S'] * 1000
    candidates = [lap for lap in laps if (not lap['deleted'] or lap.get('noise')) and not _after_race(lap)]
    def rank(lap):
        return (not lap['deleted'], lap.get('peak_rssi', 0), -lap['lap_time_stamp'])
    doubles = {id(lap) for lap in candidates for other in candidates
               if other is not lap and abs(other['lap_time_stamp'] - lap['lap_time_stamp']) <= window
               and rank(other) > rank(lap)}
    return [lap for lap in laps if id(lap) not in doubles]

def _mark_after_lap_limit(laps, lap_limit):
    # crossings after the pilot's last counted lap in a first-to-laps race, deleted ones included,
    #  are after the race
    count = 0
    for lap in laps:
        if count >= lap_limit:
            lap['deleted'] = True
            lap['late'] = True
        elif not lap['deleted']:
            count += 1

def _mark_trailing_noise(laps, min_lap_ms, end_ms):
    # crossings within the minimum lap time of any crossing before, after the last pass and near the
    #  end of the recording, are the landing or the signal settling
    min_gap = max(min_lap_ms, AUTO_CAL['DEFAULT_MIN_LAP_MS'])
    flagged = []
    last_stamp = None
    for lap in laps:
        if lap.get('late') or (lap['deleted'] and not lap.get('noise')):
            continue
        flagged.append((lap, lap.get('noise') or
                        (last_stamp is not None and lap['lap_time_stamp'] - last_stamp < min_gap)))
        last_stamp = lap['lap_time_stamp']
    window_start = end_ms - AUTO_CAL['TRAILING_NOISE_WINDOW_S'] * 1000
    while flagged and flagged[-1][1] and flagged[-1][0]['lap_time_stamp'] >= window_start:
        lap = flagged.pop()[0]
        lap['deleted'] = True
        lap['late'] = True
        lap['landing'] = True

def _mark_landing(laps):
    # with no time limit, the crossings after the last lap of ordinary length are the landing
    counted = [lap for lap in laps if not lap['deleted']]
    lap_times = [counted[i]['lap_time_stamp'] - counted[i - 1]['lap_time_stamp'] for i in range(1, len(counted))]
    if len(lap_times) < 3:
        return
    median = sorted(lap_times)[len(lap_times) // 2]
    last = len(counted) - 1
    while last > 0 and not (median * AUTO_CAL['LANDING_SHORT_RATIO'] <= lap_times[last - 1]
                            <= median * AUTO_CAL['LANDING_LONG_RATIO']):
        last -= 1
    if last == 0:
        return
    end = counted[last]['lap_time_stamp']
    for lap in laps:
        if lap['lap_time_stamp'] > end and not lap['deleted']:
            lap['deleted'] = True
            lap['late'] = True
            lap['landing'] = True

def _ruled_late(lap):
    # a lap the race's own rules put after the race: past the race time or the winning lap
    return lap.get('late') and not lap.get('landing')

def _after_race(lap):
    # a lap after the race, or a crossing the recording ended in that is no longer than a gate pass
    return lap.get('late') or (lap.get('open') and lap['crossingEnd'] - lap['crossingStart'] <= AUTO_CAL['MAX_CROSSING_S'])

def _crossings_usable(laps, skip_late=False):
    # a crossing that never closes, or that lasts far longer than a gate pass, is the threshold
    #  sitting in the ripple or the noise; laps after the race can be left out
    return not any(lap.get('open') or lap['crossingEnd'] - lap['crossingStart'] > AUTO_CAL['MAX_CROSSING_S']
                   for lap in laps if not (_ruled_late(lap) or skip_late and _after_race(lap)))

def _count_noise_crossings(laps, min_lap_ms):
    # crossings within the minimum lap time of the previous one, plus any already deleted as such;
    #  laps after the race are left out
    min_gap = min_lap_ms or AUTO_CAL['DEFAULT_MIN_LAP_MS']
    noise = 0
    last_stamp = None
    for lap in laps:
        if lap.get('late'):
            continue
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

def _adds_holeshot_only(laps, base_laps):
    # one early crossing more than the base laps, with the counted crossings after it unchanged
    stamps = [lap['lap_time_stamp'] for lap in laps if not lap['deleted']]
    base = [lap['lap_time_stamp'] for lap in base_laps if not lap['deleted']]
    return (len(stamps) == len(base) + 1 and stamps[0] <= AUTO_CAL['HOLESHOT_WINDOW_S'] * 1000 and
            all(abs(a - b) <= AUTO_CAL['HOLESHOT_MATCH_S'] * 1000 for a, b in zip(stamps[1:], base)))

def _score_calibration(laps, min_lap_ms, with_duration=True):
    # lower is better: crossings too close together to be laps, a crossing left open or overlong,
    #  merged passes, and (with_duration) the time spent in the counted crossings
    score = AUTO_CAL['NOISE_PENALTY'] * _count_noise_crossings(laps, min_lap_ms)
    stamps = []
    for lap in laps:
        if lap.get('late'):
            continue
        if lap.get('open') or lap['crossingEnd'] - lap['crossingStart'] > AUTO_CAL['MAX_CROSSING_S']:
            score += AUTO_CAL['OPEN_PENALTY']
        elif not lap['deleted'] or lap.get('noise'):
            # a crossing deleted as noise still spent its time over the threshold
            if not lap['deleted']:
                stamps.append(lap['lap_time_stamp'])
            if with_duration:
                score += AUTO_CAL['DURATION_WEIGHT'] * (lap['crossingEnd'] - lap['crossingStart'])
    lap_times = [stamps[i] - stamps[i - 1] for i in range(1, len(stamps))]
    if len(lap_times) >= 3:
        median = sorted(lap_times)[len(lap_times) // 2]
        score += AUTO_CAL['MERGED_PENALTY'] * sum(1 for t in lap_times if t > median * AUTO_CAL['MERGED_RATIO'])
    return score

def _clean_peak(values, times, lo, lap):
    # a gate pass rises past halfway, or three-quarters of the way, from the trace minimum to its peak
    #  once; a messy crossing does so several times at both levels; a dip below the level for a single
    #  reading does not separate two rises
    start = lap['crossingStart'] - AUTO_CAL['CLEAN_PEAK_WINDOW_S']
    end = lap['crossingEnd'] + AUTO_CAL['CLEAN_PEAK_WINDOW_S']
    segment = [(value, time) for value, time in zip(values, times) if start <= time <= end]
    if not segment:
        return False
    def rises(level):
        count = 0
        below = set()
        for value, time in segment:
            if value >= level:
                if count == 0 or len(below) > 1:
                    count += 1
                below = set()
            else:
                below.add(time)
        return count
    peak = max(value for value, _ in segment)
    return any(rises(lo + (peak - lo) * fraction) == 1 for fraction in (0.5, 0.75))

def _clean_peaks(values, times):
    # (value, time) of the peaks above halfway up the trace that fall steadily on both sides
    lo = min(values)
    hi = max(values)
    window = AUTO_CAL['CLEAN_PEAK_WINDOW_S']
    peaks = []
    last_time = -math.inf
    for i, (value, time) in enumerate(zip(values, times)):
        if value < (lo + hi) / 2 or time - last_time <= window:
            continue
        first = bisect.bisect_left(times, time - window)
        last = bisect.bisect_right(times, time + window)
        if value < max(values[first:last]) or values.index(value, first, last) != i:
            continue
        base = value - (value - lo) * AUTO_CAL['BELL_DROP_FRACTION']
        tolerance = (value - lo) * AUTO_CAL['BELL_TOLERANCE_FRACTION']
        sides = 0
        for step in (-1, 1):
            j = i
            lowest = value
            while 0 <= j + step < len(values) and abs(times[j + step] - time) <= AUTO_CAL['BELL_SIDE_S']:
                j += step
                if values[j] > lowest + tolerance:
                    break
                lowest = min(lowest, values[j])
                if values[j] <= base:
                    sides += 1
                    break
        if sides == 2:
            peaks.append((value, time))
            last_time = time
    return peaks

def suggest_calibration(values, times, start_time, unlimited_time, race_time_sec, min_lap_ms,
                        min_lap_behavior, min_first_crossing_ms, lap_limit=0):
    '''EnterAt/ExitAt from the RSSI history: the widest run of EnterAt values over which the pass
       count holds steady is the gate band, between the weakest pass and the ripple. Returns
       {'enter_at', 'exit_at', 'laps', 'lap_count', 'band'} or None when no band stands out.'''
    return suggest_calibration_with_reason(values, times, start_time, unlimited_time, race_time_sec,
                                           min_lap_ms, min_lap_behavior, min_first_crossing_ms, lap_limit)[0]

def suggest_calibration_with_reason(values, times, start_time, unlimited_time, race_time_sec, min_lap_ms,
                                    min_lap_behavior, min_first_crossing_ms, lap_limit=0):
    '''As suggest_calibration(), returning (suggestion, None) or (None, NoSuggestion reason).
       lap_limit is the most laps the pilot can count, holeshot included, or 0 for no limit.'''
    if len(values) != len(times):
        return None, NoSuggestion.NO_HISTORY
    # only the readings from the race start to the end of the race time count
    race_end = start_time + race_time_sec if not unlimited_time and race_time_sec else math.inf
    kept = [(value, time) for value, time in zip(values, times) if start_time <= time <= race_end]
    values = [value for value, _ in kept]
    times = [time for _, time in kept]
    if len(values) < 3:
        return None, NoSuggestion.NO_HISTORY
    found, reason = _suggest_from(values, times, start_time, unlimited_time, race_time_sec, min_lap_ms,
                                  min_lap_behavior, min_first_crossing_ms, lap_limit)
    if reason == NoSuggestion.NO_GATE_PASSES:
        # with no band, EnterAt goes a little below the weakest of the clean peaks near the typical
        #  peak height
        peaks = _clean_peaks(values, times)
        lo = min(values)
        if peaks:
            median = sorted(value for value, _ in peaks)[len(peaks) // 2]
            passes = [(value, time) for value, time in peaks if value >= lo + (median - lo) * AUTO_CAL['BELL_PASS_FRACTION']]
            if len(passes) >= AUTO_CAL['TYPICAL_LAP_MIN_CROSSINGS']:
                weakest = min(value for value, _ in passes)
                # a minimum lap too long for the spacing of the passes is replaced as in the band scan
                typical_lap = sorted(b - a for (_, a), (_, b) in zip(passes, passes[1:]))[(len(passes) - 1) // 2] * 1000
                if (min_lap_ms or AUTO_CAL['DEFAULT_MIN_LAP_MS']) > typical_lap * AUTO_CAL['MIN_LAP_TOO_LONG_FRACTION']:
                    min_lap_ms = typical_lap / 2
                # below the weakest pass, EnterAt goes down while every crossing it adds is a clean peak at
                #  least half a typical lap from the crossings already there
                window = AUTO_CAL['CLEAN_PEAK_WINDOW_S'] * 1000
                clean_stamps = [(time - start_time) * 1000 for _, time in peaks]
                def crossings(level):
                    exit_level = level - max(AUTO_CAL['MIN_EXIT_GAP'], _js_round(level * AUTO_CAL['MIN_EXIT_GAP_OF_ENTER']))
                    return [lap['lap_time_stamp'] for lap in compute_laps(values, times, start_time, level, exit_level,
                            unlimited_time, race_time_sec, min_lap_ms, 0, min_first_crossing_ms) if not lap.get('open')]
                floor = weakest
                above = crossings(floor)
                while floor - 1 > lo:
                    below = crossings(floor - 1)
                    added = [stamp for stamp in below if all(abs(stamp - other) > window for other in above)]
                    if any(all(abs(stamp - clean) > window for clean in clean_stamps)
                           or min(abs(stamp - other) for other in above) < typical_lap / 2 for stamp in added):
                        break
                    floor -= 1
                    above = below
                weakest = min([value for value, _ in peaks if value >= floor] + [weakest])
                enter = weakest - max(AUTO_CAL['BELL_ENTER_MIN'], _js_round(weakest * AUTO_CAL['BELL_ENTER_FRACTION']))
                found, _ = _suggest_from(values, times, start_time, unlimited_time, race_time_sec, min_lap_ms,
                                         min_lap_behavior, min_first_crossing_ms, lap_limit, (enter, len(passes)))
                if found:
                    reason = None
    if found:
        found = _cut_bad_crossings(found, values, times, start_time, unlimited_time, race_time_sec, min_lap_ms,
                                   min_lap_behavior, min_first_crossing_ms, lap_limit)
    return found, reason

def _cut_bad_crossings(found, values, times, start_time, unlimited_time, race_time_sec, min_lap_ms,
                       min_lap_behavior, min_first_crossing_ms, lap_limit):
    # while EnterAt is held above the margin below the weakest good pass, the crossings below the band
    #  that are messy or overlong and away from the passes are cut out of the trace, with the rest of
    #  their burst, and the suggestion found again; this stops at a crossing near a pass or a new good one
    lo = min(values)
    min_gap = min(min_lap_ms or AUTO_CAL['DEFAULT_MIN_LAP_MS'], AUTO_CAL['DEFAULT_MIN_LAP_MS']) / 1000
    values = list(values)
    for _ in range(AUTO_CAL['CUT_ROUNDS']):
        good = [peak for _, peak, ok in found['passes'] if ok]
        if not good:
            break
        weakest = min(good)
        target = weakest - _js_round(min(weakest * AUTO_CAL['PEAK_MARGIN_FRACTION'],
                                         (weakest - lo) * AUTO_CAL['PEAK_MARGIN_SPAN_FRACTION']))
        if found['enter_at'] <= target:
            break
        pass_times = [time for time, _, _ in found['passes']]
        cut = []
        for enter in range(found['band'][0] - 1, target - 1, -1):
            exit_at = enter - max(1, _js_round((enter - lo) * AUTO_CAL['SCAN_EXIT_FRACTION']))
            laps = [lap for lap in compute_laps(values, times, start_time, enter, exit_at, unlimited_time,
                                                race_time_sec, 0, 0, min_first_crossing_ms)
                    if not lap['deleted'] and not lap.get('late') and not lap.get('open')]
            new = [lap for lap in laps if not any(lap['crossingStart'] <= t <= lap['crossingEnd'] for t in pass_times)]
            if not new:
                continue
            if any(abs(start_time + lap['lap_time_stamp'] / 1000 - t) < min_gap for lap in new for t in pass_times) or \
                    any(_clean_peak(values, times, lo, lap) and
                        lap['crossingEnd'] - lap['crossingStart'] <= AUTO_CAL['MAX_PASS_CROSSING_S'] for lap in new):
                break
            cut = new
            break
        if not cut:
            break
        for lap in cut:
            # the whole burst around the crossing, clear of the passes
            span = [i for i, time in enumerate(times) if lap['crossingStart'] - min_gap <= time <= lap['crossingEnd'] + min_gap
                    and all(abs(time - t) > min_gap / 2 for t in pass_times)]
            low = min(values[i] for i in span)
            for i in span:
                values[i] = low
        again, _ = _suggest_from(values, times, start_time, unlimited_time, race_time_sec, min_lap_ms,
                                 min_lap_behavior, min_first_crossing_ms, lap_limit)
        if not again:
            break
        found = again
    return found

def _suggest_from(values, times, start_time, unlimited_time, race_time_sec, min_lap_ms,
                  min_lap_behavior, min_first_crossing_ms, lap_limit, fixed=None):
    # the suggestion from the readings given, or (None, NoSuggestion reason); with fixed, an EnterAt
    #  and the number of passes it should keep, used when no band stands out
    lo = min(values)
    hi = max(values)
    if hi - lo < AUTO_CAL['MIN_SPAN']:
        return None, NoSuggestion.WEAK_SIGNAL
    def laps_for(enter, exit_at):
        laps = compute_laps(values, times, start_time, enter, exit_at, unlimited_time, race_time_sec,
                            min_lap_ms, min_lap_behavior, min_first_crossing_ms)
        if lap_limit:
            _mark_after_lap_limit(laps, lap_limit)
        _mark_trailing_noise(laps, min_lap_ms, (times[-1] - start_time) * 1000)
        if unlimited_time:
            _mark_landing(laps)
        return laps
    def pass_count(laps):
        return len([lap for lap in laps if not _after_race(lap)]) - _count_noise_crossings(laps, min_lap_ms)
    # a minimum lap close to or longer than the laps flown would class real passes as noise; the
    #  widest run of EnterAt values with a steady number of crossings gives the typical lap
    runs = []
    for enter in range(hi - 1, lo + AUTO_CAL['BAND_MARGIN'], -1):
        laps = laps_for(enter, enter - max(1, _js_round((enter - lo) * AUTO_CAL['SCAN_EXIT_FRACTION'])))
        crossing_stamps = [lap['lap_time_stamp'] for lap in laps
                           if (not lap['deleted'] or lap.get('noise')) and not _after_race(lap)]
        if runs and runs[-1]['count'] == len(crossing_stamps):
            runs[-1]['low'] = enter
        else:
            runs.append({'count': len(crossing_stamps), 'high': enter, 'low': enter, 'stamps': crossing_stamps})
    runs = [run for run in runs if run['count'] >= AUTO_CAL['TYPICAL_LAP_MIN_CROSSINGS']]
    if runs:
        typical_lap, regular = _regular_lap_times(max(runs, key=lambda run: run['high'] - run['low'])['stamps'])
        if regular and (min_lap_ms or AUTO_CAL['DEFAULT_MIN_LAP_MS']) > typical_lap * AUTO_CAL['MIN_LAP_TOO_LONG_FRACTION']:
            min_lap_ms = typical_lap / 2
    scan = {}
    plateaus = []
    run = None
    for enter in range(hi - 1, lo + AUTO_CAL['BAND_MARGIN'], -1):
        # a wide provisional ExitAt, so the bumps after a pass stay inside its crossing
        laps = laps_for(enter, enter - max(1, _js_round((enter - lo) * AUTO_CAL['SCAN_EXIT_FRACTION'])))
        scan[enter] = laps
        if not laps or not _crossings_usable(laps, skip_late=True):
            run = None
            continue
        # passes and merged crossings must both hold for the band to continue; laps after the
        #  race come and go with the landing, so they are left out
        noise = _count_noise_crossings(laps, min_lap_ms)
        count = len([lap for lap in laps if not _after_race(lap)]) - noise
        if run and run['count'] == count and run['noise'] == noise:
            run['low'] = enter
        elif (run and run['high'] == run['low'] and len(plateaus) > 1 and run['count'] == count
              and noise == 0 and plateaus[-2]['count'] == count and plateaus[-2]['noise'] == 0
              and plateaus[-2]['low'] == enter + 2):
            # a single EnterAt with the same passes and an extra noise crossing does not break a clean band
            plateaus.pop()
            run = plateaus[-1]
            run['low'] = enter
        else:
            run = {'count': count, 'noise': noise, 'high': enter, 'low': enter}
            plateaus.append(run)
    # among the bands nearly as wide as the widest, the one with the most passes: a wide lower
    #  band holds weaker real passes, since ripple would have broken it up
    widest = max((p['high'] - p['low'] for p in plateaus), default=0)
    band = None
    def stamps(laps):
        return [lap['lap_time_stamp'] for lap in laps if not lap['deleted'] and not _after_race(lap)]
    def trailing_only(lower, upper):
        # with no time limit, passes a lower band adds only after the last pass of a higher band are
        #  flying after the race, when they are few beside the higher band's passes
        upper_stamps = stamps(upper)
        extra = [s for s in stamps(lower) if all(abs(s - u) > AUTO_CAL['HOLESHOT_MATCH_S'] * 1000 for u in upper_stamps)]
        return (unlimited_time and bool(extra) and len(extra) * 2 < len(upper_stamps)
                and min(extra) > max(upper_stamps))
    def clean_peak(lap):
        return _clean_peak(values, times, lo, lap)
    def messy_only(lower, upper):
        # passes a lower band adds that all lack a clean peak are not worth its lower EnterAt
        upper_stamps = stamps(upper)
        extra = [lap for lap in lower if not lap['deleted'] and not _after_race(lap) and
                 all(abs(lap['lap_time_stamp'] - u) > AUTO_CAL['HOLESHOT_MATCH_S'] * 1000 for u in upper_stamps)]
        return bool(extra) and not any(clean_peak(lap) for lap in extra)
    for p in plateaus:
        if p['high'] - p['low'] >= widest * AUTO_CAL['WIDE_FRACTION'] and (band is None or (p['count'] > band['count']
                and not trailing_only(scan[p['high']], scan[band['high']])
                and not messy_only(scan[p['high']], scan[band['high']]))):
            band = p  # the first found at a count is the higher, keeping more margin over the noise
    # a band narrower than the fraction of the trace span still counts when it is a fraction of the way
    #  to the minimum and its passes come at a regular pace with few noise crossings
    def too_narrow(band):
        return band is None or band['high'] - band['low'] < max(AUTO_CAL['MIN_BAND'], (hi - lo) * AUTO_CAL['MIN_BAND_FRACTION']) and (
            band['high'] - band['low'] < max(AUTO_CAL['MIN_BAND'], (band['high'] - lo) * AUTO_CAL['MIN_REGULAR_BAND_FRACTION'])
            or band['noise'] > band['count'] * AUTO_CAL['NARROW_BAND_NOISE_FRACTION']
            or not _regular_lap_times(stamps(scan[band['high']]))[1])
    if too_narrow(band):
        # with no band otherwise, adjacent bands with the same number of crossings, noise crossings
        #  included, are joined, and the highest joined band wide enough is taken
        joined = []
        for p in plateaus:
            if joined and joined[-1]['crossings'] == p['count'] + p['noise'] and joined[-1]['low'] == p['high'] + 1:
                joined[-1] = dict(joined[-1], low=p['low'], count=min(joined[-1]['count'], p['count']),
                                  noise=max(joined[-1]['noise'], p['noise']))
            else:
                joined.append(dict(p, crossings=p['count'] + p['noise']))
        wide = [p for p in joined if p['high'] - p['low'] >= max(AUTO_CAL['MIN_BAND'], (hi - lo) * AUTO_CAL['MIN_BAND_FRACTION'])]
        band = wide[0] if wide else None
        if band is None:
            if fixed is None or fixed[0] not in scan:
                return None, NoSuggestion.NO_GATE_PASSES
            band = {'count': fixed[1], 'noise': 0, 'high': fixed[0], 'low': fixed[0]}
    # below a band of good passes, narrow steady steps that each add a good pass, with no noise other
    #  than second bumps, hold weaker real passes; the lowest such step is taken as the band
    def good(lap):
        return clean_peak(lap) and lap['crossingEnd'] - lap['crossingStart'] <= AUTO_CAL['MAX_PASS_CROSSING_S']
    def counted(laps):
        return [lap for lap in laps if not lap['deleted'] and not _after_race(lap)]
    band_stamps_all = stamps(scan[band['low']]) if band in plateaus else []
    def median_gap(pass_stamps):
        gaps = sorted(b - a for a, b in zip(pass_stamps, pass_stamps[1:]))
        return gaps[len(gaps) // 2] if gaps else 0
    band_cadence = median_gap(band_stamps_all)
    cadence = band_cadence
    def spaced(lap, laps):
        # a pass at least most of a typical lap from every other pass
        return all(abs(other['lap_time_stamp'] - lap['lap_time_stamp']) >= cadence * AUTO_CAL['STEP_SPACING_FRACTION']
                   for other in counted(laps) if other is not lap)
    def steady(p):
        # the step's passes are the same at every EnterAt in it
        ref = stamps(scan[p['low']])
        return all(len(stamps(scan[e])) == len(ref) and
                   all(min(abs(s - r) for r in ref) <= AUTO_CAL['HOLESHOT_MATCH_S'] * 1000 for s in stamps(scan[e]))
                   for e in range(p['low'], p['high'] + 1))
    if band in plateaus and all(good(lap) for lap in counted(scan[band['high']])):
        base = stamps(scan[band['low']])
        low = band['low']
        count = band['count']
        step = None
        gained = False
        ended_early = unlimited_time or times[-1] - start_time < race_time_sec - AUTO_CAL['EARLY_END_S']
        for p in plateaus[plateaus.index(band) + 1:]:
            if p['high'] != low - 1 or p['count'] < count:
                break
            laps = scan[p['low']]
            kept = [lap for lap in laps if not lap['deleted'] or lap.get('noise')]
            if any(lap.get('noise') and not any(other is not lap and not other.get('noise') and
                                                abs(other['lap_time_stamp'] - lap['lap_time_stamp']) <= AUTO_CAL['DOUBLE_WINDOW_S'] * 1000
                                                for other in kept) for lap in laps):
                break
            added = [lap for lap in counted(laps)
                     if all(abs(lap['lap_time_stamp'] - b) > AUTO_CAL['HOLESHOT_MATCH_S'] * 1000 for b in base)]
            # with a single pass in the band, the typical lap is the median gap between the step's passes,
            #  once it has three
            if not band_cadence:
                cadence = median_gap(stamps(laps)) if len(counted(laps)) >= 3 else 0
            below = scan.get(p['low'] - 1, laps)
            def split(lap):
                # a second crossing within the double window just below the step marks a double peak
                return any(0 < abs(other['lap_time_stamp'] - lap['lap_time_stamp']) <= AUTO_CAL['DOUBLE_WINDOW_S'] * 1000
                           for other in below if not other['deleted'] or other.get('noise'))
            # when the recording ends before the race time, a final crossing within a lap of its end may be
            #  the landing, so it does not count as a new pass
            last = counted(laps)[-1] if counted(laps) else None
            if added and ended_early and all(lap is last and (times[-1] - start_time) * 1000 - lap['lap_time_stamp'] < cadence for lap in added):
                break
            # with two passes in the band, a good pass that splits their gap into two near-equal parts shows
            #  the gap was two laps, so the typical lap is halved
            if len(band_stamps_all) == 2 and cadence == band_cadence:
                for lap in added:
                    t = lap['lap_time_stamp']
                    before = max((b for b in base if b < t), default=None)
                    after = min((b for b in base if b > t), default=None)
                    if before is not None and after is not None and good(lap) and not split(lap) and \
                            min(t - before, after - t) >= max(t - before, after - t) * AUTO_CAL['STEP_SPACING_FRACTION']:
                        cadence = (after - before) / 2
            # with the band's typical lap the added passes are checked, with the step's own all its passes
            checked = added if band_cadence else counted(laps) if cadence else []
            if added and not any(good(lap) and not split(lap) for lap in added):
                # a step that adds only messy passes is passed over
                low = p['low']
                count = p['count']
                base = stamps(laps)
                continue
            if added and not all(spaced(lap, laps) for lap in checked):
                break
            # a step is taken only once the walk has added a good pass
            gained = gained or bool(added)
            low = p['low']
            count = p['count']
            base = stamps(laps)
            if gained and cadence and steady(p) and p['noise'] == 0 and p['count'] > band['count'] and \
                    p['high'] - p['low'] + 1 >= AUTO_CAL['MIN_BAND']:
                step = p
        if step and band['low'] - step['low'] >= (band['high'] - band['low']) * AUTO_CAL['STEP_REACH_FRACTION']:
            band = step
    enter = band['low'] + _js_round((band['high'] - band['low']) * AUTO_CAL['BAND_POSITION'])
    peaks = [lap['peak_rssi'] for lap in scan[enter] if not lap['deleted'] and not _after_race(lap) and 'peak_rssi' in lap]
    if peaks:
        weakest = min(peaks)
        margin = min(weakest * AUTO_CAL['PEAK_MARGIN_FRACTION'], (weakest - lo) * AUTO_CAL['PEAK_MARGIN_SPAN_FRACTION'])
        target = weakest - _js_round(margin)
        # below the band, EnterAt may still go down through values that add only second bumps of the
        #  band's passes or bad peaks
        lowest = band['low']
        band_stamps = stamps(scan[band['high']])
        # crossings that are messy, overlong or double-peaked down at the target are bad peaks, which are
        #  ignored here rather than holding EnterAt up
        target_laps = scan.get(max(target, min(scan)), [])
        def bad(lap):
            return not good(lap) or any(
                0 < abs(other['lap_time_stamp'] - lap['lap_time_stamp']) <= AUTO_CAL['DOUBLE_WINDOW_S'] * 1000
                for other in target_laps if not other['deleted'] or other.get('noise'))
        while lowest - 1 > target and lowest - 1 in scan and _crossings_usable(scan[lowest - 1], skip_late=True):
            core = [lap for lap in _without_doubles(scan[lowest - 1])
                    if (not lap['deleted'] or lap.get('noise')) and not _after_race(lap)]
            extra = [lap for lap in core if min(abs(lap['lap_time_stamp'] - s) for s in band_stamps) >
                     AUTO_CAL['DOUBLE_WINDOW_S'] * 1000]
            if len(core) - len(extra) != len(band_stamps) or not all(bad(lap) for lap in extra):
                break
            lowest -= 1
        # with no such values below the band, the margin keeps EnterAt in the upper half of the band
        if lowest == band['low']:
            lowest = _js_round((band['low'] + band['high']) / 2)
        enter = max(lowest, min(enter, target))
    # a weak holeshot peaks at the top of the ripple; with no early crossing in the band, step
    #  down to the first EnterAt that adds exactly one, early, keeps the later passes and keeps the set clean
    if not _has_early_crossing(scan[enter]):
        base_score = _score_calibration(scan[enter], min_lap_ms)
        for e in range(band['low'] - 1, band['low'] - AUTO_CAL['HOLESHOT_SEARCH'] - 1, -1):
            if e not in scan:
                break
            if pass_count(scan[e]) == band['count'] + 1 and _adds_holeshot_only(scan[e], scan[enter]) and \
                    _crossings_usable(scan[e]) and _score_calibration(scan[e], min_lap_ms) <= base_score:
                enter = e
                break
    # ExitAt: the lowest score, with the time spent in crossings counted, marks the clean range,
    #  the run of ExitAt values around it giving the same laps; ExitAt is placed a small margin
    #  below the top of that range, so laps are announced soon after the pass
    structural = {}
    best_exit = None
    best_score = math.inf
    min_gap = max(AUTO_CAL['MIN_EXIT_GAP'], _js_round((enter - lo) * AUTO_CAL['MIN_EXIT_GAP_FRACTION']))
    # a pass that splits into crossings within the double window at the usual ExitAt gap from the
    #  trace minimum has double peaks; while other passes remain, its crossings are left out of the
    #  ExitAt scoring
    window = AUTO_CAL['DOUBLE_WINDOW_S'] * 1000
    first_gap = max((enter - lo) * AUTO_CAL['EXIT_GAP_FRACTION'],
                    min((hi - lo) * AUTO_CAL['EXIT_SPAN_FRACTION'], (enter - lo) * AUTO_CAL['EXIT_SPAN_CAP_FRACTION']))
    first_stamps = sorted(lap['lap_time_stamp'] for lap in laps_for(enter, enter - _js_round(first_gap))
                          if (not lap['deleted'] or lap.get('noise')) and not _after_race(lap))
    doubles = []
    for a, b in zip(first_stamps, first_stamps[1:]):
        if b - a <= window:
            if doubles and doubles[-1][1] == a:
                doubles[-1] = (doubles[-1][0], b)
            else:
                doubles.append((a, b))
    if all(any(a <= s <= b for a, b in doubles) for s in first_stamps):
        doubles = []
    def scored(laps):
        return [lap for lap in laps if not any(a - window <= lap['lap_time_stamp'] <= b + window for a, b in doubles)]
    # laps after the race are left out only when no ExitAt is clean with them
    for skip_late in (False, True):
        for exit_at in range(enter - min_gap, lo, -1):
            laps = scored(laps_for(enter, exit_at))
            if not _crossings_usable(laps, skip_late) or pass_count(laps) < band['count'] - len(doubles):
                continue
            structural[exit_at] = _score_calibration(laps, min_lap_ms, with_duration=False)
            score = _score_calibration(laps, min_lap_ms)
            if score < best_score:
                best_score = score
                best_exit = exit_at
        if best_exit is not None:
            break
    if best_exit is None:
        return None, NoSuggestion.NO_CLEAN_EXIT
    top = best_exit
    while structural.get(top + 1) == structural[best_exit]:
        top += 1
    bottom = best_exit
    while structural.get(bottom - 1) == structural[best_exit]:
        bottom -= 1
    # the gap is measured to the usual low point between passes, which sits well above the trace
    #  minimum when the signal never settles between passes
    counted = [lap for lap in laps_for(enter, best_exit) if not lap['deleted'] and not _after_race(lap)]
    lows = sorted(min(values[i] for i, time in enumerate(times) if prev['crossingEnd'] < time < lap['crossingStart'])
                  for prev, lap in zip(counted, counted[1:])
                  if any(prev['crossingEnd'] < time < lap['crossingStart'] for time in times))
    floor = max(lo, lows[len(lows) // 4]) if len(lows) >= AUTO_CAL['TYPICAL_LAP_MIN_CROSSINGS'] else lo
    gap = max((enter - floor) * AUTO_CAL['EXIT_GAP_FRACTION'],
              min((hi - floor) * AUTO_CAL['EXIT_SPAN_FRACTION'], (enter - floor) * AUTO_CAL['EXIT_SPAN_CAP_FRACTION']))
    exit_at = max(bottom, min(top - _js_round((enter - lo) * AUTO_CAL['EXIT_TOP_MARGIN_FRACTION']), enter - _js_round(gap)))
    # keep the smallest gap, taking the highest ExitAt at or below it that is within the clean range or
    #  gives laps at least as clean as the chosen one; on a strong trace the fallback gap may be used
    #  while it stays clear of the trace minimum; otherwise no suggestion
    # with a fixed EnterAt, a lower ExitAt also must keep the passes of the chosen one
    keep = pass_count(scored(laps_for(enter, best_exit))) * (1 - AUTO_CAL['BELL_PASS_LOSS_FRACTION']) \
        if fixed and band['low'] == fixed[0] else 0
    def highest_clean(limit):
        for exit_value in range(limit, lo, -1):
            if (bottom <= exit_value <= top or structural.get(exit_value, math.inf) <= structural[best_exit]) and (
                    not keep or pass_count(scored(laps_for(enter, exit_value))) >= keep):
                return exit_value
        return None
    wanted = highest_clean(min(exit_at, enter - math.ceil(enter * AUTO_CAL['MIN_EXIT_GAP_OF_ENTER'])))
    fallback = highest_clean(min(exit_at, enter - math.ceil(enter * AUTO_CAL['MIN_EXIT_GAP_OF_ENTER_FALLBACK'])))
    if wanted is not None:
        exit_at = wanted
    elif hi - lo >= AUTO_CAL['FALLBACK_MIN_SPAN'] and fallback is not None and fallback - lo >= AUTO_CAL['MIN_EXIT_GAP']:
        exit_at = fallback
    else:
        return None, NoSuggestion.NO_CLEAN_EXIT
    laps = laps_for(enter, exit_at)
    # a pass that splits into crossings within the double window at the usual ExitAt gap has double
    #  peaks and is not a valid pass, nor is one with an overlong crossing; with no valid passes there
    #  is no suggestion
    split = [start_time + lap['lap_time_stamp'] / 1000 for lap in laps_for(enter, enter - _js_round(gap))
             if (not lap['deleted'] or lap.get('noise')) and not _after_race(lap)]
    def double(lap):
        inside = [t for t in split if lap['crossingStart'] <= t <= lap['crossingEnd']]
        return any(b - a <= AUTO_CAL['DOUBLE_WINDOW_S'] for a, b in zip(inside, inside[1:]))
    if all(double(lap) or lap['crossingEnd'] - lap['crossingStart'] > AUTO_CAL['MAX_PASS_CROSSING_S']
           for lap in laps if not lap['deleted'] and not _after_race(lap)):
        return None, NoSuggestion.NO_GATE_PASSES
    # each counted pass with its peak time and value, and whether it is a good pass: a clean peak, no
    #  double peaks and no overlong crossing
    passes = [(start_time + lap['lap_time_stamp'] / 1000, lap['peak_rssi'],
               not double(lap) and lap['crossingEnd'] - lap['crossingStart'] <= AUTO_CAL['MAX_PASS_CROSSING_S']
               and clean_peak(lap))
              for lap in laps if not lap['deleted'] and not _after_race(lap) and 'peak_rssi' in lap]
    return {'enter_at': enter, 'exit_at': exit_at, 'laps': laps, 'passes': passes,
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
        return self._suggest(json.loads(pilotrace.history_values), json.loads(pilotrace.history_times),
                             race_meta.start_time, race_format)

    def suggest_for_seat(self, seat_index):
        '''Suggested EnterAt/ExitAt for a seat in the current (stopped, unsaved) race: (suggestion, None) or (None, reason).'''
        race = self._racecontext.race
        if seat_index < 0 or seat_index >= race.num_nodes:
            return None, NoSuggestion.NOT_FOUND
        node = self._racecontext.interface.nodes[seat_index]
        if _pass_peak_only(self._racecontext.interface.node_map[seat_index].interface.marshal_type):
            return None, NoSuggestion.PASS_PEAK_ONLY
        return self._suggest(node.history_values, node.history_times, race.start_time_monotonic,
                             race.format)

    def _suggest(self, values, times, start_time, race_format):
        rhdata = self._racecontext.rhdata
        # with no format there is no race time, so no laps count as late
        unlimited_time = race_format.unlimited_time if race_format else True
        race_time_sec = race_format.race_time_sec if race_format else 0
        result, reason = suggest_calibration_with_reason(values, times, start_time, unlimited_time, race_time_sec,
                                     rhdata.get_optionInt('MinLapSec') * 1000,
                                     self._racecontext.serverconfig.get_item_int('TIMING', 'MinLapBehavior'),
                                     rhdata.get_optionInt('MinFirstCrossingSec') * 1000, _lap_limit(race_format))
        if result:
            logger.debug('Calibration suggestion: EnterAt {}, ExitAt {}, band {}-{}, {} laps'.format(
                result['enter_at'], result['exit_at'], result['band'][0], result['band'][1], result['lap_count']))
        else:
            logger.debug('No calibration suggestion: {}'.format(reason))
        return result, reason
