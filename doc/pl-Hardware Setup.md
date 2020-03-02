# Instrukcja Ustawienia Sprzętu

## Lista Części

### Odnoga odbiornika (z tej listy stworzysz jedną - maksymalnie można używać ośmiu)
* 1 x [Arduino Nano](https://www.ebay.com/sch/i.html?_nkw=Arduino+Nano+V3.0+16M+5V+ATmega328P)
* 1 x [RX5808 module](https://www.banggood.com/search/rx5808-module.html) with SPI mod (modules with date code 20120322 are known to work)
* 3 x rezystor 1k Ohm 
* 1 x rezystor 100k Ohm 
* przewód 26 AWG i 30 AWG

### Komponenty Systemu
* 1 x Raspberry Pi3 (użytkownicy Pi2 raportowali problemy, kiedy było podłączone więcej odnóg)
* karta Micro SD - 8 GB (minimum)
* przewód 26 AWG i 30 AWG (do połączenia do każdej odnogi odbiornika)
* wydrukowana w 3D obudowa na komponenty elektroniczne
* zasilacz 5V, 3A minimum (albo zasilacz 12V jeśli używane są regulatory na płytce)

### Dodatkowe komponenty
* ekranowanie RF (zobacz poniżej)

### Opcjonalne komponenty
* Kabel Ethernet, 15m plus
* Zewnętrzny kabel zasilający, 15m plus
* Router sieciowy
* Laptop/tablet
* Paski LED-owe WS2812b

## Ustawienie sprzętu

### RX5808 - Odbiorniki Wideo
Upewnij się, że odbiorniki wspierają protokół SPI. *Większość sprzedawanych dziś odbiorników wspiera SPI.* Jeśli nie, zmodyfikuj odbiorniki RX5808, żeby wspierały ten protokół, w następujący sposób:

Zdejmij ekranowanie z odbiornika, przytwierdzone za pomocą kilku lutów na brzegach. Użyj plecionki żeby pozbyć się cyny (możesz dodać odrobinę świeżej cyny z topnikiem). Bądź ostrożny, żeby nie uszkodzić padów połączonych do masy. Przeważnie dookoła odbiornika są małe otwory, które mogą zostać użyte do zdjęcia ekranowania.

Pozbądź się następującego rezystora:
![RX5808 spi mod](img/rx5808-new-top.jpg)

Ekranowanie powinno zostać przylutowane z powrotem, po wyjęciu rezystora.

### Odnogi odbiornika
Kompletne okablowanie każdego Arduino i odbiornika RX5808
![okablowanie odnogi odbiornika](img/Receivernode.png)

Uwaga: Prosty odbiornik może być również skonstruowany i podłączony przez USB - zobacz [doc/USB Nodes.md](USB%20Nodes.md).

### Złożenie Systemu
Skompletuj okablowanie każdej odnogi i Raspberry Pi.

Uwaga: Upewnij się, że wszystkie odnogi i Raspberry Pi są podłączone do wspólnej masy. Jeśli tak nie jest, transfer danych może działać nieprawidłowo.
![okablowanie systemu](img/D5-i2c.png)

### Dodaj ekranowanie kierunkowe
Kierunkowe ekranowanie znacząco poprawia zdolność systemu do odrzucania fałszywych pezelotów przez bramkę. Pozwala to operatorowi na podniesienie ich czułości i budowanie torów przebiegających bliżej bramki z timerem. Skonstruuj kierunkowe ekranowanie pozostawiając niewielką linię między timerem, a mierzoną bramką, ale blokując sygnały RF z innych kierunków. Najbardziej popularne opcje, aby to osiągnąć to: 
* Połóż system w metalowym pojemniku, z jedną stroną otwartą, np. w pojemniku na amunicję, wiaderku po farbie czy metalowym wiadrze albo obudowie od komputera. Zaleca się podłączenie elektrycznej masy timera do tego pojemnika.
* Wykop dziurę w ziemi i umieść tam pojemnik
* Owiń obudowę swojego timera miedzianą taśmą

### Wsparcie dla LEDów WS2812b
Piny w zielonym prostokącie są już używane przez timer. Piny zaznaczone na czerwono są tam, gdzie możesz podłączyć sygnał i masę z LED-ów WS2812b. Ledy potrzebują oddzielnego źródła zasilania. Zobacz wsparcie dla WS2812b w sekcji Ustawienia Programowe (Software Setup). 
![okablowanie LED](img/GPIO.jpg)

### Dodatkowe Czujniki
Czujniki (takie jak BME280 and INA219) mogą być podłączone do magistrali I2C. Zobacz pliki '..._sensor.py' w folderze "src/interface" dla przykładów zastosowania. Czujniki muszą być uwzględnione w pliku "src/server/config.json" -- w przykładowej konfiguracji poniżej czujnik BME280 jest skonfigurowany na linii I2C pod adresem 0x76 (jako "Climate") i czujnik INA219 jest skonfigurowany pod adresem 0x40 i 0x41.
```
    "SENSORS": {
            "i2c:0x76": {
                    "name": "Temperatura"
            },
            "i2c:0x40": {
                    "name": "Bateria",
                    "max_current": 0.1
            },
            "i2c:0x41": {
                    "name": "Pi",
                    "max_current": 2
            }
    },
```

### Wiele Timerów
Wiele timerów RotorHazard może być połączonych razem (np. dla pomiaru międzyczasów albo w trybie "odbicia lustrzanego") -- zobacz [doc/Cluster.md](Cluster.md).

-----------------------------

Zobacz Również:<br/>
[doc/USB Nodes.md](pl-USB%20Nodes.md)<br/>
[doc/Software Setup.md](Software%20Setup.md)<br/>
[doc/User Guide.md](User%20Guide.md)
