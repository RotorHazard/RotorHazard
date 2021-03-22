import sys

import gevent
import gevent.monkey
gevent.monkey.patch_all()

from flask import Flask, render_template
from flask_socketio import SocketIO
import webbrowser

import Config

sys.path.append('../interface')
sys.path.append('/home/pi/RotorHazard/src/interface')  # Needed to run on startup

import RHInterface

if len(sys.argv) < 2:
    print('Please specify serial port, e.g. COM12.')
    exit()

Config.SERIAL_PORTS = [sys.argv[1]]
INTERFACE = RHInterface.get_hardware_interface(config=Config)
print("Nodes detected: {}".format(len(INTERFACE.nodes)))

def log(s):
    print(s)

INTERFACE.hardware_log_callback=log

for node in INTERFACE.nodes:
    INTERFACE.set_mode(node.index, 1)

def scan_thread_function():
    while True:
        for node in INTERFACE.nodes:
            data = node.read_block(INTERFACE, RHInterface.READ_NODE_SCAN_HISTORY, 9)
            if data is not None and len(data) > 0:
                freqs = []
                rssis = []
                for i in range(0, len(data), 3):
                    freq = RHInterface.unpack_16(data[i:])
                    rssi = RHInterface.unpack_8(data[i+2:])
                    if freq > 0:
                        freqs.append(freq)
                        rssis.append(rssi)
                SOCKET_IO.emit('scan_data', {'node' : node.index, 'frequency' : freqs, 'rssi' : rssis})
                gevent.sleep(0.1)
        

gevent.spawn(scan_thread_function)

APP = Flask(__name__, static_url_path='/static')
SOCKET_IO = SocketIO(APP, async_mode='gevent', cors_allowed_origins='*')

def __(s):
    return s

@APP.route('/')
def scanner():
    return render_template('scannerapp.html', num_nodes=len(INTERFACE.nodes), __=__)

def start(port_val = 5080):
    print("Running http server at port {0}".format(port_val))
    def openWindow():
        webbrowser.open('http://127.0.0.1:'+str(port_val))
    gevent.spawn(openWindow)
    try:
        SOCKET_IO.run(APP, host='0.0.0.0', port=port_val, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        print("Server terminated by keyboard interrupt")
    except Exception as ex:
        print("Server exception: {0}".format(ex))

# Start HTTP server
if __name__ == '__main__':
    start()
