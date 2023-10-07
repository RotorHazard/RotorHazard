#
# Heat generation handlers
#

from typing import List
from RHUI import UIField
from eventmanager import Evt
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import random
import RHUtils
from RHUtils import catchLogExceptionsWrapper, cleanVarName
from Database import ProgramMethod

logger = logging.getLogger(__name__)

class SeedMethod(Enum):
    INPUT = 0
    HEAT_INDEX = 1

@dataclass
class HeatPlanSlot():
    method: SeedMethod
    seed_rank: int
    seed_index: int = None

@dataclass
class HeatPlan():
    name: str
    slots: List[HeatPlanSlot] = None


class HeatGeneratorManager():
    def __init__(self, racecontext, rhapi, events):
        self._generators = {}

        self._racecontext = racecontext
        self._rhapi = rhapi
        self._events = events

        events.trigger(Evt.HEAT_GENERATOR_INITIALIZE, {
            'register_fn': self.register_generator
            })

    def register_generator(self, generator):
        if isinstance(generator, HeatGenerator):
            if generator.name in self._generators:
                logger.warning('Overwriting data generator "{0}"'.format(generator.name))

            self._generators[generator.name] = generator
        else:
            logger.warning("Invalid generator")

    @property
    def generators(self):
        return self._generators

    def generate(self, generator_id, generate_args=None):
        generated_heats = self._generators[generator_id].generate(self._rhapi, generate_args)
        if generated_heats:
            result = self.apply(generator_id, generated_heats, generate_args)

            if result is not False:
                self._events.trigger(Evt.HEAT_GENERATE, {
                    'generator': generator_id,
                    'generate_args': generate_args,
                    'output_class': result
                    })
            else:
                logger.warning("Failed generating heats: generator returned no data")
            return result
        else:
            logger.error("Generation stage failed or refused to produce output: see log")
            return False

    @catchLogExceptionsWrapper
    def apply(self, generator_id, generated_heats, generate_args):
        pilot_pool = []
        filled_pool = False
        input_class = generate_args.get('input_class')  
        output_class = generate_args.get('output_class')

        if output_class is None:
            new_class = self._racecontext.rhdata.add_raceClass()
            all_class_names = [race_class.name for race_class in self._racecontext.rhdata.get_raceClasses()]
            new_class.name = RHUtils.uniqueName(self._generators[generator_id].label, all_class_names)
            output_class = new_class.id

        heat_id_mapping = []
        for heat_plan in generated_heats:
            new_heat = self._racecontext.rhdata.add_heat(init={
                'class_id': output_class,
                'name': heat_plan.name,
                'auto_frequency': True,
                'defaultMethod': ProgramMethod.NONE
                })
            heat_id_mapping.append(new_heat.id)

        for h_idx, heat_plan in enumerate(generated_heats):
            heat_alterations = []
            heat_slots = self._racecontext.rhdata.get_heatNodes_by_heat(heat_id_mapping[h_idx])

            if len(heat_slots) < len(heat_plan.slots):
                logger.warning("Not enough actual slots for requested heat generation")

            for s_idx, heat_slot in enumerate(heat_slots):
                if s_idx < len(heat_plan.slots):
                    seed_slot = heat_plan.slots[s_idx]
                    data = {
                        'heat': heat_id_mapping[h_idx],
                        'slot_id': heat_slot.id,
                        'seed_rank': seed_slot.seed_rank,
                        }
                    if seed_slot.method == SeedMethod.INPUT:
                        if input_class:
                            data['method'] = ProgramMethod.CLASS_RESULT
                            data['seed_class_id'] = input_class
                        else:
                            # randomly seed 
                            if filled_pool == False:
                                for pilot in self._racecontext.rhdata.get_pilots():
                                    pilot_pool.append(pilot.id)

                                random.shuffle(pilot_pool)
                                filled_pool = True

                            if len(pilot_pool):
                                data['method'] = ProgramMethod.ASSIGN
                                data['pilot'] = pilot_pool.pop()
                            else:
                                logger.info("Unable to seed pilot: no available pilots left to seed")
                                data['method'] = ProgramMethod.NONE

                    elif seed_slot.method == SeedMethod.HEAT_INDEX:
                        data['method'] = ProgramMethod.HEAT_RESULT
                        data['seed_heat_id'] = heat_id_mapping[seed_slot.seed_index]
                    else:
                        logger.error("Not a supported seed method: {}".format(seed_slot.method))
                        return False

                heat_alterations.append(data)

            self._racecontext.rhdata.alter_heatNodes_fast(heat_alterations)

        if filled_pool and len(pilot_pool):
            logger.info("{} unseeded pilots remaining in pool".format(len(pilot_pool)))

        return output_class

class HeatGenerator():
    def __init__(self, label, generator_fn, default_args=None, settings:List[UIField]=None, name=None):
        if name is None:
            self.name = cleanVarName(label)
        else:
            self.name = name

        self.label = label
        self._generator = generator_fn
        self.default_args = default_args
        self.settings = settings

    def generate(self, rhapi, generate_args=None):
        generate_args = {**(self.default_args if self.default_args else {}), **(generate_args if generate_args else {})}
        return self._generator(rhapi, generate_args)

