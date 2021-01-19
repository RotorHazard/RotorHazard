# Anleitung zur Ereigniseinrichtung

Die Grundlagen des Aufbaus einer Veranstaltung sind die Einrichtung von Piloten, Läufen und Knotenpunkten. Sie können auch Veranstaltungsdetails und Rennklassen hinzufügen, wenn Sie dies wünschen.

## Vorhandene Daten löschen (falls erforderlich)

Öffnen Sie unter Einstellungen die Datenbank. Verwenden Sie die Optionen hier, um veraltete Informationen aus der Datenbank zu entfernen.

## Ereignisdetails hinzufügen (optional)

Öffnen Sie unter Einstellungen das Ereignis-Panel. Aktualisieren Sie den Ereignisnamen und die Beschreibung. Diese werden auf der Startseite angezeigt, wenn Benutzer den Timer zum ersten Mal besuchen. Lassen Sie die Piloten wissen, was sie während der Veranstaltung erwartet, z.B. das Veranstaltungsformat und den Zeitplan.

## Piloten hinzufügen

Öffnen Sie unter Einstellungen das Panel Piloten. Fügen Sie für jeden teilnehmenden Piloten einen Eintrag hinzu. Der Name des Piloten wird auf der Veranstaltungsseite angezeigt; das Rufzeichen wird für die Anzeige der Rennergebnisse und für Sprachanrufe verwendet. Testen Sie die Sprachaussprache mit der Schaltfläche ">". Falls gewünscht, schreiben Sie eine phonetische Schreibweise. Diese wird nie angezeigt, wird aber zur Aussprache des Rufzeichens verwendet.

## Rennformate erstellen (optional)

Öffnen Sie unter Einstellungen die Rennformate. Passen Sie die [Einstellungen](de-User%20Guide.md#race-format) an oder erstellen Sie neue Formate, damit sie die Art der Startaufstellung Ihrer Gruppe, die Siegbedingungen usw. ändern können.

## Läufe und Klassen hinzufügen

**Läufe** sind Piloten, die zusammen zur genau gleichen Zeit fliegen. Benennen Sie Ihren Lauf, oder lassen Sie den Namen leer, um einen Standardnamen zu verwenden. Wählen Sie aus, welche Piloten genau zur gleichen Zeit fliegen, und fügen Sie sie zu einem Lauf hinzu. Die Anzahl der verfügbaren Lauf-Plätze wird durch die Anzahl der mit dem Timer verbundenen Knoten bestimmt. Verwenden Sie "Keine" für unbenutzte Lauf-Plätze.

**Klassen** sind Gruppen von Piloten mit gemeinsamen Eigenschaften. Wenn Sie mehr als eine Klasse benötigen, erstellen Sie Klassen, die darauf basieren, wie Ihre Veranstaltung strukturiert ist. Benennen Sie Ihre Klasse als Referenz an anderer Stelle. Die Klassenbeschreibung ist auf der Seite Veranstaltung sichtbar. Die Einstellung eines optionalen Formats zwingt alle Rennen innerhalb dieser Klasse, die gewählten Einstellungen für das Rennformat zu verwenden.

Weisen Sie den Klassen Läufe zu, um sie zu verwenden. Wenn ein Rennen für einen Lauf mit einer zugewiesenen Klasse gespeichert wird, werden die Ergebnisse für die Klasse separat berechnet und erscheinen als eigener Abschnitt innerhalb der Rennergebnisse.

## Knoten auf Umgebung abstimmen

Sobald der Timer am Rennort läuft, passen Sie die [Knotenparameter und Filtereinstellungen](de-Tuning%20Parameters.md) so an, dass sie der gewünschten Rennart am besten entsprechen. Optional können Sie ein Profil für diesen Ort erstellen, damit Sie es später leicht wieder laden können.

## Beispiel

8 Piloten werden sich zu einem Indoor-Micro-Quad-Rennen versammeln. Das Veranstaltungsformat besteht aus fünf Qualifikationsrunden, in denen die Gesamtrundenzahl zusammengezählt wird, wobei die vier besten Piloten in einen einzigen Endlauf aufsteigen. Vor der Veranstaltung addiert der Organisator alle Piloten in der Pilotenliste. Es werden zwei Klassen geschaffen, "Qualifying" und "Final", und beiden Klassen wird das Rennformat "Whoop Sprint" zugewiesen. Es werden zwei Läufe mit jeweils vier Piloten erstellt, und beide Läufe werden der Klasse "Qualifying" zugeordnet.

Am Tag der Veranstaltung wählt der Organisator das "Indoor"-Profil, um die gewünschten Frequenzen und Filtereinstellungen festzulegen, und stellt sicher, dass die Knoten richtig abgestimmt sind. Auf der Seite "Rennen" werden die Läufe jeweils fünf Mal durchgeführt. Der Zeitnehmer organisiert diese Läufe in die Runden 1 bis 5 für die Ergebnisseite, während die Läufe durchgeführt werden.

Nachdem die Qualifikations-Läufe beendet sind, überprüft der Veranstalter die Ergebnisseite und überprüft die "Qualifying"-Klasse, um die besten Piloten zu ermitteln. Der Organisator öffnet die Seite "Einstellungen" und das Panel "Vorläufe", erstellt einen neuen Lauf und weist ihm die vier besten Piloten zu, dann weist er dem Lauf die Klasse "Finale" zu. Das Rennen für diesen letzten Lauf wird durchgeführt. Auf der Ergebnisseite hält die Klasse "Final" die Ergebnisse des Finales und zeigt sie getrennt von den anderen an.
