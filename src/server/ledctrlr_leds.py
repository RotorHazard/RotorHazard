'''LED Controller (via serial port) LED layer.'''

import serial
import time
import gevent
import logging
logger = logging.getLogger(__name__)

ENC_STR = "utf-8"

serial_rlock_obj = gevent.lock.RLock()  # semaphore lock for serial I/O access

class LedCtrlrPixel:
    def __init__(self, serial_ctrlr_port, serial_ctrlr_baud, count, color_order, brightness):
        '''Constructor'''
        self.pixels = [0 for _i in range(count)]
        self.initial_brightness = brightness
        self.color_order = color_order
        self.pixels_same_tracker = -1  # for detecting if all pixels set to same color
        self.one_changed_flag = False  # for detecting if only a single pixel was changed since last 'show'
        self.one_changed_idx = 0
        self.serial_obj = serial.Serial(port=None, baudrate=serial_ctrlr_baud, timeout=1.0)
        self.serial_obj.setDTR(0)  # clear in case line is tied to processor reset
        self.serial_obj.setRTS(0)
        self.serial_obj.setPort(serial_ctrlr_port)
        self.serial_obj.open()  # open port (now that DTR is configured for no change)

    def begin(self):
        self.flushInitialInputBuffer()  # clear initial output from controller
        resp_str = self.sendCommandToCtrlr('V')
        if ("LED Controller" in resp_str):
            logger.info("Established LedCtrlr connection to: {}".format(resp_str))
        else:
            logger.warning("Unexpected first response from LedCtrlr: {}".format(resp_str))
        led_count = self.numPixels()
        resp_str = self.sendCommandToCtrlr('M')
        if resp_str.isdigit():
            if led_count > int(resp_str):
                logger.warning("Configured LED_COUNT ({}) is greater than LedCtrlr maximum ({})".\
                               format(led_count, resp_str))
        else:
            logger.warning("Unable to parse response to 'M' from LedCtrlr as integer: {}".format(resp_str))
        # configure the LED strip
        self.sendCommandToCtrlr("C {} {}".format(led_count, self.color_order))
        self.setBrightness(self.initial_brightness)

    def numPixels(self):
        return len(self.pixels)

    def setPixelColor(self, i, color):
        self.pixels[i] = color
        # track if only a single pixel was changed since last 'show'
        if not self.one_changed_flag:
            self.one_changed_flag = True
            self.one_changed_idx = i
        else:
            self.one_changed_flag = False
        # track if all pixels end up set to the same color
        if i == 0:
            self.pixels_same_tracker = 0
        elif i == self.pixels_same_tracker + 1 and color == self.pixels[self.pixels_same_tracker]:
            self.pixels_same_tracker = i
        else:
            self.pixels_same_tracker = -1

    def getPixelColor(self, i):
        return self.pixels[i]

    def show(self):
        if self.one_changed_flag:
            self.one_changed_flag = False  # only a single pixel was changed since last 'show'
            self.sendCommandToCtrlr("P {} {:06X}".format(\
                                  self.one_changed_idx, self.pixels[self.one_changed_idx]))
        elif self.pixels_same_tracker == len(self.pixels) - 1:
            self.sendCommandToCtrlr("F {:06X}".format(self.pixels[0]))  # all pixels same color
        else:
            self.sendCommandToCtrlr("A")
            self.sendPixelsArrayData()    # send all pixel RGB values as a stream of bytes
        self.sendCommandToCtrlr("S")

    def setBrightness(self, brightness):
        self.sendCommandToCtrlr("B {}".format(brightness))

    def flushInitialInputBuffer(self):
        with serial_rlock_obj:
            self.serial_obj.write(bytearray("\r", ENC_STR))
            time.sleep(0.1)
            cnt = 0
            while cnt < 5:
                cnt += 1
                resp = self.serial_obj.read(99)
                if resp:
                    break
                time.sleep(0.1)
            self.serial_obj.flushInput()

    def sendPixelsArrayData(self):
        bt_arr = bytearray()
        for pixel in self.pixels:
            bt_arr.append((pixel >> 16) & 0xFF)
            bt_arr.append((pixel >> 8) & 0xFF)
            bt_arr.append(pixel & 0xFF)
        return self.sendByteArrayToCtrlr(bt_arr)

    def sendCommandToCtrlr(self, command, ret_resp_flag=True):
        resp_str = self.doSendCommandToCtrlr(command, ret_resp_flag)
        if resp_str == 'E':
            err_msg_str = self.doSendCommandToCtrlr('L', True)
            logger.warning("Error message received from LedCtrlr (command={}): {}".format(command, err_msg_str))
            resp_str = "Error"
        return resp_str

    def doSendCommandToCtrlr(self, command, ret_resp_flag):
        with serial_rlock_obj:
            self.serial_obj.write(bytearray(command + '\r', ENC_STR))
            while True:
                ch = str(self.serial_obj.read(1), ENC_STR)
                if ch == '.':
                    break
                if ch == '':
                    logger.warning("No cmd response char received from LedCtrlr for command: {}".format(command))
                    break
                if ch != '>':  # receiving '>' here may be from previous command, so ignore
                    if ch == 'E':
                        logger.warning("Error response char received from LedCtrlr for command: {}".format(command))
                    else:
                        logger.warning("Unexpected cmd response char ('{}') received from LedCtrlr for command: {}".\
                                       format(ch, command))
            buff = ''
            if ch != '' and ret_resp_flag:
                cnt = 0
                while True:
                    ch = str(self.serial_obj.read(1), ENC_STR)
                    if ch == '>':
                        break
                    if ch == '':
                        logger.warning("Unexpected end of response from LedCtrlr for command: {}".format(command))
                        break
                    buff += ch
                    cnt += 1
                    if cnt >= 99:
                        logger.warning("Too-long response (len={}) received from LedCtrlr for command: {}".\
                                       format(cnt, command))
                        break
                buff = buff.strip()
            return buff

    def sendByteArrayToCtrlr(self, bt_arr):
        with serial_rlock_obj:
            self.serial_obj.write(bt_arr)
            ch = str(self.serial_obj.read(1), ENC_STR)
            if ch == '':
                logger.warning("No response char received for sendByteArr cmd from LedCtrlr")
            elif ch != '>':
                if ch == 'E':
                    logger.warning("Error response char received for sendByteArr cmd from LedCtrlr")
                    err_msg_str = self.doSendCommandToCtrlr('L', True)
                    logger.warning("Error message received for sendByteArr cmd from LedCtrlr: {}".format(err_msg_str))
                else:
                    logger.warning("Unexpected cmd response char received for sendByteArr cmd from LedCtrlr: {}".format(ch))
            return ch


def get_pixel_interface(config, brightness, *args, **kwargs):
    '''Returns the pixel interface.'''
    logger.info('LED: LedCtrlr via serial port ({}, {} baud, count={}, {})'.format(\
                                   config['SERIAL_CTRLR_PORT'], config['SERIAL_CTRLR_BAUD'], \
                                    config['LED_COUNT'], config['LED_STRIP']))
    return LedCtrlrPixel(config['SERIAL_CTRLR_PORT'], config['SERIAL_CTRLR_BAUD'], config['LED_COUNT'],\
                         config['LED_STRIP'], brightness)
