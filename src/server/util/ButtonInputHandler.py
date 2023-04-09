# ButtonInputHandler:  Handler for a button connected to a GPIO input pin
import logging
import sys
import server.util.RHGPIO as RHGPIO
sys.path.append('util')  # needed at runtime to find FakeRPiGPIO module
import gpiod

##TOD what to do when gpiod isn't real?

class ButtonInputHandler:
    """ Handler for a button connected to a GPIO input pin """
    def __init__(self, gpioPinNum, logger, buttonPressedCallbackFn=None,
                 buttonReleasedCallbackFn=None, buttonLongPressCallbackFn=None,
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
            self.line = RHGPIO.get_line(gpioPinNum)
            if not self.line:
                logger.exception("Exception error in ButtonInputHandler setup")
                raise Exception("unable to get GPIO line for buttonInputHandler")
            self.line_config = gpiod.line_request()
            self.line_config.consumer = "RotorHazard"
            self.line_config.request_type = gpiod.line_request.DIRECTION_INPUT
            self.line_config.flags = self.line_config.FLAG_BIAS_PULL_UP
            #actually request to activate the line.
            self.line.request(self.line_config)
            # GPIO.setup(gpioPinNum, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        except Exception as up:
            self.enabledFlag = False
            logger.exception("Exception error in ButtonInputHandler setup")
            logger.exception(up)


    # function called on a periodic basis to poll the input and invoke callbacks
    # returns True if button currently pressed or long press detected
    def poll_process_input(self, now_time_secs):
        try:
            if self.enabledFlag:
                in_lvl = self.line.get_value()
                if self.lastInputLevel == RHGPIO.HIGH:
                    if in_lvl == RHGPIO.LOW:  # new button press detected
                        self.pressedStartTimeSecs = now_time_secs
                        self.longPressReachedFlag = False
                        self.buttonPressedCallbackFn()
                elif self.lastInputLevel == RHGPIO.LOW:
                    if in_lvl == RHGPIO.LOW:  # button long-press detected
                        if self.pressedStartTimeSecs > 0 and \
                                    (now_time_secs - self.pressedStartTimeSecs) * 1000 > \
                                    self.buttonLongPressDelayMs:
                            if not self.longPressReachedFlag:
                                self.longPressReachedFlag = True
                                self.buttonLongPressCallbackFn()
                    else:
                        self.buttonReleasedCallbackFn(self.longPressReachedFlag)
                self.lastInputLevel = in_lvl
                return (in_lvl == RHGPIO.LOW) or self.longPressReachedFlag
            else:
                self.logger.log(logging.INFO, "ButtonHandler not enabled.")
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
    
