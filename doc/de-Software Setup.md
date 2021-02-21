# Anweisungen zur Software-Einrichtung

Die zentrale Softwarekomponente des RotorHazard-Systems ist der in Python geschriebene Server, der seine Funktionen ausführt und Webseiten für Browser bereitstellt. In einem Standard-Setup wird der Server auf einem RaspberryPi ausgeführt. (Es ist auch möglich, RotorHazard auf anderen Hardwaretypen auszuführen - siehe Abschnitt [Andere Betriebssysteme](#otheros) weiter unten.)

## System installieren (Raspberry Pi)

Hinweis: Für viele der folgenden Setup-Befehle muss der Rasperry Pi über einen Internetzugang verfügen.

Beginnen Sie mit der Installation von Raspbian und befolgen Sie die offiziellen Anweisungen hier: https://www.raspberrypi.org/downloads/raspbian/. Sie können entweder Desktop oder Lite verwenden.

Konfigurieren Sie die Schnittstellenoptionen auf dem Raspberry Pi.
Öffnen Sie ein Terminalfenster und geben Sie den folgenden Befehl ein:

```
sudo raspi-config
```

Wählen Sie Schnittstellenoptionen und aktivieren Sie: SSH, SPI und I2C.

Führen Sie ein Systemupdate und -upgrade durch (dies kann einige Minuten dauern):

```
sudo apt-get update && sudo apt-get upgrade
```

Installieren Sie Python und die Python-Treiber für das GPIO.

```
sudo apt install python-dev libffi-dev python-smbus build-essential python-pip git scons swig python-rpi.gpio
```

Installieren Sie die Funktionsoberfläche in Python

```
sudo pip install cffi
```

Aktualisieren Sie die i2c-Baudrate

```
sudo nano /boot/config.txt
```

Fügen Sie am Ende der Datei die folgenden Zeilen hinzu:

```
dtparam=i2c_baudrate=75000
core_freq=250
```

Hinweis: In der ersten Zeile wird die Übertragungsrate auf dem I2C-Bus festgelegt (der zur Kommunikation mit den Arduino-Knotenprozessoren verwendet wird). Die zweite Zeile behebt ein potenzielles Problem mit variabler Taktrate, das [hier](https://www.abelectronics.co.uk/kb/article/1089/i2c--smbus-and-raspbian-stretch-linux) beschrieben wird. Wenn ein Raspberry Pi 4 verwendet wird, muss möglicherweise die zweite Zeile weggelassen werden.

Speichern und beenden Sie die Datei mit Strg-X

Installieren Sie den RotorHazard-Code unter '/home/pi/' auf dem Raspberry Pi wie folgt: Gehen Sie zur [Seite mit der neuesten Version](https://github.com/RotorHazard/RotorHazard/releases/latest) für das Projekt und notieren Sie das Versionscode. Ersetzen Sie in den folgenden Befehlen die beiden Vorkommen von "1.2.3" durch den aktuellen Versionscode und geben Sie die folgenden Befehle ein:

```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/1.2.3 -O temp.zip
unzip temp.zip
mv RotorHazard-1.2.3 RotorHazard
rm temp.zip
```

Installieren Sie die RotorHazard-Serverabhängigkeiten (haben Sie etwas Geduld, dieser Befehl kann einige Minuten dauern):

```
cd ~/RotorHazard/src/server
sudo pip install -r requirements.txt
```

Aktualisieren Sie die Berechtigungen im Arbeitsordner:

```
cd ~/RotorHazard/src
sudo chmod 777 server
```

*Hinweis: Wenn RotorHazard bereits installiert ist, lesen Sie den folgenden Abschnitt [Aktualisieren einer vorhandenen Installation](#update).*

## Installieren Sie den Code für Empfängerknoten (Arduinos).

Arduino 1.8+ ist erforderlich. Download von https://www.arduino.cc/en/Main/Software

*Der Knotencode und die Serverversion müssen übereinstimmen. Verwenden Sie den 'Knoten'-Code, der in dem zuvor heruntergeladenen Servercode enthalten ist. Laden Sie keine andere Datei direkt von GitHub herunter.*

Der Knotencode kann mit der [Eclipse IDE](https://www.eclipse.org/eclipseide/) und der "[Eclipse C ++ - IDE für Arduino](https://marketplace.eclipse.org/content) bearbeitet und erstellt werden / eclipse-c-ide-arduino) "Plugin (oder die altmodische Methode mit der Arduino IDE). In Eclipse kann das Knotencode-Projekt über "Datei | Projekte aus Dateisystem öffnen ..." geladen werden.

Wenn Sie keine RotorHazard-Platine verwenden, bearbeiten Sie die Datei 'src/node/config.h' und konfigurieren Sie vor dem Hochladen den Wert '#define NODE_NUMBER' für jeden Knoten. Für den ersten Knoten setzen Sie NODE_NUMBER auf 1, für den zweiten auf 2 usw.

```
// Node Setup -- Set node number here (1 - 8)
#define NODE_NUMBER 1
```

Die Auswahl der Hardwareadresse ist auch möglich, indem die Hardwarestifte gemäß der [veröffentlichten Spezifikation](https://github.com/RotorHazard/RotorHazard/wiki/Specification:-Node-hardware-addressing) geerdet werden.

## Installieren Sie optionale Komponenten

### Echtzeituhr

Durch die Installation eines Echtzeituhrmoduls kann der RotorHazard-Timer das korrekte Datum und die korrekte Uhrzeit beibehalten, auch wenn keine Internetverbindung verfügbar ist. Weitere Informationen finden Sie unter '[doc/Real Time Clock.md](de-Real%20Time%20Clock.md)'.

### WS2812b LED-Unterstützung

Die ws2812b-Steuerelemente werden von folgendem Projekt bereitgestellt:

[https://github.com/jgarff/rpi_ws281x](https://github.com/jgarff/rpi_ws281x)

Klonen Sie das Repository auf den Pi und starten Sie Scons:

```
cd ~
sudo git clone https://github.com/jgarff/rpi_ws281x.git
cd rpi_ws281x
sudo scons
```

Installieren Sie die Python-Bibliothek:

```
cd python
sudo python setup.py install
```

Hinweis: Der Wert **LED_COUNT** muss in der Datei `src/server/config.json` festgelegt werden. Die Standardkonfiguration der LED-Einstellungen finden Sie in der Datei "src/server/config-dist.json". Folgende Elemente können eingestellt werden:

```
LED_COUNT:  Anzahl der LED-Pixel im Streifen (oder Panel)
LED_PIN:  GPIO-Pin mit den Pixeln verbunden (Standard 10 verwendet SPI '/dev/spidev0.0')
LED_FREQ_HZ:  LED-Signalfrequenz in Hertz (normalerweise 800000)
LED_DMA:  DMA-Kanal zur Signalerzeugung (Standard 10)
LED_INVERT:  True, um das Signal zu invertieren (bei Verwendung der NPN-Transistorpegelverschiebung)
LED_CHANNEL:  Setzen Sie für die GPIOs 13, 19, 41, 45 oder 53 auf '1'
LED_STRIP:  Streifentyp und Farbreihenfolge (Standard ist 'GRB')
LED_ROWS:  Anzahl der Zeilen im LED-Panel-Array (1 für Streifen)
PANEL_ROTATE:  Optionaler Panel-Rotationswert (Standard 0)
INVERTED_PANEL_ROWS:  Optionale Panel-Zeilenumkehrung (Standardwert false)
```

Falls angegeben, muss der Wert **LED_STRIP** einer der folgenden Werte sein: 'RGB', 'RBG', 'GRB', 'GBR', 'BRG', 'BGR', 'RGBW', 'RBGW', 'GRBW' , 'GBRW', 'BRGW', 'BGRW'

Die LED-Bibliothek erfordert direkten Speicher und GPIO-Zugriff. Wenn aktiviert, muss RotorHazard mit `sudo` ausgeführt werden.

```
sudo python server.py
```

### INA219 Spannungs- / Stromunterstützung

Die ina219-Schnittstelle wird von folgendem Projekt bereitgestellt:

https://github.com/chrisb2/pi_ina219

Klonen Sie das Repository auf den Pi:

```
cd ~
sudo git clone https://github.com/chrisb2/pi_ina219.git
cd pi_ina219
```

Installieren Sie die Python-Bibliothek:

```
sudo python setup.py install
```

### BME280 Temperaturunterstützung

Die bme280-Schnittstelle wird von folgendem Projekt bereitgestellt:
https://github.com/rm-hull/bme280

Klonen Sie das Repository auf den Pi:

```
cd ~
sudo git clone https://github.com/rm-hull/bme280.git
cd bme280
```

Installieren Sie die Python-Bibliothek:

```
sudo python setup.py install
```

### Java-Unterstützung

Java ermöglicht die Berechnung von IMD-Scores. Wenn Sie mit RASPBIAN MIT GRAFISCHER OBERFLÄCHE begonnen haben, sollte dieser Schritt nicht erforderlich sein, da Java standardmäßig installiert ist. Andernfalls:

```
sudo apt install default-jdk-headless
```

## System vorbereiten

### System neu starten

Nachdem die obigen Einrichtungsschritte ausgeführt wurden, sollte das System neu gestartet werden, indem folgendes eingegeben wird:

```
sudo reboot
```

### System starten

Die folgenden Anweisungen starten den Webserver auf dem Himbeer-Pi und ermöglichen die vollständige Kontrolle und Konfiguration des Systems, um Rennen durchzuführen und Rundenzeiten zu sparen.

#### Manueller Start

Öffnen Sie ein Terminal und geben Sie folgendes ein:

```
cd ~/RotorHazard/src/server
python server.py
```

Der Server kann durch Drücken von Strg-C gestoppt werden

#### Automatischer Start beim Hochfahren

So konfigurieren Sie das System so, dass der RotorHazard-Server beim Hochfahren automatisch gestartet wird:

Erstellen Sie eine Servicedatei:

```
sudo nano /lib/systemd/system/rotorhazard.service
```

mit folgenden Inhalten

```
[Unit]
Description=RotorHazard Server
After=multi-user.target

[Service]
WorkingDirectory=/home/pi/RotorHazard/src/server
ExecStart=/usr/bin/python server.py

[Install]
WantedBy=multi-user.target
```

Speichern und beenden (STRG-X, Y, ENTER).

Berechtigungen anpassen:

```
sudo chmod 644 /lib/systemd/system/rotorhazard.service
```

Aktivieren Sie den Dienst:

```
sudo systemctl daemon-reload
sudo systemctl enable rotorhazard.service
sudo reboot
```

#### Beenden des Serverdienstes

Wenn der RotorHazard-Server während des Startvorgangs als Dienst gestartet wurde, kann er mit einem Befehl wie dem folgenden gestoppt werden:

```
sudo systemctl stop rotorhazard
```

Geben Sie Folgendes ein, um den Dienst zu deaktivieren (damit er beim Systemstart nicht mehr ausgeführt wird):

```
sudo systemctl disable rotorhazard.service
```

### System herunterfahren

Ein Herunterfahren des Systems sollte immer durchgeführt werden, bevor der Netzstecker gezogen wird, indem Sie entweder auf der Seite "Einstellungen" auf die Schaltfläche "Herunterfahren" klicken oder Folgendes in ein Terminal eingeben:

```
sudo shutdown now
```

<a id="update"></a>

### Aktualisieren einer vorhandenen Installation

Vor dem Update sollte jeder aktuell ausgeführte RotorHazard-Server gestoppt werden. Wenn es als Dienst installiert ist, kann es mit einem Befehl wie dem folgenden gestoppt werden:

```
sudo systemctl stop rotorhazard
```

So aktualisieren Sie eine vorhandene RotorHazard-Installation: Gehen Sie zur Seite [Neueste Version](https://github.com/RotorHazard/RotorHazard/releases/latest) für das Projekt und notieren Sie den Versionscode. Ersetzen Sie in den folgenden Befehlen die beiden Vorkommen von "1.2.3" durch den aktuellen Versionscode und geben Sie die folgenden Befehle ein:

```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/1.2.3 -O temp.zip
unzip temp.zip
mv RotorHazard RotorHazard.old
mv RotorHazard-1.2.3 RotorHazard
rm temp.zip
cp RotorHazard.old/src/server/config.json RotorHazard/src/server/
cp RotorHazard.old/src/server/database.db RotorHazard/src/server/
```

Die vorherige Installation landet im Verzeichnis 'RotorHazard.old', das gelöscht oder verschoben werden kann.

Die RotorHazard-Serverabhängigkeiten sollten ebenfalls aktualisiert werden (haben Sie etwas Geduld, dieser Befehl kann einige Minuten dauern):

```
cd ~/RotorHazard/src/server
sudo pip install --upgrade --no-cache-dir -r requirements.txt
```

### Aktivieren Sie die Portweiterleitung

Der RotorHazard-Server verwendet standardmäßig Port 5000, da dies für einige Integrationen von Drittanbietern erforderlich ist. Während Sie den Port über `HTTP_PORT` in der Datei `config.json` ändern können, besteht ein besserer Ansatz häufig darin, den Web-Standardport von 80 bis 5000 weiterzuleiten.

Standardmäßig verwendet HTTP Port 80. Für andere Werte muss der Port als Teil der in Client-Browsern eingegebenen URL enthalten sein. Wenn andere Webdienste auf dem Pi ausgeführt werden, wird Port 80 möglicherweise bereits verwendet, und die Wiederverwendung führt zu Problemen. Wenn Port 80 direkt über `HTTP_PORT` verwendet wird, muss der Server möglicherweise mit dem Befehl *sudo* ausgeführt werden. Mit den folgenden Befehlen wird der Server auf Port 5000 ausgeführt, aber das System sendet den Datenverkehr von Port 80 an Port 80.

```
sudo iptables -A PREROUTING -t nat -p tcp --dport 80 -j REDIRECT --to-ports 5000
sudo iptables-save
sudo apt-get install iptables-persistent
```

Nach dem Ausführen dieser Befehle ist RotorHazard an beiden Ports 80 und 5000 verfügbar. Wenn es an Port 80 verfügbar ist, können Sie den Port beim Zugriff auf den Server deaktivieren: `http://127.0.0.1`
<br/>

---

<a id="otheros"></a>

### Andere Betriebssysteme

Der RotorHazard-Server kann auf jedem Computer mit einem Betriebssystem ausgeführt werden, das Python unterstützt. In diesen alternativen Konfigurationen können ein oder mehrere Hardwareknoten über USB verbunden sein. Weitere Informationen finden Sie unter [doc/USB Nodes.md](de-USB%20Nodes.md). Der Server kann auch mit simulierten (Schein-) Knoten ausgeführt werden.

So installieren Sie den RotorHazard-Server auf diesen Systemen:

1. Wenn auf dem Computer Python noch nicht installiert ist, laden Sie Python Version 2.7 von https://www.python.org/downloads herunter und installieren Sie es. Um zu überprüfen, ob Python installiert ist, öffnen Sie eine Eingabeaufforderung und geben Sie ```python --version``` ein
2. Laden Sie von RotorHazard [Veröffentlichungsseite auf github](https://github.com/RotorHazard/RotorHazard/releases) die Datei "Quellcode (zip)" herunter.
3. Entpacken Sie die heruntergeladene Datei in ein Verzeichnis (auch bekannt als Ordner) auf dem Computer.
4. Öffnen Sie eine Eingabeaufforderung und navigieren Sie zum Verzeichnis `src/server` in den RotorHazard-Dateien (mit dem Befehl 'cd').
5. Installieren Sie die RotorHazard-Serverabhängigkeiten mithilfe der Datei 'requirements.txt' mit einem der folgenden Befehle (Beachten Sie, dass für diesen Befehl möglicherweise Administratorzugriff auf den Computer erforderlich ist und der Befehl einige Minuten dauern kann):

* Auf einem Windows-System lautet der zu verwendende Befehl wahrscheinlich:<br/>```python -m pip install -r requirements.txt```<br/><br/>
* Auf einem Linux-System lautet der zu verwendende Befehl wahrscheinlich:<br/>```sudo pip install -r requirements.txt```<br/>

So führen Sie den RotorHazard-Server auf diesen Systemen aus:

1. Öffnen Sie eine Eingabeaufforderung und navigieren Sie zum Verzeichnis `src/server` in den RotorHazard-Dateien (falls nicht bereits vorhanden).
2. Geben Sie ```python server.py``` ein.
3. Wenn der Server ordnungsgemäß gestartet wird, sollten verschiedene Protokollmeldungen angezeigt werden, darunter eine wie folgt:

   ```
   Running http server at port 5000
   ```
4. Der Server kann durch Drücken von Strg-C gestoppt werden

Wenn Hardwareknoten über USB verbunden sind, müssen sie im Abschnitt `SERIAL_PORTS` in der Konfigurationsdatei "src/server/config.json" konfiguriert werden (siehe [doc/USB Nodes.md](de-USB%20Nodes.md) für Details).

Wenn keine Hardwareknoten konfiguriert sind, arbeitet der Server mit simulierten (Schein-) Knoten. In diesem Modus kann die Web-GUI-Oberfläche untersucht und getestet werden.

Um die Web-GUI-Oberfläche anzuzeigen, öffnen Sie einen Webbrowser und geben Sie in die Adressleiste Folgendes ein: `localhost:5000` (Wenn der HTTP_PORT-Wert in der Konfiguration geändert wurde, verwenden Sie diesen Wert anstelle von 5000). Wenn der Server ausgeführt wird, sollte die RotorHazard-Hauptseite angezeigt werden. Beachten Sie, dass für den Rennleiter reservierte Seiten (Admin / Einstellungen) mit dem in der Konfiguration angegebenen Benutzernamen und Passwort passwortgeschützt sind.
<br/>

---

<a id="logging"></a>

### Protokollierung

Der RotorHazard-Server generiert "Protokoll" -Nachrichten mit Informationen zu seinen Vorgängen. Unten finden Sie eine Beispielkonfiguration für die Protokollierung:

```
    "LOGGING": {
        "CONSOLE_LEVEL": "INFO",
        "SYSLOG_LEVEL": "NONE",
        "FILELOG_LEVEL": "INFO",
        "FILELOG_NUM_KEEP": 30,
        "CONSOLE_STREAM": "stdout"
    }
```

Die folgenden Protokollstufen können angegeben werden: DEBUG, INFO, WARNING, WARN, ERROR, FATAL, CRITICAL, NONE

Wenn der Wert FILELOG_LEVEL nicht NONE ist, generiert der Server Protokolldateien im Verzeichnis `src/server/logs`. Bei jedem Start des Servers wird eine neue Protokolldatei erstellt, wobei jede Datei einen eindeutigen Namen hat, der auf dem aktuellen Datum und der aktuellen Uhrzeit basiert (d. H. "Rh_20200621_181239.log"). Wenn Sie FILELOG_LEVEL auf DEBUG setzen, werden detailliertere Protokollmeldungen in der Protokolldatei gespeichert. Dies kann beim Debuggen von Problemen hilfreich sein.

Der Wert FILELOG_NUM_KEEP gibt die Anzahl der zu speichernden Protokolldateien an. Der Rest wird gelöscht (älteste zuerst).

Der CONSOLE_STREAM-Wert kann "stdout" oder "stderr" sein.

Wenn der Wert SYSLOG_LEVEL nicht NONE ist, sendet der Server Protokollnachrichten an das im Host-Betriebssystem integrierte Protokollierungsdienstprogramm.

Das aktuelle Serverprotokoll wird möglicherweise über den Eintrag "Serverprotokoll anzeigen" im Dropdown-Menü angezeigt. Das angezeigte Protokoll ist "live", da es aktualisiert wird, wenn neue Nachrichten generiert werden. Das Protokoll kann in einem separaten Fenster angezeigt werden, indem Sie mit der rechten Maustaste auf den Menüpunkt "Serverprotokoll anzeigen" klicken und die Option "Link in neuem Fenster öffnen" (oder ähnlich) auswählen.

Durch Klicken auf die Schaltfläche "Text auswählen" wird der gesamte angezeigte Protokolltext ausgewählt, der dann kopiert und eingefügt werden kann. Durch Klicken auf die Schaltfläche "Protokolle herunterladen" wird eine ZIP-Archivdatei erstellt und heruntergeladen, die alle verfügbaren Protokolldateien sowie die aktuellen Konfigurations- und Datenbankdateien enthält. Die '.zip'-Archivdatei kann auch generiert werden, indem der Server mit dem folgenden Befehl ausgeführt wird: `python server.py --ziplogs`

Wenn Sie Probleme melden, wird dringend empfohlen, die Schaltfläche "Protokolle herunterladen" zu verwenden und die generierte ZIP-Datei einzuschließen.

<br/>

---

Siehe auch:
[doc/Hardware Setup.md](de-Hardware%20Setup.md)<br/>
[doc/USB Nodes.md](de-USB%20Nodes.md)<br/>
[doc/User Guide.md](de-User%20Guide.md)
