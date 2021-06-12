import unittest
from interface.ChorusInterface import ChorusInterface
from server.chorus_api import ChorusAPI
from interface.MockInterface import MockInterface
import gevent

class ChorusTest(unittest.TestCase):
    class DummySerial:
        def __init__(self, handler):
            self.port = 'COM'
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
        laps = 0
        def on_start():
            nonlocal started
            started = True
        def on_stop_race():
            nonlocal race_stopped
            race_stopped = True
        def on_reset_race():
            pass
        def on_pass(node, lap_ts_ref, source, race_start_ts_ref=None):
            nonlocal laps
            laps += 1

        api = ChorusAPI(None, mock_intf, [], on_start, on_stop_race, on_reset_race)
        api_io = ChorusTest.DummySerial(lambda data : api._process_message(data))
        intf = ChorusInterface(api_io)
        api.serial_io = ChorusTest.DummySerial(lambda data : intf._process_message(data))
        intf.pass_record_callback = on_pass
        self.assertTrue(started)
        intf.set_frequency(2, 5885)
        self.assertEqual(mock_intf.nodes[2].frequency, 5885)
        intf.set_enter_at_level(4, 33)
        self.assertEqual(mock_intf.nodes[4].enter_at_level, 33)
        self.assertEqual(mock_intf.nodes[4].exit_at_level, 33)
        intf.set_exit_at_level(5, 34)
        self.assertEqual(mock_intf.nodes[4].enter_at_level, 33)
        self.assertEqual(mock_intf.nodes[4].exit_at_level, 33)
        self.assertEqual(mock_intf.nodes[5].enter_at_level, 34)
        self.assertEqual(mock_intf.nodes[5].exit_at_level, 34)
        api.emit_pass_record(mock_intf.nodes[0], 1, 98)
        gevent.sleep(0)
        self.assertEqual(laps, 1)

if __name__ == '__main__':
    unittest.main()
