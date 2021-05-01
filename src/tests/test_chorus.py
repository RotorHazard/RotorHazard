import unittest
from interface.ChorusInterface import ChorusInterface
from server.chorus_api import ChorusAPI
from interface.MockInterface import MockInterface

class ChorusTest(unittest.TestCase):
    class DummySerial:
        def __init__(self, handler):
            self.handler = handler
            self.buffer = []

        def write(self, raw_data):
            msg = bytes.decode(raw_data)[:-1]
            response = self.handler(msg)
            self.buffer.append(response)

        def read_until(self):
            data = self.buffer.pop(0)
            return data

    def test(self):
        mock_intf = MockInterface()
        started = False
        race_stopped = False
        def on_start():
            nonlocal started
            started = True
        def on_stop_race():
            nonlocal race_stopped
            race_stopped = True
        def on_reset_race():
            pass
        api = ChorusAPI(None, mock_intf, [], on_start, on_stop_race, on_reset_race)
        serial_io = ChorusTest.DummySerial(lambda data : api._process_message(data))
        intf = ChorusInterface(serial_io)
        self.assertTrue(started)
        intf.set_frequency(2, 5885)
        self.assertEqual(mock_intf.nodes[2].frequency, 5885)
        intf.set_enter_at_level(4, 33)
        self.assertEqual(mock_intf.nodes[4].enter_at_level, 33)
        self.assertEqual(mock_intf.nodes[4].exit_at_level, 33)

if __name__ == '__main__':
    unittest.main()
