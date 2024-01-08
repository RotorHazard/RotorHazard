# Utility class for Raspberry Pi GPIO functions

import time
import sys

sys.path.append('util')  # needed at runtime to find FakeRPiGPIO module

try:
    import RPi.GPIO as GPIO
    Real_RPi_GPIO_flag = True
except ImportError:
    import FakeRPiGPIO as GPIO
    Real_RPi_GPIO_flag = False
except:  # need extra exception catch for Travis CI tests
    import FakeRPiGPIO as GPIO
    Real_RPi_GPIO_flag = False
# if RPi.GPIO not available then use FakeRiGPIO from https://github.com/sn4k3/FakeRPi

# alias these GPIO constants so they can be referenced using RHGPIO
BOARD = GPIO.BOARD
BCM = GPIO.BCM
IN = GPIO.IN
OUT = GPIO.OUT
SPI = GPIO.SPI
I2C = GPIO.I2C
HARD_PWM = GPIO.HARD_PWM
SERIAL = GPIO.SERIAL
UNKNOWN = GPIO.UNKNOWN
PUD_DOWN = GPIO.PUD_DOWN
PUD_UP = GPIO.PUD_UP
PUD_OFF = GPIO.PUD_OFF
LOW = GPIO.LOW
HIGH = GPIO.HIGH
FALLING = GPIO.FALLING
RISING = GPIO.RISING
BOTH = GPIO.BOTH


# Return True if real hardware GPIO detected
def is_real_RPi_GPIO():
    return Real_RPi_GPIO_flag

# Returns True if given input pin is tied low (to GND)
def check_input_tied_low(pin_id):
    ret_flag = False
    if Real_RPi_GPIO_flag:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin_id, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        time.sleep(0.05)
        ret_flag = not GPIO.input(pin_id)
        GPIO.setup(pin_id, GPIO.IN)
    return ret_flag

# Set up channel as an input or an output
def setup(channel, mode, *args, **kwargs):
    if Real_RPi_GPIO_flag:
        GPIO.setup(channel, mode, *args, **kwargs)
    else:
        pass

# Read the value of a GPIO pin
def input(channel):  #pylint: disable=redefined-builtin
    if Real_RPi_GPIO_flag:
        return GPIO.input(channel)
    return LOW
