import os
import sys
import pandas as pd

# Voeg de root directory toe aan path voor firestore_service
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import firestore_service as db
from google.cloud.firestore_v1.base_query import FieldFilter

def deep_clean_db():
    print("--- START DEEP CLEAN DATABASE ---")
    
    # 1. Verwijder Niemanduit uit spelers collectie
    niemand_docs = list(db.players_ref.where(filter=FieldFilter('speler_naam', '==', 'Niemanduit')).stream())
    for doc in niemand_docs:
        print(f"   [DELETE] Speler document 'Niemanduit' (ID: {doc.id})")
        doc.reference.delete()

    # 2. Fix Dubbele Fré
    fre_docs = list(db.players_ref.where(filter=FieldFilter('speler_naam', '>=', 'Fr')).where(filter=FieldFilter('speler_naam', '<', 'Fs')).stream())
    if len(fre_docs) > 1:
        print(f"   [MERGE] Gevonden: {len(fre_docs)} documenten voor 'Fré'. Behoude eerste, verwijder rest.")
        for doc in fre_docs[1:]:
            doc.reference.delete()

    # 3. Merge Laura -> LauraThöni
    # Haal alle historie op waar speler_naam 'Laura' is en zet om naar 'LauraThöni'
    print("   [MERGE] Laura -> LauraThöni in alle collecties...")
    for coll_name in ['elo', 'uitslag']:
        coll_ref = db.db.collection(coll_name)
        fields = ['speler_naam'] if coll_name == 'elo' else ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']
        for field in fields:
            docs = list(coll_ref.where(filter=FieldFilter(field, '==', 'Laura')).stream())
            for doc in docs:
                doc.reference.update({field: 'LauraThöni'})
                print(f"      - Gefixed: {coll_name}.{field}")
    
    # Verwijder speler doc 'Laura'
    laura_docs = list(db.players_ref.where(filter=FieldFilter('speler_naam', '==', 'Laura')).stream())
    for doc in laura_docs:
        doc.reference.delete()

    # 4. De "LauraThni" Fix - Brute Force
    # We scannen de hele historie op namen die 'Laura' bevatten maar niet 'Thöni' zijn
    print("   [BRUTE FORCE] Scannen op encoding fouten voor LauraThöni...")
    for coll_name in ['elo', 'uitslag']:
        coll_ref = db.db.collection(coll_name)
        docs = coll_ref.stream()
        for doc in docs:
            d = doc.to_dict()
            changed = False
            for key, val in d.items():
                if isinstance(val, str) and 'Laura' in val and 'Thöni' not in val and val != 'LauraThöni':
                    print(f"      - Gevonden foutieve naam: '{val}' in {coll_name}/{doc.id}. Corrigeren...")
                    d[key] = 'LauraThöni'
                    changed = True
            if changed:
                doc.reference.set(d)

    print("\n✅ Deep clean voltooid.")
    db.clear_all_caches()

if __name__ == "__main__":
    deep_clean_db()
