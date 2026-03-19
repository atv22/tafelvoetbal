import os
import sys
import pandas as pd
from datetime import datetime

# Voeg de root directory toe aan path voor firestore_service
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import firestore_service as db
from google.cloud.firestore_v1.base_query import FieldFilter

def execute_merge(old_name, target_name):
    print(f"\n>>> Merging '{old_name}' into '{target_name}'...")
    
    # 1. Check of target bestaat
    target_docs = list(db.players_ref.where(filter=FieldFilter('speler_naam', '==', target_name)).stream())
    if not target_docs:
        print(f"   ⚠️ Waarschuwing: Doelnaam '{target_name}' niet gevonden in Firestore. Maak speler aan...")
        db.add_player(target_name, 1000)
    
    # 2. Definieer de collecties direct via db.db om attribute errors te voorkomen
    # (coll_ref, field_name)
    collections_to_update = [
        (db.db.collection('elo'), 'speler_naam'),
        (db.db.collection('uitslag'), 'thuis_1'),
        (db.db.collection('uitslag'), 'thuis_2'),
        (db.db.collection('uitslag'), 'uit_1'),
        (db.db.collection('uitslag'), 'uit_2'),
        (db.db.collection('beheer_log'), 'admin_naam'),
        (db.db.collection('requests'), 'speler_naam')
    ]
    
    total_updated = 0
    for coll_ref, field in collections_to_update:
        try:
            docs = list(coll_ref.where(filter=FieldFilter(field, '==', old_name)).stream())
            if not docs:
                continue
                
            print(f"   - Updating {len(docs)} docs in '{coll_ref.id}' [{field}]")
            
            for i in range(0, len(docs), 500):
                batch = db.db.batch()
                chunk = docs[i:i+500]
                for doc in chunk:
                    batch.update(doc.reference, {field: target_name})
                batch.commit()
                total_updated += len(chunk)
        except Exception as coll_err:
            print(f"   ⚠️ Kon collectie '{coll_ref.id}' niet updaten: {coll_err}")
    
    # 3. Verwijder oude speler document(en) uit 'spelers' collectie
    try:
        old_player_docs = list(db.db.collection('spelers').where(filter=FieldFilter('speler_naam', '==', old_name)).stream())
        for doc in old_player_docs:
            print(f"   - Verwijderen oude speler doc ID: {doc.id}")
            doc.reference.delete()
    except Exception as del_err:
        print(f"   ⚠️ Kon oude speler documenten niet verwijderen: {del_err}")
        
    print(f"   ✅ Klaar voor deze merge. {total_updated} documenten bijgewerkt.")

def main():
    # Merges gebaseerd op de audit
    merges = [
        ("Fre", "Fré"),
        ("LauraThni", "LauraThöni"),
        ("Stephan", "Stefan")
    ]
    
    print("--- STARTING REQUESTED MERGES IN FIRESTORE ---")
    
    for old, target in merges:
        try:
            execute_merge(old, target)
        except Exception as e:
            print(f"   ❌ Kritieke fout bij merge {old} -> {target}: {e}")
            
    print("\n--- OPSCHONING VOLTOOID ---")
    db.clear_all_caches()

if __name__ == "__main__":
    main()
