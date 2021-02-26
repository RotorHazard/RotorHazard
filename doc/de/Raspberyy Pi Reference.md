# Raspberry Pi Referenz und Hinweise

### SSH-Fernzugriff (nur Terminal)

https://www.raspberrypi.org/documentation/remote-access/ssh/

### VNC-Fernzugriff (Remotedesktop-GUI)

https://www.raspberrypi.org/documentation/remote-access/vnc/README.md

### Samba Share für Windows-Netzwerke

Installieren Sie Samba

```
$ sudo apt-get install samba samba-common-bin
```

Öffnen Sie die Konfiguration

```
$ sudo leafpad /etc/samba/smb.conf
```

Stellen Sie Folgendes ein, kommentieren Sie es bei Bedarf aus

```
workgroup = WORKGROUP
wins support = yes
```

Fügen Sie am Ende der Konfiguration hinzu

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

Stellen Sie das pi-Benutzerpasswort ein

```
$ sudo smbpasswd -a pi
```

### Github Installation

```
$ sudo apt-get install git
```

### WLAN-Zugangspunkt

[Installieren und konfigurieren von dnsmasq und hostapd](https://github.com/SurferTim/documentation/blob/6bc583965254fa292a470990c40b145f553f6b34/configuration/wireless/access-point.md)

Durch Ausfüllen der Anweisungen kann der AP auch Datenverkehr zur Kabelverbindung weiterleiten (vorausgesetzt, die Kabelverbindung verfügt über Internet).

Während einige Modelle von Raspberry Pi über ein integriertes drahtloses Netzwerk verfügen, wird dies für die meisten Benutzer des Timers nicht empfohlen. Das interne Funkgerät hat eine geringe Reichweite, und wenn der Timer auf dem Boden (was üblich ist) oder in einem Richtungs-HF-Schutzschild (das für viele Innenräume erforderlich ist) platziert wird, wird seine Fähigkeit weiter verringert. Verwenden Sie stattdessen ein externes WLAN-Modul oder verbinden Sie den Pi mit einem eigenständigen WLAN-Router.
