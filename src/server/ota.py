import logging
from pathlib import Path
from flask import request, send_file
from flask.blueprints import Blueprint

logger = logging.getLogger(__name__)

def createBlueprint():
    APP = Blueprint('ota', __name__)

    @APP.route('/ota/')
    def ota_upgrade():
        user_agent = request.headers.get('User-Agent')
        if user_agent == 'ESP32-http-Update':
            firmware_path = 'build_esp32/rhnode.bin'
            provided_version = request.headers['X-Esp32-Version']
        elif user_agent == 'ESP8266-http-Update':
            firmware_path = 'build_esp8266/rhnode.bin'
            provided_version = request.headers['x-ESP8266-version']
        else:
            return "", 501

        current_version = None
        config_file = Path("node")/Path(firmware_path).parent/'sketch/config.h'
        with open(config_file, 'rt') as f:
            for line in f:
                if line.startswith("#define FIRMWARE_VERSION"):
                    current_version = line.split(' ')[-1][1:-2]
                    break
        if not current_version:
            raise Exception("Could not find FIRMWARE_VERSION in {}".format(config_file))

        if float(current_version[1:]) > float(provided_version[1:]):
            bin_path = Path("../node")/firmware_path
            logger.info("OTA upgrade from {} to {} using {}".format(provided_version, current_version, bin_path))
            return send_file(bin_path, mimetype='application/octet-stream')
        else:
            logger.info("No OTA upgrade available for {} (available {})".format(provided_version, current_version))
            return "", 304

    return APP
