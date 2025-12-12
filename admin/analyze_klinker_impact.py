
import sys
import os
import pandas as pd
import numpy as np
from collections import defaultdict
import traceback

# Add project root to path to allow importing utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from utils.utils_new_elo import calculate_new_elo
except ImportError:
    # Fallback if running from root
    sys.path.append(os.getcwd())
    from utils.utils_new_elo import calculate_new_elo

def main():
    print("Loading data...")
    # Load matches
    try:
        df_matches = pd.read_csv(os.path.join('csv', 'read', 'uitslag.csv'))
    except FileNotFoundError:
        print("Error: csv/read/uitslag.csv not found.")
        return

    # Sort by date to ensure correct order of replay
    if 'timestamp' in df_matches.columns:
        df_matches['timestamp'] = pd.to_datetime(df_matches['timestamp'])
        df_matches = df_matches.sort_values('timestamp')
    else:
        print("Warning: No timestamp found, assuming CSV order is chronological.")

    # Pre-scan for all players to avoid default-dict issues
    all_players = set()
    player_cols = ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']
    for col in player_cols:
        if col in df_matches.columns:
            all_players.update(df_matches[col].dropna().unique())
            
    print(f"Found {len(all_players)} unique players.")

    # Initialize Elo ratings explicitly
    current_elo = {player: [1000.0] for player in all_players}
    
    # Stats collectors
    results = []
    
    print(f"Replaying {len(df_matches)} matches...")
    
    for idx, match_row in df_matches.iterrows():
        # Construct match dict for calculate_new_elo
        
        # Check for missing players in this specific match (e.g. NaN)
        # If dataset has missing players, skip or handle?
        # Assuming clean data for now, but adding check
        players = [match_row['thuis_1'], match_row['thuis_2'], match_row['uit_1'], match_row['uit_2']]
        if any(pd.isna(p) for p in players):
            # print(f"Skipping match {idx} due to missing player names.")
            continue

        match_data = {
            "Thuis_1": match_row['thuis_1'],
            "Thuis_2": match_row['thuis_2'],
            "Uit_1": match_row['uit_1'],
            "Uit_2": match_row['uit_2'],
            "Thuis_score": match_row['thuis_score'],
            "Uit_score": match_row['uit_score'],
            "klinkers_thuis_1": match_row.get('klinkers_thuis_1', 0),
            "klinkers_thuis_2": match_row.get('klinkers_thuis_2', 0),
            "klinkers_uit_1": match_row.get('klinkers_uit_1', 0),
            "klinkers_uit_2": match_row.get('klinkers_uit_2', 0)
        }
        
        # Verify keys exist (sanity check)
        for p in players:
            if p not in current_elo:
                current_elo[p] = [1000.0]

        # Snapshot pre-match stats
        match_stats = {
            'match_id': match_row.get('match_id', idx),
            'timestamp': match_row.get('timestamp'),
            'score_diff': abs(match_row['thuis_score'] - match_row['uit_score']),
            'players': {}
        }
        
        # Calculate new Elo
        try:
            new_elo_df = calculate_new_elo(match_data, current_elo)
        except Exception as e:
            print(f"Error calculating Elo for match {idx}: {e}")
            traceback.print_exc()
            continue
            
        # Process results
        for _, row in new_elo_df.iterrows():
            player = row['Speler']
            new_rating = row['ELO']
            old_rating = current_elo[player][-1]
            delta = new_rating - old_rating
            
            # Identify role and klinkers
            role = ''
            klinkers = 0
            teammate = ''
            
            if player == match_row['thuis_1']:
                role = 'thuis_1'
                klinkers = match_row.get('klinkers_thuis_1', 0)
                teammate = match_row['thuis_2']
            elif player == match_row['thuis_2']:
                role = 'thuis_2'
                klinkers = match_row.get('klinkers_thuis_2', 0)
                teammate = match_row['thuis_1']
            elif player == match_row['uit_1']:
                role = 'uit_1'
                klinkers = match_row.get('klinkers_uit_1', 0)
                teammate = match_row['uit_2']
            elif player == match_row['uit_2']:
                role = 'uit_2'
                klinkers = match_row.get('klinkers_uit_2', 0)
                teammate = match_row['uit_1']
                
            match_stats['players'][player] = {
                'old_elo': old_rating,
                'new_elo': new_rating,
                'delta': delta,
                'klinkers': int(klinkers) if not pd.isna(klinkers) else 0,
                'teammate': teammate,
                'won': (delta > 0) 
            }
            
            # Update history
            current_elo[player].append(new_rating)
            
        results.append(match_stats)

    # --- Analysis ---
    print("\nAnalyzing results...")
    
    klinker_deltas_vs_teammate = []
    
    for match in results:
        # Check intra-team comparisons
        # Safely access players
        t1 = match_row['thuis_1']
        t2 = match_row['thuis_2']
        u1 = match_row['uit_1']
        u2 = match_row['uit_2']
        
        # Re-derive teams from match_stats to be sure
        # The keys in match_stats['players'] are accurate
        
        match_players = match['players']
        
        # Group by team based on teammate mapping
        processed_players = set()
        
        for player, stats in match_players.items():
            if player in processed_players:
                continue
            
            teammate = stats['teammate']
            if teammate in match_players:
                processed_players.add(player)
                processed_players.add(teammate)
                
                p1_stats = stats
                p2_stats = match_players[teammate]
                
                # Check klinkers
                if p1_stats['klinkers'] == 0 and p2_stats['klinkers'] == 0:
                    continue
                
                gain_diff = p1_stats['delta'] - p2_stats['delta']
                klinker_diff = p1_stats['klinkers'] - p2_stats['klinkers']
                
                if klinker_diff != 0:
                    klinker_deltas_vs_teammate.append({
                        'klinker_diff': klinker_diff,
                        'elo_gain_diff': gain_diff,
                        'p1_elo': p1_stats['old_elo'],
                        'p2_elo': p2_stats['old_elo']
                    })

    df_analysis = pd.DataFrame(klinker_deltas_vs_teammate)
    
    if df_analysis.empty:
        print("No matches found where teammates had different klinker counts.")
    else:
        print(f"\nFound {len(df_analysis)} team-pairs with mixed klinker counts.")
        
        similar_elo = df_analysis[abs(df_analysis['p1_elo'] - df_analysis['p2_elo']) < 1]
        
        print("\n--- Control Group: Teammates with identical (diff < 1.0) starting Elo ---")
        if similar_elo.empty:
            print("No teammates had identical Elo.")
        else:
            print(f"Subset size: {len(similar_elo)}")
            mean_diff = similar_elo['elo_gain_diff'].mean()
            print(f"Mean difference in Elo Gain (Player w/ Klinkers - Teammate): {mean_diff:.10f}")
            if abs(mean_diff) < 0.000001:
                print("CONCLUSION: No effect detected. Players with equal rating gain EXACTLY the same Elo regardless of klinkers.")
            else:
                print("CONCLUSION: EFFECT DETECTED! Klinkers seem to affect individual Elo.")
                
        # Also print raw correlation
        corr = df_analysis['klinker_diff'].corr(df_analysis['elo_gain_diff'])
        print(f"\nOverall Correlation (Klinker Diff vs Elo Gain Diff): {corr:.4f}")
        
if __name__ == "__main__":
    main()
