"""
Script: admin/elo_analyse_herberekend.py

- Analyseert de lokaal herberekende ELO geschiedenis (ELO_Herberekend_*.csv) en de uitslagen (Tafelvoetbal_Uitslagen_*.csv)
- Rapporteert:
    * Winnaars per seizoen (hoogste ELO aan eind seizoen)
    * Top 5 huidig seizoen
    * Metrics: aantal unieke spelers, aantal matches, gemiddelde ELO, min/max ELO per seizoen
    * Check: alle spelers met ELO-score komen voor in uitslagen per seizoen
"""
import os
import glob
import pandas as pd
from datetime import datetime

# --- Config ---
DATA_DIR = 'data'
ELO_HERBEREKEND_PATTERN = os.path.join(DATA_DIR, 'ELO_Herberekend_*.csv')
UITSLAGEN_PATTERN = os.path.join(DATA_DIR, 'Tafelvoetbal_Uitslagen_*.csv')

# --- Helpers ---
def parse_seizoen_from_matchdatum(datum):
    # datum: '2023-09-01' of '2023-09-01 20:00:00'
    jaar = int(str(datum)[:4])
    maand = int(str(datum)[5:7])
    if maand >= 8:
        return f"{jaar}/{jaar+1}"
    else:
        return f"{jaar-1}/{jaar}"

def get_latest_file(pattern):
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError(f"Geen bestanden gevonden voor pattern: {pattern}")
    return max(files, key=os.path.getmtime)

# --- Load data ---
elo_file = get_latest_file(ELO_HERBEREKEND_PATTERN)
elo_df = pd.read_csv(elo_file)

uitslagen_file = get_latest_file(UITSLAGEN_PATTERN)
uitslagen_df = pd.read_csv(uitslagen_file)

# --- Seizoen kolom toevoegen ---
elo_df['seizoen'] = elo_df['timestamp'].apply(parse_seizoen_from_matchdatum)
uitslagen_df['seizoen'] = uitslagen_df['timestamp'].apply(parse_seizoen_from_matchdatum)

# --- Analyse per seizoen ---
seizoenen = sorted(elo_df['seizoen'].unique())
print(f"Gevonden seizoenen: {seizoenen}\n")

for seizoen in seizoenen:
    print(f"=== Seizoen {seizoen} ===")
    elo_seizoen = elo_df[elo_df['seizoen'] == seizoen]
    uitslagen_seizoen = uitslagen_df[uitslagen_df['seizoen'] == seizoen]
    # Seizoensgrenzen bepalen
    if not uitslagen_seizoen.empty:
        eerste_uit = uitslagen_seizoen['timestamp'].min()
        laatste_uit = uitslagen_seizoen['timestamp'].max()
    else:
        eerste_uit = laatste_uit = None
    if not elo_seizoen.empty:
        eerste_elo_dt = elo_seizoen['timestamp'].min()
        laatste_elo_dt = elo_seizoen['timestamp'].max()
    else:
        eerste_elo_dt = laatste_elo_dt = None
    print(f"  Uitslagen-csv: {eerste_uit} t/m {laatste_uit}")
    print(f"  ELO-csv     : {eerste_elo_dt} t/m {laatste_elo_dt}")
    # Winnaar: hoogste ELO na laatste wedstrijd
    laatste_datum = laatste_elo_dt
    laatste_elo = elo_seizoen[elo_seizoen['timestamp'] == laatste_datum]
    winnaar = laatste_elo.sort_values('rating', ascending=False).iloc[0]
    print(f"Winnaar (ELO-csv): {winnaar['speler_naam']} (ELO: {winnaar['rating']:.1f})")
    # Top 5
    top5 = laatste_elo.sort_values('rating', ascending=False).head(5)
    print("Top 5 laatste ELO (ELO-csv):")
    for i, row in enumerate(top5.itertuples(), 1):
        print(f"  {i}. {row.speler_naam} ({row.rating:.1f})")
    # Metrics
    unieke_spelers = elo_seizoen['speler_naam'].nunique()
    aantal_matches = uitslagen_seizoen['match_id'].nunique()
    gem_elo = laatste_elo['rating'].mean()
    min_elo = laatste_elo['rating'].min()
    max_elo = laatste_elo['rating'].max()
    print(f"Aantal unieke spelers (ELO-csv): {unieke_spelers}")
    print(f"Aantal matches (uitslagen-csv): {aantal_matches}")
    print(f"Gemiddelde ELO (laatste, ELO-csv): {gem_elo:.1f}")
    print(f"Min/Max ELO (laatste, ELO-csv): {min_elo:.1f} / {max_elo:.1f}")
    # Check: alle spelers met ELO-score komen voor in uitslagen
    spelers_elo = set(elo_seizoen['speler_naam'].unique())
    spelers_uitslag = set(pd.unique(uitslagen_seizoen[['thuis_1', 'thuis_2', 'uit_1', 'uit_2']].values.ravel('K')))
    spelers_uitslag.discard(None)
    spelers_uitslag.discard(float('nan'))
    spelers_uitslag = {s for s in spelers_uitslag if isinstance(s, str) and s.strip()}
    ontbrekend = spelers_elo - spelers_uitslag
    if ontbrekend:
        print(f"Waarschuwing: {len(ontbrekend)} spelers met ELO-score (ELO-csv) niet in uitslagen van dit seizoen (uitslagen-csv):")
        for s in sorted(ontbrekend):
            print(f"  - {s}")
    else:
        print("Alle spelers met ELO-score (ELO-csv) komen voor in uitslagen van dit seizoen (uitslagen-csv).")
    print()

# --- Check: spelers in uitslagen maar niet in ELO-csv ---
    spelers_elo = set(elo_df[elo_df['seizoen'] == seizoen]['speler_naam'].unique())
    spelers_uitslag = set(pd.unique(uitslagen_df[uitslagen_df['seizoen'] == seizoen][['thuis_1', 'thuis_2', 'uit_1', 'uit_2']].values.ravel('K')))
    spelers_uitslag.discard(None)
    spelers_uitslag.discard(float('nan'))
    spelers_uitslag = {s for s in spelers_uitslag if isinstance(s, str) and s.strip()}
    ontbrekende_elo = spelers_uitslag - spelers_elo
    if ontbrekende_elo:
        print(f"[WAARSCHUWING] De volgende spelers komen wel voor in de uitslagen-csv van seizoen {seizoen}, maar hebben geen enkele ELO-regel in de ELO-csv van dat seizoen:")
        for s in sorted(ontbrekende_elo):
            print(f"  - {s}")

# --- Speciale analyse voor speler Robert ---
print("\n=== Speciale analyse: Robert ===")
robert_stats = []
for seizoen in seizoenen:
    uitslagen_seizoen = uitslagen_df[uitslagen_df['seizoen'] == seizoen]
    elo_seizoen = elo_df[elo_df['seizoen'] == seizoen]
    # Filter wedstrijden waar Robert meespeelt
    mask = uitslagen_seizoen[['thuis_1', 'thuis_2', 'uit_1', 'uit_2']].apply(lambda row: 'Robert' in row.values, axis=1)
    robert_matches = uitslagen_seizoen[mask]
    n_matches = len(robert_matches)
    # Goals tellen
    goals = 0
    for idx, row in robert_matches.iterrows():
        if row['thuis_1'] == 'Robert' or row['thuis_2'] == 'Robert':
            goals += row['thuis_score']
        if row['uit_1'] == 'Robert' or row['uit_2'] == 'Robert':
            goals += row['uit_score']
    # ELO van Robert en winnaar: pak laatste bekende ELO in seizoen
    if not elo_seizoen.empty:
        robert_elo_rows = elo_seizoen[elo_seizoen['speler_naam'] == 'Robert']
        robert_elo = robert_elo_rows.sort_values('timestamp').iloc[-1]['rating'] if not robert_elo_rows.empty else None
        # Winnaar: hoogste laatst bekende ELO in seizoen
        laatste_elo_per_speler = elo_seizoen.sort_values('timestamp').groupby('speler_naam').tail(1)
        winnaar_row = laatste_elo_per_speler.sort_values('rating', ascending=False).iloc[0]
        winnaar_naam = winnaar_row['speler_naam']
        winnaar_elo = winnaar_row['rating']
        # Uitslagen-metrics winnaar
        mask_winnaar = uitslagen_seizoen[['thuis_1', 'thuis_2', 'uit_1', 'uit_2']].apply(lambda row: winnaar_naam in row.values, axis=1)
        winnaar_matches = uitslagen_seizoen[mask_winnaar]
        winnaar_n_matches = len(winnaar_matches)
        winnaar_goals = 0
        for idx, row in winnaar_matches.iterrows():
            if row['thuis_1'] == winnaar_naam or row['thuis_2'] == winnaar_naam:
                winnaar_goals += row['thuis_score']
            if row['uit_1'] == winnaar_naam or row['uit_2'] == winnaar_naam:
                winnaar_goals += row['uit_score']
        # Aantal ELO-berekeningen in ELO-csv
        robert_elo_count = robert_elo_rows.shape[0]
        winnaar_elo_count = elo_seizoen[elo_seizoen['speler_naam'] == winnaar_naam].shape[0]
    else:
        robert_elo = winnaar_naam = winnaar_elo = None
        winnaar_n_matches = winnaar_goals = robert_elo_count = winnaar_elo_count = None
    robert_stats.append({
        'seizoen': seizoen,
        'matches': n_matches,
        'goals': goals,
        'elo': robert_elo,
        'elo_count': robert_elo_count,
        'winnaar': winnaar_naam,
        'winnaar_elo': winnaar_elo,
        'winnaar_matches': winnaar_n_matches,
        'winnaar_goals': winnaar_goals,
        'winnaar_elo_count': winnaar_elo_count
    })
    print(f"Seizoen {seizoen}:")
    print(f"  Robert (uitslagen-csv): {n_matches} matches, {goals} goals")
    print(f"  Robert (ELO-csv): ELO: {robert_elo}, {robert_elo_count} ELO-berekeningen")
    print(f"  Winnaar (uitslagen-csv): {winnaar_naam}: {winnaar_n_matches} matches, {winnaar_goals} goals")
    print(f"  Winnaar (ELO-csv): {winnaar_naam}: ELO: {winnaar_elo}, {winnaar_elo_count} ELO-berekeningen")

# --- Huidig seizoen: extra top 5 ---
huidig_seizoen = seizoenen[-1]
elo_huidig = elo_df[elo_df['seizoen'] == huidig_seizoen]
laatste_datum = elo_huidig['timestamp'].max()
laatste_elo = elo_huidig[elo_huidig['timestamp'] == laatste_datum]
print(f"=== Top 5 huidig seizoen ({huidig_seizoen}) ===")
top5 = laatste_elo.sort_values('rating', ascending=False).head(5)
for i, row in enumerate(top5.itertuples(), 1):
    print(f"  {i}. {row.speler_naam} ({row.rating:.1f})")

# --- Overzicht alle seizoenen ---
print("\n=== Overzicht seizoenen ===")
for seizoen in seizoenen:
    elo_seizoen = elo_df[elo_df['seizoen'] == seizoen]
    print(f"{seizoen}: {elo_seizoen['speler_naam'].nunique()} spelers, {elo_seizoen['match_id'].nunique()} matches")
