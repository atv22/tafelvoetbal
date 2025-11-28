"""
Script: admin/elo_push_to_firestore.py

- Verwijdert eerst alle bestaande ELO-geschiedenis uit Firestore (collectie 'elo')
- Laadt de meest recente ELO_Herberekend_*.csv
- Pusht alle ELO-regels naar Firestore (één document per regel, met match_id, speler_naam, timestamp, rating)

Let op: vereist geldige Firestore credentials (firestore-key.json) en google-cloud-firestore package.
"""
import os
import pandas as pd
from google.cloud import firestore
import json

DATA_DIR = 'data'
ELO_PATTERN = 'ELO_Herberekend_'
CREDENTIALS = 'firestore-key.json'

# --- Firestore setup ---
def get_firestore_client():
    return firestore.Client.from_service_account_json(CREDENTIALS)

def main():
    # Vind laatste ELO-csv
    files = [f for f in os.listdir(DATA_DIR) if f.startswith(ELO_PATTERN) and f.endswith('.csv')]
    if not files:
        print('Geen ELO_Herberekend_*.csv gevonden in ./data')
        return
    latest = sorted(files)[-1]
    df = pd.read_csv(os.path.join(DATA_DIR, latest))
    print(f"Push naar Firestore van bestand: {latest} ({len(df)} regels)")
    # Firestore connectie
    db = get_firestore_client()
    elo_ref = db.collection('elo')
    # Oude ELO-geschiedenis verwijderen
    print("Verwijderen oude ELO-geschiedenis uit Firestore...")
    batch = db.batch()
    docs = elo_ref.stream()
    count = 0
    for doc in docs:
        batch.delete(doc.reference)
        count += 1
        if count % 400 == 0:
            batch.commit()
            batch = db.batch()
    batch.commit()
    print(f"Verwijderd: {count} documenten.")
    # Nieuwe ELO pushen
    print("Pushen nieuwe ELO-geschiedenis...")
    batch = db.batch()
    for i, (_, row) in enumerate(df.iterrows(), 1):
        doc_ref = elo_ref.document()
        data = {
            'match_id': row['match_id'],
            'speler_naam': row['speler_naam'],
            'timestamp': str(row['timestamp']),
            'rating': float(row['rating'])
        }
        batch.set(doc_ref, data)
        if i % 400 == 0:
            batch.commit()
            batch = db.batch()
            print(f"  {i} regels gepusht...")
    batch.commit()
    print(f"Klaar! Totaal {len(df)} regels gepusht.")

if __name__ == "__main__":
    main()
