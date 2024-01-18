# Utility class for Raspberry Pi GPIO functions

import time

try:
    import lgpio
    import gpiozero
    Real_GPIO_Zero_flag = True
    Real_RPi_GPIO_flag = False
    GPIO = {}
except ImportError:
    try:
        import RPi.GPIO as GPIO
        Real_GPIO_Zero_flag = False
        Real_RPi_GPIO_flag = True
    except ImportError:
        Real_GPIO_Zero_flag = False
        Real_RPi_GPIO_flag = False
        GPIO = {}
except:  # need extra exception catch for Travis CI tests
    Real_GPIO_Zero_flag = False
    Real_RPi_GPIO_flag = False
    GPIO = {}

# setup these GPIO constants so they can be referenced using RH_GPIO
BOARD = getattr(GPIO, "BOARD", 0)
BCM =  getattr(GPIO, "BCM", 1)
IN =  getattr(GPIO, "IN", 0)
OUT =  getattr(GPIO, "OUT", 1)
UNKNOWN =  getattr(GPIO, "UNKNOWN", -1)
PUD_DOWN =  getattr(GPIO, "PUD_DOWN", 0)
PUD_UP =  getattr(GPIO, "PUD_UP", 1)
PUD_OFF =  getattr(GPIO, "PUD_OFF", -1)
LOW =  getattr(GPIO, "LOW", 0)
HIGH =  getattr(GPIO, "HIGH", 1)
FALLING =  getattr(GPIO, "FALLING", 0)
RISING =  getattr(GPIO, "RISING", 1)
BOTH =  getattr(GPIO, "BOTH", 2)

Input_devices_dict = {}
Output_devices_dict = {}

# Returns True if real hardware GPIO detected
def is_real_hw_GPIO():
    return Real_GPIO_Zero_flag or Real_RPi_GPIO_flag

# Returns a string indicating the type of GPIO detected
def get_GPIO_type_str():
    if Real_GPIO_Zero_flag:
        return "True (GPIO Zero)"
    if Real_RPi_GPIO_flag:
        return "True (RPi.GPIO)"
    return "False"

# Returns True if given input pin is tied low (to GND)
def check_input_tied_low(pin_id):
    ret_flag = False
    if Real_GPIO_Zero_flag:
        input_dev = gpiozero.InputDevice(pin_id, pull_up=True)
        time.sleep(0.05)
        ret_flag = input_dev.is_active
        input_dev.close()
    elif Real_RPi_GPIO_flag:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin_id, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        time.sleep(0.05)
        ret_flag = not GPIO.input(pin_id)
        GPIO.setup(pin_id, GPIO.IN)
    return ret_flag

# Set up channel as an input or an output
def setup(channel, mode, *args, **kwargs):
    if Real_GPIO_Zero_flag:
        if mode == OUT:
            if Output_devices_dict.get(channel):
                Output_devices_dict[channel].close()
                del Output_devices_dict[channel]
            if Input_devices_dict.get(channel):
                Input_devices_dict[channel].close()
                del Input_devices_dict[channel]
            Output_devices_dict[channel] = gpiozero.OutputDevice(channel)
        else:
            if Input_devices_dict.get(channel):
                Input_devices_dict[channel].close()
                del Input_devices_dict[channel]
            if Output_devices_dict.get(channel):
                Output_devices_dict[channel].close()
                del Output_devices_dict[channel]
            Input_devices_dict[channel] = gpiozero.InputDevice(channel, \
                                              pull_up=(kwargs.get("pull_up_down")==PUD_UP))
    elif Real_RPi_GPIO_flag:
        GPIO.setup(channel, mode, *args, **kwargs)

# Performs cleanup action on the given channel
def close_channel(channel):
    if Real_GPIO_Zero_flag:
        if Input_devices_dict.get(channel):
            Input_devices_dict[channel].close()
            del Input_devices_dict[channel]
        if Output_devices_dict.get(channel):
            Output_devices_dict[channel].close()
            del Output_devices_dict[channel]

# Set numbering mode for IO pins
def setmode(mode):
    if Real_RPi_GPIO_flag:
        GPIO.setmode(mode)

# Read the value of a GPIO pin
def input(channel):  #pylint: disable=redefined-builtin
    if Real_GPIO_Zero_flag:
        input_dev = Input_devices_dict.get(channel)
        if input_dev:
            return LOW if input_dev.is_active else HIGH
        return HIGH
    elif Real_RPi_GPIO_flag:
        return GPIO.input(channel)
    return HIGH

# Set output state of a GPIO pin
def output(channel, state):
    if Real_GPIO_Zero_flag:
        output_dev = Output_devices_dict.get(channel)
        if output_dev:
            if state == HIGH:
                output_dev.on()
            else:
                output_dev.off()
        else:
            return UNKNOWN
    elif Real_RPi_GPIO_flag:
        return GPIO.output(channel, state)
    return LOW
