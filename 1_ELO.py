import streamlit as st
import pandas as pd
import firestore_service as db # Use Firestore
from styles import setup_page

setup_page()

st.title(":crown: ELO rating :crown:")

# --- Data ophalen ---
players_df = db.get_players()
matches_df = db.get_matches()

if players_df.empty:
    st.info("Nog geen spelers geregistreerd.")
    st.stop()

# --- Bereken extra statistieken ---
def calculate_stats(players, matches):
    stats_list = []
    for index, player in players.iterrows():
        player_name = player['speler_naam']
        player_matches = matches[
            (matches['thuis_1'] == player_name) | (matches['thuis_2'] == player_name) |
            (matches['uit_1'] == player_name) | (matches['uit_2'] == player_name)
        ]

        if player_matches.empty:
            stats = {'Gespeeld': 0, 'Voor': 0, 'Tegen': 0, 'Doelsaldo': 0, 'Klinkers': 0}
        else:
            goals_for = 0
            goals_against = 0
            klinkers = 0
            for _, match in player_matches.iterrows():
                if player_name in [match['thuis_1'], match['thuis_2']]:
                    goals_for += match['thuis_score']
                    goals_against += match['uit_score']
                    if player_name == match['thuis_1']:
                        klinkers += match.get('klinkers_thuis_1', 0)
                    else:
                        klinkers += match.get('klinkers_thuis_2', 0)
                else:
                    goals_for += match['uit_score']
                    goals_against += match['thuis_score']
                    if player_name == match['uit_1']:
                        klinkers += match.get('klinkers_uit_1', 0)
                    else:
                        klinkers += match.get('klinkers_uit_2', 0)
            
            stats = {
                'Gespeeld': len(player_matches),
                'Voor': int(goals_for),
                'Tegen': int(goals_against),
                'Doelsaldo': int(goals_for - goals_against),
                'Klinkers': int(klinkers)
            }
        
        stats['Speler'] = player_name
        stats['ELO'] = player['rating']
        stats_list.append(stats)
        
    return pd.DataFrame(stats_list)

# --- Huidige ELO rating tonen ---
st.header("Huidige ELO rating van alle spelers")

if not players_df.empty:
    stats_df = calculate_stats(players_df, matches_df)
    
    # Sorteer en selecteer kolommen voor weergave
    display_df = stats_df.sort_values(by='ELO', ascending=False)
    st.dataframe(display_df[['Speler', 'ELO', 'Gespeeld', 'Voor', 'Tegen', 'Doelsaldo', 'Klinkers']], width='stretch')
else:
    st.info("Geen spelersdata beschikbaar.")

# --- ELO ontwikkeling tonen ---
st.header("Ontwikkeling ELO rating per speler")

player_names = sorted(players_df['speler_naam'].tolist())
selected_player = st.selectbox("Selecteer een speler:", player_names)

if selected_player:
    # Haal de ELO geschiedenis op voor de geselecteerde speler
    # De _ttl parameter is een workaround om st.cache_data te forceren opnieuw te draaien
    history_df = db.get_elo_history(_ttl=60, speler_naam=selected_player)
    
    if not history_df.empty:
        history_df['match_num'] = range(1, len(history_df) + 1)
        st.line_chart(history_df, x='match_num', y='rating')
    else:
        st.info(f"Geen ELO geschiedenis gevonden voor {selected_player}.")