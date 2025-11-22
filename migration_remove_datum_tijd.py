
import firestore_service as db
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore

def remove_datum_tijd_from_firestore():
    matches_ref = db.matches_ref
    batch = db.db.batch()
    count = 0
    docs = matches_ref.stream()
    for doc in docs:
        data = doc.to_dict()
        update_fields = {}
        if 'datum' in data:
            update_fields['datum'] = firestore.DELETE_FIELD
        if 'tijd' in data:
            update_fields['tijd'] = firestore.DELETE_FIELD
        if update_fields:
            batch.update(doc.reference, update_fields)
            count += 1
            if count % 400 == 0:
                batch.commit()
                batch = db.db.batch()
    if count % 400 != 0:
        batch.commit()
    print(f"Verwijderd uit {count} Firestore documenten.")

if __name__ == "__main__":
    remove_datum_tijd_from_firestore()
