# Arduino Nodes

## Compiling and Uploading with the Arduino IDE

The traditional method of loading (or flashing) the node code onto the Arduino processors (one for each node) is by loading the code into the Arduino IDE program and using its 'Upload' function.  Arduino IDE version 1.8 or newer is required, and it can be downloaded from https://www.arduino.cc/en/Main/Software

The code for the Arduino nodes is in the `src/node` directory. To get these files onto your computer, go to the [RotorHazards releases page on GitHub](https://github.com/RotorHazard/RotorHazard/releases) and download the .zip file for the release you're installing (*make sure it is the same release as the one you installed on the Raspberry Pi*).  For instance, if you're installing version 2.2.0, go to the release page for [that version](https://github.com/RotorHazard/RotorHazard/releases/tag/2.2.0), click on "Source code (zip)" and download the file, which in this case will be "RotorHazard-2.2.0.zip".  Unpack that .zip file into a directory on your computer, and the `src/node` directory will be in there.

In the Arduino IDE, select "File | Open" and navigate to where the `src/node` directory is located, and click on the "node.ino" file to open the node-code project.  In the Arduino IDE the board type (under "Tools") will need to be set to match the Arduino -- the standard setup is:  for 'Board' select "Arduino Nano" and for 'Processor' select "ATMega328P" or "ATMega328P (Old Bootloader)", depending on the particular Arduino used.  If all is well, clicking on the 'Verify' button will successfully compile the code

Using the Arduino IDE, the Arduino processors for the nodes are programmed (flashed) one at a time.  The target Arduino is plugged into the computer via its USB connector -- when connected, it will be assigned a serial-port name (like "COM3").  In the Arduino IDE the serial port (under "Tools | Port") will need to be set to match the connected Arduino.  (If you view the "Tools | Port" selections before and after connecting the Arduino, you should see its serial-port name appear.)  Clicking on the 'Upload' button should flash the code onto the Arduino processor.

If you are not using a [RotorHazard PCB](../../resources/PCB/README.md), edit the `src/node/config.h` file and configure the '#define NODE_NUMBER' value for each node before uploading. For the first node set NODE_NUMBER to 1, for the second set it to 2, etc.
```
// Node Setup -- Set node number here (1 - 8)
#define NODE_NUMBER 1
```

Hardware address selection is also possible by grounding hardware pins following the [published specification](https://github.com/RotorHazard/RotorHazard/wiki/Specification:-Node-hardware-addressing) (this is how the Arduinos are wired on the [RotorHazard PCB](../../resources/PCB/README.md)).

## Command-line Compiling and Uploading (Arduino Nodes)

Command-line batch/script files for compiling and uploading the node code may be found in the `src/node/scripts` directory. For these files to work, the Arduino IDE needs to be installed -- Arduino IDE version 1.8 or newer is required, and it can be downloaded from https://www.arduino.cc/en/Main/Software

The following batch/script files are available:

* *build_arduino* : Builds the Arduino node code, creating the firmware file `src/node/build_arduino/rhnode.hex`

* *upload_arduino* : Builds the Arduino node code and uploads it using the serial (COM) port specified as the first argument. An optional second argument, "--skipBuild", may be specified to skip the build and upload the last firmware file that was built

* *upload_arduino_oldbl* : Same as '*upload_arduino*' except that it uses the 57600 baud rate, which is needed for Arduinos with the "old bootloader"

## Verify Arduino Addresses

The following command may be run on the Raspberry Pi to verify that the Arduino nodes are wired and programmed properly:
```
sudo i2cdetect -y 1
```
On an setup with 8 nodes the response should look something like this:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- 08 -- 0a -- 0c -- 0e --
10: 10 -- 12 -- 14 -- 16 -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
```
The "08" through "16" values represent the presence of each Arduino at its address (in hexadecimal, 08 for node 1, 0a for node 2, etc).  On a setup with 4 nodes only the first four addresses will appear.
