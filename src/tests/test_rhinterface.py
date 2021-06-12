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
        subprocess.run("./scripts/build_ci.sh 1", cwd='node', shell=True)
        self.node_proc = subprocess.Popen(["node/build_ci/rhnode1", "COUNTER", "127.0.0.1:7881"])
        try:
            laps = 0
            def on_pass(node, lap_ts_ref, source, race_start_ts_ref=None):
                nonlocal laps
                laps += 1
    
            config = Config()
            config.SERIAL_PORTS = []
            config.SOCKET_PORTS = [7881]
            intf = RHInterface(config=config, warn_loop_time=66000)
            try:
                intf.pass_record_callback = on_pass
                self.assertEqual(len(intf.nodes), 1)
                for i in range(len(intf.nodes)):
                    self.assertEqual(intf.nodes[i].index, i)
                    self.assertEqual(intf.nodes[i].multi_node_index, i)
                    self.assertEqual(intf.nodes[i].multi_node_slot_index, i)
                self.check_settings(intf)
                intf.start()
    
                # test laps
                gevent.sleep(10)
                self.assertGreater(laps, 0)
    
                # test scan
                node = intf.nodes[0]
                intf.set_frequency_scan(0, True)
                self.assertEqual(node.scan_enabled, True)
                gevent.sleep(10)
                self.assertGreater(len(node.scan_data), 0)
                intf.set_frequency_scan(0, False)
                self.assertEqual(node.scan_enabled, False)
                self.assertEqual(len(node.scan_data), 0)
    
                intf.send_shutdown_started_message()
            finally:
                intf.stop()
                intf.close()
        finally:
            self.node_proc.terminate()
            self.node_proc.wait(timeout=30)
        self.gcov('test_rhnode1')

    def test_multinode(self):
        subprocess.run("./scripts/build_ci.sh 4", cwd='node', shell=True)
        self.node_proc = subprocess.Popen(["node/build_ci/rhnode4", "COUNTER", "127.0.0.1:7884"])
        try:
            laps = 0
            def on_pass(node, lap_ts_ref, source, race_start_ts_ref=None):
                nonlocal laps
                laps += 1
    
            config = Config()
            config.SERIAL_PORTS = []
            config.SOCKET_PORTS = [7884]
            intf = RHInterface(config=config, warn_loop_time=66000)
            try:
                intf.pass_record_callback = on_pass
                self.assertEqual(len(intf.nodes), 4)
                for i in range(len(intf.nodes)):
                    self.assertEqual(intf.nodes[i].index, i)
                    self.assertEqual(intf.nodes[i].multi_node_index, i)
                    self.assertEqual(intf.nodes[i].multi_node_slot_index, i)
                self.check_settings(intf)
                intf.start()
    
                gevent.sleep(10)
                self.assertGreater(laps, 0)
    
                intf.send_shutdown_started_message()
            finally:
                intf.stop()
                intf.close()
        finally:
            self.node_proc.terminate()
            self.node_proc.wait(timeout=30)
        self.gcov('test_rhnode4')

    def test_no_nodes(self):
        subprocess.run("./scripts/build_ci.sh 0", cwd='node', shell=True)
        self.node_proc = subprocess.Popen(["node/build_ci/rhnode0", "COUNTER", "127.0.0.1:7880"])
        try:
            config = Config()
            config.SERIAL_PORTS = []
            config.SOCKET_PORTS = [7880]
            intf = RHInterface(config=config, warn_loop_time=66000)
            try:
                self.assertEqual(len(intf.nodes), 0)
                intf.start()
    
                gevent.sleep(1)
    
                intf.send_shutdown_started_message()
            finally:
                intf.stop()
                intf.close()
        finally:
            self.node_proc.terminate()
            self.node_proc.wait(timeout=30)
        self.gcov('test_rhnode0')

    def check_settings(self, intf):
        for i in range(len(intf.nodes)):
            intf.set_frequency(i, 5885)
            self.assertEqual(intf.nodes[i].frequency, 5885)
            intf.set_enter_at_level(i, 23)
            self.assertEqual(intf.nodes[i].enter_at_level, 23)
            intf.set_exit_at_level(i, 24)
            self.assertEqual(intf.nodes[i].exit_at_level, 24)

    def gcov(self, testname):
        subprocess.run("gcov -b -c *.cpp", cwd='node', shell=True)
        subprocess.run("mkdir -p {0}; mv *.gcov {0}; rm *.gcda; rm *.gcno".format(testname), cwd='node', shell=True)

if __name__ == '__main__':
    unittest.main() 
