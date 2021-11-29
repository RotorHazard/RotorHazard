# S32_BPill Nodes

*Note:* The recommended method for installing the currently-released node firmware onto the S32_BPill processor is to use the `Update Nodes` button (in the 'System' section on the 'Settings' page) on the RotorHazard web GUI. The steps described below are for developers who wish to build the node firmware from the source code.

## Compiling and Uploading with the Arduino IDE

The node code may be loaded (or flashed) onto the S32_BPill processor by loading the code into the Arduino IDE program and using its 'Upload' function. Arduino IDE version 1.8 or newer is required, and it can be downloaded from https://www.arduino.cc/en/Main/Software

Support for STM32 processors in the Arduino IDE is provided by the [STM32duino project](https://github.com/stm32duino). The installation steps are described in detail on the STM32duino "[Getting Started](https://github.com/stm32duino/wiki/wiki/Getting-Started)" page. The basic steps are as follows:

1. In the "Preferences" dialog add the following link to the "Additional Boards Managers URLs" field:

`https://github.com/stm32duino/BoardManagerFiles/raw/main/package_stmicroelectronics_index.json`

2. In the "Tools" menu, select "Board" | "Boards Manager"; select "Contributed" type; select "STM32 MCU based boards", select a version and click on install. (The newest version is usually the one you want.) After the installation is complete you can close the Board Manager.

3. In the "Tools" menu, select "Board" | "Boards Manager..." | "STM32 boards groups" | "Generic STM32F1 Series"

4. In the "Tools" menu, select "Board part number" | "BluePill F103C8"

5. In the "Tools" menu the Serial, USB, and library items my be left at their default values; this is a typical setup:
```
  Board:  "Generic STM32F1 series"
  Board part number:  "BluePill F103C8"
  U(S)ART support:  "Enabled (generic 'Serial')"
  USB support (if available):  "None"
  USB speed (if available):  "Low/Full Speed"
  Optimize:  "Smallest (-Os default)"
  C Runtime Library:  "Newlib Nano (default)"
```

6. In the Arduino IDE, select "File | Open" and navigate to where the `src/node` directory is located, and click on the "node.ino" file to open the node-code project.

7. Click on the 'Verify' button to confirm that the code can be built successfully.

<a id="s32ftdi"></a>
8a. The code may be uploaded to the processor on the RotorHazard S32_BPill board by connecting an FTDI to the 6-pin J4 ("BPill Serial FTDI Link") connector on the board. (The other end of the FTDI is connected to the USB port on a PC.) The Raspberry Pi must not be powered on during programming. In the Arduino IDE the serial port (under "Tools | Port") will need to be set to match the connected FTDI.  (If you view the "Tools | Port" selections before and after connecting the FTDI, you should see its serial-port name appear.) In the "Tools" menu, set the "Upload method" to "STM32CubeProgrammer (Serial)". Clicking on the 'Upload' button should flash the code onto the S32_BPill processor.

<a id="s32stlink"></a>
8b. If other methods are unsuccessful, the code may be uploaded to the BPill processor using an [ST-Link](https://www.ebay.com/sch/i.html?_nkw=ST-Link) USB programming adapter. It should be wired to the 4 pins of the programming connector on the BPill processor (SWCLK, SWDIO, GND, 3.3V as shown [here](https://alexbirkett.github.io/microcontroller/2019/03/30/flash_bluepill_using_ST_link.html)). In the "Tools" menu, set the "Upload method" to "STM32CubeProgrammer (SWD)". Clicking on the 'Upload' button should flash the code onto the S32_BPill processor.

*STM32F4:* If the code needs to be built for an STM32F4 module (as described [here](../../resources/S32_BPill_PCB/stm32f4module.md)) the above process may be used if the "Board part number" is configured to match the processor type.  Also, to configure the proper I/O pinout, the following line should added to the "src/node/config.h" file (right after the "#include" statements):  `#define STM32_F4_PROCTYPE 1`

## Command-line Compiling and Uploading (S32_BPill Nodes)

Command-line batch/script files for compiling and uploading the node code may be found in the `src/node/scripts` directory. For these files to work, the Arduino IDE needs to be installed -- Arduino IDE version 1.8 or newer is required, and it can be downloaded from https://www.arduino.cc/en/Main/Software

The following batch/script files are available:

* *install_stm32_boards* : Installs the required support libraries into the Arduino IDE installation. This can take a few minutes, but only needs to be run once to install the libraries

* *build_stm32* : Builds the S32_BPill node code (for the STM32F103C8 module), creating the firmware file `src/node/build_stm32/RH_S32_BPill_node.bin`

* *build_stm32_f4* : Builds the S32_BPill node code (for the STM32F411CE "[Black Pill](https://github.com/WeActTC/MiniSTM32F4x1)" module), creating the firmware file `src/node/build_stm32/RH_S32_BPill_node_F4.bin`

* *upload_stm32* : Builds the S32_BPill node code and uploads it using the serial (COM) port specified as the first argument. An optional second argument, "--skipBuild", may be specified to skip the build and upload the last firmware file that was built. See the last step [above](#s32ftdi) for info on using an FTDI for uploading

* *upload_stm32_F4* : Version of 'upload_stm32' for the STM32F411CE "[Black Pill](https://github.com/WeActTC/MiniSTM32F4x1)" module

## Compiling and Uploading with Sloeber Eclipse (S32_BPill Nodes)

The node code may also be edited and built using the [Sloeber-Eclipse IDE](http://eclipse.baeyens.it). To install Sloeber-Eclipse:

1. Install Sloeber-Eclipse (V4.4.1 or later) from http://eclipse.baeyens.it <br>
  Note: The length of install path should be less than 26 characters ([Sloeber limitation](https://github.com/Sloeber/arduino-eclipse-plugin/issues/705))

2. Install STMicroelectronics-STM32 into Sloeber-Eclipse:
  * Open "Arduino > Preferences"
  * In the tree view that pops up, go to "Arduino > Third party index url's" and add the following support package URL:

`https://github.com/stm32duino/BoardManagerFiles/raw/main/package_stmicroelectronics_index.json`

3. In "Arduino | Preferences | Platforms and Boards" open the tree to "STMicroelectronics | STM32 MCU based boards" and select a version. (The newest version is usually the one you want.)

S32_BPill-node project files for Sloeber-Eclipse may be found in the `src/node/project_files/eclipse_sloeber` directory -- copy these files to the `src/node` directory. Then, in Sloeber-Eclipse, the node-code project may be loaded via "File | Open Projects from File System..."

In "Project | Properties | Arduino" the "Arduino board selection" settings should be similar to these:
```
Platform folder:  .../STMicroelectronics/hardware/stm32/2.1.0
Board:  Generic STM32F1 series
Upload Protocol:  Default
Port:  [COM for FTDI]
Optimize:  Smallest (-Os default)
Board part number:  BluePill F103C8
C Runtime Library:  Newlib Nano (default)
Upload method:  STM32CubeProgrammer (Serial)
USB support:  None
U(S)ART support:  Enabled (generic 'Serial')
USB speed:  Low/Full Speed
```

Hitting the 'Verify' button will build the code, which should create the firmware file `src/node/Release/rhnode_S32_BPill.bin`

*STM32F4:* If the code needs to be built for an STM32F4 module (as described [here](../../resources/S32_BPill_PCB/stm32f4module.md)) the above process may be used if the "Board part number" is configured to match the processor type.  Also, to configure the proper I/O pinout, the following line should added to the "src/node/config.h" file (right after the "#include" statements):  `#define STM32_F4_PROCTYPE 1`
