import pandas as pd
from firestore_service import get_matches, get_elo_logs

try:
    m_df = get_matches()
    m_df['timestamp'] = pd.to_datetime(m_df['timestamp'], utc=True)
    j_matches = m_df[(m_df['thuis_1'] == 'Johannes') | (m_df['thuis_2'] == 'Johannes') | (m_df['uit_1'] == 'Johannes') | (m_df['uit_2'] == 'Johannes')]
    j_matches = j_matches.sort_values(['timestamp'], ascending=[True])
    print("Matches Johannes:")
    print(j_matches.tail(5)[['timestamp', 'thuis_1', 'thuis_2', 'uit_1', 'uit_2']])

    elo_df = get_elo_logs()
    j_elo = elo_df[elo_df['speler_naam'] == 'Johannes'].copy()
    j_elo['timestamp'] = pd.to_datetime(j_elo['timestamp'], utc=True)
    j_elo = j_elo.sort_values(['timestamp'], ascending=[True], na_position='first')
    print("\nELO Johannes:")
    print(j_elo.tail(10))
except Exception as e:
    print(f"Error: {e}")
