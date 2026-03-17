import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
"""
Lokaal ELO-herbereken-script op basis van uitslagen-CSV.
- Leest uitslagen uit data/Tafelvoetbal_Uitslagen_*.csv
- Berekent ELO-geschiedenis per speler, per wedstrijd, met seizoensreset (1000 bij elk nieuw seizoen)
- Schrijft resultaat naar data/ELO_Herberekend_<datum>.csv
- Geen Firestore nodig, puur lokaal/debug
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
from datetime import datetime, timedelta
from utils.utils_new_elo import calculate_new_elo

def get_prinsjesdag(year):
    september = datetime(year, 9, 1)
    weekday = september.weekday()
    first_tuesday = september + timedelta(days=(1 - weekday) % 7)
    prinsjesdag = first_tuesday + timedelta(days=14)
    return prinsjesdag.replace(hour=0, minute=0, second=0, microsecond=0)


def get_march15(year):
    return datetime(year, 3, 15, 23, 59, 59)


def get_march16(year):
    return datetime(year, 3, 16, 0, 0, 0)


def bepaal_seizoenen(df):
    jaren = sorted(set(df['timestamp'].dt.year))
    bounds = [get_prinsjesdag(y) for y in range(min(jaren)-1, max(jaren)+2)]
    bounds = sorted(bounds)
    seizoenen = []
    for year in range(min(jaren) - 1, max(jaren) + 1):
        prinsjesdag = get_prinsjesdag(year)
        next_prinsjesdag = get_prinsjesdag(year + 1)

        # Seizoen 1: Prinsjesdag tot 15 maart (inclusief)
        season1_start = prinsjesdag
        season1_end = get_march15(year + 1)
        mask1 = (df['timestamp'] >= season1_start) & (df['timestamp'] <= season1_end)
        if mask1.sum() > 0:
            seizoenen.append({'start': season1_start, 'end': season1_end})

        # Seizoen 2: 16 maart tot Prinsjesdag
        season2_start = get_march16(year + 1)
        season2_end = next_prinsjesdag.replace(hour=23, minute=59, second=59, microsecond=0)
        mask2 = (df['timestamp'] >= season2_start) & (df['timestamp'] <= season2_end)
        if mask2.sum() > 0:
            seizoenen.append({'start': season2_start, 'end': season2_end})
    return seizoenen

def main():
    # Zoek laatste uitslagenbestand
    data_dir = 'data'
    files = [f for f in os.listdir(data_dir) if f.startswith('Tafelvoetbal_Uitslagen_') and f.endswith('.csv')]
    if not files:
        print('Geen uitslagenbestand gevonden in ./data')
        return
    latest = sorted(files)[-1]
    df = pd.read_csv(os.path.join(data_dir, latest))
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    seizoenen = bepaal_seizoenen(df)
    print(f"{len(seizoenen)} seizoenen gevonden:")
    for i, s in enumerate(seizoenen):
        print(f"  {i+1}: {s['start'].date()} t/m {s['end'].date()}")
    # ELO-logica
    elo_history = []
    player_elos = {}
    for seizoen in seizoenen:
        # Reset alle spelers naar 1000 bij seizoensstart
        spelers_in_seizoen = set(df[(df['timestamp'] >= seizoen['start']) & (df['timestamp'] <= seizoen['end'])][['thuis_1','thuis_2','uit_1','uit_2']].values.flatten())
        for speler in spelers_in_seizoen:
            if pd.isna(speler): continue
            player_elos[speler] = 1000
        # Doorloop alle wedstrijden in seizoen
        matches = df[(df['timestamp'] >= seizoen['start']) & (df['timestamp'] <= seizoen['end'])]
        for _, row in matches.iterrows():
            match_dict = {
                'Thuis_1': row['thuis_1'],
                'Thuis_2': row['thuis_2'],
                'Uit_1': row['uit_1'],
                'Uit_2': row['uit_2'],
                'Thuis_score': int(row['thuis_score']),
                'Uit_score': int(row['uit_score']),
                'klinkers_thuis_1': int(row.get('klinkers_thuis_1', 0)) if pd.notna(row.get('klinkers_thuis_1', 0)) else 0,
                'klinkers_thuis_2': int(row.get('klinkers_thuis_2', 0)) if pd.notna(row.get('klinkers_thuis_2', 0)) else 0,
                'klinkers_uit_1': int(row.get('klinkers_uit_1', 0)) if pd.notna(row.get('klinkers_uit_1', 0)) else 0,
                'klinkers_uit_2': int(row.get('klinkers_uit_2', 0)) if pd.notna(row.get('klinkers_uit_2', 0)) else 0
            }
            # ELO input
            all_ELO_ratings = {p: [player_elos.get(p, 1000)] for p in [row['thuis_1'], row['thuis_2'], row['uit_1'], row['uit_2']]}
            new_elo_df = calculate_new_elo(match_dict, all_ELO_ratings)
            for _, r in new_elo_df.iterrows():
                speler = r['Speler']
                player_elos[speler] = r['ELO']
                elo_history.append({
                    'match_id': row['match_id'],
                    'speler_naam': speler,
                    'timestamp': row['timestamp'],
                    'rating': r['ELO']
                })

    # Controle: geen enkele match_id mag meer dan 4 ELO entries hebben
    elo_df = pd.DataFrame(elo_history)
    counts = elo_df['match_id'].value_counts()
    fouten = counts[counts > 4]
    if not fouten.empty:
        print("[WAARSCHUWING] De volgende match_id's hebben meer dan 4 ELO entries:")
        for mid, cnt in fouten.items():
            print(f"  match_id {mid}: {cnt} entries")
    else:
        print("[CHECK] Alle match_id's hebben maximaal 4 ELO entries.")

    # Schrijf naar CSV
    outname = f"ELO_Herberekend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    outpath = os.path.join(data_dir, outname)
    elo_df.to_csv(outpath, index=False)
    print(f"Geschiedenis opgeslagen als {outpath}")

if __name__ == "__main__":
    main()
