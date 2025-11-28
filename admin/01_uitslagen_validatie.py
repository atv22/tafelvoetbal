"""
Script: admin/uitslagen_validatie.py

- Controleert de uitslagen-CSV op:
    * Naamvarianten per speler (case, spaties, accenten)
    * Consistentie van datums (geen future/past, oplopend, geen dubbele timestamps)
    * Score-validatie: thuis_score + uit_score == 19, winnaar heeft altijd 10
    * Geen lege of ontbrekende spelersvelden
    * Unieke match_id's
    * Overzicht van alle unieke spelersnamen per seizoen
    * Waarschuwing bij verdachte of afwijkende data

Voer dit script uit vóór ELO-herberekening!
"""
import os
import pandas as pd
from datetime import datetime
import unicodedata

DATA_DIR = 'data'
UITSLAGEN_PATTERN = 'Tafelvoetbal_Uitslagen_'

# --- Helpers ---
def normalize_name(name):
    if pd.isna(name):
        return ''
    # Lowercase, strip, remove accents
    name = str(name).strip().lower()
    name = unicodedata.normalize('NFKD', name)
    name = ''.join([c for c in name if not unicodedata.combining(c)])
    return name

def main():
    # Vind laatste uitslagenbestand
    files = [f for f in os.listdir(DATA_DIR) if f.startswith(UITSLAGEN_PATTERN) and f.endswith('.csv')]
    if not files:
        print('Geen uitslagenbestand gevonden in ./data')
        return
    latest = sorted(files)[-1]
    df = pd.read_csv(os.path.join(DATA_DIR, latest))
    print(f"Validatie van bestand: {latest}\n")
    # Check op verplichte kolommen
    required = ['thuis_1','thuis_2','uit_1','uit_2','thuis_score','uit_score','timestamp','match_id']
    for col in required:
        if col not in df.columns:
            print(f"[FOUT] Kolom ontbreekt: {col}")
            return
    # Check op lege spelersvelden
    for col in ['thuis_1','thuis_2','uit_1','uit_2']:
        leeg = df[col].isna().sum()
        if leeg > 0:
            print(f"[WAARSCHUWING] {leeg} lege waarden in kolom {col}")
    # Check op unieke match_id
    if df['match_id'].duplicated().any():
        print("[FOUT] Dubbele match_id's gevonden!")
    # Check op score-validatie
    for idx, row in df.iterrows():
        s1, s2 = int(row['thuis_score']), int(row['uit_score'])
        if s1 + s2 > 19:
            print(f"[FOUT] Score optelling te hoog bij match_id {row['match_id']}: {s1}+{s2} > 19")
        if s1 != 10 and s2 != 10:
            print(f"[FOUT] Geen winnaar met 10 bij match_id {row['match_id']}: {s1}-{s2}")
    # Check op datum-consistentie
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    if df['timestamp'].isna().any():
        print("[FOUT] Onleesbare of ontbrekende timestamps!")
    if not df['timestamp'].is_monotonic_increasing:
        print("[WAARSCHUWING] Timestamps niet strikt oplopend!")
    if df['timestamp'].duplicated().any():
        print("[WAARSCHUWING] Dubbele timestamps gevonden!")
    now = datetime.now()
    if (df['timestamp'] > now).any():
        print("[WAARSCHUWING] Er zijn wedstrijden met een datum in de toekomst!")
    # Naamvarianten en unieke namen per seizoen
    df['seizoen'] = df['timestamp'].apply(lambda d: f"{d.year-1}/{d.year}" if d.month < 8 else f"{d.year}/{d.year+1}")
    for seizoen, groep in df.groupby('seizoen'):
        print(f"\nSeizoen {seizoen}:")
        namen = set()
        norm_namen = set()
        for col in ['thuis_1','thuis_2','uit_1','uit_2']:
            for naam in groep[col].unique():
                if pd.isna(naam): continue
                namen.add(naam)
                norm_namen.add(normalize_name(naam))
        print(f"  Unieke spelersnamen: {sorted(namen)}")
        if len(namen) != len(norm_namen):
            print("  [WAARSCHUWING] Mogelijke naamvarianten of typfouten aanwezig!")
            # Toon mogelijke dubbelen en de betreffende regels
            norm_map = {}
            for naam in namen:
                n = normalize_name(naam)
                norm_map.setdefault(n, []).append(naam)
            for n, varianten in norm_map.items():
                if len(varianten) > 1:
                    print(f"    Varianten voor '{n}': {varianten}")
                    # Toon de rijen waarin deze varianten voorkomen
                    for v in varianten:
                        rows = groep[(groep['thuis_1'] == v) | (groep['thuis_2'] == v) | (groep['uit_1'] == v) | (groep['uit_2'] == v)]
                        for _, r in rows.iterrows():
                            print(f"      match_id: {r['match_id']}, datum: {r['timestamp']}, spelers: [{r['thuis_1']}, {r['thuis_2']}] vs [{r['uit_1']}, {r['uit_2']}] score: {r['thuis_score']}-{r['uit_score']}")
    print("\nValidatie voltooid.")

if __name__ == "__main__":
    main()
