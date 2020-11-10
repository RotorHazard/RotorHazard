# USB Knoten

Hardwareknoten können über USB an das System angeschlossen werden. Ein Knoten kann mit einem Arduino, einem RX5808-Modul und sechs Drähten erstellt werden. mit den unten gezeigten Verbindungen.

![USB node wiring](img/USB_node_wiring.jpg)
![USB node built1](img/USB_node_built1.jpg)
![USB node built2](img/USB_node_built2.jpg)

Der obige Build verwendet ein Arduino Nano V3.0 16M 5V ATmega328P-Modul (zu finden bei [eBay](https://www.ebay.com/sch/i.html?_nkw=Arduino+Nano+V3.0+) 16M + 5V + ATmega328P)) und ein RX5808-Modul (zu finden unter [banggood](https://www.banggood.com/search/rx5808-module.html) und [eBay](https://www.ebay.com/sch/i.html?_nkw=rx5808+module)).

USB-Knoten können an die USB-Anschlüsse des Raspberry Pi eines Standard-RotorHazard-Timers angeschlossen oder an [jeden Computer, auf dem der RotorHazard-Server ausgeführt wird](Software%20Setup.md#otheros) angeschlossen werden. Die USB-Knoten müssen im Abschnitt "SERIAL_PORTS" in der Datei "src/server/config.json" konfiguriert werden.

#### Raspberry Pi

Auf dem Raspberry Pi wird auf einen angeschlossenen USB-Knoten mit einem seriellen Portnamen wie "/dev/ttyUSB0" verwiesen. Der Befehl `` `ls /dev/ttyUSB *` `` zeigt die aktuellen seriellen USB-Ports an. Die Datei "src/server/config.json" sollte einen Eintrag wie den folgenden enthalten:

```
	"SERIAL_PORTS": ["/dev/ttyUSB0"],
```

Mehrere USB-Knoten würden folgendermaßen konfiguriert:

```
	"SERIAL_PORTS": ["/dev/ttyUSB0","/dev/ttyUSB1"],
```

#### Windows Computer

Auf einem Windows-Computer wird auf einen angeschlossenen USB-Knoten mit einem seriellen Anschlussnamen wie "COM5" verwiesen. Die aktuellen Ports können im Windows-Geräte-Manager unter "Ports (COM & LPT)" angezeigt werden. Wenn der USB-Knoten angeschlossen ist, sollte sein Eintrag angezeigt werden. Möglicherweise muss der Treiber installiert oder aktualisiert werden (mit dem Namen "USB-SERIAL"). Die Datei "src/server/config.json" sollte einen Eintrag wie den folgenden enthalten:

```
	"SERIAL_PORTS": ["COM5"],
```

Mehrere USB-Knoten würden folgendermaßen konfiguriert:

```
	"SERIAL_PORTS": ["COM5","COM6"],
```

<br/>

---

Siehe auch:
[doc/Hardware Setup.md](de-Hardware%20Setup.md)
[doc/Software Setup.md](de-Software%20Setup.md)
[doc/User Guide.md](de-User%20Guide.md)
