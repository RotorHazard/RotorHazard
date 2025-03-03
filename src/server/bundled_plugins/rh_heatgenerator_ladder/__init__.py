''' Heat generator for ladders '''

import logging
import RHUtils
import random
from eventmanager import Evt
from HeatGenerator import HeatGenerator, HeatPlan, HeatPlanSlot, SeedMethod
from RHUI import UIField, UIFieldType, UIFieldSelectOption

logger = logging.getLogger(__name__)

def getTotalPilots(rhapi, generate_args):
    input_class_id = generate_args.get('input_class')

    if input_class_id:
        if generate_args.get('total_pilots'):
            total_pilots = int(generate_args['total_pilots'])
        else:
            race_class = rhapi.db.raceclass_by_id(input_class_id)
            class_results = rhapi.db.raceclass_results(race_class)
            if class_results and type(class_results) == dict:
                # fill from available results
                total_pilots = len(class_results['by_race_time'])
            else:
                # fall back to all pilots
                total_pilots = len(rhapi.db.pilots)
    else:
        # use total number of pilots
        total_pilots = len(rhapi.db.pilots)

    return total_pilots

def generateLadder(rhapi, generate_args=None):
    available_seats = generate_args.get('available_seats')
    suffix = rhapi.__(generate_args.get('suffix', 'Main'))

    if generate_args.get('qualifiers_per_heat') is not None and generate_args.get('advances_per_heat') is not None:
        qualifiers_per_heat = int(generate_args['qualifiers_per_heat'])
        advances_per_heat = int(generate_args['advances_per_heat'])
    elif generate_args.get('advances_per_heat') is not None:
        advances_per_heat = int(generate_args['advances_per_heat'])
        qualifiers_per_heat = available_seats - advances_per_heat
    elif generate_args.get('qualifiers_per_heat') is not None:
        qualifiers_per_heat = int(generate_args['qualifiers_per_heat'])
        advances_per_heat = available_seats - qualifiers_per_heat
    else:
        qualifiers_per_heat = available_seats - 1
        advances_per_heat = 1

    if qualifiers_per_heat < 1 or advances_per_heat < 1:
        if not ('advances_per_heat' in generate_args and generate_args['advances_per_heat'] == 0):
            logger.warning("Unable to seed ladder: provided qualifiers and advances must be > 0")
            return False

    total_pilots = getTotalPilots(rhapi, generate_args)

    if total_pilots == 0:
        logger.warning("Unable to seed ladder: no pilots available")
        return False

    letters = rhapi.__('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    heats = []

    if 'seed_offset' in generate_args:
        seed_offset = max(int(generate_args['seed_offset']) - 1, 0)
    else:
        seed_offset = 0

    unseeded_pilots = list(range(seed_offset, total_pilots+seed_offset))
    heat_pilots = 0

    while len(unseeded_pilots):
        if heat_pilots == 0:
            heat = HeatPlan(
                letters[len(heats)] + ' ' + suffix,
                []
            )

        if heat_pilots < qualifiers_per_heat:
            # slot qualifiers
            heat.slots.append(HeatPlanSlot(SeedMethod.INPUT, unseeded_pilots.pop(0) + 1))

            heat_pilots += 1
        else:
            if len(unseeded_pilots) <= advances_per_heat:
                # slot remainder as qualifiers
                for seed in unseeded_pilots:
                    heat.slots.append(HeatPlanSlot(SeedMethod.INPUT, seed + 1))

                unseeded_pilots = [] # empty after using

            else:
                # slot advances
                for adv_idx in range(advances_per_heat):
                    heat.slots.append(HeatPlanSlot(SeedMethod.HEAT_INDEX, adv_idx + 1, -len(heats) - 2))

            heats = [heat, *heats] # insert at front
            heat_pilots = 0

    if heat_pilots: # insert final heat
        heats = [heat, *heats]

    return heats

def generateBalancedHeats(rhapi, generate_args=None):
    available_seats = generate_args.get('available_seats')
    suffix = rhapi.__(generate_args.get('suffix', 'Qualifier'))

    if generate_args.get('qualifiers_per_heat'):
        qualifiers_per_heat = int(generate_args['qualifiers_per_heat'])
    else:
        qualifiers_per_heat = available_seats

    if qualifiers_per_heat < 1:
        logger.warning("Unable to seed ladder: provided qualifiers must be > 1")
        return False

    total_pilots = getTotalPilots(rhapi, generate_args)

    if total_pilots == 0:
        logger.warning("Unable to seed heats: no pilots available")
        return False

    total_heats = (total_pilots // qualifiers_per_heat)
    if total_pilots % qualifiers_per_heat:
        total_heats += 1

    letters = rhapi.__('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    heats = []

    for idx in range(total_heats):
        if idx < len(letters):
            designator = letters[idx]
        else:
            n = idx // len(letters)
            designator = f"{n}{letters[idx % len(letters)]}"

        heats.append(HeatPlan(designator + ' ' + suffix, []))

    if 'seed_offset' in generate_args:
        seed_offset = max(int(generate_args['seed_offset']) - 1, 0)
    else:
        seed_offset = 0

    unseeded_pilots = list(range(seed_offset, total_pilots+seed_offset))
    random.shuffle(unseeded_pilots)

    heatNum = 0
    while len(unseeded_pilots):
        if heatNum >= len(heats):
            heatNum = 0

        heats[heatNum].slots.append(HeatPlanSlot(SeedMethod.INPUT, unseeded_pilots.pop(0) + 1))
        heatNum += 1

    return heats

def register_handlers(args):
    for generator in [
        HeatGenerator(
            "Ranked fill",
            generateLadder,
            {
                'advances_per_heat': 0,
            },
            [
                UIField('qualifiers_per_heat', "Maximum pilots per heat", UIFieldType.BASIC_INT, placeholder="Auto"),
                UIField('total_pilots', "Maxiumum pilots in class", UIFieldType.BASIC_INT, placeholder="Auto", desc="Used only with input class"),
                UIField('seed_offset', "Seed from rank", UIFieldType.BASIC_INT, value=1),
                UIField('suffix', "Heat title suffix", UIFieldType.TEXT, placeholder="Main", value="Main"),
            ],
        ),
        HeatGenerator(
            "Balanced random fill",
            generateBalancedHeats,
            None,
            [
                UIField('qualifiers_per_heat', "Maximum pilots per heat", UIFieldType.BASIC_INT, placeholder="Auto"),
                UIField('total_pilots', "Maxiumum pilots in class", UIFieldType.BASIC_INT, placeholder="Auto", desc="Used only with input class"),
                UIField('seed_offset', "Seed from rank", UIFieldType.BASIC_INT, value=1),
                UIField('suffix', "Heat title suffix", UIFieldType.TEXT, placeholder="Qualifier", value="Qualifier"),
            ]
        ),
        HeatGenerator(
            "Ladder",
            generateLadder,
            None,
            [
                UIField('advances_per_heat', "Advances per heat", UIFieldType.BASIC_INT, placeholder="Auto"),
                UIField('qualifiers_per_heat', "Seeded slots per heat", UIFieldType.BASIC_INT, placeholder="Auto"),
                UIField('total_pilots', "Pilots in class", UIFieldType.BASIC_INT, placeholder="Auto", desc="Used only with input class"),
                UIField('seed_offset', "Seed from rank", UIFieldType.BASIC_INT, value=1),
                UIField('suffix', "Heat title suffix", UIFieldType.TEXT, placeholder="Main", value="Main"),
            ]
        ),
    ]:
        args['register_fn'](generator)

def initialize(rhapi):
    rhapi.events.on(Evt.HEAT_GENERATOR_INITIALIZE, register_handlers)

