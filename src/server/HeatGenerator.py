#
# Heat generation handlers
#

import logging
import random
from Database import ProgramMethod

logger = logging.getLogger(__name__)

class HeatGeneratorManager():
    generators = {}

    def __init__(self, RHData, Results, PageCache, Language, Events):
        self._RHData = RHData
        self._Results = Results
        self._PageCache = PageCache
        self._Language = Language
        self.Events = Events

        self.Events.trigger('HeatGenerator_Initialize', {
            'registerFn': self.registerGenerator
            })

    def registerGenerator(self, generator):
        if hasattr(generator, 'name'):
            if generator.name in self.generators:
                logger.warning('Overwriting data generator "{0}"'.format(generator.name))

            self.generators[generator.name] = generator
        else:
            logger.warning('Invalid generator')

    def hasGenerator(self, generator_id):
        return generator_id in self.generators

    def getGenerators(self):
        return self.generators

    def generate(self, generator_id, generate_args=None):
        generated_heats = self.generators[generator_id].generate(self._RHData, self._Results, self._PageCache, generate_args)
        if generated_heats:
            self.apply(generated_heats, generate_args)
            return True
        else:
            logger.error('Generation stage failed or refused to produce output: see log')
            return False

    def apply(self, generated_heats, generate_args):
        pilot_pool = []
        filled_pool = False
        input_class = generate_args.get('input_class')  
        output_class = generate_args.get('output_class')

        if output_class is None:
            new_class = self._RHData.add_raceClass()
            output_class = new_class.id

        heat_id_mapping = []
        for heat_plan in generated_heats:
            new_heat = self._RHData.add_heat(init={
                'class_id': output_class,
                'note': heat_plan['name'],
                'auto_frequency': True,
                'defaultMethod': ProgramMethod.NONE
                })
            heat_id_mapping.append(new_heat.id)

        for h_idx, heat_plan in enumerate(generated_heats):
            heat_alterations = []
            heat_slots = self._RHData.get_heatNodes_by_heat(heat_id_mapping[h_idx])

            if len(heat_slots) < len(heat_plan['slots']):
                logger.warning('Not enough actual slots for requested heat generation')

            for s_idx, heat_slot in enumerate(heat_slots):
                if s_idx < len(heat_plan['slots']):
                    seed_slot = heat_plan['slots'][s_idx]
                    data = {
                        'heat': heat_id_mapping[h_idx],
                        'slot_id': heat_slot.id,
                        'seed_rank': seed_slot['seed_rank'],
                        }
                    if seed_slot['method'] == 'input':
                        if input_class:
                            data['method'] = ProgramMethod.CLASS_RESULT
                            data['seed_class_id'] = input_class
                        else:
                            # randomly seed 
                            if filled_pool == False:
                                for pilot in self._RHData.get_pilots():
                                    pilot_pool.append(pilot.id)

                                random.shuffle(pilot_pool)
                                filled_pool = True

                            if len(pilot_pool):
                                data['method'] = ProgramMethod.ASSIGN
                                data['pilot'] = pilot_pool.pop()
                            else:
                                logger.info('Unable to seed pilot: no available pilots left to seed')
                                data['method'] = ProgramMethod.NONE

                    elif seed_slot['method'] == ProgramMethod.HEAT_RESULT:
                        data['method'] = ProgramMethod.HEAT_RESULT
                        data['seed_heat_id'] = heat_id_mapping[seed_slot['seed_heat_id']]
                    else:
                        logger.error('Not a supported seed method: {}'.format(seed_slot['method']))
                        return False

                heat_alterations.append(data)

            self._RHData.alter_heatNodes_fast(heat_alterations)

        if filled_pool and len(pilot_pool):
            logger.info("{} unseeded pilots remaining in pool".format(len(pilot_pool)))

class HeatGenerator():
    def __init__(self, name, label, generatorFn, defaultArgs=None):
        self.name = name
        self.label = label
        self.generator = generatorFn
        self.defaultArgs = defaultArgs

    def generate(self, RHData, Results, PageCache, generate_args=None):
        generate_args = {**(self.defaultArgs if self.defaultArgs else {}), **(generate_args if generate_args else {})}

        return self.generator(RHData, Results, PageCache, generate_args)
