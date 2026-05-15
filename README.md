# Berliner Kulturzettel

Tägliche Übersicht über Theater, Konzert, Ballett, Kunst und Lesung in Berlin.
Automatische Aktualisierung jede Nacht. Auf dem iPad als App-Icon nutzbar.

## Wie das Ganze funktioniert

```
   ┌──────────────────┐
   │   GitHub Repo    │  ←─ enthält App + Scraper
   └────────┬─────────┘
            │
   ┌────────┴─────────────────────┐
   │                              │
   ▼                              ▼
GitHub Actions          Netlify
(läuft 1×/Tag um 7 Uhr) (hostet die App als Website)
   │                              │
   ▼                              ▼
holt Veranstaltungen     deine URL: kulturzettel.netlify.app
und schreibt              ↑
events.json              (auf dem iPad öffnen und
   │                      „Zum Home-Bildschirm" → fertig)
   └─→ committet ins Repo
       Netlify deployed automatisch neu
```

Ergebnis: Du tippst auf das Icon auf dem iPad, die App öffnet sich mit
den aktuellsten Veranstaltungen. Komplett automatisch, dauerhaft kostenlos.

## Setup — Schritt für Schritt

Das ganze Setup geht vom iPad aus. Veranschlage ca. 20 Minuten.

### Schritt 1: GitHub-Account anlegen (falls noch nicht vorhanden)

Auf [github.com](https://github.com) registrieren. Kostenlos.

### Schritt 2: Repository erstellen

1. Auf GitHub auf **„New repository"** klicken
2. Name: `berlin-kulturzettel` (oder wie du willst)
3. **Public** wählen (damit GitHub Actions kostenlos läuft)
4. **„Create repository"**

### Schritt 3: Dateien hochladen

Auf der neuen Repository-Seite:
1. **„uploading an existing file"** klicken (im leeren Repo der Link mittig)
2. Den **gesamten Inhalt** des Ordners `berlin-kulturzettel` hochladen
   (Dateien einzeln auswählen — Drag&Drop funktioniert auch im iPad-Safari)
3. **Wichtig:** Die Struktur muss erhalten bleiben:
   ```
   .github/workflows/scrape.yml
   public/index.html
   public/manifest.json
   public/events.json
   public/icon-192.png
   public/icon-512.png
   public/apple-touch-icon.png
   scripts/scraper.py
   netlify.toml
   .gitignore
   README.md
   ```
4. Commit message: „Initial setup" — auf **„Commit changes"**

Falls Drag&Drop nicht klappt: Die GitHub-iOS-App ist eine Alternative,
oder du nutzt das **Working Copy**-App (iPadOS) für Git-Operationen.

### Schritt 4: Bei Netlify anmelden und Repo verbinden

1. Auf [netlify.com](https://netlify.com) gehen und **mit GitHub anmelden**
2. **„Add new site" → „Import an existing project"** → **GitHub**
3. Dein `berlin-kulturzettel`-Repo auswählen
4. Build-Einstellungen sind durch `netlify.toml` schon korrekt:
   - Publish directory: `public`
   - Build command: (leer)
5. **„Deploy site"**

Nach ca. 30 Sekunden ist die App live. Netlify gibt dir eine URL wie
`random-name-12345.netlify.app`. Die kannst du in den Site-Settings
zu etwas Schönerem umbenennen, z. B. `udo-kulturzettel.netlify.app`.

### Schritt 5: Auf dem iPad zum Home-Bildschirm hinzufügen

1. Die Netlify-URL im **Safari** öffnen (wichtig: Safari, nicht Chrome)
2. Auf das **Teilen-Symbol** tippen (Kasten mit Pfeil nach oben)
3. **„Zum Home-Bildschirm"** wählen
4. Name bestätigen → **„Hinzufügen"**

Jetzt hast du das Kulturzettel-Icon auf dem Home-Bildschirm.
Beim Antippen öffnet es sich im Vollbild, ohne Browser-Leiste —
wie eine echte App.

### Schritt 6: Den Scraper aktivieren

In deinem GitHub-Repo:
1. Tab **„Actions"** öffnen
2. Falls Actions deaktiviert sind: **„I understand my workflows, enable them"**
3. Im linken Menü auf **„Daten aktualisieren"** klicken
4. Rechts oben **„Run workflow"** → **„Run workflow"** bestätigen

Nach ca. 1–2 Minuten ist der erste Lauf fertig und `events.json`
ist mit echten Daten aktualisiert. Ab jetzt läuft das automatisch
jede Nacht um 7 Uhr morgens.

## Erste Hürden, die typisch auftreten

**„Der Scraper liefert nichts für Haus X."**
→ Normal. Die Scraper sind Vorlagen, jede Website ist anders gebaut.
Schau in `scripts/scraper.py` und passe die jeweilige Funktion an
(`scrape_schaubuehne`, `scrape_philharmonie` usw.). Wenn du mir die
URL und das HTML schickst, helfe ich beim Parser.

**„Actions schlägt fehl mit ‚permission denied'."**
→ Repo-Settings → Actions → General → **„Workflow permissions"** →
„Read and write permissions" anhaken.

**„Auf dem iPad wird die App im Browser geöffnet statt im Vollbild."**
→ Du hast die Seite vor dem „Zum Home-Bildschirm hinzufügen" wahrscheinlich
in Chrome geöffnet. In Safari nochmal versuchen.

**„Daten sind nicht aktuell."**
→ App schließen und neu öffnen (kompletter Swipe-up).
Safari/PWA cached aggressiv. Im Notfall: in Safari den Cache leeren
oder die URL mit `?neu=1` hinten dran aufrufen.

## Häuser anpassen

Im Skript `scripts/scraper.py` ist jedes Haus eine eigene Funktion.
Wenn du Häuser ergänzen/streichen willst, bearbeite die Liste `SCRAPERS`
am unteren Ende. Nach Speichern und Push läuft der nächste tägliche
Lauf mit der neuen Konfiguration.

## Datenformat events.json

```json
{
  "generated": "2026-05-15T08:00:00+02:00",
  "events": [
    {
      "id": "abc123",
      "title": "Der zerbrochne Krug",
      "category": "Theater",
      "venue": "Berliner Ensemble",
      "date": "2026-05-15",
      "time": "19:30",
      "url": "https://...",
      "description": "Kurzbeschreibung."
    }
  ]
}
```

Du kannst die Datei auch direkt im GitHub-Webeditor bearbeiten,
falls du einzelne Veranstaltungen von Hand pflegen willst.
Nach dem Speichern deployed Netlify automatisch neu.

## Kosten

Alles im Free-Tier:
- **GitHub**: unbegrenzte Public Repos
- **GitHub Actions**: 2000 Minuten/Monat (du nutzt vielleicht 5)
- **Netlify**: 100 GB Traffic/Monat, automatische HTTPS
