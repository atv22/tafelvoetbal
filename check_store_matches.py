import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from firestore_service import initialize_firestore, init_firestore_listeners, _build_matches_df
import time
import pandas as pd

print("Initializing listeners...")
store = init_firestore_listeners()

time.sleep(3) # Wait for on_snapshot to populate

matches = list(store["matches"].values())
print(f"Total matches in store: {len(matches)}")

df = _build_matches_df(123)
print(f"Total matches in DF: {len(df)}")
if not df.empty:
    print("\nLatest matches in DF:")
    print(df[['match_id', 'timestamp', 'thuis_score', 'uit_score']].head(10))
