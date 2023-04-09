import sys
import unittest
#to run:
#python -m unittest test_GPIO

class GPIOTest(unittest.TestCase):

    def test_test(self):
        self.assertTrue(True)

    # def test_lgpio:
    #     RHGPIO_S32ID_PIN = 25
    #     import lgpio as GPIO
    #     chip = GPIO.gpiochip_open(0)
    #     GPIO.gpio_claim_input(chip, RHGPIO_S32ID_PIN, GPIO.SET_PULL_UP)
    #     time.sleep(0.05)
    #     S32BPillBoardFlag = not GPIO.gpio_read(chip, RHGPIO_S32ID_PIN)
    #     GPIO.gpio_claim_input(chip, RHGPIO_S32ID_PIN)
    #     self.assertTrue(S32BPillBoardFlag)

    def test_gpiod(self):
        #this works for both official bindings and this loliot library.
        # https://wiki.loliot.net/docs/lang/python/libraries/gpiod/python-gpiod-about
        # and
        # https://git.kernel.org/pub/scm/libs/libgpiod/libgpiod.git/

        import gpiod
        chip = gpiod.chip('gpiochip1')
        line = chip.find_line('7J1 Header Pin22')
        line_config = gpiod.line_request()
        line_config.consumer = "TEST"
        line_config.request_type = gpiod.line_request.DIRECTION_INPUT
        line_config.flags = line_config.FLAG_BIAS_PULL_UP
        line.request(line_config, 1)
        s32_b_pill_board_flag = not line.get_value()
        self.assertTrue(s32_b_pill_board_flag)
        line.release()


