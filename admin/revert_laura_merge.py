import os
import sys
import pandas as pd
from datetime import datetime

# Voeg de root directory toe aan path voor firestore_service
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import firestore_service as db
from google.cloud.firestore_v1.base_query import FieldFilter

def revert_laura_split():
    print("--- START HERSTEL: LAURA VS LAURATHÖNI ---")
    
    # 1. Herstel speler 'Laura'
    print("   [1/3] Herstellen speler document 'Laura'...")
    laura_exists = list(db.players_ref.where(filter=FieldFilter('speler_naam', '==', 'Laura')).stream())
    if not laura_exists:
        db.add_player('Laura', 1000)
        print("      - Speler 'Laura' opnieuw aangemaakt.")
    else:
        print("      - Speler 'Laura' bestond al (weer).")

    # 2. Lees backup data
    print("   [2/3] Inlezen backup data...")
    csv_elo = pd.read_csv('csv/read/elo.csv')
    csv_elo['timestamp'] = pd.to_datetime(csv_elo['timestamp'], format='mixed', utc=True).dt.tz_localize(None)
    laura_elo_backups = csv_elo[csv_elo['speler_naam'] == 'Laura']
    
    csv_matches = pd.read_csv('csv/read/uitslag.csv')
    csv_matches['timestamp'] = pd.to_datetime(csv_matches['timestamp'], format='mixed', utc=True).dt.tz_localize(None)
    
    # Maak een set van timestamps/IDs die Laura horen te zijn
    laura_match_ids = set(csv_matches[
        (csv_matches['thuis_1'] == 'Laura') | 
        (csv_matches['thuis_2'] == 'Laura') | 
        (csv_matches['uit_1'] == 'Laura') | 
        (csv_matches['uit_2'] == 'Laura')
    ]['match_id'].tolist())

    # 3. Herstel historie in Firestore
    print("   [3/3] Historie terugzetten in Firestore...")
    
    # ELO herstel
    elo_coll = db.db.collection('elo')
    # We zoeken alle records die nu 'LauraThöni' zijn
    current_laurathoni_elo = list(elo_coll.where(filter=FieldFilter('speler_naam', '==', 'LauraThöni')).stream())
    
    reverted_elo = 0
    for doc in current_laurathoni_elo:
        d = doc.to_dict()
        m_id = d.get('match_id')
        # Als deze match_id in de backup bij 'Laura' hoorde, zet hem terug
        if m_id in laura_match_ids or m_id in laura_elo_backups['match_id'].values:
            doc.reference.update({'speler_naam': 'Laura'})
            reverted_elo += 1
            
    print(f"      - {reverted_elo} ELO logs teruggezet naar 'Laura'.")

    # Wedstrijden herstel
    matches_coll = db.db.collection('uitslag')
    reverted_matches = 0
    for m_id in laura_match_ids:
        # Haal het specifieke document op uit Firestore
        # We zoeken op match_id veld
        m_docs = list(matches_coll.where(filter=FieldFilter('match_id', '==', m_id)).stream())
        for doc in m_docs:
            d = doc.to_dict()
            changed = False
            for field in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
                # Als het veld nu 'LauraThöni' is maar in de CSV 'Laura' was
                # We checken de CSV rij voor deze match_id
                csv_row = csv_matches[csv_matches['match_id'] == m_id].iloc[0]
                if d.get(field) == 'LauraThöni' and csv_row.get(field) == 'Laura':
                    d[field] = 'Laura'
                    changed = True
            if changed:
                doc.reference.set(d)
                reverted_matches += 1

    print(f"      - {reverted_matches} wedstrijden teruggezet naar 'Laura'.")
    print("\n✅ Herstel voltooid. Laura en LauraThöni zijn weer gesplitst.")
    db.clear_all_caches()

if __name__ == "__main__":
    revert_laura_split()
