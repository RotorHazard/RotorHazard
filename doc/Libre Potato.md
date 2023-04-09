# Detect libre
`cat /proc/device-tree/compatible` 
libretech,aml-s905x-ccamlogic,s905xamlogic,meson-gxl`

`cat /proc/device-tree/model`
Libre Computer AML-S905X-CC

# Enable i2c interface on the correct pins
```bash
sudo ldto merge i2c-ao`
```

# Enable spi interface on the correct pins
Single SPI on CE0 pin 24

```bash
sudo ldto merge spicc spicc-spidev
```

# Enable serial on /dev/serial0
Libre puts serial on ttyAML*
ttyAML6 is what pi calls serial0
```bash
sudo ldto enable uart-a
```
Edit config.json and change BPILL_SERIAL_PORT to point to /dev/ttyAML6
```json
{
	...,
	"SERIAL_PORTS": [],
	"BPILL_SERIAL_PORT": "/dev/ttyAML6",
	...
}

```

## Le Potato supports hardware SPI on the 40-pin GPIO header with the same pinout as Raspberry Pi 2/3/4 Model B/B+ boards.

```
MOSI on pin 19
MISO on pin 21
SCLK on pin 23
CE0 on pin 24
CE1 on pin 26
```
They can be used directly with hardware drivers or exposed as /dev/spidev0.0 and /dev/spidev0.1.
If you only have 1 SPI slave device, you only need CE0 on pin 24. To activate /dev/spidev0.0, run:

`sudo ldto enable spicc spicc-spidev`
If you have two SPI slave devices, you need both CE0 on pin 24 and CE1 on pin 26. To activate /dev/spidev0.0 and /dev/spidev0.1, run:

`sudo ldto enable spicc-cs1 spicc-cs1-spidev`
After you have tested your device(s) and confirmed that they are working, you can enable it permanently via:

`sudo ldto merge spicc spicc-spidev`
or
`sudo ldto merge spicc-cs1 spicc-cs1-spidev`
Reboot and it should appear those SPI devices should appear without having to run enable.

If you no longer need SPI devices after merging them, you can reset the system to default by:

`sudo ldto reset`

# tools for detecting pinout 
https://hub.libre.computer/t/libre-computer-wiring-tool/40

# Potato GPIO lines:

line   0:    "UART TX"       unused   input  active-high 
	line   1:    "UART RX"       unused   input  active-high 
	line   2:   "Blue LED" "librecomputer:blue" output active-high [used]
	line   3: "SDCard Voltage Switch" "VCC_CARD" output active-high [used]
	line   4: "7J1 Header Pin5" unused input active-high 
	line   5: "7J1 Header Pin3" unused input active-high 
	line   6: "7J1 Header Pin12" unused input active-high 
	line   7:      "IR In"       unused   input  active-high 
	line   8: "9J3 Switch HDMI CEC/7J1 Header " unused input active-high 
	line   9: "7J1 Header Pin13" unused input active-high 
	line  10: "7J1 Header Pin15" unused output active-high 
gpiochip1 - 100 lines:
	line   0:      unnamed       unused   input  active-high 
	line   1:      unnamed       unused   input  active-high 
	line   2:      unnamed       unused   input  active-high 
	line   3:      unnamed       unused   input  active-high 
	line   4:      unnamed       unused   input  active-high 
	line   5:      unnamed       unused   input  active-high 
	line   6:      unnamed       unused   input  active-high 
	line   7:      unnamed       unused   input  active-high 
	line   8:      unnamed       unused   input  active-high 
	line   9:      unnamed       unused   input  active-high 
	line  10:      unnamed       unused   input  active-high 
	line  11:      unnamed       unused   input  active-high 
	line  12:      unnamed       unused   input  active-high 
	line  13:      unnamed       unused   input  active-high 
	line  14: "Eth Link LED" unused input active-high 
	line  15: "Eth Activity LED" unused input active-high 
	line  16:   "HDMI HPD"       unused   input  active-high 
	line  17:   "HDMI SDA"       unused   input  active-high 
	line  18:   "HDMI SCL"       unused   input  active-high 
	line  19: "HDMI_5V_EN" "regulator-hdmi-5v" output active-high [used]
	line  20: "9J1 Header Pin2" unused input active-high 
	line  21: "Analog Audio Mute" "enable" output active-high [used]
	line  22: "2J3 Header Pin6" unused input active-high 
	line  23: "2J3 Header Pin5" unused input active-high 
	line  24: "2J3 Header Pin4" unused input active-high 
	line  25: "2J3 Header Pin3" unused input active-high 
	line  26:    "eMMC D0"       unused   input  active-high 
	line  27:    "eMMC D1"       unused   input  active-high 
	line  28:    "eMMC D2"       unused   input  active-high 
	line  29:    "eMMC D3"       unused   input  active-high 
	line  30:    "eMMC D4"       unused   input  active-high 
	line  31:    "eMMC D5"       unused   input  active-high 
	line  32:    "eMMC D6"       unused   input  active-high 
	line  33:    "eMMC D7"       unused   input  active-high 
	line  34:   "eMMC Clk"       unused   input  active-high 
	line  35: "eMMC Reset"      "reset"  output   active-low [used]
	line  36:   "eMMC CMD"       unused   input  active-high 
	line  37: "ALT BOOT MODE" unused input active-high 
	line  38:      unnamed       unused   input  active-high 
	line  39:      unnamed       unused   input  active-high 
	line  40:      unnamed       unused   input  active-high 
	line  41: "eMMC Data Strobe" unused input active-high 
	line  42:  "SDCard D1"       unused   input  active-high 
	line  43:  "SDCard D0"       unused   input  active-high 
	line  44: "SDCard CLK"       unused   input  active-high 
	line  45: "SDCard CMD"       unused   input  active-high 
	line  46:  "SDCard D3"       unused   input  active-high 
	line  47:  "SDCard D2"       unused   input  active-high 
	line  48: "SDCard Det"         "cd"   input   active-low [used]
	line  49:      unnamed       unused   input  active-high 
	line  50:      unnamed       unused   input  active-high 
	line  51:      unnamed       unused   input  active-high 
	line  52:      unnamed       unused   input  active-high 
	line  53:      unnamed       unused   input  active-high 
	line  54:      unnamed       unused   input  active-high 
	line  55:      unnamed       unused   input  active-high 
	line  56:      unnamed       unused   input  active-high 
	line  57:      unnamed       unused   input  active-high 
	line  58:      unnamed       unused   input  active-high 
	line  59:      unnamed       unused   input  active-high 
	line  60:      unnamed       unused   input  active-high 
	line  61:      unnamed       unused   input  active-high 
	line  62:      unnamed       unused   input  active-high 
	line  63:      unnamed       unused   input  active-high 
	line  64:      unnamed       unused   input  active-high 
	line  65:      unnamed       unused   input  active-high 
	line  66:      unnamed       unused   input  active-high 
	line  67:      unnamed       unused   input  active-high 
	line  68:      unnamed       unused   input  active-high 
	line  69:      unnamed       unused   input  active-high 
	line  70:      unnamed       unused   input  active-high 
	line  71:      unnamed       unused   input  active-high 
	line  72:      unnamed       unused   input  active-high 
	line  73:  "Green LED" "librecomputer:system-status" output active-high [used]
	line  74: "VCCK Enable" unused input active-high 
	line  75: "7J1 Header Pin27" unused input active-high 
	line  76: "7J1 Header Pin28" unused input active-high 
	line  77: "VCCK Regulator" unused input active-high 
	line  78: "VDDEE Regulator" unused input active-high 
	line  79: "7J1 Header Pin22" unused input active-high 
	line  80: "7J1 Header Pin26" unused input active-high 
	line  81: "7J1 Header Pin36" unused input active-high 
	line  82: "7J1 Header Pin38" unused input active-high 
	line  83: "7J1 Header Pin40" unused input active-high 
	line  84: "7J1 Header Pin37" unused input active-high 
	line  85: "7J1 Header Pin33" unused input active-high 
	line  86: "7J1 Header Pin35" unused input active-high 
	line  87: "7J1 Header Pin19" unused input active-high 
	line  88: "7J1 Header Pin21" unused input active-high 
	line  89: "7J1 Header Pin24" "spi0 CS0" output active-low [used]
	line  90: "7J1 Header Pin23" unused input active-high 
	line  91: "7J1 Header Pin8" unused input active-high 
	line  92: "7J1 Header Pin10" unused input active-high 
	line  93: "7J1 Header Pin16" unused input active-high 
	line  94: "7J1 Header Pin18" unused input active-high 
	line  95: "7J1 Header Pin32" unused input active-high 
	line  96: "7J1 Header Pin29" unused input active-high 
	line  97: "7J1 Header Pin31" unused input active-high 
	line  98: "7J1 Header Pin7" unused input active-high 
	line  99:      unnamed       unused   input  active-high 
