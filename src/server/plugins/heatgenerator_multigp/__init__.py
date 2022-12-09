'''JSON data exporter'''

import logging
logger = logging.getLogger(__name__)
from HeatGenerator import HeatGenerator
from Database import ProgramMethod

def registerHandlers(args):
    if 'registerFn' in args:
        for generator in discover():
            args['registerFn'](generator)

def initialize(**kwargs):
    if 'Events' in kwargs:
        kwargs['Events'].on('HeatGenerator_Initialize', 'HeatGenerator_register_mgp2e', registerHandlers, {}, 75, True)

def bracket_2e_mgp(RHData, Results, PageCache, Language, generate_args=None):
    heats = [
        {
            'name': 'Race 1',
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
            'name': 'Race 2',
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
            'name': 'Race 3',
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
            'name': 'Race 4',
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
            'name': 'Race 5',
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
            'name': 'Race 6',
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
            'name': 'Race 7',
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
            'name': 'Race 8',
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
            'name': 'Race 9',
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
            'name': 'Race 10',
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
            'name': 'Race 11: Winners Bracket Semifinal',
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
            'name': 'Race 12: Winners Bracket Semifinal',
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
            'name': 'Race 13: Consolation Bracket Semifinal',
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
            'name': 'Race 14: Winners Bracket Final',
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

    return heats

def discover(*args, **kwargs):
    # returns array of exporters with default arguments
    return [
        HeatGenerator(
            'bracket_2e_mgp',
            '16-seed Double Elimination (MultiGP)',
            bracket_2e_mgp,
        ),
    ]
