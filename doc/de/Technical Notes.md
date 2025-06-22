# Technische Hinweise

Der RotorHazard Race Timer ist ein Open-Source-Zeitmesssystem mit mehreren Knoten, das anhand der Videosignale von FPV-Fahrzeugen ermittelt, wann sie die Start- / Ziellinie überqueren. Das Herzstück des Systems ist ein Raspberry Pi, und jeder Knoten verfügt über ein dediziertes Arduino Nano- und RX5808-Modul.

Auf dem Raspberry Pi wird das Raspbian-Betriebssystem (mit Desktop) ausgeführt, und das RotorHazard-System verwendet eine in Python geschriebene Serverkomponente. Die Standalone-Server-Version verwendet die Bibliothek "[Flask](http://flask.pocoo.org)", um Webseiten über eine Netzwerkverbindung für einen Computer oder ein tragbares Gerät bereitzustellen. In einer SQL-Datenbank werden Einstellungen (über die Erweiterung '[SQLAlchemy](https://www.sqlalchemy.org)' und die Erweiterung '[gevent](http://www.gevent.org)' gespeichert. Diese Bibliothek wird verwendet, um asynchrone Ereignisse und Threading zu behandeln. Die bereitgestellten Webseiten verwenden die Javascript-Bibliothek '[Articulate.js](http://articulate.purefreedom.com)', um Sprachansagen zu generieren.

Das RotorHazard-Projekt wird hier auf GitHub gehostet: https://github.com/RotorHazard/RotorHazard
