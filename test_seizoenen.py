# test_seizoenen.py
"""
Combineert alle validatie- en debugchecks voor seizoenen, ELO logs en match-tellingen.
"""
import pandas as pd
from firestore_service import get_seasons, get_matches, get_elo_logs
from datetime import datetime

def main():
    print("\n=== SEIZOENENOVERZICHT EN VERGELIJKING ===")
    seasons_df = get_seasons()
    matches_df = get_matches()
    elo_df = get_elo_logs()

    # Forceer alle timestamps naar tz-naive
    for df in [matches_df, elo_df, seasons_df]:
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            try:
                df['timestamp'] = df['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
            except Exception:
                df['timestamp'] = df['timestamp'].dt.tz_localize(None)
        if 'startdatum' in df.columns:
            df['startdatum'] = pd.to_datetime(df['startdatum'], errors='coerce')
            try:
                df['startdatum'] = df['startdatum'].dt.tz_convert('UTC').dt.tz_localize(None)
            except Exception:
                df['startdatum'] = df['startdatum'].dt.tz_localize(None)
        if 'einddatum' in df.columns:
            df['einddatum'] = pd.to_datetime(df['einddatum'], errors='coerce')
            try:
                df['einddatum'] = df['einddatum'].dt.tz_convert('UTC').dt.tz_localize(None)
            except Exception:
                df['einddatum'] = df['einddatum'].dt.tz_localize(None)

    # Controle: aantal wedstrijden per seizoen
    print('\nAANTAL WEDSTRIJDEN PER SEIZOEN:')
    for _, row in seasons_df.iterrows():
        start = row['startdatum']
        end = row['einddatum']
        seizoen_matches = matches_df[(matches_df['timestamp'] >= start) & (matches_df['timestamp'] <= end)]
        print(f"{row['seizoen_naam']}: {len(seizoen_matches)} matches (overzicht: {row['aantal_wedstrijden']})")

    # Controle: ELO logs per seizoen
    print('\nELO LOGS PER SEIZOEN:')
    for _, row in seasons_df.iterrows():
        start = row['startdatum']
        end = row['einddatum']
        seizoen_elo = elo_df[(elo_df['timestamp'] >= start) & (elo_df['timestamp'] <= end)]
        print(f"{row['seizoen_naam']}: {len(seizoen_elo)} elo logs")

    # Controle: elke match heeft 4 ELO logs?
    print('\nMATCHES ZONDER 4 ELO LOGS:')
    elo_counts = elo_df.groupby('match_id').size()
    for match_id, count in elo_counts.items():
        if count != 4:
            print(f"Match {match_id}: {count} elo logs")

    # Controle: seizoenswinnaar in overzicht vs hoogste ELO
    print('\nSEIZOENSWINNAAR CHECK:')
    for _, row in seasons_df.iterrows():
        start = row['startdatum']
        end = row['einddatum']
        seizoen_elo = elo_df[(elo_df['timestamp'] >= start) & (elo_df['timestamp'] <= end)]
        if not seizoen_elo.empty:
            laatste_elo = seizoen_elo.sort_values('timestamp').groupby('speler_naam').last().reset_index()
            winnaar = laatste_elo.sort_values('rating', ascending=False).iloc[0]['speler_naam']
            print(f"{row['seizoen_naam']}: hoogste ELO: {winnaar}")
        else:
            print(f"{row['seizoen_naam']}: geen ELO logs")

    # Extra: Huidig seizoen check (optioneel)
    grens = datetime(2025, 9, 16, 0, 0, 0)
    huidig = matches_df[matches_df['timestamp'] >= grens]
    print(f"\nAantal wedstrijden vanaf 2025-09-16 00:00:00: {len(huidig)}")
    if not huidig.empty:
        print(huidig[['thuis_1','thuis_2','uit_1','uit_2','timestamp']].sort_values('timestamp'))
    else:
        print("Geen wedstrijden gevonden in huidig seizoen.")

if __name__ == "__main__":
    main()
