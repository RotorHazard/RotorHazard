#from .PWM import PWM as PWMClass

__author__ = 'Tiago'
__documentation__ = 'http://sourceforge.net/p/raspberry-gpio-python/wiki/Examples/'

RPI_REVISION = 1
VERSION = 1

BOARD = 0
BCM = 1

IN = 0
OUT = 1

INPUT = 0
OUTPUT = 1
SPI = 2
I2C = 3
HARD_PWM = 4
SERIAL = 5
UNKNOWN = -1

PUD_DOWN = 0
PUD_UP = 1
PUD_OFF = -1

LOW = 0
HIGH = 1

FALLING = 0
RISING = 1
BOTH = 2

_setup_mode = BOARD
_warnings = False


def setmode(mode):
    """
    There are two ways of numbering the IO pins on a Raspberry Pi within RPi.GPIO. The first is using the BOARD numbering system. This refers to the pin numbers on the P1 header of the Raspberry Pi board. The advantage of using this numbering system is that your hardware will always work, regardless of the board revision of the RPi. You will not need to rewire your connector or change your code.
    The second numbering system is the BCM numbers. This is a lower level way of working - it refers to the channel numbers on the Broadcom SOC. You have to always work with a diagram of which channel number goes to which pin on the RPi board. Your script could break between revisions of Raspberry Pi boards.
    To specify which you are using using (mandatory):
    :param mode:
    :return:
    """
    _setup_mode = mode


def setwarnings(mode):
    """
    It is possible that you have more than one script/circuit on the GPIO of your Raspberry Pi.
    As a result of this, if RPi.GPIO detects that a pin has been configured to something other than the default (input),
    you get a warning when you try to configure a script. To disable these warnings:
    :param mode:
    :return:
    """
    _warnings = mode


def setup(channel, mode, initial=None, pull_up_down=None):
    """
    You need to set up every channel you are using as an input or an output. To configure a channel as an input:
    :param channel:
    :param mode:
    :param initial:
    :param pull_up_down:
    :return:
    """
    pass  #pylint: disable=unnecessary-pass


def gpio_function(pin):
    """
    Shows the function of a GPIO channel.
    will return a value from: GPIO.INPUT, GPIO.OUTPUT, GPIO.SPI, GPIO.I2C, GPIO.HARD_PWM, GPIO.SERIAL, GPIO.UNKNOWN
    :param pin:
    :return: GPIO.INPUT, GPIO.OUTPUT, GPIO.SPI, GPIO.I2C, GPIO.HARD_PWM, GPIO.SERIAL, GPIO.UNKNOWN
    """
    return None


def input(channel):  #pylint: disable=redefined-builtin
    """
    To read the value of a GPIO pin:
    :param channel:
    :return:
    """
    return LOW


def output(channel, state):
    """
    To set the output state of a GPIO pin:
    :param channel:
    :return:
    """
    return LOW


def PWM(channel, frequency):
    """
    :param channel:
    :param frequency:
    To create a PWM instance:
    :return:
    """
#    return PWMClass()
    return None


def cleanup(channel=None):
    """
    At the end any program, it is good practice to clean up any resources you might have used. This is no different with RPi.GPIO.
    By returning all channels you have used back to inputs with no pull up/down, you can avoid accidental damage to your RPi by shorting out the pins.
    Note that this will only clean up GPIO channels that your script has used.
    :param channel: It is possible that you only want to clean up one channel, leaving some set up when your program exits
    :return:
    """
    pass  #pylint: disable=unnecessary-pass


def wait_for_edge(channel, edge_type):
    """
    The wait_for_edge() function is designed to block execution of your program until an edge is detected.
    :param channel:
    :param edge_type:
    :return:
    """
    pass  #pylint: disable=unnecessary-pass


def add_event_detect(channel, edge_type, callback=None, bouncetime=0):
    """
    The event_detected() function is designed to be used in a loop with other things, but unlike polling it is not going to miss the change in state of an input while the CPU is busy working on other things.
    This could be useful when using something like Pygame or PyQt where there is a main loop listening and responding to GUI events in a timely basis.
    :param channel:
    :param edge_type:
    :return:
    """
    pass  #pylint: disable=unnecessary-pass


def add_event_callback(channel, callback, bouncetime=0):
    pass


def remove_event_detect(channel):
    """
    If for some reason, your program no longer wishes to detect edge events, it is possible to stop them
    :param channel:
    :return:
    """
    pass  #pylint: disable=unnecessary-pass
