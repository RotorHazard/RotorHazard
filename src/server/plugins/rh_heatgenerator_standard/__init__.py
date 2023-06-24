'''Standardized heat structures'''
# FAI: https://www.fai.org/sites/default/files/ciam/wcup_drones/sc4_vol_f9_dronesport_22_2022-03-01_0.pdf
# MultiGP: https://docs.google.com/document/d/1jWVjCnoIGdW1j_bklrbg-0D24c3x6YG5m_vmF7faG-U/edit#heading=h.hoxlrr3v86bb

import logging
from eventmanager import Evt
from HeatGenerator import HeatGenerator, HeatPlan, HeatPlanSlot, SeedMethod
from RHUI import UIField, UIFieldType, UIFieldSelectOption

logger = logging.getLogger(__name__)

def bracket_1e_16_fai(rhapi):
    return [
        HeatPlan(
            rhapi.__("Race") + " 1",
            [
                HeatPlanSlot(SeedMethod.INPUT, 1),
                HeatPlanSlot(SeedMethod.INPUT, 8),
                HeatPlanSlot(SeedMethod.INPUT, 9),
                HeatPlanSlot(SeedMethod.INPUT, 16)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 2",
            [
                HeatPlanSlot(SeedMethod.INPUT, 4),
                HeatPlanSlot(SeedMethod.INPUT, 5),
                HeatPlanSlot(SeedMethod.INPUT, 12),
                HeatPlanSlot(SeedMethod.INPUT, 13)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 3",
            [
                HeatPlanSlot(SeedMethod.INPUT, 3),
                HeatPlanSlot(SeedMethod.INPUT, 6),
                HeatPlanSlot(SeedMethod.INPUT, 10),
                HeatPlanSlot(SeedMethod.INPUT, 14)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 4",
            [
                HeatPlanSlot(SeedMethod.INPUT, 2),
                HeatPlanSlot(SeedMethod.INPUT, 7),
                HeatPlanSlot(SeedMethod.INPUT, 11),
                HeatPlanSlot(SeedMethod.INPUT, 15)
            ]
        ),
        HeatPlan(
            rhapi.__("Semifinal") + " 1",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 1)
            ]
        ),
        HeatPlan(
            rhapi.__("Semifinal") + " 2",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 3)
            ]
        ),
        HeatPlan(
            rhapi.__("Small Final"),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 5)
            ]
        ),
        HeatPlan(
            rhapi.__("Final"),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 5)
            ]
        )
    ]

def bracket_1e_32_fai(rhapi):
    return [
        HeatPlan(
            rhapi.__("Race") + " 1 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 1),
                HeatPlanSlot(SeedMethod.INPUT, 16),
                HeatPlanSlot(SeedMethod.INPUT, 24),
                HeatPlanSlot(SeedMethod.INPUT, 32)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 2 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 8),
                HeatPlanSlot(SeedMethod.INPUT, 9),
                HeatPlanSlot(SeedMethod.INPUT, 17),
                HeatPlanSlot(SeedMethod.INPUT, 25)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 3 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 6),
                HeatPlanSlot(SeedMethod.INPUT, 11),
                HeatPlanSlot(SeedMethod.INPUT, 19),
                HeatPlanSlot(SeedMethod.INPUT, 27)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 4 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 4),
                HeatPlanSlot(SeedMethod.INPUT, 13),
                HeatPlanSlot(SeedMethod.INPUT, 21),
                HeatPlanSlot(SeedMethod.INPUT, 29)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 5 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 3),
                HeatPlanSlot(SeedMethod.INPUT, 14),
                HeatPlanSlot(SeedMethod.INPUT, 22),
                HeatPlanSlot(SeedMethod.INPUT, 30)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 6 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 5),
                HeatPlanSlot(SeedMethod.INPUT, 12),
                HeatPlanSlot(SeedMethod.INPUT, 20),
                HeatPlanSlot(SeedMethod.INPUT, 28)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 7 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 7),
                HeatPlanSlot(SeedMethod.INPUT, 10),
                HeatPlanSlot(SeedMethod.INPUT, 18),
                HeatPlanSlot(SeedMethod.INPUT, 26)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 8 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 2),
                HeatPlanSlot(SeedMethod.INPUT, 15),
                HeatPlanSlot(SeedMethod.INPUT, 23),
                HeatPlanSlot(SeedMethod.INPUT, 31)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 9 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 1)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 10 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 3)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 11 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 5)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 12 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 7)
            ]
        ),
        HeatPlan(
            rhapi.__("Semifinal") + " 1",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 9),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 9)
            ]
        ),
        HeatPlan(
            rhapi.__("Semifinal") + " 2",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 11)
            ]
        ),
        HeatPlan(
            rhapi.__("Small Final"),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 13),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 13)
            ]
        ),
        HeatPlan(
            rhapi.__("Final"),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 13),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 13)
            ]
        )
    ]

def bracket_1e_64_fai(rhapi):
    return [
        HeatPlan(
            rhapi.__("Race") + " 1 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 1),
                HeatPlanSlot(SeedMethod.INPUT, 32),
                HeatPlanSlot(SeedMethod.INPUT, 48),
                HeatPlanSlot(SeedMethod.INPUT, 64)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 2 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 16),
                HeatPlanSlot(SeedMethod.INPUT, 17),
                HeatPlanSlot(SeedMethod.INPUT, 33),
                HeatPlanSlot(SeedMethod.INPUT, 49)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 3 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 8),
                HeatPlanSlot(SeedMethod.INPUT, 25),
                HeatPlanSlot(SeedMethod.INPUT, 41),
                HeatPlanSlot(SeedMethod.INPUT, 57)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 4 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 14),
                HeatPlanSlot(SeedMethod.INPUT, 19),
                HeatPlanSlot(SeedMethod.INPUT, 35),
                HeatPlanSlot(SeedMethod.INPUT, 51)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 5 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 4),
                HeatPlanSlot(SeedMethod.INPUT, 29),
                HeatPlanSlot(SeedMethod.INPUT, 45),
                HeatPlanSlot(SeedMethod.INPUT, 61)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 6 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 12),
                HeatPlanSlot(SeedMethod.INPUT, 21),
                HeatPlanSlot(SeedMethod.INPUT, 37),
                HeatPlanSlot(SeedMethod.INPUT, 53)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 7 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 6),
                HeatPlanSlot(SeedMethod.INPUT, 27),
                HeatPlanSlot(SeedMethod.INPUT, 43),
                HeatPlanSlot(SeedMethod.INPUT, 59)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 8 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 10),
                HeatPlanSlot(SeedMethod.INPUT, 23),
                HeatPlanSlot(SeedMethod.INPUT, 39),
                HeatPlanSlot(SeedMethod.INPUT, 55)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 9 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 9),
                HeatPlanSlot(SeedMethod.INPUT, 24),
                HeatPlanSlot(SeedMethod.INPUT, 40),
                HeatPlanSlot(SeedMethod.INPUT, 56)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 10 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 5),
                HeatPlanSlot(SeedMethod.INPUT, 28),
                HeatPlanSlot(SeedMethod.INPUT, 44),
                HeatPlanSlot(SeedMethod.INPUT, 60)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 11 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 11),
                HeatPlanSlot(SeedMethod.INPUT, 22),
                HeatPlanSlot(SeedMethod.INPUT, 38),
                HeatPlanSlot(SeedMethod.INPUT, 54)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 12 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 3),
                HeatPlanSlot(SeedMethod.INPUT, 30),
                HeatPlanSlot(SeedMethod.INPUT, 46),
                HeatPlanSlot(SeedMethod.INPUT, 62)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 13 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 13),
                HeatPlanSlot(SeedMethod.INPUT, 20),
                HeatPlanSlot(SeedMethod.INPUT, 36),
                HeatPlanSlot(SeedMethod.INPUT, 52)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 14 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 7),
                HeatPlanSlot(SeedMethod.INPUT, 26),
                HeatPlanSlot(SeedMethod.INPUT, 42),
                HeatPlanSlot(SeedMethod.INPUT, 58)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 15 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 15),
                HeatPlanSlot(SeedMethod.INPUT, 18),
                HeatPlanSlot(SeedMethod.INPUT, 34),
                HeatPlanSlot(SeedMethod.INPUT, 50)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 16 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 2),
                HeatPlanSlot(SeedMethod.INPUT, 31),
                HeatPlanSlot(SeedMethod.INPUT, 47),
                HeatPlanSlot(SeedMethod.INPUT, 63)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 17 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 1)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 18 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 3)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 19 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 5)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 20 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 7)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 21 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 9),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 9)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 22 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 11)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 23 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 13),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 13)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 24 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 14),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 14),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 15),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 15)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 25 (E3)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 16),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 16),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 17),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 17)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 26 (E3)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 18),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 18),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 19),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 19)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 27 (E3)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 20),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 20),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 21),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 21)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 28 (E3)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 22),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 22),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 23),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 23)
            ]
        ),
        HeatPlan(
            rhapi.__("Semifinal 1"),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 24),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 24),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 25),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 25)
            ]
        ),
        HeatPlan(
            rhapi.__("Semifinal 2"),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 26),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 26),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 27),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 27)
            ]
        ),
        HeatPlan(
            rhapi.__("Small Final"),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 28),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 28),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 29),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 29)
            ]
        ),
        HeatPlan(
            rhapi.__("Final"),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 28),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 28),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 29),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 29)
            ]
        )
    ]

def bracket_2e_16_fai(rhapi):
    return [
       HeatPlan(
            rhapi.__("Race") + " 1",
            [
                HeatPlanSlot(SeedMethod.INPUT, 1),
                HeatPlanSlot(SeedMethod.INPUT, 8),
                HeatPlanSlot(SeedMethod.INPUT, 9),
                HeatPlanSlot(SeedMethod.INPUT, 16)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 2",
            [
                HeatPlanSlot(SeedMethod.INPUT, 4),
                HeatPlanSlot(SeedMethod.INPUT, 5),
                HeatPlanSlot(SeedMethod.INPUT, 12),
                HeatPlanSlot(SeedMethod.INPUT, 13)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 3",
            [
                HeatPlanSlot(SeedMethod.INPUT, 3),
                HeatPlanSlot(SeedMethod.INPUT, 6),
                HeatPlanSlot(SeedMethod.INPUT, 10),
                HeatPlanSlot(SeedMethod.INPUT, 14)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 4",
            [
                HeatPlanSlot(SeedMethod.INPUT, 2),
                HeatPlanSlot(SeedMethod.INPUT, 7),
                HeatPlanSlot(SeedMethod.INPUT, 11),
                HeatPlanSlot(SeedMethod.INPUT, 15)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 5",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 3)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 6",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 2)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 7",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 1)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 8",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 3)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 9",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 6)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 10",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 7)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 11",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 9),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 9)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 12",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 7)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 13",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 11)
            ]
        ),
        HeatPlan(
            rhapi.__("Final"),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 12)
            ]
        )
    ]

def bracket_2e_32_fai(rhapi):
    return [
        HeatPlan(
            rhapi.__("Race") + " 1 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 1),
                HeatPlanSlot(SeedMethod.INPUT, 16),
                HeatPlanSlot(SeedMethod.INPUT, 24),
                HeatPlanSlot(SeedMethod.INPUT, 32)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 2 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 8),
                HeatPlanSlot(SeedMethod.INPUT, 9),
                HeatPlanSlot(SeedMethod.INPUT, 17),
                HeatPlanSlot(SeedMethod.INPUT, 25)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 3 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 6),
                HeatPlanSlot(SeedMethod.INPUT, 11),
                HeatPlanSlot(SeedMethod.INPUT, 19),
                HeatPlanSlot(SeedMethod.INPUT, 27)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 4 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 4),
                HeatPlanSlot(SeedMethod.INPUT, 13),
                HeatPlanSlot(SeedMethod.INPUT, 21),
                HeatPlanSlot(SeedMethod.INPUT, 29)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 5 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 3),
                HeatPlanSlot(SeedMethod.INPUT, 14),
                HeatPlanSlot(SeedMethod.INPUT, 22),
                HeatPlanSlot(SeedMethod.INPUT, 30)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 6 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 5),
                HeatPlanSlot(SeedMethod.INPUT, 12),
                HeatPlanSlot(SeedMethod.INPUT, 20),
                HeatPlanSlot(SeedMethod.INPUT, 28)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 7 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 7),
                HeatPlanSlot(SeedMethod.INPUT, 10),
                HeatPlanSlot(SeedMethod.INPUT, 18),
                HeatPlanSlot(SeedMethod.INPUT, 26)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 8 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 2),
                HeatPlanSlot(SeedMethod.INPUT, 15),
                HeatPlanSlot(SeedMethod.INPUT, 23),
                HeatPlanSlot(SeedMethod.INPUT, 31)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 9 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 1)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 10 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 3)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 11 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 5)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 12 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 7)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 13 (DE1)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 3)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 14 (DE1)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 7)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 15 (DE1)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 2)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 16 (DE1)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 6)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 17 (DE2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 14),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 15),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 9)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 18 (DE2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 13),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 11)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 19 (DE2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 9),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 15),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 14),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 8)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 20 (DE2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 13),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 10)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 21 (DE3)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 18),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 16),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 17),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 19)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 22 (DE3)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 16),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 18),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 19),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 17)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 23 (E3)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 9),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 9)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 24 (E3)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 11)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 25 (DE4)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 22),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 20),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 21),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 23)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 26 (DE4)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 23),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 21),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 20),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 22)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 27 (DE5)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 24),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 24),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 25),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 25)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 28 (E4)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 22),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 22),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 23),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 23)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 29 (DE6)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 27),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 26),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 26),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 27)
            ]
        ),
        HeatPlan(
            rhapi.__("Final"),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 28),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 27),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 27),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 28)
            ]
        )
    ]

def bracket_2e_64_fai(rhapi):
    return [
        HeatPlan(
            rhapi.__("Race") + " 1 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 1),
                HeatPlanSlot(SeedMethod.INPUT, 32),
                HeatPlanSlot(SeedMethod.INPUT, 48),
                HeatPlanSlot(SeedMethod.INPUT, 64)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 2 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 16),
                HeatPlanSlot(SeedMethod.INPUT, 17),
                HeatPlanSlot(SeedMethod.INPUT, 33),
                HeatPlanSlot(SeedMethod.INPUT, 49)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 3 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 8),
                HeatPlanSlot(SeedMethod.INPUT, 25),
                HeatPlanSlot(SeedMethod.INPUT, 41),
                HeatPlanSlot(SeedMethod.INPUT, 57)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 4 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 14),
                HeatPlanSlot(SeedMethod.INPUT, 19),
                HeatPlanSlot(SeedMethod.INPUT, 35),
                HeatPlanSlot(SeedMethod.INPUT, 51)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 5 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 4),
                HeatPlanSlot(SeedMethod.INPUT, 29),
                HeatPlanSlot(SeedMethod.INPUT, 45),
                HeatPlanSlot(SeedMethod.INPUT, 61)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 6 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 12),
                HeatPlanSlot(SeedMethod.INPUT, 21),
                HeatPlanSlot(SeedMethod.INPUT, 37),
                HeatPlanSlot(SeedMethod.INPUT, 53)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 7 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 6),
                HeatPlanSlot(SeedMethod.INPUT, 27),
                HeatPlanSlot(SeedMethod.INPUT, 43),
                HeatPlanSlot(SeedMethod.INPUT, 59)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 8 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 10),
                HeatPlanSlot(SeedMethod.INPUT, 23),
                HeatPlanSlot(SeedMethod.INPUT, 39),
                HeatPlanSlot(SeedMethod.INPUT, 55)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 9 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 9),
                HeatPlanSlot(SeedMethod.INPUT, 24),
                HeatPlanSlot(SeedMethod.INPUT, 40),
                HeatPlanSlot(SeedMethod.INPUT, 56)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 10 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 5),
                HeatPlanSlot(SeedMethod.INPUT, 28),
                HeatPlanSlot(SeedMethod.INPUT, 44),
                HeatPlanSlot(SeedMethod.INPUT, 60)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 11 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 11),
                HeatPlanSlot(SeedMethod.INPUT, 22),
                HeatPlanSlot(SeedMethod.INPUT, 38),
                HeatPlanSlot(SeedMethod.INPUT, 54)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 12 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 3),
                HeatPlanSlot(SeedMethod.INPUT, 30),
                HeatPlanSlot(SeedMethod.INPUT, 46),
                HeatPlanSlot(SeedMethod.INPUT, 62)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 13 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 13),
                HeatPlanSlot(SeedMethod.INPUT, 20),
                HeatPlanSlot(SeedMethod.INPUT, 36),
                HeatPlanSlot(SeedMethod.INPUT, 52)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 14 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 7),
                HeatPlanSlot(SeedMethod.INPUT, 26),
                HeatPlanSlot(SeedMethod.INPUT, 42),
                HeatPlanSlot(SeedMethod.INPUT, 58)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 15 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 15),
                HeatPlanSlot(SeedMethod.INPUT, 18),
                HeatPlanSlot(SeedMethod.INPUT, 34),
                HeatPlanSlot(SeedMethod.INPUT, 50)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 16 (E1)",
            [
                HeatPlanSlot(SeedMethod.INPUT, 2),
                HeatPlanSlot(SeedMethod.INPUT, 31),
                HeatPlanSlot(SeedMethod.INPUT, 47),
                HeatPlanSlot(SeedMethod.INPUT, 63)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 17 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 1)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 18 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 3)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 19 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 5)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 20 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 7)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 21 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 9),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 9)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 22 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 11)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 23 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 13),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 13)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 24 (E2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 14),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 14),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 15),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 15)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 25 (DE1)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 3)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 26 (DE1)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 7)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 27 (DE1)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 2)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 28 (DE1)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 6)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 29 (DE1)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 9),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 11)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 30 (DE1)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 13),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 14),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 15)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 31 (DE1)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 9),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 10)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 32 (DE1)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 13),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 15),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 14)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 33 (DE2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 16),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 30),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 31),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 17)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 34 (DE2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 18),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 28),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 29),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 19)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 35 (DE2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 17),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 31),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 30),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 16)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 36 (DE2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 19),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 29),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 28),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 18)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 37 (DE2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 20),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 25),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 24),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 21)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 38 (DE2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 22),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 27),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 26),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 23)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 39 (DE2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 21),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 24),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 25),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 20)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 40 (DE2)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 23),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 26),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 27),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 22)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 41 (DE3)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 34),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 32),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 33),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 35)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 42 (DE3)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 32),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 34),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 35),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 33)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 43 (DE3)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 38),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 36),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 37),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 39)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 44 (DE3)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 36),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 38),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 39),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 37)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 45 (E3)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 16),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 16),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 17),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 17)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 46 (E3)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 18),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 18),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 19),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 19)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 47 (E3)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 20),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 20),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 21),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 21)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 48 (E3)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 22),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 22),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 23),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 23)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 49 (DE4)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 44),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 42),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 43),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 45)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 50 (DE4)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 46),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 40),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 41),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 47)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 51 (DE4)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 45),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 43),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 42),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 44)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 52 (DE4)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 47),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 41),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 40),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 46)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 53 (DE5)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 50),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 48),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 49),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 51)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 54 (DE5)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 48),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 50),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 51),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 49)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 55 (E4)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 44),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 44),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 45),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 45)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 56 (E4)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 46),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 46),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 47),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 47)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 57 (DE6)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 54),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 52),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 53),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 55)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 58 (DE6)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 55),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 53),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 52),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 54)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 59 (DE7)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 56),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 56),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 57),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 57)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 60 (E5)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 54),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 54),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 55),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 55)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 61 (DE7)",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 59),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 58),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 58),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 59)
            ]
        ),
        HeatPlan(
            rhapi.__("Final"),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 60),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 59),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 59),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 60)
            ]
        )
    ]

def bracket_2e_16_multigp(rhapi):
    return [
        HeatPlan(
            rhapi.__("Race") + " 1",
            [
                HeatPlanSlot(SeedMethod.INPUT, 3),
                HeatPlanSlot(SeedMethod.INPUT, 6),
                HeatPlanSlot(SeedMethod.INPUT, 11),
                HeatPlanSlot(SeedMethod.INPUT, 14)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 2",
            [
                HeatPlanSlot(SeedMethod.INPUT, 2),
                HeatPlanSlot(SeedMethod.INPUT, 7),
                HeatPlanSlot(SeedMethod.INPUT, 10),
                HeatPlanSlot(SeedMethod.INPUT, 15)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 3",
            [
                HeatPlanSlot(SeedMethod.INPUT, 4),
                HeatPlanSlot(SeedMethod.INPUT, 5),
                HeatPlanSlot(SeedMethod.INPUT, 12),
                HeatPlanSlot(SeedMethod.INPUT, 13)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 4",
            [
                HeatPlanSlot(SeedMethod.INPUT, 1),
                HeatPlanSlot(SeedMethod.INPUT, 8),
                HeatPlanSlot(SeedMethod.INPUT, 9),
                HeatPlanSlot(SeedMethod.INPUT, 16)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 5",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 1)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 6",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 0),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 1),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 1)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 7",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 3)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 8",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 2),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 3),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 3)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 9",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 4),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 5)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 10",
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 6),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 7)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 11: " + rhapi.__("Winners Bracket Semifinal"),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 5),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 7),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 7)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 12: " + rhapi.__("Winners Bracket Semifinal"),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 8),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 9),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 9)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 13: " + rhapi.__("Consolation Bracket Semifinal"),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 11),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 3, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 4, 10)
            ]
        ),
        HeatPlan(
            rhapi.__("Race") + " 14: " + rhapi.__("Winners Bracket Final"),
            [
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 10),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 1, 12),
                HeatPlanSlot(SeedMethod.HEAT_INDEX, 2, 12)
            ]
        )
    ]

def bracket_1e_std(rhapi, generate_args):
    if 'standard' not in generate_args:
        return False

    if generate_args['standard'] == 'fai16':
        heats = bracket_1e_16_fai(rhapi)
    elif generate_args['standard'] == 'fai32':
        heats = bracket_1e_32_fai(rhapi)
    elif generate_args['standard'] == 'fai64':
        heats = bracket_1e_64_fai(rhapi)
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

def bracket_2e_std(rhapi, generate_args):
    if 'standard' not in generate_args:
        return False

    if generate_args['standard'] == 'fai16':
        heats = bracket_2e_16_fai(rhapi)
    elif generate_args['standard'] == 'fai32':
        heats = bracket_2e_32_fai(rhapi)
    elif generate_args['standard'] == 'fai64':
        heats = bracket_2e_64_fai(rhapi)
    elif generate_args['standard'] == 'multigp16':
        return bracket_2e_16_multigp(rhapi)
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

def register_handlers(args):
    for generator in [
        HeatGenerator(
            'bracket_1e_std',
            "Regulation bracket, single elimination",
            bracket_1e_std,
            None,
            [
                UIField('standard', "Spec", UIFieldType.SELECT, options=[
                        UIFieldSelectOption('fai16', "FAI, 4-up, 16-pilot"),
                        UIFieldSelectOption('fai32', "FAI, 4-up, 32-pilot"),
                        UIFieldSelectOption('fai64', "FAI, 4-up, 64-pilot"),
                    ], value='fai16'),
                UIField('seed_offset', "Seed from rank", UIFieldType.BASIC_INT, value=1),
            ],
        ),
        HeatGenerator(
            'bracket_2e_std',
            "Regulation bracket, double elimination",
            bracket_2e_std,
            None,
            [
                UIField('standard', "Spec", UIFieldType.SELECT, options=[
                        UIFieldSelectOption('fai16', "FAI, 4-up, 16-pilot"),
                        UIFieldSelectOption('fai32', "FAI, 4-up, 32-pilot"),
                        UIFieldSelectOption('fai64', "FAI, 4-up, 64-pilot"),
                        UIFieldSelectOption('multigp16', "MultiGP, 4-up, 16-pilot"),
                    ], value='fai16'),
                UIField('seed_offset', "Seed from rank", UIFieldType.BASIC_INT, value=1),
            ],
        ),
    ]:
        args['register_fn'](generator)

def initialize(**kwargs):
    kwargs['events'].on(Evt.HEAT_GENERATOR_INITIALIZE, 'HeatGenerator_register_standards', register_handlers, {}, 75)

