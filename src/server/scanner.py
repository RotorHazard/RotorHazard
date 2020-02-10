import sys
from flask import Flask, render_template
from flask_socketio import SocketIO
import webbrowser

import gevent
import gevent.monkey
gevent.monkey.patch_all()

sys.path.append('../interface')
sys.path.append('/home/pi/RotorHazard/src/interface')  # Needed to run on startup

import RHInterface

if len(sys.argv) < 2:
    print('Please specify serial port, e.g. COM12.')
    exit()

INTERFACE = RHInterface.get_hardware_interface(
    config={
        'SERIAL_PORTS': [sys.argv[1]]
    }
)

def log(s):
    print(s)

INTERFACE.hardware_log_callback=log

for node in INTERFACE.nodes:
    node.set_scan_interval(5645, 5945, 80, 5, 2)
    INTERFACE.set_frequency(node.index, 5645)

INTERFACE.start()

def heartbeat_thread_function():
    while True:
        gevent.sleep(0.1)
        heartbeat_data = INTERFACE.get_heartbeat_json()
        SOCKET_IO.emit('heartbeat', heartbeat_data)
        

gevent.spawn(heartbeat_thread_function)

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
