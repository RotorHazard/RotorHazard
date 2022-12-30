'''Standardized heat structures'''
# FAI: https://www.fai.org/sites/default/files/ciam/wcup_drones/sc4_vol_f9_dronesport_22_2022-03-01_0.pdf
# MultiGP: https://docs.google.com/document/d/1jWVjCnoIGdW1j_bklrbg-0D24c3x6YG5m_vmF7faG-U/edit#heading=h.hoxlrr3v86bb

import logging
logger = logging.getLogger(__name__)
import RHUtils
import random
from HeatGenerator import HeatGenerator
from Database import ProgramMethod

def registerHandlers(args):
    if 'registerFn' in args:
        for generator in discover():
            args['registerFn'](generator)

def __(arg): # Replaced with language from initialize()
    return arg

def initialize(**kwargs):
    if 'Events' in kwargs:
        kwargs['Events'].on('HeatGenerator_Initialize', 'HeatGenerator_register_ladder', registerHandlers, {}, 75, True)
    if '__' in kwargs:
        __ = kwargs['__']

def getTotalPilots(RHData, Results, generate_args):
    input_class_id = generate_args['input_class'] if 'input_class' in generate_args else None

    if input_class_id:
        race_class = RHData.get_raceClass(input_class_id)
        class_results = Results.get_results_race_class(RHData, race_class)
        if class_results['result']: 
            # fill from available results
            # TODO: Check class finalized status
            total_pilots = len(class_results['result']['by_race_time'])
        else:
            if 'total_pilots' in generate_args:
                total_pilots = generate_args['total_pilots']
            else:
                # fall back to number of pilots
                pilots = RHData.get_pilots()
                total_pilots = len(pilots)
    else:
        # use total number of pilots
        pilots = RHData.get_pilots()
        total_pilots = len(pilots)

    return total_pilots

def generateLadder(RHData, Results, _PageCache, generate_args=None):
    available_nodes = generate_args['available_nodes'] if 'available_nodes' in generate_args else None
    suffix = generate_args['suffix'] if 'suffix' in generate_args else __('Main')

    if 'qualifiers_per_heat' in generate_args and 'advances_per_heat' in generate_args:
        qualifiers_per_heat = generate_args['qualifiers_per_heat']
        advances_per_heat = generate_args['advances_per_heat']
    elif 'advances_per_heat' in generate_args:
        advances_per_heat = generate_args['advances_per_heat']
        qualifiers_per_heat = available_nodes - advances_per_heat
    elif 'qualifiers_per_heat' in generate_args:
        qualifiers_per_heat = generate_args['qualifiers_per_heat']
        advances_per_heat = available_nodes - qualifiers_per_heat
    else:
        qualifiers_per_heat = available_nodes - 1
        advances_per_heat = 1

    if qualifiers_per_heat < 1 or advances_per_heat < 1:
        if not ('advances_per_heat' in generate_args and generate_args['advances_per_heat'] == 0):
            logger.warning('Unable to seed ladder: provided qualifiers and advances must be > 0')
            return False

    total_pilots = getTotalPilots(RHData, Results, generate_args)

    if total_pilots == 0:
        logger.warning('Unable to seed ladder: no pilots available')
        return False

    letters = __('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    heats = []

    unseeded_pilots = list(range(total_pilots))
    heat_pilots = 0

    while len(unseeded_pilots):
        if heat_pilots == 0:
            heat = {
                'name': letters[len(heats)] + ' ' + suffix,
                'slots': []
                }

        if heat_pilots < qualifiers_per_heat:
            # slot qualifiers
            heat['slots'].append({
                    'method': 'input',
                    'seed_rank': unseeded_pilots.pop(0) + 1
                })

            heat_pilots += 1
        else:
            if len(unseeded_pilots) <= advances_per_heat:
                # slot remainder as qualifiers
                for seed in unseeded_pilots:
                    heat['slots'].append({
                            'method': 'input',
                            'seed_rank': seed + 1
                        })

                unseeded_pilots = [] # empty after using

            else:
                # slot advances
                for adv_idx in range(advances_per_heat):
                    heat['slots'].append({
                            'method': ProgramMethod.HEAT_RESULT,
                            'seed_heat_id': -len(heats) - 2,
                            'seed_rank': adv_idx + 1,
                        })

            heats = [heat, *heats] # insert at front
            heat_pilots = 0

    if heat_pilots: # insert final heat
        heats = [heat, *heats]

    return heats

def generateBalancedHeats(RHData, Results, _PageCache, generate_args=None):
    available_nodes = generate_args['available_nodes'] if 'available_nodes' in generate_args else None
    suffix = generate_args['suffix'] if 'suffix' in generate_args else __('Qualifier')

    if 'qualifiers_per_heat' in generate_args:
        qualifiers_per_heat = generate_args['qualifiers_per_heat']
    else:
        qualifiers_per_heat = available_nodes

    if qualifiers_per_heat < 1:
        logger.warning('Unable to seed ladder: provided qualifiers must be > 1')
        return False

    total_pilots = getTotalPilots(RHData, Results, generate_args)

    if total_pilots == 0:
        logger.warning('Unable to seed heats: no pilots available')
        return False

    total_heats = (total_pilots // qualifiers_per_heat)
    if total_pilots % qualifiers_per_heat:
        total_heats += 1

    letters = __('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    heats = []

    for idx in range(total_heats):
        heats.append({
            'name': letters[idx] + ' ' + suffix,
            'slots': []
            })

    unseeded_pilots = list(range(total_pilots))
    random.shuffle(unseeded_pilots)

    heatNum = 0
    while len(unseeded_pilots):
        if heatNum >= len(heats):
            heatNum = 0

        heats[heatNum]['slots'].append({
                'method': 'input',
                'seed_rank': unseeded_pilots.pop(0) + 1
                })
        heatNum += 1

    return heats

def discover(*args, **kwargs):
    # returns array of exporters with default arguments
    return [
        HeatGenerator(
            'ladder_1a',
            'Ladder, single advance',
            generateLadder,
        ),
        HeatGenerator(
            'ladder_2a',
            'Ladder, double advance',
            generateLadder,
            {
                'advances_per_heat': 2,
            }
        ),
        HeatGenerator(
            'ladder_0a',
            'Ranked fill',
            generateLadder,
            {
                'advances_per_heat': 0,
            }
        ),
        HeatGenerator(
            'balanced_fill',
            'Balanced random fill',
            generateBalancedHeats
        ),

    ]
