"""
Admin script om spelers samen te voegen (merge) en namen te corrigeren in de gehele Firestore database.
Handig voor het oplossen van dubbele spelers of namen met encoding fouten.
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Voeg de root directory toe aan path voor firestore_service
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import firestore_service as db
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

def get_all_players():
    docs = db.players_ref.stream()
    players = []
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id
        players.append(d)
    return pd.DataFrame(players).sort_values('speler_naam')

def merge_players(old_names, target_name):
    """
    Merge alle data van old_names naar target_name.
    """
    print(f"\n--- Start merge van {old_names} naar '{target_name}' ---")
    
    # 1. Controleer of target_name bestaat
    target_docs = list(db.players_ref.where(filter=FieldFilter('speler_naam', '==', target_name)).stream())
    if not target_docs:
        print(f"Fout: Doelnaam '{target_name}' niet gevonden in de database. Maak deze eerst aan of controleer spelling.")
        return
    
    target_ref = target_docs[0].reference
    
    # 2. Update Collecties
    collections_to_update = [
        (db.elo_ref, 'speler_naam'),
        (db.matches_ref, 'thuis_1'),
        (db.matches_ref, 'thuis_2'),
        (db.matches_ref, 'uit_1'),
        (db.matches_ref, 'uit_2'),
        (db.beheer_ref, 'admin_naam'),
        (db.requests_ref, 'speler_naam')
    ]
    
    for old_name in old_names:
        if old_name == target_name:
            continue
            
        print(f"\nVerwerken van '{old_name}'...")
        
        for coll_ref, field in collections_to_update:
            docs = list(coll_ref.where(filter=FieldFilter(field, '==', old_name)).stream())
            if not docs:
                continue
                
            print(f"  Updating {len(docs)} documenten in '{coll_ref.id}' (veld: {field})...")
            
            # Firestore batch limiet is 500
            for i in range(0, len(docs), 500):
                batch = db.db.batch()
                chunk = docs[i:i+500]
                for doc in chunk:
                    batch.update(doc.reference, {field: target_name})
                batch.commit()
        
        # 3. Verwijder de oude speler documenten
        old_player_docs = list(db.players_ref.where(filter=FieldFilter('speler_naam', '==', old_name)).stream())
        for doc in old_player_docs:
            print(f"  Verwijderen van speler document ID: {doc.id}")
            doc.reference.delete()
            
    print(f"\n✅ Merge voltooid! '{target_name}' heeft nu alle historie van {old_names}.")
    db.clear_all_caches()

def main():
    print("Haal spelerslijst op...")
    players_df = get_all_players()
    
    if players_df.empty:
        print("Geen spelers gevonden.")
        return
        
    print("\n--- Geregistreerde Spelers ---")
    for i, row in enumerate(players_df.itertuples(), 1):
        print(f"{i:3}. {row.speler_naam:25} (Rating: {int(row.rating)})")
        
    print("\nInstructies:")
    print("Voer de NUMMERS in van de spelers die je wilt MERGEN (bijv: 5, 8).")
    print("Voer daarna de naam in van de speler die de HOOFDNAAM moet worden.")
    
    try:
        input_indices = input("\nNummers van te mergen spelers (komma-gescheiden): ")
        indices = [int(x.strip()) - 1 for x in input_indices.split(',')]
        
        old_names = [players_df.iloc[i].speler_naam for i in indices]
        print(f"Geselecteerd voor merge: {old_names}")
        
        target_name = input("Wat is de correcte doelnaam? (moet exact overeenkomen): ").strip()
        
        bevestig = input(f"Weet je zeker dat je {old_names} wilt mergen naar '{target_name}'? (ja/nee): ")
        if bevestig.lower() == 'ja':
            merge_players(old_names, target_name)
        else:
            print("Geannuleerd.")
            
    except Exception as e:
        print(f"Fout: {e}")

if __name__ == "__main__":
    main()
