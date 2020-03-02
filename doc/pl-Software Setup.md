# Instrukcje Konfiguracji Oprogramowania

Głównym komponentem oprogramowania systemu RotorHazard jest jego serwer, napisany w języku python, który operuje jego funkcjami i służy jako serwer web dla przeglądarki. W standardowym ustawieniu serwer jest włączony na Raspberry Pi. Możliwe jest włączenie RotorHazard na innym typie urządzenia – zobacz poniżej sekcję [Inne Systemy Operacyjne](#otheros).
## Zainstaluj System – (Raspberry Pi)
Uwaga: Wiele spośród wymienionych niżej komend wymaga połączenia z Internetem.

Zacznij od instalacji systemu Raspbian. Postępuj zgodnie z oficjalnymi instrukcjami na stronie:
https://www.raspberrypi.org/downloads/raspbian/. Możesz użyć wersji Desktop albo Lite.

Skonfiguruj interfejs na Raspberry Pi. Otwórz okno terminala i wpisz następujące komendy:
```
sudo raspi-config
```
Wybierz Interfacing Options i włącz: SSH, SPI, and I2C.

Wykonaj aktualizację systemu – może zająć kilka minut:
```
sudo apt-get update && sudo apt-get upgrade
```
Zainstaluj python i sterowniki python dla GPIO:
```
sudo apt-get install python-dev python-rpi.gpio libffi-dev python-smbus build-essential python-pip git scons swig
```
Zainstaluj interfejs funkcji dla python:
```
sudo pip install cffi
```
Zaktualizuj przepływność magistrali I2C:
```
sudo nano /boot/config.txt
```
Dodaj następujące linie na końcu pliku:
```
dtparam=i2c_baudrate=75000
core_freq=250
```
Zapisz i zamknij naciskając Ctrl+X.

Zainstaluj RotorHazard w '/home/pi/' na Raspberry Pi następujący sposób:
Idź do strony [Latest Release page](https://github.com/RotorHazard/RotorHazard/releases/latest)

„Ostatnie wydania” i zobacz jaka jest aktualna wersja kodu. W komendach poniżej zastąp znaki "1.2.3" aktualną wersję kodu i wpisz następujące komendy:
```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/1.2.3 -O temp.zip
unzip temp.zip
mv RotorHazard-1.2.3 RotorHazard
rm temp.zip
```
Zainstaluj tak zwane „zależności” serwera RotorHazard - bądź cierpliwy może zająć to kilka minut:
```
cd ~/RotorHazard/src/server
sudo pip install -r requirements.txt
```
Zmień ustawienia dostępu dla folderu:
```
cd ~/RotorHazard/src
sudo chmod 777 server
```
Uwaga: jeśli RotorHazard jest już zainstalowany, zobacz w sekcji poniżej[uaktualnianie obecnej instalacji](#update).

## Zainstaluj kod dla odnóg Arduino
Wymagane jest Arduino w wersji minimum 1.8. Ściągnij z:
https://www.arduino.cc/en/Main/Software

*Wersja oprogramowania dla odnóg oraz serwera muszą do siebie pasować. Użyj kodu przygotowanego dla odnóg z tego samego folderu, z którego instalujesz serwer. Nie ściągaj innych plików bezpośrednio z GitHub.*

Kod dla odnóg może być edytowany i przygotowany używając [Eclipse IDE](https://www.eclipse.org/eclipseide/) i "[Eclipse C++ IDE dla Arduino](https://marketplace.eclipse.org/content/eclipse-c-ide-arduino)" (albo “po-staremu” używając Arduino IDE). W Eclipse projekt zawierający kod dla odnóg może być otwarty poprzez „Plik”, „Otwórz projekt z pliku systemowego…”

Edytuj plik 'src/node/rhnode.cpp' i skonfiguruj wartość '#define NODE_NUMBER' dla każdej odnogi przed uaktualnieniem. Dla pierwszej odnogi ustaw NODE_NUMBER jako 1, dla drugiej ustaw jako 2, itd.
```
// Node Setup -- Set node number here (1 - 8)
#define NODE_NUMBER 1
```
Automatyczne numerowanie sprzętowe, również jest możliwe. Ustaw NODE_NUMBER jako 0, następnie połącz następujące piny z masą:

node #1: pin D5 podłączony do masy<br/>
node #2: pin D6 podłączony do masy<br/>
node #3: pin D7 podłączony do masy<br/>
node #4: pin D8 podłączony do masy<br/>
node #5: pin D5 i pin D4 podłączone do masy<br/>
node #6: pin D6 i pin D4 podłączone do masy<br/>
node #7: pin D7 i pin D4 podłączone do masy<br/>
node #8: pin D8 i pin D4 podłączone do masy


## Zainstaluj Opcjonalne Składniki
### Wsparcie dla LEDów WS2812b
Kontrola nad WS2812b jest dostarczona przez następujący projekt:
https://github.com/jgarff/rpi_ws281x

Sklonuj repozytorium na Pi i zainicjuj Scons:
```
cd ~
sudo git clone https://github.com/jgarff/rpi_ws281x.git
cd rpi_ws281x
sudo scons
```

Zainstaluj bibliotekę Python:
```
cd python
sudo python setup.py install
```

### Wsparcie dla miernika Napięcia/Natężenia INA219
Interfejs INA219 jest dostarczony przez następujący projekt:
https://github.com/chrisb2/pi_ina219

Sklonuj repozytorium na Pi:
```
cd ~
sudo git clone https://github.com/chrisb2/pi_ina219.git
cd pi_ina219
```
Zainstaluj bibliotekę Python:
```
sudo python setup.py install
```

### Wsparcie dla czujnika temperatury BME280
Interfejs BME280 jest dostarczony przez następujący projekt: https://github.com/rm-hull/bme280

Sklonuj repozytorium na Pi:
```
cd ~
sudo git clone https://github.com/rm-hull/bme280.git
cd bme280
```
Zainstaluj bibliotekę Python:
```
sudo python setup.py install
```

### Java Support
Java umożliwia kalkulację oceny zniekształceń intermodulacyjnych „IMD score”. Jeśli zainstalowałeś w kroku pierrwszym “RASPBIAN WITH DESKTOP”, ten krok nie powinien być konieczny. W innym wypadku:
```
sudo apt-get install openjdk-8-jdk
```

## Przygotuj System
### Zrestartuj System
Po tym jak powyższe kroki zostaną przeprowadzone system powinien być zrestartowany poprzez następujące komendy:
```
sudo reboot
```

### Uruchom System
Następujące instrukcje włączą serwer web na Raspberry Pi, umożliwiając pełną kontrolę oraz konfigurację systemu, aby móc przeprowadzać wyścigi i zapisywać czasy okrążeń.

#### Manualny Start
Otwórz okno terminal i wpisz:
```
cd ~/RotorHazard/src/server
python server.py
```
Serwer może być zatrzymany poprzez wciśnięcie Ctrl+C

#### Uruchamianie podczas rozruchu
Stwórz usługę
```
sudo nano /lib/systemd/system/rotorhazard.service
```
Z następującą zawartością:
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
Zapisz i wyjdź (CTRL+X, Y, ENTER).

Zaktualizuj ustawienia dostępu.
```
sudo chmod 644 /lib/systemd/system/rotorhazard.service
```

Komendy uruchamiania podczas rozruchu:
```
sudo systemctl daemon-reload
sudo systemctl enable rotorhazard.service
sudo reboot
```

### Wyłączanie Systemu
System powinien zawsze być prawidłowo wyłączony przed odłączeniem zasilania – poprzez wciśnięcie przycisku w Ustawieniach lub poprzez wpisanie następującej komendy:
```
sudo shutdown now
```

<a id="update"></a>
### Uaktualnianie obecnej instalacji

Przed uaktualnieniem, wszystkie obecnie uruchomione serwery powinny być zatrzymane. Jeśli serwer jest zainstalowany jako usługa, może być zatrzymany przez wpisanie komendy: `sudo systemctl stop rotorhazard`

Aby uaktualnić obecną instalację RotorHazard: Idź do [Latest Release page](https://github.com/RotorHazard/RotorHazard/releases/latest) „Ostatnie wydania” i zobacz jaka jest aktualna wersja kodu. W komendach poniżej zastąp znaki "1.2.3" aktualną wersję kodu i wpisz następujące komendy:
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
Poprzednia instalacja znajdzie się w folderze 'RotorHazard.old', który może zostać usunięty lub przeniesiony.

„Zależności” RotorHazard również powinny być uaktualnione – bądź cierpliwy – może to zająć kilka minut:
```
cd ~/RotorHazard/src/server
sudo pip install --upgrade --no-cache-dir -r requirements.txt
```
<br/>

-----------------------------

<a id="otheros"></a>
### Pozostałe Systemy Operacyjne

Serwer RotorHazard może być uruchomiony na każdym komputerze obsługującym python. W tych alternatywnych konfiguracjach, jedna albo więcej odnóg może być podłączona przez USB – zobacz [doc/USB Nodes.md](USB%20Nodes.md) aby uzyskać więcej informacji. Serwer może również być włączony używając “wirtualnych” (sztucznych) odnóg.

Aby zainstalować serwer RotorHazard na tych systemach:

1. Jeśli komputer nie posiada zainstalowanego Python’a w wersji 2.7 zainstaluj go z https://www.python.org/downloads. Żeby sprawdzić czy Python jest zainstalowany, otwórz wiersz poleceń i wpisz ```python --version```

2. Z RotorHazard [Releases page on github](https://github.com/RotorHazard/RotorHazard/releases), ściągnij plik "Source code (zip)".

3. Rozpakuj ściągnięty plik w folderze, na komputerze.

4. Otwórz wiersz poleceń i nawiguj do pliku ```src/server``` w plikach RotorHazard (używając komend 'cd’).

5. Zainstaluj “zależności” serwera RotorHazard używając pliku 'requirements.txt'. Na systemie Windows komenda jakiej prawdopodobnie będziesz musiał użyć to: ```python -m pip install -r requirements.txt```<br/>
Zwróć uwagę, że ta komenda może wymagać uprawnień administratora i jej wykonanie może zająć kilka minut.

Aby uruchomić serwer RotorHazard na tych systemach:

1. Otwórz wiersz poleceń i nawiguj do pliku ```src/server``` w plikach RotorHazard (chyba, że już się tam znajdujesz).

2. Wpisz: ```python server.py```

3. Jeśli serwer uruchomił się prawidłowo, powinieneś zobaczyć wiersz log’ów, np:
    ```
    Running http server at port 5000
    ```

4. Serwer może być zatrzymany poprzez naciśnięcie Ctrl+C

Jeśli odnogi są podłączone poprzez USB, muszą zostać skonfigurowane w sekcji "SERIAL_PORTS" w pliku konfiguracyjnym "src/server/config.json" (zobacz [doc/USB Nodes.md](USB%20Nodes.md) aby uzyskać szczegółowe informacje).

Jeśli żadna odnoga sprzętowa nie jest skonfigurowana, serwer będzie operował używając symulowanych – sztucznych – odnóg. w tym trybie interfejs web może byś testowany i eksplorowany.

Aby obejrzeć interfejs web, otwórz przeglądarkę internetową i wpisz w pole adresu: ```localhost:5000``` (jeśli HTTP_PORT w konfiguracji został zmieniony, wpisz wybraną wartość zamiast 5000). Jeśli serwer uruchomiony, wtedy strona główna RotorHazard powinna się pojawić. Zwróć uwagę że strony przynależne do zarządzającego zawodami (Admin/Settings) są chronione hasłem z nazwą użytkownika i hasłem ustalonymi w pliku konfiguracyjnym.
<br/>

-----------------------------

Zobacz również:<br/>
[doc/Hardware Setup.md](Hardware%20Setup.md)<br/>
[doc/USB Nodes.md](USB%20Nodes.md)<br/>
[doc/User Guide.md](User%20Guide.md)



