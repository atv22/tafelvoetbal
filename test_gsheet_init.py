import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from firestore_service import _fetch_all_gsheet_data, get_matches, store
import pandas as pd

print("Fetching gsheet data...")
data = _fetch_all_gsheet_data()
store["matches"] = data.get("matches", {})
store["elo"] = data.get("elo", {})
store["players"] = data.get("players", {})

print(f"Matches count: {len(store['matches'])}")
print(f"ELO count: {len(store['elo'])}")
print(f"Players count: {len(store['players'])}")

# Now let's try to build dataframes
from firestore_service import _build_matches_df, _build_elo_logs_df

try:
    df = _build_matches_df(123)
    print("Matches DF built successfully!")
    print(df.head(2)[['match_id', 'timestamp']])
except Exception as e:
    print(f"Error building matches DF: {e}")

try:
    df_elo = _build_elo_logs_df(123)
    print("ELO DF built successfully!")
    print(df_elo.head(2)[['match_id', 'timestamp']])
except Exception as e:
    print(f"Error building ELO DF: {e}")
