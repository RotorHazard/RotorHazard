# Kalibracja i Parametry Strojenia Czujników

Każda odnoga monitoruje siłę sygnału (RSSI) wybranych częstotliwości i używa tych względnych wartości, żeby zdeterminować kiedy nadajnik jest w pobliżu bramki. System pomiaru czasu RotorHazard pozwala na kalibrację każdej odnogi indywidualnie, przez co różnice w sprzecie mogą zostać skompensowane dla danego systemu i otoczenia.

Odnoga może być w stanie *Przelotu* (Crossing) lub *Czysto* (Clear). Jeśli odnoga jest w stanie *Czysto*, system zakłada, że nadajnik nie jest w pobliżu bramki, ponieważ wartość RSSI jest niska. Jeśli jest w stanie
*Przelotu*, system zakłada, że nadajnik przekracza bramkę, ponieważ wartość RSSI jest wysoka. Przelot przez okrążanie będzie zapisany, kiedy zakończy się *Przelot*, a system wróci do stanu *Czysto*.

![Wykres strojenia](img/Tuning%20Graph-06.svg)<br />
_RSSI podczas wyścigu wygląda podobnie do tego, z dużą ilością zmian i  pików. Kiedy nadajnik jest w pobliżu timera, wartość odczytu wzrasta._

## Parametry
Dwa parametry, które wpływają na stan *Przelotu*: *Wlot* i  *Wylot*.

### Wlot
System przełączy się w stan *Przelotu*, gdy wartość RSSI przekroczy tę wartość. Pokazuje to czerwona linia.

### Wylot
System przełączy się w stan *Czysto*, gdy wartość RSSI spadnie poniżej tej wartości. Pokazuje to pomarańczowa linia.

Pomiędzy *Wlotem* a *Wylotem*, system pozostanie w stanie *Przelot* lub *Czysto* w zależności od poprzedniego stanu.

![Przykładowy wykres RSSI](img/Sample%20RSSI%20Graph.svg)

### Tryb kalibracji

*Manualny* tryb kalibracji będzie zawsze używał wartości * Wlot* i * Wylot* podanych przez użytkownika.

*Adaptacyjny* tryb kalibracji będzie używał wartości * Wlot* i * Wylot* podanych przez użytkownika dopóki nie pojawią się zapisane wyścigi. Kiedy pojawią się napisane wyścigi, zmiana biegów spowoduje rozpoczęcie poszukiwania danych z poprzedniego wyścigu dla najlepszych wartości kalibracji, żeby użyć ich w kolejnym biegu. Wartości te są skopiowane i zamienione przez obecne *Wlot* i *Wylot* dla wszystkich odnóg. Tryb ten poprawia kalibrację wraz z każdym zapisanym wyścigiem, gdy zarządzający wyścigiem potwierdzi pojawiające się okrążenie - liczy się ono albo jest przeliczane ponownie używając strony *Zarządzanie*.

## Strojenie
Przed strojeniem, włącz timer i zostaw go włączonego na kilka minut, aby pozwolić odbiornikom się nagrzać. Wartości RSSI mają tendencję do zwiększania się o kilka punktów po tym jak timer się nagrzeje

Możesz użyć zakładki *Zarządzanie*, żeby stroić wartości wizualnie.  Zbierz dane przeprowadzając wyścig z pilotem na każdym kanale, później je zapisz. Otwórz stronę *Zarządzanie* i zobacz dane wyścigów. Ustaw wartości Wlot i Wylot, do momentu kiedy liczba okrążeń będzie poprawa. Zapisz wartości wlot i wylot na każdej od nogi żeby użyć ich jako kalibrację dla kolejnych wyścigów.

### Ustawianie wartości *Wlot*
![Wykres Strojenia](img/Tuning%20Graph-10.svg)

* Poniżej piku podczas wszystkich przelotów przez bramkę
* Powyżej każdego piku kiedy nadajnik nie jest w pobliżu bramki
* Wyżej niż wartość *Wylot*

### Ustawianie wartości *Wylot*
![Wykres Strojenia](img/Tuning%20Graph-11.svg)

* Poniżej każdego spłaszczenia jakie pojawiają się podczas przygotowywania przez bramkę
* Powyżej najniższej wartości widzianej atrakcje okrążenia
* Poniżej wartości *Wlot*

Wartość *Wylot* bliższa wartości *Wlot* pozwala timerowi na ogłoszenie i wyświetlenie okrążeń wcześniej, ale może powodować, że zbyt wiele okrążenie dostanie zapisanych

### Przykład Strojenia
![Wykres Strojenia](img/Tuning%20Graph-01.svg)<br />
_Dwa okrążenia są zapisane. Sygnał rośnie powyżej wartości *Wlot*, a później opada poniżej wartości *Wylot* 2 razy, raz przy każdym piku. Podczas tych dwóch przelotów timer szuka najsilniejszego sygnału po odfiltrowywaniu szumu, żeby użyć go jako zapisanego czasu okrążenia

### Alternatywne Metody Strojenia

Przycisk *Przechwyć* (Capture) może być użyty żeby zapisać obecną wartość RSSI jako *Wlot* albo *Wylot* dla każdej odnogi. Wartości mogą być też wpisane ręcznie.

Włącz quad na poprawnym kanale i spraw, żeby zbliżył się bardzo blisko timera na kilka sekund. To pozwoli timerowi przechwycić wartości RSSI dla tej odnogi. Proces ten powinien być przeprowadzony dla każdej odnogi/kanału, który jest strojony. Wartość piku będzie wyświetlona.

#### Wlot
Dobrym punktem startowym dla *Wlot* jest przechwycenie wartości z quadem około 1.5 do 3m od timera.

#### Wylot
Dobrym punktem startowym dla *Wylot* jest przechwycenie wartości z quadem około 6 do 9m od timera.

## Uwagi
* Niska wartość *Wylot* może nadal powodować, że pomiary będą poprawne, ale system będzie dłużej czekał na ogłoszenie okrążeń. Opóźnienie w podaniu okrążenia nie wpływa na dokładność pomiaru.
* Ustawienie Minimalnego Czasu Okrążenia może być użyte, żeby zapobiec dodatkowym przekroczeniom bramki, ale może zamaskować przelot, który pojawia się zbyt szybko. Zaleca się pozostawienie zachowania jako *Podświetl*, a nie *Odrzuć*.
* Jeśli doświadczasz jakichś kwestii związanych z opóźnieniami podczas wyścigu, a wartość RSSI na wykresie odpowiada na odległość nadajnika, nie przerywaj wyścigu. Zachowaj wyścig po tym jak jest ukończony i odwiedź stronę *Zarządzanie*. Wszystkie dane historyczne RSSI są zapisane i wyścig może być dokładnie przekalkulowany z nowymi danymi strojenia.

## Rozwiązywanie Problemów

### Brakujące okrążenie (System przeważnie w stanie *Czysto*)
![Wykres Strojenia](](img/Tuning%20Graph-04.svg)<br />
_Okrążenia nie są zapisane jeśli wartość RSSI nie przekroczy wartości *Wlot*._
* Obniż *Wlot*

### Brakujące okrążenia (przeważnie w stanie *Przekraczanie*)
![Wykres Strojenia]img/Tuning%20Graph-05.svg)<br />
_Okrążenia są łączone w jedno jeśli *Wylot* jest za wysoko, ponieważ pierwsze okrążenie nigdy się nie skończyło._
* Podwyższ *Wylot*

### Obrażenia są zarejestrowane w innych częściach torów
![Wykres Strojenia](img/Tuning%20Graph-03.svg)<br />
_Dodatkowe przekroczenia pojawiają się kiedy wartość *Wlot* jest ustawiona za nisko._
* Podnieść wartość *Wlot* do momentu kiedy *Przelot* będzie zaczynać się tylko w pobliżu bramki. Użyj strony *Zarządzanie* po zapisaniu w wyścigu, żeby stwierdzić jaka powinna być to wartość i zapisz najbardziej pasujące wartości.

### Wiele okrążeń zarejestrowanych na raz
![Wykres Strojenia](img/Tuning%20Graph-02.svg)<br />
_Zbyt wiele okrążeń pojawia się kiedy wartość *Wylot* jest za blisko wartości *Wlot*, ponieważ okrążenie kończy się zbyt szybko._
* Podnieś wartość *Wlot*, jeśli to możliwe
* Obniż wartośc *Wylot*

### Ustawienie Minimalny Czas Okrążenia zawsze utrzymuje pierwsze przekroczenie i odrzuca kolejne które pojawiają się zbyt szybko.
*W takim wypadku ustawienie to odrzuciłoby pierwsze poprawne przekroczenie i utrzymało kolejne niepoprawne. Zaleca się pozostawienie opcji ustawionej na *Podświetlenie*, a nie na *Odrzucenie*, żeby organizator wyścigu mógł ręcznie sprawdzić każdy przypadek.

### Okrążeniom zajmuje dużo czasu, żeby się zarejestrowały
![Wykres Strojenia](img/Tuning%20Graph-09.svg)<br />
_Zapisanie okrążeń trwa zbyt długo kiedy wartość *Wylot* jest za niska. Nie wpływa to na poprawność czasu zapisanych okrążeń._
* Podnieś *Wylot*

### Odnoga nigdy nie jest w stanie *Przelot*
![Wykres Strojenia](img/Tuning%20Graph-07.svg)<br />
_Okrążenie nigdy nie zostanie zarejestrowane jeśli wartość RSSI nigdy nie przekroczy wartości *Wlot*._
* Obniż *Wlot*

### Odnoga nigdy nie jest w stanie *Czysto*
![Wykres Strojenia](img/Tuning%20Graph-08.svg)<br />
_Okrążenie nigdy się nie skończy jeśli wartość RSSI nigdy nie spadnie poniżej wartości *Wylot*._
* Podnieś *Wylot*
