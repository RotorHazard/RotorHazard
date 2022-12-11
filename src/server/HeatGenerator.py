#
# Heat generation handlers
#

import logging
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
                logger.warning('Overwriting data generator "{0}"'.format(generator['name']))

            self.generators[generator.name] = generator
        else:
            logger.warning('Invalid generator')

    def hasGenerator(self, generator_id):
        if generator_id in self.generators:
            return True
        return False

    def getGenerators(self):
        return self.generators

    def generate(self, generator_id, generate_args=None):
        generated_heats = self.generators[generator_id].generate(self._RHData, self._Results, self._PageCache, self._Language, generate_args)
        if generated_heats:
            self.apply(generated_heats, generate_args)
            return True
        else:
            logger.error('Generation stage failed or refused to produce output') # TODO: provide better context
            return False

    def apply(self, generated_heats, generate_args):
        input_class = generate_args['input_class'] if 'input_class' in generate_args else None 
        output_class = generate_args['output_class'] if 'output_class' in generate_args else None

        if output_class is None:
            new_class = self._RHData.add_raceClass()
            output_class = new_class.id

        heat_id_mapping = {}
        for h_idx, heat_plan in enumerate(generated_heats):
            # TODO: Provide combined heat+slot fn  
            new_heat = self._RHData.add_heat(init={
                'class_id': output_class,
                'note': heat_plan['name'],
                'auto_frequency': True,
                'defaultMethod': ProgramMethod.NONE
                })
            heat_id_mapping[h_idx] = new_heat.id

            heat_slots = self._RHData.get_heatNodes_by_heat(new_heat.id)

            if len(heat_slots) < len(heat_plan['slots']):
                logger.warning('Not enough actual slots for requested heat generation')

            for s_idx, heat_slot in enumerate(heat_slots):
                if s_idx < len(heat_plan['slots']):
                    seed_slot = heat_plan['slots'][s_idx]
                    data = {
                        'heat': new_heat.id,
                        'slot_id': heat_slot.id,
                        'seed_rank': seed_slot['seed_rank'],
                        }
                    if seed_slot['method'] == 'input':
                        if input_class:
                            data['method'] = ProgramMethod.CLASS_RESULT
                            data['seed_class_id'] = input_class
                        else:
                            # random seeding!
                            data['method'] = ProgramMethod.ASSIGN
                            data['pilot'] = None # TODO: Do random seeding
                    elif seed_slot['method'] == ProgramMethod.HEAT_RESULT:
                        data['method'] = ProgramMethod.HEAT_RESULT
                        data['seed_heat_id'] = heat_id_mapping[seed_slot['seed_heat_id']]
                    else:
                        logger.error('Not a supported seed method: {}'.format(seed_slot['method']))
                        return False

                self._RHData.alter_heat(data)

class HeatGenerator():
    def __init__(self, name, label, generatorFn):
        self.name = name
        self.label = label
        self.generator = generatorFn

    def generate(self, RHData, Results, PageCache, Language, generate_args=None):
        return self.generator(RHData, Results, PageCache, Language, generate_args)
