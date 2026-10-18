# 🛠️ Admin Scripts & Database Onderhoud

Deze map (`admin/`) bevat zelfstandige Python-scripts voor beheerders om de Firestore-database en de Google Sheets back-up te inspecteren, auditen, synchroniseren en onderhouden buiten de reguliere Streamlit-interface om.

> **💡 Tip:** Voer alle scripts altijd uit vanuit de **hoofdmap (root)** van het project, met de virtuele omgeving (`.venv`) geactiveerd, zodat alle imports en de authenticatie (`firestore-key.json` of `.streamlit/secrets.toml`) goed worden gevonden.

```powershell
# Activeer eerst de virtuele omgeving vanuit de hoofdmap:
.\.venv\Scripts\Activate.ps1
```

---

## 📂 Overzicht van Beschikbare Scripts

### 1. 🔄 Synchronisatie & Back-ups

| Script | Gebruik & Beschrijving |
| :--- | :--- |
| **`sync_firestore_to_sheets.py`** | Synchroniseert alle collecties (`Spelers`, `Wedstrijden`, `ELO_Logs`, `Verzoeken`, `Beheer_Log`) vanuit Firestore naar het Google Sheets back-upbestand.<br>**Commando:** `python admin/sync_firestore_to_sheets.py` |
| **`export_all_firestore_to_csv.py`** | Exporteert alle Firestore-collecties én de afgeleide seizoenen naar lokale CSV-bestanden (standaard in `data/exports/<timestamp>/`). Ideaal voor lokale archieven of diepte-analyses.<br>**Commando:** `python admin/export_all_firestore_to_csv.py --outdir data/exports` |
| **`reconcile_csv_to_sheets.py`** | Voegt lokale CSV-bestanden (uit `csv/read/`) en Firestore-data samen, ontdubbelt ze en pusht het gecombineerde resultaat naar Google Sheets.<br>**Commando:** `python admin/reconcile_csv_to_sheets.py` |
| **`import_offline_csv_writes.py`** | *Legacy / Nood-script:* Importeert lokaal opgeslagen CSV-wijzigingen uit `csv/write/` naar Firestore met duplicaatcontrole. Standaard draait dit veilig in `dry-run` modus.<br>**Commando (test):** `python admin/import_offline_csv_writes.py --dry-run true`<br>**Commando (echt schrijven):** `python admin/import_offline_csv_writes.py --dry-run false` |

---

### 2. 🧮 ELO-Herberekening & Seizoensonderhoud

Wanneer er via het tabblad **⚙️ Beheer** in de app een wedstrijd wordt verwijderd of aangepast, zet de app een vlag (`recalc_needed = True` in `system_config/elo_recalc`). Normaal gesproken voert de app deze herberekening automatisch uit na **23:00 uur**. Met onderstaande tools kun je dit proces handmatig aansturen:

| Script | Gebruik & Beschrijving |
| :--- | :--- |
| **`recalculate_elo_cron.py`** | Controleert of er een ELO-herberekening gepland staat en voert deze uit. Gebruik de `--force` vlag om de 23:00-uur tijdcheck te negeren en direct vanaf de vroegst gewijzigde wedstrijd te herberekenen.<br>**Commando (normaal):** `python admin/recalculate_elo_cron.py`<br>**Commando (direct forceren):** `python admin/recalculate_elo_cron.py --force` |
| **`delete_elo_history_for_season.py`** | Bevat de hulpfunctie `delete_elo_history_for_season(start_date, end_date, dry_run=False)` om gericht ELO-logdocumenten binnen een specifieke datumreeks in batches te verwijderen (bijv. voorafgaand aan een schone seizoensopbouw). |
| **`analyze_klinker_impact.py`** | Analyse- en simulatiescript dat historische wedstrijden chronologisch afspeelt om de correlatie en impact van *klinkers* op individuele ELO-stijgingen te verifiëren.<br>**Commando:** `python admin/analyze_klinker_impact.py` |

---

### 3. 👥 Spelerbeheer & Database Inspectie

| Script | Gebruik & Beschrijving |
| :--- | :--- |
| **`merge_players.py`** | Interactief CLI-script om dubbele spelers (bijv. door spelfouten of oude aliassen) veilig samen te voegen tot één hoofdnaam. Werkt automatisch alle verwijzingen bij in `uitslag`, `elo` en `beheer_log`, en verwijdert daarna het dubbele speler-document.<br>**Commando:** `python admin/merge_players.py` |
| **`full_player_audit.py`** | Voert een volledige audit uit op alle spelersnamen in Firestore en lokale CSV's. Spoort encoding-fouten (`?`, vreemde tekens), bijna-dubbele namen (case/accent-verschillen) en spelers die wel in wedstrijden voorkomen maar ontbreken in de `spelers`-collectie op.<br>**Commando:** `python admin/full_player_audit.py` |
| **`inspectie.py`** | Vergelijkt het daadwerkelijke schema in Firestore (op basis van een steekproef van documenten) met het verwachte schema uit `db.expected_schema()`. Toont ontbrekende en onverwachte velden per collectie.<br>**Commando:** `python admin/inspectie.py` |
| **`check_final.py`** | Klein diagnostisch script om snel te controleren of de rating van een specifieke speler synchroon loopt tussen Firestore en de Google Sheets fallback.<br>**Commando:** `python admin/check_final.py` |

---

## ⚠️ Richtlijnen voor Veilig Beheer

1. **Maak altijd eerst een export:** Voer vóór grote herberekeningen of speler-merges altijd eerst `python admin/export_all_firestore_to_csv.py` uit zodat je een lokale snapshot hebt.
2. **Eenvoudige naamswijziging vs. Samenvoegen (Merge):**
   - Wil je alleen een typfout in een naam herstellen naar een naam die **nog niet bestaat**? Dat kan direct in de app via **⚙️ Beheer → ✏️ Bewerken**.
   - Bestaan er **twee aparte spelers** die eigenlijk dezelfde persoon zijn? Gebruik dan `python admin/merge_players.py` zodat hun volledige wedstrijd- en ELO-historie netjes wordt samengevoegd.
3. **Let op Firestore Quota:** Het volledig wissen en opnieuw opbouwen van alle ELO-logs over meerdere jaren kost veel Firestore-writes. Gebruik daarom bij voorkeur de incrementele herberekening (`recalculate_elo_cron.py --force`) die alleen herberekent vanaf de vroegst gewijzigde wedstrijd binnen het betreffende seizoen.
