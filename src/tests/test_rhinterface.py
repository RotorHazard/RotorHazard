import sys
import logging
import unittest
from interface.RHInterface import RHInterface
from server import Config
import gevent
import subprocess

logger = logging.getLogger()
logger.level = logging.DEBUG
logger.addHandler(logging.StreamHandler(sys.stdout))

class RHInterfaceTest(unittest.TestCase):
    def test_node(self):
        self.node_proc = subprocess.Popen(["node/build_sil/rhnode1", "COUNTER", "127.0.0.1:7881"])
        try:
            laps = 0
            def on_pass(node, lap_ts_ref, source, race_start_ts_ref=None):
                nonlocal laps
                laps += 1
    
            config = Config
            config.SOCKET_PORTS = [7881]
            intf = RHInterface(config=config, warn_loop_time=66000)
            intf.pass_record_callback = on_pass
            self.assertEqual(len(intf.nodes), 1)
            intf.set_frequency(0, 5885)
            self.assertEqual(intf.nodes[0].frequency, 5885)
            intf.set_enter_at_level(0, 33)
            self.assertEqual(intf.nodes[0].enter_at_level, 33)
            intf.set_exit_at_level(0, 34)
            self.assertEqual(intf.nodes[0].exit_at_level, 34)
            intf.start()
            gevent.sleep(10)
            self.assertGreater(laps, 0)
            intf.stop()
            intf.close()
        finally:
            self.node_proc.terminate()

    def test_multinode(self):
        self.node_proc = subprocess.Popen(["node/build_sil/rhnode4", "COUNTER", "127.0.0.1:7884"])
        try:
            laps = 0
            def on_pass(node, lap_ts_ref, source, race_start_ts_ref=None):
                nonlocal laps
                laps += 1
    
            config = Config
            config.SOCKET_PORTS = [7884]
            intf = RHInterface(config=config, warn_loop_time=66000)
            intf.pass_record_callback = on_pass
            self.assertEqual(len(intf.nodes), 4)
            intf.set_frequency(0, 5885)
            self.assertEqual(intf.nodes[0].frequency, 5885)
            intf.set_enter_at_level(1, 33)
            self.assertEqual(intf.nodes[1].enter_at_level, 33)
            intf.set_exit_at_level(2, 34)
            self.assertEqual(intf.nodes[2].exit_at_level, 34)
            intf.start()
            gevent.sleep(10)
            self.assertGreater(laps, 0)
            intf.stop()
            intf.close()
        finally:
            self.node_proc.terminate()

    def test_no_nodes(self):
        self.node_proc = subprocess.Popen(["node/build_sil/rhnode0", "COUNTER", "127.0.0.1:7880"])
        try:
            config = Config
            config.SOCKET_PORTS = [7880]
            intf = RHInterface(config=config, warn_loop_time=66000)
            self.assertEqual(len(intf.nodes), 0)
            intf.close()
        finally:
            self.node_proc.terminate()

if __name__ == '__main__':
    unittest.main()
