# Admin scripts voor ELO-beheer

Deze map bevat alle beheerscripts voor het valideren, herberekenen, analyseren, exporteren en synchroniseren van de ELO-geschiedenis en uitslagen van de tafelvoetbal-app.

## Waarom ELO-beheer?

Het ELO-systeem bepaalt de sterkte van elke speler op basis van hun prestaties in wedstrijden. Omdat de ELO-geschiedenis en de uitslagen de basis vormen voor alle ranglijsten en analyses, is het essentieel dat deze data:

- **Consistent** is tussen Firestore (de database) en lokale berekeningen
- **Herleidbaar** is: elke wijziging of correctie kan worden gevalideerd en geanalyseerd
- **Herstelbaar** is: bij fouten, bugs of correcties kan de volledige ELO-geschiedenis opnieuw worden opgebouwd uit de ruwe uitslagen

## Typische beheeracties

1. **Valideren van uitslagen**
   - Controleer of de ruwe uitslagen (CSV) logisch en compleet zijn (geen dubbele of ontbrekende timestamps, correcte namen, etc).
   - Script: `01_uitslagen_validatie.py`

2. **Herberekenen van ELO**
   - Bouw de volledige ELO-geschiedenis opnieuw op uit de gevalideerde uitslagen.
   - Script: `02_elo_herbereken_lokaal.py`

3. **Analyseren van ELO-resultaten**
   - Controleer of de winnaar en top 3 per seizoen correct zijn bepaald (op basis van de hoogste laatst bekende ELO).
   - Script: `03_elo_analyse_herberekend.py`

4. **Pushen naar Firestore**
   - Vervang de ELO-geschiedenis in Firestore door de lokaal herberekende versie, zodat de app altijd de juiste data toont.
   - Script: `04_elo_push_to_firestore.py`

5. **Vergelijken Firestore vs lokaal**
   - Controleer of de ELO-geschiedenis in Firestore exact overeenkomt met de lokale berekening.
   - Script: `05_elo_compare_firestore_vs_lokaal.py`

6. **Exporteren van data**
   - Exporteer de volledige ELO-geschiedenis of uitslagen uit Firestore naar CSV voor archief, analyse of migratie.
   - Scripts: `00_export_elo_firestore.py`, `00_export_wedstrijden_firestore.py`, `export_all_firestore_to_csv.py`

## Offline modus (CSV fallback)

Wanneer Firestore tijdelijk niet bereikbaar is (bijv. quota bereikt), blijft de app werken met CSV-fallbacks:

- Lezen (backup): app leest uit `csv/read/*.csv` als Firestore faalt voor spelers, wedstrijden, ELO, requests en afgeleide seizoenen.
- Schrijven (offline queue): nieuwe spelers, requests, uitslagen en ELO-updates worden in `csv/write/*.csv` opgeslagen.

Zodra Firestore weer beschikbaar is, kun je de offline writes importeren:

```powershell
& .\.venv\Scripts\Activate.ps1
python admin\import_offline_csv_writes.py --dry-run true   # bekijk wat er geïmporteerd wordt
python admin\import_offline_csv_writes.py --dry-run false  # voer import uit
```

Dit script doet:

- Spelers: voegt nieuwe namen toe (dupcheck op `speler_naam`).
- Requests: schrijft alle verzoeken met timestamp.
- Uitslagen: voegt unieke wedstrijden toe (dupcheck op spelers, score, timestamp), koppelt bijbehorende ELO-logs.
- ELO: schrijft ELO-logs voor geïmporteerde wedstrijden met dezelfde timestamp.

Tip: toon een melding in de UI wanneer de app in offline CSV-modus draait, zodat gebruikers weten dat hun invoer wordt gequeued en later gesynchroniseerd.

## Wanneer ELO-beheer uitvoeren?

- Na het importeren of corrigeren van uitslagen
- Na het herstellen van fouten in de database
- Bij twijfel over de juistheid van de ranglijsten of ELO-scores
- Periodiek, als controle of backup

## Belangrijk

- **Altijd eerst valideren** voor je ELO's herberekent of pusht!
- **Controleer altijd de analyse** na een herberekening: klopt de winnaar/top 3 per seizoen?
- **Vergelijk altijd Firestore met lokaal** na een push, zodat je zeker weet dat de app de juiste data toont.

Voor vragen of uitleg: zie de code of neem contact op met de beheerder.
