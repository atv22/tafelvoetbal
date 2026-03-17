import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from analytics import get_vectorized_player_stats
from tab_home import calculate_stats

def test_get_vectorized_player_stats_basic():
    # Setup mock data
    matches_data = [
        {
            'thuis_1': 'Speler A', 'thuis_2': 'Speler B', 
            'uit_1': 'Speler C', 'uit_2': 'Speler D',
            'thuis_score': 10, 'uit_score': 5,
            'klinkers_thuis_1': 1, 'klinkers_thuis_2': 0,
            'klinkers_uit_1': 0, 'klinkers_uit_2': 0,
            'timestamp': datetime.now(),
            'match_id': '1'
        },
        {
            'thuis_1': 'Speler C', 'thuis_2': 'Speler D', 
            'uit_1': 'Speler A', 'uit_2': 'Speler B',
            'thuis_score': 10, 'uit_score': 8,
            'klinkers_thuis_1': 0, 'klinkers_thuis_2': 0,
            'klinkers_uit_1': 0, 'klinkers_uit_2': 0,
            'timestamp': datetime.now(),
            'match_id': '2'
        }
    ]
    matches_df = pd.DataFrame(matches_data)
    
    stats = get_vectorized_player_stats(matches_df)
    
    assert not stats.empty
    assert len(stats) == 4
    
    # Speler A: 1 win (10-5), 1 loss (8-10). Total Matches: 2, Wins: 1, Goals: 18, Goals_Tegen: 15
    player_a = stats[stats['Speler'] == 'Speler A'].iloc[0]
    assert player_a['Matches'] == 2
    assert player_a['Wins'] == 1
    assert player_a['Goals'] == 18
    assert player_a['Goals_Tegen'] == 15
    assert player_a['Winrate'] == 50.0
    assert player_a['Klinkers'] == 1

def test_calculate_stats_integration():
    players_df = pd.DataFrame([
        {'speler_naam': 'Speler A', 'rating': 1200},
        {'speler_naam': 'Speler B', 'rating': 1100},
        {'speler_naam': 'Speler E', 'rating': 1000} # No matches
    ])
    
    matches_data = [
        {
            'thuis_1': 'Speler A', 'thuis_2': 'Speler B', 
            'uit_1': 'Speler C', 'uit_2': 'Speler D',
            'thuis_score': 10, 'uit_score': 5,
            'timestamp': datetime.now(),
            'match_id': '1'
        }
    ]
    matches_df = pd.DataFrame(matches_data)
    
    stats_df = calculate_stats(players_df, matches_df)
    
    assert len(stats_df) == 3
    
    # Check Speler A
    a_stats = stats_df[stats_df['Speler'] == 'Speler A'].iloc[0]
    assert a_stats['ELO'] == 1200
    assert a_stats['Gespeeld'] == 1
    assert a_stats['Win%'] == 100.0
    
    # Check Speler E (no matches)
    e_stats = stats_df[stats_df['Speler'] == 'Speler E'].iloc[0]
    assert e_stats['ELO'] == 1000
    assert e_stats['Gespeeld'] == 0
    assert e_stats['Win%'] == 0.0

def test_performance_comparison():
    # Generate 1000 random matches
    players = [f"P{i}" for i in range(20)]
    data = []
    for i in range(1000):
        p = np.random.choice(players, 4, replace=False)
        data.append({
            'thuis_1': p[0], 'thuis_2': p[1],
            'uit_1': p[2], 'uit_2': p[3],
            'thuis_score': np.random.randint(0, 11),
            'uit_score': np.random.randint(0, 11),
            'timestamp': datetime.now(),
            'match_id': str(i)
        })
    df = pd.DataFrame(data)
    
    import time
    start = time.perf_counter()
    stats = get_vectorized_player_stats(df)
    end = time.perf_counter()
    
    duration = end - start
    print(f"Vectorized stats for 1000 matches took {duration:.4f}s")
    
    assert duration < 0.5 # Should be very fast
    assert len(stats) > 0
