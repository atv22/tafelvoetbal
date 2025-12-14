import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
"""
Exporteer de volledige ELO-historie uit Firestore naar een CSV-bestand in ./data
Bestandsnaam: Tafelvoetbal_ELO_Geschiedenis_<datum>.csv
"""
import pandas as pd
from datetime import datetime
from firestore_service import get_elo_logs

def main():
    df = get_elo_logs()
    if df is None or df.empty:
        print("[ERROR] Geen ELO-logs gevonden in Firestore.")
        return
    datum = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"Tafelvoetbal_ELO_Geschiedenis_{datum}.csv"
    df.to_csv(f"data/{fname}", index=False)
    print(f"ELO-historie geëxporteerd naar data/{fname} ({len(df)} regels)")

if __name__ == "__main__":
    main()
