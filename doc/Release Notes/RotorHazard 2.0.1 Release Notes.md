# RotorHazard 2.0.1 Release Notes

## Updates
* Language translation updates
* Update LED library
* Fix LEDs not actually optional
* Fix opening Marshal page clears local settings
* Fix database recovery of RSSI thresholds
* Update requirements to prevent dependency vulnerabilities
* Add DJI channels

## Upgrade Notes
* If you run LEDs, you will need to update the rpi_281x library. Connect the pi to the internet, then run "sudo pip install --upgrade rpi_ws281x".
