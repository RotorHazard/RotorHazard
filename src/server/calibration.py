'''Seat calibration adjustment'''

import logging
import json
import RHUtils
from eventmanager import Evt
from RHUtils import catchLogExceptionsWrapper

FALLBACK_CALIBRATION_METHOD_ID = 0 # Manual

logger = logging.getLogger(__name__)


class CalibrationMethod:
    def __init__(self, name):
        self.name = name

    def calibrate(self, rhapi, node, seat_index):
        """ Calibration method suggests CalibrationResult to use """
        pass

class AdaptiveCalibrationMethod(CalibrationMethod):
    def __init__(self):
        super().__init__("Adaptive")

    def calibrate(self, rhapi, node, seat_index):
        ''' Search race history for best tuning values '''
        if rhapi.race.current_heat == RHUtils.HEAT_ID_NONE:
            logger.debug('Skipping auto calibration; server in practice mode')
            return None

        # get commonly used values
        heat = rhapi.rhdata.get_heat(rhapi.race.current_heat)
        pilot = rhapi.rhdata.get_pilot_from_heatNode(rhapi.race.current_heat, seat_index)
        current_class = heat.class_id
        races = rhapi.rhdata.get_savedRaceMetas()
        races.sort(key=lambda x: x.id, reverse=True)
        pilotRaces = rhapi.rhdata.get_savedPilotRaces()
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

        return None

class ManualCalibrationMethod(CalibrationMethod):
    def __init__(self):
        super().__init__("Manual")

    def calibrate(self, _rhapi, node, _seat_index):
        return {
            'enter_at_level': node.enter_at_level,
            'exit_at_level': node.exit_at_level
        }

class CalibrationMethodsManager:
    def __init__(self, Events):
        self._methods = []

        # preregister adaptive calibration method
        self.registerMethod(ManualCalibrationMethod())
        self.registerMethod(AdaptiveCalibrationMethod())

        Events.trigger(Evt.CALIBRATION_INITIALIZE, {
            'register_fn': self.registerMethod
        })


    def registerMethod(self, method):
        if isinstance(method, CalibrationMethod):
            self._methods.append(method)
            logger.info(f"Registered {method.name} calibration method")
        else:
            logger.warning('Invalid method')

    def get_registered_methods(self):
        registered_methods = map(lambda m: m.name, self._methods)
        return registered_methods

class Calibration:
    def __init__(self, racecontext):
        self._racecontext = racecontext

    @catchLogExceptionsWrapper
    def set_enter_at_level(self, seat_index, enter_at_level):
        '''Set node enter-at level.'''

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

    @catchLogExceptionsWrapper
    def set_exit_at_level(self, seat_index, exit_at_level):
        '''Set node exit-at level.'''

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

    def calibrate_nodes(self):
        ''' Apply best tuning values to nodes '''
        for seat_index, node in enumerate(self._racecontext.interface.nodes):
            calibration = self.find_best_calibration_values(node, seat_index)

            if node.enter_at_level is not calibration['enter_at_level']:
                self.set_enter_at_level(seat_index, calibration['enter_at_level'])

            if node.exit_at_level is not calibration['exit_at_level']:
                self.set_exit_at_level(seat_index, calibration['exit_at_level'])

        logger.info('Updated calibration with best discovered values')
        self._racecontext.rhui.emit_enter_and_exit_at_levels()

    def find_best_calibration_values(self, node, seat_index):
        calibration_methods = self._racecontext.calibration_method_manager._methods
        fallback_calibration_method = calibration_methods[FALLBACK_CALIBRATION_METHOD_ID]
        calibration_method_id = self._racecontext.serverconfig.get_item_int('TIMING', 'calibrationMode')

        # Verify configuration values
        if calibration_method_id < 0 or calibration_method_id >= len(calibration_methods):
            logger.warning(f"Unexpected calibration method selected: {calibration_method_id}. Falling back to manual control")
            return fallback_calibration_method.calibrate(self._racecontext, node, seat_index)

        # Attempt to derive calibration values via selected calibration method
        calibration_method = calibration_methods[calibration_method_id];
        logger.debug(f"Attempting to use {calibration_method.name} calibration method for deriving calibration values")
        calib = calibration_method.calibrate(self._racecontext, node, seat_index)
        if calib is None:
            logger.debug('Node {0} calibration: no calibration hints found, no change'.format(node.index+1))
            return fallback_calibration_method.calibrate(self._racecontext, node, seat_index)

        return calib
