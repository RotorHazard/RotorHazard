import gevent.monkey
gevent.monkey.patch_all()

import logging
import sys
from flask import Flask, render_template
from flask_socketio import SocketIO
import webbrowser

from rh.app.config import Config
from rh.interface import RHInterface, MockInterface

def scan(port, socket):
    if port == 'MOCK':
        INTERFACE = MockInterface.get_hardware_interface()
    elif port.startswith('COM') or port.startswith('/dev/'):
        config = Config()
        config.SERIAL_PORTS = [port]
        INTERFACE = RHInterface.get_hardware_interface(config=config)
    elif port.startswith('i2c:'):
        from rh.helpers import parse_i2c_url
        from rh.helpers.i2c_helper import I2CBus

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
        INTERFACE.set_mode(node.index, RHInterface.SCANNER_MODE)
    
    def scan_thread_function():
        while True:
            for node in INTERFACE.nodes:
                freqs, rssis = INTERFACE.read_scan_history(node.index)
                if freqs and rssis:
                    socket.emit('scan_data', {'node' : node.index, 'frequency' : freqs, 'rssi' : rssis})
                    gevent.sleep(0.1)
            
    
    gevent.spawn(scan_thread_function)
    return INTERFACE

def start(com_port, web_port = 5080):
    APP = Flask(__name__, template_folder='../server/templates', static_folder='../server/static',static_url_path='/static')
    SOCKET_IO = SocketIO(APP, async_mode='gevent', cors_allowed_origins='*')
    INTERFACE = scan(com_port, SOCKET_IO)
    
    @APP.route('/')
    def scanner():
        return render_template('scannerapp.html', num_nodes=len(INTERFACE.nodes), __=lambda s: s)

    print("Running http server at port {0}".format(web_port))
    def openWindow():
        webbrowser.open('http://127.0.0.1:'+str(web_port))
    gevent.spawn(openWindow)
    try:
        SOCKET_IO.run(APP, host='0.0.0.0', port=web_port, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        print("Server terminated by keyboard interrupt")
    except Exception as ex:
        print("Server exception: {0}".format(ex))

    INTERFACE.close()

# Start HTTP server
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('socketio').setLevel(logging.WARN)
    logging.getLogger('engineio').setLevel(logging.WARN)
    logging.getLogger('geventwebsocket').setLevel(logging.WARN)
    if len(sys.argv) < 2:
        print('Please specify serial port, e.g. COM12 (or I2C address, e.g. i2c:1/0x08, or socket port, e.g. :5005).')
        exit()
    port = sys.argv[1]
    start(port)
