'''Class to hold race management variables.'''

import logging
import json
import RHUtils
import RHTimeFns
import Results
import gevent
import random
from dataclasses import dataclass
from datetime import datetime
from flask import request, copy_current_request_context
from time import monotonic
from eventmanager import Evt
from filtermanager import Flt
from util.InvokeFuncQueue import InvokeFuncQueue
from RHUtils import catchLogExceptionsWrapper
from led_event_manager import ColorVal
from Database import RoundType

from FlaskAppObj import APP
APP.app_context().push()

logger = logging.getLogger(__name__)

@dataclass
class Crossing(dict):
    node_index: int = None
    pilot_id: int = None
    lap_number: int = 0
    lap_time_stamp: int = None
    lap_time: int = None
    lap_time_formatted: str = None
    source: str = None
    deleted: bool = False
    late_lap: bool = False
    invalid: bool = False
    def __bool__(self):
        return True  # always evaluate object as 'True', even if underlying dict is empty

class RHRace():
    '''Class to hold race management variables.'''
    def __init__(self, racecontext):
        # internal references
        self._racecontext = racecontext
        self._filters = racecontext.filters
        self.__ = self._racecontext.language.__
        # setup/options
        self.num_nodes = 0
        self.current_heat = RHUtils.HEAT_ID_NONE # heat ID
        self.node_pilots = {} # current race pilots, by node, filled on heat change
        self.node_teams = {} # current race teams, by node, filled on heat change
        self._format = None # raceformat object
        self._profile = None
        # sequence
        self.scheduled = False # Whether to start a race when time
        self.scheduled_time = 0 # Start race when time reaches this value
        self.start_token = False # Check start thread matches correct stage sequence
        # status
        self.race_status = RaceStatus.READY
        self.timer_running = False
        self.stage_time_monotonic = 0
        self.start_time = 0 # datetime object
        self.start_time_formatted = ''
        self.start_time_monotonic = 0
        self.start_time_epoch_ms = 0 # ms since 1970-01-01
        self.unlimited_time = True
        self.race_time_sec = 0
        self.show_init_time_flag = False  # True show 'race_time_sec' value on initial Run-page timer display (if nonzero)
        self.coop_best_time = 0.0  # best time achieved in co-op racing mode (seconds)
        self.coop_num_laps = 0     # best # of laps in co-op racing mode
        self.node_laps = {} # current race lap objects, by node
        self.node_has_finished = {}     # True if pilot for node has finished race
        self.node_finished_effect = {}  # True if effect for pilot-finished for node has been triggered
        self.node_fin_effect_wait_count = 0  # number of finished effects waiting for all crossings completed
        self.any_races_started = False
        # concluded
        self.end_time = 0 # Monotonic, updated when race is stopped
        # leaderboard/cache
        self.lap_results = None # current race calculated lap list
        self.lap_cacheStatus = None # whether cache is valid

        self.results = None # current race results
        self.cacheStatus = None # whether cache is valid
        self.status_message = '' # Race status message (winner, team info)

        self.team_results = None # current race results
        self.team_cacheStatus = None # whether cache is valid

        self.win_status = WinStatus.NONE # whether race is won
        self.race_winner_name = ''
        self.race_winner_phonetic = ''
        self.race_winner_lap_id = 0
        self.race_winner_pilot_id = RHUtils.PILOT_ID_NONE

        self.prev_race_winner_name = ''
        self.prev_race_winner_phonetic = ''
        self.prev_race_winner_pilot_id = RHUtils.PILOT_ID_NONE

        self.race_leader_lap = 0  # current race leader
        self.race_leader_pilot_id = RHUtils.PILOT_ID_NONE
        self.race_initial_pass_flag = False  # set True after first gate pass of any pilot

        self.db_id = None
        self._seat_colors = []
        self.external_flag = False # is race data controlled externally (from cluster)
        self.pass_invoke_func_queue_obj = InvokeFuncQueue(logger)

        self.clear_results()

        '''
        Lap Object (dict) for node_laps:
            lap_number
            lap_time_stamp
            lap_time
            lap_time_formatted
            source
            deleted
        '''



    @catchLogExceptionsWrapper
    def stage(self, data=None):
        # need to show alert via spawn in case a clear-messages event was just triggered
        if request:
            @catchLogExceptionsWrapper
            @copy_current_request_context
            def emit_alert_msg(self, msg_text):
                self._racecontext.rhui.emit_priority_message(msg_text, True, nobroadcast=True)

        data = self._filters.run_filters(Flt.RACE_STAGE, data)

        with (self._racecontext.rhdata.get_db_session_handle()):  # make sure DB session/connection is cleaned up

            if data and data.get('secondary_format'):
                self.format = self._racecontext.serverstate.secondary_race_format

            assigned_start_epoch = data.get('start_time_epoch_ms', False) if data else None
            if assigned_start_epoch:
                if data.get('correction_ms'):
                    assigned_start_epoch = assigned_start_epoch + data['correction_ms']

                assigned_start = self._racecontext.serverstate.epoch_millis_to_monotonic(
                    assigned_start_epoch)
            else:
                assigned_start = data.get('start_time_s', False) if data else None

            race_format = self.format
            if race_format is self._racecontext.serverstate.secondary_race_format and \
                    ((not data) or (not data.get('ignore_secondary_heat'))):
                # if running as secondary timer
                self.check_create_sec_format_heat()

            self._racecontext.rhdata.clear_lapSplits()  # clear lap-splits from previous race

            heat_data = self._racecontext.rhdata.get_heat(self.current_heat)

            if heat_data:
                heatNodes = self._racecontext.rhdata.get_heatNodes_by_heat(self.current_heat)

                if not heat_data.active:
                    logger.info("Canceling staging: Current heat is not active")
                    if request:
                        gevent.spawn(emit_alert_msg, self, \
                                 self._racecontext.language.__('Current heat is not active'))
                    return False

                saved_races = self._racecontext.rhdata.get_savedRaceMetas_by_heat(self.current_heat)
                if saved_races and heat_data.class_id:
                    raceclass = self._racecontext.rhdata.get_raceClass(heat_data.class_id)
                    if raceclass.round_type == RoundType.GROUPED:
                        logger.info("Canceling staging: Current heat has saved race and round type is groups")
                        if request:
                            gevent.spawn(emit_alert_msg, self, \
                                     self._racecontext.language.__('Current heat has saved race'))
                        return False

                pilot_names_list = []
                for heatNode in heatNodes:
                    if heatNode.node_index is not None and heatNode.node_index < self.num_nodes:
                        if heatNode.pilot_id != RHUtils.PILOT_ID_NONE:
                            pilot_obj = self._racecontext.rhdata.get_pilot(heatNode.pilot_id)
                            if pilot_obj and pilot_obj.callsign:
                                pilot_names_list.append(pilot_obj.callsign)

                if request and len(pilot_names_list) <= 0:
                    gevent.spawn(emit_alert_msg, self, \
                                 self._racecontext.language.__('No valid pilots in race'))

                logger.info("Staging new race, format: {}".format(getattr(race_format, "name", "????")))
                max_round = self._racecontext.rhdata.get_max_round(self.current_heat)
                if max_round is None:
                    max_round = 0
                logger.info("Racing heat '{}' round {}, pilots: {}".format(heat_data.display_name, (max_round+1),
                                                                           ", ".join(pilot_names_list)))
            else:
                heatNodes = []

                profile_freqs = json.loads(self.profile.frequencies)

                class FauxHeatNode():
                    node_index = None
                    pilot_id = 1

                for idx in range(self.num_nodes):
                    if (profile_freqs["f"][idx]):
                        heatNode = FauxHeatNode
                        heatNode.node_index = idx
                        heatNodes.append(heatNode)

            if self.race_status != RaceStatus.READY:
                if race_format is self._racecontext.serverstate.secondary_race_format:  # if running as secondary timer
                    if self.race_status == RaceStatus.RACING:
                        return  # if race in progress then leave it be
                    # if missed stop/discard message then clear current race
                    logger.info("Forcing race clear/restart because running as secondary timer")
                    self.discard_laps()
                elif self.race_status == RaceStatus.DONE and not self.any_laps_recorded():
                    self.discard_laps()  # if no laps then allow restart

            if self.race_status == RaceStatus.READY: # only initiate staging if ready
                # common race start events (do early to prevent processing delay when start is called)
                self._racecontext.interface.enable_calibration_mode() # Nodes reset triggers on next pass

                if race_format is not self._racecontext.serverstate.secondary_race_format: # don't enforce class format if running as secondary timer
                    if heat_data and heat_data.class_id != RHUtils.CLASS_ID_NONE:
                        class_format_id = self._racecontext.rhdata.get_raceClass(heat_data.class_id).format_id
                        if class_format_id != RHUtils.FORMAT_ID_NONE:
                            self.format = self._racecontext.rhdata.get_raceFormat(class_format_id)
                            self._racecontext.rhui.emit_current_laps()
                            logger.info("Forcing race format from class setting: '{0}' ({1})".format(self.format.name, self.format.id))

                self.clear_laps() # Clear laps before race start
                self.init_node_cross_fields()  # set 'cur_pilot_id' and 'cross' fields on nodes
                self._racecontext.last_race = None # clear all previous race data
                self.timer_running = False # indicate race timer not running
                self.race_status = RaceStatus.STAGING
                self.win_status = WinStatus.NONE
                self.race_winner_name = ''
                self.race_winner_phonetic = ''
                self.race_winner_lap_id = 0
                self.race_winner_pilot_id = RHUtils.PILOT_ID_NONE
                self.race_leader_lap = 0  # clear current race leader
                self.race_leader_pilot_id = RHUtils.PILOT_ID_NONE
                self.race_initial_pass_flag = False
                self.status_message = ''
                self.any_races_started = True

                self.set_race_format_time_fields(race_format, heat_data)

                self.init_node_finished_flags(heatNodes)

                self._racecontext.interface.set_race_status(RaceStatus.STAGING)
                self._racecontext.rhui.emit_current_laps() # Race page, blank laps to the web client
                self._racecontext.rhui.emit_current_leaderboard() # Race page, blank leaderboard to the web client
                self._racecontext.rhui.emit_race_status()

                assigned_start_ok_flag = False
                if assigned_start:
                    self.stage_time_monotonic = monotonic() + float(self._racecontext.serverconfig.get_item('GENERAL', 'RACE_START_DELAY_EXTRA_SECS'))
                    if assigned_start > self.stage_time_monotonic:
                        staging_tones = 0
                        hide_stage_timer = True
                        self.start_time_monotonic = assigned_start
                        assigned_start_ok_flag = True

                if not assigned_start_ok_flag:
                    staging_fixed_ms = (0 if race_format.staging_fixed_tones <= 1 else race_format.staging_fixed_tones - 1) * 1000

                    staging_random_ms = random.randint(0, race_format.start_delay_max_ms)
                    hide_stage_timer = (race_format.start_delay_max_ms > 0)

                    staging_total_ms = staging_fixed_ms + race_format.start_delay_min_ms + staging_random_ms

                    if race_format.staging_delay_tones == StagingTones.TONES_NONE:
                        if staging_total_ms > 0:
                            staging_tones = race_format.staging_fixed_tones
                        else:
                            staging_tones = staging_fixed_ms / 1000
                    else:
                        staging_tones = staging_total_ms // 1000
                        if staging_random_ms % 1000:
                            staging_tones += 1

                    self.stage_time_monotonic = monotonic() + float(self._racecontext.serverconfig.get_item('GENERAL', 'RACE_START_DELAY_EXTRA_SECS'))
                    self.start_time_monotonic = self.stage_time_monotonic + (staging_total_ms / 1000 )

                self.start_time_epoch_ms = self._racecontext.serverstate.monotonic_to_epoch_millis(self.start_time_monotonic)
                self.start_token = random.random()
                gevent.spawn(self.race_start_thread, self.start_token)

                # Announce staging with final parameters
                eventPayload = {
                    'hide_stage_timer': hide_stage_timer,
                    'pi_staging_at_s': self.stage_time_monotonic,
                    'server_staging_epoch_ms': self._racecontext.serverstate.monotonic_to_epoch_millis(self.stage_time_monotonic),
                    'staging_tones': staging_tones,
                    'pi_starts_at_s': self.start_time_monotonic,
                    'server_start_epoch_ms': self.start_time_epoch_ms,
                    'unlimited_time': self.unlimited_time,
                    'race_time_sec': self.race_time_sec,
                    'color': ColorVal.ORANGE,
                    'heat_id': self.current_heat,
                    'race_node_colors': self.seat_colors,
                }

                if self._racecontext.cluster:
                    splitsData = {}
                    splitsData['start_time_epoch_ms'] = self._racecontext.race.start_time_epoch_ms
                    self._racecontext.cluster.emitToSplits('stage_race', splitsData, addTimeCorrFlag=True)

                self._racecontext.events.trigger(Evt.RACE_STAGE, eventPayload)
                self._racecontext.rhui.emit_race_stage(eventPayload)

                if request and heat_data and race_format.race_time_sec == 0 and not race_format.unlimited_time:
                    logger.warning("Current race format '{}' specifies an invalid combination of RaceClockMode=FixedTime and TimeDuration=0".\
                                   format(race_format.name))
                    # need to show alert via spawn in case a clear-messages event was just triggered
                    gevent.spawn(emit_alert_msg, self, \
                                 self._racecontext.language.__('Current race format specifies fixed time with zero duration'))

            else:
                logger.info("Attempted to stage race while status is not 'ready'")

    def set_race_format_time_fields(self, race_format, heat_data):
        if race_format:
            self.unlimited_time = race_format.unlimited_time
            self.race_time_sec = race_format.race_time_sec
            # handle special case where co-op mode uses best-time value from heat:
            if race_format.team_racing_mode == RacingMode.COOP_ENABLED:
                if heat_data:
                    self._racecontext.rhdata.get_heat_coop_values(heat_data, self)
                    if race_format.win_condition == WinCondition.FIRST_TO_LAP_X and \
                                self.coop_best_time and self.coop_best_time > 0.001:
                        self.unlimited_time = False
                        self.race_time_sec = round(self.coop_best_time, 1)
                self.show_init_time_flag = True  # show 'race_time_sec' value on initial Run-page timer display (if nonzero)
            else:
                self.show_init_time_flag = False
        else:
            self.show_init_time_flag = False


    @catchLogExceptionsWrapper
    def race_start_thread(self, start_token):
        APP.app_context().push()
        with self._racecontext.rhdata.get_db_session_handle():  # make sure DB session/connection is cleaned up
            # clear any lingering crossings at staging (if node rssi < enterAt)
            for node in self._racecontext.interface.nodes:
                if node.crossing_flag and node.frequency > 0 and \
                    (self.format is self._racecontext.serverstate.secondary_race_format or \
                    (node.current_pilot_id != RHUtils.PILOT_ID_NONE and node.current_rssi < node.enter_at_level)):
                    logger.info("Forcing end crossing for node {0} at staging (rssi={1}, enterAt={2}, exitAt={3})".\
                               format(node.index+1, node.current_rssi, node.enter_at_level, node.exit_at_level))
                    self._racecontext.interface.force_end_crossing(node.index)

            if self._racecontext.cluster and self._racecontext.cluster.hasSecondaries():
                self._racecontext.cluster.doClusterRaceStart()

            # set lower EnterAt/ExitAt values if configured
            if self._racecontext.serverconfig.get_item_int('TIMING', 'startThreshLowerAmount') > 0 and self._racecontext.serverconfig.get_item_int('TIMING', 'startThreshLowerDuration') > 0:
                lower_amount = self._racecontext.serverconfig.get_item_int('TIMING', 'startThreshLowerAmount')
                logger.info("Lowering EnterAt/ExitAt values at start of race, amount={0}%, duration={1} secs".\
                            format(lower_amount, self._racecontext.serverconfig.get_item_int('TIMING', 'startThreshLowerDuration')))
                lower_end_time = self.start_time_monotonic + self._racecontext.serverconfig.get_item_int('TIMING', 'startThreshLowerDuration')
                for node in self._racecontext.interface.nodes:
                    if node.frequency > 0 and (self.format is self._racecontext.serverstate.secondary_race_format or node.current_pilot_id != RHUtils.PILOT_ID_NONE):
                        if node.current_rssi < node.enter_at_level:
                            diff_val = int((node.enter_at_level-node.exit_at_level)*lower_amount/100)
                            if diff_val > 0:
                                new_enter_at = node.enter_at_level - diff_val
                                new_exit_at = max(node.exit_at_level - diff_val, 0)
                                if node.api_valid_flag and node.is_valid_rssi(new_enter_at):
                                    logger.info("For node {0} lowering EnterAt from {1} to {2} and ExitAt from {3} to {4}"\
                                            .format(node.index+1, node.enter_at_level, new_enter_at, node.exit_at_level, new_exit_at))
                                    node.start_thresh_lower_time = lower_end_time  # set time when values will be restored
                                    node.start_thresh_lower_flag = True
                                    # use 'transmit_' instead of 'set_' so values are not saved in node object
                                    self._racecontext.interface.transmit_enter_at_level(node, new_enter_at)
                                    self._racecontext.interface.transmit_exit_at_level(node, new_exit_at)
                            else:
                                logger.info("Not lowering EnterAt/ExitAt values for node {0} because EnterAt value ({1}) unchanged"\
                                        .format(node.index+1, node.enter_at_level))
                        else:
                            logger.info("Not lowering EnterAt/ExitAt values for node {0} because current RSSI ({1}) >= EnterAt ({2})"\
                                    .format(node.index+1, node.current_rssi, node.enter_at_level))

            # do non-blocking delay before time-critical code
            while (monotonic() < self.start_time_monotonic - 0.5):
                gevent.sleep(0.1)

            if self.race_status == RaceStatus.STAGING and \
                self.start_token == start_token:
                # Only start a race if it is not already in progress
                # Null this thread if token has changed (race stopped/started quickly)

                # do blocking delay until race start
                while monotonic() < self.start_time_monotonic:
                    pass

                # !!! RACE STARTS NOW !!!

                # do time-critical tasks
                self._racecontext.events.trigger(Evt.RACE_START, {
                    'heat_id': self.current_heat,
                    'color': ColorVal.GREEN
                    })

                # do secondary start tasks (small delay is acceptable)
                self.start_time = datetime.now() # record start time as datetime object
                self.start_time_formatted = RHTimeFns.datetimeToFormattedStr(self.start_time) # record standard-formatted time

                for node in self._racecontext.interface.nodes:
                    node.history_values = [] # clear race history
                    node.history_times = []
                    node.under_min_lap_count = 0
                    # clear any lingering crossing (if rssi>enterAt then first crossing starts now)
                    if node.crossing_flag and node.frequency > 0 and (
                        self.format is self._racecontext.serverstate.secondary_race_format or node.current_pilot_id != RHUtils.PILOT_ID_NONE):
                        logger.info("Forcing end crossing for node {0} at start (rssi={1}, enterAt={2}, exitAt={3})".\
                                   format(node.index+1, node.current_rssi, node.enter_at_level, node.exit_at_level))
                        self._racecontext.interface.force_end_crossing(node.index)

                self.race_status = RaceStatus.RACING # To enable registering passed laps
                self._racecontext.interface.set_race_status(RaceStatus.RACING)
                self.timer_running = True # indicate race timer is running

                # kick off race expire processing
                race_format = self.format
                if race_format and race_format.unlimited_time == 0: # count down
                    gevent.spawn(self.race_expire_thread, start_token)

                self._racecontext.rhui.emit_race_status() # Race page, to set race button states
                logger.info('Race started at {:.3f} ({:.0f})'.format(self.start_time_monotonic, self.start_time_epoch_ms))
                logger.info('Race started at {:.3f} ({:.0f}) time={}'.format(self.start_time_monotonic, self.start_time_epoch_ms, \
                                                                                     self.start_time_formatted))

    @catchLogExceptionsWrapper
    def race_expire_thread(self, start_token):
        APP.app_context().push()
        with self._racecontext.rhdata.get_db_session_handle():  # make sure DB session/connection is cleaned up
            race_format = self.format
            if race_format and race_format.unlimited_time == 0: # count down
                gevent.sleep(race_format.race_time_sec)
                # if race still in progress and is still same race
                if self.race_status == RaceStatus.RACING and self.start_token == start_token:
                    logger.info("Race count-down timer reached expiration")
                    self.timer_running = False # indicate race timer no longer running
                    self._racecontext.events.trigger(Evt.RACE_FINISH, {
                        'heat_id': self.current_heat,
                        })
                    self.pass_invoke_func_queue_obj.waitForQueueEmpty()  # wait until any active pass-record processing is finished
                    self.check_win_condition(at_finish=True, start_token=start_token)
                    self._racecontext.rhui.emit_current_leaderboard()
                    if race_format.lap_grace_sec > -1:
                        gevent.sleep((self.start_time_monotonic + race_format.race_time_sec + race_format.lap_grace_sec) - monotonic())
                        if self.race_status == RaceStatus.RACING and self.start_token == start_token:
                            self.stop()
                            logger.debug("Race grace period reached")
                        else:
                            logger.debug("Grace period timer {} is unused".format(start_token))
                else:
                    logger.debug("Race-time-expire thread {} is unused".format(start_token))

    @catchLogExceptionsWrapper
    def stop(self, doSave=False):
        '''Stops the race and stops registering laps.'''
        with self._racecontext.rhdata.get_db_session_handle():  # make sure DB session/connection is cleaned up
            if self._racecontext.cluster:
                self._racecontext.cluster.emitToSplits('stop_race')

            if self.race_status == RaceStatus.RACING:
                # clear any crossings still in progress
                any_forced_flag = False
                for node in self._racecontext.interface.nodes:
                    if node.crossing_flag and node.frequency > 0 and \
                                    node.current_pilot_id != RHUtils.PILOT_ID_NONE:
                        logger.info("Forcing end crossing for node {} at race stop (rssi={}, enterAt={}, exitAt={})".\
                                    format(node.index+1, node.current_rssi, node.enter_at_level, node.exit_at_level))
                        self._racecontext.interface.force_end_crossing(node.index)
                        any_forced_flag = True
                if any_forced_flag:  # give forced end-crossings a chance to complete before stopping race
                    gevent.spawn_later(0.5, self.do_stop_race_actions_thread, doSave)
                else:
                    self.do_stop_race_actions(doSave)
            else:
                self.do_stop_race_actions(doSave)

            # Loop back to race page to stop the timer
            self._racecontext.rhui.emit_race_stop()

    def do_stop_race_actions_thread(self, doSave=False):
        with self._racecontext.rhdata.get_db_session_handle():  # make sure DB session/connection is cleaned up
            self.do_stop_race_actions(doSave)

    @catchLogExceptionsWrapper
    def do_stop_race_actions(self, doSave=False):
        if self.race_status == RaceStatus.RACING:
            self.end_time = monotonic() # Update the race end time stamp
            delta_time = self.end_time - self.start_time_monotonic
            end_time_ms = self._racecontext.serverstate.monotonic_to_epoch_millis(self.end_time)

            logger.info('Race stopped at {:.3f} ({:.0f}), time={}, duration {:.0f}s'.format(self.end_time, \
                                            end_time_ms, RHTimeFns.epochMsToFormattedStr(end_time_ms), delta_time))

            min_laps_list = []  # show nodes with laps under minimum (if any)
            for node in self._racecontext.interface.nodes:
                if node.under_min_lap_count > 0:
                    min_laps_list.append('Node {0} Count={1}'.format(node.index+1, node.under_min_lap_count))
            if len(min_laps_list) > 0:
                logger.info('Nodes with laps under minimum:  ' + ', '.join(min_laps_list))

            self.race_status = RaceStatus.DONE # To stop registering passed laps, waiting for laps to be cleared
            self._racecontext.interface.set_race_status(RaceStatus.DONE)

            self._racecontext.events.trigger(Evt.RACE_STOP, {
                'heat_id': self.current_heat,
                'color': ColorVal.RED
            })
            self.pass_invoke_func_queue_obj.waitForQueueEmpty()  # wait until any active pass-record processing is finished
            self.check_win_condition()

            if self._racecontext.cluster and self._racecontext.cluster.hasSecondaries():
                self._racecontext.cluster.doClusterRaceStop()

        elif self.race_status == RaceStatus.STAGING:
            logger.info('Stopping race during staging')
            self.race_status = RaceStatus.READY # Go back to ready state
            self._racecontext.interface.set_race_status(RaceStatus.READY)
            self._racecontext.events.trigger(Evt.LAPS_CLEAR)
            delta_time = 0

        else:
            self.race_status = RaceStatus.DONE # To stop registering passed laps, waiting for laps to be cleared
            self._racecontext.interface.set_race_status(RaceStatus.DONE)

            logger.debug('No active race to stop')
            delta_time = 0

        # check if nodes may be set to temporary lower EnterAt/ExitAt values (and still have them)
        if self._racecontext.serverconfig.get_item_int('TIMING', 'startThreshLowerAmount') > 0 and \
                delta_time < self._racecontext.serverconfig.get_item_int('TIMING', 'startThreshLowerDuration'):
            for node in self._racecontext.interface.nodes:
                # if node EnterAt/ExitAt values need to be restored then do it soon
                if node.frequency > 0 and (
                    self.format is self._racecontext.serverstate.secondary_race_format or (
                        node.current_pilot_id != RHUtils.PILOT_ID_NONE and \
                        node.start_thresh_lower_flag)):
                    node.start_thresh_lower_time = self.end_time + 0.1

        self.timer_running = False # indicate race timer not running
        self.scheduled = False # also stop any deferred start

        self._racecontext.rhui.emit_race_status() # Race page, to set race button states
        self._racecontext.rhui.emit_current_leaderboard()

        if doSave:
            # do with a bit of delay to prevent clearing results before stop event-actions can process them
            gevent.spawn_later(0.05, self.do_save_actions)

    @catchLogExceptionsWrapper
    def save(self):
        '''Handle "save" UI action'''

        if self.race_status == RaceStatus.RACING:
            self.stop(doSave=True)
        else:
            self.do_save_actions()

    @catchLogExceptionsWrapper
    def do_save_actions(self):
        '''Save current laps data to the database.'''
        with (self._racecontext.rhdata.get_db_session_handle()):  # make sure DB session/connection is cleaned up
            if self.current_heat == RHUtils.HEAT_ID_NONE:
                self.discard_laps(saved=True)
                return False

            if self.race_winner_pilot_id != RHUtils.PILOT_ID_NONE:
                self.prev_race_winner_name = self.race_winner_name
                self.prev_race_winner_phonetic = self.race_winner_phonetic
                self.prev_race_winner_pilot_id = self.race_winner_pilot_id

            if self._racecontext.cluster:
                self._racecontext.cluster.emitToSplits('save_laps')

            heat = self._racecontext.rhdata.get_heat(self.current_heat)

            # Clear caches
            heat_result = self._racecontext.rhdata.get_results_heat(self.current_heat)
            if heat.class_id:
                class_result = self._racecontext.rhdata.get_results_raceClass(heat.class_id)
            event_result = self._racecontext.rhdata.get_results_event()

            token = monotonic()
            self._racecontext.rhdata.clear_results_heat(self.current_heat, token)
            self._racecontext.rhdata.clear_results_raceClass(heat.class_id, token)
            self._racecontext.rhdata.clear_results_event(token)

            # Get the last saved round for the current heat
            max_round = self._racecontext.rhdata.get_max_round(self.current_heat)

            if max_round is None:
                max_round = 0
            # Loop through laps to copy to saved races
            profile = self.profile
            profile_freqs = json.loads(profile.frequencies)

            new_race_data = {
                'round_id': max_round+1,
                'heat_id': self.current_heat,
                'class_id': heat.class_id,
                'format_id': self.format.id if hasattr(self.format, 'id') else RHUtils.FORMAT_ID_NONE,
                'start_time': self.start_time_monotonic,
                'start_time_formatted': self.start_time_formatted,
                }

            new_race = self._racecontext.rhdata.add_savedRaceMeta(new_race_data)
            self.db_id = new_race.id

            race_data = {}

            for node_index in range(self.num_nodes):
                if profile_freqs["f"][node_index] != RHUtils.FREQUENCY_ID_NONE:
                    pilot_id = self._racecontext.rhdata.get_pilot_from_heatNode(self.current_heat, node_index)

                    if pilot_id is not None:
                        race_data[node_index] = {
                            'race_id': new_race.id,
                            'pilot_id': pilot_id,
                            'history_values': json.dumps(self._racecontext.interface.nodes[node_index].history_values),
                            'history_times': json.dumps(self._racecontext.interface.nodes[node_index].history_times),
                            'enter_at': self._racecontext.interface.nodes[node_index].enter_at_level,
                            'exit_at': self._racecontext.interface.nodes[node_index].exit_at_level,
                            'frequency': self._racecontext.interface.nodes[node_index].frequency,
                            'laps': self.node_laps[node_index]
                            }

                        self._racecontext.rhdata.set_pilot_used_frequency(pilot_id, {
                            'b': profile_freqs["b"][node_index],
                            'c': profile_freqs["c"][node_index],
                            'f': profile_freqs["f"][node_index]
                            })

            self._racecontext.rhdata.add_race_data(race_data)

            self._racecontext.events.trigger(Evt.LAPS_SAVE, {
                'race_id': new_race.id,
                })

            logger.info('Current laps saved: Heat {0} Round {1}'.format(self.current_heat, max_round+1))

            if self.format.team_racing_mode == RacingMode.COOP_ENABLED:
                self._racecontext.rhdata.update_heat_coop_values(heat, self.coop_best_time, self.coop_num_laps)
                # keep time fields in the current race in sync with the current race format
                self.set_race_format_time_fields(self.format, self.current_heat)
                self._racecontext.rhui.emit_heat_data()    # update displayed values
                self._racecontext.rhui.emit_race_status()

            result = self.get_results()
            if heat_result:
                self._racecontext.rhdata.set_results_heat(heat, token,
                    Results.build_incremental(self._racecontext, result, heat_result))
            else:
                self._racecontext.rhdata.get_results_heat(self.current_heat)

            if heat.class_id:
                if class_result:
                    self._racecontext.rhdata.set_results_raceClass(heat.class_id, token,
                        Results.build_incremental(self._racecontext, result, class_result))
                else:
                    self._racecontext.rhdata.get_results_raceClass(heat.class_id)

            if event_result:
                self._racecontext.rhdata.set_results_event(token,
                    Results.build_incremental(self._racecontext, result, event_result))
            else:
                self._racecontext.rhdata.get_results_event()

            self.discard_laps(saved=True) # Also clear the current laps

            regen_heat = False
            if heat.class_id:
                raceclass = self._racecontext.rhdata.get_raceClass(heat.class_id)
                if raceclass.round_type == RoundType.GROUPED:
                    if raceclass.rounds == 0 or heat.group_id + 1 < raceclass.rounds:
                        # Regenerate to new heat + group
                        regen_heat = self._racecontext.rhdata.duplicate_heat(heat, new_heat_name=heat.name, group_id=heat.group_id + 1)

                    # Deactivate current heat
                    self._racecontext.rhdata.alter_heat({
                        'heat': heat.id,
                        'active': False
                    }, mute_event=True if regen_heat is False else True)

                    self._racecontext.rhui.emit_heat_data()

            next_heat = self._racecontext.rhdata.get_next_heat_id(heat, regen_heat)

            if next_heat is not heat.id:
                self.set_heat(next_heat)

            # spawn thread for updating results caches
            gevent.spawn(self.rebuild_page_cache)

            self._racecontext.rhui.emit_race_saved(new_race, race_data)

    def rebuild_page_cache(self):
        self._racecontext.pagecache.set_valid(False)
        self._racecontext.rhui.emit_result_data()

    @catchLogExceptionsWrapper
    def build_atomic_result_caches(self, params):
        with self._racecontext.rhdata.get_db_session_handle():  # make sure DB session/connection is cleaned up
            self._racecontext.pagecache.set_valid(False)
            Results.build_atomic_results(self._racecontext.rhdata, params)
            self._racecontext.rhui.emit_result_data()

    @catchLogExceptionsWrapper
    def add_lap(self, node, lap_timestamp_absolute, source):
        '''Handles pass records from the nodes.'''
        APP.app_context().push()

        with self._racecontext.rhdata.get_db_session_handle():  # make sure DB session/connection is cleaned up

            logger.debug('Pass record: Node={}, abs_ts={:.3f}, source={} ("{}")' \
                         .format(node.index+1, lap_timestamp_absolute, source, self._racecontext.interface.get_lap_source_str(source)))
            node.pass_crossing_flag = False  # clear the "synchronized" version of the crossing flag
            node.debug_pass_count += 1
            self._racecontext.rhui.emit_node_data() # For updated triggers and peaks

            profile_freqs = json.loads(self.profile.frequencies)
            if profile_freqs["f"][node.index] != RHUtils.FREQUENCY_ID_NONE :
                # always count laps if race is running, otherwise test if lap should have counted before race end
                if self.race_status is RaceStatus.RACING \
                    or (self.race_status is RaceStatus.DONE and \
                        lap_timestamp_absolute < self.end_time):

                    # Get the current pilot id on the node
                    pilot_id = self._racecontext.rhdata.get_pilot_from_heatNode(self.current_heat, node.index)

                    # reject passes before race start and with disabled (no-pilot) nodes
                    race_format = self.format
                    if (pilot_id is not None and pilot_id != RHUtils.PILOT_ID_NONE) or race_format is self._racecontext.serverstate.secondary_race_format or self.current_heat is RHUtils.HEAT_ID_NONE:
                        if lap_timestamp_absolute >= self.start_time_monotonic:

                            # if node EnterAt/ExitAt values need to be restored then do it soon
                            if node.start_thresh_lower_flag:
                                node.start_thresh_lower_time = monotonic()

                            lap_time_stamp = (lap_timestamp_absolute - self.start_time_monotonic)
                            lap_time_stamp *= 1000 # store as milliseconds

                            lap_number = len(self.get_active_laps()[node.index])

                            if lap_number: # This is a normal completed lap
                                # Find the time stamp of the last lap completed (including "late" laps for timing)
                                last_lap_time_stamp = self.get_active_laps(True)[node.index][-1].lap_time_stamp

                                # New lap time is the difference between the current time stamp and the last
                                lap_time = lap_time_stamp - last_lap_time_stamp

                            else: # No previous laps, this is the first pass
                                # Lap zero represents the time from the launch pad to flying through the gate
                                lap_time = lap_time_stamp
                                node.first_cross_flag = True  # indicate first crossing completed

                            if race_format is self._racecontext.serverstate.secondary_race_format:
                                min_lap = 0  # don't enforce min-lap time if running as secondary timer
                                min_lap_behavior = 0
                            else:
                                min_lap = self._racecontext.rhdata.get_optionInt("MinLapSec")
                                min_lap_behavior = self._racecontext.serverconfig.get_item_int('TIMING', "MinLapBehavior")

                            lap_time_fmtstr = RHUtils.format_time_to_str(lap_time, self._racecontext.serverconfig.get_item('UI', 'timeFormat'))
                            lap_ts_fmtstr = RHUtils.format_time_to_str(lap_time_stamp, self._racecontext.serverconfig.get_item('UI', 'timeFormat'))
                            pilot_obj = self._racecontext.rhdata.get_pilot(pilot_id)
                            if pilot_obj:
                                pilot_namestr = pilot_obj.callsign
                            else:
                                if (profile_freqs["b"][node.index] and profile_freqs["c"][node.index]):
                                    pilot_namestr = profile_freqs["b"][node.index] + str(profile_freqs["c"][node.index])
                                else:
                                    pilot_namestr = str(profile_freqs["f"][node.index])

                            lap_ok_flag = True
                            lap_late_flag = False
                            pilot_done_flag = False
                            if lap_number != 0:  # if initial lap then always accept and don't check lap time; else:
                                if lap_time <= 0: # if lap is non-sequential
                                    logger.info('Ignoring lap prior to already recorded lap: Node={}, lap={}, lapTime={}, sinceStart={}, source={}, pilot: {}' \
                                               .format(node.index+1, lap_number, \
                                                       lap_time_fmtstr, lap_ts_fmtstr, \
                                                       self._racecontext.interface.get_lap_source_str(source), \
                                                       pilot_namestr))
                                    lap_ok_flag = False

                                if lap_ok_flag and lap_time < (min_lap * 1000):  # if lap time less than minimum
                                    node.under_min_lap_count += 1
                                    logger.info('Pass record under lap minimum ({}): Node={}, lap={}, lapTime={}, sinceStart={}, count={}, source={}, pilot: {}' \
                                               .format(min_lap, node.index+1, lap_number, \
                                                       lap_time_fmtstr, lap_ts_fmtstr, \
                                                       node.under_min_lap_count, self._racecontext.interface.get_lap_source_str(source), \
                                                       pilot_namestr))
                                    if min_lap_behavior != 0:  # if behavior is 'Discard New Short Laps'
                                        lap_ok_flag = False

                                if lap_ok_flag and race_format.unlimited_time == 0 and \
                                    race_format.lap_grace_sec > -1 and \
                                    lap_time_stamp > (race_format.race_time_sec + race_format.lap_grace_sec)*1000:
                                    logger.info('Ignoring lap after grace period expired: Node={}, lap={}, lapTime={}, sinceStart={}, source={}, pilot: {}' \
                                               .format(node.index+1, lap_number, lap_time_fmtstr, lap_ts_fmtstr, \
                                                       self._racecontext.interface.get_lap_source_str(source), pilot_namestr))
                                    lap_ok_flag = False

                            if lap_ok_flag:
                                node_finished_flag = self.get_node_finished_flag(node.index)
                                if not node_finished_flag:
                                    # set next node race status as 'finished' if timer mode is count-down race and race-time has expired
                                    if race_format.unlimited_time == 0 and lap_time_stamp > race_format.race_time_sec * 1000:
                                        pilot_done_flag = True
                                    elif self.format.win_condition == WinCondition.FIRST_TO_LAP_X:
                                        if race_format.start_behavior != StartBehavior.FIRST_LAP:
                                            if lap_number >= race_format.number_laps_win:
                                                pilot_done_flag = True
                                        else:
                                            if lap_number + 1 >= race_format.number_laps_win:
                                                pilot_done_flag = True
                                else:
                                    lap_late_flag = True  # "late" lap pass (after grace lap)
                                    logger.info('Ignoring lap after pilot done: Node={}, lap={}, lapTime={}, sinceStart={}, source={}, pilot: {}' \
                                               .format(node.index+1, lap_number, lap_time_fmtstr, lap_ts_fmtstr, \
                                                       self._racecontext.interface.get_lap_source_str(source), pilot_namestr))

                                if self.win_status == WinStatus.DECLARED and race_format.unlimited_time == 1 and \
                                                            self.format.win_condition == WinCondition.FIRST_TO_LAP_X:
                                    if self.format.team_racing_mode == RacingMode.TEAM_ENABLED:
                                        lap_late_flag = True  # "late" lap pass after team race winner declared (when no time limit)
                                        if pilot_obj:
                                            t_str = ", Team " + pilot_obj.team
                                        else:
                                            t_str = ""
                                        logger.info('Ignoring lap after race winner declared: Node={}, lap={}, lapTime={}, sinceStart={}, source={}, pilot: {}{}' \
                                                   .format(node.index+1, lap_number, lap_time_fmtstr, lap_ts_fmtstr, \
                                                           self._racecontext.interface.get_lap_source_str(source), pilot_namestr, t_str))
                                    elif self.format.team_racing_mode == RacingMode.COOP_ENABLED:
                                        lap_late_flag = True  # "late" lap pass after co-op race done (when no time limit)
                                        logger.info('Ignoring lap after co-op race done: Node={}, lap={}, lapTime={}, sinceStart={}, source={}, pilot: {}' \
                                                   .format(node.index+1, lap_number, lap_time_fmtstr, lap_ts_fmtstr, \
                                                           self._racecontext.interface.get_lap_source_str(source), pilot_namestr))

                                if logger.getEffectiveLevel() <= logging.DEBUG:  # if DEBUG msgs actually being logged
                                    late_str = " (late lap)" if lap_late_flag else ""
                                    enter_fmtstr = RHUtils.format_time_to_str((node.enter_at_timestamp-self.start_time_monotonic)*1000, \
                                                                       self._racecontext.serverconfig.get_item('UI', 'timeFormat')) \
                                                   if node.enter_at_timestamp else "0"
                                    exit_fmtstr = RHUtils.format_time_to_str((node.exit_at_timestamp-self.start_time_monotonic)*1000, \
                                                                      self._racecontext.serverconfig.get_item('UI', 'timeFormat')) \
                                                   if node.exit_at_timestamp else "0"
                                    logger.debug('Lap pass{}: Node={}, lap={}, lapTime={}, sinceStart={}, abs_ts={:.3f}, passtime={}, source={}, enter={}, exit={}, dur={:.0f}ms, pilot: {}' \
                                                .format(late_str, node.index+1, lap_number, lap_time_fmtstr, lap_ts_fmtstr, \
                                                        lap_timestamp_absolute,
                                                        RHTimeFns.epochMsToFormattedStr(self._racecontext.serverstate.monotonic_to_epoch_millis(lap_timestamp_absolute)), \
                                                        self._racecontext.interface.get_lap_source_str(source), \
                                                        enter_fmtstr, exit_fmtstr, \
                                                        (node.exit_at_timestamp-node.enter_at_timestamp)*1000, pilot_namestr))

                                # emit 'pass_record' message (to primary timer in cluster, livetime, etc).
                                self._racecontext.rhui.emit_pass_record(node, lap_time_stamp)

                                # Add the new lap to the database
                                lap_data = Crossing()
                                lap_data.lap_number = lap_number
                                lap_data.lap_time_stamp = lap_time_stamp
                                lap_data.lap_time = lap_time
                                lap_data.lap_time_formatted = lap_time_fmtstr
                                lap_data.source = source
                                lap_data.deleted = lap_late_flag  # delete if lap pass is after race winner declared
                                lap_data.late_lap = lap_late_flag

                                self.node_laps[node.index].append(lap_data)

                                self.clear_results()

                                self._racecontext.events.trigger(Evt.RACE_LAP_RECORDED, {
                                    'pilot_id': pilot_id,
                                    'node_index': node.index,
                                    'peak_rssi': node.pass_peak_rssi,
                                    'frequency': node.frequency,
                                    'color': self.seat_colors[node.index],
                                    'lap': lap_data,
                                    'results': self.get_results(),
                                    'gap_info': Results.get_gap_info(self._racecontext, node.index),
                                    'pilot_done_flag': pilot_done_flag,
                                    })

                                self._racecontext.rhui.emit_current_laps() # update all laps on the race page
                                self._racecontext.rhui.emit_current_leaderboard() # generate and update leaderboard

                                if lap_number == 0:
                                    self._racecontext.rhui.emit_first_pass_registered(node.index) # play first-pass sound
                                    if not self.race_initial_pass_flag:
                                        self.race_initial_pass_flag = True
                                        self._racecontext.events.trigger(Evt.RACE_INITIAL_PASS)

                                if race_format.start_behavior == StartBehavior.FIRST_LAP:
                                    lap_number += 1

                                # announce lap
                                if lap_number > 0:
                                    check_leader = race_format.win_condition != WinCondition.NONE and \
                                                   self.win_status != WinStatus.DECLARED
                                    # announce pilot lap number unless winner declared and pilot has finished final lap
                                    lap_id = lap_number if self.win_status != WinStatus.DECLARED or \
                                                           (not node_finished_flag) else None
                                    if race_format.team_racing_mode == RacingMode.TEAM_ENABLED:
                                        team_name = pilot_obj.team if pilot_obj else ""
                                        team_laps = self.team_results['meta']['teams'][team_name]['laps']
                                        if not lap_late_flag:
                                            logger.debug('Lap pass: Node={}, lap={}, pilot={} -> Team {} lap {}' \
                                                  .format(node.index+1, lap_number, pilot_namestr, team_name, team_laps))
                                        # if winning team has been declared then don't announce team lap number
                                        if self.win_status == WinStatus.DECLARED:
                                            team_phonetic = ' '
                                        else:
                                            team_phonetic = self.__("Team") + " " + team_name + ", " + self.__("Lap") + \
                                                            " " + str(team_laps)
                                        self._racecontext.rhui.emit_phonetic_data(pilot_id, lap_id, lap_time, team_phonetic, \
                                                        (check_leader and \
                                                         team_name == Results.get_leading_team_name(self.team_results)), \
                                                        node_finished_flag, node.index)
                                    elif race_format.team_racing_mode == RacingMode.COOP_ENABLED:
                                        coop_laps = self.team_results['by_race_time'][0]['laps']
                                        if not lap_late_flag:
                                            logger.debug('Lap pass: Node={}, lap={}, pilot={} -> Co-op lap {}' \
                                                         .format(node.index+1, lap_number, pilot_namestr, coop_laps))
                                        # if win has been declared then don't announce coop lap number
                                        if self.win_status == WinStatus.DECLARED:
                                            team_phonetic = ' '
                                        else:
                                            team_phonetic =  self.__("Co-op") + " " +  self.__("Lap") + " " + str(coop_laps)
                                        self._racecontext.rhui.emit_phonetic_data(pilot_id, lap_id, lap_time, \
                                                                                  team_phonetic, False, node_finished_flag, node.index)
                                    else:
                                        if check_leader:
                                            leader_pilot_id = Results.get_leading_pilot_id(self, self._racecontext.interface, True)
                                        else:
                                            leader_pilot_id = RHUtils.PILOT_ID_NONE
                                        self._racecontext.rhui.emit_phonetic_data(pilot_id, lap_id, lap_time, None, \
                                                        (pilot_id == leader_pilot_id), node_finished_flag, node.index)
                                        if leader_pilot_id != RHUtils.PILOT_ID_NONE:
                                            # if new leading pilot was not called out above (different pilot) then call out now
                                            if leader_pilot_id != pilot_id:
                                                self._racecontext.rhui.emit_phonetic_leader(leader_pilot_id)
                                                leader_pilot_obj = self._racecontext.rhdata.get_pilot(leader_pilot_id)
                                                if leader_pilot_obj:
                                                    logger.info('Pilot {} is leading'.format(leader_pilot_obj.callsign))
                                            else:
                                                logger.info('Pilot {} is leading'.format(pilot_namestr))
                                            self._racecontext.events.trigger(Evt.RACE_PILOT_LEADING, {
                                                'pilot_id': leader_pilot_id,
                                                'node_index': self._racecontext.rhdata.get_node_idx_from_heatNode(\
                                                                              self.current_heat, leader_pilot_id)
                                            })

                                    # check for and announce possible winner and trigger possible pilot-done events
                                    #  (but wait until pass-record processings are finished)
                                    self.pass_invoke_func_queue_obj.put(self.finish_add_lap_processing, \
                                                    pilot_done_flag, pilot_id, pilot_obj, node, emit_leaderboard_on_win=True)

                            else:
                                # record lap as 'invalid'
                                lap_data = Crossing()
                                lap_data.lap_number = lap_number
                                lap_data.lap_time_stamp = lap_time_stamp
                                lap_data.lap_time = lap_time
                                lap_data.lap_time_formatted = lap_time_fmtstr
                                lap_data.source = source
                                lap_data.deleted = True
                                lap_data.invalid = True

                                self.node_laps[node.index].append(lap_data)
                        else:
                            logger.debug('Pass record dismissed: Node {}, Race not started (abs_ts={:.3f}, source={})' \
                                .format(node.index+1, lap_timestamp_absolute, self._racecontext.interface.get_lap_source_str(source)))
                    else:
                        logger.debug('Pass record dismissed: Node {}, Pilot not defined (abs_ts={:.3f}, source={})' \
                            .format(node.index+1, lap_timestamp_absolute, self._racecontext.interface.get_lap_source_str(source)))
            else:
                logger.debug('Pass record dismissed: Node {}, Frequency not defined (abs_ts={:.3f}, source={})' \
                    .format(node.index+1, lap_timestamp_absolute, self._racecontext.interface.get_lap_source_str(source)))

    # check for and announce possible winner and trigger possible pilot-done events
    @catchLogExceptionsWrapper
    def finish_add_lap_processing(self, pilot_done_flag, done_pilot_id, done_pilot_obj, done_node_obj, **kwargs):
        prev_node_finished_flag = self.get_node_finished_flag(done_node_obj.index)
        if pilot_done_flag and not prev_node_finished_flag:
            self.set_node_finished_flag(done_node_obj.index)
        self.check_win_condition(**kwargs)  # check for and announce possible winner
        if self.win_status != WinStatus.PENDING_CROSSING:  # if not waiting for crossings to finish
            any_done_flag = False
            if pilot_done_flag and not prev_node_finished_flag:  # if pilot just finished race
                logger.info('Pilot {} done'.format(done_pilot_obj.callsign if done_pilot_obj else done_node_obj.index))
                self._racecontext.events.trigger(Evt.RACE_PILOT_DONE, {
                    'pilot_id': done_pilot_id,
                    'node_index': done_node_obj.index,
                    'color': self.seat_colors[done_node_obj.index],
                    'results': self.get_results(),
                })
                self.set_node_finished_effect_flag(done_node_obj.index)  # indicate pilot-finished event was triggered
                any_done_flag = True
            # check if any pilot-finished events were waiting for crossings to finish, and trigger them now if so
            if self.win_status == WinStatus.DECLARED and self.node_fin_effect_wait_count > 0:
                for chk_node in self._racecontext.interface.nodes:
                    if chk_node.current_pilot_id != RHUtils.PILOT_ID_NONE and \
                                    self.get_node_finished_flag(chk_node.index) and \
                                    not self.get_node_finished_effect_flag(chk_node.index):
                        chk_pilot_obj = self._racecontext.rhdata.get_pilot(chk_node.current_pilot_id)
                        logger.info('Pilot {} done (after all crossings completed)'.format(chk_pilot_obj.callsign if chk_pilot_obj else chk_node.index))
                        self._racecontext.events.trigger(Evt.RACE_PILOT_DONE, {
                            'pilot_id': chk_node.current_pilot_id,
                            'node_index': chk_node.index,
                            'color': self.seat_colors[chk_node.index],
                            'results': self.get_results(),
                        })
                        self.set_node_finished_effect_flag(chk_node.index)  # indicate pilot-finished event was triggered
                        self.node_fin_effect_wait_count -= 1
                        any_done_flag = True
            if any_done_flag:
                gevent.spawn(self.update_leaderboard_after_done)
        elif pilot_done_flag and not prev_node_finished_flag:  # if pilot just finished race
            self.node_fin_effect_wait_count += 1
            logger.debug('Waiting to process node {} done until all crossings completed'.format(done_node_obj.index+1))

    # update leaderboard to reflect pilot just finished (done)
    @catchLogExceptionsWrapper
    def update_leaderboard_after_done(self):
        gevent.sleep(0.001)
        wait_count = 0  # if 'calc_leaderboard_fn' in progress then let it finish
        while Results.is_in_calc_leaderboard_fn():
            gevent.sleep(0.01)
            wait_count += 1
            if wait_count > 1000:  # timeout after 10 seconds
                logger.error("update_leaderboard_after_done: Timeout waiting for invocation of 'calc_leaderboard()' to finish{}")
                break
        self.clear_results()
        self._racecontext.rhui.emit_current_laps() # update all laps on the race page
        self._racecontext.rhui.emit_current_leaderboard() # generate and update leaderboard

    @catchLogExceptionsWrapper
    def delete_lap(self, data):
        '''Delete a false lap.'''

        with self._racecontext.rhdata.get_db_session_handle():  # make sure DB session/connection is cleaned up

            node_index = data['node']
            lap_index = data['lap_index']

            if node_index is None or lap_index is None:
                logger.error("Bad parameter in 'on_delete_lap()':  node_index={0}, lap_index={1}".format(node_index, lap_index))
                return

            self.node_laps[node_index][lap_index].invalid = True

            time = self.node_laps[node_index][lap_index].lap_time_stamp

            race_format = self.format
            self.set_node_finished_flag(node_index, False)
            lap_number = 0
            for lap in self.node_laps[node_index]:
                lap.deleted = False
                if self.get_node_finished_flag(node_index):
                    lap.late_lap = True
                    lap.deleted = True
                else:
                    lap.late_lap = False

                if lap.invalid:
                    lap.lap_number = None
                    lap.deleted = True
                else:
                    lap.lap_number = lap_number
                    if race_format.unlimited_time == 0 and lap.lap_time_stamp > (race_format.race_time_sec * 1000) or \
                        (race_format.win_condition == WinCondition.FIRST_TO_LAP_X and lap_number >= race_format.number_laps_win):
                        self.set_node_finished_flag(node_index)
                    lap_number += 1

            db_last = False
            db_next = False
            for lap in self.node_laps[node_index]:
                if not lap.invalid and ((not lap.deleted) or lap.late_lap):
                    if lap.lap_time_stamp < time:
                        db_last = lap
                    if lap.lap_time_stamp > time:
                        db_next = lap
                        break

            if db_next and db_last:
                db_next.lap_time = db_next.lap_time_stamp - db_last.lap_time_stamp
                db_next.lap_time_formatted = RHUtils.format_time_to_str(db_next.lap_time, self._racecontext.serverconfig.get_item('UI', 'timeFormat'))
            elif db_next:
                db_next.lap_time = db_next.lap_time_stamp
                db_next.lap_time_formatted = RHUtils.format_time_to_str(db_next.lap_time, self._racecontext.serverconfig.get_item('UI', 'timeFormat'))

            try:  # delete any split laps for deleted lap
                lap_splits = self._racecontext.rhdata.get_lapSplits_by_lap(node_index, lap_number)
                if lap_splits and len(lap_splits) > 0:
                    for lap_split in lap_splits:
                        self._racecontext.rhdata.clear_lapSplit(lap_split)
            except:
                logger.exception("Error deleting split laps")

            self._racecontext.events.trigger(Evt.LAP_DELETE, {
                'node_index': node_index,
                })

            logger.info('Lap deleted: Node {0} LapIndex {1}'.format(node_index+1, lap_index))

            self.clear_results()
            self.pass_invoke_func_queue_obj.waitForQueueEmpty()  # wait until any active pass-record processing is finished
            self.get_results()  # update leaderboard before checking possible updated winner/leader
            self.check_win_condition(deletedLap=True)  # handle possible change in win status

            # handle possible change in race leader
            if race_format.team_racing_mode == RacingMode.INDIVIDUAL:
                leader_pilot_id = Results.get_leading_pilot_id(self, self._racecontext.interface, True)
                if leader_pilot_id != RHUtils.PILOT_ID_NONE:
                    self._racecontext.rhui.emit_phonetic_leader(leader_pilot_id)
                    leader_pilot_obj = self._racecontext.rhdata.get_pilot(leader_pilot_id)
                    if leader_pilot_obj:
                        logger.info('Pilot {} is leading (after deleted lap)'.format(leader_pilot_obj.callsign))

            self._racecontext.rhui.emit_current_laps() # Race page, update web client
            self._racecontext.rhui.emit_current_leaderboard() # Race page, update web client

    @catchLogExceptionsWrapper
    def restore_deleted_lap(self, data):
        '''Restore a deleted (or "late") lap.'''

        with self._racecontext.rhdata.get_db_session_handle():  # make sure DB session/connection is cleaned up

            node_index = data['node']
            lap_index = data['lap_index']

            if node_index is None or lap_index is None:
                logger.error("Bad parameter in 'on_restore_deleted_lap()':  node_index={0}, lap_index={1}".format(node_index, lap_index))
                return

            lap_obj = self.node_laps[node_index][lap_index]

            lap_obj.deleted = False
            lap_obj.late_lap = False

            lap_number = 0  # adjust lap numbers and times as needed
            last_lap_ts = 0
            for idx, lap in enumerate(self.node_laps[node_index]):
                if not lap.deleted:
                    if idx >= lap_index:
                        lap.lap_number = lap_number
                        lap.lap_time = lap.lap_time_stamp - last_lap_ts
                        lap.lap_time_formatted = RHUtils.format_time_to_str(lap.lap_time, self._racecontext.serverconfig.get_item('UI', 'timeFormat'))
                    last_lap_ts = lap.lap_time_stamp
                    lap_number += 1

            self._racecontext.events.trigger(Evt.LAP_RESTORE_DELETED, {
                'node_index': node_index,
                })

            logger.info('Restored deleted lap: Node {0} LapIndex {1}'.format(node_index+1, lap_index))

            self.clear_results()
            self.pass_invoke_func_queue_obj.waitForQueueEmpty()  # wait until any active pass-record processing is finished
            self.get_results()  # update leaderboard before checking possible updated winner/leader
            self.check_win_condition(deletedLap=True)  # handle possible change in win status

            # handle possible change in race leader
            if self.format and self.format.team_racing_mode == RacingMode.INDIVIDUAL:
                leader_pilot_id = Results.get_leading_pilot_id(self, self._racecontext.interface, True)
                if leader_pilot_id != RHUtils.PILOT_ID_NONE:
                    self._racecontext.rhui.emit_phonetic_leader(leader_pilot_id)
                    leader_pilot_obj = self._racecontext.rhdata.get_pilot(leader_pilot_id)
                    if leader_pilot_obj:
                        logger.info('Pilot {} is leading (after deleted lap)'.format(leader_pilot_obj.callsign))

            self._racecontext.rhui.emit_current_laps() # Race page, update web client
            self._racecontext.rhui.emit_current_leaderboard() # Race page, update web client

    @catchLogExceptionsWrapper
    def discard_laps(self, **kwargs):
        '''Clear the current laps without saving.'''

        with self._racecontext.rhdata.get_db_session_handle():  # make sure DB session/connection is cleaned up

            if self.race_status == RaceStatus.STAGING or self.race_status == RaceStatus.RACING:
                self.stop()

            self.clear_laps()
            self.race_status = RaceStatus.READY # Flag status as ready to start next race
            self._racecontext.interface.set_race_status(RaceStatus.READY)
            self.win_status = WinStatus.NONE
            self.race_winner_name = ''
            self.race_winner_phonetic = ''
            self.race_winner_lap_id = 0
            self.race_winner_pilot_id = RHUtils.PILOT_ID_NONE
            self.race_leader_lap = 0  # clear current race leader
            self.race_leader_pilot_id = RHUtils.PILOT_ID_NONE
            self.race_initial_pass_flag = False
            self.status_message = ''
            self._racecontext.rhui.emit_current_laps() # Race page, blank laps to the web client
            self._racecontext.rhui.emit_current_leaderboard() # Race page, blank leaderboard to the web client
            self._racecontext.rhui.emit_race_status() # Race page, to set race button states

            if 'saved' in kwargs and kwargs['saved'] == True:
                # discarding follows a save action
                pass
            else:
                # discarding does not follow a save action
                self._racecontext.events.trigger(Evt.LAPS_DISCARD)
                if self._racecontext.cluster:
                    self._racecontext.cluster.emitToSplits('discard_laps')

            self._racecontext.events.trigger(Evt.LAPS_CLEAR)

    def clear_laps(self):
        '''Clear the current laps table.'''
        self._racecontext.branch_race_obj()
        self.db_id = None
        self.reset_current_laps() # Clear out the current laps table
        logger.info('Current laps cleared')

    def reset_current_laps(self):
        '''Resets database current laps to default.'''
        self.node_laps = {}
        for idx in range(self.num_nodes):
            self.node_laps[idx] = []

        self.clear_results()
        logger.debug('Database current laps reset')

    def init_node_cross_fields(self):
        '''Sets the 'current_pilot_id' and 'cross' values on each node.'''
        for node in self._racecontext.interface.nodes:
            node.current_pilot_id = RHUtils.PILOT_ID_NONE
            if node.frequency and node.frequency > 0:
                if self.current_heat is not RHUtils.HEAT_ID_NONE:
                    heatnodes = self._racecontext.rhdata.get_heatNodes_by_heat(self.current_heat)
                    for heatnode in heatnodes:
                        if heatnode.node_index == node.index:
                            node.current_pilot_id = heatnode.pilot_id
                            break

            node.first_cross_flag = False
            node.show_crossing_flag = False

    def schedule(self, s, m=0):
        with self._racecontext.rhdata.get_db_session_handle():  # make sure DB session/connection is cleaned up

            if self.race_status != RaceStatus.READY:
                logger.warning("Ignoring request to schedule race: Status not READY")
                return False

            if s or m:
                self.scheduled = True
                self.scheduled_time = monotonic() + (int(m) * 60) + int(s)

                self._racecontext.events.trigger(Evt.RACE_SCHEDULE, {
                    'scheduled_at': self.scheduled_time,
                    'heat_id': self.current_heat,
                    })

                self._racecontext.rhui.emit_priority_message(self.__("Next race begins in {0:01d}:{1:02d}".format(int(m), int(s))), True)

                logger.info("Scheduling race in {0:01d}:{1:02d}".format(int(m), int(s)))
            else:
                self.scheduled = False
                self._racecontext.events.trigger(Evt.RACE_SCHEDULE_CANCEL, {
                    'heat_id': self.current_heat,
                    })
                self._racecontext.rhui.emit_priority_message(self.__("Scheduled race cancelled"), False)

            self._racecontext.rhui.emit_race_schedule()
            return True

    def init_node_finished_flags(self, heatNodes):
        self.node_has_finished = {}
        for heatNode in heatNodes:
            if heatNode.node_index is not None and heatNode.node_index < self.num_nodes:
                if heatNode.pilot_id != RHUtils.PILOT_ID_NONE:
                    self.node_has_finished[heatNode.node_index] = False
                else:
                    self.node_has_finished[heatNode.node_index] = None
                self.node_finished_effect[heatNode.node_index] = False
                self.node_fin_effect_wait_count = 0

    def set_node_finished_flag(self, node_index, value=True):
        self.node_has_finished[node_index] = value

    def get_node_finished_flag(self, node_index):
        return self.node_has_finished.get(node_index, None)

    def check_all_nodes_finished(self):
        return False not in self.node_has_finished.values()

    def set_node_finished_effect_flag(self, node_index, value=True):
        self.node_finished_effect[node_index] = value

    def get_node_finished_effect_flag(self, node_index):
        return self.node_finished_effect.get(node_index)

    def check_win_condition(self, **kwargs):
        previous_win_status = self.win_status
        win_not_decl_flag = self.win_status in [WinStatus.NONE, WinStatus.PENDING_CROSSING, WinStatus.OVERTIME]
        del_lap_flag = 'deletedLap' in kwargs
        logger.debug("Entered 'check_win_condition()', win_status={}, win_not_decl_flag={}, del_lap_flag={}".\
                     format(self.win_status, win_not_decl_flag, del_lap_flag))

        # if winner not yet declared or racer lap was deleted then check win condition
        win_status_dict = Results.check_win_condition_result(self._racecontext, **kwargs) \
                          if win_not_decl_flag or del_lap_flag else None

        if win_status_dict is not None:
            logger.debug("In 'check_win_condition()', win_status_dict: {}".format(win_status_dict))
            race_format = self.format
            self.win_status = win_status_dict['status']

            if self.win_status != WinStatus.NONE and logger.getEffectiveLevel() <= logging.DEBUG:
                logger.debug("Pilot lap counts: " + Results.get_pilot_lap_counts_str(self.results))
                if race_format.team_racing_mode == RacingMode.TEAM_ENABLED:
                    logger.debug("Team lap totals: " + Results.get_team_lap_totals_str(self.team_results))

            # if racer lap was deleted and result is winner un-declared
            if del_lap_flag and self.win_status != previous_win_status and \
                                self.win_status == WinStatus.NONE:
                self.win_status = WinStatus.NONE
                self.race_winner_name = ''
                self.race_winner_phonetic = ''
                self.race_winner_lap_id = 0
                self.race_winner_pilot_id = RHUtils.PILOT_ID_NONE
                self.status_message = ''
                logger.info("Race status msg:  <None>")
                return win_status_dict

            if win_status_dict['status'] == WinStatus.DECLARED:
                # announce winner
                status_msg_str = log_msg_str = phonetic_str = None
                win_data = win_status_dict['data']
                winner_flag = True
                if race_format.team_racing_mode == RacingMode.TEAM_ENABLED:
                    win_str = win_data.get('name', '')
                    team_win_str = self._racecontext.language.__('Team') + ' ' + win_str
                    self.race_winner_name = team_win_str
                    self.race_winner_phonetic = team_win_str
                    status_msg_str = self._racecontext.language.__('Winner is') + ' ' + team_win_str
                    log_msg_str = "Race status msg:  Winner is Team " + win_str
                    phonetic_str = status_msg_str

                elif race_format.team_racing_mode == RacingMode.COOP_ENABLED:
                    coop_leaderboard = self.team_results.get('by_race_time')
                    if type(coop_leaderboard) is list and len(coop_leaderboard) > 0:
                        coop_leaderboard = coop_leaderboard[0]
                    coop_time = coop_leaderboard.get('coop_total_time') if type(coop_leaderboard) is dict else None
                    if coop_time:
                        total_time_ms = coop_leaderboard.get('coop_total_time_raw', 0)
                        coop_time_secs = round(float(total_time_ms)/1000, 3)  # save time in seconds, rounded to nearest ms
                        phonetic_time = RHUtils.format_phonetic_time_to_str(total_time_ms, \
                                            self._racecontext.rhdata.get_option('timeFormatPhonetic'))
                        new_best_str = ""
                        diff_str = ""
                        phonetic_diff_str = ""
                        if self.unlimited_time:  # if first race to establish target time
                            log_msg_str = "Race status msg:  Race done, co-op time is " + coop_time
                            self.coop_best_time = coop_time_secs
                            winner_flag = False  # don't play winner tone when announcing
                        else:
                            self._racecontext.rhui.emit_race_stop()
                            time_format = self._racecontext.serverconfig.get_item('UI', 'timeFormat')
                            prev_coop_time_ms = int(self.coop_best_time*1000 + 0.5)
                            prev_coop_time_str = RHUtils.format_time_to_str(prev_coop_time_ms, time_format)
                            if coop_time_secs >= self.coop_best_time:  # co-op time was not better than target time
                                diff_ms = int(coop_time_secs*1000+0.5) - prev_coop_time_ms
                                diff_str = RHUtils.format_split_time_to_str(diff_ms, time_format)
                                log_msg_str = "Race status msg:  Race done, co-op time is " + coop_time + ", prev co-op time was " + \
                                              prev_coop_time_str + " (" + diff_str + " behind)"
                                diff_str += " " + self.__("behind") + ")"
                                phonetic_diff_str = " " + self.__("behind")
                                winner_flag = False  # don't play winner tone when announcing
                            else:  # new best co-op time established
                                diff_ms = prev_coop_time_ms - int(coop_time_secs*1000+0.5)
                                diff_str = RHUtils.format_split_time_to_str(diff_ms, time_format)
                                log_msg_str = "Race status msg:  Race done, new best co-op time is " + coop_time + ", prev co-op time was " + \
                                              prev_coop_time_str + " (" + diff_str + " ahead)"
                                new_best_str = self.__('success! New best') + ' '
                                diff_str += " " + self.__("ahead") + ")"
                                phonetic_diff_str = " " + self.__("ahead")
                                self.coop_best_time = coop_time_secs
                            diff_str = ", " + self.__("previous co-op time was ") + prev_coop_time_str + ", (" + diff_str
                            phonetic_diff_str = ", " + self.__("previous co-op time was ") + \
                                                RHUtils.format_phonetic_time_to_str(prev_coop_time_ms, \
                                                    self._racecontext.serverconfig.get_item('UI', 'timeFormatPhonetic')) + ", " + \
                                                RHUtils.format_phonetic_time_to_str(diff_ms, \
                                                    self._racecontext.serverconfig.get_item('UI', 'timeFormatPhonetic')) + \
                                                phonetic_diff_str
                        status_msg_str = self.__("Race done") + ", " + new_best_str + self.__("co-op time is") + \
                                         " " + coop_time + diff_str
                        phonetic_str = self.__("Race done") + ", " + new_best_str + self.__("co-op time is") + \
                                       " " + phonetic_time + phonetic_diff_str

                else:
                    win_str = win_data.get('callsign', '')
                    self.race_winner_name = win_str
                    self.race_winner_lap_id = win_data.get('laps', 0)
                    status_msg_str = self._racecontext.language.__('Winner is') + ' ' + win_str
                    log_msg_str = "Race status msg:  Winner is " + win_str
                    win_pilot_id = win_data.get('pilot_id')
                    if win_pilot_id:
                        self.race_winner_pilot_id = win_pilot_id
                        win_phon_name = self._racecontext.rhdata.get_pilot(win_pilot_id).phonetic
                    elif win_data['callsign']:
                        win_phon_name = win_data['callsign']
                    else:
                        win_phon_name = None
                    if (not win_phon_name) or len(win_phon_name) <= 0:  # if no phonetic then use callsign
                        win_phon_name = win_data.get('callsign', '')
                    self.race_winner_phonetic = win_phon_name
                    phonetic_str = self._racecontext.language.__('Winner is') + ' ' + win_phon_name

                # if racer lap was deleted then only output if win-status details changed
                if status_msg_str and ((not del_lap_flag) or self.win_status != previous_win_status or \
                                            status_msg_str != self.status_message):
                    self.status_message = status_msg_str
                    logger.info(log_msg_str)
                    self._racecontext.rhui.emit_phonetic_text(phonetic_str, 'race_winner', winner_flag)
                    self._racecontext.events.trigger(Evt.RACE_WIN, {
                        'win_status': win_status_dict,
                        'message': self.status_message,
                        'node_index': win_data.get('node', -1),
                        'color': self.seat_colors[win_data['node']] \
                                                if 'node' in win_data else None,
                        })

            elif win_status_dict['status'] == WinStatus.TIE:
                # announce tied
                if win_status_dict['status'] != previous_win_status:
                    self.status_message = self._racecontext.language.__('Race Tied')
                    logger.info("Race status msg:  Race Tied")
                    self._racecontext.rhui.emit_phonetic_text(self.status_message, 'race_winner')
            elif win_status_dict['status'] == WinStatus.OVERTIME:
                # announce overtime
                if win_status_dict['status'] != previous_win_status:
                    self.status_message = self._racecontext.language.__('Race Tied: Overtime')
                    logger.info("Race status msg:  Race Tied: Overtime")
                    self._racecontext.rhui.emit_phonetic_text(self.status_message, 'race_winner')

            if 'max_consideration' in win_status_dict:
                logger.info("Waiting {0}ms to declare winner.".format(win_status_dict['max_consideration']))
                gevent.sleep(win_status_dict['max_consideration'] / 1000)
                if 'start_token' in kwargs and self.start_token == kwargs['start_token']:
                    logger.info("Maximum win condition consideration time has expired.")
                    self.check_win_condition(forced=True)

            if 'emit_leaderboard_on_win' in kwargs:
                if self.win_status != WinStatus.NONE:
                    self._racecontext.rhui.emit_current_leaderboard()  # show current race status on leaderboard

        return win_status_dict


    def get_active_laps(self, late_lap_flag=False):
        # return active (non-deleted) laps objects
        filtered = {}
        if not late_lap_flag:
            for node_index in self.node_laps:
                filtered[node_index] = list(filter(lambda lap : lap.deleted == False, self.node_laps[node_index]))
        else:
            for node_index in self.node_laps:
                filtered[node_index] = list(filter(lambda lap : \
                                (lap.deleted == False or lap.late_lap), self.node_laps[node_index]))
        return filtered

    def any_laps_recorded(self):
        for node_index in range(self.num_nodes):
            if len(self.node_laps[node_index]) > 0:
                return True
        return False

    def build_laps_list(self):
        current_laps = []
        for node_idx in range(self.num_nodes):
            node_laps = []
            fastest_lap_time = float("inf")
            fastest_lap_index = None
            last_lap_id = -1
            for idx, lap in enumerate(self.node_laps[node_idx]):
                if (not lap.invalid) and \
                    ((not lap.deleted) or lap.late_lap):
                    if not lap.late_lap:
                        last_lap_id = lap_number = lap.lap_number
                        if self.format and self.format.start_behavior == StartBehavior.FIRST_LAP:
                            lap_number += 1
                        splits = self.get_splits(node_idx, last_lap_id)
                        if lap.lap_time > 0 and idx > 0 and lap.lap_time < fastest_lap_time:
                            fastest_lap_time = lap.lap_time
                            fastest_lap_index = idx
                    else:
                        lap_number = -1
                        last_lap_id += 1
                        splits = self.get_splits(node_idx, last_lap_id)

                    node_laps.append({
                        'lap_index': idx,
                        'lap_number': lap_number,
                        'lap_raw': lap.lap_time,
                        'lap_time': lap.lap_time_formatted,
                        'lap_time_stamp': lap.lap_time_stamp,
                        'splits': splits,
                        'late_lap': lap.late_lap
                    })

            pilot_data = None
            if node_idx in self.node_pilots:
                pilot = self._racecontext.rhdata.get_pilot(self.node_pilots[node_idx])
                if pilot:
                    pilot_data = {
                        'id': pilot.id,
                        'name': pilot.name,
                        'callsign': pilot.callsign
                    }

            current_laps.append({
                'laps': node_laps,
                'fastest_lap_index': fastest_lap_index,
                'pilot': pilot_data,
                'finished_flag': self.get_node_finished_flag(node_idx)
            })
        current_laps = {
            'node_index': current_laps
        }
        return current_laps

    def get_splits(self, node_idx, lap_id):
        splits = []
        if self._racecontext.cluster:
            for secondary_index in range(len(self._racecontext.cluster.secondaries)):
                if self._racecontext.cluster.isSplitSecondaryAvailable(secondary_index):
                    split = self._racecontext.rhdata.get_lapSplit_by_params(node_idx, lap_id, secondary_index)
                    if split:
                        split_payload = {
                            'split_id': secondary_index,
                            'split_raw': split.split_time,
                            'split_time': split.split_time_formatted,
                            'split_speed': '{0:.2f}'.format(split.split_speed) if split.split_speed is not None else None
                        }
                    else:
                        split_payload = {
                            'split_id': secondary_index,
                            'split_time': '-'
                        }
                    splits.append(split_payload)
        return splits

    def get_lap_results(self):
        if 'data_ver' in self.lap_cacheStatus and 'build_ver' in self.lap_cacheStatus:
            token = self.lap_cacheStatus['data_ver']
            if self.lap_cacheStatus['data_ver'] == self.lap_cacheStatus['build_ver']:
                # cache hit
                return self.lap_results
            # else: cache miss
        else:
            logger.error('Laps cache has invalid status')
            token = monotonic()
            self.clear_lap_results(token)

        # cache rebuild
        # logger.debug('Building current race results')
        build = self.build_laps_list()
        self.set_lap_results(token, build)
        return build

    def get_results(self):
        if 'data_ver' in self.cacheStatus and 'build_ver' in self.cacheStatus:
            token = self.cacheStatus['data_ver']
            if self.cacheStatus['data_ver'] == self.cacheStatus['build_ver']:
                # cache hit
                return self.results
            # else: cache miss
        else:
            logger.error('Race cache has invalid status')
            token = monotonic()
            self.clear_results(token)

        # cache rebuild
        # logger.debug('Building current race results')
        build = Results.calc_leaderboard(self._racecontext, current_race=self, current_profile=self.profile)
        self.set_results(token, build)
        return build

    def get_team_results(self):
        if 'data_ver' in self.team_cacheStatus and 'build_ver' in self.team_cacheStatus:
            token = self.team_cacheStatus['data_ver']
            if self.team_cacheStatus['data_ver'] == self.team_cacheStatus['build_ver']:
                # cache hit
                return self.team_results
            # else: cache miss
        else:
            logger.error('Race cache has invalid status')
            token = monotonic()
            self.clear_team_results(token)
        # cache rebuild
        logger.debug('Building current race results')
        build = Results.calc_team_leaderboard(self._racecontext)
        self.set_team_results(token, build)
        return build

    def get_coop_results(self):
        if 'data_ver' in self.team_cacheStatus and 'build_ver' in self.team_cacheStatus:
            token = self.team_cacheStatus['data_ver']
            if self.team_cacheStatus['data_ver'] == self.team_cacheStatus['build_ver']:
                # cache hit
                return self.team_results
            # else: cache miss
        else:
            logger.error('Race cache has invalid status')
            token = monotonic()
            self.clear_team_results(token)
        # cache rebuild
        logger.debug('Building current race results')
        build = Results.calc_coop_leaderboard(self._racecontext)
        self.set_coop_results(token, build)
        return build

    def set_lap_results(self, token, lap_results):
        lap_results = self._filters.run_filters(Flt.LAPS_SAVE, lap_results)
        if self.lap_cacheStatus['data_ver'] == token:
            self.lap_cacheStatus['build_ver'] = token
            self.lap_results = lap_results
        return True

    def set_results(self, token, results):
        results = self._filters.run_filters(Flt.RACE_RESULTS, results)
        if self.cacheStatus['data_ver'] == token:
            self.cacheStatus['build_ver'] = token
            self.results = results
        return True

    def set_team_results(self, token, results):
        results = self._filters.run_filters(Flt.RACE_TEAM_RESULTS, results)
        if self.team_cacheStatus['data_ver'] == token:
            self.team_cacheStatus['build_ver'] = token
            self.team_results = results
        return True

    def set_coop_results(self, token, results):
        results = self._filters.run_filters(Flt.RACE_COOP_RESULTS, results)
        if self.team_cacheStatus['data_ver'] == token:
            self.team_cacheStatus['build_ver'] = token
            self.team_results = results
        return True

    def clear_lap_results(self, token=None):
        if token is None:
            token = monotonic()

        self.lap_cacheStatus = {
            'data_ver': token,
            'build_ver': None
        }
        return True

    def clear_results(self, token=None):
        if token is None:
            token = monotonic()

        self.lap_cacheStatus = {
            'data_ver': token,
            'build_ver': None
        }
        self.cacheStatus = {
            'data_ver': token,
            'build_ver': None
        }
        self.team_cacheStatus = {
            'data_ver': token,
            'build_ver': None
        }
        return True

    def clear_team_results(self, token=None):
        if token is None:
            token = monotonic()

        self.team_cacheStatus = {
            'data_ver': token,
            'build_ver': None
        }
        return True

    @property
    def seat_colors(self):
        return self._seat_colors

    @seat_colors.setter
    def seat_colors(self, value):
        self._seat_colors = value

    def updateSeatColors(self, mode_override=False):
        if self.external_flag:
            return self.seat_colors

        colors = []
        if mode_override is not False:
            mode = mode_override
        else:
            mode = self._racecontext.serverconfig.get_item_int('LED', 'ledColorMode', 0)

        if self.current_heat == RHUtils.HEAT_ID_NONE:
            practice_flag = True
            if mode == 1:
                mode = 0
        else:
            practice_flag = False

        if mode == 0:
            seatColorOpt = self._racecontext.serverconfig.get_item('LED', 'seatColors')
            if seatColorOpt:
                seatColors = seatColorOpt
            else:
                seatColors = self._racecontext.serverstate.seat_color_defaults
        elif mode == 2:
            profile_freqs = json.loads(self.profile.frequencies)

        for node_index in range(self.num_nodes):
            color = '#ffffff'

            if not practice_flag and (not self.node_pilots or self.node_pilots[node_index] == RHUtils.PILOT_ID_NONE):
                color = '#222222'

            elif mode == 0: # by seat
                color = seatColors[node_index % len(seatColors)]

            elif mode == 1: # by pilot
                color = self._racecontext.rhdata.get_pilot(self.node_pilots[node_index]).color

            elif mode == 2: # by frequency, following https://betaflight.com/docs/development/LedStrip#vtx-frequency
                freq = profile_freqs["f"][node_index]

                if freq <= 5672:
                    color = '#ffffff' # White
                elif freq <= 5711:
                    color = '#ff0000' # Red
                elif freq <= 5750:
                    color = '#ff8000' # Orange
                elif freq <= 5789:
                    color = '#ffff00' # Yellow
                elif freq <= 5829:
                    color = '#00ff00' # Green
                elif freq <= 5867:
                    color = '#0000ff' # Blue
                elif freq <= 5906:
                    color = '#8000ff' # Dark Violet
                else:
                    color = '#ff0080' # Deep Pink

            colors.append(RHUtils.hexToColor(color))

        self._seat_colors = colors

    @property
    def profile(self):
        if self._profile is None:
            stored_profile = self._racecontext.rhdata.get_optionInt('currentProfile')
            self._profile = self._racecontext.rhdata.get_profile(stored_profile)
        return self._profile

    @profile.setter
    def profile(self, value):
        self._profile = value

    @property
    def format(self):
        if self._format is None:
            stored_format = self._racecontext.rhdata.get_optionInt('currentFormat')
            if stored_format:
                race_format = self._racecontext.rhdata.get_raceFormat(stored_format)
                if not race_format:
                    race_format = self._racecontext.rhdata.get_first_raceFormat()
                    self._racecontext.rhdata.set_option('currentFormat', race_format.id)
            else:
                race_format =self._racecontext.rhdata.get_first_raceFormat()

            # create a shared instance
            self._format = RHRaceFormat.copy(race_format)
            self._format.id = race_format.id  #pylint: disable=attribute-defined-outside-init
        return self._format

    def getDbRaceFormat(self):
        if self.format is None or RHRaceFormat.isDbBased(self.format):
            stored_format = self._racecontext.rhdata.get_optionInt('currentFormat')
            return self._racecontext.rhdata.get_raceFormat(stored_format)
        else:
            return None

    @format.setter
    def format(self, race_format):
        if self.race_status == RaceStatus.READY:
            if RHRaceFormat.isDbBased(race_format): # stored in DB, not internal race format
                if self._format and getattr(self._format, 'id', -1) != race_format.id:
                    self.prev_race_winner_name = ''  # if format changed then clear previous race winner
                    self.prev_race_winner_phonetic = ''
                    self.prev_race_winner_pilot_id = RHUtils.PILOT_ID_NONE
                self._racecontext.rhdata.set_option('currentFormat', race_format.id)
                # create a shared instance
                self._format = RHRaceFormat.copy(race_format)
                self._format.id = race_format.id  #pylint: disable=attribute-defined-outside-init
                self.clear_results() # refresh leaderboard
            else:
                self._format = race_format
        else:
            logger.info('Preventing race format change: Race status not READY')

    # For secondary/split timer, check that current heat has all needed node slots filled with pilots
    #  and create a new 'Secondary-Format Heat' and pilot entries if needed
    def check_create_sec_format_heat(self):
        try:
            use_current_heat_flag = False
            # check if current heat can be used
            if self.current_heat != RHUtils.HEAT_ID_NONE:
                heat_obj = self._racecontext.rhdata.get_heat(self.current_heat)
                if heat_obj and self._racecontext.rhdata.check_all_heat_nodes_filled(heat_obj.id):
                    use_current_heat_flag = True
                    logger.debug('Using current heat for secondary format: Heat {}'.format(heat_obj.id))
            if not use_current_heat_flag:
                # check if any of the existing heats can be used
                heats = self._racecontext.rhdata.get_heats()
                for heat_obj in heats:
                    if self._racecontext.rhdata.check_all_heat_nodes_filled(heat_obj.id):
                        logger.info('Setting current heat for secondary format to Heat {}'.format(heat_obj.id))
                        self.set_heat(heat_obj.id)
                        use_current_heat_flag = True
                        break
                if not use_current_heat_flag:
                    # create new heat to use
                    heat_pilots = {}
                    # check if existing pilot entries have the default names and use them if no; else create new ones
                    for node_obj in self._racecontext.interface.nodes:
                        callsign = self._racecontext.language.__('~Callsign %d') % (node_obj.index + 1)
                        pilot_obj = self._racecontext.rhdata.get_pilot_for_callsign(callsign)
                        if pilot_obj is None:
                            pilot_name = self._racecontext.language.__('~Pilot %d Name') % (node_obj.index + 1)
                            pilot_obj = self._racecontext.rhdata.add_pilot({'callsign': callsign, 'name': pilot_name})
                            logger.info('Created new pilot entry for secondary format: id={}, callsign: {}'.\
                                        format(pilot_obj.id, pilot_obj.callsign))
                        else:
                            logger.info('Reusing pilot entry for secondary format: id={}, callsign: {}'.\
                                        format(pilot_obj.id, pilot_obj.callsign))
                        heat_pilots[node_obj.index] = pilot_obj.id
                    heat_obj = self._racecontext.rhdata.add_heat(init={'name': 'Secondary-Format Heat'},
                                                           initPilots=heat_pilots)
                    logger.info('Creating and using new heat for secondary format: Heat {}'.format(heat_obj.id))
                    self.set_heat(heat_obj.id)
        except:
            logger.exception("Error checking/creating heat for secondary format")

    def set_heat(self, new_heat_id, silent=False, force=False, mute_event=False): #set_current_heat_data
        new_heat_id = self._filters.run_filters(Flt.RACE_SET_HEAT, new_heat_id)

        logger.info('Setting current heat to Heat {0}'.format(new_heat_id))

        if force:
            self.finalize_heat_set(new_heat_id, mute_event=mute_event)

        heat = self._racecontext.rhdata.get_heat(new_heat_id)
        if heat and not heat.active:
            self.finalize_heat_set(RHUtils.HEAT_ID_NONE, mute_event=mute_event)

        result = self._racecontext.heatautomator.calc_heat(new_heat_id, silent)

        if result == 'safe':
            self.finalize_heat_set(new_heat_id, mute_event=mute_event)
        elif result == 'no-heat':
            self.finalize_heat_set(RHUtils.HEAT_ID_NONE, mute_event=mute_event)

        # keep time fields in the current race in sync with the current race format
        self.set_race_format_time_fields(self.format, heat)

    def finalize_heat_set(self, new_heat_id, mute_event=False): #finalize_current_heat_set
        if self.race_status == RaceStatus.READY:

            if new_heat_id == RHUtils.HEAT_ID_NONE:
                self.node_pilots = {}
                self.node_teams = {}
                if self.current_heat != new_heat_id:
                    logger.info("Switching to practice mode; races will not be saved until a heat is selected")
                    self.current_heat = new_heat_id
                else:
                    logger.debug("Running in practice mode; races will not be saved until a heat is selected")
                self._racecontext.rhdata.set_option('currentHeat', self.current_heat)

            else:
                self.current_heat = new_heat_id
                self._racecontext.rhdata.set_option('currentHeat', self.current_heat)
                self.node_pilots = {}
                self.node_teams = {}
                for idx in range(self.num_nodes):
                    self.node_pilots[idx] = RHUtils.PILOT_ID_NONE
                    self.node_teams[idx] = None

                for heatNode in self._racecontext.rhdata.get_heatNodes_by_heat(new_heat_id):
                    if heatNode.node_index is not None:
                        self.node_pilots[heatNode.node_index] = heatNode.pilot_id

                        if heatNode.pilot_id is not RHUtils.PILOT_ID_NONE:
                            self.node_teams[heatNode.node_index] = self._racecontext.rhdata.get_pilot(heatNode.pilot_id).team
                        else:
                            self.node_teams[heatNode.node_index] = None

                heat_data = self._racecontext.rhdata.get_heat(new_heat_id)

                if heat_data.class_id != RHUtils.CLASS_ID_NONE:
                    class_format_id = self._racecontext.rhdata.get_raceClass(heat_data.class_id).format_id
                    if class_format_id != RHUtils.FORMAT_ID_NONE:
                        self.format = self._racecontext.rhdata.get_raceFormat(class_format_id)
                        self._racecontext.rhui.emit_current_laps()
                        logger.info("Forcing race format from class setting: '{0}' ({1})".format(self.format.name, self.format.id))

                adaptive = bool(self._racecontext.serverconfig.get_item_int('TIMING', 'calibrationMode'))
                if adaptive:
                    self._racecontext.calibration.auto_calibrate()

            self.updateSeatColors()

            if not mute_event:
                self._racecontext.events.trigger(Evt.HEAT_SET, {
                    'heat_id': new_heat_id,
                    })

            self.clear_results() # refresh leaderboard

            self._racecontext.rhui.emit_current_heat() # Race page, to update heat selection button
            self._racecontext.rhui.emit_current_leaderboard() # Race page, to update callsigns in leaderboard
            self._racecontext.rhui.emit_current_laps()  # make sure Current-race page shows correct number of node slots
            self._racecontext.rhui.emit_race_status()
        else:
            logger.debug('Prevented heat change for active race')


class RHRaceFormat():
    def __init__(self, name, unlimited_time, race_time_sec, lap_grace_sec, staging_fixed_tones, start_delay_min_ms, start_delay_max_ms, staging_delay_tones, number_laps_win, win_condition, team_racing_mode, start_behavior, points_method):
        self.name = name
        self.unlimited_time = unlimited_time
        self.race_time_sec = race_time_sec
        self.lap_grace_sec = lap_grace_sec
        self.staging_fixed_tones = staging_fixed_tones
        self.start_delay_min_ms = start_delay_min_ms
        self.start_delay_max_ms = start_delay_max_ms
        self.staging_delay_tones = staging_delay_tones
        self.number_laps_win = number_laps_win
        self.win_condition = win_condition
        self.team_racing_mode = team_racing_mode
        self.start_behavior = start_behavior
        self.points_method = points_method

    @classmethod
    def copy(cls, race_format):
        return RHRaceFormat(name=race_format.name,
                            unlimited_time=race_format.unlimited_time,
                            race_time_sec=race_format.race_time_sec,
                            lap_grace_sec=race_format.lap_grace_sec,
                            staging_fixed_tones=race_format.staging_fixed_tones,
                            start_delay_min_ms=race_format.start_delay_min_ms,
                            start_delay_max_ms=race_format.start_delay_max_ms,
                            staging_delay_tones=race_format.staging_delay_tones,
                            number_laps_win=race_format.number_laps_win,
                            win_condition=race_format.win_condition,
                            team_racing_mode=race_format.team_racing_mode,
                            start_behavior=race_format.start_behavior,
                            points_method=race_format.points_method)

    @classmethod
    def isDbBased(cls, race_format):
        return hasattr(race_format, 'id')

class StagingTones():
    TONES_NONE = 0
    TONES_ONE = 1
    TONES_ALL = 2
    # TONES_3_2_1 = 3

class StartBehavior():
    HOLESHOT = 0
    FIRST_LAP = 1
    STAGGERED = 2

class WinCondition():
    NONE = 0
    MOST_PROGRESS = 1 # most laps in fastest time
    FIRST_TO_LAP_X = 2
    FASTEST_LAP = 3
    FASTEST_CONSECUTIVE = 4
    MOST_LAPS = 5 # lap count only
    MOST_LAPS_OVERTIME = 6 # lap count only, laps and time after T=0

class RacingMode():
    INDIVIDUAL = 0
    TEAM_ENABLED = 1
    COOP_ENABLED = 2

class WinStatus():
    NONE = 0
    TIE = 1
    PENDING_CROSSING = 2
    DECLARED = 3
    OVERTIME = 4

class RaceStatus():
    READY = 0
    STAGING = 3
    RACING = 1
    DONE = 2

