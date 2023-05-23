# Utility class for Raspberry Pi GPIO functions
import json
import logging
# resources:
# https://www.ics.com/blog/gpio-programming-exploring-libgpiod-library
# https://lloydrochester.com/post/hardware/libgpiod-intro-rpi/

import time
from util.sbcUtil import *
logger = logging.getLogger(__name__)


HIGH = 1
LOW = 0
UNKNOWN = -1

sbc_model = ''
gpio_lookup = {}
gpio_model_lookup = {
    "Raspberry Pi 3 Model B Rev 1.2" : "pi3b_gpio.json",
    "Libre Computer AML-S905X-CC" : "potato_gpio.json",
    "Raspberry Pi Zero W Rev 1.1": "pizero_gpio.json",
    "Raspberry Pi 4 Model B Rev 1.2": "pi4_gpio.json"
}


if is_raspberry() or is_libre():
    RealGPIOFlag = True
    import gpiod
else:
    RealGPIOFlag = False

s32_blue_pill_board_flag = None
def is_real_gpio():
    return RealGPIOFlag

def is_blue_pill_board():

    global s32_blue_pill_board_flag

    if s32_blue_pill_board_flag is None:
        if RealGPIOFlag:
            line = get_line_by_board_pin(22)
            if line:
                line_config = gpiod.line_request()
                line_config.consumer = "RotorHazard"
                line_config.request_type = gpiod.line_request.DIRECTION_INPUT
                line_config.flags = line_config.FLAG_BIAS_PULL_UP
                line.request(line_config, 1)
                time.sleep(0.05)
                s32_blue_pill_board_flag = not line.get_value()
                line.release()
    return s32_blue_pill_board_flag


def set_blue_pill_board_flag():
    global s32_blue_pill_board_flag
    s32_blue_pill_board_flag = True


def get_line(pin_number):
    """
    returns a handle to a gpiod.line object.
    if system is a raspberry then it treats pin_number as the GPIO number.
    if system is libre then it treats pin_number as the board pin number.
    """
    line_name = None

    if is_raspberry():
        line_name = f'GPIO{pin_number}'
    elif is_libre():
        line_name = f'7J1 Header Pin{pin_number}'
    return get_line_by_name(line_name)

def get_line_by_name(line_name):
    """
    If you already know the name of the line you want to use
    you can use this method to get a handle to the line
    """
    print(f'trying {line_name} for GPIO number')
    for chip in gpiod.make_chip_iter():
        # line = chip.find_line(line_name)
        # if line is not None:
        #     return line
        for offset in range(chip.num_lines):
            the_line = chip.get_line(offset)
            if the_line:
                the_name = the_line.name
                if line_name == the_name:
                    return the_line
    return None

def load_lookup_table():
    """
    We are storing the lookup tables for converting from board pin to line offset in
    json files within this directory.
    each json file contains an array of dicts in the form
    {
        "Board_Pin": 28,
        "Chip": "gpiochip0",
        "Line": "line   1:",
        "Offset": 1,
        "Name": "ID_SCL",
        "Info": "I2C_ ID EEPROM"
    }
    """
    try:
        import importlib.resources as pkg_resources
    except ImportError:
        # Try backported to PY<37 `importlib_resources`.
        import importlib_resources as pkg_resources

    global gpio_lookup
    global sbc_model
    if not gpio_lookup:
        sbc_model = get_sbc_model()
        if not sbc_model:
            sbc_model = "Raspberry Pi 3 Model B Rev 1.2"
    logger.info(f"sbc_model is: {sbc_model}")
    try:

        json_name = gpio_model_lookup[sbc_model]
        logger.info(f"gpio info file is: {json_name}")
    except Exception as up:
        logger.error(f"Failed to find gpio info file. sbc:'{sbc_model}")
        raise up
    import util
    gpio_lookup = json.loads(pkg_resources.read_text(util, json_name))

def get_line_by_board_pin(board_pin):
    load_lookup_table()
    for record in gpio_lookup:
        if record["Board_Pin"] == board_pin:
            logger.info(f"Using gpio record: {record}")
            chip = gpiod.chip(record["Chip"])
            return chip.get_line(record["Offset"])
    return None






