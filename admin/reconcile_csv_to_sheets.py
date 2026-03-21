import sys
import os
import pandas as pd
import gspread
from google.oauth2 import service_account
import streamlit as st

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import firestore_service as db_service

DEFAULT_SHEET_ID = "1cCiNoYfro9SqS8qIjEKT8prsAvAA7wowvhzhh2ljHnA"
SHEET_ID = os.environ.get("GSHEET_ID", DEFAULT_SHEET_ID)
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
CSV_DIR = os.path.join(ROOT, 'csv', 'read')

def get_creds():
    try:
        if "firestore_credentials" in st.secrets:
            return service_account.Credentials.from_service_account_info(dict(st.secrets["firestore_credentials"]), scopes=SCOPES)
    except: pass
    key_path = os.path.join(ROOT, "firestore-key.json")
    if os.path.exists(key_path):
        return service_account.Credentials.from_service_account_file(key_path, scopes=SCOPES)
    raise FileNotFoundError("Credentials niet gevonden.")

def reconcile():
    print("Reconciling CSV data with Google Sheets/Firestore...")
    creds = get_creds()
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)

    # Mappings: (Sheet Naam, Firestore Functie, CSV Bestandsnaam, Identificatie Kolommen)
    mappings = [
        ("Spelers", db_service.get_players, "spelers.csv", ["speler_naam"]),
        ("Wedstrijden", db_service.get_matches, "uitslag.csv", ["timestamp", "thuis_1", "uit_1"]),
        ("ELO_Logs", db_service.get_elo_logs, "elo.csv", ["timestamp", "speler_naam"]),
        ("Verzoeken", db_service.get_requests, "requests.csv", ["Timestamp", "Verzoek"])
    ]

    for sheet_name, fetch_func, csv_name, id_cols in mappings:
        print(f"\nVerwerken van {sheet_name}...")
        
        # 1. Haal Firestore data op
        try:
            df_fs = fetch_func()
        except Exception as e:
            print(f"Firestore error voor {sheet_name}: {e}")
            df_fs = pd.DataFrame()

        # 2. Haal CSV data op
        csv_path = os.path.join(CSV_DIR, csv_name)
        if not os.path.exists(csv_path):
            print(f"Geen CSV gevonden voor {csv_name}")
            df_csv = pd.DataFrame()
        else:
            df_csv = pd.read_csv(csv_path)
            # Timestamp normalisatie
            for col in df_csv.columns:
                if 'timestamp' in col.lower():
                    df_csv[col] = pd.to_datetime(df_csv[col], errors='coerce')

        # 3. Mergen en ontdubbelen
        if df_fs is None: df_fs = pd.DataFrame()
        
        combined = pd.concat([df_fs, df_csv], ignore_index=True)
        
        if not combined.empty:
            # Drop duplicates gebaseerd op ID kolommen (indien aanwezig in data)
            actual_id_cols = [c for c in id_cols if c in combined.columns]
            if actual_id_cols:
                # Normaliseer ID kolommen voor vergelijking
                temp_combined = combined.copy()
                for c in actual_id_cols:
                    if pd.api.types.is_datetime64_any_dtype(temp_combined[c]):
                        temp_combined[c] = temp_combined[c].dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # Bepaal welke rijen we houden (prioriteit aan Firestore/nieuwste)
                combined = combined.loc[temp_combined.drop_duplicates(subset=actual_id_cols, keep='first').index]

            print(f"Dataset resultaat: {len(combined)} rijen (Firestore: {len(df_fs)}, CSV: {len(df_csv)})")
            
            # 4. Push naar Google Sheets
            try:
                # Timestamp conversie naar string voor Sheets
                df_to_push = combined.copy()
                for col in df_to_push.columns:
                    if pd.api.types.is_datetime64_any_dtype(df_to_push[col]):
                        df_to_push[col] = df_to_push[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                
                try:
                    worksheet = sh.worksheet(sheet_name)
                except gspread.exceptions.WorksheetNotFound:
                    worksheet = sh.add_worksheet(title=sheet_name, rows="100", cols="20")
                
                worksheet.clear()
                data = [df_to_push.columns.values.tolist()] + df_to_push.fillna('').values.tolist()
                worksheet.update('A1', data)
                print(f"Succesvol {len(df_to_push)} rijen gepusht naar {sheet_name}")
            except Exception as e:
                print(f"Fout bij pushen naar {sheet_name}: {e}")
        else:
            print(f"Geen data om te verwerken voor {sheet_name}")

if __name__ == "__main__":
    reconcile()
