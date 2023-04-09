# Utility class for Raspberry Pi GPIO functions

import time

try:
    import RPi.GPIO as GPIO
    RealRPiGPIOFlag = True
    UseLGPIO = False
except ImportError:
    try:
        import lgpio as GPIO
        RealRPiGPIOFlag = True
        UseLGPIO = True
    except ImportError:
        import util.FakeRPiGPIO as GPIO
        RealRPiGPIOFlag = False
        UseLGPIO = False
except:  # need extra exception catch for Travis CI tests
    import util.FakeRPiGPIO as GPIO
    RealRPiGPIOFlag = False
    UseLGPIO = False
# if RPi.GPIO not available then use FakeRiGPIO from https://github.com/sn4k3/FakeRPi

RHGPIO_S32ID_PIN = 25  # input is tied low on S32_BPill PCB

S32BPillBoardFlag = False

def isRealRPiGPIO():
    return RealRPiGPIOFlag

def isS32BPillBoard():
    return S32BPillBoardFlag

def setS32BPillBoardFlag():
    global S32BPillBoardFlag
    S32BPillBoardFlag = True


# if input tied low then set flag identifying S32_BPill board
if RealRPiGPIOFlag:
    if UseLGPIO:
        chip = GPIO.gpiochip_open(0)
        GPIO.gpio_claim_input(chip, RHGPIO_S32ID_PIN, GPIO.SET_PULL_UP)
        time.sleep(0.05)
        S32BPillBoardFlag = not GPIO.gpio_read(chip, RHGPIO_S32ID_PIN)
        GPIO.gpio_claim_input(chip, RHGPIO_S32ID_PIN)


    else:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RHGPIO_S32ID_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        time.sleep(0.05)
        S32BPillBoardFlag = not GPIO.input(RHGPIO_S32ID_PIN)
        GPIO.setup(RHGPIO_S32ID_PIN, GPIO.IN)
