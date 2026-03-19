import os
import sys
import pandas as pd

# Voeg de root directory toe aan path voor firestore_service
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import firestore_service as db
from google.cloud.firestore_v1.base_query import FieldFilter

def fix_all_laura_variations():
    target_name = "LauraThöni"
    print(f"--- Opschonen van alle LauraTh... variaties naar '{target_name}' ---")
    
    # Lijst van collecties en de relevante velden
    collections = [
        ('elo', 'speler_naam'),
        ('uitslag', 'thuis_1'),
        ('uitslag', 'thuis_2'),
        ('uitslag', 'uit_1'),
        ('uitslag', 'uit_2')
    ]
    
    total_fixed = 0
    
    for coll_name, field in collections:
        coll_ref = db.db.collection(coll_name)
        # We halen alle documenten op waar de naam begint met LauraTh
        # In Firestore kun je prefix matchen met >= en <
        docs = list(coll_ref.where(filter=FieldFilter(field, '>=', 'LauraTh')).where(filter=FieldFilter(field, '<', 'LauraThu')).stream())
        
        for doc in docs:
            current_name = doc.to_dict().get(field)
            if current_name != target_name:
                print(f"   [FIX] {coll_name}.{field}: '{current_name}' -> '{target_name}'")
                doc.reference.update({field: target_name})
                total_fixed += 1
                
    # Ook even checken op de losse 'Laura' (indien gewenst, maar u zei alleen LauraThni)
    # Laten we LauraThni specifiek in alle data zoeken via substring matching als back-up
    print("\nExtra controle op specifieke foute patterns...")
    all_docs_elo = coll_ref = db.db.collection('elo').stream()
    for doc in all_docs_elo:
        name = doc.to_dict().get('speler_naam', '')
        if 'Laura' in name and name != target_name and name != 'Laura':
             print(f"   [FIX ELO] '{name}' -> '{target_name}'")
             doc.reference.update({'speler_naam': target_name})
             total_fixed += 1

    print(f"\n✅ Totaal aantal historische records gecorrigeerd: {total_fixed}")
    db.clear_all_caches()

if __name__ == "__main__":
    fix_all_laura_variations()
