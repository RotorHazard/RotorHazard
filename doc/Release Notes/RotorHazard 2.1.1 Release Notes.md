# RotorHazard 2.1.1 Release Notes

## Updates from 2.1.0

 * Fix LED custom color selector
 * Fix profile selector
 * Added support for RGBW strips
 * Improved documentation and translations

See [release notes from 2.1.0](https://github.com/RotorHazard/RotorHazard/releases/tag/2.1.0) for more information on this version.

## Upgrade Notes

To install RotorHazard on a new system, see the instructions in doc/Software Setup.md

To update an existing RotorHazard installation to this version:
```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/2.1.1 -O temp.zip
unzip temp.zip
mv RotorHazard RotorHazard.old
mv RotorHazard-2.1.1 RotorHazard
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

No additional code changes have been made to nodes since the 2.1.0 release.

As always, to report bugs please post a [GitHub issue](https://github.com/RotorHazard/RotorHazard/issues).
