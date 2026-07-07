import os
import sys
# Add current dir to path to import firestore_service
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from firestore_service import initialize_firestore
import pandas as pd
from datetime import datetime, timedelta

db = initialize_firestore()
if db is None:
    print("Could not connect to Firestore")
    sys.exit(1)

logs_ref = db.collection('beheer_log')
two_days_ago = datetime.now() - timedelta(days=2)
logs = logs_ref.where('Timestamp', '>=', two_days_ago).stream()

log_list = []
for doc in logs:
    data = doc.to_dict()
    log_list.append(data)

if not log_list:
    print("No logs in the last 2 days.")
else:
    df = pd.DataFrame(log_list)
    df = df.sort_values(by='Timestamp')
    for idx, row in df.iterrows():
        ts = row.get('Timestamp')
        action = row.get('Actie', 'N/A')
        details = row.get('Details', 'N/A')
        print(f"[{ts}] {action}: {details}")
