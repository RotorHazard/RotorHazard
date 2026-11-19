'''python -m unittest discover'''
import os
import sys
import unittest
from unittest import mock

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                             'server', 'util'))

import RH_GPIO  #pylint: disable=import-error


class FakeLgpio:
    SET_PULL_UP = 32
    SET_PULL_DOWN = 64

    def __init__(self):
        self.chip_info = {
            11: [0, 15, 'gpiochip11', 'gpio-brcmstb'],
            15: [0, 54, 'gpiochip15', 'pinctrl-rp1'],
        }
        self.levels = {}
        self.claimed_inputs = []
        self.claimed_outputs = []
        self.writes = []
        self.freed = []
        self.closed = []

    def gpiochip_open(self, chip_num):
        return chip_num

    def gpio_get_chip_info(self, gpio_handle):
        return self.chip_info[gpio_handle]

    def gpiochip_close(self, gpio_handle):
        self.closed.append(gpio_handle)

    def gpio_claim_input(self, gpio_handle, channel, pull_flag):
        self.claimed_inputs.append((gpio_handle, channel, pull_flag))

    def gpio_claim_output(self, gpio_handle, channel, level):
        self.claimed_outputs.append((gpio_handle, channel, level))
        self.levels[channel] = level

    def gpio_read(self, gpio_handle, channel):
        del gpio_handle
        return self.levels[channel]

    def gpio_write(self, gpio_handle, channel, level):
        self.writes.append((gpio_handle, channel, level))
        self.levels[channel] = level

    def gpio_free(self, gpio_handle, channel):
        self.freed.append((gpio_handle, channel))


class RHGPIOTest(unittest.TestCase):
    def setUp(self):
        self.original_lgpio = getattr(RH_GPIO, 'lgpio', None)
        self.original_gpio_zero_flag = RH_GPIO.Real_GPIO_Zero_flag
        self.fake_lgpio = FakeLgpio()
        RH_GPIO.lgpio = self.fake_lgpio
        RH_GPIO.Real_GPIO_Zero_flag = True
        RH_GPIO.Input_devices_dict.clear()
        RH_GPIO.Output_devices_dict.clear()

    def tearDown(self):
        for channel in list(RH_GPIO.Input_devices_dict):
            RH_GPIO.close_channel(channel)
        for channel in list(RH_GPIO.Output_devices_dict):
            RH_GPIO.close_channel(channel)
        RH_GPIO.Real_GPIO_Zero_flag = self.original_gpio_zero_flag
        if self.original_lgpio is None:
            del RH_GPIO.lgpio
        else:
            RH_GPIO.lgpio = self.original_lgpio

    def test_find_rp1_gpiochip_by_label(self):
        with mock.patch.object(RH_GPIO.glob, 'glob',
                               return_value=['/dev/gpiochip11', '/dev/gpiochip15']):
            self.assertEqual(RH_GPIO._get_rp1_gpiochip_num(), 15)  #pylint: disable=protected-access
        self.assertEqual(self.fake_lgpio.closed, [11, 15])

    def test_check_input_tied_low_uses_rp1_chip(self):
        self.fake_lgpio.levels[25] = RH_GPIO.LOW
        with mock.patch.object(RH_GPIO, '_get_rp1_gpiochip_num', return_value=15), \
             mock.patch.object(RH_GPIO.time, 'sleep'):
            self.assertTrue(RH_GPIO.check_input_tied_low(25))
        self.assertEqual(self.fake_lgpio.claimed_inputs,
                         [(15, 25, self.fake_lgpio.SET_PULL_UP)])
        self.assertEqual(self.fake_lgpio.freed, [(15, 25)])

    def test_setup_and_read_rp1_input(self):
        self.fake_lgpio.levels[19] = RH_GPIO.HIGH
        with mock.patch.object(RH_GPIO, '_get_rp1_gpiochip_num', return_value=15):
            RH_GPIO.setup(19, RH_GPIO.IN, pull_up_down=RH_GPIO.PUD_UP)
        self.assertEqual(RH_GPIO.input(19), RH_GPIO.HIGH)
        self.fake_lgpio.levels[19] = RH_GPIO.LOW
        self.assertEqual(RH_GPIO.input(19), RH_GPIO.LOW)
        RH_GPIO.close_channel(19)
        self.assertEqual(self.fake_lgpio.freed, [(15, 19)])

    def test_setup_and_write_rp1_output(self):
        with mock.patch.object(RH_GPIO, '_get_rp1_gpiochip_num', return_value=15):
            RH_GPIO.setup(17, RH_GPIO.OUT)
        RH_GPIO.output(17, RH_GPIO.HIGH)
        RH_GPIO.output(17, RH_GPIO.LOW)
        self.assertEqual(self.fake_lgpio.claimed_outputs, [(15, 17, RH_GPIO.LOW)])
        self.assertEqual(self.fake_lgpio.writes,
                         [(15, 17, RH_GPIO.HIGH), (15, 17, RH_GPIO.LOW)])
        RH_GPIO.close_channel(17)
        self.assertEqual(self.fake_lgpio.freed, [(15, 17)])


if __name__ == '__main__':
    unittest.main()
