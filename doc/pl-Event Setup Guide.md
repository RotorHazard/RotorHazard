# Poradnik Organizacji Eventu

Podstawy konfuguracji eventu to ustawienie pilotów, biegów i odnóg (odbiorników). Możesz też dodać szczegóły do wydarzenia i klasy zawodów -- jeśli chcesz.

## Wyczyść Obecne Dane (jeśli potrzeba)
W Ustawieniach, otwórz Bazę Danych. Użyj opcji do usunięcia starych informacji z bazy danych.

## Ustaw Szczegóły Wydarzenia (opcjonalne)
W Ustawieniach otwórz panel Wydarzenia. Uaktualnij nazwę Wydarzenia i Opis. Pokażą się one na pierwszej stronie, gdy użytkownik po raz pierwszy odwiedzi stronę timera. Daj znać pilotom czego się spodziewać podczas wydarzenia, np. format wydarzenia i harmonogram.

## Dodaj Pilotów
Dodaj wpis dla każdego uczestniczącego pilota. Nazwisko pilota pojawi się na stronie wydarzenia. Znak Wywoławczy będzie używany na potrzeby wyników wyścigów i komunikatów głosowych. Możesz przetestować wymowę znakiem ">". Jeśli chcesz, wpisz wymowę (fonetycznie). Nie będzie nigdy wyświetlona, ale będzie używana podczas komunikatów głosowych jako Znak Wywoławczy.

## Stwórz Format Wyścigu (opcjonalne)
W Ustawieniach otwórz Formaty Wyścigów. [Dostosuj ustawienia](User%20Guide.md#race-format) albo stwórz nowe formaty, żeby pasowały do zamierzonego sposobu wystartowania, warunków wygranej itd.

## Dodaj biegi i Klasy
**Biegi** to piloci latający w tym samym czasie. Nazwij swój bieg, albo pozostaw to pole puste, żeby używać domyślnej nazwy. Wybierz którzy piloci będą lecieć razem i przypisz ich do odpowiedniego miejsca ("slotu"). Numer dostępnych "slotów" jest dostępny i zdeterminowany przez liczbę odnóg (odbiorników) podłączonych do timera. Użyj "None" dla nieużywanych slotów.

**Klasy** to grupy pilotów, którzy współdzielą charakterystykę. Stwórz klasy bazując na tym, jak Twój event jest zaprojektowany, jeśli potrzebujesz więcej niż jednej klasy. Nazwij swoją klasę dla odniesienia w innych miejscach. Opis klasy jest widoczny na stronie Wydarzenia. Ustawianie opcjonalnego formatu powoduje, że wszystkie wyścigi w danej klasie używają wybranego Formatu Wyścigów.

Przypisz biegi do klas, aby móc ich używać. Kiedy wyścig jest zapisany jako bieg do przypisanej klasy, rezultaty będą kalkulowane osobno i pojawią się oddzielnie jako oddzielna sekcja w wynikach wyścigów.

## Strojenie odbiorników w zależności od okoliczności i środowiska
Kiedy timer jest uruchomiony w miejscu wyścigu, ustaw [parametry odbiorników i filtrowania](Tuning%20Parameters.md), żeby najlepiej pasowały do wybranego typu wyścigów. Opcjonalnie, stwórz profil dla danej lokacji, żeby później móc go łatwo wczytać.

## Przykład

8 Pilotów zbiera się w pomieszczeniu, żeby ścigać się micro-quadami. Format wyścigu to pięć rund kwalifikacyjnych, rozstrzyganych poprzez dodanie całkowitej ilości okrążeń czterech najlepszych pilotów do pojedynczego wyścigu finałowego. Przed wydarzeniem, organizator dodaje wszystkich pilotów w panelu Piloci. Dwie klasy są stworzone, "Kwalifikacje" i "Finał" i obie klasy są wpisane w format "Whoop Sprint". Dwa biegi są stworzone, po czterech pilotów w każdym i oba biegi są przypisane do klasy "Kwalifikacje".

W dzień wydarzenie, organizator wybiera profil "Wewnątrz", żeby ustawić żądane częstotliwości i filtrowanie i upewnić się, że odbiorniki są zestrojone poprawnie. Ze strony Wyścig, każdy bieg jest przeprowadzony pięć razy. Timer organizuje te wyścigi w rundy 1 do 5 na stronie wyników kiedy wyścigi są przeprowadzane.

Po biegach kwalifikacyjnych, organizator sprawdza stronę wyników i sprawdza którzy piloci z klasy "Kwalifikacje" są najlepsi. Organizator otwiera Ustawienia i panel Biegi, tworzy nowy bieg i przypisuje do niego czterech najlepszych pilotów. Następnie przypisuje klasę "Finał" do tego biegu. Wyścig dla tego biegu jest przeprowadzony. Na stronie wyników, klasa "Finał" posiada rezultaty finału i pokazywana jest oddzielnie od pozostałych.
