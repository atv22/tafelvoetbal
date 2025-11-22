import pandas as pd
from firestore_service import get_matches
from datetime import datetime

def main():
    df = get_matches()
    if df.empty:
        print("Geen wedstrijden gevonden.")
        return
    grens = datetime(2025, 9, 16, 0, 0, 0)
    huidig = df[df['timestamp'] >= grens]
    print(f"Aantal wedstrijden vanaf 2025-09-16 00:00:00: {len(huidig)}")
    if not huidig.empty:
        print(huidig[['thuis_1','thuis_2','uit_1','uit_2','timestamp']].sort_values('timestamp'))
    else:
        print("Geen wedstrijden gevonden in huidig seizoen.")

if __name__ == "__main__":
    main()