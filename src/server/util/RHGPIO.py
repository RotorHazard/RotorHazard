# Utility class for Raspberry Pi GPIO functions

# resources:
# https://www.ics.com/blog/gpio-programming-exploring-libgpiod-library
# https://lloydrochester.com/post/hardware/libgpiod-intro-rpi/

import time
from sbcUtil import *
import gpiod

if is_raspberry() or is_libre():
    RealGPIOFlag = True
else:
    RealGPIOFlag = False

s32_blue_pill_board_flag = False


def is_real_gpio():
    return RealGPIOFlag


def is_blue_pill_board():
    return s32_blue_pill_board_flag


def set_blue_pill_board_flag():
    global s32_blue_pill_board_flag
    s32_blue_pill_board_flag = True


# if input tied low then set flag identifying S32_BPill board
if RealGPIOFlag:
    chip = None
    line = None
    if is_raspberry():
        #on raspberry the 40pin header on is on chip 0
        #and we want to use GPIO25
        chip = gpiod.chip('gpiochip0')
        line = chip.find_line('GPIO25')
    if is_libre():
        chip = gpiod.chip('gpiochip1')
        line = chip.find_line('7J1 Header Pin22')
    if chip and line:
        line_config = gpiod.line_request()
        line_config.consumer = "RotorHazard"
        line_config.request_type = gpiod.line_request.DIRECTION_INPUT
        line_config.flags = line_config.FLAG_BIAS_PULL_UP
        line.request(line_config, 1)
        time.sleep(0.05)
        s32_b_pill_board_flag = not line.get_value()
        line.release()
        chip.close()
