'''Standardized heat structures'''
# FAI: https://www.fai.org/sites/default/files/ciam/wcup_drones/sc4_vol_f9_dronesport_22_2022-03-01_0.pdf
# MultiGP: https://docs.google.com/document/d/1jWVjCnoIGdW1j_bklrbg-0D24c3x6YG5m_vmF7faG-U/edit#heading=h.hoxlrr3v86bb

import logging
from eventmanager import Evt
from HeatGenerator import HeatGenerator, HeatPlan, HeatPlanSlot, SeedMethod
from RHUI import UIField, UIFieldType, UIFieldSelectOption

logger = logging.getLogger(__name__)

def registerHandlers(args):
    if 'registerFn' in args:
        for generator in discover():
            args['registerFn'](generator)

def initialize(**kwargs):
    if 'Events' in kwargs:
        kwargs['Events'].on(Evt.HEAT_GENERATOR_INITIALIZE, 'HeatGenerator_register_standards', registerHandlers, {}, 75)

def bracket_1e_16_fai(RHAPI):
    return [
        HeatPlan(
            RHAPI.__('Race') + ' 1',
            [
                HeatPlanSlot(SeedMethod.INPUT, 1),
                HeatPlanSlot(SeedMethod.INPUT, 8),
                HeatPlanSlot(SeedMethod.INPUT, 9),
                HeatPlanSlot(SeedMethod.INPUT, 16)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 2',
            [
                HeatPlanSlot(SeedMethod.INPUT, 4),
                HeatPlanSlot(SeedMethod.INPUT, 5),
                HeatPlanSlot(SeedMethod.INPUT, 12),
                HeatPlanSlot(SeedMethod.INPUT, 13)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 3',
            [
                HeatPlanSlot(SeedMethod.INPUT, 3),
                HeatPlanSlot(SeedMethod.INPUT, 6),
                HeatPlanSlot(SeedMethod.INPUT, 10),
                HeatPlanSlot(SeedMethod.INPUT, 14)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 4',
            [
                HeatPlanSlot(SeedMethod.INPUT, 2),
                HeatPlanSlot(SeedMethod.INPUT, 7),
                HeatPlanSlot(SeedMethod.INPUT, 11),
                HeatPlanSlot(SeedMethod.INPUT, 15)
            ]
        ),
        HeatPlan(
            RHAPI.__('Semifinal') + ' 1',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 1)
            ]
        ),
        HeatPlan(
            RHAPI.__('Semifinal') + ' 2',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 3)
            ]
        ),
        HeatPlan(
            RHAPI.__('Small Final'),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 5)
            ]
        ),
        HeatPlan(
            RHAPI.__('Final'),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 5)
            ]
        )
    ]

def bracket_1e_32_fai(RHAPI):
    return [
        HeatPlan(
            RHAPI.__('Race') + ' 1 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 1),
                HeatPlanSlot(SeedMethod.INPUT, 16),
                HeatPlanSlot(SeedMethod.INPUT, 24),
                HeatPlanSlot(SeedMethod.INPUT, 32)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 2 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 8),
                HeatPlanSlot(SeedMethod.INPUT, 9),
                HeatPlanSlot(SeedMethod.INPUT, 17),
                HeatPlanSlot(SeedMethod.INPUT, 25)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 3 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 6),
                HeatPlanSlot(SeedMethod.INPUT, 11),
                HeatPlanSlot(SeedMethod.INPUT, 19),
                HeatPlanSlot(SeedMethod.INPUT, 27)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 4 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 4),
                HeatPlanSlot(SeedMethod.INPUT, 13),
                HeatPlanSlot(SeedMethod.INPUT, 21),
                HeatPlanSlot(SeedMethod.INPUT, 29)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 5 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 3),
                HeatPlanSlot(SeedMethod.INPUT, 14),
                HeatPlanSlot(SeedMethod.INPUT, 22),
                HeatPlanSlot(SeedMethod.INPUT, 30)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 6 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 5),
                HeatPlanSlot(SeedMethod.INPUT, 12),
                HeatPlanSlot(SeedMethod.INPUT, 20),
                HeatPlanSlot(SeedMethod.INPUT, 28)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 7 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 7),
                HeatPlanSlot(SeedMethod.INPUT, 10),
                HeatPlanSlot(SeedMethod.INPUT, 18),
                HeatPlanSlot(SeedMethod.INPUT, 26)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 8 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 2),
                HeatPlanSlot(SeedMethod.INPUT, 15),
                HeatPlanSlot(SeedMethod.INPUT, 23),
                HeatPlanSlot(SeedMethod.INPUT, 31)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 9 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 1)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 10 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 3)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 11 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 5)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 12 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 7)
            ]
        ),
        HeatPlan(
            RHAPI.__('Semifinal') + ' 1',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 9),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 9)
            ]
        ),
        HeatPlan(
            RHAPI.__('Semifinal') + ' 2',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 11)
            ]
        ),
        HeatPlan(
            RHAPI.__('Small Final'),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 13),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 13)
            ]
        ),
        HeatPlan(
            RHAPI.__('Final'),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 13),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 13)
            ]
        )
    ]

def bracket_1e_64_fai(RHAPI):
    return [
        HeatPlan(
            RHAPI.__('Race') + ' 1 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 1),
                HeatPlanSlot(SeedMethod.INPUT, 32),
                HeatPlanSlot(SeedMethod.INPUT, 48),
                HeatPlanSlot(SeedMethod.INPUT, 64)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 2 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 16),
                HeatPlanSlot(SeedMethod.INPUT, 17),
                HeatPlanSlot(SeedMethod.INPUT, 33),
                HeatPlanSlot(SeedMethod.INPUT, 49)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 3 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 8),
                HeatPlanSlot(SeedMethod.INPUT, 25),
                HeatPlanSlot(SeedMethod.INPUT, 41),
                HeatPlanSlot(SeedMethod.INPUT, 57)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 4 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 14),
                HeatPlanSlot(SeedMethod.INPUT, 19),
                HeatPlanSlot(SeedMethod.INPUT, 35),
                HeatPlanSlot(SeedMethod.INPUT, 51)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 5 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 4),
                HeatPlanSlot(SeedMethod.INPUT, 29),
                HeatPlanSlot(SeedMethod.INPUT, 45),
                HeatPlanSlot(SeedMethod.INPUT, 61)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 6 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 12),
                HeatPlanSlot(SeedMethod.INPUT, 21),
                HeatPlanSlot(SeedMethod.INPUT, 37),
                HeatPlanSlot(SeedMethod.INPUT, 53)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 7 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 6),
                HeatPlanSlot(SeedMethod.INPUT, 27),
                HeatPlanSlot(SeedMethod.INPUT, 43),
                HeatPlanSlot(SeedMethod.INPUT, 59)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 8 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 10),
                HeatPlanSlot(SeedMethod.INPUT, 23),
                HeatPlanSlot(SeedMethod.INPUT, 39),
                HeatPlanSlot(SeedMethod.INPUT, 55)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 9 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 9),
                HeatPlanSlot(SeedMethod.INPUT, 24),
                HeatPlanSlot(SeedMethod.INPUT, 40),
                HeatPlanSlot(SeedMethod.INPUT, 56)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 10 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 5),
                HeatPlanSlot(SeedMethod.INPUT, 28),
                HeatPlanSlot(SeedMethod.INPUT, 44),
                HeatPlanSlot(SeedMethod.INPUT, 60)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 11 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 11),
                HeatPlanSlot(SeedMethod.INPUT, 22),
                HeatPlanSlot(SeedMethod.INPUT, 38),
                HeatPlanSlot(SeedMethod.INPUT, 54)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 12 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 3),
                HeatPlanSlot(SeedMethod.INPUT, 30),
                HeatPlanSlot(SeedMethod.INPUT, 46),
                HeatPlanSlot(SeedMethod.INPUT, 62)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 13 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 13),
                HeatPlanSlot(SeedMethod.INPUT, 20),
                HeatPlanSlot(SeedMethod.INPUT, 36),
                HeatPlanSlot(SeedMethod.INPUT, 52)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 14 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 7),
                HeatPlanSlot(SeedMethod.INPUT, 26),
                HeatPlanSlot(SeedMethod.INPUT, 42),
                HeatPlanSlot(SeedMethod.INPUT, 58)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 15 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 15),
                HeatPlanSlot(SeedMethod.INPUT, 18),
                HeatPlanSlot(SeedMethod.INPUT, 34),
                HeatPlanSlot(SeedMethod.INPUT, 50)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 16 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 2),
                HeatPlanSlot(SeedMethod.INPUT, 31),
                HeatPlanSlot(SeedMethod.INPUT, 47),
                HeatPlanSlot(SeedMethod.INPUT, 63)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 17 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 1)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 18 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 3)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 19 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 5)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 20 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 7)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 21 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 9),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 9)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 22 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 11)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 23 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 13),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 13)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 24 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 14),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 14),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 15),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 15)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 25 (E3)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 16),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 16),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 17),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 17)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 26 (E3)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 18),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 18),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 19),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 19)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 27 (E3)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 20),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 20),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 21),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 21)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 28 (E3)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 22),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 22),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 23),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 23)
            ]
        ),
        HeatPlan(
            RHAPI.__('Semifinal 1'),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 24),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 24),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 25),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 25)
            ]
        ),
        HeatPlan(
            RHAPI.__('Semifinal 2'),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 26),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 26),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 27),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 27)
            ]
        ),
        HeatPlan(
            RHAPI.__('Small Final'),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 28),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 28),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 29),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 29)
            ]
        ),
        HeatPlan(
            RHAPI.__('Final'),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 28),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 28),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 29),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 29)
            ]
        )
    ]

def bracket_2e_16_fai(RHAPI):
    return [
       HeatPlan(
            RHAPI.__('Race') + ' 1',
            [
                HeatPlanSlot(SeedMethod.INPUT, 1),
                HeatPlanSlot(SeedMethod.INPUT, 8),
                HeatPlanSlot(SeedMethod.INPUT, 9),
                HeatPlanSlot(SeedMethod.INPUT, 16)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 2',
            [
                HeatPlanSlot(SeedMethod.INPUT, 4),
                HeatPlanSlot(SeedMethod.INPUT, 5),
                HeatPlanSlot(SeedMethod.INPUT, 12),
                HeatPlanSlot(SeedMethod.INPUT, 13)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 3',
            [
                HeatPlanSlot(SeedMethod.INPUT, 3),
                HeatPlanSlot(SeedMethod.INPUT, 6),
                HeatPlanSlot(SeedMethod.INPUT, 10),
                HeatPlanSlot(SeedMethod.INPUT, 14)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 4',
            [
                HeatPlanSlot(SeedMethod.INPUT, 2),
                HeatPlanSlot(SeedMethod.INPUT, 7),
                HeatPlanSlot(SeedMethod.INPUT, 11),
                HeatPlanSlot(SeedMethod.INPUT, 15)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 5',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 3)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 6',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 2)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 7',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 1)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 8',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 3)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 9',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 6)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 10',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 7)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 11',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 9),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 9)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 12',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 7)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 13',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 11)
            ]
        ),
        HeatPlan(
            RHAPI.__('Final'),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 12)
            ]
        )
    ]

def bracket_2e_32_fai(RHAPI):
    return [
        HeatPlan(
            RHAPI.__('Race') + ' 1 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 1),
                HeatPlanSlot(SeedMethod.INPUT, 16),
                HeatPlanSlot(SeedMethod.INPUT, 24),
                HeatPlanSlot(SeedMethod.INPUT, 32)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 2 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 8),
                HeatPlanSlot(SeedMethod.INPUT, 9),
                HeatPlanSlot(SeedMethod.INPUT, 17),
                HeatPlanSlot(SeedMethod.INPUT, 25)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 3 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 6),
                HeatPlanSlot(SeedMethod.INPUT, 11),
                HeatPlanSlot(SeedMethod.INPUT, 19),
                HeatPlanSlot(SeedMethod.INPUT, 27)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 4 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 4),
                HeatPlanSlot(SeedMethod.INPUT, 13),
                HeatPlanSlot(SeedMethod.INPUT, 21),
                HeatPlanSlot(SeedMethod.INPUT, 29)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 5 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 3),
                HeatPlanSlot(SeedMethod.INPUT, 14),
                HeatPlanSlot(SeedMethod.INPUT, 22),
                HeatPlanSlot(SeedMethod.INPUT, 30)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 6 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 5),
                HeatPlanSlot(SeedMethod.INPUT, 12),
                HeatPlanSlot(SeedMethod.INPUT, 20),
                HeatPlanSlot(SeedMethod.INPUT, 28)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 7 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 7),
                HeatPlanSlot(SeedMethod.INPUT, 10),
                HeatPlanSlot(SeedMethod.INPUT, 18),
                HeatPlanSlot(SeedMethod.INPUT, 26)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 8 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 2),
                HeatPlanSlot(SeedMethod.INPUT, 15),
                HeatPlanSlot(SeedMethod.INPUT, 23),
                HeatPlanSlot(SeedMethod.INPUT, 31)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 9 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 1)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 10 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 3)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 11 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 5)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 12 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 7)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 13 (DE1)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 3)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 14 (DE1)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 7)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 15 (DE1)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 2)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 16 (DE1)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 6)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 17 (DE2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 14),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 15),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 9)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 18 (DE2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 13),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 11)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 19 (DE2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 9),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 15),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 14),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 8)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 20 (DE2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 13),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 10)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 21 (DE3)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 18),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 16),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 17),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 19)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 22 (DE3)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 16),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 18),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 19),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 17)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 23 (E3)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 9),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 9)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 24 (E3)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 11)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 25 (DE4)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 22),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 20),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 21),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 23)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 26 (DE4)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 23),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 21),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 20),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 22)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 27 (DE5)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 24),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 24),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 25),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 25)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 28 (E4)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 22),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 22),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 23),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 23)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 29 (DE6)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 27),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 26),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 26),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 27)
            ]
        ),
        HeatPlan(
            RHAPI.__('Final'),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 28),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 27),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 27),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 28)
            ]
        )
    ]

def bracket_2e_64_fai(RHAPI):
    return [
        HeatPlan(
            RHAPI.__('Race') + ' 1 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 1),
                HeatPlanSlot(SeedMethod.INPUT, 32),
                HeatPlanSlot(SeedMethod.INPUT, 48),
                HeatPlanSlot(SeedMethod.INPUT, 64)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 2 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 16),
                HeatPlanSlot(SeedMethod.INPUT, 17),
                HeatPlanSlot(SeedMethod.INPUT, 33),
                HeatPlanSlot(SeedMethod.INPUT, 49)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 3 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 8),
                HeatPlanSlot(SeedMethod.INPUT, 25),
                HeatPlanSlot(SeedMethod.INPUT, 41),
                HeatPlanSlot(SeedMethod.INPUT, 57)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 4 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 14),
                HeatPlanSlot(SeedMethod.INPUT, 19),
                HeatPlanSlot(SeedMethod.INPUT, 35),
                HeatPlanSlot(SeedMethod.INPUT, 51)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 5 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 4),
                HeatPlanSlot(SeedMethod.INPUT, 29),
                HeatPlanSlot(SeedMethod.INPUT, 45),
                HeatPlanSlot(SeedMethod.INPUT, 61)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 6 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 12),
                HeatPlanSlot(SeedMethod.INPUT, 21),
                HeatPlanSlot(SeedMethod.INPUT, 37),
                HeatPlanSlot(SeedMethod.INPUT, 53)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 7 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 6),
                HeatPlanSlot(SeedMethod.INPUT, 27),
                HeatPlanSlot(SeedMethod.INPUT, 43),
                HeatPlanSlot(SeedMethod.INPUT, 59)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 8 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 10),
                HeatPlanSlot(SeedMethod.INPUT, 23),
                HeatPlanSlot(SeedMethod.INPUT, 39),
                HeatPlanSlot(SeedMethod.INPUT, 55)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 9 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 9),
                HeatPlanSlot(SeedMethod.INPUT, 24),
                HeatPlanSlot(SeedMethod.INPUT, 40),
                HeatPlanSlot(SeedMethod.INPUT, 56)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 10 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 5),
                HeatPlanSlot(SeedMethod.INPUT, 28),
                HeatPlanSlot(SeedMethod.INPUT, 44),
                HeatPlanSlot(SeedMethod.INPUT, 60)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 11 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 11),
                HeatPlanSlot(SeedMethod.INPUT, 22),
                HeatPlanSlot(SeedMethod.INPUT, 38),
                HeatPlanSlot(SeedMethod.INPUT, 54)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 12 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 3),
                HeatPlanSlot(SeedMethod.INPUT, 30),
                HeatPlanSlot(SeedMethod.INPUT, 46),
                HeatPlanSlot(SeedMethod.INPUT, 62)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 13 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 13),
                HeatPlanSlot(SeedMethod.INPUT, 20),
                HeatPlanSlot(SeedMethod.INPUT, 36),
                HeatPlanSlot(SeedMethod.INPUT, 52)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 14 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 7),
                HeatPlanSlot(SeedMethod.INPUT, 26),
                HeatPlanSlot(SeedMethod.INPUT, 42),
                HeatPlanSlot(SeedMethod.INPUT, 58)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 15 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 15),
                HeatPlanSlot(SeedMethod.INPUT, 18),
                HeatPlanSlot(SeedMethod.INPUT, 34),
                HeatPlanSlot(SeedMethod.INPUT, 50)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 16 (E1)',
            [
                HeatPlanSlot(SeedMethod.INPUT, 2),
                HeatPlanSlot(SeedMethod.INPUT, 31),
                HeatPlanSlot(SeedMethod.INPUT, 47),
                HeatPlanSlot(SeedMethod.INPUT, 63)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 17 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 1)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 18 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 3)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 19 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 5)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 20 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 7)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 21 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 9),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 9)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 22 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 11)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 23 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 13),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 13)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 24 (E2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 14),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 14),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 15),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 15)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 25 (DE1)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 3)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 26 (DE1)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 7)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 27 (DE1)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 2)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 28 (DE1)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 6)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 29 (DE1)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 9),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 11)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 30 (DE1)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 13),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 14),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 15)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 31 (DE1)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 9),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 10)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 32 (DE1)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 13),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 15),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 14)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 33 (DE2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 16),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 30),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 31),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 17)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 34 (DE2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 18),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 28),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 29),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 19)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 35 (DE2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 17),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 31),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 30),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 16)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 36 (DE2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 19),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 29),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 28),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 18)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 37 (DE2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 20),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 25),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 24),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 21)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 38 (DE2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 22),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 27),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 26),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 23)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 39 (DE2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 21),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 24),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 25),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 20)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 40 (DE2)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 23),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 26),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 27),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 22)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 41 (DE3)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 34),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 32),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 33),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 35)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 42 (DE3)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 32),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 34),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 35),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 33)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 43 (DE3)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 38),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 36),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 37),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 39)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 44 (DE3)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 36),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 38),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 39),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 37)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 45 (E3)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 16),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 16),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 17),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 17)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 46 (E3)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 18),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 18),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 19),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 19)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 47 (E3)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 20),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 20),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 21),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 21)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 48 (E3)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 22),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 22),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 23),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 23)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 49 (DE4)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 44),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 42),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 43),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 45)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 50 (DE4)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 46),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 40),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 41),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 47)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 51 (DE4)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 45),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 43),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 42),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 44)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 52 (DE4)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 47),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 41),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 40),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 46)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 53 (DE5)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 50),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 48),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 49),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 51)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 54 (DE5)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 48),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 50),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 51),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 49)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 55 (E4)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 44),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 44),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 45),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 45)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 56 (E4)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 46),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 46),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 47),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 47)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 57 (DE6)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 54),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 52),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 53),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 55)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 58 (DE6)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 55),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 53),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 52),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 54)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 59 (DE7)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 56),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 56),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 57),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 57)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 60 (E5)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 54),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 54),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 55),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 55)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 61 (DE7)',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 59),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 58),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 58),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 59)
            ]
        ),
        HeatPlan(
            RHAPI.__('Final'),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 60),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 59),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 59),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 60)
            ]
        )
    ]

def bracket_2e_16_multigp(RHAPI):
    return [
        HeatPlan(
            RHAPI.__('Race') + ' 1',
            [
                HeatPlanSlot(SeedMethod.INPUT, 3),
                HeatPlanSlot(SeedMethod.INPUT, 6),
                HeatPlanSlot(SeedMethod.INPUT, 11),
                HeatPlanSlot(SeedMethod.INPUT, 14)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 2',
            [
                HeatPlanSlot(SeedMethod.INPUT, 2),
                HeatPlanSlot(SeedMethod.INPUT, 7),
                HeatPlanSlot(SeedMethod.INPUT, 10),
                HeatPlanSlot(SeedMethod.INPUT, 15)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 3',
            [
                HeatPlanSlot(SeedMethod.INPUT, 4),
                HeatPlanSlot(SeedMethod.INPUT, 5),
                HeatPlanSlot(SeedMethod.INPUT, 12),
                HeatPlanSlot(SeedMethod.INPUT, 13)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 4',
            [
                HeatPlanSlot(SeedMethod.INPUT, 1),
                HeatPlanSlot(SeedMethod.INPUT, 8),
                HeatPlanSlot(SeedMethod.INPUT, 9),
                HeatPlanSlot(SeedMethod.INPUT, 16)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 5',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 1)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 6',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 1)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 7',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 3)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 8',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 3)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 9',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 5)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 10',
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 7)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 11: ' + RHAPI.__('Winners Bracket Semifinal'),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 7)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 12: ' + RHAPI.__('Winners Bracket Semifinal'),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 9),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 9)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 13: ' + RHAPI.__('Consolation Bracket Semifinal'),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 10)
            ]
        ),
        HeatPlan(
            RHAPI.__('Race') + ' 14: ' + RHAPI.__('Winners Bracket Final'),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 12)
            ]
        )
    ]

def bracket_1e_std(RHAPI, generate_args):
    if 'standard' not in generate_args:
        return False

    if generate_args['standard'] == 'fai16':
        heats = bracket_1e_16_fai(RHAPI)
    elif generate_args['standard'] == 'fai32':
        heats = bracket_1e_32_fai(RHAPI)
    elif generate_args['standard'] == 'fai64':
        heats = bracket_1e_64_fai(RHAPI)
    else:
        return False

    if 'seed_offset' in generate_args:
        seed_offset = max(int(generate_args['seed_offset']) - 1, 0)
        if seed_offset:
            for heat in heats:
                for slot in heat.slots:
                    if slot.method == SeedMethod.INPUT:
                        slot.seed_rank += seed_offset

    return heats

def bracket_2e_std(RHAPI, generate_args):
    if 'standard' not in generate_args:
        return False

    if generate_args['standard'] == 'fai16':
        heats = bracket_2e_16_fai(RHAPI)
    elif generate_args['standard'] == 'fai32':
        heats = bracket_2e_32_fai(RHAPI)
    elif generate_args['standard'] == 'fai64':
        heats = bracket_2e_64_fai(RHAPI)
    elif generate_args['standard'] == 'multigp16':
        return bracket_2e_16_multigp(RHAPI)
    else:
        return False

    if 'seed_offset' in generate_args:
        seed_offset = max(int(generate_args['seed_offset']) - 1, 0)
        if seed_offset:
            for heat in heats:
                for slot in heat.slots:
                    if slot.method == SeedMethod.INPUT:
                        slot.seed_rank += seed_offset

    return heats

def discover(*_args, **_kwargs):
    # returns array of exporters with default arguments
    return [
        HeatGenerator(
            'bracket_1e_std',
            'Regulation bracket, single elimination',
            bracket_1e_std,
            None,
            [
                UIField('standard', "Spec", UIFieldType.SELECT, options=[
                        UIFieldSelectOption('fai16', "FAI, 4-up, 16-pilot"),
                        UIFieldSelectOption('fai32', "FAI, 4-up, 32-pilot"),
                        UIFieldSelectOption('fai64', "FAI, 4-up, 64-pilot"),
                    ], value="fai16"),
                UIField('seed_offset', "Seed from rank", UIFieldType.BASIC_INT, value=1),
            ],
        ),
        HeatGenerator(
            'bracket_2e_std',
            'Regulation bracket, double elimination',
            bracket_2e_std,
            None,
            [
                UIField('standard', "Spec", UIFieldType.SELECT, options=[
                        UIFieldSelectOption('fai16', "FAI, 4-up, 16-pilot"),
                        UIFieldSelectOption('fai32', "FAI, 4-up, 32-pilot"),
                        UIFieldSelectOption('fai64', "FAI, 4-up, 64-pilot"),
                        UIFieldSelectOption('multigp16', "MultiGP, 4-up, 16-pilot"),
                    ], value="fai16"),
                UIField('seed_offset', "Seed from rank", UIFieldType.BASIC_INT, value=1),
            ],
        ),
    ]
