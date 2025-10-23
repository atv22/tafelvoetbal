import streamlit as st
import pandas as pd
from config import get_uitslag_df
from utils import get_klinkers_for_player, elo_calculation
st.title("ELO rating (bèta)")
df = get_uitslag_df()
if df.empty:
    st.info("Nog geen wedstrijden geregistreerd.")
    st.stop()
# Filter er ‘Niemand’ regels uit
mask_valid = ~df[['Thuis_1','Thuis_2','Uit_1','Uit_2']].isin(['Niemand','Niemanduit']).any(axis=1)
df_elo = df[mask_valid]
player_stats = {}
match_ind = 1
for _, row in df_elo.iterrows():
    home_team = [row['Thuis_1'], row['Thuis_2']]
    away_team = [row['Uit_1'], row['Uit_2']]
    home_score = int(row['Thuis_score'])
    away_score = int(row['Uit_score'])
    timestamp = row['Timestamp']
    for team, score, opposing_team, opposing_score in [
        (home_team, home_score, away_team, away_score),
        (away_team, away_score, home_team, home_score),
    ]:
        elo_temp_match = {}
        for t in [team, opposing_team]:
            for player in t:
                player_stats.setdefault(player, [])
                elo = 1000 if not player_stats[player] else player_stats[player][-1][2]
                elo_temp_match[player] = elo
        for player in team:
            player_stats.setdefault(player, [])
            match_index = match_ind
            elo = elo_temp_match[player]
            opponents = [p for p in opposing_team]
            opponent_elo = sum(elo_temp_match[o] for o in opponents) / 2
            elo = elo_calculation(elo, opponent_elo, score, opposing_score)
            total_goals = sum(s[4] for s in player_stats[player]) + score
            total_matches = len(player_stats[player]) + 1
            avg_goals_per_match = round(total_goals / total_matches, 2)
            total_goals_opposing = sum(s[7] for s in player_stats[player]) + opposing_score
            goal_diff = score - opposing_score
            goal_diff_total = sum(s[8] for s in player_stats[player]) + goal_diff
            avg_goal_diff = round(goal_diff_total / total_matches, 2)
            klinkers = get_klinkers_for_player(player, row)
            klinkers_total = sum(s[12] for s in player_stats[player]) + klinkers
            avg_klinkers = round(klinkers_total / total_matches, 2)
            player_stats[player].append([
                match_index, timestamp, elo, total_matches, score, total_goals, avg_goals_per_match,
                opposing_score, goal_diff, goal_diff_total, avg_goal_diff, total_goals_opposing,
                klinkers, klinkers_total, avg_klinkers,
            ])
            match_ind += 1
# overzicht huidig
rows = []
for player, stats in player_stats.items():
    latest = stats[-1]
    rows.append([player] + latest)
col = ['Speler','Wedstrijd Index','Timestamp','ELO','Gespeeld','Doelpunten laatste wedstrijd','Voor',
       'Gem aantal doelpunten per wedstrijd','Score tegenstander','Doelsaldo wedstrijd','Doelsaldo',
       'Gem. doelsaldo','Tegen','Klinkers wedstrijd','Klinkers','Gem. klinkers']
df_player = pd.DataFrame(rows, columns=col).sort_values(by='ELO', ascending=False)
st.header("Huidige ELO rating van alle spelers")
st.dataframe(df_player[["Speler","ELO","Gespeeld","Voor","Tegen","Doelsaldo","Gem. doelsaldo","Klinkers"]])
st.header("Ontwikkeling ELO rating per speler")
players_elo = sorted(list(player_stats.keys()))
selected = st.selectbox("Selecteer een speler:", players_elo)
if selected:
    elo_data = {
        "Match Index": [s[3] for s in player_stats[selected]],
        "ELO Rating": [s[2] for s in player_stats[selected]]}
st.write(player_stats)
 