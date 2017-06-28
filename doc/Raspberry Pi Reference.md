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



