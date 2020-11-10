# Versionshinweise zu RotorHazard 2.2.0

RotorHazard 2.2.0 bietet viele neue Funktionen und Korrekturen, darunter:

### Protokollierung

Die RotorHazard-Oberfläche verfügt jetzt über einen Menüpunkt "Serverprotokoll anzeigen" (im Menü "...") und eine Schaltfläche "Protokolle herunterladen", mit der eine ".zip" -Archivdatei erstellt und heruntergeladen wird, die alle verfügbaren Protokoll-, die aktuellen Konfigurations- und Datenbankdateien. Wenn Sie Probleme melden, wird dringend empfohlen, die Schaltfläche "Protokolle herunterladen" zu verwenden und die generierte ZIP-Datei einzuschließen.

### VRx-Steuerung

Siehe [doc/Video Receiver.md](doc/de-Video%20Receiver.md)

### Streaming

Die Menüoption _..._-> _Stream Displays_ generiert eine Liste von URLs, die von OBS direkt in Szenen eingefügt werden können.

### Erzeugung von Läufen

Aus dem Bereich _Einstellungen_ -> _Läufe_. Wenn eine andere Eingabeklasse als "Zufällig" ausgewählt ist, werden Vorläufe mit der Einstellung "Gewinnbedingung" des Rennformats der Eingabeklasse generiert. Niedrigere Läufe werden zuerst hinzugefügt.

### Ergebnisquelle anzeigen

Fahren Sie mit der Maus über oder klicken / tippen Sie auf die schnellste Runde oder die schnellste aufeinanderfolgende Zeit, um zu sehen, welche Runde / Hitze die Grundlage für diese Zeit war.

## Updates von RotorHazard 2.1.1

* VRx Control und OSD-Messaging (unterstützt ClearView 2.0) #291 #285 #236
* Dynamische Overlay-Seiten zur Verwendung mit Live-Streaming (OBS) #318 #282 #226
* Verbesserte Leistung bei der Ergebnisgenerierung und Zwischenspeicherung #293 #193 #113
* Erzeugung von Läufen aus Klassenergebnissen oder verfügbaren Piloten #304 #192
* Sortierung der Piloten nach Name oder Rufzeichen #297 #195 #177
* Aktivieren von "Entfernen nicht verwendeter Piloten, Vorläufe, Klassen" #300 #8
* Duplizierung von Vorläufen und Klassen #314 #180
* Neue Optionen für die Inszenierung von Tönen #268 #93 #189
* Anzeige der Läufe / Runden für das Ergebnis in der zusammenfassenden Bestenliste #298 #157
* Markieren Sie Runden, die nach dem Ende des Rennens mit fester Zeit aufgezeichnet wurden #209 #313
* Beliebige Benutzer-Text-zu-Sprache-Beschriftungen #315 #208 #161
* Hardware-Energieeinsparung #311
* Update der Knotenhardwareadressierung #277 #252
* Aktivieren der systeminternen Programmierung von Knoten #277 #262
* Verbesserte Protokollierung und Protokollsichtbarkeit #330 #324 #289 #283 #295 #301 #303
* In Datei #323 gespeicherte Protokolle
* Automatisches Bereinigen von Protokolldateien #323
* Verbesserte Datenbankwiederherstellung #308
* Internes Ereignissystem zum Auslösen von Verhalten; aktiviert Plugins und andere Integrationen von Drittanbietern #273 #299
* Probleme beim Überqueren von Pässen bei maxLapsWin-Rennen #348 wurden behoben
* Vereinfachung und Bereinigung des Knotencodes #296
* Knotenverlaufspufferung #230
* Hauptseite der Dokumentation #327
* Experimenteller Knoten-Tiefpassfilter #230
* Verbesserungen der Codestruktur #319 #287 #310
* Verbesserungen der Datenbankorganisation #267 #136
* Fehlerbehebungen #312 #305
* Das Update des Wärmeerzeugers beim Umbenennen der Klasse #332 wurde behoben
* Fehler behoben: Freqs Callout falsche Frequenzen #336
* Behoben, dass IMDtabler nicht verwendete Knoten #335 liest
* Dokumentation zu [Protokollierungskonfiguration](https://github.com/RotorHazard/RotorHazard/blob/master/doc/de-Software%20Setup.md#logging) hinzugefügt
* Versionshinweisdateien im Dokument hinzugefügt
* Andere Dokumentationsaktualisierungen

## Upgrade-Hinweise

Informationen zum Installieren von RotorHazard auf einem neuen System finden Sie in den Anweisungen in doc / Software Setup.md

So aktualisieren Sie eine vorhandene RotorHazard-Installation auf diese Version:

```
cd ~
wget https://codeload.github.com/RotorHazard/RotorHazard/zip/2.2.0 -O temp.zip
unzip temp.zip
mv RotorHazard RotorHazard.old
mv RotorHazard-2.2.0 RotorHazard
rm temp.zip
cp RotorHazard.old/src/server/config.json RotorHazard/src/server/
cp RotorHazard.old/src/server/database.db RotorHazard/src/server/
```

Die vorherige Installation landet im Verzeichnis 'RotorHazard.old', das gelöscht oder verschoben werden kann.

Die RotorHazard-Serverabhängigkeiten sollten ebenfalls aktualisiert werden (haben Sie etwas Geduld, dieser Befehl kann einige Minuten dauern):

```
cd ~/RotorHazard/src/server
sudo pip install --upgrade --no-cache-dir -r requirements.txt
```

## Knotencode (Arduino)

Für diese Version (seit 2.1.1) wurden Änderungen am Knotencode vorgenommen, um Hardware-Energieeinsparung, Verlaufspufferung, neue Hardware-Adressierungsspezifikation, systeminterne Programmierung und andere Funktionen zu ermöglichen. Bitte aktualisieren Sie diese mit dem in dieser Version enthaltenen Code.
