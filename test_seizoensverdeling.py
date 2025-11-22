import pandas as pd
from firestore_service import get_matches, get_seasons

def test_season_distribution():
    seasons_df = get_seasons()
    if seasons_df.empty:
        print("Geen seizoenen-data om te tonen.")
        return

    print("\nVolledige seizoenen-DataFrame uit get_seasons():")
    print(seasons_df)
    print("\nTelling per seizoen (volgens get_seasons()):")
    for _, season in seasons_df.iterrows():
        print(f"{season['seizoen_naam']}: {season['aantal_wedstrijden']} wedstrijden, {season['startdatum']} t/m {season['einddatum']}")

if __name__ == "__main__":
    test_season_distribution()
