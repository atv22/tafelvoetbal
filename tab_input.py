"""
TAB 2: Input module voor tafelvoetbal app
Bevat wedstrijd invoer formulier, validatie en ELO berekeningen
"""
import streamlit as st
import time
import firestore_service as db
from utils_new_elo import calculate_new_elo


def render_match_input_form(player_names, player_elos):
    """Render het wedstrijd invoer formulier (nu met datum keuze)"""
    klink = st.radio("Zijn er klinkers gescoord?", ("Nee", "Ja"))

    selected_names = {
        'Thuis 1': {'name': None, 'klinkers': 0},
        'Thuis 2': {'name': None, 'klinkers': 0},
        'Uit 1':   {'name': None, 'klinkers': 0},
        'Uit 2':   {'name': None, 'klinkers': 0},
    }

    # Default testspelers als ze bestaan
    test_defaults = ["TestThuisA", "TestThuisB", "TestUitA", "TestUitB"]
    default_indices = []
    for test_name in test_defaults:
        if test_name in player_names:
            default_indices.append(player_names.index(test_name))
        else:
            default_indices.append(0)

    import uuid
    session_key = str(uuid.uuid4())
    with st.form("formulier"):
        cols = st.columns(4)
        for i, title in enumerate(selected_names):
            with cols[i]:
                selected_names[title]['name'] = st.selectbox(
                    title,
                    player_names,
                    key=f"sel_{title}_{session_key}",
                    index=default_indices[i] if len(default_indices) == 4 else i % len(player_names)
                )

        if klink == "Ja":
            klinker_cols = st.columns(4)
            for i, title in enumerate(selected_names):
                with klinker_cols[i]:
                    selected_names[title]['klinkers'] = st.number_input(f"Klinkers {title}", min_value=0, max_value=10, step=1, key=f"kl_{title}_{session_key}")

        score_cols = st.columns(2)
        with score_cols[0]:
            home_score = st.number_input("Score Thuis:", min_value=0, max_value=10, step=1, key=f"score_thuis_{session_key}")
        with score_cols[1]:
            away_score = st.number_input("Score Uit:",   min_value=0, max_value=10, step=1, key=f"score_uit_{session_key}")

        from datetime import datetime
        now = datetime.now()
        match_date = st.date_input("Datum van de wedstrijd", value=now.date(), key=f"date_{session_key}", help="Standaard vandaag. Kies een andere dag indien gewenst.")
        match_time = st.time_input("Tijd van de wedstrijd", value=now.time().replace(microsecond=0), key=f"time_{session_key}", help="Standaard huidige tijd. Kies een andere tijd indien gewenst.")

        if st.form_submit_button("Verstuur Uitslag"):
            match_datetime = datetime.combine(match_date, match_time)
            return process_match_submission(selected_names, home_score, away_score, player_elos, match_datetime)
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
    # Prepare match dict for new ELO calculation
    # Detect home/away columns for ELO calculation (support both schemas)
    match = {
        "Thuis_1": selected_names['Thuis 1']['name'],
        "Thuis_2": selected_names['Thuis 2']['name'],
        "Uit_1": selected_names['Uit 1']['name'],
        "Uit_2": selected_names['Uit 2']['name'],
        "Thuis_score": home_score,
        "Uit_score": away_score
    }
    all_ELO_ratings = {}
    for player in [match["Thuis_1"], match["Thuis_2"], match["Uit_1"], match["Uit_2"]]:
        if player is not None:
            all_ELO_ratings[player] = [player_elos.get(player, 1000)]
    new_elo_df = calculate_new_elo(match, all_ELO_ratings)
    new_elos = dict(zip(new_elo_df["Speler"], new_elo_df["ELO"].astype(float)))
    return new_elos


def prepare_match_data(selected_names, home_score, away_score, match_date):
    """Bereid wedstrijd data voor om op te slaan inclusief custom datum"""
    # match_date is nu een datetime object
    # Alleen nieuwe kolomnamen opslaan
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
        'timestamp': match_date,
    }


def process_match_submission(selected_names, home_score, away_score, player_elos, match_date):
    """Proces de complete wedstrijd submissie"""
    # Valideer input
    if not validate_match_input(selected_names, home_score, away_score):
        return False

    # Bereken nieuwe ELO ratings
    new_elos = calculate_new_elos(selected_names, home_score, away_score, player_elos)

    # Bereid data voor
    match_data = prepare_match_data(selected_names, home_score, away_score, match_date)
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