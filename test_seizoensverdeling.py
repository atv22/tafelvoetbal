import pandas as pd
from firestore_service import get_matches, get_seasons

def test_season_distribution():
    matches_df = get_matches()
    seasons_df = get_seasons()
    if matches_df.empty or seasons_df.empty:
        print("Geen data om te testen.")
        return

    # Zorg dat timestamp kolom datetime is
    matches_df['timestamp'] = pd.to_datetime(matches_df['timestamp'], errors='coerce')
    errors = []
    for _, season in seasons_df.iterrows():
        start = pd.to_datetime(season['startdatum'])
        end = pd.to_datetime(season['einddatum'])
        seizoen_naam = season.get('seizoen_naam', f"{start.year}/{end.year}")
        # Filter alle wedstrijden in dit seizoen
        season_matches = matches_df[(matches_df['timestamp'] >= start) & (matches_df['timestamp'] <= end)]
        n_reported = season['aantal_wedstrijden']
        n_actual = len(season_matches)
        print(f"{seizoen_naam}: {n_actual} wedstrijden (volgens seizoenen tabel: {n_reported})")
        if n_actual != n_reported:
            errors.append(f"Mismatch in {seizoen_naam}: verwacht {n_actual}, tabel zegt {n_reported}")
    if errors:
        print("\nFouten gevonden:")
        for err in errors:
            print("-", err)
    else:
        print("Alle seizoenen correct verdeeld!")

if __name__ == "__main__":
    test_season_distribution()
