
import sys
import os
import pandas as pd
import time

# Add parent directory to path to import firestore_service
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import firestore_service as db

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'csv', 'read', 'elo.csv')

def run_csv_migration():
    print("Starting CSV-based migration...")
    print(f"Reading ELO data from: {CSV_PATH}")
    
    try:
        # 1. Read CSV
        if not os.path.exists(CSV_PATH):
            print(f"Error: CSV file not found at {CSV_PATH}")
            return

        df = pd.read_csv(CSV_PATH)
        print(f"Loaded {len(df)} rows from CSV.")
        
        # 2. Find latest rating per player
        # Convert timestamp to datetime, handling mixed formats (with/without timezone)
        # utc=True ensures all are converted to UTC, handling mixed offsets
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, format='mixed')
        except Exception as e:
            print(f"Error parsing timestamps with format='mixed': {e}")
            print("Retrying with default parsing...")
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

        print("Timestamps parsed successfully.")
        print(df.dtypes)
        
        # Sort by player and timestamp descending
        df_sorted = df.sort_values(by=['speler_naam', 'timestamp'], ascending=[True, False])
        
        # Drop duplicates to keep only the first (latest) entry per player
        latest_ratings = df_sorted.drop_duplicates(subset=['speler_naam'], keep='first')
        
        print(f"Found latest ratings for {len(latest_ratings)} players.")
        
        # 3. Update Firestore
        # We still need to fetch players to get their document references (or query by name)
        # To save reads, we can query by name for each player in our list? 
        # No, fetching all players is 1 read per player (or 1 list operation).
        # List operation is better.
        
        print("Fetching players from Firestore to match IDs...")
        players_docs = list(db.players_ref.stream())
        print(f"Found {len(players_docs)} players in Firestore.")
        
        # Create a map of name -> doc_ref
        player_map = {doc.to_dict().get('speler_naam'): doc.reference for doc in players_docs}
        
        batch = db.db.batch()
        batch_counter = 0
        updated_count = 0
        
        for _, row in latest_ratings.iterrows():
            name = row['speler_naam']
            rating = row['rating']
            
            if name in player_map:
                ref = player_map[name]
                # We can check if update is needed if we read the doc data, but we already have it.
                # Let's just update to be sure.
                batch.update(ref, {'rating': rating})
                batch_counter += 1
                updated_count += 1
                
                if batch_counter >= 400:
                    batch.commit()
                    batch = db.db.batch()
                    batch_counter = 0
                    print(f"Committed batch. Updated {updated_count} players.")
            else:
                print(f"Warning: Player '{name}' found in CSV but not in Firestore players collection.")

        if batch_counter > 0:
            batch.commit()
            
        print(f"Migration finished. Updated {updated_count} players using CSV data.")
        
    except Exception as e:
        print(f"Error during CSV migration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_csv_migration()
