import unittest

from leds import led_handler_strip, led_handler_bitmap, led_handler_character, led_handler_graph
from server.RHRace import RHRace
from interface.MockInterface import MockInterface

class MockPixel:
    def __init__(self, count):
        self.pixels = [0 for _i in range(count)]
        self.frames = []

    def begin(self):
        pass

    def numPixels(self):
        return len(self.pixels)

    def setPixelColor(self, i, color):
        self.pixels[i] = color

    def getPixelColor(self, i):
        return self.pixels[i]

    def show(self):
        self.frames.append(self.pixels.copy())

class MockManager:
    def getDisplayColor(self, n, from_result=False):
        return 1

class LedsTest(unittest.TestCase):
    def test_strip(self):
        self.run_effects(led_handler_strip)

    def test_bitmap(self):
        self.run_effects(led_handler_bitmap)

    def test_character(self):
        self.run_effects(led_handler_character)

    def test_graph(self):
        self.run_effects(led_handler_graph)

    def run_effects(self, module):
        strip = MockPixel(36)
        race = RHRace()
        race.result_fn = lambda race: {'by_race_time': [{'starts':1, 'node':0, 'position':1}]}
        test_args = {
            'RACE': race,
            'iterations': 3,
            'time': 0,
            'lap': {
                'lap_number': 5,
                'lap_time': 45000,
                'lap_time_formatted': '45s'
            },
            'node_index': 0,
            'hide_stage_timer': True,
            'message': 'Test',
            'strip': strip,
            'manager': MockManager(),
            'INTERFACE': MockInterface()
        }
        config = {'LED_ROWS': 6, 'PANEL_ROTATE': False, 'INVERTED_PANEL_ROWS': False}
        effects = module.discover(config)
        for effect in effects:
            args = {}
            args.update(effect['defaultArgs'])
            args.update(test_args)
            strip.frames = []
            effect['handlerFn'](args)
            self.assertGreater(len(strip.frames), 0, effect)

if __name__ == '__main__':
    unittest.main()
