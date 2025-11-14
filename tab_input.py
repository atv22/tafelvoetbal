"""
TAB 2: Input module voor tafelvoetbal app
Bevat wedstrijd invoer formulier, validatie en ELO berekeningen
"""
import streamlit as st
import time
import firestore_service as db
from utils import elo_calculation


def render_match_input_form(player_names, player_elos):
    """Render het wedstrijd invoer formulier"""
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
            return process_match_submission(selected_names, home_score, away_score, player_elos)
    
    return False


def validate_match_input(selected_names, home_score, away_score):
    """Valideer de wedstrijd invoer"""
    # Score validatie
    if home_score == 10 and away_score == 10:
        st.error('Beide scores kunnen niet 10 zijn.')
        return False
    if home_score != 10 and away_score != 10:
        st.error('Eén van de scores moet 10 zijn.')
        return False
    
    # Speler uniekheid validatie
    player_list = [p['name'] for p in selected_names.values()]
    if len(set(player_list)) < 4:
        st.error("Selecteer vier unieke spelers.")
        return False
    
    return True


def calculate_new_elos(selected_names, home_score, away_score, player_elos):
    """Bereken nieuwe ELO ratings voor alle spelers"""
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
    
    return new_elos


def prepare_match_data(selected_names, home_score, away_score):
    """Bereid wedstrijd data voor om op te slaan"""
    return {
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


def process_match_submission(selected_names, home_score, away_score, player_elos):
    """Proces de complete wedstrijd submissie"""
    # Valideer input
    if not validate_match_input(selected_names, home_score, away_score):
        return False

    # Bereken nieuwe ELO ratings
    new_elos = calculate_new_elos(selected_names, home_score, away_score, player_elos)

    # Bereid data voor
    match_data = prepare_match_data(selected_names, home_score, away_score)
    elo_updates = list(new_elos.items())

    # Opslaan in Firestore
    success = db.add_match_and_update_elo(match_data, elo_updates)

    if success:
        st.success("Uitslag en nieuwe ELO ratings succesvol opgeslagen!")
        if (home_score == 10 and away_score == 0) or (home_score == 0 and away_score == 10):
            st.balloons()
        time.sleep(1)
        st.rerun()
        return True
    else:
        st.error("Er is een fout opgetreden bij het opslaan van de wedstrijd.")
        return False


def render_input_tab(players_df):
    """Render de complete Input tab"""
    st.header("Tafelvoetbal Competitie ⚽ — Invullen")
    
    if players_df.empty:
        st.warning("Er zijn nog geen spelers. Voeg eerst een speler toe via de 'Spelers' tab.")
    else:
        player_names = sorted(players_df['speler_naam'].tolist())
        player_elos = players_df.set_index('speler_naam')['rating'].to_dict()

        render_match_input_form(player_names, player_elos)