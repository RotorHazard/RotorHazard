'''RotorHazard socket interface layer.'''
import gevent.monkey
gevent.monkey.patch_all()
import logging
import socket

from . import RHInterface as rhi

logger = logging.getLogger(__name__)


class SocketNodeManager(rhi.RHNodeManager):
    def __init__(self, socket_obj):
        super().__init__()
        self.socket_io = socket_obj
        sock_addr = self.socket_io.getsockname()
        self.addr = "socket://{}:{}/".format(sock_addr[0], sock_addr[1])

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

    def close(self):
        self.socket_io.close()


def discover(idxOffset, config, *args, **kwargs):
    node_managers = []
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
                    while True: # while server socket doesn't time-out
                        conn, client_addr = server.accept()
                        logger.info("Connection from {}:{}".format(client_addr[0], client_addr[1]))
                        conn.settimeout(2)
                        node_manager = SocketNodeManager(conn)
                        if node_manager.discover_nodes(next_index):
                            next_index += len(node_manager.nodes)
                            node_managers.append(node_manager)
                        else:
                            conn.close()
                except socket.timeout:
                    pass
    return node_managers
