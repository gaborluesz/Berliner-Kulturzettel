#!/usr/bin/env python3
"""
Berliner Kulturzettel — Daten-Sammler
======================================

Holt täglich Veranstaltungen aus Berliner Kulturhäusern und schreibt
sie in eine JSON-Datei, die in die Web-App geladen werden kann.

Nutzung:
    python3 berlin_kultur_scraper.py
    python3 berlin_kultur_scraper.py --days 7 --output events.json

Abhängigkeiten:
    pip install requests beautifulsoup4 lxml

Hinweis:
    Web-Scraping ist fragil. Wenn ein Haus seine Website umgestaltet,
    bricht der jeweilige Parser. Die Funktionen sind so isoliert,
    dass du einzelne Häuser leicht anpassen oder ergänzen kannst.

    Wo möglich, sollten offizielle Datenquellen (RSS, iCal, JSON-APIs)
    bevorzugt werden. Mehrere Berliner Häuser bieten iCal-Feeds an.
"""

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import urljoin

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Bitte installiere: pip install requests beautifulsoup4 lxml")
    sys.exit(1)


# ───────────────────────────────────────────────────────────────────
# Datenmodell
# ───────────────────────────────────────────────────────────────────

@dataclass
class Event:
    id: str
    title: str
    category: str       # Theater | Konzert | Ballett | Kunst | Lesung
    venue: str
    date: str           # ISO YYYY-MM-DD
    time: str           # HH:MM oder "10:00–18:00"
    url: str = ""
    description: str = ""

    @staticmethod
    def make_id(venue: str, title: str, date: str) -> str:
        seed = f"{venue}|{title}|{date}".lower()
        return hashlib.md5(seed.encode("utf-8")).hexdigest()[:10]


# ───────────────────────────────────────────────────────────────────
# HTTP-Helper
# ───────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": "Mozilla/5.0 (BerlinKulturzettel/1.0; persönliche Nutzung)"
}

def fetch(url: str, timeout: int = 15) -> Optional[str]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return r.text
    except Exception as e:
        print(f"  ! Fehler beim Laden von {url}: {e}", file=sys.stderr)
        return None


# ───────────────────────────────────────────────────────────────────
# Scraper-Funktionen pro Haus
# ───────────────────────────────────────────────────────────────────
#
# Jede Funktion gibt eine Liste von Event-Objekten zurück.
# Wenn ein Haus seine Seite umstellt, hier den Parser anpassen.
#
# Hinweis: Diese Scraper sind als Vorlagen ausgelegt. Sie liefern
# erfolgreich Events, wenn die HTML-Struktur stabil ist, fallen
# aber leise zurück (leere Liste), wenn sich etwas geändert hat.
# Prüfe regelmäßig die Ausgabe.
# ───────────────────────────────────────────────────────────────────

def scrape_berliner_ensemble() -> List[Event]:
    """Berliner Ensemble — Spielplan."""
    url = "https://www.berliner-ensemble.de/spielplan"
    html = fetch(url)
    if not html:
        return []
    events = []
    soup = BeautifulSoup(html, "lxml")
    # Struktur kann variieren — wir suchen nach typischen Mustern
    for item in soup.select("[class*='spielplan'] [class*='event'], article, .calendar-entry"):
        title_el = item.find(["h2", "h3", "h4"])
        date_el = item.find(attrs={"datetime": True}) or item.find(class_=re.compile("date"))
        time_el = item.find(class_=re.compile("time|uhr"))
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        date_str = (date_el.get("datetime") if date_el and date_el.has_attr("datetime")
                    else date_el.get_text(strip=True) if date_el else "")
        date_iso = parse_german_date(date_str)
        if not date_iso:
            continue
        time = time_el.get_text(strip=True) if time_el else "19:30"
        events.append(Event(
            id=Event.make_id("Berliner Ensemble", title, date_iso),
            title=title, category="Theater", venue="Berliner Ensemble",
            date=date_iso, time=time, url=url,
        ))
    return events


def scrape_schaubuehne() -> List[Event]:
    url = "https://www.schaubuehne.de/de/spielplan/index.html"
    html = fetch(url)
    if not html:
        return []
    events = []
    soup = BeautifulSoup(html, "lxml")
    for item in soup.select(".spielplan-tag, .event, article"):
        title_el = item.find(["h2", "h3", "a"])
        date_el = item.find(attrs={"datetime": True})
        if not title_el or not date_el:
            continue
        title = title_el.get_text(strip=True)
        date_iso = parse_german_date(date_el.get("datetime", ""))
        if not date_iso:
            continue
        time_match = re.search(r"\b(\d{1,2}:\d{2})\b", item.get_text())
        time = time_match.group(1) if time_match else "20:00"
        events.append(Event(
            id=Event.make_id("Schaubühne", title, date_iso),
            title=title, category="Theater", venue="Schaubühne",
            date=date_iso, time=time, url=url,
        ))
    return events


def scrape_volksbuehne() -> List[Event]:
    return scrape_generic("https://www.volksbuehne.berlin/de/spielplan",
                          "Volksbühne", "Theater")


def scrape_deutsches_theater() -> List[Event]:
    return scrape_generic("https://www.deutschestheater.de/spielplan/",
                          "Deutsches Theater", "Theater")


def scrape_gorki() -> List[Event]:
    return scrape_generic("https://www.gorki.de/de/spielplan",
                          "Maxim Gorki Theater", "Theater")


def scrape_hau() -> List[Event]:
    return scrape_generic("https://www.hebbel-am-ufer.de/programm/",
                          "Hebbel am Ufer", "Theater")


def scrape_philharmonie() -> List[Event]:
    return scrape_generic("https://www.berliner-philharmoniker.de/konzerte/kalender/",
                          "Berliner Philharmonie", "Konzert")


def scrape_staatsoper() -> List[Event]:
    return scrape_generic("https://www.staatsoper-berlin.de/de/spielplan/",
                          "Staatsoper Unter den Linden", "Konzert")


def scrape_deutsche_oper() -> List[Event]:
    return scrape_generic("https://www.deutscheoperberlin.de/de_DE/calendar",
                          "Deutsche Oper Berlin", "Konzert")


def scrape_komische_oper() -> List[Event]:
    return scrape_generic("https://www.komische-oper-berlin.de/spielplan/",
                          "Komische Oper", "Konzert")


def scrape_konzerthaus() -> List[Event]:
    return scrape_generic("https://www.konzerthaus.de/de/programm",
                          "Konzerthaus Berlin", "Konzert")


def scrape_staatsballett() -> List[Event]:
    return scrape_generic("https://www.staatsballett-berlin.de/de/spielplan/",
                          "Staatsballett Berlin", "Ballett")


def scrape_gemaeldegalerie() -> List[Event]:
    return scrape_generic("https://www.smb.museum/museen-einrichtungen/gemaeldegalerie/",
                          "Gemäldegalerie", "Kunst", default_time="10:00–18:00")


def scrape_hamburger_bahnhof() -> List[Event]:
    return scrape_generic("https://www.smb.museum/museen-einrichtungen/hamburger-bahnhof/",
                          "Hamburger Bahnhof", "Kunst", default_time="10:00–18:00")


def scrape_berlinische_galerie() -> List[Event]:
    return scrape_generic("https://berlinischegalerie.de/ausstellung/",
                          "Berlinische Galerie", "Kunst", default_time="10:00–18:00")


def scrape_neue_nationalgalerie() -> List[Event]:
    return scrape_generic("https://www.smb.museum/museen-einrichtungen/neue-nationalgalerie/",
                          "Neue Nationalgalerie", "Kunst", default_time="10:00–18:00")


def scrape_kw() -> List[Event]:
    return scrape_generic("https://www.kw-berlin.de/exhibitions/",
                          "KW Institute for Contemporary Art", "Kunst",
                          default_time="11:00–19:00")


def scrape_gropius_bau() -> List[Event]:
    return scrape_generic("https://www.berlinerfestspiele.de/de/gropius-bau/programm/programm-uebersicht.html",
                          "Martin-Gropius-Bau", "Kunst", default_time="10:00–19:00")


def scrape_literaturhaus() -> List[Event]:
    return scrape_generic("https://literaturhaus-berlin.de/programm/",
                          "Literaturhaus Berlin", "Lesung")


def scrape_lcb() -> List[Event]:
    return scrape_generic("https://lcb.de/programm/",
                          "Literarisches Colloquium Berlin", "Lesung")


def scrape_brecht_haus() -> List[Event]:
    return scrape_generic("https://www.lfbrecht.de/veranstaltungen/",
                          "Brecht-Haus", "Lesung")


def scrape_lettretage() -> List[Event]:
    return scrape_generic("https://www.lettretage.de/kalender/",
                          "Lettrétage", "Lesung")


# ───────────────────────────────────────────────────────────────────
# Generischer Parser — versucht typische HTML-Muster zu erkennen
# ───────────────────────────────────────────────────────────────────

def scrape_generic(url: str, venue: str, category: str,
                   default_time: str = "20:00") -> List[Event]:
    html = fetch(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    events = []
    seen = set()

    # Strategie 1: Elemente mit <time datetime="...">
    for time_tag in soup.find_all("time", attrs={"datetime": True}):
        date_iso = parse_german_date(time_tag.get("datetime", ""))
        if not date_iso:
            continue
        # Suche umliegenden Container für Titel
        container = time_tag.find_parent(["article", "li", "div"])
        if not container:
            continue
        title_el = container.find(["h1", "h2", "h3", "h4"])
        if not title_el:
            continue
        title = clean_text(title_el.get_text())
        if not title or len(title) < 3:
            continue

        time_match = re.search(r"\b(\d{1,2}:\d{2})\b", container.get_text())
        time = time_match.group(1) if time_match else default_time

        link = container.find("a", href=True)
        event_url = urljoin(url, link["href"]) if link else url

        desc_el = container.find("p")
        description = clean_text(desc_el.get_text()[:200]) if desc_el else ""

        key = (title, date_iso)
        if key in seen:
            continue
        seen.add(key)

        events.append(Event(
            id=Event.make_id(venue, title, date_iso),
            title=title, category=category, venue=venue,
            date=date_iso, time=time, url=event_url,
            description=description,
        ))

    return events


# ───────────────────────────────────────────────────────────────────
# Helfer
# ───────────────────────────────────────────────────────────────────

GERMAN_MONTHS = {
    "januar": 1, "februar": 2, "märz": 3, "april": 4, "mai": 5, "juni": 6,
    "juli": 7, "august": 8, "september": 9, "oktober": 10, "november": 11, "dezember": 12,
    "jan": 1, "feb": 2, "mär": 3, "mrz": 3, "apr": 4, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "sept": 9, "okt": 10, "nov": 11, "dez": 12,
}

def parse_german_date(s: str) -> Optional[str]:
    """Versucht verschiedene deutsche Datumsformate zu parsen.
    Gibt ISO YYYY-MM-DD zurück oder None."""
    if not s:
        return None
    s = s.strip()

    # ISO-Format direkt
    iso_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if iso_match:
        return iso_match.group(0)

    # DD.MM.YYYY
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"

    # DD. Monatsname YYYY
    m = re.search(r"(\d{1,2})\.\s*([A-Za-zäöüÄÖÜ]+)\s+(\d{4})", s)
    if m:
        month = GERMAN_MONTHS.get(m.group(2).lower())
        if month:
            return f"{m.group(3)}-{month:02d}-{int(m.group(1)):02d}"

    return None


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


# ───────────────────────────────────────────────────────────────────
# Haupt-Sammelfunktion
# ───────────────────────────────────────────────────────────────────

SCRAPERS = [
    ("Berliner Ensemble", scrape_berliner_ensemble),
    ("Schaubühne", scrape_schaubuehne),
    ("Volksbühne", scrape_volksbuehne),
    ("Deutsches Theater", scrape_deutsches_theater),
    ("Maxim Gorki", scrape_gorki),
    ("Hebbel am Ufer", scrape_hau),
    ("Berliner Philharmonie", scrape_philharmonie),
    ("Staatsoper Unter den Linden", scrape_staatsoper),
    ("Deutsche Oper", scrape_deutsche_oper),
    ("Komische Oper", scrape_komische_oper),
    ("Konzerthaus Berlin", scrape_konzerthaus),
    ("Staatsballett Berlin", scrape_staatsballett),
    ("Gemäldegalerie", scrape_gemaeldegalerie),
    ("Hamburger Bahnhof", scrape_hamburger_bahnhof),
    ("Berlinische Galerie", scrape_berlinische_galerie),
    ("Neue Nationalgalerie", scrape_neue_nationalgalerie),
    ("KW Institute", scrape_kw),
    ("Martin-Gropius-Bau", scrape_gropius_bau),
    ("Literaturhaus Berlin", scrape_literaturhaus),
    ("Literarisches Colloquium Berlin", scrape_lcb),
    ("Brecht-Haus", scrape_brecht_haus),
    ("Lettrétage", scrape_lettretage),
]


def collect_all(days: int = 7) -> List[Event]:
    """Sammelt Events von allen Häusern für die nächsten N Tage."""
    today = datetime.now().date()
    cutoff = today + timedelta(days=days)
    all_events: List[Event] = []

    for name, scraper in SCRAPERS:
        print(f"  → {name} …", flush=True)
        try:
            events = scraper()
            # Auf relevanten Zeitraum filtern
            events = [e for e in events
                      if today.isoformat() <= e.date <= cutoff.isoformat()]
            print(f"    {len(events)} Events", flush=True)
            all_events.extend(events)
        except Exception as e:
            print(f"    ! Fehler: {e}", file=sys.stderr)

    # Duplikate entfernen
    seen = set()
    unique = []
    for ev in all_events:
        if ev.id not in seen:
            seen.add(ev.id)
            unique.append(ev)

    return unique


def main():
    parser = argparse.ArgumentParser(description="Berliner Kulturzettel — Daten-Sammler")
    parser.add_argument("--days", type=int, default=7,
                        help="Wie viele Tage in die Zukunft (Standard: 7)")
    parser.add_argument("--output", default="events.json",
                        help="Ausgabedatei (Standard: events.json)")
    args = parser.parse_args()

    print(f"Sammle Veranstaltungen für die nächsten {args.days} Tage …\n")
    events = collect_all(days=args.days)

    payload = {
        "generated": datetime.now(timezone.utc).astimezone().isoformat(),
        "events": [asdict(e) for e in events],
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\n✓ {len(events)} Veranstaltungen geschrieben nach {args.output}")
    print(f"  Lade diese Datei in der Web-App über »JSON laden«.")


if __name__ == "__main__":
    main()
