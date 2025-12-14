import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
"""
Exporteer de volledige uitslagen (wedstrijden) uit Firestore naar een CSV-bestand in ./data
Bestandsnaam: Tafelvoetbal_Uitslagen_Export_<datum>.csv
"""
import pandas as pd
from datetime import datetime
from firestore_service import get_matches

def main():
    df = get_matches()
    if df is None or df.empty:
        print("[ERROR] Geen wedstrijden gevonden in Firestore.")
        return
    datum = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"Tafelvoetbal_Uitslagen_Export_{datum}.csv"
    df.to_csv(f"data/{fname}", index=False)
    print(f"Wedstrijden geëxporteerd naar data/{fname} ({len(df)} regels)")

if __name__ == "__main__":
    main()
