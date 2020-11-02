# RotorHazard Race Timer Benutzerhandbuch

## Ersteinrichtung

### Hardware- und Software-Setup

Befolgen Sie die Anweisungen hier, falls dies noch nicht geschehen ist: <br>
[Hardware Setup](de-Hardware%20Setup.md)<br>
[Software Setup](de-Software%20Setup.md)<br>
[RF shielding](de-Shielding%20and%20Course%20Position.md)

### Konfigurationsdatei einrichten

Suchen Sie im Verzeichnis "src / server" nach *config-dist.json* und kopieren Sie es nach *config.json*. Bearbeiten Sie diese Datei und ändern Sie die Werte ADMIN_USERNAME und ADMIN_PASSWORD. Diese Elemente in dieser Datei müssen im gültigen JSON-Format vorliegen. Ein Linter-Dienstprogramm wie [JSONLint](https://jsonlint.com/) kann verwendet werden, um nach Syntaxfehlern zu suchen.

ADMIN_USERNAME und ADMIN_PASSWORD sind die Anmeldeinformationen, die Sie benötigen, um auf die für den Rennleiter reservierten Seiten zuzugreifen (d. H. Auf die Seiten *Einstellungen* und *Ausführen*).

### Stellen Sie eine Verbindung zum Server her

Ein Computer, ein Smartphone oder ein Tablet kann zur Interaktion mit dem Race-Timer verwendet werden, indem ein Webbrowser gestartet und die IP-Adresse des Raspberry Pi eingegeben wird. Der Raspberry Pi kann über ein Ethernet-Kabel oder ein verfügbares WiFi-Netzwerk verbunden werden. Wenn die IP-Adresse des Pi nicht bekannt ist, kann sie mit dem Terminalbefehl "ifconfig" angezeigt und über die "Netzwerkeinstellungen" auf dem Pi-Desktop auf einen statischen Wert konfiguriert werden. Wenn der Pi mit einem WiFi-Netzwerk verbunden ist, finden Sie seine IP-Adresse in der Liste "Clients" auf der Administrationsseite für den Router des Netzwerks.

Geben Sie im Webbrowser die IP-Adresse von für den Race-Timer und den Portwert ein, den Sie in der Konfigurationsdatei festgelegt haben (oder lassen Sie den Port: weg, wenn er auf 80 eingestellt ist).

```
XXX.XXX.XXX.XXX:5000
```

Sobald die Seite erfolgreich angezeigt wurde, kann sie im Browser mit einem Lesezeichen versehen werden. Für den Rennleiter reservierte Seiten ("Admin / Einstellungen") sind mit dem in der Konfigurationsdatei angegebenen Benutzernamen und Passwort passwortgeschützt.

## Seiten

### Home

Auf dieser Seite werden der Name und die Beschreibung des Ereignisses sowie eine Reihe von Schaltflächen für verschiedene andere Seiten angezeigt.

### Veranstaltung

Auf dieser öffentlichen Seite werden das aktuelle Klassen-Setup (falls zutreffend) sowie eine Zusammenfassung der Piloten und ihrer Vorläufe mit Kanalzuweisung angezeigt.

### Ergebnisse

Auf dieser öffentlichen Seite werden Ergebnisse und berechnete Statistiken aller zuvor gespeicherten Rennen angezeigt, die in zusammenklappbaren Feldern organisiert sind. Die Gesamtergebnisse werden für jeden Lauf mit mehreren Runden, jeder Klasse und dem gesamten Ereignis angezeigt.

### Aktuell

Auf dieser Seite werden Informationen zum aktuell laufenden Rennen angezeigt, einschließlich Echtzeit-Rennzeit, Rundenzeiten des Piloten und Rangliste. Es wird automatisch mit dem Ereignis aktualisiert und eignet sich für die Projektion auf einen gut sichtbaren Bildschirm.

Im Abschnitt Audiosteuerung kann der Benutzer auswählen, ob für einen Piloten, alle Piloten oder keine Piloten Runden angekündigt werden sollen. Auf diese Weise kann ein Pilot entscheiden, nur seine eigenen angekündigten Runden zu hören. Ein Benutzer kann auch die Stimme, Lautstärke, Rate und Tonhöhe dieser Ansagen anpassen.

### Einstellungen

Auf dieser Seite können Sie die optionalen Einstellungen und das Ereignis-Setup des Timers ändern.

#### Frequenzeinstellung

Wählen Sie eine Voreinstellung oder wählen Sie die Frequenzen für jeden Knoten manuell aus. Eine beliebige Frequenzauswahl ist möglich, ebenso wie das Deaktivieren eines Knotens. Der IMD-Wert für aktuell ausgewählte Frequenzen wird berechnet und am unteren Rand des Bedienfelds angezeigt.

Profile enthalten Frequenzen und Knotenoptimierungswerte. Durch Ändern dieser Liste wird das ausgewählte Profil sofort aktiviert, und durch Ändern der aktuellen Frequenzen und der Knotenoptimierung wird sofort im Profil gespeichert.

#### Sensor-Tuning

Eine ausführliche Beschreibung und Tuning-Anleitung finden Sie hier [doc/Tuning Parameters.md](de-Tuning%20Parameters.md).

#### Veranstaltung und Klassen

Ereignisinformationen werden auf der Startseite angezeigt, wenn Benutzer zum ersten Mal eine Verbindung zum System herstellen.

Für Veranstaltungen sind keine Klassen erforderlich. Es ist nicht erforderlich, eine Klasse zu erstellen, es sei denn, Sie haben zwei oder mehr in dem Ereignis. Klassen können verwendet werden, um separate Statistiken für Gruppen von Vorläufen zu generieren. Zum Beispiel Open- und Spec-Klassen oder Anfänger- / Pro-Klassen.

#### Vorläufe

Fügen Sie Läufe hinzu, bis genug für alle Piloten vorhanden sind. Falls gewünscht, können optionale Wärmenamen hinzugefügt werden. Heizschlitze können auf *Keine* gesetzt werden, wenn dort kein Pilot zugewiesen ist.

Wenn Sie Klassen verwenden, weisen Sie jede Hitze einer Klasse zu. Stellen Sie sicher, dass für jeden Piloten in jeder Klasse genügend Vorläufe vorhanden sind. Läufe, die einer Klasse zugeordnet sind, sind in einer anderen nicht verfügbar.

Während Sie Rennen laufen, werden die Vorläufe gesperrt und können nicht geändert werden. Dies schützt gespeicherte Renndaten vor Ungültigkeit. Um die Vorläufe erneut zu ändern, öffnen Sie das Bedienfeld *Datenbank* und löschen Sie die Rennen.

#### Piloten

Fügen Sie einen Eintrag für jeden Piloten hinzu, der Rennen fahren wird. Das System kündigt Piloten anhand ihres Rufzeichens an. Eine phonetische Schreibweise für ein Rufzeichen kann verwendet werden, um die Sprachanrufe zu beeinflussen. es ist nicht notwendig.

#### Audiosteuerung

Alle Audiosteuerelemente sind lokal für den Browser und das Gerät, auf dem Sie sie eingestellt haben, einschließlich der Liste der verfügbaren Sprachen, Lautstärken und der verwendeten Ansagen oder Anzeigen.

Sprachauswahl wählt die Text-zu-Sprache-Engine. Die verfügbaren Optionen werden vom Webbrowser und vom Betriebssystem bereitgestellt.

Mit Ankündigungen kann der Benutzer wählen, ob er das Rufzeichen, die Rundennummer und / oder die Rundenzeit jedes Piloten beim Überqueren hören möchte. Die Ankündigung "Race Timer" zeigt perio an, wie viel Zeit verstrichen ist oder noch verbleibt, abhängig vom Timer-Modus im Race-Format. "Team Lap Total" wird nur verwendet, wenn "Team Racing Mode" aktiviert ist.

Sprachlautstärke, Frequenz und Tonhöhe steuern alle Text-zu-Sprache-Ansagen. "Tonlautstärke" steuert die Start- und Endsignale des Rennens.

Anzeigetöne sind sehr kurze Töne, die Rückmeldung über die Funktionsweise des Timers geben und am nützlichsten sind, wenn Sie versuchen, ihn abzustimmen. Jeder Knoten ist mit einer eindeutigen Tonhöhe gekennzeichnet. "Crossing Entered" piept einmal, wenn ein Pass beginnt, und "Crossing Exited" piept zweimal schnell, wenn ein Pass abgeschlossen ist. Die Taste "Manuelle Runde" piept einmal, wenn mit der Taste "Manuell" ein simulierter Durchgang erzwungen wird.

#### Rennformat

Rennformate definieren, wie ein Rennen durchgeführt wird. Wähle ein aktives Rennformat. Einstellungen, die Sie hier anpassen, werden im aktuell aktiven Format gespeichert.

Der Renntimer kann nach oben oder unten zählen, wie im Renn-Timer-Modus ausgewählt. Verwenden Sie "No Time Limit" für einen "First to X Laps" -Stil mit einem Timer, der von Null aufwärts zählt. Verwenden Sie "Feste Zeit" für einen Timer, der nach dem Start des Rennens auf Null herunterzählt. Die Zeitdauer wird im Modus "Feste Zeit" verwendet, um die Länge des Rennens zu bestimmen.

Jedes Rennen beginnt mit einer Inszenierungssequenz. Race Staging kann mit einer festen oder variablen Anzahl von Staging-Sekunden und mit oder ohne Staging-Töne durchgeführt werden. Stellen Sie die _Minimum Start Delay_ und _Maximum Start Delay_ auf die Werte (in Sekunden) ein, die für die Rennstrecke gewünscht werden. Wenn diese Werte unterschiedlich sind, wählt der Timer einen zufälligen Wert für die Staging-Zeit. Zufällige Staging-Zeiten sind nützlich, um Fehlstarts zu verhindern. Der Timer zeigt während der Bereitstellung "Bereit" an und verdeckt die Startzeit des Rennens. Stellen Sie für eine feste Staging-Zeit "Minimum" und "Maximum" auf den gleichen Wert ein. Der Staging-Timer zeigt offen die Anzahl der Sekunden an, bis das Rennen beginnt.

_Eine kleine Zeit wird benötigt, um sicherzustellen, dass der Timer mit der gesamten Hardware synchronisiert wurde, sodass selbst bei einer Staging-Zeit von Null eine kurze Staging-Zeitspanne vorhanden ist._

Während der Staging-Sequenz kann eine Anzahl von Tönen erzeugt werden, wie durch _Staging-Töne_ festgelegt. Bei "Jede Sekunde" gibt der Timer während der Inszenierung kontinuierlich einen Ton aus. Mit "Eins" gibt der Timer sofort zu Beginn der Inszenierung einen Ton aus. Bei "Keine" wird keine akustische Warnung ausgegeben. Unabhängig von der Einstellung _Staging Tones_ wird der Ton "Race Start" immer noch abgespielt, wenn das Staging abgeschlossen ist und das Rennen beginnt.

_Win Condition_ bestimmt, wie der Timer den Gewinner des Rennens anruft, welche Informationen im OSD und in der Streaming-Anzeige angezeigt werden und welche Sortiermethode für Bestenlisten verwendet wird. Die Sortierung der Bestenlisten wirkt sich auf die Ergebnisseite und den Wärmeerzeuger aus.

* __Die meisten Runden in der schnellsten Zeit__: Die Piloten werden anhand der Anzahl der absolvierten Runden und der Dauer ihrer Runden beurteilt. Wenn es ein Unentschieden für die Anzahl der absolvierten Runden gibt, wird der Pilot, der diese Runden in kürzerer Zeit absolviert hat, höher eingestuft.
* __Nur die meisten Runden__: Wird nur nach der Anzahl der abgeschlossenen Runden gewertet. Piloten mit der gleichen Rundenzahl sind gebunden. Verwenden Sie den Modus "Feste Zeit" für einen Rennstil, bevor das Timing zuverlässig war, oder den Modus "Kein Zeitlimit", um die größte Distanz anstelle der kürzesten Zeit zu beurteilen.
* __Die meisten Runden nur mit Überstunden__: Ähnlich wie _Most Runden in der schnellsten Zeit_, jedoch mit einer Komponente "Plötzlicher Tod". Wenn der Timer abläuft (oder das Rennen vorzeitig abgebrochen wird), wenn ein Pilot mehr Runden als alle anderen hat, ist dieser Pilot der Gewinner. Wenn nach Ablauf des Timers ein Gleichstand für die Rundenanzahl besteht, ist der erste der gebundenen Piloten auf der ganzen Linie der Gewinner.
* __Erste bis X Runden__: Das Rennen wird fortgesetzt, bis ein Pilot die gewünschte Rundenzahl erreicht hat. In diesem Modus wird der Parameter _Number of Laps to Win_ verwendet. Wird normalerweise im Rennmodus _No Time Limit_ verwendet.
* __Schnellste Runde__: Ignoriert den Rennfortschritt und berücksichtigt nur die schnellste Einzelrunde jedes Piloten.
* __Schnellste 3 aufeinanderfolgende Runden__: Berücksichtigt alle Runden, die ein Pilot absolviert hat, und verwendet die drei aufeinander folgenden Runden mit der schnellsten kombinierten Zeit.
* __None__: Erklärt unter keinen Umständen einen Gewinner. Vorläufe, die aus einer Klasse mit dieser Bedingung generiert wurden, werden zufällig zugewiesen.

_Team Racing Mode_ aktiviert die alternative Wertung für zusätzliche Rennformate. Die Gewinnbedingungen im Teamrennmodus unterscheiden sich etwas:

* __Die meisten Runden in der schnellsten Zeit__: Die Teams werden anhand der Gesamtzahl der Runden aller Mitglieder und der Dauer dieser Runden beurteilt.
* __Nur die meisten Runden__: Die Teams werden anhand der Gesamtzahl der kombinierten Runden aller Mitglieder beurteilt.
* __Die meisten Runden nur mit Überstunden__: Die Teams werden anhand der Gesamtzahl der kombinierten Runden aller Mitglieder beurteilt. Wenn nach Ablauf der Zeit ein Gleichstand besteht, gewinnt das erste Team (von dem Unentschieden), das eine Runde hinzugefügt hat, den Sieger.
* __Erste bis X Runden__: Das erste Team, das die gewünschte Anzahl kombinierter Runden erreicht hat, ist der Gewinner.
* __Schnellste Runde__: Nachdem alle Teammitglieder eine Runde beigesteuert haben, werden die Teams anhand des Durchschnitts der schnellsten Rundenzeit der Piloten beurteilt.
* __Schnellste 3 aufeinanderfolgende Runden__: Nachdem alle Teammitglieder 3 Runden beigesteuert haben, werden die Teams anhand des Durchschnitts der schnellsten "drei aufeinander folgenden Runden" der Piloten beurteilt.

Mit _Fastest Lap_ und _Fastest 3 Consecutive Laps_ können Teams mit unterschiedlich vielen Piloten fair miteinander konkurrieren.

_Minimale Rundenzeit_ markiert oder verwirft Pässe, bei denen Runden registriert worden wären, die kürzer als die angegebene Dauer sind. Verwenden Sie das Verhalten "Verwerfen" mit Vorsicht, da dadurch möglicherweise gültige Daten entfernt werden. _Minimum Lap Time_ wird nicht im Rennformat gespeichert.

#### LED-Effekte

Wählen Sie für jedes Timer-Ereignis einen visuellen Effekt. Der Timer zeigt diesen Effekt an, wenn das Ereignis eintritt, und überschreibt sofort alle vorhandenen Anzeigen oder Effekte. Einige visuelle Effekte sind nur für bestimmte Timer-Ereignisse verfügbar. Einige visuelle Effekte werden durch das Ereignis verändert, insbesondere die Farbe der Ein- und Ausgänge der Gate-Kreuzung. Die meisten Effekte können über das LED-Bedienfeld in der Vorschau angezeigt werden.

Einige LED-Effekte können sich kurz verzögern, wenn der Timer mit zeitkritischen Aufgaben beschäftigt ist. (Andere wie der Start des Rennens werden nie verzögert.) Aufgrund dieses Effekts und möglicherweise gleichzeitiger Überfahrten sollte "Ausschalten" normalerweise für Torausgänge vermieden werden. Verwenden Sie stattdessen _"No Change"_ am Gate-Eingang und den gewünschten Effekt beim Gate-Ausgang.

_Dieser Abschnitt wird nicht angezeigt, wenn für Ihren Timer keine LEDs konfiguriert sind. Ein Hinweis wird im Startprotokoll angezeigt._

#### LED-Steuerung

Dieser Abschnitt überschreibt die aktuelle LED-Anzeige. Wählen Sie diese Option, um die Anzeige vorübergehend auszuschalten, einige vorkonfigurierte Farben anzuzeigen, benutzerdefinierte Farben anzuzeigen oder einen definierten Effekt anzuzeigen. Sie können auch den Schieberegler verwenden, um die Helligkeit Ihres Panels anzupassen. Die ideale Einstellung für FPV-Kameras ist, wenn das beleuchtete Feld der Helligkeit eines weißen Objekts entspricht. Dadurch liegt die Panel-Ausgabe innerhalb des Dynamikbereichs, den die Kamera erfassen kann. Die Verwendung einer niedrigen Helligkeitseinstellung verzerrt jedoch die Farbwiedergabe und die Glätte der Farbübergänge.

_Dieser Abschnitt wird nicht angezeigt, wenn für Ihren Timer keine LEDs konfiguriert sind. Ein Hinweis wird im Startprotokoll angezeigt._

#### Datenbank

Wählen Sie, ob Sie die aktuelle Datenbank sichern (in einer Datei auf dem Pi speichern und zum Herunterladen auffordern) oder Daten löschen möchten. Sie können Rennen, Klassen, Vorläufe und Piloten beenden.

#### System

Wählen Sie die Sprache der Benutzeroberfläche aus und ändern Sie Parameter, die sich auf das Erscheinungsbild des Timers auswirken, z. B. Name und Farbschema. Sie können den Server auch von hier aus herunterfahren.

### Lauf

Auf dieser Seite können Sie den Timer steuern und Rennen starten.

Wählen Sie die Hitze für das Rennen, das als nächstes ausgeführt werden soll.

Starten Sie das Rennen, wenn Sie bereit sind. (Hotkey: <kbd>z</kbd>). Der Timer führt eine schnelle Kommunikation mit dem Server durch, um die Client / Server-Antwortzeit zu kompensieren, und beginnt dann mit dem durch das aktuelle Race-Format definierten Staging-Verfahren.

Die Tuning-Parameter können hier über die Taste eingestellt werden.Eine ausführliche Beschreibung und Tuning-Anleitung finden Sie hier [doc/Tuning Parameters.md](de-Tuning%20Parameters.md).

Während des Rennens steht neben jeder gezählten Runde ein "×". Dadurch wird dieser Rundenpass verworfen, sodass seine Zeit auf die nächste Runde verschoben wird. Verwenden Sie diese Option, um fehlerhafte zusätzliche Pässe zu entfernen oder Piloten zu bereinigen, die nach Beendigung des Rennens in der Nähe des Starttors fliegen.

Durch Drücken der Taste "+ Runde" wird manuell ein Rundenpass für diesen Knoten ausgelöst.

Wenn ein Rennen beendet ist, verwenden Sie die Schaltfläche "Rennen stoppen" (Hotkey: <kbd>x</kbd>), um das Zählen von Runden abzubrechen. Sie müssen dies auch dann tun, wenn der Timer in einem "Countdown" -Format Null erreicht. Ein beliebtes Rennformat ermöglicht es den Piloten, die Runde zu beenden, auf der sie sich befinden, wenn die Zeit abgelaufen ist. Um optimale Ergebnisse zu erzielen, löschen Sie das Timing-Gate und lassen Sie alle gültigen Überfahrten enden, bevor Sie das Rennen beenden.

Sobald ein Rennen beendet ist, müssen Sie "Runden speichern" oder "Runden verwerfen" wählen, bevor Sie ein anderes Rennen starten. "Runden speichern" (Hotkey: <kbd>c</kbd>) speichert die Rennergebnisse in der Datenbank und zeigt sie auf der Seite "Ergebnisse" an. "Runden verwerfen" (Hotkey: <kbd>v</kbd>) verwirft die Rennergebnisse. Durch das Speichern von Runden wird die Auswahl des Laufs automatisch auf den nächsten Lauf mit derselben Klasse wie beim gespeicherten Rennen vorgerückt.

Das Race Management-Bedienfeld bietet schnellen Zugriff zum Ändern des aktuellen Rennformats, Profils, der minimalen Rundenzeit oder des Team-Rennmodus. _Audio Control_ und _LED Control_ entsprechen der Seite Einstellungen. Der Verlaufsexport gibt eine CSV-Datei aus, die von den aufgezeichneten RSSI-Werten des zuletzt abgeschlossenen Rennens heruntergeladen werden soll. "Zeit bis zum Start des Rennens" plant ein Rennen, das zu einem späteren Zeitpunkt durchgeführt werden soll. Die Betreiber können dies verwenden, um ein festes Limit für die Zeit festzulegen, die Piloten zur Vorbereitung benötigen, oder um den Timer zu starten und dann selbst am Rennen teilzunehmen.

### Marshal

Passen Sie die Ergebnisse gespeicherter Rennen an.

Wählen Sie die Runde, die Hitze und den Piloten aus, um sie anzupassen. Ein- und Ausstiegspunkte werden automatisch aus den gespeicherten Renndaten geladen. Passen Sie die Ein- und Ausstiegspunkte an, um das Rennen nachträglich neu zu kalibrieren. "Vom Knoten laden", um aktuelle Live-Kalibrierungsdaten über die aktiven Werte zu kopieren. "Auf Knoten speichern", um die aktiven Werte über die aktuellen Live-Werte zu kopieren. "Rennen neu berechnen", um die aktiven Ein- / Ausstiegswerte als Kalibrierungspunkte für eine "Wiederholung" des Rennens zu verwenden. Dadurch werden aktuelle Runden gelöscht und durch die neu berechneten Informationen ersetzt. Manuell eingegebene Runden bleiben erhalten.

Fügen Sie Runden hinzu, indem Sie die Überfahrtzeit in Sekunden ab Rennbeginn eingeben und dann auf die Schaltfläche "Runde hinzufügen" klicken.

Löschen Sie Runden mit der Taste "×" in der unerwünschten Runde. Gelöschte Runden werden aus den Berechnungen entfernt, bleiben jedoch zur späteren Bezugnahme in den Daten vorhanden. "Runden verwerfen", um die Daten dauerhaft aus der Datenbank zu entfernen.

Sie können auf das Diagramm klicken / es berühren, um Ein- / Ausstiegspunkte festzulegen, die Neuberechnung zu aktivieren und bestimmte Runden hervorzuheben. Durch Klicken auf Runden in der Liste wird auch eine Markierung in der Grafik hinzugefügt. Drücken Sie <kbd>delete</kbd> oder <kbd>x</kbd>, um eine markierte Runde zu löschen. Aktive Runden werden grün angezeigt und gelöschte Runden werden rot. Die Breite der Rundenanzeige zeigt die Ein- / Ausstiegspunkte an, und die gelbe Markierung zeichnet eine Linie zur genauen Rundenzeit in diesem Fenster.

"Änderungen übernehmen", wenn Sie mit dem Anpassen der Renndaten fertig sind, um sie in der Datenbank zu speichern und die Rennergebnisse zu aktualisieren.
