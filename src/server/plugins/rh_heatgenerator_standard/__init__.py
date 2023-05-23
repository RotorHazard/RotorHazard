'''Standardized heat structures'''
# FAI: https://www.fai.org/sites/default/files/ciam/wcup_drones/sc4_vol_f9_dronesport_22_2022-03-01_0.pdf
# MultiGP: https://docs.google.com/document/d/1jWVjCnoIGdW1j_bklrbg-0D24c3x6YG5m_vmF7faG-U/edit#heading=h.hoxlrr3v86bb

import logging
from HeatGenerator import HeatGenerator
from Database import ProgramMethod

logger = logging.getLogger(__name__)

def registerHandlers(args):
    if 'registerFn' in args:
        for generator in discover():
            args['registerFn'](generator)

def __(arg): # Replaced with outer language.__ during initialize()
    return arg

def initialize(**kwargs):
    if 'Events' in kwargs:
        kwargs['Events'].on('HeatGenerator_Initialize', 'HeatGenerator_register_standards', registerHandlers, {}, 75)
    if '__' in kwargs:
        __ = kwargs['__']

def bracket_1e_16_fai():
    return [
        {
            'name': __('Race') + ' 1',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 1
                },
                {
                    'method': 'input',
                    'seed_rank': 8
                },
                {
                    'method': 'input',
                    'seed_rank': 9
                },
                {
                    'method': 'input',
                    'seed_rank': 16
                }
            ]
        },
        {
            'name': __('Race') + ' 2',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 4
                },
                {
                    'method': 'input',
                    'seed_rank': 5
                },
                {
                    'method': 'input',
                    'seed_rank': 12
                },
                {
                    'method': 'input',
                    'seed_rank': 13
                }
            ]
        },
        {
            'name': __('Race') + ' 3',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 3
                },
                {
                    'method': 'input',
                    'seed_rank': 6
                },
                {
                    'method': 'input',
                    'seed_rank': 10
                },
                {
                    'method': 'input',
                    'seed_rank': 14
                }
            ]
        },
        {
            'name': __('Race') + ' 4',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 2
                },
                {
                    'method': 'input',
                    'seed_rank': 7
                },
                {
                    'method': 'input',
                    'seed_rank': 11
                },
                {
                    'method': 'input',
                    'seed_rank': 15
                }
            ]
        },
        {
            'name': __('Semifinal') + ' 1',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Semifinal') + ' 2',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Small Final'),
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Final'),
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 2
                }
            ]
        }
    ]

def bracket_1e_32_fai():
    return [
        {
            'name': __('Race') + ' 1 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 1
                },
                {
                    'method': 'input',
                    'seed_rank': 16
                },
                {
                    'method': 'input',
                    'seed_rank': 24
                },
                {
                    'method': 'input',
                    'seed_rank': 32
                }
            ]
        },
        {
            'name': __('Race') + ' 2 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 8
                },
                {
                    'method': 'input',
                    'seed_rank': 9
                },
                {
                    'method': 'input',
                    'seed_rank': 17
                },
                {
                    'method': 'input',
                    'seed_rank': 25
                }
            ]
        },
        {
            'name': __('Race') + ' 3 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 6
                },
                {
                    'method': 'input',
                    'seed_rank': 11
                },
                {
                    'method': 'input',
                    'seed_rank': 19
                },
                {
                    'method': 'input',
                    'seed_rank': 27
                }
            ]
        },
        {
            'name': __('Race') + ' 4 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 4
                },
                {
                    'method': 'input',
                    'seed_rank': 13
                },
                {
                    'method': 'input',
                    'seed_rank': 21
                },
                {
                    'method': 'input',
                    'seed_rank': 29
                }
            ]
        },
        {
            'name': __('Race') + ' 5 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 3
                },
                {
                    'method': 'input',
                    'seed_rank': 14
                },
                {
                    'method': 'input',
                    'seed_rank': 22
                },
                {
                    'method': 'input',
                    'seed_rank': 30
                }
            ]
        },
        {
            'name': __('Race') + ' 6 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 5
                },
                {
                    'method': 'input',
                    'seed_rank': 12
                },
                {
                    'method': 'input',
                    'seed_rank': 20
                },
                {
                    'method': 'input',
                    'seed_rank': 28
                }
            ]
        },
        {
            'name': __('Race') + ' 7 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 7
                },
                {
                    'method': 'input',
                    'seed_rank': 10
                },
                {
                    'method': 'input',
                    'seed_rank': 18
                },
                {
                    'method': 'input',
                    'seed_rank': 26
                }
            ]
        },
        {
            'name': __('Race') + ' 8 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 2
                },
                {
                    'method': 'input',
                    'seed_rank': 15
                },
                {
                    'method': 'input',
                    'seed_rank': 23
                },
                {
                    'method': 'input',
                    'seed_rank': 31
                }
            ]
        },
        {
            'name': __('Race') + ' 9 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 10 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 11 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 12 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 6,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 6,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Semifinal') + ' 1',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 8,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 8,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 9,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 9,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Semifinal') + ' 2',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 10,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 10,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 11,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 11,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Small Final'),
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 12,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 12,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 13,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 13,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Final'),
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 12,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 12,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 13,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 13,
                    'seed_rank': 2
                }
            ]
        }
    ]

def bracket_1e_64_fai():
    return [
        {
            'name': __('Race') + ' 1 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 1
                },
                {
                    'method': 'input',
                    'seed_rank': 32
                },
                {
                    'method': 'input',
                    'seed_rank': 48
                },
                {
                    'method': 'input',
                    'seed_rank': 64
                }
            ]
        },
        {
            'name': __('Race') + ' 2 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 16
                },
                {
                    'method': 'input',
                    'seed_rank': 17
                },
                {
                    'method': 'input',
                    'seed_rank': 33
                },
                {
                    'method': 'input',
                    'seed_rank': 49
                }
            ]
        },
        {
            'name': __('Race') + ' 3 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 8
                },
                {
                    'method': 'input',
                    'seed_rank': 25
                },
                {
                    'method': 'input',
                    'seed_rank': 41
                },
                {
                    'method': 'input',
                    'seed_rank': 57
                }
            ]
        },
        {
            'name': __('Race') + ' 4 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 14
                },
                {
                    'method': 'input',
                    'seed_rank': 19
                },
                {
                    'method': 'input',
                    'seed_rank': 35
                },
                {
                    'method': 'input',
                    'seed_rank': 51
                }
            ]
        },
        {
            'name': __('Race') + ' 5 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 4
                },
                {
                    'method': 'input',
                    'seed_rank': 29
                },
                {
                    'method': 'input',
                    'seed_rank': 45
                },
                {
                    'method': 'input',
                    'seed_rank': 61
                }
            ]
        },
        {
            'name': __('Race') + ' 6 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 12
                },
                {
                    'method': 'input',
                    'seed_rank': 21
                },
                {
                    'method': 'input',
                    'seed_rank': 37
                },
                {
                    'method': 'input',
                    'seed_rank': 53
                }
            ]
        },
        {
            'name': __('Race') + ' 7 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 6
                },
                {
                    'method': 'input',
                    'seed_rank': 27
                },
                {
                    'method': 'input',
                    'seed_rank': 43
                },
                {
                    'method': 'input',
                    'seed_rank': 59
                }
            ]
        },
        {
            'name': __('Race') + ' 8 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 10
                },
                {
                    'method': 'input',
                    'seed_rank': 23
                },
                {
                    'method': 'input',
                    'seed_rank': 39
                },
                {
                    'method': 'input',
                    'seed_rank': 55
                }
            ]
        },
        {
            'name': __('Race') + ' 9 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 9
                },
                {
                    'method': 'input',
                    'seed_rank': 24
                },
                {
                    'method': 'input',
                    'seed_rank': 40
                },
                {
                    'method': 'input',
                    'seed_rank': 56
                }
            ]
        },
        {
            'name': __('Race') + ' 10 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 5
                },
                {
                    'method': 'input',
                    'seed_rank': 28
                },
                {
                    'method': 'input',
                    'seed_rank': 44
                },
                {
                    'method': 'input',
                    'seed_rank': 60
                }
            ]
        },
        {
            'name': __('Race') + ' 11 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 11
                },
                {
                    'method': 'input',
                    'seed_rank': 22
                },
                {
                    'method': 'input',
                    'seed_rank': 38
                },
                {
                    'method': 'input',
                    'seed_rank': 54
                }
            ]
        },
        {
            'name': __('Race') + ' 12 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 3
                },
                {
                    'method': 'input',
                    'seed_rank': 30
                },
                {
                    'method': 'input',
                    'seed_rank': 46
                },
                {
                    'method': 'input',
                    'seed_rank': 62
                }
            ]
        },
        {
            'name': __('Race') + ' 13 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 13
                },
                {
                    'method': 'input',
                    'seed_rank': 20
                },
                {
                    'method': 'input',
                    'seed_rank': 36
                },
                {
                    'method': 'input',
                    'seed_rank': 52
                }
            ]
        },
        {
            'name': __('Race') + ' 14 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 7
                },
                {
                    'method': 'input',
                    'seed_rank': 26
                },
                {
                    'method': 'input',
                    'seed_rank': 42
                },
                {
                    'method': 'input',
                    'seed_rank': 58
                }
            ]
        },
        {
            'name': __('Race') + ' 15 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 15
                },
                {
                    'method': 'input',
                    'seed_rank': 18
                },
                {
                    'method': 'input',
                    'seed_rank': 34
                },
                {
                    'method': 'input',
                    'seed_rank': 50
                }
            ]
        },
        {
            'name': __('Race') + ' 16 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 2
                },
                {
                    'method': 'input',
                    'seed_rank': 31
                },
                {
                    'method': 'input',
                    'seed_rank': 47
                },
                {
                    'method': 'input',
                    'seed_rank': 63
                }
            ]
        },
        {
            'name': __('Race') + ' 17 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 18 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 19 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 20 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 6,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 6,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 21 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 8,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 8,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 9,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 9,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 22 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 10,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 10,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 11,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 11,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 23 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 12,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 12,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 13,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 13,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 24 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 14,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 14,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 15,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 15,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 25 (E3)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 16,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 16,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 17,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 17,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 26 (E3)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 18,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 18,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 19,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 19,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 27 (E3)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 20,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 20,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 21,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 21,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 28 (E3)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 22,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 22,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 23,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 23,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Semifinal 1'),
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 24,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 24,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 25,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 25,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Semifinal 2'),
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 26,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 26,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 27,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 27,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Small Final'),
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 28,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 28,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 29,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 29,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Final'),
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 28,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 28,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 29,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 29,
                    'seed_rank': 2
                }
            ]
        }
    ]

def bracket_2e_16_fai():
    return [
       {
            'name': __('Race') + ' 1',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 1
                },
                {
                    'method': 'input',
                    'seed_rank': 8
                },
                {
                    'method': 'input',
                    'seed_rank': 9
                },
                {
                    'method': 'input',
                    'seed_rank': 16
                }
            ]
        },
        {
            'name': __('Race') + ' 2',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 4
                },
                {
                    'method': 'input',
                    'seed_rank': 5
                },
                {
                    'method': 'input',
                    'seed_rank': 12
                },
                {
                    'method': 'input',
                    'seed_rank': 13
                }
            ]
        },
        {
            'name': __('Race') + ' 3',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 3
                },
                {
                    'method': 'input',
                    'seed_rank': 6
                },
                {
                    'method': 'input',
                    'seed_rank': 10
                },
                {
                    'method': 'input',
                    'seed_rank': 14
                }
            ]
        },
        {
            'name': __('Race') + ' 4',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 2
                },
                {
                    'method': 'input',
                    'seed_rank': 7
                },
                {
                    'method': 'input',
                    'seed_rank': 11
                },
                {
                    'method': 'input',
                    'seed_rank': 15
                }
            ]
        },
        {
            'name': __('Race') + ' 5',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 6',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 7',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 8',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 9',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 6,
                    'seed_rank': 3
                }
            ]
        },
        {
            'name': __('Race') + ' 10',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 6,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 3
                }
            ]
        },
        {
            'name': __('Race') + ' 11',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 8,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 8,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 9,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 9,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 12',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 6,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 6,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 13',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 11,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 10,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 10,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 11,
                    'seed_rank': 3
                }
            ]
        },
        {
            'name': __('Final'),
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 12,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 11,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 11,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 12,
                    'seed_rank': 1
                }
            ]
        }
    ]

def bracket_2e_32_fai():
    return [
        {
            'name': __('Race') + ' 1 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 1
                },
                {
                    'method': 'input',
                    'seed_rank': 16
                },
                {
                    'method': 'input',
                    'seed_rank': 24
                },
                {
                    'method': 'input',
                    'seed_rank': 32
                }
            ]
        },
        {
            'name': __('Race') + ' 2 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 8
                },
                {
                    'method': 'input',
                    'seed_rank': 9
                },
                {
                    'method': 'input',
                    'seed_rank': 17
                },
                {
                    'method': 'input',
                    'seed_rank': 25
                }
            ]
        },
        {
            'name': __('Race') + ' 3 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 6
                },
                {
                    'method': 'input',
                    'seed_rank': 11
                },
                {
                    'method': 'input',
                    'seed_rank': 19
                },
                {
                    'method': 'input',
                    'seed_rank': 27
                }
            ]
        },
        {
            'name': __('Race') + ' 4 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 4
                },
                {
                    'method': 'input',
                    'seed_rank': 13
                },
                {
                    'method': 'input',
                    'seed_rank': 21
                },
                {
                    'method': 'input',
                    'seed_rank': 29
                }
            ]
        },
        {
            'name': __('Race') + ' 5 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 3
                },
                {
                    'method': 'input',
                    'seed_rank': 14
                },
                {
                    'method': 'input',
                    'seed_rank': 22
                },
                {
                    'method': 'input',
                    'seed_rank': 30
                }
            ]
        },
        {
            'name': __('Race') + ' 6 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 5
                },
                {
                    'method': 'input',
                    'seed_rank': 12
                },
                {
                    'method': 'input',
                    'seed_rank': 20
                },
                {
                    'method': 'input',
                    'seed_rank': 28
                }
            ]
        },
        {
            'name': __('Race') + ' 7 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 7
                },
                {
                    'method': 'input',
                    'seed_rank': 10
                },
                {
                    'method': 'input',
                    'seed_rank': 18
                },
                {
                    'method': 'input',
                    'seed_rank': 26
                }
            ]
        },
        {
            'name': __('Race') + ' 8 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 2
                },
                {
                    'method': 'input',
                    'seed_rank': 15
                },
                {
                    'method': 'input',
                    'seed_rank': 23
                },
                {
                    'method': 'input',
                    'seed_rank': 31
                }
            ]
        },
        {
            'name': __('Race') + ' 9 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 10 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 11 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 12 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 6,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 6,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 13 (DE1)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 14 (DE1)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 6,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 15 (DE1)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 16 (DE1)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 6,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 17 (DE2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 8,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 14,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 15,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 9,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 18 (DE2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 10,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 12,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 13,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 11,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 19 (DE2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 9,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 15,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 14,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 8,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 20 (DE2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 11,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 13,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 12,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 10,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 21 (DE3)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 18,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 16,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 17,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 19,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 22 (DE3)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 16,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 18,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 19,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 17,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 23 (E3)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 8,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 8,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 9,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 9,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 24 (E3)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 10,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 10,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 11,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 11,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 25 (DE4)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 22,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 20,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 21,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 23,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 26 (DE4)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 23,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 21,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 20,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 22,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 27 (DE5)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 24,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 24,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 25,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 25,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 28 (E4)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 22,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 22,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 23,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 23,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 29 (DE6)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 27,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 26,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 26,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 27,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Final'),
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 28,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 27,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 27,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 28,
                    'seed_rank': 1
                }
            ]
        }
    ]

def bracket_2e_64_fai():
    return [
        {
            'name': __('Race') + ' 1 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 1
                },
                {
                    'method': 'input',
                    'seed_rank': 32
                },
                {
                    'method': 'input',
                    'seed_rank': 48
                },
                {
                    'method': 'input',
                    'seed_rank': 64
                }
            ]
        },
        {
            'name': __('Race') + ' 2 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 16
                },
                {
                    'method': 'input',
                    'seed_rank': 17
                },
                {
                    'method': 'input',
                    'seed_rank': 33
                },
                {
                    'method': 'input',
                    'seed_rank': 49
                }
            ]
        },
        {
            'name': __('Race') + ' 3 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 8
                },
                {
                    'method': 'input',
                    'seed_rank': 25
                },
                {
                    'method': 'input',
                    'seed_rank': 41
                },
                {
                    'method': 'input',
                    'seed_rank': 57
                }
            ]
        },
        {
            'name': __('Race') + ' 4 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 14
                },
                {
                    'method': 'input',
                    'seed_rank': 19
                },
                {
                    'method': 'input',
                    'seed_rank': 35
                },
                {
                    'method': 'input',
                    'seed_rank': 51
                }
            ]
        },
        {
            'name': __('Race') + ' 5 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 4
                },
                {
                    'method': 'input',
                    'seed_rank': 29
                },
                {
                    'method': 'input',
                    'seed_rank': 45
                },
                {
                    'method': 'input',
                    'seed_rank': 61
                }
            ]
        },
        {
            'name': __('Race') + ' 6 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 12
                },
                {
                    'method': 'input',
                    'seed_rank': 21
                },
                {
                    'method': 'input',
                    'seed_rank': 37
                },
                {
                    'method': 'input',
                    'seed_rank': 53
                }
            ]
        },
        {
            'name': __('Race') + ' 7 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 6
                },
                {
                    'method': 'input',
                    'seed_rank': 27
                },
                {
                    'method': 'input',
                    'seed_rank': 43
                },
                {
                    'method': 'input',
                    'seed_rank': 59
                }
            ]
        },
        {
            'name': __('Race') + ' 8 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 10
                },
                {
                    'method': 'input',
                    'seed_rank': 23
                },
                {
                    'method': 'input',
                    'seed_rank': 39
                },
                {
                    'method': 'input',
                    'seed_rank': 55
                }
            ]
        },
        {
            'name': __('Race') + ' 9 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 9
                },
                {
                    'method': 'input',
                    'seed_rank': 24
                },
                {
                    'method': 'input',
                    'seed_rank': 40
                },
                {
                    'method': 'input',
                    'seed_rank': 56
                }
            ]
        },
        {
            'name': __('Race') + ' 10 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 5
                },
                {
                    'method': 'input',
                    'seed_rank': 28
                },
                {
                    'method': 'input',
                    'seed_rank': 44
                },
                {
                    'method': 'input',
                    'seed_rank': 60
                }
            ]
        },
        {
            'name': __('Race') + ' 11 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 11
                },
                {
                    'method': 'input',
                    'seed_rank': 22
                },
                {
                    'method': 'input',
                    'seed_rank': 38
                },
                {
                    'method': 'input',
                    'seed_rank': 54
                }
            ]
        },
        {
            'name': __('Race') + ' 12 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 3
                },
                {
                    'method': 'input',
                    'seed_rank': 30
                },
                {
                    'method': 'input',
                    'seed_rank': 46
                },
                {
                    'method': 'input',
                    'seed_rank': 62
                }
            ]
        },
        {
            'name': __('Race') + ' 13 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 13
                },
                {
                    'method': 'input',
                    'seed_rank': 20
                },
                {
                    'method': 'input',
                    'seed_rank': 36
                },
                {
                    'method': 'input',
                    'seed_rank': 52
                }
            ]
        },
        {
            'name': __('Race') + ' 14 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 7
                },
                {
                    'method': 'input',
                    'seed_rank': 26
                },
                {
                    'method': 'input',
                    'seed_rank': 42
                },
                {
                    'method': 'input',
                    'seed_rank': 58
                }
            ]
        },
        {
            'name': __('Race') + ' 15 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 15
                },
                {
                    'method': 'input',
                    'seed_rank': 18
                },
                {
                    'method': 'input',
                    'seed_rank': 34
                },
                {
                    'method': 'input',
                    'seed_rank': 50
                }
            ]
        },
        {
            'name': __('Race') + ' 16 (E1)',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 2
                },
                {
                    'method': 'input',
                    'seed_rank': 31
                },
                {
                    'method': 'input',
                    'seed_rank': 47
                },
                {
                    'method': 'input',
                    'seed_rank': 63
                }
            ]
        },
        {
            'name': __('Race') + ' 17 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 18 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 19 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 20 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 6,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 6,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 21 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 8,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 8,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 9,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 9,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 22 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 10,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 10,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 11,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 11,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 23 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 12,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 12,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 13,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 13,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 24 (E2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 14,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 14,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 15,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 15,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 25 (DE1)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 26 (DE1)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 6,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 27 (DE1)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 28 (DE1)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 6,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 29 (DE1)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 8,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 9,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 10,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 11,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 30 (DE1)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 12,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 13,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 14,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 15,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 31 (DE1)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 9,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 8,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 11,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 10,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 32 (DE1)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 13,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 12,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 15,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 14,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 33 (DE2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 16,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 30,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 31,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 17,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 34 (DE2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 18,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 28,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 29,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 19,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 35 (DE2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 17,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 31,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 30,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 16,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 36 (DE2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 19,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 29,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 28,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 18,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 37 (DE2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 20,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 25,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 24,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 21,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 38 (DE2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 22,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 27,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 26,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 23,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 39 (DE2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 21,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 24,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 25,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 20,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 40 (DE2)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 23,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 26,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 27,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 22,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 41 (DE3)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 34,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 32,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 33,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 35,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 42 (DE3)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 32,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 34,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 35,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 33,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 43 (DE3)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 38,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 36,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 37,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 39,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 44 (DE3)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 36,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 38,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 39,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 37,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 45 (E3)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 16,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 16,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 17,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 17,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 46 (E3)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 18,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 18,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 19,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 19,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 47 (E3)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 20,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 20,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 21,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 21,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 48 (E3)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 22,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 22,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 23,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 23,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 49 (DE4)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 44,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 42,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 43,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 45,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 50 (DE4)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 46,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 40,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 41,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 47,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 51 (DE4)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 45,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 43,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 42,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 44,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 52 (DE4)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 47,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 41,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 40,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 46,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 53 (DE5)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 50,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 48,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 49,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 51,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 54 (DE5)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 48,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 50,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 51,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 49,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 55 (E4)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 44,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 44,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 45,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 45,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 56 (E4)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 46,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 46,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 47,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 47,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 57 (DE6)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 54,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 52,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 53,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 55,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 58 (DE6)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 55,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 53,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 52,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 54,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 59 (DE7)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 56,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 56,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 57,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 57,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 60 (E5)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 54,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 54,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 55,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 55,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 61 (DE7)',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 59,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 58,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 58,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 59,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Final'),
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 60,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 59,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 59,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 60,
                    'seed_rank': 1
                }
            ]
        }
    ]

def bracket_2e_16_multigp():
    return [
        {
            'name': __('Race') + ' 1',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 3
                },
                {
                    'method': 'input',
                    'seed_rank': 6
                },
                {
                    'method': 'input',
                    'seed_rank': 11
                },
                {
                    'method': 'input',
                    'seed_rank': 14
                }
            ]
        },
        {
            'name': __('Race') + ' 2',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 2
                },
                {
                    'method': 'input',
                    'seed_rank': 7
                },
                {
                    'method': 'input',
                    'seed_rank': 10
                },
                {
                    'method': 'input',
                    'seed_rank': 15
                }
            ]
        },
        {
            'name': __('Race') + ' 3',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 4
                },
                {
                    'method': 'input',
                    'seed_rank': 5
                },
                {
                    'method': 'input',
                    'seed_rank': 12
                },
                {
                    'method': 'input',
                    'seed_rank': 13
                }
            ]
        },
        {
            'name': __('Race') + ' 4',
            'slots': [
                {
                    'method': 'input',
                    'seed_rank': 1
                },
                {
                    'method': 'input',
                    'seed_rank': 8
                },
                {
                    'method': 'input',
                    'seed_rank': 9
                },
                {
                    'method': 'input',
                    'seed_rank': 16
                }
            ]
        },
        {
            'name': __('Race') + ' 5',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 6',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 0,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 1,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 7',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 4
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 8',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 2,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 3,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 9',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 4,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 10',
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 6,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 6,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 11: ' + __('Winners Bracket Semifinal'),
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 5,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 7,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 12: ' + __('Winners Bracket Semifinal'),
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 8,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 8,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 9,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 9,
                    'seed_rank': 2
                }
            ]
        },
        {
            'name': __('Race') + ' 13: ' + __('Consolation Bracket Semifinal'),
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 11,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 11,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 10,
                    'seed_rank': 3
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 10,
                    'seed_rank': 4
                }
            ]
        },
        {
            'name': __('Race') + ' 14: ' + __('Winners Bracket Final'),
            'slots': [
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 10,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 10,
                    'seed_rank': 2
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 12,
                    'seed_rank': 1
                },
                {
                    'method': ProgramMethod.HEAT_RESULT,
                    'seed_heat_id': 12,
                    'seed_rank': 2
                }
            ]
        }
    ]

def bracket_1e_std(_RaceContext, generate_args):
    if 'standard' not in generate_args:
        return False

    if generate_args['standard'] == 'fai16':
        heats = bracket_1e_16_fai()
    elif generate_args['standard'] == 'fai32':
        heats = bracket_1e_32_fai()
    elif generate_args['standard'] == 'fai64':
        heats = bracket_1e_64_fai()
    else:
        return False

    if 'seed_offset' in generate_args:
        seed_offset = max(int(generate_args['seed_offset']) - 1, 0)
        if seed_offset:
            for heat in heats:
                for slot in heat['slots']:
                    if slot['method'] == 'input':
                        slot['seed_rank'] += seed_offset

    return heats

def bracket_2e_std(_RaceContext, generate_args):
    if 'standard' not in generate_args:
        return False

    if generate_args['standard'] == 'fai16':
        heats = bracket_2e_16_fai()
    elif generate_args['standard'] == 'fai32':
        heats = bracket_2e_32_fai()
    elif generate_args['standard'] == 'fai64':
        heats = bracket_2e_64_fai()
    elif generate_args['standard'] == 'multigp16':
        return bracket_2e_16_multigp()
    else:
        return False

    if 'seed_offset' in generate_args:
        seed_offset = max(int(generate_args['seed_offset']) - 1, 0)
        if seed_offset:
            for heat in heats[:4]:
                for slot in heat['slots']:
                    slot['seed_rank'] += seed_offset

    return heats

def discover(*_args, **_kwargs):
    # returns array of exporters with default arguments
    return [
        HeatGenerator(
            'bracket_1e_std',
            'Standard bracket, single elimination',
            bracket_1e_std,
            None,
            [
                {
                    'id': 'standard',
                    'label': "Standard",
                    'fieldType': 'select',
                    'options': [
                        {'name': "fai16", 'value': "FAI, 4-up, 16-pilot"},
                        {'name': "fai32", 'value': "FAI, 4-up, 32-pilot"},
                        {'name': "fai64", 'value': "FAI, 4-up, 64-pilot"},
                    ],
                    'value': "fai16",
                },
                {
                    'id': 'seed_offset',
                    'label': "Seed from rank",
                    'fieldType': 'basic_int',
                    'value': 1,
                },
            ],
        ),
        HeatGenerator(
            'bracket_2e_std',
            'Standard bracket, double elimination',
            bracket_2e_std,
            None,
            [
                {
                    'id': 'standard',
                    'label': "Standard",
                    'fieldType': 'select',
                    'options': [
                        {'name': "fai16", 'value': "FAI, 4-up, 16-pilot"},
                        {'name': "fai32", 'value': "FAI, 4-up, 32-pilot"},
                        {'name': "fai64", 'value': "FAI, 4-up, 64-pilot"},
                        {'name': "multigp16", 'value': "MultiGP, 4-up, 16-pilot"},
                    ],
                    'value': "fai16",
                },
                {
                    'id': 'seed_offset',
                    'label': "Seed from rank",
                    'fieldType': 'basic_int',
                    'value': 1,
                },
            ],
        ),
    ]
