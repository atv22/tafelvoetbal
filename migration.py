
import firestore_service as db
import pandas as pd

def migrate_matches():
    """
    Migrates match data in Firestore from the old format (speler1, score_team1)
    to the new format (thuis_1, thuis_score).
    """
    print("Starting migration of 'uitslag' collection...")
    matches_ref = db.db.collection('uitslag')
    matches_docs = matches_ref.stream()

    migrated_count = 0
    docs_to_update = []

    for doc in matches_docs:
        match_data = doc.to_dict()
        doc_id = doc.id
        
        # Check if this document needs migration
        if 'speler1' in match_data or 'score_team1' in match_data:
            new_data = match_data.copy()
            
            # Rename fields
            new_data['thuis_1'] = new_data.pop('speler1', None)
            new_data['thuis_2'] = new_data.pop('speler2', None)
            new_data['uit_1'] = new_data.pop('speler3', None)
            new_data['uit_2'] = new_data.pop('speler4', None)
            new_data['thuis_score'] = new_data.pop('score_team1', None)
            new_data['uit_score'] = new_data.pop('score_team2', None)
            
            # Remove any None values that may result from pop
            new_data = {k: v for k, v in new_data.items() if v is not None}
            
            docs_to_update.append((doc.reference, new_data))
            migrated_count += 1
            print(f"Marked document {doc_id} for migration.")

    if not docs_to_update:
        print("No documents needed migration. Database is up to date.")
        return

    print(f"\nFound {migrated_count} documents to migrate. Updating now...")

    # Update documents in a batch
    batch = db.db.batch()
    for ref, data in docs_to_update:
        batch.set(ref, data, merge=True) # Use set with merge=True to be safe
    
    try:
        batch.commit()
        print(f"\nSuccessfully migrated {migrated_count} documents!")
        # Clear cache to ensure the app re-fetches the updated data
        db.st.cache_data.clear()
    except Exception as e:
        print(f"\nAn error occurred during the batch update: {e}")

if __name__ == '__main__':
    migrate_matches()
