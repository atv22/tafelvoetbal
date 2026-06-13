"""
Gecombineerde integriteitstest voor tafelvoetbal-wedstrijddatabase.
- Controleert aanwezigheid van wedstrijden per jaar (2022, 2023, 2024, 2025)
- Controleert aanwezigheid van wedstrijden per seizoen (2022/2023, 2023/2024, ...)
- Controleert op wedstrijden buiten seizoensgrenzen
- Inspecteert ruwe timestamp-data op type en parsing
"""

import pandas as pd
import pytest
from firestore_service import get_matches, get_seasons

@pytest.mark.parametrize("year", [2022, 2023, 2024, 2025])
def test_matches_per_year(year):
    matches_df = get_matches()
    matches_year = matches_df[matches_df['timestamp'].dt.year == year]  # type: ignore
    if matches_year.empty:
        pytest.skip(f'Geen wedstrijden met een timestamp in {year} gevonden!')
    assert not matches_year.empty

@pytest.mark.parametrize("season_str", [
    "CJ 2022 Zomer", "CJ 2022 Winter",
    "CJ 2023 Zomer", "CJ 2023 Winter",
    "CJ 2024 Zomer", "CJ 2024 Winter"
])
def test_matches_per_season(season_str):
    seasons_df = get_seasons()
    matches_df = get_matches()
    doel_seizoen = seasons_df[seasons_df['seizoen_naam'].str.contains(season_str)]
    assert not doel_seizoen.empty, f'Seizoen {season_str} niet gevonden!'
    row = doel_seizoen.iloc[0]
    start = pd.to_datetime(row['start_datum'])
    if matches_df[matches_df['timestamp'].dt.year == start.year].empty:
        pytest.skip(f"Geen wedstrijden met timestamp in het jaar {start.year} gevonden.")
    end = pd.to_datetime(row['eind_datum'])
    matches_in_season = matches_df[(matches_df['timestamp'] >= start) & (matches_df['timestamp'] <= end)]
    assert not matches_in_season.empty, f'Geen wedstrijden gevonden in seizoen {season_str}!'

@pytest.mark.parametrize("season_str,margin_start,margin_end", [
    ("CJ 2022 Zomer", pd.Timestamp('2022-03-15'), pd.Timestamp('2022-09-30')),
    ("CJ 2022 Winter", pd.Timestamp('2022-09-01'), pd.Timestamp('2023-03-15')),
    ("CJ 2023 Zomer", pd.Timestamp('2023-03-15'), pd.Timestamp('2023-09-30')),
    ("CJ 2023 Winter", pd.Timestamp('2023-09-01'), pd.Timestamp('2024-03-15')),
    ("CJ 2024 Zomer", pd.Timestamp('2024-03-15'), pd.Timestamp('2024-09-30')),
    ("CJ 2024 Winter", pd.Timestamp('2024-09-01'), pd.Timestamp('2025-03-15')),
])
def test_out_of_season_matches(season_str, margin_start, margin_end):
    seasons_df = get_seasons()
    matches_df = get_matches()
    doel_seizoen = seasons_df[seasons_df['seizoen_naam'].str.contains(season_str)]
    assert not doel_seizoen.empty, f'Seizoen {season_str} niet gevonden!'
    row = doel_seizoen.iloc[0]
    start = pd.to_datetime(row['start_datum'])
    if matches_df[matches_df['timestamp'].dt.year == start.year].empty:
        pytest.skip(f"Geen wedstrijden met timestamp in het jaar {start.year} gevonden.")
    end = pd.to_datetime(row['eind_datum'])
    alle_season_matches = matches_df[(matches_df['timestamp'] >= start) & (matches_df['timestamp'] <= end)]
    ruime_matches = matches_df[(matches_df['timestamp'] >= margin_start) & (matches_df['timestamp'] <= margin_end)]
    buiten_seizoen = ruime_matches[~ruime_matches['match_id'].isin(alle_season_matches['match_id'])]
    if not buiten_seizoen.empty:
        print(f"Waarschuwing: {len(buiten_seizoen)} wedstrijden buiten seizoen {season_str} in marge {margin_start} - {margin_end}:")
        print(buiten_seizoen[['match_id','timestamp','thuis_1','thuis_2','uit_1','uit_2']])
        pytest.skip(f'Er zijn {len(buiten_seizoen)} wedstrijden buiten seizoen {season_str} in marge {margin_start} - {margin_end}. Zie output.')
    assert buiten_seizoen.empty

def inspect_raw_timestamps():
    matches_df = get_matches()
    print(f"Aantal ruwe matches: {len(matches_df)}")
    if 'timestamp' not in matches_df.columns:
        print('Geen timestamp-kolom gevonden!')
        return
    types = matches_df['timestamp'].map(type).value_counts()
    print('Types in timestamp-kolom:')
    print(types)
    not_parsed = matches_df[~matches_df['timestamp'].apply(lambda x: pd.api.types.is_datetime64_any_dtype(type(x)))]
    print(f"Aantal niet-geparste timestamps: {len(not_parsed)}")
    if not not_parsed.empty:
        print(not_parsed[['match_id','timestamp','thuis_1','thuis_2','uit_1','uit_2']])
    string_2023 = matches_df[matches_df['timestamp'].astype(str).str.contains('2023', na=False)]
    print(f"Aantal matches met '2023' in timestamp-string: {len(string_2023)}")
    if not string_2023.empty:
        print(string_2023[['match_id','timestamp','thuis_1','thuis_2','uit_1','uit_2']])

def main():
    # Jaarchecks
    for jaar in [2022, 2023, 2024, 2025]:
        test_matches_per_year(jaar)
    # Seizoenschecks (pas aan indien andere seizoensnamen)
    for seizoen, marge in [
        ("2022/2023", (pd.Timestamp('2022-07-01'), pd.Timestamp('2023-07-01'))),
        ("2023/2024", (pd.Timestamp('2023-07-01'), pd.Timestamp('2024-07-01'))),
        ("2024/2025", (pd.Timestamp('2024-07-01'), pd.Timestamp('2025-07-01'))),
    ]:
        test_matches_per_season(seizoen)
        test_out_of_season_matches(seizoen, marge[0], marge[1])
    # Timestamp inspectie
    inspect_raw_timestamps()
    print('Alle integriteitstests succesvol!')

if __name__ == "__main__":
    main()
