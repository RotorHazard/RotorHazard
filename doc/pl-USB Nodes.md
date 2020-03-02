# Odnogi USB

Sprzętowe odnogi mogą być podłączone bezpośrednio do systemu poprzez USB. Odnoga/odbiornik może być stworzony przez Arduino, moduł RX5808 i sześć kabelków, w sposób wskazany poniżej.
![USB odnoga okablowanie](img/USB_node_wiring.jpg)
![USB odnoga budowa1](img/USB_node_built1.jpg)
![USB odnoga budowa2](img/USB_node_built2.jpg)

Powyższa konstrukcja używa Arduino Nano V3.0 16M 5V ATmega328P (możesz go znaleźć na [eBay](https://www.ebay.com/sch/i.html?_nkw=Arduino+Nano+V3.0+16M+5V+ATmega328P)) i moduł RX5808 (możesz go znaleźć na [banggood](https://www.banggood.com/search/rx5808-module.html) i [eBay](https://www.ebay.com/sch/i.html?_nkw=rx5808+module)).

Odnogi USB mogą być podłączone do portów USB Raspberry Pi w standardowej konstrukcji timera RotorHazard albo mogą być podłączone do [każdego komputera na jakim jest włączony serwer RotorHazard](Software%20Setup.md#otheros). Odnogi USB wymagają skonfigurowania w sekcji "SERIAL_PORTS" w pliku "src/server/config.json".

#### Raspberry Pi

Na Raspberry Pi, podłączona odnoga USB będzie odnosiła się do nazwy portu np. "/dev/ttyUSB0".  Komenda ```ls /dev/ttyUSB*``` pokazuje obecnie używane porty szeregowe USB. Plik "src/server/config.json" powinien zawierać następujący wpis:
```
	"SERIAL_PORTS": ["/dev/ttyUSB0"],
```
Wiele odnóg USB powinno być skonfigurowanych następująco:
```
	"SERIAL_PORTS": ["/dev/ttyUSB0","/dev/ttyUSB1"],
```

#### Komputer Windows

Na komputerze z systemem Windows, podłączona odnoga USB będzie odnosiła się do nazwy portu szeregowego, np."COM5". Obecnie używane porty mogą zostać sprawdzone w Menadżerze Urządzeń pod "Porty (COM & LPT)" -- kiedy odnoga USB jest podłączana, wpis powinien się pojawić. Może być konieczne zainstalowanie albo aktualizacja sterownika (nazywającego się "USB-SERIAL"). Plik "src/server/config.json" powinien zawierać następujący wpis:
```
	"SERIAL_PORTS": ["COM5"],
```
Wiele odnóg USB powinno być skonfigurowanych następująco:
```
	"SERIAL_PORTS": ["COM5","COM6"],
```

<br/>

-----------------------------

Zobacz również:
[doc/Hardware Setup.md](Hardware%20Setup.md)
[doc/Software Setup.md](Software%20Setup.md)
[doc/User Guide.md](User%20Guide.md)
