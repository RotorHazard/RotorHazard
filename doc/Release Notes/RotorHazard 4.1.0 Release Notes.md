# RotorHazard 4.1.0 Release Notes

## Highlights

### Support for Raspberry Pi 5
All Pi 5 models are now supported. LEDs cannot (yet) be connected directly to a Pi5, but can be operated using an [LEDCtrlr](https://github.com/RotorHazard/LEDCtrlr) module.

### Performance Optimization
Leaderboard generation time reduced significantly as database size increases, while simultaneously improving system responsiveness during results builds. Gains of over 1100% seen on large databases.

### Improved event and server data handling
Archive and switch events using the `Event` panel. Server configuration is no longer stored in the main database, allowing carryover of server settings while switching events.

### RHAPI 1.1
Includes plugin manifest files; lap add; data attributes for heats, classes, formats, and races; endpoints for server config values. UI for plugins shows what's installed and any failure conditions

### Other Notable Updates
* Additional text variables and documentation
* Split timing improvements
* Security updates, bug fixes, and stability improvements
* Expanded data communications with FPVTrackSide (which enable adaptive calibration)
* Marshaling UI updates; visible frequency info; adjusting values recalculates
* Improved notification of network communications issues
* Updated NuclearHazard build files and Atom
* Periodic sensor logging
* Schedule Race shortcut key (s)
* LED subsystem improvements
* Updated frequency reference includes O3
* Japanese localization
* Documentation updates


<a name="documentation"></a>
## Documentation
Documentation for RotorHazard may be found at:
https://github.com/RotorHazard/RotorHazard/tree/v4.1.0/doc


## Installation / Upgrade Notes

> [!TIP]
> [RotorHazard Install Manager](https://github.com/RotorHazard/RH_Install-Manager) is generally able to install new beta versions within a few hours of release.

To install RotorHazard on a new system, see the instructions in '[doc/Software Setup.md](https://github.com/RotorHazard/RotorHazard/blob/v4.1.0/doc/Software%20Setup.md)'

To update an existing RotorHazard installation, see [Updating an Existing Installation](https://github.com/RotorHazard/RotorHazard/blob/v4.1.0/doc/Software%20Setup.md#updating-an-existing-installation). The current version code is `4.1.0`.

The minimum version of Python supported is now 3.8. If your Python is older than this, you should upgrade using the steps in the Software Setup document under "5. [Install Python](https://github.com/RotorHazard/RotorHazard/blob/main/doc/Software%20Setup.md#5-install-python)." or set up a new environment. Do this before updating RotorHazard, or the update may fail.


## RotorHazard Node Code
The node-code version is now 1.1.5 (introduced in 4.1.0-beta.1). Doing a reflash on your node processor is recommended if you're using a board that has an STM32-type processor (optional for Arduino-based boards).

For STM32-based boards, the recommended method for installing the node firmware is to use the Update Nodes button (in the 'System' section on the 'Settings' page) on the RotorHazard web GUI.


## Known Issues
- Renaming a heat will not update the cached "source" display name for fastest lap and consecutives.

## Issue Reporting
If you encounter a bug, please report it using the [Issues page on GitHub](https://github.com/RotorHazard/RotorHazard/issues). When reporting issues, using the "Download Logs" button and including the generated '.zip' file is highly recommended (see below).

The Server Log may be displayed via the "View Server Log" item in the drop-down menu. Clicking on the "Select Text" button will select all the displayed log text, which may then be copied and pasted. Clicking on the "Download Logs" button will create and download a '.zip' archive file containing all available log files and the current configuration and database files.


## What's Changed
* Add v5 nuclearhazard files by @SpencerGraffunder in https://github.com/RotorHazard/RotorHazard/pull/802
* Eliminate dependency "six" by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/805
* Bump minimum python version to 3.8 by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/806
* Fix LED displays by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/807
* Split timer improvements (nameOnly option, etc) by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/811
* Remove hard-coded panel size from row inversion by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/817
* Software Setup doc updates for venv etc by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/815
* RH4 Event setup guide updates by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/818
* Log absolute timestamps for race events by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/820
* Add Schedule Race shortcut by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/813
* Documentation updates for RH4 by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/821
* Improved plugins handling/logging when no Pillow library by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/828
* add Simplified Chinese localization by @L1cardo in https://github.com/RotorHazard/RotorHazard/pull/826
* Add custom UI panels to streams page by @klaasnicolaas in https://github.com/RotorHazard/RotorHazard/pull/824
* Database as "Event" UI paradigm by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/827
* migrate getsize to getbbox by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/829
* RHAPI lap_add by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/814
* Cleanup unreachable code by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/835
* Dependency cleanup by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/831
* Marshaling UI updates by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/832
* Data attributes for heats, classes, and races (meta) by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/836
* Add support for TIME_BEHIND callout variable by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/833
* Add 'Clear Messages' action by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/834
* Basic Plugin UI by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/837
* Raceformat data attributes by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/839
* Apply generate parameters as class attribute by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/838
* Added format button to home page. by @vikibaarathi in https://github.com/RotorHazard/RotorHazard/pull/841
* Improve frontend status displays by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/842
* RH_GPIO abstraction layer by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/847
* Pi 5 support by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/848
* Update node code to version 1.1.5 by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/849
* Temporally remove Chinese localization by @L1cardo in https://github.com/RotorHazard/RotorHazard/pull/845
* Only display stream seats with frequency enabled by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/843
* Periodic sensor logging by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/844
* Fix sequential assumption for dataloggers by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/851
* UI improvements by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/852
* Remove event handler kill and prevent LED shutdown by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/853
* Updates for Flask and SqlAlchemy libraries / usage by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/861
* Added O3 frequency band, as well as the new frequency chart by @eduardorcosta in https://github.com/RotorHazard/RotorHazard/pull/859
* Add support for LEDCtrlr by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/871
* Add pilot-frequency info to Marshal page by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/873
* Expand returned server info to TrackSide by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/863
* Add Japanese localization by @ToshihiroMakuuchi in https://github.com/RotorHazard/RotorHazard/pull/870
* Fixes for database connections building up by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/876
* Japanese localization fixes by @ToshihiroMakuuchi in https://github.com/RotorHazard/RotorHazard/pull/877
* Add import/export for Audio Settings by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/879
* Japanese localization fixex (v4.1.0-beta2) by @ToshihiroMakuuchi in https://github.com/RotorHazard/RotorHazard/pull/884
* Record race history when initiated from FPVTrackSide by @eedok in https://github.com/RotorHazard/RotorHazard/pull/885
* Migrate config to class and provide API endpoints by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/869
* Improved gevent.sleep/thread management by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/887
* Results optimization by @HazardCreative in https://github.com/RotorHazard/RotorHazard/pull/895
* Single Pass Mapping by @i-am-grub in https://github.com/RotorHazard/RotorHazard/pull/897
* Add NuclearHazard Atom PCB files by @SpencerGraffunder in https://github.com/RotorHazard/RotorHazard/pull/898
* Japanese localization additional fix02 by @ToshihiroMakuuchi in https://github.com/RotorHazard/RotorHazard/pull/894
* Fix issue with switching from 'None' to pilot in heat by @ethomas997 in https://github.com/RotorHazard/RotorHazard/pull/908

## New Contributors
* @L1cardo made their first contribution in https://github.com/RotorHazard/RotorHazard/pull/826
* @eduardorcosta made their first contribution in https://github.com/RotorHazard/RotorHazard/pull/859
* @ToshihiroMakuuchi made their first contribution in https://github.com/RotorHazard/RotorHazard/pull/870
* @eedok made their first contribution in https://github.com/RotorHazard/RotorHazard/pull/885
* @i-am-grub made their first contribution in https://github.com/RotorHazard/RotorHazard/pull/897

**Full Changelog**: https://github.com/RotorHazard/RotorHazard/compare/v4.0.1...v4.1.0