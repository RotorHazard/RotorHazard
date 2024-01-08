# Utility class for Raspberry Pi GPIO functions

import time

try:
    import RPi.GPIO as GPIO
    Real_RPi_GPIO_flag = True
except ImportError:
    import util.FakeRPiGPIO as GPIO
    Real_RPi_GPIO_flag = False
except:  # need extra exception catch for Travis CI tests
    import util.FakeRPiGPIO as GPIO
    Real_RPi_GPIO_flag = False
# if RPi.GPIO not available then use FakeRiGPIO from https://github.com/sn4k3/FakeRPi


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
