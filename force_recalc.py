import firestore_service as db
import pandas as pd

try:
    seasons = db.get_seasons()
    current = None
    for s in seasons:
        if s.get('is_huidig') or s.get('is_current'):
            current = s
            break
    
    if not current and seasons:
        current = seasons[0] # Fallback to first if none marked

    if current:
        start_ts = pd.Timestamp(current.get('start_datum', current.get('startdatum')))
        end_ts = pd.Timestamp(current.get('eind_datum', current.get('einddatum')))
        print(f"Recalculating for season: {current.get('naam')} from {start_ts} to {end_ts}")
        
        if start_ts.tzinfo is None:
            start_ts = start_ts.tz_localize('UTC')
        if end_ts.tzinfo is None:
            end_ts = end_ts.tz_localize('UTC')

        success = db.recalculate_elos_from(start_ts, start_ts, end_ts)
        print(f"Success: {success}")
    else:
        print("No seasons found.")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {e}")
