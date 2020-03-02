# Uwagi techniczne

RotorHazard Race timer jest otwartym projektem open-source opartym o wiele odnóg (nodes), używającym sygnału video z pojazdów i urządzeń FPV, żeby zdeterminować kiedy przekraczają linię start/meta. Sercem systemu jest Raspberry Pi, każda odnoga posiada Arduino Nano i moduł odbiorczy RX5808.

Raspberry Pi używa systemu Raspbian OS (w wersji desktop), a system RotorHazard używa komponentu serwerowego napisanego w języku Python. Wersja wolno-stojaca używa biblioteki '[Flask](http://flask.pocoo.org)' żeby stworzyć stronę internetową dla komputera PC lub urządzania mobilnego poprzez połączenie sieciowe. Baza danych SQL jest używana, żeby przechowywać ustawienia (przez rozszerzenie  '[flask_sqlalchemy](http://flask-sqlalchemy.pocoo.org)') i bibliotekę '[gevent](http://www.gevent.org)' aby móc obsługiwać asynchorniczne zdarzenia i wątki. Strona internetowa, która jest tworzona używa biblioteki Javascript '[Articulate.js](http://articulate.purefreedom.com)' żeby generować komunikaty głosowe.

Projekt RotorHazard jest hostowany na GitHub, tutaj:
https://github.com/RotorHazard/RotorHazard.
