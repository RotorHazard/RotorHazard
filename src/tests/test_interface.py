import unittest
from interface import calculate_checksum, ExtremumFilter, RssiHistory
from interface.MockInterface import MockInterface
from interface.BaseHardwareInterface import PeakNadirHistory


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

    def test_peak_nadir_history_empty(self):
        intf = MockInterface(1)
        node = intf.nodes[0]
        now = 100
        pn = PeakNadirHistory(node, now)
        self.assertTrue(pn.isEmpty())

    def test_peak_nadir_history_peak_before_nadir(self):
        intf = MockInterface(1)
        node = intf.nodes[0]
        now = 100
        pn = PeakNadirHistory(node, now)
        pn.peakRssi = 10
        pn.nadirRssi = 1
        pn.peakFirstTime = pn.peakLastTime = 8000
        pn.nadirFirstTime = pn.nadirLastTime = 5000
        history = RssiHistory()
        pn.addTo(history)
        history_times, history_values = history.get()
        self.assertListEqual(history_times, [92, 95])
        self.assertListEqual(history_values, [10, 1])

    def test_peak_nadir_history_peak_before_nadir_extended(self):
        intf = MockInterface(1)
        node = intf.nodes[0]
        now = 100
        pn = PeakNadirHistory(node, now)
        pn.peakRssi = 10
        pn.nadirRssi = 1
        pn.peakFirstTime = 9000
        pn.peakLastTime = 8000
        pn.nadirFirstTime = 6000
        pn.nadirLastTime = 5000
        history = RssiHistory()
        pn.addTo(history)
        history_times, history_values = history.get()
        self.assertListEqual(history_times, [91, 92, 94, 95])
        self.assertListEqual(history_values, [10, 10, 1, 1])

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
