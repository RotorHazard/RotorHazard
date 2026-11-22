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
        if chip_num not in self.chip_info:
            raise RuntimeError("can not open gpiochip")
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
        self.reset_rp1_search()
        self.gpiozero_chip_patcher = mock.patch.object(RH_GPIO, '_get_gpiozero_chip_num', return_value=4)
        self.gpiozero_chip_mock = self.gpiozero_chip_patcher.start()

    @staticmethod
    def reset_rp1_search():
        RH_GPIO._rp1_gpiochip_num = RH_GPIO._RP1_NOT_CHECKED  #pylint: disable=protected-access
        RH_GPIO._rp1_search_errors.clear()  #pylint: disable=protected-access

    def tearDown(self):
        self.gpiozero_chip_patcher.stop()
        self.reset_rp1_search()
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

    def test_rp1_gpiochip_search_runs_once(self):
        with mock.patch.object(RH_GPIO.glob, 'glob',
                               return_value=['/dev/gpiochip11', '/dev/gpiochip15']) as glob_mock:
            self.assertEqual(RH_GPIO._get_rp1_gpiochip_num(), 15)  #pylint: disable=protected-access
            self.assertEqual(RH_GPIO._get_rp1_gpiochip_num(), 15)  #pylint: disable=protected-access
        self.assertEqual(glob_mock.call_count, 1)

    def test_gpio_type_str_shows_rp1_chip(self):
        with mock.patch.object(RH_GPIO.glob, 'glob',
                               return_value=['/dev/gpiochip11', '/dev/gpiochip15']):
            self.assertEqual(RH_GPIO.get_GPIO_type_str(), "True (lgpio gpiochip15)")

    def test_gpiozero_used_when_its_chip_is_rp1(self):
        self.fake_lgpio.chip_info[4] = [0, 54, 'gpiochip4', 'pinctrl-rp1']
        with mock.patch.object(RH_GPIO.glob, 'glob',
                               return_value=['/dev/gpiochip4', '/dev/gpiochip15']) as glob_mock:
            self.assertIsNone(RH_GPIO._get_rp1_gpiochip_num())  #pylint: disable=protected-access
            self.assertEqual(RH_GPIO.get_GPIO_type_str(), "True (GPIO Zero)")
        glob_mock.assert_not_called()
        self.assertEqual(self.fake_lgpio.closed, [4])

    def test_prefer_flag_uses_lgpio_when_gpiozero_chip_is_rp1(self):
        self.fake_lgpio.chip_info[4] = [0, 54, 'gpiochip4', 'pinctrl-rp1']
        with mock.patch.object(RH_GPIO, 'PREFER_RP1_LGPIO_FLAG', True), \
             mock.patch.object(RH_GPIO.glob, 'glob',
                               return_value=['/dev/gpiochip4', '/dev/gpiochip15']):
            self.assertEqual(RH_GPIO._get_rp1_gpiochip_num(), 4)  #pylint: disable=protected-access
            self.assertEqual(RH_GPIO.get_GPIO_type_str(), "True (lgpio gpiochip4)")
        self.gpiozero_chip_mock.assert_not_called()

    def test_rp1_search_runs_when_gpiozero_chip_unknown(self):
        self.gpiozero_chip_mock.side_effect = RuntimeError("no revision")
        with mock.patch.object(RH_GPIO.glob, 'glob',
                               return_value=['/dev/gpiochip11', '/dev/gpiochip15']):
            self.assertEqual(RH_GPIO._get_rp1_gpiochip_num(), 15)  #pylint: disable=protected-access

    def test_gpio_type_str_shows_search_errors(self):
        self.fake_lgpio.chip_info.clear()
        with mock.patch.object(RH_GPIO.glob, 'glob', return_value=['/dev/gpiochip0']):
            self.assertEqual(RH_GPIO.get_GPIO_type_str(),
                             "True (GPIO Zero; gpiochip errors: /dev/gpiochip4: can not open gpiochip; "
                             "/dev/gpiochip0: can not open gpiochip)")

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
