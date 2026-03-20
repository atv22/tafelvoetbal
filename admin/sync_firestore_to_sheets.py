import sys
import os
import pandas as pd
import gspread
from google.oauth2 import service_account
import streamlit as st

# Voeg de root-map toe aan sys.path om firestore_service te kunnen importeren
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import firestore_service as db_service

# Google Sheet ID van de gebruiker
SHEET_ID = "1cCiNoYfro9SqS8qIjEKT8prsAvAA7wowvhzhh2ljHnA"

# Scopes nodig voor Google Sheets en Drive
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def get_creds():
    """Haal Google credentials op via st.secrets of lokaal bestand."""
    # Probeer Streamlit secrets eerst (voor Streamlit Cloud)
    try:
        if "firestore_credentials" in st.secrets:
            key_dict = dict(st.secrets["firestore_credentials"])
            return service_account.Credentials.from_service_account_info(key_dict, scopes=SCOPES)
    except Exception:
        pass
    
    # Fallback naar lokaal bestand (voor lokale dev)
    key_path = os.path.join(ROOT, "firestore-key.json")
    if os.path.exists(key_path):
        return service_account.Credentials.from_service_account_file(key_path, scopes=SCOPES)
    
    raise FileNotFoundError("Geen Google credentials gevonden in st.secrets of firestore-key.json")

def sync_to_sheets():
    print("Start synchronisatie Firestore -> Google Sheets...")
    
    try:
        creds = get_creds()
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)
    except Exception as e:
        import traceback
        print(f"Fout bij verbinden met Google Sheets: {e}")
        traceback.print_exc()
        print("\nBELANGRIJK: Zorg ervoor dat het service account e-mailadres Editor rechten heeft op de sheet.")
        print(f"Sheet link: https://docs.google.com/spreadsheets/d/{SHEET_ID}")
        return

    # Mappings: (Sheet Naam, Firestore functie)
    mappings = [
        ("Spelers", db_service.get_players),
        ("Wedstrijden", db_service.get_matches),
        ("ELO_Logs", db_service.get_elo_logs),
        ("Verzoeken", db_service.get_requests),
        ("Beheer_Log", db_service.get_beheer_log)
    ]

    for sheet_name, fetch_func in mappings:
        print(f"\nSynchroniseren van {sheet_name}...")
        try:
            df = fetch_func()
            if df is None or (hasattr(df, 'empty') and df.empty):
                print(f"Geen data gevonden voor {sheet_name}, overslaan.")
                continue
            
            # Timestamp conversie naar string voor Sheets (voorkomt JSON serialisatie errors)
            df = df.copy()
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Zorg dat de worksheet bestaat
            try:
                worksheet = sh.worksheet(sheet_name)
            except gspread.exceptions.WorksheetNotFound:
                worksheet = sh.add_worksheet(title=sheet_name, rows="100", cols="20")
                print(f"Nieuw tabblad '{sheet_name}' aangemaakt.")
            
            # Leegmaken
            worksheet.clear()
            
            # Dataframe naar lijst van lijsten (inclusief header)
            # We vullen NaNs met lege strings
            data = [df.columns.values.tolist()] + df.fillna('').values.tolist()
            
            # Update de sheet
            worksheet.update('A1', data)
            print(f"Succesvol {len(df)} rijen gesynchroniseerd naar '{sheet_name}'.")
            
        except Exception as e:
            print(f"Fout bij synchroniseren van {sheet_name}: {e}")

    print("\nSynchronisatie voltooid.")

if __name__ == "__main__":
    sync_to_sheets()
