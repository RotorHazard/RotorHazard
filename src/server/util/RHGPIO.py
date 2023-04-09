# Utility class for Raspberry Pi GPIO functions

import time
from sbcUtil import *

if is_raspberry():
    RealGPIOFlag = True
if is_libre():

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
    if is_raspberry():
        import RPi.GPIO as GPIO
        RHGPIO_S32ID_PIN = 25  # input is tied low on S32_BPill PCB.  This is pin # 22 which is GPIO25
        # The GPIO.BOARD option specifies that you are referring to the pins by the number of the pin on the plug - i.e the numbers printed on the board (e.g. P1) and in the middle of the diagrams below.
        # The GPIO.BCM option means that you are referring to the pins by the "Broadcom SOC channel" number, these are the numbers after "GPIO" in the green rectangles around the outside of the below diagrams:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RHGPIO_S32ID_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        time.sleep(0.05)
        s32_blue_pill_board_flag = not GPIO.input(RHGPIO_S32ID_PIN)
        GPIO.setup(RHGPIO_S32ID_PIN, GPIO.IN)
    elif is_libre():
        import gpiod
        chip = gpiod.chip('gpiochip1')
        #potato pin22 aka GPIO 25 is on the 2nd gpio chip, 7J1 header.
        line = chip.find_line('7J1 Header Pin22')
        line_config = gpiod.line_request()
        line_config.consumer = "Rotorhazard"
        line_config.request_type = gpiod.line_request.DIRECTION_INPUT
        line_config.flags = line_config.FLAG_BIAS_PULL_UP
        line.request(line_config, 1)
        s32_blue_pill_board_flag = not line.get_value()
        if s32_blue_pill_board_flag:
            set_blue_pill_board_flag()
        line.release()
