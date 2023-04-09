import sys
sys.path.append('../../src')

import time
import logging
from server.util.ButtonInputHandler import ButtonInputHandler

button_input_handler = None

def button_pressed():
    print("button down event")
def button_released(long_press_reached_flag):
    print(f"button up event. long press: {long_press_reached_flag}")

def button_long_press():
     print(f"button long press event")

if __name__ == '__main__':
    button_input_handler = ButtonInputHandler(
        16, logging.getLogger("button_pres"),
            button_pressed, button_released,
            button_long_press)
    
    while True:
        button_input_handler.poll_process_input(time.monotonic())
        time.sleep(.05)
