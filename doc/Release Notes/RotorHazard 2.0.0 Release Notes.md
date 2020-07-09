# RotorHazard 2.0.0 Release Notes

## Main Features
* Improved node filtering improves timing accuracy and ease of calibration by resisting outlier noise. No longer requires setting filter ratio when changing between indoor and outdoor environments.
* Race history collection: Records signal data during a race so calibration can be adjusted afterward.
* Improved browser timer (system-clock based vs. interval-based): more accurate and better synchronization
* Synchronization and delay compensation for i2c and browser communciations
* Synchronization of LED changes and browser start signals
* Race marshaling: add laps, remove laps, and recalculate all laps based on signal history.
* LiveTime support.
* Race scheduling (delayed staging/start)
* JSON API exposes race data for use by other services on network.
* Supports BME280 temperature sensor and INA219 voltage sensor 

### UI
* Added [keyboard shortcuts](https://github.com/RotorHazard/RotorHazard/blob/master/doc/User%20Guide.md#run) for start race, stop race, save laps, clear laps, manual laps, and dismiss message
* Selectable generated or MP3 tones (each work better on different browsers)
* Improved use of large screen areas
* Warn about suspect calibration values
* Display local race start time
* Display race lap absolute timestamp
* Restore opened panels when results refresh
* Warn about browser timer sync loss
* Less intrusive message location 

### Other
* New 3D printed case design/STL files
* Improved documentation
* Added French language
* Some UK localization
* Optionally used libraries are not required to install
* Simulated interface for developing without hardware present
* Unit tests for important node functions
* Can stop a race during staging
* Bug fixes and performance improvements

## Upgrade Notes
* The monotonic library is now required. Connect the pi to the internet, change to the server directory, then run "sudo pip install -r requirements.txt" to get it.
* Use of [directional RF shielding](https://github.com/RotorHazard/RotorHazard/blob/master/doc/Hardware%20Setup.md#add-a-directional-rf-shield) is now considered a required part of the hardware build.
