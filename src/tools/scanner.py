import gevent.monkey
gevent.monkey.patch_all()

import logging
import sys
from flask import Flask, render_template
from flask_socketio import SocketIO
import webbrowser

from server import Config
from interface import RHInterface, MockInterface

def scan(port, socket):
    if port == 'MOCK':
        INTERFACE = MockInterface.get_hardware_interface()
    else:
        Config.SERIAL_PORTS = [port]
        INTERFACE = RHInterface.get_hardware_interface(config=Config)
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
        print('Please specify serial port, e.g. COM12.')
        exit()
    port = sys.argv[1]
    start(port)
