# Raspberry Pi Reference and Notes

### SSH Remote Access (Terminal Only)

https://www.raspberrypi.org/documentation/remote-access/ssh/

### VNC Remote Access (Remote Desktop GUI)

https://www.raspberrypi.org/documentation/remote-access/vnc/README.md

### Samba Share for Windows Networking

Install Samba
```
$ sudo apt-get install samba samba-common-bin
```
Open the config
```
$ sudo leafpad /etc/samba/smb.conf
```
Set the following, uncomment if needed
```
workgroup = WORKGROUP
wins support = yes
```
Add to the bottom of config
```
[pihome]
   comment= Pi Home
   path=/home/pi
   browseable=Yes
   writeable=Yes
   only guest=no
   create mask=0777
   directory mask=0777
   public=no
```
Set to the pi user password
```
$ sudo smbpasswd -a pi
```

### Github Installation
```
$ sudo apt-get install git
```

### Wireless Access Point
[Install and configure dnsmasq and hostapd](https://github.com/SurferTim/documentation/blob/6bc583965254fa292a470990c40b145f553f6b34/configuration/wireless/access-point.md)

Completing the instructions will also allow the AP to route traffic to the wired connection (assuming the wired connection has internet)

While some models of Raspberry Pi have onboard wireless networking, it is not recommended for most users of the timer. The internal wireless has poor range, and placing the timer on the ground (which is common) or inside a directional RF shield (necessary for many indoor spaces) will further reduce its capability. Instead, use an external WiFi module or connect the Pi to a standalone wireless router.
