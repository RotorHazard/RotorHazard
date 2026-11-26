'''Tests for network serial nodes ("socket://host:port" in SERIAL_PORTS).

python -m unittest discover
'''
import os
import socket
import sys
import threading
import time
import unittest

import gevent
import gevent.lock  # (serial_node uses it without importing it; the server imports it first)

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.join(_SRC_DIR, 'interface'))
sys.path.append(os.path.join(_SRC_DIR, 'server', 'util'))

import serial_node  # noqa: E402
import SerialPortInfo  # noqa: E402

API_LEVEL = 36
SEATS = 2

# write commands and their data lengths (each followed by a checksum byte)
WRITE_LENGTHS = {0x7A: 1, 0x51: 2, 0x71: 1, 0x72: 1, 0x75: 2, 0x78: 1}


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class FakeNode:
    '''A multi-node processor behind a TCP server, answering the RotorHazard node protocol.'''

    def __init__(self, port):
        self.port = port
        self.silent = False  # True: read commands get no reply (as a far end that is gone)
        self.ignore = set()  # read commands that get no reply (not supported by this node)
        self.cur = 0
        self.freq = [5658] * SEATS
        self.enter_at = [96] * SEATS
        self.exit_at = [80] * SEATS
        self.conns = []
        self.listener = None
        self.running = False

    def start(self):
        self.listener = socket.socket()
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(('127.0.0.1', self.port))
        self.listener.listen(4)
        self.running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        return self

    def stop(self):
        self.running = False
        for sock in [self.listener] + self.conns:
            try:
                sock.close()
            except OSError:
                pass
        self.conns = []

    def _accept_loop(self):
        while self.running:
            try:
                conn, _ = self.listener.accept()
            except OSError:
                return
            self.conns.append(conn)
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    @staticmethod
    def _recv_exact(conn, n):
        data = b''
        while len(data) < n:
            chunk = conn.recv(n - len(data))
            if not chunk:
                raise OSError('closed')
            data += chunk
        return data

    @staticmethod
    def _text(text):
        return text.encode().ljust(16, b'\0')[:16]

    def _reply(self, cmd):
        c = self.cur
        replies = {
            0x22: bytes([0x25, API_LEVEL]),
            0x39: bytes([SEATS]),
            0x3A: bytes([c]),
            0x3C: bytes([c]),
            0x3D: self._text('1.2.3'),
            0x3E: self._text('Nov 26 2026'),
            0x3F: self._text('12:00:00'),
            0x40: self._text('FAKE'),
            0x11: bytes([0, 0]),
            0x03: self.freq[c].to_bytes(2, 'big'),
            0x04: bytes([1]),  # TEST_RX_REGISTER: receiver module present
            0x31: bytes([self.enter_at[c]]),
            0x32: bytes([self.exit_at[c]]),
            0x23: bytes([120]),
            0x24: bytes([40]),
            # lap 0, 1000 ms since pass, level 50, node peak 120, pass peak 0, loop 2000 us
            0x0D: bytes([0, 0x03, 0xE8, 50, 120, 0, 0x07, 0xD0]),
            # no crossing, pass nadir 0, node nadir 40, no queued extremum
            0x0E: bytes([0, 0, 40, 0, 0, 0, 0, 0]),
        }
        return replies.get(cmd)

    def _serve(self, conn):
        try:
            while self.running:
                cmd = self._recv_exact(conn, 1)[0]
                if cmd in WRITE_LENGTHS:
                    data = self._recv_exact(conn, WRITE_LENGTHS[cmd] + 1)[:-1]
                    if cmd == 0x7A:
                        self.cur = min(data[0], SEATS - 1)
                    elif cmd == 0x51:
                        self.freq[self.cur] = int.from_bytes(data, 'big')
                    elif cmd == 0x71:
                        self.enter_at[self.cur] = data[0]
                    elif cmd == 0x72:
                        self.exit_at[self.cur] = data[0]
                    continue
                reply = self._reply(cmd)
                if reply is None or self.silent or cmd in self.ignore:
                    continue
                conn.sendall(reply + bytes([sum(reply) & 0xFF]))
        except OSError:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass


class FakeInterface:
    '''The parts of RHInterface that SerialNode uses.'''

    def __init__(self):
        self.messages = []

    def log(self, message):
        self.messages.append(message)

    def inc_intf_read_block_count(self):
        pass

    def inc_intf_read_error_count(self):
        pass

    def inc_intf_write_block_count(self):
        pass

    def inc_intf_write_error_count(self):
        pass


def wait_for(cond, timeout_secs):
    '''Runs the gevent loop (for background probes) until cond() or the timeout; returns cond()'''
    end = time.monotonic() + timeout_secs
    while time.monotonic() < end:
        if cond():
            return True
        gevent.sleep(0.05)
    return cond()


class SocketNodeTest(unittest.TestCase):
    def setUp(self):
        self.port = free_port()
        self.url = 'socket://127.0.0.1:{}'.format(self.port)
        self.fake = FakeNode(self.port).start()
        self.nodes = []
        SerialPortInfo._url_present_cache.clear()

    def tearDown(self):
        for ser in set(node.serial for node in self.nodes):
            try:
                ser.close()
            except Exception:
                pass
        self.fake.stop()

    def discover(self):
        self.nodes = serial_node.discover(0, None, ports=[self.url])
        return self.nodes

    def test_url_helpers(self):
        self.assertTrue(serial_node.is_url_port('socket://gate1.local:2217'))
        self.assertFalse(serial_node.is_url_port('/dev/ttyACM0'))
        self.assertFalse(serial_node.is_url_port('COM3'))
        self.assertEqual(serial_node.url_port_address('socket://gate1.local:2217'), ('gate1.local', 2217))
        self.assertEqual(serial_node.url_port_address('rfc2217://10.0.0.5:4000'), ('10.0.0.5', 4000))
        self.assertIsNone(serial_node.url_port_address('socket://nohostport'))
        self.assertIsNone(serial_node.url_port_address('loop://'))

    def test_discover(self):
        nodes = self.discover()
        self.assertEqual(len(nodes), SEATS)
        self.assertEqual(nodes[0].api_level, API_LEVEL)
        self.assertEqual(nodes[0].firmware_version_str, '1.2.3')
        self.assertEqual([node.multi_node_index for node in nodes], list(range(SEATS)))
        self.assertIs(nodes[0].serial, nodes[1].serial)  # one connection for the processor

    def test_nodelay_and_reopen_delay(self):
        nodes = self.discover()
        sock = nodes[0].serial._socket
        self.assertNotEqual(sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY), 0)
        self.assertNotEqual(sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE), 0)
        self.assertEqual(nodes[0].serial.rh_reopen_delay_secs, serial_node.REOPEN_S32_DELAY_SECS)

    def test_polling(self):
        nodes = self.discover()
        intf = FakeInterface()
        data = nodes[1].read_block(intf, 0x0D, 8)
        self.assertEqual(list(data), [0, 0x03, 0xE8, 50, 120, 0, 0x07, 0xD0])
        self.assertEqual(self.fake.cur, 1)  # the seat was selected first
        self.assertTrue(nodes[0].write_block(intf, 0x51, serial_node.pack_16(5917)))
        self.assertEqual(serial_node.unpack_16(nodes[0].read_block(intf, 0x03, 2)), 5917)
        self.assertEqual(self.fake.freq[0], 5917)

    def test_unreachable(self):
        self.fake.stop()
        start = time.monotonic()
        self.assertEqual(self.discover(), [])
        self.assertLess(time.monotonic() - start, 3.0)

    def test_silent_far_end(self):
        '''A far end that stops answering without closing the connection (cable pulled)'''
        nodes = self.discover()
        intf = FakeInterface()
        ser = nodes[0].serial
        self.fake.silent = True
        reads = 0
        while not getattr(ser, 'rh_reopen_pending', False) and reads < 20:
            nodes[0].read_block(intf, 0x0D, 8)
            reads += 1
        self.assertTrue(ser.rh_reopen_pending, 'port not marked lost')
        self.assertFalse(ser.is_open)
        self.assertTrue(any('no response from network node' in m for m in intf.messages))
        # answering again: reopened by the next I/O attempts
        self.fake.silent = False
        self.assertTrue(wait_for(lambda: nodes[0].port_available(intf) or
                                 getattr(ser, 'rh_reopen_count', 0) > 0, 8.0), 'port not reopened')
        self.assertEqual(ser.rh_reopen_count, 1)
        self.assertTrue(wait_for(lambda: nodes[0].read_block(intf, 0x0D, 8) is not None, 3.0))

    def test_unanswered_command(self):
        '''A node that doesn't answer one command is not taken for a lost connection'''
        nodes = self.discover()
        intf = FakeInterface()
        self.fake.ignore = {0x23}
        for _ in range(4):
            self.assertIsNone(nodes[0].read_block(intf, 0x23, 1))  # 5 tries each, ~1.25 s
            self.assertIsNotNone(nodes[0].read_block(intf, 0x0D, 8))
        self.assertFalse(getattr(nodes[0].serial, 'rh_reopen_pending', False))

    def test_far_end_restart(self):
        '''The node's server goes away (bridge rebooted) and comes back'''
        nodes = self.discover()
        intf = FakeInterface()
        ser = nodes[0].serial
        self.fake.stop()
        reads = 0
        while not getattr(ser, 'rh_reopen_pending', False) and reads < 20:
            nodes[0].read_block(intf, 0x0D, 8)
            reads += 1
        self.assertTrue(ser.rh_reopen_pending, 'port not marked lost')
        # while it is away, reopen attempts fail without stalling
        start = time.monotonic()
        nodes[0].port_available(intf)
        self.assertLess(time.monotonic() - start, 0.2)
        self.fake = FakeNode(self.port).start()
        self.assertTrue(wait_for(lambda: nodes[0].port_available(intf) or
                                 getattr(ser, 'rh_reopen_count', 0) > 0, 8.0), 'port not reopened')
        self.assertTrue(wait_for(lambda: nodes[0].read_block(intf, 0x0D, 8) is not None, 3.0))
        self.assertNotEqual(ser._socket.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY), 0)

    def test_port_info(self):
        self.assertEqual(SerialPortInfo._norm_key(' Socket://Gate1.local:2217 '), 'socket://gate1.local:2217')
        self.assertTrue(SerialPortInfo.port_present(self.url))
        listing = SerialPortInfo.list_serial_ports([self.url])
        self.assertNotIn(self.url, listing['configured_missing'])
        entry = [p for p in listing['ports'] if p['device'] == self.url]
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry[0]['configured'], self.url)
        self.fake.stop()
        SerialPortInfo._url_present_cache.clear()
        self.assertFalse(SerialPortInfo.port_present(self.url))


if __name__ == '__main__':
    unittest.main()
