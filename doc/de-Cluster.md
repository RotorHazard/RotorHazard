# Cluster

Zusätzliche RotorHazard-Zeitgeber können als "Slave" -Einheiten angeschlossen werden, die über ihre Netzwerkverbindung (d. H. WiFi) verbunden sind. Der Standardmodus ist "Split" (für Split-Timing), wodurch mehrere Timer auf der Strecke platziert werden können, um Zwischenrundenzeiten zu erhalten. Es wird auch ein "Spiegel" -Modus unterstützt, in dem der Slave-Timer die Aktionen des Masters spiegelt (z. B. als "Nur-LED" -Timer, der die Aktionen des Masters anzeigt).

### Konfiguration

Zusätzliche Timer können (in 'src/server/config.json') unter "ALLGEMEIN" mit einem "SLAVES" -Eintrag konfiguriert werden, der ein Array von IP-Adressen der Slave-Timer in der Spurreihenfolge enthält.

```
{
	"GENERAL": {
		... ,
		"SLAVES": ["192.168.1.2:5000", "192.168.1.3:5000"]
	}
}
```

Zusätzliche Optionen können konfiguriert werden, zum Beispiel:

```
{
	"GENERAL": {
		... ,
		"SLAVES": [{"address": "192.168.1.2:5000", "mode": "split", "distance": 5}, {"address": "192.168.1.2:5000", "mode": "mirror"}],
		"SLAVE_TIMEOUT": 10
	}
}
```

* "Adresse": Die IP-Adresse und der Port für den Slave-Timer.
* "Modus": Der Modus für den Timer (entweder "Timer" oder "Spiegel").
* "Entfernung": Die Entfernung vom vorherigen Tor (zur Berechnung der Geschwindigkeit).
* "queryInterval": Anzahl der Sekunden zwischen Heartbeat- / Abfragenachrichten (Standard 10).
* "recEventsFlag": Setzen Sie 'true', um Timer-Ereignisse vom Master aus zu übertragen (Standard 'false' für "split" -Timer, 'true' für "Mirror" -Timer).
* "SLAVE_TIMEOUT": Maximale Anzahl von Sekunden, die auf den Verbindungsaufbau gewartet werden soll.

Der Wert "Adresse" kann mit Sternchen-Platzhalterzeichen angegeben werden. Wenn die IP-Adresse des 'Master'-Timers beispielsweise "192.168.0.11" lautet: `"*.77" => "192.168.0.77"`, `"*.*.3.77" => "192.168.3.77"`, `"*" => "192.168.0.11"`

### Uhrensynchronisation

Die Genauigkeit der gemeldeten Zwischenzeiten ist höher, wenn alle Uhren ihre Uhren synchronisiert haben. Dies kann durch Hinzufügen von präzisen [Echtzeituhr (RTC) Geräten](de-Real%20Time%20Clock.md) wie [DS3231](https://www.adafruit.com/product/3013)zu allen Timern erreicht werden. NTP kann so konfiguriert werden, dass es wie unten gezeigt zwischen den Timern arbeitet.

Auf allen Timern:

```
sudo apt-get install ntp
```

Bearbeiten Sie auf dem Master /etc/npd.conf und fügen Sie ähnliche Zeilen hinzu:

```
broadcast 192.168.123.255
restrict 192.168.123.0 mask 255.255.255.0
```

Bearbeiten Sie auf den Slaves /etc/npd.conf und fügen Sie ähnliche Zeilen hinzu:

```
server 192.168.123.1
```

Auf allen Timern:

```
sudo systemctl stop systemd-timesyncd
sudo systemctl disable systemd-timesyncd
sudo /etc/init.d/ntp restart
```

### Zufallszahlengenerator

Der Zufallszahlengenerator hilft bei der Verbesserung der WiFi-Konnektivität (behält die Entropie für die Verschlüsselung bei). Aktivieren Sie das Hardware-RNG, um die verfügbare Entropie zu verbessern.

```
sudo apt-get install rng-tools
```

Bearbeiten Sie /etc/default/rng-tools und kommentieren Sie die Zeile aus:

```
HRNGDEVICE=/dev/hwrng
```

Starten Sie dann rng-tools mit neu

```
sudo service rng-tools restart
```

### Anmerkungen

Verpasste / falsche Zwischenzeiten haben keinen Einfluss auf die Aufzeichnung der Rundenzeiten durch den Master-Timer.

Informationen zum Aktivieren der Ankündigung von Zwischenzeiten finden Sie in der Option "*Cluster / Split Timer*" auf der Seite *Einstellungen* im Abschnitt *Audiosteuerung*. Um Audioanzeigen zu aktivieren, wann ein Cluster- / Slave-Timer eine Verbindung herstellt und trennt, aktivieren Sie das Kontrollkästchen "*Cluster-Timer verbinden / trennen*" unter "*Anzeigetöne*". (Beachten Sie, dass diese Optionen nur sichtbar sind, wenn ein Cluster-Timer angeschlossen ist.)

Der Status der verbundenen Cluster-Timer kann auf der Seite *Einstellungen* im Abschnitt *System* angezeigt werden. (Diese Statusinformationen sind auch auf der Seite *Ausführen* verfügbar.) Die folgenden Elemente werden angezeigt:

* *Adresse* - Netzwerkadresse für den Cluster-Timer (Klicken Sie hier, um die Web-GUI für den Timer aufzurufen.)
* *S* oder *M* - Nach der Adresse wird ein 'S' angezeigt, wenn der Timer geteilt ist, oder ein 'M', wenn der Timer gespiegelt ist
* *Latenz: min avg max last* - Netzwerklatenz (in Millisekunden) für Heartbeat- / Abfragenachrichten
* *Disconns* - Häufigkeit, mit der der Cluster-Timer getrennt wurde
* *Kontakte* - Anzahl der Netzwerkkontakte mit dem Cluster-Timer
* *TimeDiff* - Zeitdifferenz (in Millisekunden) zwischen Systemuhren auf Master- und Cluster-Timer
* *UpSecs* - Anzahl der Sekunden, in denen der Cluster-Timer verbunden wurde
* *DownSecs* - Anzahl der Sekunden, in denen der Cluster-Timer getrennt wurde
* *Verfügbar* - Verfügbarkeitsbewertung (in Prozent) für den Cluster-Timer
* *LastContact* - Zeit (in Sekunden) seit dem letzten Kontakt mit dem Timer oder eine Statusmeldung

Bei normalem Betrieb werden die Rundenverlaufsdaten nicht auf den Slave-Timern gespeichert. Um die Rundenverlaufsdaten anzuzeigen und das Marshalling für einen Slave-Timer durchzuführen, klicken Sie auf die Schaltfläche '*Runden speichern*' am Slave-Timer, bevor das Rennen auf dem Master gespeichert oder verworfen wird, und wechseln Sie dann zur Seite *Marschall* des Slaves Timer.

Ein Slave kann auch ein Master sein, aber Sub-Splits werden nicht nach oben weitergegeben.

Wenn Sie einen Wi-Fi-basierten Cluster verwenden möchten, finden Sie Anweisungen zum Einrichten eines Zugangspunkts (Wi-Fi-Hotspot) unter
[https://www.raspberrypi.org/documentation/configuration/wireless/access-point.md](https://www.raspberrypi.org/documentation/configuration/wireless/access-point.md).
Lesen Sie auch [https://github.com/mr-canoehead/vpn_client_gateway/wiki/Configuring-the-Pi-as-a-WiFi-Access-Point](https://github.com/mr-canoehead/vpn_client_gateway/wiki/Configuring-the-Pi-as-a-WiFi-Access-Point)
and [https://superuser.com/questions/1263588/strange-issue-with-denyinterfaces-in-access-point-config](https://superuser.com/questions/1263588/strange-issue-with-denyinterfaces-in-access-point-config).
Fügen Sie `denyinterfaces wlan0` zu `/etc/dhcpcd.conf` und führen Sie `sudo nano /etc/network/interfaces.d/wlan0`
aus um

```
allow-hotplug wlan0
iface wlan0 inet static
	address 10.2.2.1
	netmask 255.255.255.0
	network 10.2.2.0
	broadcast 10.2.2.255
	post-up systemctl restart hostapd
```

hinzuzufügen, damit dhcpd mit hostapd gut funktioniert.
