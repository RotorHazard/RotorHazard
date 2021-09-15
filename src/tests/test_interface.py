import unittest
from interface import calculate_checksum, ExtremumFilter
from interface.MockInterface import MockInterface
from interface.Node import NodeManager

class InterfaceTest(unittest.TestCase):
    def test_checksum(self):
        data = bytearray([200, 145])
        checksum = calculate_checksum(data)
        self.assertEqual(89, checksum)

    def test_extremum_filter(self):
        f = ExtremumFilter()
        input_data = [2, 5, 5, 5, 4, 8, 9, 7, 7, 1, 3]
        # NB: includes inflexion points
        expected =   [0, None, 5, None, 5, 4, None, 9, 7, 7, 1]
        actual = [f.filter(x) for x in input_data]
        self.assertListEqual(expected, actual)

    def test_node_consolidate_history(self):
        nm = NodeManager()
        nm.addr = 'test:'
        node = nm.add_node(0)
        node.history_times =  [0,1,2,3]
        node.history_values = [5,3,6,7]
        node.pass_history = [(0.5,8), (2,9)]
        node.consolidate_history()
        self.assertListEqual(node.history_times, [0,0.5,1,2,3])
        self.assertListEqual(node.history_values, [5,8,3,9,7])

    def test_ai_calibrate_nodes(self):
        intf = MockInterface(1)
        node = intf.nodes[0]
        node.ai_calibrate = True
        node.first_cross_flag = True
        node.enter_at_level = 12
        node.exit_at_level = 12
        node.history_values = [2,2,3,4,2,4,20,22,18,2,3,4,2]
        new_enter_at_level = None
        new_exit_at_level = None
        def new_enter_or_exit_at_mock_callback(node_idx, enter_level, exit_level):
            nonlocal new_enter_at_level, new_exit_at_level
            new_enter_at_level = enter_level
            new_exit_at_level = exit_level
        intf.new_enter_or_exit_at_callback = new_enter_or_exit_at_mock_callback
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
        def new_enter_or_exit_at_mock_callback(node_idx, enter_level, exit_level):
            nonlocal new_enter_at_level, new_exit_at_level
            new_enter_at_level = enter_level
            new_exit_at_level = exit_level
        intf.new_enter_or_exit_at_callback = new_enter_or_exit_at_mock_callback
        intf.calibrate_nodes(0, {
            0: ([{'lap_time_stamp': 7000, 'deleted': False}], history_times, history_values)
        })
        self.assertEqual(new_enter_at_level, 11)
        self.assertEqual(new_exit_at_level, 6)


if __name__ == '__main__':
    unittest.main()
