import firestore_service as db
import pandas as pd

try:
    elo_logs = db.elo_ref.where('speler_naam', '==', 'Johannes').stream()
    logs = [l.to_dict() for l in elo_logs]
    df = pd.DataFrame(logs)
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', utc=True)
        df = df.sort_values('timestamp', ascending=False)
        print("Latest ELO logs for Johannes:")
        print(df.head(10)[['timestamp', 'rating', 'match_id']])
    else:
        print("No ELO logs for Johannes found in Firestore.")
except Exception as e:
    print(f"Error: {e}")
