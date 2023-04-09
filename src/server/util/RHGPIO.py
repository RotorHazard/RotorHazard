# Utility class for Raspberry Pi GPIO functions

# resources:
# https://www.ics.com/blog/gpio-programming-exploring-libgpiod-library
# https://lloydrochester.com/post/hardware/libgpiod-intro-rpi/

import time
from util.sbcUtil import *
import gpiod

HIGH = 1
LOW = 0
UNKNOWN = -1

if is_raspberry() or is_libre():
    RealGPIOFlag = True
else:
    RealGPIOFlag = False

global s32_blue_pill_board_flag
s32_blue_pill_board_flag = None
def is_real_gpio():
    return RealGPIOFlag


def is_blue_pill_board():

    global s32_blue_pill_board_flag

    if s32_blue_pill_board_flag is None:
        if RealGPIOFlag:
            line = None
            if is_raspberry():
                #on raspberry the 40pin header on is on chip 0
                #and we want to use GPIO25
                line = get_line(25)
            elif is_libre():
                line = get_line(22)
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


def get_line(pin_number) -> gpiod.line:
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

def get_line_by_name(line_name) -> gpiod.line:
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
