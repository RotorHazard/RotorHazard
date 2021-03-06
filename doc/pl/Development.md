# Rozwój

Ten dokument jest przede wszystkim przeznaczony dla developerów.

Jeśli chcesz mieć wkład w RotorHazard otwierając "pull request" dla poprawy błędów albo dla nowych funkcji, przeczytaj proszę następujący tekst zanim zaczniesz. To pomoże Ci wnieść wkład w sposób, który znacząco zwiększy szansę na jego akceptację.

## Używanie git i GitHub

Upewnij się, że rozumiesz jak działa GitHub: https://guides.github.com/introduction/flow/index.html

Utrzymuj "pull request" skoncentrowany tylko na jednej rzeczy, ponieważ to sprawia, że jest łatwiejszy do wdrożenia i przetestowania w krótkim czasie.

Jeśli potrzebujesz pomocy w "pull request" na GitHub są instrukcje:

https://help.github.com/articles/creating-a-pull-request

Przebieg dla wnoszenia wkładu jest taki:

1. Zaloguj się na GirHub, przejdź do [repozytorium GitHub](https://github.com/RotorHazard/RotorHazard) i naciśnij "fork”
2. Następnie, używając wiersza poleceń/terminala na komputerze: `git clone <url do TWOJEGO „forka”>`
3. `cd RotorHazard`
4. `git checkout main`
5. `git checkout -b my-new-code`
6. Wprowadź zmiany
7. `git add <pliki-które zmieniłeś>`
8. `git commit`
9. `git push origin my-new-code`
10. Stwórz pull request używając GitHub UI żeby połączyć Twoje zmiany z Twojego nowego brancha do `RotorHazard/main`
11. Powtórz od punktu 4 dla nowych i innych zmian
