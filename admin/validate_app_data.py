import os
import sys
import pandas as pd
import json

# Voeg root toe aan path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import firestore_service as db
import streamlit as st

def validate_app_data():
    print("=== App Data Validatie Start ===")
    
    # Forceer offline mode om GSheet fallback te testen
    print("\n1. Testen van GSheet Fallback (forceer offline)...")
    db.set_offline_mode(True)
    
    try:
        print("\n--- Spelers ---")
        p = db.get_players()
        print(f"Aantal spelers: {len(p)}")
        if not p.empty:
            print(f"Kolommen: {p.columns.tolist()}")
            print(f"Eerste speler: {p['speler_naam'].iloc[0]} (Rating: {p['rating'].iloc[0]})")
        
        print("\n--- Wedstrijden ---")
        m = db.get_matches()
        print(f"Aantal wedstrijden: {len(m)}")
        if not m.empty:
            print(f"Kolommen: {m.columns.tolist()}")
            print(f"Type timestamp: {type(m['timestamp'].iloc[0])}")
            print(f"Laatste wedstrijd: {m['timestamp'].iloc[0]}")

        print("\n--- ELO Logs ---")
        e = db.get_elo_logs()
        print(f"Aantal ELO logs: {len(e)}")
        if not e.empty:
            print(f"Kolommen: {e.columns.tolist()}")

        print("\n--- Seizoenen ---")
        s = db.get_seasons()
        print(f"Aantal seizoenen: {len(s)}")
        if not s.empty:
            print(f"Huidig seizoen: {s['seizoen_naam'].iloc[-1]}")

    except Exception as ex:
        print(f"\nCRITICAL ERROR tijdens validatie: {ex}")
        import traceback
        traceback.print_exc()

    print("\n=== App Data Validatie Eind ===")

if __name__ == "__main__":
    validate_app_data()
