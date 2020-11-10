# Videoempfängersteuerung

_Diese Funktionalität befindet sich noch in der Beta-Phase und entwickelt sich ständig weiter._

RotorHazard unterstützt die drahtlose Kommunikation mit Videoempfängern. Die anfängliche Unterstützung für den ClearView2.0-Empfänger ist freigegeben. Die folgenden Funktionen werden mit dieser Funktionalität hinzugefügt:

* Veröffentlichen Sie Rundenzeiten und Teilungen auf dem OSD des Videoempfängers
* Veröffentlichen Sie Meldungen zum Rennstatus (Bereit, Los, Stopp) im OSD
* Veröffentlichen Sie andere Prioritätsnachrichten im OSD
* Synchronisieren Sie die Frequenzen der angeschlossenen Videoempfänger
* Zeigen Sie an, ob Videoempfänger an ein Signal gebunden sind

_Hinweis: Nachrichten werden derzeit NICHT mit der Rennuhr synchronisiert._

## OSD-Nachrichten

### Rennnachrichten

Rennstatusmeldungen werden automatisch angezeigt. Die Nachrichten ändern sich abhängig von den aktuellen _Race Format_-Einstellungen, insbesondere _Win Condition_. Rennnachrichten folgen im Allgemeinen diesem Muster:
`[Rank]-[Callsign] [Last Lap Number]|[Last Lap Time] / [+/-][Split] [Split Callsign]`
Zum Beispiel:
`1-Hazard L3|0:24.681 / -0:04.117 RYANF55`

* Die meisten Rennmodi: Die angezeigte Aufteilung ist die Differenz der gesamten Rennzeit zum vorausfahrenden Piloten, bis der nächste Pilot überquert, und wird dann auf den dahinter liegenden Piloten aktualisiert.
* Schnellste Runde: Der Split ist immer der nächste Pilot. Wenn auf dem ersten Platz, ist der Split wieder die beste Kursrunde.
* Schnellste 3 aufeinanderfolgende Zeit: Die Aufteilung wird durch die aktuell beste aufeinanderfolgende 3-Runden-Zeit des Piloten ersetzt.

Lange Pilotrufzeichen werden für das OSD abgeschnitten.

Zeichen, die zum Präfixieren der Rangfolge und der Rundennummer verwendet werden, können im _VRx-Kontrollfeld in _Einstellungen_ konfiguriert werden.

### Benutzerdefinierte Nachrichten

Im Bereich "Nachricht senden" auf der Seite "Einstellungen" werden Nachrichten, die mit "An VRx senden" markiert sind, auf allen angeschlossenen Videoempfänger-OSDs angezeigt.

## Einstellungen

Der Status der angeschlossenen Empfänger wird im Bedienfeld _VRx Control_ in _Settings_ angezeigt. Empfänger werden einem Knoten zugewiesen, der für Videofrequenz- und OSD-Nachrichten folgt.

**WICHTIG: Durch Ändern der Knoten- / Sitznummer in diesem Bereich wird der VRx sofort geändert, und ein Pilot kann den Videokontakt verlieren. MIT DISKRETION VERWENDEN.**

Hier können Zeichen festgelegt werden, mit denen der Rang und die Rundennummer in der OSD-Nachricht vorangestellt werden.

## Software-Setup in RotorHazard

### Installieren und konfigurieren Sie einen MQTT-Broker.

Der MQTT-Broker muss nicht auf demselben System wie der RorotHazard-Server installiert sein, vereinfacht jedoch die Einrichtung und Wartung. So installieren Sie auf einem Raspberry Pi vom Terminal aus:

sudo apt update
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable mosquitto.service

### Fügen Sie den Block VRX_CONTROL zu config.json hinzu.

Setzen Sie "ENABLED" auf "true" und "HOST" auf die IP-Adresse Ihres MQTT-Brokers (verwenden Sie "localhost", wenn es sich auf demselben System wie der RotorHazard-Server befindet). Beispiel:

```
"VRX_CONTROL": {
    "HOST": "localhost",
    "ENABLED": true
},
```

Die Standardkonfigurationsdatei befindet sich in `RotorHazard/src/server/config.json`.

### Installieren Sie die ClearView Receiver Library.

Für die Kommunikation mit ClearView-Geräten ist eine Python-Bibliothek erforderlich. Derzeit ist ClearView2.0 der einzige unterstützte Empfänger, daher ist diese Installation erforderlich.

```
cd ~
git clone https://github.com/ryaniftron/clearview_interface_public.git --depth 1
cd ~/clearview_interface_public/src/clearview-py
python -m pip install -e .
```

## Einrichten des ClearView2.0-Empfänger

Stellen Sie sicher, dass Ihr ClearView2.0-Empfänger [auf die letztgültige Version](http://proteanpaper.com/fwupdate.cgi?comp=iftrontech&manu=2) aktualisiert ist.

Ein ClearView-Kommunikationsmodul ermöglicht es ClearView2.0, Befehle aus einem Netzwerk zu empfangen. Das CVCM wird im Handel erhältlich sein. Benutzer können ein CVCM mit einer ESP32-Entwicklungskarte und einer CV2-Aktualisierungskarte erstellen. Weitere Informationen und Anweisungen zum Erstellen finden Sie im Code-Repo [ClearView Interface](https://github.com/ryaniftron/clearview_interface_public).
