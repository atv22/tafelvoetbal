import firestore_service as db
from google.cloud.firestore import SERVER_TIMESTAMP

try:
    config_ref = db.db.collection('system_config').document('elo_recalc')
    config_ref.set({
        'recalc_needed': True,
        'last_recalc_time': SERVER_TIMESTAMP,
        'season_start': None,
        'season_end': None,
        'season_naam': None
    }, merge=True)
    print("recalc_needed flag set to True.")
except Exception as e:
    print(f"Error: {e}")
