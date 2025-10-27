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
        
        # Veilige filtering om KeyError te voorkomen
        conditions = []
        for col in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
            if col in matches.columns:
                conditions.append(matches[col] == player_name)
        
        if not conditions:
            player_matches = pd.DataFrame()
        else:
            player_matches = matches[pd.concat(conditions, axis=1).any(axis=1)]

        if player_matches.empty:
            stats = {'Gespeeld': 0, 'Voor': 0, 'Tegen': 0, 'Doelsaldo': 0, 'Klinkers': 0}
        else:
            goals_for = 0
            goals_against = 0
            klinkers = 0
            for _, match in player_matches.iterrows():
                thuis_spelers = [match.get('thuis_1'), match.get('thuis_2')]
                uit_spelers = [match.get('uit_1'), match.get('uit_2')]
                
                if player_name in thuis_spelers:
                    goals_for += int(match.get('thuis_score', 0) or 0)
                    goals_against += int(match.get('uit_score', 0) or 0)
                    if player_name == match.get('thuis_1'):
                        klinkers += int(match.get('klinkers_thuis_1', 0) or 0)
                    else:
                        klinkers += int(match.get('klinkers_thuis_2', 0) or 0)
                elif player_name in uit_spelers:
                    goals_for += int(match.get('uit_score', 0) or 0)
                    goals_against += int(match.get('thuis_score', 0) or 0)
                    if player_name == match.get('uit_1'):
                        klinkers += int(match.get('klinkers_uit_1', 0) or 0)
                    else:
                        klinkers += int(match.get('klinkers_uit_2', 0) or 0)
            
            stats = {
                'Gespeeld': len(player_matches),
                'Voor': int(goals_for),
                'Tegen': int(goals_against),
                'Doelsaldo': int(goals_for - goals_against),
                'Klinkers': int(klinkers)
            }
        
        stats['Speler'] = player_name
        stats['ELO'] = int(player['rating'])
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