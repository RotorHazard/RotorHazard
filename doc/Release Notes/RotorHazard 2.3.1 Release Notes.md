# RotorHazard 2.3.1 Release Notes

## Updates from 2.3.0

 * Fix LiveTime Decoder page
 * Fix Java detection for Python 3.8 #477
 * Resolve deprecated log functions #476

See [release notes from 2.3.0](https://github.com/RotorHazard/RotorHazard/releases/tag/2.3.0) for more information on this version.
<a name="documentation"></a>
## Documentation

Documentation for RotorHazard 2.3.1 may be found at:
https://github.com/RotorHazard/RotorHazard/blob/2.3.1/doc/README.md

## Installation / Upgrade Notes

To install RotorHazard on a new system, see the instructions in [doc/Software Setup.md](https://github.com/RotorHazard/RotorHazard/blob/2.3.1/doc/Software%20Setup.md)

To update an existing RotorHazard installation to this version:
```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/2.3.1 -O temp.zip
unzip temp.zip
mv RotorHazard RotorHazard.old
mv RotorHazard-2.3.1 RotorHazard
rm temp.zip
cp RotorHazard.old/src/server/config.json RotorHazard/src/server/
cp RotorHazard.old/src/server/database.db RotorHazard/src/server/
```
The previous installation ends up in the 'RotorHazard.old' directory, which may be deleted or moved.

The RotorHazard server dependencies should also be updated (be patient, this command may take a few minutes):
```
cd ~/RotorHazard/src/server
sudo pip install --upgrade --no-cache-dir -r requirements.txt
```

## Node Code (Arduino)
There are no node code changes for this version since 2.2.0. You will need to upgrade your Arduino firmware only if upgrading from a version prior to 2.2.

## Issues
If you encounter a bug, please report it using the [Issues page on GitHub](https://github.com/RotorHazard/RotorHazard/issues). Open "View Server Log" (in the "..." menu) and a "Download Logs" button will create and download a '.zip' archive file containing all available log files and the current configuration and database files.