import sys
import gevent

sys.path.append('../interface')

import SerialRHInterface

INTERFACE = SerialRHInterface.get_hardware_interface(
	config={
		'SERIAL_PORTS': ['COM12']
	}
)

def log(s):
    print(s)

INTERFACE.hardware_log_callback=log

node = INTERFACE.nodes[0]
node.is_scanning = True

INTERFACE.start()

while True:
    INTERFACE.get_heartbeat_json()
    print("{0} {1}".format(node.frequency, node.current_rssi))
    gevent.sleep(0.1)
