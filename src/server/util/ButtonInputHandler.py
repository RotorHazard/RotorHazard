# ButtonInputHandler:  Handler for a button connected to a GPIO input pin

import sys
sys.path.append('util')  # needed at runtime to find RH_GPIO module

import RH_GPIO

class ButtonInputHandler:
    """ Handler for a button connected to a GPIO input pin """
    def __init__(self, gpioPinNum, logger, buttonPressedCallbackFn=None, \
                 buttonReleasedCallbackFn=None, buttonLongPressCallbackFn=None, \
                 buttonLongPressDelayMs=3000, startEnabledFlag=True):
        self.gpioPinNum = gpioPinNum
        self.logger = logger
        self.buttonPressedCallbackFn = buttonPressedCallbackFn if buttonPressedCallbackFn \
                                                               else self.noop
        self.buttonReleasedCallbackFn = buttonReleasedCallbackFn if buttonReleasedCallbackFn \
                                                                 else self.noop
        self.buttonLongPressCallbackFn = buttonLongPressCallbackFn if buttonLongPressCallbackFn \
                                                                   else self.noop
        self.buttonLongPressDelayMs = buttonLongPressDelayMs
        self.longPressReachedFlag = False
        self.lastInputLevel = RH_GPIO.UNKNOWN
        self.pressedStartTimeSecs = 0
        self.enabledFlag = startEnabledFlag
        self.errorLoggedCount = 0
        try:
            RH_GPIO.setup(gpioPinNum, RH_GPIO.IN, pull_up_down=RH_GPIO.PUD_UP)
        except Exception as ex:
            if str(ex).find("GPIO busy") > 0:
                logger.error("Unable to access GPIO pin {} in ButtonInputHandler setup; may need to remove line \"dtoverlay=gpio-shutdown,gpio_pin={}\" from 'boot' config file ".\
                             format(gpioPinNum, gpioPinNum))
            else:
                logger.exception("Exception error in ButtonInputHandler setup")

    # function called on a periodic basis to poll the input and invoke callbacks
    # returns True if button currently pressed or long press detected
    def pollProcessInput(self, nowTimeSecs):
        try:
            if self.enabledFlag:
                inLvl = RH_GPIO.input(self.gpioPinNum)
                if self.lastInputLevel == RH_GPIO.HIGH:
                    if inLvl == RH_GPIO.LOW:  # new button press detected
                        self.pressedStartTimeSecs = nowTimeSecs
                        self.longPressReachedFlag = False
                        self.buttonPressedCallbackFn()
                elif self.lastInputLevel == RH_GPIO.LOW:
                    if inLvl == RH_GPIO.LOW:  # button long-press detected
                        if self.pressedStartTimeSecs > 0 and \
                                    (nowTimeSecs - self.pressedStartTimeSecs) * 1000 > \
                                    self.buttonLongPressDelayMs:
                            if not self.longPressReachedFlag:
                                self.longPressReachedFlag = True
                                self.buttonLongPressCallbackFn()
                    else:
                        self.buttonReleasedCallbackFn(self.longPressReachedFlag)
                self.lastInputLevel = inLvl
                return (inLvl == RH_GPIO.LOW) or self.longPressReachedFlag
        except:
            self.errorLoggedCount += 1
            # log the first ten, but then only 1 per 100 after that
            if self.errorLoggedCount <= 10 or self.errorLoggedCount % 100 == 0:
                self.logger.exception("Exception error in ButtonInputHandler 'pollProcessInput()'")
        return False

    def setEnabled(self, flgVal=True):
        self.enabledFlag = flgVal
        if not flgVal:
            self.longPressReachedFlag = False
            self.lastInputLevel = RH_GPIO.UNKNOWN
            self.pressedStartTimeSecs = 0
            RH_GPIO.close_channel(self.gpioPinNum)

    def isEnabled(self):
        return self.enabledFlag

    def noop(self, param1=None):
        pass
    