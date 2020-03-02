# Odniesienia i noty Raspberry Pi

### zdalny dostęp SSH (tylko Wiersz Poleceń)

https://www.raspberrypi.org/documentation/remote-access/ssh/

### zdalny dostęp VNC (Zdalny Pulpit i Interfejs Graficzny)

https://www.raspberrypi.org/documentation/remote-access/vnc/README.md

### Udostępnianie Samba dla Sieci Windows

Zainstaluj Samba
```
$ sudo apt-get install samba samba-common-bin
```
Otwórz konfigurację
```
$ sudo leafpad /etc/samba/smb.conf
```
Ustaw następująco, odkomentuj jeśli potrzeba
```
workgroup = WORKGROUP
wins support = yes
```
Dodaj na koniec pliku config
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
Ustaw hasło dla użytkownika pi
```
$ sudo smbpasswd -a pi
```

### Instalacja Github
```
$ sudo apt-get install git
```

### Zdalny Access Point (hot-spot WiFi)
[Zainstaluj i skonfiguruj dnsmasq i hostapd](https://github.com/SurferTim/documentation/blob/6bc583965254fa292a470990c40b145f553f6b34/configuration/wireless/access-point.md)

Skompletowanie instrukcji pozwoli również Access Pointowi skierować ruch do połączenia z użyciem kabla (zakładając, że połączenia z użyciem kabla - ethernet - posiada dostęp do Internetu)

Niektóre nowe modele Raspberry Pi mają wbudowane sieciowe moduły bezprzewodowe. Jednak nie jest wskazane używanie ich przez większość użytkowników. Wbudowane moduły bezprzewodowe mają kiepski zasięg, a postawienie timera na ziemi (co się często zdarza) albo wewnątrz kierunkowego chassis - potrzebnego podczas wyścigów w pomieszczeniach - jeszcze bardziej zredukuje zasięg. Lepiej użyj zewnętrznego modułu WiFi albo podłącz Pi do zewnętrznego routera bezprzewodowego. Możesz też użyć kabla ethernet.
