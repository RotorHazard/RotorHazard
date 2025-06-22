# Utility class for Raspberry Pi GPIO functions

import time

try:
    Real_GPIO_Zero_flag = False
    Real_RPi_GPIO_flag = False
    try:
        import lgpio     #pylint: disable=import-error
        import gpiozero  #pylint: disable=import-error
        Real_GPIO_Zero_flag = True
    except:
        pass
    try:
        import RPi.GPIO as GPIO  #pylint: disable=import-error
        Real_RPi_GPIO_flag = True
    except:
        pass
    try:
        if Real_GPIO_Zero_flag and Real_RPi_GPIO_flag:
            with open("/proc/device-tree/model", 'r') as fileHnd:
                _modelStr = fileHnd.read()
            if _modelStr.startswith("Raspberry Pi ") and int(_modelStr[13:15]) < 5:
                Real_GPIO_Zero_flag = False  # for Pi 3/4 prefer Rpi.GPIO (works better with shutdown button)
            else:
                Real_RPi_GPIO_flag = False
    except:
        Real_RPi_GPIO_flag = False
except:  # if failure then assume no hardware GPIO available
    Real_GPIO_Zero_flag = False
    Real_RPi_GPIO_flag = False

if not Real_RPi_GPIO_flag:
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
