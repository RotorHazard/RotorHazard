# RotorHazard Race Timer - Instrukcja Użytkownika

## Wstępna Konfiguracja

###  Ustawienia Sprzętu i Oprogramowania
Follow the instructions here if not done already:
[doc/Hardware Setup.md](Hardware%20Setup.md)
[doc/Software Setup.md](Software%20Setup.md)

###  Ustaw Plik Konfiguracyjny
W folderze "src/server" znajdź plik *config-dist.json* skopiuj go jako *config.json*.  Edytuj plik modyfikując wartości: HTTP_PORT,  ADMIN_USERNAME, and ADMIN_PASSWORD. Python szczególnie zwraca uwagę, żeby ten plik był ważnym plikiem JSON. Narzędzie linter i podobne [JSONLint](https://jsonlint.com/) może być użyte żeby sprawdzić poprawność składni.

HTTP_PORT jest portem, na którym serwer będzie włączony. Domyślnie, HTTP używa portu 80. Inne wartości wymagają, żeby port zawierał się jako część adresu wpisanego w przeglądarkę klienta. Jeśli inne usługi sieciowe chodzą już na Pi, port 80 może być już w użyciu i serwer nie będzie mógł wystartować. Jeśli port 80 jest używany, serwer może wymagać użycia komendy *sudo*. Port 5000 powinien być dostępny. Niektóre wersje LiveTime będą mogły się połączyć z serwerem tylko na porcie 5000.

ADMIN_USERNAME i ADMIN_PASSWORD są danymi do logowania, potrzebnymi aby zmieniać ustawienia.


### Połączenie z Serwerem
Komputer, telefon albo tablet może być użyty do interakcji z timerem, przez włączenie strony internetowej i wpisanie adresu IP należącego do Raspberry Pi. Raspberry Pi może być podłączone używając kabla Ethernet albo do dostępnej sieci WiFi. Jeżeli adres IP Raspberry jest nieznany może być sprawdzony poprzez wpisanie w wierszu poleceń komendy "ifconfig". Może być też skonfigurowany jako statyczny adres IP w preferencjach sieciowych, w wersji desktop systemu. Jeśli jest połączony z siecią WiFi, jego adres IP może być sprawdzony na liście "klientów", ma stronie konfiguracyjnej routera. 


W przeglądarce sieciowej, wpisz adres IP timera i port ustawiony w pliku konfiguracyjnym albo zostaw port nie-wpisany jeśli jest ustawiony na 80.

```
XXX.XXX.XXX.XXX:5000
```

Kiedy strona zostanie wyświetlana, może być dodana do zakładek w przeglądarce. Strony zarezerwowane dla zarządzającego zawodami ("Admin/Settings") - ustawienia - są zabezpieczone hasłem. Nazwa użytkownika i hasłem ustawione są w pliku konfiguracyjnym.

## Strony

### Domowa

Ta strona wyświetla nazwę wydarzenia i opis oraz zestaw przycisków przełączających do innych stron.

### Wydarzenie

To strona ogólnodostępna wyświetlająca aktualne ustawienia klasy - jeśli dostępne - i podsumowanie pilotów oraz ich biegu i ustawień kanału.

### Wyniki

To strona ogólnodostępna wyświetlająca wyniki i obliczone statystyki wszystkich zapisanych wyścigów, zorganizowane jako zwijający się panel. Zgromadzone rezultaty, są wyświetlane dla każdego biegu z wieloma rundami dla każdej klasy i dla całego wydarzenia.

### Aktualny

Ta strona wyświetla informacje o aktualnie trwającym wyścigu, zawiera czas wyścigu podany na żywo, czasy poszczególnych Pilotów i ich wyniki. Automatycznie uaktualnia się wraz z wydarzeniem jest przystosowana do wyświetlania na ogólno-dostepnym, dużym ekranie.

W sekcja Kontroli Audio, użytkownik może wybrać czy chce słuchać komunikatów dotyczących wszystkich, żadnego czy poszczególnych pilotów oraz ich okrążeń i czasów. W ten sposób pilot może przystosować się i słuchać tylko swoich czasów i okrążeń. Użytkownik może również ustawić głos, głośność, język oraz mowę komunikatów głosowych.

### Ustawienia

Ta strona pozwala na zmianę opcjonalnych ustawienie timera i wydarzenia.

#### Ustawienia Częstotliwości

Wybierz przygotowane ustawienie albo osobiście wybierz częstotliwości dla każdej od odnogi. Odgórne przypisanie częstotliwości jest możliwe, tak samo jak wyłączenie poszczególnych odnóg. Wynik IMD dla aktualnie wybranych częstotliwości jest obliczany i pokazany na dole panelu.

Profile zawierają częstotliwości i strojenia dla odnóg. Zmiana od razu aktywuje wybrany profil, zmienia aktualnie wybrane częstotliwości, a strojenie odnogi od razu zapisuje się do profilu.

#### Strojenie Czujników

Zobacz [doc/Tuning Parameters.md](Tuning%20Parameters.md) dla szczegółowych informacji, opisu i przewodnika po strojeniu.

#### Wydarzenia i Klasy

Informacje o wydarzeniu są wyświetlane na stronie głównej, kiedy użytkownik po raz pierwszy podłącza się do systemu.

Klasy nie są  wymagane, nie ma potrzeby tworzenia klas, chyba że masz dwie lub więcej klas w danym wydarzeniu. Klasy mogą być użyte, żeby generować oddzielne statystyki dla grupy kilku biegów. Na przykład klasa Open i Spec albo Początkujący i Pro-piloci.

#### Biegi

Dodaj biegi, aż będzie ich wystarczająco dużo, żeby wszyscy piloci mogli się ścigać. Opcjonalnie możesz nazwać bieg - jeśli chcesz. Wolne miejsca w biegach mogą być ustawione jako "None" jeśli żaden pilot nie jest przypisany.

Jeśli używasz Klas, przypisz każdy bieg do klasy. Upewnij się dodałeś odpowiednią ilość biegów dla każdego pilota, w każdej klasie. Biegi przypisane do jednej klasy, nie są dostępne w innej.

Kiedy przeprowadzasz wyścigi, biegi będą zablokowane i nie będą mogły być zmienione. To chroni zapisane wyścigi przed tym, żeby nie stały się nie ważne. Żeby zmienić biegi, otwórz panel "Baza Danych" i skasuj wyścigi.

#### Piloci

Dodaj wpis dla każdego pilota który będzie się ścigał. System będzie ogłaszał pilotów bazując na ich zapisanych znakach wywoławczych. Fonetyczna wymowa dla każdego znaku może być użyta, żeby dostosować komunikaty głosowe, nie jest to jednak wymagane.

#### Kontrola Audio 

Wszelka kontrola audio jest przypisana lokalnie do przeglądarki i urządzenia gdzie ją ustawiasz, włączając w to listę dostępnych języków, głośność, i to jakie komunikaty i wskaźniki mają być w życiu.

Wybór języka zmienia silnik zamiany tekstu-na-mowę. Dostępne wybory są dostarczone przez przeglądarkę i system operacyjny.

Komunikaty głosowe pozwalają użytkownikowi na wybór żeby słyszeć znak wywoławczy każdego pilota, numer oraz czas okrążenia. Komunikaty głosowe timera będą okresowo informować ile czasu zostało, w zależności od ustawień timera w formacie wyścigu. Łączny Czas Drużyny jest użyty wyłącznie kiedy włączony jest Tryb Drużynowy.

Możesz ustawić głośność oraz wysokość głosu komunikatów. Głośność dźwięków kontroluje sygnały startu i końca oraz przekroczenia linii.

Wskaźnik piszczy bardzo krótkimi dźwiękami, które dają informację zwrotną jak timer działa i są najbardziej przydatne podczas ustawiania go. Każda odnoga jest identyfikowana oddzielnym dźwiękiem. Wlot w linię będzie piszczał raz kiedy przelot się zaczyna a Wylot będzie piszczał szybko 2 razy kiedy przelot przez bramkę pomiarową jest zakończony. "Ręczny przycisk okrążenia" będzie piszczał raz, jeśli przycisk zostanie użyty żeby wymusić symulowany przelot.

#### Format Wyścigu

Format wyścigu zbiera ustawienia, które definiują jak wyścig jest przeprowadzony. Wybierz aktywny format wyścigu. Ustawienia które wybierzesz będą zapisane do obecnie aktywowanego formatu.

Timer może odliczać czas w dół albo w górę. Użyj odliczania w górę dla heads-up, pierwszy do danej ilości okrążeń. Użyj odliczenia w dół dla formatów o ustalonym z góry czasie. Długość odliczania jest użyta tylko podczas odliczania w dół.

Ustawienia odliczania wpływają na to czy czas będzie widoczny przed wyścigiem. "Pokaż odliczanie" pokaże czas do sygnału startu wyścigu. "Ukryj odliczanie" wyświetli tylko "Gotowi" zanim wyścig się rozpocznie.

Minimalne i Maksymalne Opóźnienie Startu ustawia ile sekund może trwać odliczanie przed wyścigiem. Ustaw taką samą liczbę dla ustalonego z góry czasu odliczania albo przedział dla losowego czasu w tym zakresie.

Minimalny Czas Okrążenia i tryb wyścigu drużynowego nie są zapisane w formacie wyścigu.

Minimalny Czas Okrążenia automatycznie odrzuca przyloty, które normalnie byłyby zarejestrowane, ale mają czas krótszy niż zapisana wartość. Używaj tego ustawienia z rozwagą, ponieważ odrzuci dane które mogłyby być ważne.

#### Efekty LED-owe

Wybierz efekty wizualne dla każdego zdarzenia. Timer wyświetli ten efekt kiedy dojdzie do danego zdarzenia, od razu nad nadpisując każde trwające zdarzenie albo efekt. Niektóre efekty wizualne są dostępne tylko dla niektórych zdarzeń. Niektóre efekty mogą być zmodyfikowany przez wydarzenie, głównie może być to zauważone zmianą koloru podczas wlotu i wylotu z bramki. Większość efektów może być sprawdzona przedtem w Panelu Kontrolnym LED.

Niektóre efekty LED-owe mogą być opóźnione o krótki czas jeśli timer jest zajęty przez jakieś krytyczne zadania. Zdarzenia takie jak start wyścigu nigdy nie są opóźnione. W związku z tym oraz potencjalnym przekroczeniem linii przez kilka osób na raz opcja "Wyłącz" powinna być unikalna dla opuszczenia bramki - zamiast tego użyj opcji "Brak zmiany" podczas Wlotu do bramki i zamierzony przez Ciebie efekt podczas Wylotu.

Ta sekcja nie pojawi się w ustawieniach jeżeli timer nie ma ustawionych LED-ów. Informacja na ten temat pojawia się podczas uruchomienia się serwera - w terminalu.

#### Kontrola LED

Ta sekcja nadpisuje to co aktualnie wyświetlają LEDy. Wybierz ją dla tymczasowego wyłączenia wyświetlania albo dla skonfigurowanych kolorów, wyświetlenia zapisanego efektu albo danego koloru. Możesz też użyć suwaka, żeby ustawić jasność twojego panelu LED. Idealne ustawienie dla kamer FPV jest wtedy, kiedy świecący się panel ma taką samą jasność jak biały obiekt. Sprawia to, że panel znajduje się w zakresie dynamicznym tego co kamera może uchwycić. Jednakże, użycie niskiej jasności może zniekształcić reprodukcję kolorów i płynność zmiany kolorów.

Ta sekcja nie pojawi się w ustawieniach jeżeli timer nie ma ustawionych LED-ów. Informacja na ten temat pojawia się podczas uruchomienia się serwera - w terminalu.

#### Baza Danych 

Wybierz kopię zapasową aktualnej bazy danych - zapisz do pliku i ściągnij albo Wyczyść dane. Możesz też wyczyścić wyścigi, klasy, biegi i pilotów.

#### System 

Wybierz język interfejsu i zmień parametry które wpływają na wygląd interfejsu timera takie jak nazwa albo schemat kolorów. Możesz też zamknąć serwer z poziomu tego panelu.

### Bieg

Ta strona pozwala ci na kontrolowanie timera i włączanie wyścigu. 

Wybierz bieg, który ma być włączony jako kolejny.

Rozpocznij wyścig kiedy będziesz gotowy. (Skrót klawiszowy: <kbd>z</kbd>) Timer wykona szybkie połączenie z serwerem, żeby skompensować czas odpowiedzi między klientem, a serwerem. Następnie rozpocznie się procedura zdefiniowana przez obecny format wyścigu.

Ustawienia strojenia mogą być zmienione tutaj poprzez przycisk "⚠". Zobacz [doc/Tuning Parameters.md](Tuning%20Parameters.md) dla szczegółowego opisu i przewodnika po strojeniu.

Podczas wyścigu dla obok każdego policzonego okrążenia dostępny jest przycisk "×". Powoduje on, że dane okrążenia nie zostaną uznane, a ich czas będzie przesunięty do kolejnego okrążenia. Użyj tego żeby usunąć błędne dodatkowe przyloty, albo usunąć pilotów latających blisko bramki startowej, po tym jak ich wyścig się już zakończył.

Przycisk "+ Lap" jest dostarczony aby wymusić przelot dla danej odnogi - zostanie od razu zapisany.

Kiedy wyścig jest zakończony, użyj przycisku Koniec Wyścigu(Skrót: <kbd>x</kbd>), aby zakończyć naliczanie okrążeń. Musisz to zrobić nawet kiedy timer dojdzie już do zera. W popularnym formacie odliczania w dół, piloci będą mogli kończyć okrążenie, nawet kiedy ich czas się skończy. Dla najlepszych rezultatów oczyść bramkę startową i pozwól na wszystkie ważne przeloty przez linię przed zatrzymaniem wyścigu.

Kiedy wyścig zostanie podsumowany musisz wybrać Zapisanie Okrążeń albo Oczyszczanie Okrążeń, zanim zaczniesz kolejny wyścig. Zapisanie Okrążeń (Skrót: <kbd>c</kbd>) zapisze wyniki wyścigu do bazy danych i pokaże je na karcie Rezultaty. Oczyszczanie Okrążeń (Skrót: <kbd>v</kbd>) nie weźmie pod uwagę wyników wyścigu. Zapisanie okrążeń automatycznie przesunie bieg do kolejnego w tej samej klasie co zapisany wyścig.

Panel Zarządzanie Wyścigiem dostarcza szybkiego dostępu, żeby zmienić aktualny format wyścigu, profil, minimalny czas okrążeń albo tryb drużynowy. Kontrola audio, kontrola LED są w tym samym miejscu co karta Ustawienia. Eksport Historii robi zrzut pliku CSV, który może być ściągnięty. Są nim zapisane wartości RSSI z ostatniego wyścigu. Czas do rozpoczęcia wyścigu ustali w harmonogramie wyścig jaki ma się odbyć w przyszłości. Operator może tego użyć, by ustawić twardy limit ilości czasu jaki piloci mają na przygotowanie się albo na włączenie timera i uczestniczenie samemu w wyścigu.

### Zarządzanie

Zarządzaj rezultatami z zapisanych wyścigów.

Wybierz rundę, bieg i pilota, które chcesz ustawić. Punkty wlotu i wylotu są automatycznie pobrane z zapisanych danych wyścigu. Dostosuj punkt wlotu i wylotu, żeby ponownie skalibrować wyścig, po tym jak już się odbył. "Odczytaj z odnogi", żeby skopiować aktualne dane kalibracji do aktualnych wartości. "Zapisz do odnogi", żeby skopiować aktualne wartości do aktualnie używanych wartości. "Policz ponownie wyścig", żeby użyć aktywnego punktu wlotu i wylotu jako punktów kalibracji dla kalkulowanego ponownie wyścigu. Wymaże to obecne okrążenia i zastąpi je informacjami obliczonymi ponownie. Manualne wpisywanie okrążeń jest zachowane.

Dodaj okrążenia wpisując czas przekroczenia w sekundach od początku wyścigu, a następnie naciśnij przycisk Dodaj Okrążenie ("Add Lap").

Usuń okrążenia przyciskiem "×" na niechcianym okrążeniu. Niechciane okrążenia są usuwane z kalkulacji, ale pozostają obecne w danych, dla późniejszego odniesienia. "Oczyść okrążenia", żeby permanentnie usunąć te dane z bazy danych.

Możesz kliknąć albo nacisnąć na wykresie, żeby ustalić punkty wlotu i wylotu, aktywować rekalkulację albo podświetlić dane okrążenie. Kliknij na okrążenie na liście żeby podświetlić je na wykresie. Naciśnij <kbd>delete</kbd> albo <kbd>x</kbd> żeby usunąć podświetlone obciążenie. Aktywne okrążenia są wyświetlane na zielono, a usunięte zmieniają się na czerwone. Szerokość wskazanego okrążenia pokazuje punkt wlotu i wylotu, żółte podświetlenie rysuje linie dokładnego czasu okrążenia w tym oknie.

"Wprowadź zmiany" po tym jak skończysz ustawianie danych wyścigu, żeby zapisać je do bazy danych i uaktualnić wyniki wyścigów.
