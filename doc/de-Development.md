# Entwicklung

Dieses Dokument richtet sich in erster Linie an Entwickler.

Wenn Sie planen, zu RotorHazard beizutragen, indem Sie einen [pull request](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-requests) für einen Bugfix oder eine Funktion öffnen, lesen Sie bitte den folgenden Text, bevor Sie beginnen. Dies wird Ihnen helfen, Ihren Beitrag in einer Form einzureichen, die eine gute Chance hat, angenommen zu werden.

## Verwendung von git und GitHub

Stellen Sie sicher, dass Sie den GitHub-Workflow verstehen: [https://guides.github.com/introduction/flow/index.html](https://guides.github.com/introduction/flow/index.html)

Konzentrieren Sie Pull-Anfragen nur auf eine Sache, da dies die zeitnahe Zusammenführung und Prüfung erleichtert.

Wenn Sie Hilfe bei Pull-Anfragen benötigen, finden Sie hier einen Leitfaden zu GitHub: [https://help.github.com/articles/creating-a-pull-request](https://help.github.com/articles/creating-a-pull-request)

Der Hauptfluss für einen Beitrag ist wie folgt:

1. Melden Sie sich bei GitHub an, gehen Sie zum [RotorHazard repository](https://github.com/RotorHazard/RotorHazard) und drücken Sie `Fork`.
2. Verwenden Sie dann die Befehlszeile/Terminal auf Ihrem Computer: `git clone <url zu IHREM fork>`
3. `cd RotorGefahr`
4. `git checkout master`
5. `git checkout -b mein-neuer-Code`
6. Änderungen vornehmen
7. `git add <Dateien, die sich geändert haben>`
8. `git commit`
9. `git push origin mein-neuer-Code`
10. Erstellen Sie eine Pull-Anfrage unter Verwendung der GitHub-Web-Benutzeroberfläche, um Ihre Änderungen aus Ihrem neuen Zweig in `RotorHazard/master` zusammenzuführen.
11. Wiederholen Sie ab Schritt 4 für weitere Änderungen

Vor allem ist zu bedenken, dass separate Pull-Anforderungen für getrennte Zweige erstellt werden sollten.  Erstellen Sie niemals eine "Pull"-Anfrage von Ihrem "Master"-Zweig.

Sobald Sie den PR erstellt haben, wird jeder neue Commit/Push in Ihrem Zweig von Ihrem Zweig in den PR im Haupt-Repo von GitHub/RotorHazard übertragen. Checken Sie zuerst einen anderen Zweig aus, wenn Sie etwas anderes wünschen.

Später können Sie die Änderungen aus dem RotorHazard-Repository in Ihren `Master`-Zweig bekommen, indem Sie das RotorHazard-Repository als [git remote](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/configuring-a-remote-for-a-fork) hinzufügen ("upstream") und daraus wie folgt zusammenführen:

1. `git remote add upstream https://github.com/RotorHazard/RotorHazard.git`
2. `git checkout master`
3. `git pull upstream master`
4. `git push origin master` (dies ist ein optionaler Schritt, der Ihr Repository auf GitHub aktualisieren wird)

<br>

Wenn Sie Windows verwenden, wird [TortoiseGit](https://tortoisegit.org) dringend empfohlen.

## Kodierungsstil

Wenn Code zu einer bestehenden Datei hinzugefügt wird, sollte der neue Code in Bezug auf Einrückung (Leerzeichen vs. Tabulatoren), Klammern, Namenskonventionen usw. dem bereits vorhandenen folgen.

Wenn ein PR die Funktionalität modifiziert, versuchen Sie, unnötige Whitespace-Änderungen (d.h. das Hinzufügen/Entfernen von Leerzeichen am Ende oder Zeilenumbrüchen) zu vermeiden, da es dadurch schwieriger wird, die funktionalen Änderungen zu erkennen. Verbesserungen an Leerzeichen und Codestil sollten mit PRs umgesetzt werden, die nur diese Dinge tun.

## Eclipse-PyDev-Projekt

Die [Eclipse IDE](https://www.eclipse.org/eclipseide/) (mit der Erweiterung [PyDev](https://www.pydev.org)) kann zur Bearbeitung des Python-Quellcodes verwendet werden -- die Dateien ".project" und ".pydevproject" definieren das Projekt, das über "File | Open Projects from File System..." in Eclipse geladen werden kann.
