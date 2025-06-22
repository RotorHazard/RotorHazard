# RotorHazard 4.0.0 Release Notes

## Highlights

### Auto Seeding and Frequency Management
Seed heats based on the results of any heat or class, allowing event formats automatically driven by pilot performance. When seeding, it intelligently minimizes frequency changes and uses event history to reduce the need for re-calibrations.

### Heat Generation, Race Points
Generate popular event formats including ladder (letter) mains and regulation (FAI, MultiGP) single- and double-elimination brackets, which run with automatic seeding and frequency management. Fill heats randomly for qualifying while balancing the number of pilots in each. Award points for finishing position. New heat generators and points methods may be added by plugins.

### Class Ranking
Rank performance by best X rounds, last heat position (for ladders), or cumulative points. New class ranking methods may be added by plugins.

### Extended Plugin Reach and API
New methods provide easy access and greatly extend the reach of plugins. A new API introduces a stable method to access data and functions, providing plugin authors with the capability to significantly extend functionality. See [Plugins](/doc/Plugins.md).

### New Low-Cost Build Option
Spencer Graffunder's NuclearHazard is designed to allow components to be populated at the factory, reducing costs, size, and build time.

### Other Notable Updates
* FPVTrackSide support
* Pilotless practice mode
* Variable consecutive laps base
* Message center
* Secondary timer action mode
* Bug fixes, stability upgrades, and performance upgrades


## Compatibility
This version uses an updated version of the socket library which is not compatible with previous RotorHazard releases. All timers in a cluster (mirrors, split timers) and socket-based interfaces must be updated to match. Because of this upgrade away from outdated and insecure code, **Delta5 emulation has ended with RotorHazard 3.2**.


<a name="documentation"></a>
## Documentation
Documentation for RotorHazard 4.0.0 may be found at:
https://github.com/RotorHazard/RotorHazard/tree/v4.0.0/doc


## Installation / Upgrade Notes
To install RotorHazard on a new system, see the instructions in '[doc/Software Setup.md](https://github.com/RotorHazard/RotorHazard/blob/v4.0.0/doc/Software%20Setup.md)'

To update an existing RotorHazard installation, see [Updating an Existing Installation](https://github.com/RotorHazard/RotorHazard/blob/v4.0.0/doc/Software%20Setup.md#updating-an-existing-installation). The current version code is `4.0.0`.


## RotorHazard Node Code
No updates to the node code have been made since RotorHazard version 3.0.0 (the node-code version is 1.1.4).


## Issues
If you encounter a bug, please report it using the [Issues page on GitHub](https://github.com/RotorHazard/RotorHazard/issues). When reporting issues, using the "Download Logs" button and including the generated '.zip' file is highly recommended (see below).

The Server Log may be displayed via the "View Server Log" item in the drop-down menu. Clicking on the "Select Text" button will select all the displayed log text, which may then be copied and pasted. Clicking on the "Download Logs" button will create and download a '.zip' archive file containing all available log files and the current configuration and database files.


## Detailed updates from 3.2
* Event Structure by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/699
* Use InvokeFnQueue with 'pass_record_callback' and 'check_win_condition' by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/700
* RHData 'restore_table' improvements by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/701
* Event structure support by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/705
* Update doc on PCB for 6 arduinos by @laurent-clouet in https://github.com/RotorHazard/RotorHazard/pull/702
* Update Software Setup.md by @MacDaddyFPV in https://github.com/RotorHazard/RotorHazard/pull/710
* Event structure UI, cleanup, and stability by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/711
* Re-implement VRx Control as Manager/Controller; enabling plugins by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/721
* Stream node display misalignment by @vikibaarathi in https://github.com/RotorHazard/RotorHazard/pull/722
* RHRace cleanup by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/726
* RHData resolvers by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/727
* Expand User Interface class by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/728
* Shared race context by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/730
* Fixed calling wrong query to get race format ID by @vikibaarathi in https://github.com/RotorHazard/RotorHazard/pull/736
* Message center for server messages by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/737
* Updated sample path for fresh install lang by @vikibaarathi in https://github.com/RotorHazard/RotorHazard/pull/738
* Global color enable by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/739
* Fix UI focus issue by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/740
* Variable consecutive laps base by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/741
* Frontend parameter UI by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/745
* Add margin to elements in pilot form by @vikibaarathi in https://github.com/RotorHazard/RotorHazard/pull/742
* Improve french language by @arnaudmorin in https://github.com/RotorHazard/RotorHazard/pull/750
* Pluggable class rank by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/747
* Data import by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/748
* Fix /api/race/current return json by @arnaudmorin in https://github.com/RotorHazard/RotorHazard/pull/754
* Frequency aware adaptive calibration by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/749
* Update jquery and socket-io versions by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/752
* Schedule race action by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/755
* Points-based ranking by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/757
* Add DJI freqs in IMDtabler tables by @arnaudmorin in https://github.com/RotorHazard/RotorHazard/pull/753
* Replace plugin interfaces with RHAPI by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/759
* PEP8 refactoring by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/762
* Event / callout improvements by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/765
* Plugin exception handling by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/758
* RHAPI Expansion by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/767
* Fixed race duration field toggle when no time limit by @vikibaarathi in https://github.com/RotorHazard/RotorHazard/pull/770
* Improved race-leader detection by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/771
* Added secondary timer 'action' mode by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/772
* Check/create heat on secondary timer if needed by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/776
* Add NuclearHazard files by @SpencerGraffunder in https://github.com/RotorHazard/RotorHazard/pull/764
* Next round marker by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/778
* FPVTrackSide connector by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/777
* Split/speed timer improvements by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/781
* Add fastest-speed callout variables by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/782
* Allow speed callouts outside of race laps by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/791
* RHAPI/Event expansion by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/790

### New Contributors
* @laurent-clouet made their first contribution in https://github.com/RotorHazard/RotorHazard/pull/702
* @MacDaddyFPV made their first contribution in https://github.com/RotorHazard/RotorHazard/pull/710
* @vikibaarathi made their first contribution in https://github.com/RotorHazard/RotorHazard/pull/722
* @arnaudmorin made their first contribution in https://github.com/RotorHazard/RotorHazard/pull/750
* @SpencerGraffunder made their first contribution in https://github.com/RotorHazard/RotorHazard/pull/764

Full Changelog: https://github.com/RotorHazard/RotorHazard/compare/v3.2.0...v4.0.0