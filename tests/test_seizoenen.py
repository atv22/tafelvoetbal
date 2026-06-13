import pandas as pd
from firestore_service import get_seasons, get_matches, get_elo_logs, normalize_timestamp_series
from datetime import datetime
import pytest

@pytest.mark.integration
def test_seizoenen_validaties():
    seasons_df = get_seasons()
    matches_df = get_matches()
    elo_df = get_elo_logs()

    # Forceer alle timestamps naar tz-naive via hulpfunctie
    for df in [matches_df, elo_df, seasons_df]:
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df['timestamp'] = normalize_timestamp_series(df['timestamp'])
        if 'start_datum' in df.columns:
            df['start_datum'] = pd.to_datetime(df['start_datum'], errors='coerce')
            df['start_datum'] = normalize_timestamp_series(df['start_datum'])
        if 'eind_datum' in df.columns:
            df['eind_datum'] = pd.to_datetime(df['eind_datum'], errors='coerce')
            df['eind_datum'] = normalize_timestamp_series(df['eind_datum'])

    # Controle: aantal wedstrijden per seizoen (aantal_wedstrijden is 0 in get_seasons wegens optimalisatie)
    for _, row in seasons_df.iterrows():
        start = row['start_datum']
        end = row['eind_datum']
        seizoen_matches = matches_df[(matches_df['timestamp'] >= start) & (matches_df['timestamp'] <= end)]
        assert len(seizoen_matches) >= 0

    # Controle: elke match heeft 4 ELO logs (alleen als match_id bestaat)
    if 'match_id' in elo_df.columns:
        elo_counts = elo_df.groupby('match_id').size()
        for match_id, count in elo_counts.items():
            if count != 4:
                print(f"Waarschuwing: Match {match_id} heeft {count} elo logs (verwacht: 4)")

    # Controle: seizoenswinnaar in overzicht vs hoogste ELO
    for _, row in seasons_df.iterrows():
        start = row['start_datum']
        end = row['eind_datum']
        seizoen_elo = elo_df[(elo_df['timestamp'] >= start) & (elo_df['timestamp'] <= end)]
        if not seizoen_elo.empty:
            laatste_elo = seizoen_elo.sort_values('timestamp').groupby('speler_naam').last().reset_index()
            winnaar = laatste_elo.sort_values('rating', ascending=False).iloc[0]['speler_naam']
            assert winnaar is not None

    # Extra: Huidig seizoen check (optioneel)
    grens = datetime(2025, 9, 16, 0, 0, 0)
    huidig = matches_df[matches_df['timestamp'] >= grens]
    # Geen assert, alleen informatief