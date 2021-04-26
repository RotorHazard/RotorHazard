import sys

import gevent
import gevent.monkey
gevent.monkey.patch_all()

import Config

sys.path.append('../interface')
sys.path.append('/home/pi/RotorHazard/src/interface')  # Needed to run on startup

import RHInterface

if len(sys.argv) < 3:
    print('Please specify serial port, e.g. COM12, and a frequency.')
    exit()
    
showLoopTime = len(sys.argv) > 3

Config.SERIAL_PORTS = [sys.argv[1]]
freq = int(sys.argv[2])
INTERFACE = RHInterface.get_hardware_interface(config=Config)
print("Nodes detected: {}".format(len(INTERFACE.nodes)))

def log(s):
    print(s)

INTERFACE.hardware_log_callback=log

for node in INTERFACE.nodes:
    INTERFACE.set_mode(node.index, 2)
    INTERFACE.set_frequency(node.index, freq)

def write_buffer(fname, buf):
    with open(fname, 'w') as f:
        for v in buf:
            f.write('{}\n'.format(v))
    print("Written {} ({})".format(fname, len(buf)))

count = 1
dataBuffer = []
minLoopTime = 9999999
maxLoopTime = 0
try:
    while True:
        gevent.sleep(0.1)
    
        for node in INTERFACE.nodes:
            if showLoopTime:
                data = node.read_block(INTERFACE, RHInterface.READ_LAP_PASS_STATS, 8)
                loopTime = RHInterface.unpack_16(data[6:])
                minLoopTime = min(loopTime, minLoopTime)
                maxLoopTime = max(loopTime, maxLoopTime)
                print("Loop time: {} (min {}, max {})".format(loopTime, minLoopTime, maxLoopTime))
            data = node.read_block(INTERFACE, RHInterface.READ_NODE_RSSI_HISTORY, 16)
            if data is not None and len(data) > 0:
                for rssi in data:
                    if rssi == 0xFF:
                        fname = "rssi_dump_{}.csv".format(count)
                        write_buffer(fname, dataBuffer)
                        dataBuffer = []
                        count += 1
                    elif rssi > 0:
                        dataBuffer.append(rssi)
except:
    fname = 'rssi_dump.csv'
    write_buffer(fname, dataBuffer)
    raise
