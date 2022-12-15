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

def ladder(_RHData, _Results, _PageCache, generate_args=None):
    qualifiers_per_heat = generate_args['qualifiers_per_heat'] if 'qualifiers_per_heat' in generate_args else 3
    advances_per_heat = generate_args['advances_per_heat'] if 'advances_per_heat' in generate_args else 2
    total_pilots = generate_args['total_pilots'] if 'total_pilots' in generate_args else 8

    letters = __('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    heats = []

    unseeded_pilots = list(range(total_pilots))
    heat_pilots = 0

    while len(unseeded_pilots):
        if heat_pilots == 0:
            heat = {
                'name': letters[len(heats)] + ' Main',
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

    return heats

def discover(*args, **kwargs):
    # returns array of exporters with default arguments
    return [
        HeatGenerator(
            'ladder',
            'Ladder',
            ladder,
        ),
    ]
