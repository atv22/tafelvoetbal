import firestore_service as db
import pandas as pd

try:
    seasons_df = db.get_seasons()
    if not seasons_df.empty:
        current_season = seasons_df.iloc[-1]
        start_ts = current_season['start_datum']
        end_ts = current_season['eind_datum']
        
        if start_ts.tzinfo is None:
            start_ts = start_ts.tz_localize('UTC')
        if end_ts.tzinfo is None:
            end_ts = end_ts.tz_localize('UTC')

        start_ts_pd = pd.Timestamp(start_ts).tz_localize(None)
        
        all_matches = db.get_matches()
        all_matches['ts_naive'] = all_matches['timestamp'].apply(lambda x: x.replace(tzinfo=None) if hasattr(x, 'tzinfo') and x.tzinfo is not None else x)
        
        season_mask = (all_matches['ts_naive'].dt.date >= pd.Timestamp(start_ts).date()) & (all_matches['ts_naive'].dt.date <= pd.Timestamp(end_ts).date())
        season_matches = all_matches[season_mask]
        
        future_matches = season_matches[season_matches['ts_naive'] >= start_ts_pd]
        print(f"Season start: {start_ts_pd}")
        print(f"Season matches count: {len(season_matches)}")
        print(f"Future matches count: {len(future_matches)}")
        if not future_matches.empty:
            print("First future match:", future_matches.iloc[0]['ts_naive'])
            print("Last future match:", future_matches.iloc[-1]['ts_naive'])
    else:
        print("No seasons found.")
except Exception as e:
    print(f"Error: {e}")
