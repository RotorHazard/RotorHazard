# Kalibrierungs- und Sensorabstimmungsparameter

_Wenn Sie Probleme beim Kalibrieren Ihres Timers haben, stellen Sie sicher, dass Sie die [HF-Abschirmung](Shielding%20and%20Course%20Position.md) korrekt konstruiert und platziert haben._

Jeder Knoten verfolgt die Signalstärke (RSSI) auf einer ausgewählten Frequenz und verwendet diese relative Stärke, um zu bestimmen, ob sich ein Sender in der Nähe des Timing-Gates befindet. Mit dem RotorHazard-Zeitmesssystem können Sie jeden Knoten einzeln kalibrieren, um das Verhalten und die Hardwareunterschiede zwischen System und Umgebung auszugleichen.

Ein Knoten kann *Crossing* oder *Clear* sein. Wenn ein Knoten *Clear* ist, glaubt das System, dass sich ein Sender nicht in der Nähe des Timing-Gates befindet, da der RSSI niedrig ist. Wenn es sich um *Crossing* handelt, geht das System davon aus, dass ein Sender am Timing Gate vorbeikommt, da der RSSI hoch ist. Ein Rundenpass wird aufgezeichnet, sobald die *Überfahrt* beendet ist und das System zu *Löschen* zurückkehrt.

![Tuning Graph](../img/Tuning%20Graph-06.svg)<br />
_RSSI während eines Rennens erscheint ähnlich wie diese Grafik mit vielen sichtbaren Gipfeln und Tälern. Wenn sich der Sender dem Timing-Gate nähert, steigt das Signal an._

## Parameter

Zwei Parameter, die sich auf den Status *Crossing* auswirken: *EnterAt* und *ExitAt*.

### EnterAt

Das System wechselt zu *Crossing*, wenn RSSI auf oder über dieses Niveau steigt. Es wird durch eine rote Linie angezeigt.

### ExitAt

Das System wechselt zu *Löschen*, sobald der RSSI-Wert unter diesen Wert fällt. Es wird durch eine orange Linie angezeigt.

Zwischen *EnterAt* und *ExitAt* bleibt das System je nach vorherigem Status *Crossing* oder *Clear*.

![Sample RSSI Graph](../img/Sample%20RSSI%20Graph.svg)

### Kalibrierungsmodus

Der *manuelle* Kalibrierungsmodus verwendet immer die vom Benutzer angegebenen Werte *EnterAt* und *ExitAt*.

Der *adaptive* Kalibrierungsmodus verwendet die benutzerdefinierten Punkte, sofern keine Rennen gespeichert sind. Wenn gespeicherte Rennen vorhanden sind, wird durch Ändern der Vorläufe eine Suche in den vorherigen Renndaten nach den besten Kalibrierungswerten für das bevorstehende Rennen eingeleitet. Diese Werte werden kopiert und ersetzen die aktuellen Werte *EnterAt* und *ExitAt* für alle Knoten. Dieser Modus verbessert die Kalibrierung, da mehr Rennen gespeichert werden, wenn der Rennleiter die Anzahl der eingehenden Runden bestätigt oder sie über die Seite *Marschall* neu berechnet.

### Start des Rennens EnterAt/ExitAt Absenkung

Zu Beginn eines Rennens können viele Quads gleichzeitig durch das Starttor fahren, und dies kann dazu führen, dass auf einigen Knoten niedrigere RSSI-Werte erkannt werden (was dazu führen kann, dass ein anfänglicher Gate-Pass verpasst wird). Um dies zu berücksichtigen, können die folgenden Einstellungen konfiguriert werden:

*Start des Rennens EnterAt / ExitAt-Senkungsbetrag (Prozent):* Legt den Betrag fest, um den die EnterAt- und ExitAt-Werte für alle Knoten in Prozent reduziert werden. Wenn beispielsweise 30 (Prozent) konfiguriert ist, wird der EnterAt-Wert auf einen Wert gesenkt, der 30% näher am ExitAt-Wert liegt. (Wenn also EnterAt=90 und ExitAt=80 ist, wird der EnterAt-Wert auf 87 gesenkt.) Der ExitAt-Wert wird ebenfalls um denselben Betrag gesenkt.

*Startbeginn EnterAt / ExitAt-Absenkungsdauer (Sekunden):* Legt die maximale Zeitspanne (in Sekunden) fest, in der die EnterAt- und ExitAt-Werte gesenkt werden. Wenn eine Gate-Kreuzung für einen Knoten vor diesem Zeitpunkt als abgeschlossen erkannt wird, werden die EnterAt- und ExitAt-Werte für diesen Knoten wiederhergestellt.

Vorgeschlagene Werte sind 30 (Prozent) und 10 (Sekunden). Wenn eine dieser Einstellungen als Null konfiguriert ist, werden die EnterAt- und ExitAt-Werte nicht gesenkt.

Beachten Sie, dass auf der Seite *Marschall* diese Einstellungen berücksichtigt werden. Wenn sie also nicht Null sind, wird möglicherweise der erste Rundenpass auf einem Knoten erkannt, obwohl der maximale RSSI-Wert niedriger als der angezeigte EnterAt-Wert zu sein scheint.

## Tuning

Schalten Sie den Timer vor dem Einstellen ein und lassen Sie ihn einige Minuten laufen, damit sich die Empfängermodule erwärmen können. Die RSSI-Werte steigen in der Regel um einige Punkte an, wenn sich der Timer erwärmt.

Auf der Seite *Marschall* können Sie Werte visuell einstellen. Sammeln Sie Daten, indem Sie auf jedem Kanal ein Rennen mit einem Piloten durchführen, und speichern Sie sie dann. Öffnen Sie die Seite *Marschall* und zeigen Sie die Renndaten an. Passen Sie die Ein- und Ausstiegspunkte an, bis die Anzahl der Runden korrekt ist. Speichern Sie die Eingabe- / Ausstiegspunkte auf jedem Knoten, um sie als Kalibrierung für zukünftige Rennen zu verwenden.

### Stellen Sie den Wert *EnterAt* ein

![Tuning Graph](../img/Tuning%20Graph-10.svg)

* Unterhalb der Spitze aller Torübergänge
* Über jeder Spitze, wenn sich der Sender nicht in der Nähe des Gates befindet
* Höher als *ExitAt*

### Stellen Sie den Wert *ExitAt* ein

![Tuning Graph](../img/Tuning%20Graph-11.svg)

* Unterhalb von Tälern, die während einer Torüberquerung auftreten
* Über dem niedrigsten Wert, der während einer Runde gesehen wurde
* Niedriger als *EnterAt*

ExitAt-Werte, die näher an EnterAt liegen, ermöglichen es dem Timer, Runden früher anzukündigen und anzuzeigen, können jedoch dazu führen, dass mehrere Runden aufgezeichnet werden.

### Tuning Beispiel

![Tuning Graph](../img/Tuning%20Graph-01.svg)<br />
_Zwei Runden werden aufgezeichnet. Das Signal steigt über *EnterAt* und fällt dann zweimal unter *ExitAt*, einmal an jedem Peak. Innerhalb dieser beiden Kreuzungsfenster findet der Timer nach der Rauschfilterung das stärkste Signal, das als aufgezeichnete Rundenzeit verwendet werden kann._

### Alternative Tuning Methode

Mit den Schaltflächen *Capture* kann der aktuelle RSSI-Wert als *EnterAt* - oder *ExitAt* -Wert für jeden Knoten gespeichert werden. Die Werte können auch manuell eingegeben und angepasst werden.

Schalten Sie ein Quad auf dem richtigen Kanal ein und bringen Sie es einige Sekunden lang sehr nahe an den Timer. Dadurch kann der Timer den RSSI-Spitzenwert für diesen Knoten erfassen. Dies sollte für jeden Knoten / Kanal erfolgen, der abgestimmt wird. Der Spitzenwert wird angezeigt.

#### EnterAt

Ein guter Ausgangspunkt für *EnterAt* ist die Erfassung des Werts mit einem Quad, das etwa 1,5 bis 3 m vom Timer entfernt ist.

#### ExitAt

Ein guter Ausgangspunkt für *ExitAt* ist die Erfassung des Werts mit einem Quad, das etwa 6 bis 9 m vom Timer entfernt ist.

## Anmerkungen

* Ein niedriger *ExitAt* -Wert kann immer noch ein genaues Timing liefern, aber das System wartet länger, bevor Runden angekündigt werden. Eine Verzögerung bei der Ansage hat keinen Einfluss auf die Genauigkeit des Timers.
* Die Einstellung *Minimale Rundenzeit* kann verwendet werden, um zusätzliche Durchgänge zu verhindern, kann jedoch Kreuzungen maskieren, die zu früh ausgelöst werden. Es wird empfohlen, das Verhalten bei *Hervorheben* anstatt bei *Verwerfen* zu belassen.
* Wenn während eines Rennens Zeitprobleme auftreten und die RSSI-Grafiken auf den Senderstandort reagieren, beenden Sie das Rennen nicht. Speichern Sie das Rennen nach Abschluss und besuchen Sie die Seite *Marschall*. Der gesamte RSSI-Verlauf wird gespeichert und das Rennen kann mit aktualisierten Tuning-Werten genau neu berechnet werden.

## Fehlerbehebung

### Fehlende Runden (System normalerweise *Löschen*)

![Tuning Graph](../img/Tuning%20Graph-04.svg)<br />
_Runden werden nicht aufgezeichnet, wenn RSSI EnterAt nicht erreicht wurde._

* Senken Sie *EnterAt*

### Fehlende Runden (System normalerweise *Crossing*)

![Tuning Graph](../img/Tuning%20Graph-05.svg)<br />
_Runden werden zusammengeführt, wenn *ExitAt* zu hoch ist, weil die erste Rundenüberquerung nie abgeschlossen wird._

* Erhöhen Sie *ExitAt*

### Runden registrieren sich für andere Teile eines Kurses

![Tuning Graph](../img/Tuning%20Graph-03.svg)<br />
_Extra-Kreuzungen treten auf, wenn *EnterAt* zu niedrig ist._

* Erhöhen Sie *EnterAt*, bis *Kreuzungen* erst in der Nähe des Timing-Gates beginnen. (Verwenden Sie nach dem Speichern eines Rennens die Seite *Marschall*, um die besten Werte zu ermitteln und zu speichern.)

### Viele Runden werden gleichzeitig registriert

![Tuning Graph](../img/Tuning%20Graph-02.svg)<br />
_Zu viele Runden treten auf, wenn *ExitAt* zu nahe an *EnterAt* liegt, weil Runden zu schnell beendet werden._

* Erhöhen Sie nach Möglichkeit *EnterAt*
* Niedriger *ExitAt*

Die Einstellung *Minimale Rundenzeit* behält immer die erste Überfahrt bei und verwirft nachfolgende Runden, die zu früh auftreten. In diesem Fall würde diese Einstellung die richtige erste Kreuzung verwerfen und die falsche zweite Kreuzung beibehalten. Es wird empfohlen, das Verhalten *Minimale Rundenzeit* bei *Hervorheben* anstatt bei *Verwerfen* zu belassen, damit ein Rennveranstalter jeden Fall manuell überprüfen kann.

### Die Registrierung der Runden dauert lange

![Tuning Graph](../img/Tuning%20Graph-09.svg)<br />
_Die Rundenaufzeichnung dauert lange, wenn *ExiAt* niedrig ist. Dies hat keinen Einfluss auf die Genauigkeit der aufgezeichneten Zeit._

* Erhöhen Sie *ExitAt*

### Der Knoten kreuzt niemals

![Tuning Graph](../img/Tuning%20Graph-07.svg)<br />
_Laps werden nicht registriert, wenn RSSI *EnterAt* nie erreicht ._

* Senken Sie *EnterAt*

### Der Knoten ist niemals *klar*

![Tuning Graph](../img/Tuning%20Graph-08.svg)<br />
_Laps werden nicht abgeschlossen, wenn RSSI niemals unter *ExitAt* fällt ._

* Erhöhen Sie *ExitAt*
