# ButtonInputHandler:  Handler for a button connected to a GPIO input pin

import sys
sys.path.append('util')  # needed at runtime to find RHGPIO module

import RHGPIO

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
        self.lastInputLevel = RHGPIO.UNKNOWN
        self.pressedStartTimeSecs = 0
        self.enabledFlag = startEnabledFlag
        self.errorLoggedCount = 0
        try:
            RHGPIO.setup(gpioPinNum, RHGPIO.IN, pull_up_down=RHGPIO.PUD_UP)
        except:
            logger.exception("Exception error in ButtonInputHandler setup")

    # function called on a periodic basis to poll the input and invoke callbacks
    # returns True if button currently pressed or long press detected
    def pollProcessInput(self, nowTimeSecs):
        try:
            if self.enabledFlag:
                inLvl = RHGPIO.input(self.gpioPinNum)
                if self.lastInputLevel == RHGPIO.HIGH:
                    if inLvl == RHGPIO.LOW:  # new button press detected
                        self.pressedStartTimeSecs = nowTimeSecs
                        self.longPressReachedFlag = False
                        self.buttonPressedCallbackFn()
                elif self.lastInputLevel == RHGPIO.LOW:
                    if inLvl == RHGPIO.LOW:  # button long-press detected
                        if self.pressedStartTimeSecs > 0 and \
                                    (nowTimeSecs - self.pressedStartTimeSecs) * 1000 > \
                                    self.buttonLongPressDelayMs:
                            if not self.longPressReachedFlag:
                                self.longPressReachedFlag = True
                                self.buttonLongPressCallbackFn()
                    else:
                        self.buttonReleasedCallbackFn(self.longPressReachedFlag)
                self.lastInputLevel = inLvl
                return (inLvl == RHGPIO.LOW) or self.longPressReachedFlag
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
            self.lastInputLevel = RHGPIO.UNKNOWN
            self.pressedStartTimeSecs = 0

    def isEnabled(self):
        return self.enabledFlag

    def noop(self, param1=None):
        pass
    