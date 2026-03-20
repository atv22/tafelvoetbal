import gspread
from google.oauth2 import service_account
import pandas as pd
import json
import os
import streamlit as st

SHEET_ID = "1cCiNoYfro9SqS8qIjEKT8prsAvAA7wowvhzhh2ljHnA"
GS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

def debug_sheet():
    print(f"--- Debugging Google Sheet: {SHEET_ID} ---")
    try:
        # Credentials laden
        if os.path.exists("firestore-key.json"):
            creds = service_account.Credentials.from_service_account_file("firestore-key.json", scopes=GS_SCOPES)
            print("Geladen via firestore-key.json")
        else:
            print("Lokaal bestand niet gevonden, debuggen via secrets niet mogelijk in bare script.")
            return

        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)
        
        for name in ["Spelers", "Wedstrijden", "ELO_Logs"]:
            print(f"\nTabblad: {name}")
            try:
                ws = sh.worksheet(name)
                values = ws.get_all_values()
                if not values:
                    print("  [!] Tabblad is leeg.")
                    continue
                
                print(f"  Header: {values[0]}")
                print(f"  Aantal rijen: {len(values) - 1}")
                if len(values) > 1:
                    print(f"  Eerste data rij: {values[1]}")
                
                df = pd.DataFrame(values[1:], columns=values[0])
                print(f"  DataFrame shape: {df.shape}")
                print(f"  Kolommen in DF: {df.columns.tolist()}")
                
            except Exception as e:
                print(f"  [!] Fout bij tabblad {name}: {e}")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    debug_sheet()
