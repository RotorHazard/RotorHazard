import gevent.monkey 
gevent.monkey.patch_all()

import logging
import sys
from rh.app.config import Config
from rh.interface import RHInterface, MockInterface
from rh.helpers import parse_i2c_url
try:
    from rh.helpers.i2c_helper import I2CBus
except:
    I2CBus = None


def start(port, freq, write_buffer):
    if port == 'MOCK':
        INTERFACE = MockInterface.get_hardware_interface()
    elif port.startswith('COM') or port.startswith('/dev/'):
        config = Config()
        config.SERIAL_PORTS = [port]
        INTERFACE = RHInterface.get_hardware_interface(config=config)
    elif port.startswith('i2c:'):
        if not I2CBus:
            raise ValueError("No I2C bus support available")
        bus_addr = parse_i2c_url(port)
        params = {}
        params['idxOffset'] = 0
        params['i2c_helper'] = [I2CBus(bus_addr[0])]
        params['i2c_addrs'] = [bus_addr[1]]
        INTERFACE = RHInterface.get_hardware_interface(**params)
    elif port.startswith(':'):
        config = Config()
        config.SOCKET_PORTS = [int(port[1:])]
        INTERFACE = RHInterface.get_hardware_interface(config=config)
    else:
        print("Invalid port: {}".format(port))
        exit(1)
    print("Nodes detected: {}".format(len(INTERFACE.nodes)))

    for node in INTERFACE.nodes:
        INTERFACE.set_mode(node.index, RHInterface.RSSI_HISTORY_MODE)
        INTERFACE.set_frequency(node.index, freq)

    count = 1
    dataBuffer = []
    try:
        while True:
            gevent.sleep(0.1)

            for node in INTERFACE.nodes:
                data = INTERFACE.read_rssi_history(node.index)
                if data is not None and len(data) > 0:
                    for rssi in data:
                        if rssi == 0xFF:
                            filename = "rssi_dump_{}.csv".format(count)
                            write_buffer(filename, dataBuffer)
                            dataBuffer = []
                            count += 1
                        elif rssi > 0:
                            dataBuffer.append(rssi)
    except:
        filename = 'rssi_dump.csv'
        write_buffer(filename, dataBuffer)
        INTERFACE.close()
        raise

def write_buffer(filename, buf):
    with open(filename, 'w') as f:
        for v in buf:
            f.write('{}\n'.format(v))
    print("Written {} ({})".format(filename, len(buf)))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 3:
        print('Please specify a serial port, e.g. COM12 (or I2C address, e.g. i2c:1/0x08, or socket port, e.g. :5005), and a frequency.')
        exit()
    port = sys.argv[1]
    freq = int(sys.argv[2])
    start(port, freq, write_buffer)
