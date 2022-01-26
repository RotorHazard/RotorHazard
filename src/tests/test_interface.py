import unittest
from rh.interface import calculate_checksum, ExtremumFilter, RssiHistory
from rh.interface.MockInterface import MockInterface


class InterfaceTest(unittest.TestCase):
    def test_checksum(self):
        data = bytearray([200, 145])
        checksum = calculate_checksum(data)
        self.assertEqual(89, checksum)

    def test_extremum_filter(self):
        f = ExtremumFilter()
        input_data = [2, 5, 5, 5, 4, 8, 9, 7, 7, 1, 3]
        # NB: includes inflexion points
        expected_rssi = [2, 5, None, 5, 4, None, 9, 7, 7, 1]
        expected = [(i,v) for i,v in enumerate(expected_rssi)]
        actual = [f.filter(i,x) for i, x in enumerate(input_data)]
        self.assertListEqual(expected, actual[1:])

    def test_rssi_history_append(self):
        history = RssiHistory()
        history.set([0,1], [5,5])
        history.append(10, 5)
        actual_times, actual_values = history.get()
        self.assertListEqual(actual_times, [0,10])
        self.assertListEqual(actual_values, [5,5])

    def test_rssi_history_merge(self):
        history = RssiHistory()
        history.set([0,1,2,3], [5,3,6,7])
        pass_history = [(0.5,8), (2,9)]
        history.merge(pass_history)
        actual_times, actual_values = history.get()
        self.assertListEqual(actual_times, [0,0.5,1,2,3])
        self.assertListEqual(actual_values, [5,8,3,9,7])

    def test_is_new_lap(self):
        intf = MockInterface(1)
        node = intf.nodes[0]
        lap_enter_exit = intf.is_new_lap(node, 0, False)
        self.assertTupleEqual(lap_enter_exit, (False, False, False))

        lap_enter_exit = intf.is_new_lap(node, 0, True)  # enter
        self.assertTupleEqual(lap_enter_exit, (False, True, False))
        intf.process_crossing(node, True, 1, 10, 22, 8)

        lap_enter_exit = intf.is_new_lap(node, 0, False)  # exit
        self.assertTupleEqual(lap_enter_exit, (False, False, True))
        intf.process_crossing(node, False, 1, 20, 22, 8)

        lap_enter_exit = intf.is_new_lap(node, 1, False)  # lap
        self.assertTupleEqual(lap_enter_exit, (True, False, False))
        intf.process_lap_stats(node, 1, 30, 40, 5)

        self.assertEqual(node.pass_count, 1)

    def test_is_new_lap_init(self):
        intf = MockInterface(1)
        node = intf.nodes[0]
        intf.is_new_lap(node, 4, False)
        self.assertEqual(node.pass_count, 4)

    def test_is_new_lap_retry_enter(self):
        intf = MockInterface(1)
        node = intf.nodes[0]
        lap_enter_exit = intf.is_new_lap(node, 0, False)
        self.assertTupleEqual(lap_enter_exit, (False, False, False))

        lap_enter_exit = intf.is_new_lap(node, 0, True)  # enter
        lap_enter_exit = intf.is_new_lap(node, 0, True)  # enter
        self.assertTupleEqual(lap_enter_exit, (False, True, False))
        intf.process_crossing(node, True, 1, 100, 22, 8)
        lap_enter_exit = intf.is_new_lap(node, 0, True)  # enter
        self.assertTupleEqual(lap_enter_exit, (False, False, False))

        self.assertEqual(node.pass_count, 0)

    def test_is_new_lap_missed_enter(self):
        intf = MockInterface(1)
        node = intf.nodes[0]
        lap_enter_exit = intf.is_new_lap(node, 0, False)
        self.assertTupleEqual(lap_enter_exit, (False, False, False))

        lap_enter_exit = intf.is_new_lap(node, 0, False)  # exit
        self.assertTupleEqual(lap_enter_exit, (False, False, False))

        lap_enter_exit = intf.is_new_lap(node, 1, False)  # lap
        self.assertTupleEqual(lap_enter_exit, (True, True, True))
        intf.process_lap_stats(node, 1, 100, 40, 5)

        self.assertEqual(node.pass_count, 1)

    def test_is_new_lap_missed_exit(self):
        intf = MockInterface(1)
        node = intf.nodes[0]
        lap_enter_exit = intf.is_new_lap(node, 0, False)
        self.assertTupleEqual(lap_enter_exit, (False, False, False))

        lap_enter_exit = intf.is_new_lap(node, 0, True)  # enter
        self.assertTupleEqual(lap_enter_exit, (False, True, False))

        lap_enter_exit = intf.is_new_lap(node, 1, False)  # lap
        self.assertTupleEqual(lap_enter_exit, (True, True, True))
        intf.process_lap_stats(node, 1, 100, 40, 5)

        self.assertEqual(node.pass_count, 1)

    def test_is_new_lap_missed_lap(self):
        intf = MockInterface(1)
        node = intf.nodes[0]
        lap_enter_exit = intf.is_new_lap(node, 0, False)
        self.assertTupleEqual(lap_enter_exit, (False, False, False))

        lap_enter_exit = intf.is_new_lap(node, 0, False)  # exit
        self.assertTupleEqual(lap_enter_exit, (False, False, False))

        lap_enter_exit = intf.is_new_lap(node, 1, True)  # enter
        self.assertTupleEqual(lap_enter_exit, (True, True, True))
        intf.process_lap_stats(node, 1, 100, 40, 5)

        self.assertEqual(node.pass_count, 1)

    def test_is_new_lap_missed_enter_stats(self):
        intf = MockInterface(1)
        node = intf.nodes[0]
        lap_enter_exit = intf.is_new_lap(node, 0, False)
        self.assertTupleEqual(lap_enter_exit, (False, False, False))

        lap_enter_exit = intf.is_new_lap(node, 0, True)  # enter
        self.assertTupleEqual(lap_enter_exit, (False, True, False))

        lap_enter_exit = intf.is_new_lap(node, 0, False)  # exit
        self.assertTupleEqual(lap_enter_exit, (False, True, True))
        intf.process_crossing(node, False, 1, 100, 22, 8)

        lap_enter_exit = intf.is_new_lap(node, 1, False)  # lap
        self.assertTupleEqual(lap_enter_exit, (True, True, False))
        intf.process_lap_stats(node, 1, 200, 40, 5)

        self.assertEqual(node.pass_count, 1)

    def test_is_new_lap_missed_exit_stats(self):
        intf = MockInterface(1)
        node = intf.nodes[0]
        lap_enter_exit = intf.is_new_lap(node, 0, False)
        self.assertTupleEqual(lap_enter_exit, (False, False, False))

        lap_enter_exit = intf.is_new_lap(node, 0, True)  # enter
        self.assertTupleEqual(lap_enter_exit, (False, True, False))
        intf.process_crossing(node, True, 1, 100, 22, 8)

        lap_enter_exit = intf.is_new_lap(node, 0, False)  # exit
        self.assertTupleEqual(lap_enter_exit, (False, False, True))

        lap_enter_exit = intf.is_new_lap(node, 1, False)  # lap
        self.assertTupleEqual(lap_enter_exit, (True, False, True))
        intf.process_lap_stats(node, 1, 200, 40, 5)

        self.assertEqual(node.pass_count, 1)

    def test_is_new_lap_missed_all(self):
        intf = MockInterface(1)
        node = intf.nodes[0]
        lap_enter_exit = intf.is_new_lap(node, 0, False)
        self.assertTupleEqual(lap_enter_exit, (False, False, False))

        lap_enter_exit = intf.is_new_lap(node, 0, True)  # enter
        self.assertTupleEqual(lap_enter_exit, (False, True, False))

        lap_enter_exit = intf.is_new_lap(node, 0, False)  # exit
        self.assertTupleEqual(lap_enter_exit, (False, True, True))

        lap_enter_exit = intf.is_new_lap(node, 1, False)  # lap
        self.assertTupleEqual(lap_enter_exit, (True, True, True))

        self.assertEqual(node.pass_count, 0)

    def test_ai_calibrate_nodes(self):
        intf = MockInterface(1)
        node = intf.nodes[0]
        node.ai_calibrate = True
        node.first_cross_flag = True
        node.enter_at_level = 12
        node.exit_at_level = 12
        rssis = [2,2,3,4,2,4,20,22,18,2,3,4,2]
        node.history.set(list(range(len(rssis))), rssis)
        new_enter_at_level = None
        new_exit_at_level = None
        def new_enter_callback(node, enter_level):
            nonlocal new_enter_at_level
            new_enter_at_level = enter_level
        def new_exit_callback(node, exit_level):
            nonlocal new_exit_at_level
            new_exit_at_level = exit_level
        intf.listener.on_enter_trigger_changed = new_enter_callback
        intf.listener.on_exit_trigger_changed = new_exit_callback
        intf.ai_calibrate_nodes()
        self.assertEqual(new_enter_at_level, 11)
        self.assertEqual(new_exit_at_level, 9)

    def test_calibrate_nodes(self):
        intf = MockInterface(1)
        node = intf.nodes[0]
        node.ai_calibrate = True
        history_values = [2,2,3,4,2,4,20,22,18,2,3,4,2]
        history_times = list(range(len(history_values)))
        new_enter_at_level = None
        new_exit_at_level = None
        def new_enter_callback(node, enter_level):
            nonlocal new_enter_at_level
            new_enter_at_level = enter_level
        def new_exit_callback(node, exit_level):
            nonlocal new_exit_at_level
            new_exit_at_level = exit_level
        intf.listener.on_enter_trigger_changed = new_enter_callback
        intf.listener.on_exit_trigger_changed = new_exit_callback
        intf.calibrate_nodes(0, {
            0: ([{'lap_time_stamp': 7000, 'deleted': False}], history_times, history_values)
        })
        self.assertEqual(new_enter_at_level, 11)
        self.assertEqual(new_exit_at_level, 6)


if __name__ == '__main__':
    unittest.main()
