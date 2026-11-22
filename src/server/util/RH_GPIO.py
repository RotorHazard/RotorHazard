# Utility class for Raspberry Pi GPIO functions

import glob
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

# Set True to use lgpio directly on the Pi 5 RP1 gpiochip even when GPIO Zero can access it
PREFER_RP1_LGPIO_FLAG = False

_RP1_NOT_CHECKED = -1
_rp1_gpiochip_num = _RP1_NOT_CHECKED
_rp1_search_errors = []

# Returns the gpiochip number that the GPIO Zero lgpio pin factory opens
def _get_gpiozero_chip_num():
    from gpiozero.pins.local import get_pi_revision  #pylint: disable=import-error,import-outside-toplevel
    return 4 if (get_pi_revision() & 0xff0) >> 4 == 0x17 else 0

# Returns True if the given gpiochip is the Pi 5 RP1 controller
def _is_rp1_gpiochip(chip_num):
    gpio_handle = None
    try:
        gpio_handle = lgpio.gpiochip_open(chip_num)
        chip_info = lgpio.gpio_get_chip_info(gpio_handle)
        return len(chip_info) >= 4 and chip_info[3] == "pinctrl-rp1"
    except Exception as ex:
        _rp1_search_errors.append("/dev/gpiochip{}: {}".format(chip_num, ex))
        return False
    finally:
        if gpio_handle is not None:
            lgpio.gpiochip_close(gpio_handle)

# Returns the gpiochip number for the Pi 5 RP1 controller if GPIO Zero does not open it
# (or if PREFER_RP1_LGPIO_FLAG is set), or None.
# Newer kernels may assign it a dynamic number instead of gpiochip0/gpiochip4.
def _find_rp1_gpiochip_num():
    gpiozero_chip_num = None
    if not PREFER_RP1_LGPIO_FLAG:
        try:
            gpiozero_chip_num = _get_gpiozero_chip_num()
        except Exception as ex:
            _rp1_search_errors.append("GPIO Zero chip: {}".format(ex))
        if gpiozero_chip_num is not None and _is_rp1_gpiochip(gpiozero_chip_num):
            return None
    for chip_path in glob.glob("/dev/gpiochip*"):
        try:
            chip_num = int(chip_path.rsplit("gpiochip", 1)[1])
        except ValueError:
            continue
        if chip_num != gpiozero_chip_num and _is_rp1_gpiochip(chip_num):
            return chip_num
    return None

# Returns the RP1 gpiochip number to use via lgpio, or None to use GPIO Zero; searches on the first call only
def _get_rp1_gpiochip_num():
    global _rp1_gpiochip_num
    if _rp1_gpiochip_num == _RP1_NOT_CHECKED:
        _rp1_gpiochip_num = _find_rp1_gpiochip_num()
    return _rp1_gpiochip_num

class _LgpioInputDevice:
    """Minimal gpiozero-compatible input using a selected gpiochip."""
    def __init__(self, chip_num, channel, pull_up=False):
        self._gpio_handle = lgpio.gpiochip_open(chip_num)
        self._channel = channel
        self._active_low = pull_up
        try:
            pull_flag = lgpio.SET_PULL_UP if pull_up else lgpio.SET_PULL_DOWN
            lgpio.gpio_claim_input(self._gpio_handle, channel, pull_flag)
        except Exception:
            lgpio.gpiochip_close(self._gpio_handle)
            self._gpio_handle = None
            raise

    @property
    def is_active(self):
        """Returns True when the configured active level is present."""
        level = lgpio.gpio_read(self._gpio_handle, self._channel)
        return not level if self._active_low else bool(level)

    def close(self):
        """Releases the GPIO line and gpiochip handle."""
        if self._gpio_handle is not None:
            try:
                lgpio.gpio_free(self._gpio_handle, self._channel)
            finally:
                lgpio.gpiochip_close(self._gpio_handle)
                self._gpio_handle = None

class _LgpioOutputDevice:
    """Minimal gpiozero-compatible output using a selected gpiochip."""
    def __init__(self, chip_num, channel):
        self._gpio_handle = lgpio.gpiochip_open(chip_num)
        self._channel = channel
        try:
            lgpio.gpio_claim_output(self._gpio_handle, channel, LOW)
        except Exception:
            lgpio.gpiochip_close(self._gpio_handle)
            self._gpio_handle = None
            raise

    def on(self):
        """Sets the GPIO line high."""
        lgpio.gpio_write(self._gpio_handle, self._channel, HIGH)

    def off(self):
        """Sets the GPIO line low."""
        lgpio.gpio_write(self._gpio_handle, self._channel, LOW)

    def close(self):
        """Releases the GPIO line and gpiochip handle."""
        if self._gpio_handle is not None:
            try:
                lgpio.gpio_free(self._gpio_handle, self._channel)
            finally:
                lgpio.gpiochip_close(self._gpio_handle)
                self._gpio_handle = None

# Returns True if real hardware GPIO detected
def is_real_hw_GPIO():
    return Real_GPIO_Zero_flag or Real_RPi_GPIO_flag

# Returns a string indicating the type of GPIO detected
def get_GPIO_type_str():
    if Real_GPIO_Zero_flag:
        rp1_chip_num = _get_rp1_gpiochip_num()
        if rp1_chip_num is not None:
            return "True (lgpio gpiochip{})".format(rp1_chip_num)
        if _rp1_search_errors:
            return "True (GPIO Zero; gpiochip errors: {})".format("; ".join(_rp1_search_errors))
        return "True (GPIO Zero)"
    if Real_RPi_GPIO_flag:
        return "True (RPi.GPIO)"
    return "False"

# Returns True if given input pin is tied low (to GND)
def check_input_tied_low(pin_id):
    ret_flag = False
    if Real_GPIO_Zero_flag:
        rp1_chip_num = _get_rp1_gpiochip_num()
        input_dev = _LgpioInputDevice(rp1_chip_num, pin_id, pull_up=True) \
                    if rp1_chip_num is not None \
                    else gpiozero.InputDevice(pin_id, pull_up=True)
        try:
            time.sleep(0.05)
            ret_flag = input_dev.is_active
        finally:
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
        rp1_chip_num = _get_rp1_gpiochip_num()
        if mode == OUT:
            if Output_devices_dict.get(channel):
                Output_devices_dict[channel].close()
                del Output_devices_dict[channel]
            if Input_devices_dict.get(channel):
                Input_devices_dict[channel].close()
                del Input_devices_dict[channel]
            Output_devices_dict[channel] = _LgpioOutputDevice(rp1_chip_num, channel) \
                                           if rp1_chip_num is not None \
                                           else gpiozero.OutputDevice(channel)
        else:
            if Input_devices_dict.get(channel):
                Input_devices_dict[channel].close()
                del Input_devices_dict[channel]
            if Output_devices_dict.get(channel):
                Output_devices_dict[channel].close()
                del Output_devices_dict[channel]
            pull_up = kwargs.get("pull_up_down") == PUD_UP
            Input_devices_dict[channel] = _LgpioInputDevice(rp1_chip_num, channel, pull_up) \
                                          if rp1_chip_num is not None \
                                          else gpiozero.InputDevice(channel, pull_up=pull_up)
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
