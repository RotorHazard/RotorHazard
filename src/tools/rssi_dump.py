import gevent.monkey 
gevent.monkey.patch_all()

import logging
import sys
from server import Config
from interface import RHInterface, MockInterface, unpack_16

def start(port, freq, showLoopTime, write_buffer):
    if port == 'MOCK':
        INTERFACE = MockInterface.get_hardware_interface()
    else:
        Config.SERIAL_PORTS = [port]
        INTERFACE = RHInterface.get_hardware_interface(config=Config)
    print("Nodes detected: {}".format(len(INTERFACE.nodes)))

    for node in INTERFACE.nodes:
        INTERFACE.set_mode(node.index, RHInterface.RSSI_HISTORY_MODE)
        INTERFACE.set_frequency(node.index, freq)

    count = 1
    dataBuffer = []
    minLoopTime = 9999999
    maxLoopTime = 0
    try:
        while True:
            gevent.sleep(0.1)

            for node in INTERFACE.nodes:
                if showLoopTime:
                    data = node.read_block(RHInterface.READ_LAP_PASS_STATS, 8)
                    loopTime = unpack_16(data[6:])
                    minLoopTime = min(loopTime, minLoopTime)
                    maxLoopTime = max(loopTime, maxLoopTime)
                    print("Loop time: {} (min {}, max {})".format(loopTime, minLoopTime, maxLoopTime))
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
        print('Please specify serial port, e.g. COM12, and a frequency.')
        exit()
    port = sys.argv[1]
    freq = int(sys.argv[2])
    showLoopTime = len(sys.argv) > 3
    start(port, freq, showLoopTime, write_buffer)
