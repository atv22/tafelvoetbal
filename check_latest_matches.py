import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from firestore_service import initialize_firestore
import pandas as pd
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime, timedelta
import pytz

db = initialize_firestore()
matches_ref = db.collection('uitslag')

print("Fetching ALL latest 5 matches from Firestore, regardless of timestamp filter...")
query = matches_ref.order_by('timestamp', direction='DESCENDING').limit(5)
docs = query.stream()
for doc in docs:
    d = doc.to_dict()
    print(f"ID: {doc.id}, TS: {d.get('timestamp')} (Type: {type(d.get('timestamp'))}), Thuis: {d.get('thuis_score')}")

print("\nFetching matches with filter >= 7 days ago...")
last_week = datetime.now(pytz.utc) - timedelta(days=7)
print(f"Filter date: {last_week}")
q2 = matches_ref.where(filter=FieldFilter('timestamp', '>=', last_week))
docs2 = q2.stream()
count = 0
for doc in docs2:
    count += 1
    d = doc.to_dict()
    print(f"Match found in filter! TS: {d.get('timestamp')}")
print(f"Total matches from last 7 days: {count}")
