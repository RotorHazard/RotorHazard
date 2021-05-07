'''RotorHazard socket interface layer.'''
import gevent.monkey
gevent.monkey.patch_all()
import logging
import socket

from .Node import Node
from . import RHInterface as rhi

logger = logging.getLogger(__name__)

class SocketIOLine:
    def __init__(self):
        self.lock = gevent.lock.RLock()

    def select(self, node):
        return True

    def __enter__(self):
        self.lock.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        self.lock.__exit__(exc_type, exc_value, traceback)


class SocketNode(Node):
    def __init__(self, index, socket_io):
        super().__init__(index=index, io_line=SocketIOLine())
        self.socket_io = socket_io

    @property
    def addr(self):
        sock_addr = self.socket_io.getsockname()
        return "socket:{}:{}".format(sock_addr[0], sock_addr[1])

    def close(self):
        self.socket_io.close()

    def _create(self, index):
        return SocketNode(index, self.socket_io)

    def _read_command(self, command, size):
        self.socket_io.sendall(bytearray([command]))
        data = bytearray()
        remaining = size + 1
        while remaining > 0:
            partial = self.socket_io.recv(size + 1, socket.MSG_WAITALL)
            remaining -= len(partial)
            data.extend(partial)
        return data

    def _write_command(self, command, data):
        data_with_cmd = bytearray()
        data_with_cmd.append(command)
        data_with_cmd.extend(data)
        self.socket_io.sendall(data_with_cmd)


def discover(idxOffset, config, *args, **kwargs):
    nodes = []
    config_sock_ports = getattr(config, 'SOCKET_PORTS', [])
    if config_sock_ports:
        next_index = idxOffset
        for port in config_sock_ports:
            with socket.socket() as server:
                server.bind(('', port))
                server.settimeout(5)
                logger.info("Listening on {}".format(port))
                server.listen()
                try:
                    while True:
                        conn, client_addr = server.accept()
                        logger.info("Connection from {}:{}".format(client_addr[0], client_addr[1]))
                        node = SocketNode(next_index, conn)
                        multi_nodes = rhi.build_nodes(node)
                        next_index += len(multi_nodes)
                        nodes.extend(multi_nodes)
                except socket.timeout:
                    pass
    return nodes
