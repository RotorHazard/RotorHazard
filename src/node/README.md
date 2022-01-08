# Receiver Node Firmware

The `src/node` directory contains the source code for the RotorHazard nodes. The same code may be used on Arduino nodes, or S32_BPill/ESP32 multi-node boards.

For Arduino nodes, see '[readme_Arduino.md](readme_Arduino.md)'

For S32_BPill nodes, see '[readme_S32_BPill.md](readme_S32_BPill.md)'

For ESP32/ESP8266 nodes, see '[readme_ESP32.md](readme_ESP32.md)'

<br>

## Unit Tests

Setup as per <https://github.com/Arduino-CI/arduino_ci>, then

```
set path=c:\msys64\mingw64\bin;%path%
bundle exec arduino_ci.rb --skip-examples-compilation
```
