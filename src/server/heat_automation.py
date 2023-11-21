'''Seeding and frequency automation for heats'''

import logging
import random
import json
import RHUtils
from Database import ProgramMethod, HeatStatus
from flask import request

logger = logging.getLogger(__name__)

class HeatAutomator:
    def __init__(self, racecontext):
        self._racecontext = racecontext

    def calc_heat(self, heat_id, silent=False):
        heat = self._racecontext.rhdata.get_heat(heat_id)

        if (heat):
            calc_result = self.calc_heat_pilots(heat)

            if calc_result['calc_success'] is False:
                logger.warning('{} plan cannot be fulfilled.'.format(heat.display_name))

            if calc_result['calc_success'] is None:
                # Heat is confirmed or has saved races
                return 'safe'

            if calc_result['calc_success'] is True and calc_result['has_calc_pilots'] is False and not heat.auto_frequency:
                # Heat has no calc issues, no dynamic slots, and auto-frequnecy is off
                return 'safe'

            adaptive = bool(self._racecontext.rhdata.get_optionInt('calibrationMode'))

            if adaptive:
                calc_fn = self.find_best_slot_node_adaptive
            else:
                calc_fn = self.find_best_slot_node_basic

            self.run_auto_frequency(heat, self._racecontext.race.profile.frequencies, self._racecontext.race.num_nodes, calc_fn)

            if request and not silent:
                self._racecontext.rhui.emit_heat_plan_result(heat_id, calc_result)

            return 'unsafe'

        else:
            return 'no-heat'

    def calc_heat_pilots(self, heat_or_id):
        heat = self._racecontext.RHData.resolve_heat_from_heat_or_id(heat_or_id)

        result = {
             'calc_success': True,
             'has_calc_pilots': False,
             'unassigned_slots': 0
             }

        if not heat:
            logger.error('Requested invalid heat {}'.format(heat.id))
            result['calc_success'] = False
            return result

        # skip if heat status confirmed
        if (heat.status == HeatStatus.CONFIRMED):
            result['calc_success'] = None
            logger.debug("Skipping pilot recalculation: Heat confirmed (heat {})".format(heat.id))
            return result

        # don't alter if saved races exist
        race_list = self._racecontext.RHData.get_savedRaceMetas_by_heat(heat.id) 

        if (race_list):
            result['calc_success'] = None
            logger.debug("Skipping pilot recalculation: Races exist (heat {})".format(heat.id))
            return result

        slots = self._racecontext.RHData.get_heatNodes_by_heat(heat.id)
        for slot in slots:
            if slot.method == ProgramMethod.NONE:
                slot.pilot_id = RHUtils.PILOT_ID_NONE

            elif slot.method == ProgramMethod.HEAT_RESULT:
                if slot.seed_id:
                    if slot.seed_rank:
                        result['has_calc_pilots'] = True
                        logger.debug('Seeding Slot {} from Heat {}'.format(slot.id, slot.seed_id))
                        seed_heat = self._racecontext.RHData.get_heat(slot.seed_id)

                        if seed_heat:
                            output = self._racecontext.RHData.get_results_heat(seed_heat)
                            if output:
                                results = output[output['meta']['primary_leaderboard']]
                                if slot.seed_rank - 1 < len(results):
                                    slot.pilot_id = results[slot.seed_rank - 1]['pilot_id']
                                else:
                                    slot.pilot_id = RHUtils.PILOT_ID_NONE
                                    result['unassigned_slots'] += 1
                            else:
                                logger.debug("Can't assign pilot from heat {}: Results not available".format(slot.seed_id))
                                slot.pilot_id = RHUtils.PILOT_ID_NONE
                                result['unassigned_slots'] += 1
                        else:
                            result['calc_success'] = False
                            logger.info("Can't seed from heat {}: does not exist".format(slot.seed_id))
                    else:
                        result['calc_success'] = False
                        logger.info("Can't seed from heat {}: rank is null".format(slot.seed_id))
                else:
                    slot.pilot_id = RHUtils.PILOT_ID_NONE
                    logger.debug("Ignoring null heat as seed source")

            elif slot.method == ProgramMethod.CLASS_RESULT:
                if slot.seed_id:
                    if slot.seed_rank:
                        result['has_calc_pilots'] = True
                        logger.debug('Seeding Slot {} from Class {}'.format(slot.id, slot.seed_id))
                        seed_class = self._racecontext.RHData.get_raceClass(slot.seed_id)

                        if seed_class:
                            positions = None

                            ranking = self._racecontext.RHData.get_ranking_raceClass(seed_class)
                            if ranking: # manual ranking
                                positions = ranking['ranking']
                            else: # auto ranking
                                results = self._racecontext.RHData.get_results_raceClass(seed_class)
                                if results:
                                    positions = results[results['meta']['primary_leaderboard']]

                            if positions:
                                if slot.seed_rank - 1 < len(positions):
                                    slot.pilot_id = positions[slot.seed_rank - 1]['pilot_id']
                                else:
                                    slot.pilot_id = RHUtils.PILOT_ID_NONE
                                    result['unassigned_slots'] += 1
                            else:
                                logger.debug("Can't assign pilot from class {}: Results not available".format(slot.seed_id))
                                slot.pilot_id = RHUtils.PILOT_ID_NONE
                                result['unassigned_slots'] += 1
                        else:
                            result['calc_success'] = False
                            logger.info("Can't seed from class {}: does not exist".format(slot.seed_id))
                    else:
                        result['calc_success'] = False
                        logger.info("Can't seed from class {}: rank is null".format(slot.seed_id))
                else:
                    slot.pilot_id = RHUtils.PILOT_ID_NONE
                    logger.debug("Ignoring null class as seed source")

            logger.debug('Slot {} Pilot is {}'.format(slot.id, slot.pilot_id if slot.pilot_id else None))

        self._racecontext.RHData.commit()
        return result

    def run_auto_frequency(self, heat_or_id, current_frequencies, num_nodes, calc_fn):
        logger.debug('running auto-frequency with {}'.format(calc_fn))
        heat = self._racecontext.RHData.resolve_heat_from_heat_or_id(heat_or_id)
        slots = self._racecontext.RHData.get_heatNodes_by_heat(heat.id)

        if heat.auto_frequency:
            # clear all node assignments
            for slot in slots:
                slot.node_index = None

            # collect node data
            available_seats = []
            profile_freqs = json.loads(current_frequencies)
            for node_index in range(num_nodes):
                if profile_freqs["f"][node_index] != RHUtils.FREQUENCY_ID_NONE:
                    available_seats.append({
                        'idx': node_index,
                        'frq': {
                            'f': profile_freqs["f"][node_index],
                            'b': profile_freqs["b"][node_index],
                            'c': profile_freqs["c"][node_index]
                            },
                        'matches': []
                        })

            # get frequency matches from pilots
            for slot in slots:
                if slot.pilot_id:
                    used_frequencies_json = self._racecontext.RHData.get_pilot(slot.pilot_id).used_frequencies
                    if used_frequencies_json:
                        used_frequencies = json.loads(used_frequencies_json)
                        for node in available_seats:
                            end_idx = len(used_frequencies) - 1
                            for f_idx, pilot_freq in enumerate(used_frequencies):
                                if node['frq']['f'] == pilot_freq['f']:
                                    node['matches'].append({
                                            'slot': slot,
                                            'band': pilot_freq['b'],
                                            'priority': True if f_idx == end_idx else False
                                         })

            eliminated_matches = []
            if callable(calc_fn):
                while len(available_seats):
                    # request assignment from calc function
                    m_node, m_slot, an_idx = calc_fn(available_seats)
                    if m_node and m_slot:
                        # calc function returned assignment
                        m_slot.node_index = m_node['idx']
                        for slot_idx, slot_match in enumerate(m_node['matches']):
                            if slot_match['slot'] != m_slot:
                                eliminated_matches.append(slot_match)
                        del available_seats[an_idx]
                        for available_node in available_seats:
                            for slot_idx, slot_match in enumerate(available_node['matches']):
                                if slot_match['slot'] == m_slot:
                                    available_node['matches'][slot_idx] = None
                                available_node['matches'] = [x for x in available_node['matches'] if x is not None]
                    else:
                        # calc function didn't make an assignment
                        random.shuffle(available_seats)
                        if len(eliminated_matches):

                            for slot_idx, slot_match in enumerate(eliminated_matches):
                                if eliminated_matches[slot_idx]['slot'].node_index is None:
                                    # Stay on D-band if needed
                                    if eliminated_matches[slot_idx] \
                                    and eliminated_matches[slot_idx]['band'] == 'D' \
                                    and eliminated_matches[slot_idx]['priority'] == True:
                                        for n_idx, node in enumerate(available_seats):
                                            if node['frq']['b'] == 'D':
                                                eliminated_matches[slot_idx]['slot'].node_index = available_seats[n_idx]['idx']
                                                available_seats[n_idx] = None
                                                break
                                    else:
                                        # else explicity avoid D-band
                                        for n_idx, node in enumerate(available_seats):
                                            if node['frq']['b'] != 'D':
                                                eliminated_matches[slot_idx]['slot'].node_index = available_seats[n_idx]['idx']
                                                available_seats[n_idx] = None
                                                break

                                    available_seats = [x for x in available_seats if x is not None]
                                eliminated_matches[slot_idx] = None

                            if len(available_seats):
                                # can't keep D/non-D but nodes not full
                                for slot_idx, slot_match in enumerate(eliminated_matches):
                                    if eliminated_matches[slot_idx] and eliminated_matches[slot_idx]['slot'].node_index is None:
                                        eliminated_matches[slot_idx]['slot'].node_index = available_seats[0]['idx']
                                        del(available_seats[0])
                                    eliminated_matches[slot_idx] = None
                                
                            eliminated_matches = [x for x in eliminated_matches if x is not None]
                        else:
                            # place pilots with no history into first available slots
                            for slot in slots:
                                if slot.node_index is None and slot.pilot_id:
                                    if len(available_seats):
                                        slot.node_index = available_seats[0]['idx']
                                        del(available_seats[0])
                                    else:
                                        logger.warning("Dropping pilot {}; No remaining available nodes for slot {}".format(slot.pilot_id, slot))
                            break
            else:
                logger.error('calc_fn is not a valid auto-frequency algortihm')
                return False

            self._racecontext.RHData.commit()
        else:
            logger.debug('requested auto-frequency when disabled')

        return True

    # Auto-frequency algorithm prioritizing minimum channel changes
    def find_best_slot_node_basic(self, available_seats):
        # if only one match has priority
        for an_idx, node in enumerate(available_seats):
            num_priority = 0
            best_match = 0
            for idx, option in enumerate(node['matches']):
                if option['priority']:
                    num_priority += 1
                    best_match = idx

            if num_priority == 1:
                return node, node['matches'][best_match]['slot'], an_idx

        # if any match has priority
        for an_idx, node in enumerate(available_seats):
            order = list(range(len(node['matches'])))
            random.shuffle(order)
            for idx in order:
                if node['matches'][idx]['priority']:
                    return node, node['matches'][idx]['slot'], an_idx

        # if only match
        for an_idx, node in enumerate(available_seats):
            if len(node['matches']) == 1:
                return node, node['matches'][0]['slot'], an_idx

        # if any match
        for an_idx, node in enumerate(available_seats):
            if len(node['matches']):
                idx = random.randint(0, len(node['matches']) - 1)
                return node, node['matches'][idx]['slot'], an_idx

        return None, None, None

    # Auto-frequency algorithm suitable for Adaptive Calibration
    def find_best_slot_node_adaptive(self, available_seats):
        # if only match has priority
        for an_idx, node in enumerate(available_seats):
            if len(node['matches']) == 1:
                if node['matches'][0]['priority']:
                    return node, node['matches'][0]['slot'], an_idx

        # if only match
        for an_idx, node in enumerate(available_seats):
            if len(node['matches']) == 1:
                return node, node['matches'][0]['slot'], an_idx

        # if one match has priority
        for an_idx, node in enumerate(available_seats):
            num_priority = 0
            best_match = 0
            for idx, option in enumerate(node['matches']):
                if option['priority']:
                    num_priority += 1
                    best_match = idx

            if num_priority == 1:
                return node, node['matches'][best_match]['slot'], an_idx

        # if any match has priority
        for an_idx, node in enumerate(available_seats):
            order = list(range(len(node['matches'])))
            random.shuffle(order)
            for idx in order:
                if node['matches'][idx]['priority']:
                    return node, node['matches'][idx]['slot'], an_idx

        # if any match
        for an_idx, node in enumerate(available_seats):
            if len(node['matches']):
                idx = random.randint(0, len(node['matches']) - 1)
                return node, node['matches'][idx]['slot'], an_idx

        return None, None, None

