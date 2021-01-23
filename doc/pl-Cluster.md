# Grupa

Dodatkowe timery RotorHazard mogą być podłączone jako moduły "secondary", porozumiewające się za pomocą wbudowanych interfejsów sieciowych (np. WiFi). Domyślny tryb to  „timer” (dla mierzenia międzyczasów), który pozwala wielu timerom być umieszczonym wzdłuż toru, żeby podawać międzyczasy. Tryb "lustrzany" (mirror) również jest wspierany. W trybie tym moduł "secondary" dokładnie odwzorowuje to co robi moduł główny (np. może być ustawiony jako "tylko-LED i pokazywać animacje LED-owe modułu głównego).

### Konfiguracja

Dodatkowe czasomierze mogą być skonfigurowane (w pliku 'src/server/config.json') w sekcji "GENERAL" z wpisem "SECONDARIES" zamierającym macierz adresów IP czasomierzy ułożoną według kolejności timerów na torze.


```
{
	"GENERAL": {
		... ,
		"SECONDARIES": ["192.168.1.2:5000", "192.168.1.3:5000"]
	}
}
```

Dodatkowe opcje mogą być skonfigurowane, np:

```
{
	"GENERAL": {
		... ,
		"SECONDARIES": [{"address": "192.168.1.2:5000", "mode": "timer", "distance": 5}, {"address": "192.168.1.2:5000", "mode": "mirror"}],
		"SECONDARY_TIMEOUT": 10
	}
}
```
* "address": Adres IP i port modułu "secondary".
* "mode": Tryb timera ("mirror" lub "timer")
* "distance": Dystans od poprzedniej bramki - dla obliczenia prędkości.

### Synchronizacja zegarów

Bardzo istotne, żeby timery miały zsynchronizowany czas.
Możesz użyć do tego NTP.

Na wszystkich timerach:

	sudo apt-get install ntp

Na głównym, edytuj /etc/npd.conf i dodaj linie podobne do:

	restrict 192.168.123.0 mask 255.255.255.0
	broadcast 192.168.123.255

Na modułach "secondary", edytuj /etc/npd.conf i dodaj linie podobne do:

	server 192.168.123.1

Na wszystkich timerach:

	sudo systemctl stop systemd-timesyncd
	sudo systemctl disable systemd-timesyncd
	sudo /etc/init.d/ntp restart

### Generator liczb losowych

Generator liczb losowych poprawia łączność WiFi (podtrzymuje entropię dla szyfrowania). Aktywuj sprzętowy RNG żeby poprawić dostępną entropię.

	sudo apt-get install rng-tools

Edytuj /etc/default/rng-tools i odkomentuj linię:

   HRNGDEVICE=/dev/hwrng

Następnie, zrestartuj rng-tools wpisując

    sudo service rng-tools restart

### Uwagi

Przegapione i niepoprawne międzyczasy nie mają żadnego wpływu na zapamiętywanie czasów okrążeń przez moduł główny.

Moduł "secondary", również może być głównym, ale pod-podziały nie są przekazywane wyżej w hierarchii.

Jeśli chcesz używać Grupy opartej o Wifi, instrukcje jak stworzyć Access Point (WiFi hot-spot) możesz znaleźć na:
<https://www.raspberrypi.org/documentation/configuration/wireless/access-point.md>.
Przeczytaj też <https://github.com/mr-canoehead/vpn_client_gateway/wiki/Configuring-the-Pi-as-a-WiFi-Access-Point>
i <https://superuser.com/questions/1263588/strange-issue-with-denyinterfaces-in-access-point-config>.
Zwłaszcza dodaj `denyinterfaces wlan0` do `/etc/dhcpcd.conf` i `sudo nano /etc/network/interfaces.d/wlan0`
```
allow-hotplug wlan0
iface wlan0 inet static
	address 10.2.2.1
	netmask 255.255.255.0
	network 10.2.2.0
	broadcast 10.2.2.255
	post-up systemctl restart hostapd
```
żeby dhcpcd współpracowało poprawnie z hot-spotem.
