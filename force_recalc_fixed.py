import firestore_service as db
import pandas as pd

try:
    seasons_df = db.get_seasons()
    if not seasons_df.empty:
        current_season = seasons_df.iloc[-1]
        start_ts = current_season['start_datum']
        end_ts = current_season['eind_datum']
        print(f"Recalculating for season: {current_season['seizoen_naam']} from {start_ts} to {end_ts}")
        
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
