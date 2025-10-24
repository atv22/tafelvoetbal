import time
import streamlit as st
import firestore_service as db # Use Firestore
from utils import elo_calculation # Use ELO calculation from utils
from styles import setup_page

setup_page()

st.title("Tafelvoetbal Competitie ⚽ — Invullen")

# --- Data ophalen ---
players_df = db.get_players()
if players_df.empty:
    st.warning("Er zijn nog geen spelers. Voeg eerst een speler toe via de 'Spelers' pagina.")
    st.stop()

player_names = sorted(players_df['speler_naam'].tolist())
player_elos = players_df.set_index('speler_naam')['rating'].to_dict()

# --- UI ---
klink = st.radio("Zijn er klinkers gescoord?", ("Nee", "Ja"))

selected_names = {
    'Thuis 1': {'name': None, 'klinkers': 0},
    'Thuis 2': {'name': None, 'klinkers': 0},
    'Uit 1':   {'name': None, 'klinkers': 0},
    'Uit 2':   {'name': None, 'klinkers': 0},
}

with st.form("formulier"):
    cols = st.columns(4)
    for i, title in enumerate(selected_names):
        with cols[i]:
            selected_names[title]['name'] = st.selectbox(title, player_names, key=f"sel_{title}", index=i % len(player_names))

    if klink == "Ja":
        klinker_cols = st.columns(4)
        for i, title in enumerate(selected_names):
            with klinker_cols[i]:
                selected_names[title]['klinkers'] = st.number_input(f"Klinkers {title}", min_value=0, max_value=10, step=1, key=f"kl_{title}")

    score_cols = st.columns(2)
    with score_cols[0]:
        home_score = st.number_input("Score Thuis:", min_value=0, max_value=10, step=1)
    with score_cols[1]:
        away_score = st.number_input("Score Uit:",   min_value=0, max_value=10, step=1)

    if st.form_submit_button("Verstuur Uitslag"):
        # --- Validatie ---
        if home_score == 10 and away_score == 10:
            st.error('Beide scores kunnen niet 10 zijn.')
            st.stop()
        if home_score != 10 and away_score != 10:
            st.error('Eén van de scores moet 10 zijn.')
            st.stop()
        
        player_list = [p['name'] for p in selected_names.values()]
        if len(set(player_list)) < 4:
            st.error("Selecteer vier unieke spelers.")
            st.stop()

        # --- ELO Berekening ---
        home_team_names = [selected_names['Thuis 1']['name'], selected_names['Thuis 2']['name']]
        away_team_names = [selected_names['Uit 1']['name'], selected_names['Uit 2']['name']]

        home_team_elos = [player_elos[p] for p in home_team_names]
        away_team_elos = [player_elos[p] for p in away_team_names]

        avg_elo_home = sum(home_team_elos) / 2
        avg_elo_away = sum(away_team_elos) / 2

        new_elos = {}
        for player_name in home_team_names:
            new_elos[player_name] = elo_calculation(player_elos[player_name], avg_elo_away, home_score, away_score)
        for player_name in away_team_names:
            new_elos[player_name] = elo_calculation(player_elos[player_name], avg_elo_home, away_score, home_score)

        # --- Data voorbereiden voor Firestore ---
        match_data = {
            'thuis_1': selected_names['Thuis 1']['name'],
            'thuis_2': selected_names['Thuis 2']['name'],
            'uit_1': selected_names['Uit 1']['name'],
            'uit_2': selected_names['Uit 2']['name'],
            'thuis_score': home_score,
            'uit_score': away_score,
            'klinkers_thuis_1': selected_names['Thuis 1']['klinkers'],
            'klinkers_thuis_2': selected_names['Thuis 2']['klinkers'],
            'klinkers_uit_1': selected_names['Uit 1']['klinkers'],
            'klinkers_uit_2': selected_names['Uit 2']['klinkers'],
        }

        elo_updates = list(new_elos.items())

        # --- Opslaan in Firestore ---
        success = db.add_match_and_update_elo(match_data, elo_updates)

        if success:
            st.success("Uitslag en nieuwe ELO ratings succesvol opgeslagen!")
            if (home_score == 10 and away_score == 0) or (home_score == 0 and away_score == 10):
                st.balloons()
            time.sleep(1)
            st.rerun()
        else:
            st.error("Er is een fout opgetreden bij het opslaan van de wedstrijd.")