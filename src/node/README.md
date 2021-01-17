# Receiver Node Firmware

The `src/node` directory contains the source code for the RotorHazard nodes. The same code may be used on Arduino nodes, or on an S32_BPill multi-node board.

For Arduino nodes, see '[readme_Arduino.md](readme_Arduino.md)'

For S32_BPill nodes, see '[readme_S32_BPill.md](readme_S32_BPill.md)'


<br>

## Unit Tests

Setup as per <https://github.com/Arduino-CI/arduino_ci>, then

```
set path=c:\Ruby25-x64\msys64\mingw64\bin;%path%
bundle exec arduino_ci_remote.rb --skip-compilation
```
