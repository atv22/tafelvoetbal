"""
TAB 2: Input module voor tafelvoetbal app
Bevat wedstrijd invoer formulier, validatie en ELO berekeningen
"""

import streamlit as st
import time
import firestore_service as db
from utils.utils_new_elo import calculate_new_elo
from datetime import datetime
from utils.utils import IGNORE_PLAYERS


def validate_match_input(selected_names, home_score, away_score):
    """Valideer de wedstrijd invoer"""
    # Score validatie (accepteer ook float 10.0)
    def is_tien(val):
        try:
            return abs(float(val) - 10) < 1e-6
        except Exception:
            return False

    if is_tien(home_score) and is_tien(away_score):
        st.error('Beide scores kunnen niet 10 zijn.')
        return False
    if not is_tien(home_score) and not is_tien(away_score):
        st.error('Eén van de scores moet 10 zijn.')
        return False
    
    # Speler uniekheid validatie
    player_list = [p['name'] for p in selected_names.values()]
    if len(set(player_list)) < 4:
        st.error("Selecteer vier unieke spelers.")
        return False
    
    return True


def calculate_new_elos(selected_names, home_score, away_score, player_elos, matches_df=None):
    """Bereken nieuwe ELO ratings voor alle spelers"""
    # Prepare match dict for new ELO calculation
    match = {
        "Thuis_1": selected_names['Thuis 1']['name'],
        "Thuis_2": selected_names['Thuis 2']['name'],
        "Uit_1": selected_names['Uit 1']['name'],
        "Uit_2": selected_names['Uit 2']['name'],
        "Thuis_score": home_score,
        "Uit_score": away_score,
        "klinkers_thuis_1": selected_names['Thuis 1']['klinkers'],
        "klinkers_thuis_2": selected_names['Thuis 2']['klinkers'],
        "klinkers_uit_1": selected_names['Uit 1']['klinkers'],
        "klinkers_uit_2": selected_names['Uit 2']['klinkers']
    }

    # Haal match counts op voor K-factor stabiliteit
    match_counts = {}
    if matches_df is not None and not matches_df.empty:
        from analytics import get_vectorized_player_stats
        stats = get_vectorized_player_stats(matches_df)
        if not stats.empty:
            match_counts = dict(zip(stats['Speler'], stats['Matches']))

    all_ELO_ratings = {}
    for player in [match["Thuis_1"], match["Thuis_2"], match["Uit_1"], match["Uit_2"]]:
        if player is not None:
            # We voegen 'mock' history toe op basis van match_count om de K-factor correct te berekenen
            count = match_counts.get(player, 0)
            all_ELO_ratings[player] = [player_elos.get(player, 1000)] * (count + 1)

    new_elo_df = calculate_new_elo(match, all_ELO_ratings)
    new_elos = dict(zip(new_elo_df["Speler"], new_elo_df["ELO"].astype(float)))
    return new_elos


def prepare_match_data(selected_names, home_score, away_score, match_date):
    """Bereid wedstrijd data voor om op te slaan inclusief custom datum"""
    # match_date is nu een datetime object
    # Alleen nieuwe kolomnamen opslaan in de juiste volgorde
    return {
        'timestamp': match_date,
        'thuis_1': selected_names['Thuis 1']['name'],
        'thuis_2': selected_names['Thuis 2']['name'],
        'thuis_score': home_score,
        'uit_1': selected_names['Uit 1']['name'],
        'uit_2': selected_names['Uit 2']['name'],
        'uit_score': away_score,
        'klinkers_thuis_1': selected_names['Thuis 1']['klinkers'],
        'klinkers_thuis_2': selected_names['Thuis 2']['klinkers'],
        'klinkers_uit_1': selected_names['Uit 1']['klinkers'],
        'klinkers_uit_2': selected_names['Uit 2']['klinkers'],
    }


def check_duplicate_match(selected_names, home_score, away_score, match_datetime, matches_df):
    """Controleert of er al een wedstrijd met exact dezelfde spelers en score is binnen 24 uur."""
    if matches_df is None or matches_df.empty:
        return False
        
    p1 = selected_names['Thuis 1']['name']
    p2 = selected_names['Thuis 2']['name']
    p3 = selected_names['Uit 1']['name']
    p4 = selected_names['Uit 2']['name']
    
    input_home = {p1, p2}
    input_away = {p3, p4}
    
    import pandas as pd
    dt = pd.to_datetime(match_datetime)
    
    # Maak een kopie om waarschuwingen te voorkomen en normaliseer timestamps
    matches_df_copy = matches_df.copy()
    matches_df_copy['timestamp'] = pd.to_datetime(matches_df_copy['timestamp'])
    
    # Check binnen 24 uur (voor en na de ingevoerde datum/tijd)
    time_diff = (matches_df_copy['timestamp'] - dt).abs()
    recent_matches = matches_df_copy[time_diff <= pd.Timedelta(hours=24)]
    
    for _, match in recent_matches.iterrows():
        db_home = {match.get('thuis_1'), match.get('thuis_2')}
        db_away = {match.get('uit_1'), match.get('uit_2')}
        
        try:
            db_home_score = int(match.get('thuis_score', 0))
            db_away_score = int(match.get('uit_score', 0))
        except (ValueError, TypeError):
            continue
        
        # 1. Exacte team match
        if input_home == db_home and input_away == db_away:
            if home_score == db_home_score and away_score == db_away_score:
                return True
                
        # 2. Omgedraaide team match (thuis is uit geworden en vice versa)
        if input_home == db_away and input_away == db_home:
            if home_score == db_away_score and away_score == db_home_score:
                return True
                
    return False


def save_match_direct(match_data, elo_updates, home_score, away_score):
    """Slaat de wedstrijd direct op in de database zonder waarschuwingen."""
    try:
        success = db.add_match_and_update_elo(match_data, elo_updates)
    except db.FirestoreUnavailable as e:
        st.error("Database niet bereikbaar: mogelijk budgetlimiet bereikt.")
        with st.expander("Toon technische details"):
            st.code(str(e.details) if hasattr(e, 'details') else str(e))
        return False
        
    if success:
        st.success("Uitslag en nieuwe ELO ratings succesvol opgeslagen!")
        if hasattr(db, 'is_offline') and db.is_offline():
            st.warning("De database is momenteel offline. De uitslag kon niet direct naar Firestore worden geschreven.")
        if (home_score == 10 and away_score == 0) or (home_score == 0 and away_score == 10):
            st.balloons()
        time.sleep(1)
        st.rerun()
        return True
    else:
        st.error("Er is een fout opgetreden bij het opslaan van de wedstrijd.")
        return False


def process_match_submission(selected_names, home_score, away_score, player_elos, match_date, matches_df=None):
    """Proces de complete wedstrijd submissie met dubbele uitslagcontrole"""
    # Valideer input
    if not validate_match_input(selected_names, home_score, away_score):
        return False

    # Bereken nieuwe ELO ratings
    new_elos = calculate_new_elos(selected_names, home_score, away_score, player_elos, matches_df)

    # Bereid data voor
    match_data = prepare_match_data(selected_names, home_score, away_score, match_date)
    elo_updates = list(new_elos.items())

    # Check voor duplicaten binnen 24 uur
    if check_duplicate_match(selected_names, home_score, away_score, match_date, matches_df):
        st.session_state.show_duplicate_warning = True
        st.session_state.duplicate_match_data = match_data
        st.session_state.duplicate_elo_updates = elo_updates
        st.session_state.duplicate_home_score = home_score
        st.session_state.duplicate_away_score = away_score
        st.rerun()
        return False

    # Opslaan in Firestore
    return save_match_direct(match_data, elo_updates, home_score, away_score)


def render_input_tab(players_df, matches_df=None):
    """Render de complete Input tab"""
    st.header("Tafelvoetbal Competitie ⚽ — Invullen")

    # Toon waarschuwing bij mogelijke dubbele wedstrijd
    if st.session_state.get("show_duplicate_warning"):
        st.warning("⚠️ **Mogelijke dubbele wedstrijd gedetecteerd!**\n\nEr is in de afgelopen 24 uur al een wedstrijd geregistreerd met exact dezelfde spelers en score. Weet je zeker dat dit een nieuwe, extra wedstrijd is?")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Ja, sla deze uitslag toch op (bewuste dubbele invoer)", type="primary"):
                match_data = st.session_state.duplicate_match_data
                elo_updates = st.session_state.duplicate_elo_updates
                home_score = st.session_state.duplicate_home_score
                away_score = st.session_state.duplicate_away_score
                
                # Opschonen waarschuwingsstate vóór het opslaan
                del st.session_state.show_duplicate_warning
                del st.session_state.duplicate_match_data
                del st.session_state.duplicate_elo_updates
                del st.session_state.duplicate_home_score
                del st.session_state.duplicate_away_score
                
                save_match_direct(match_data, elo_updates, home_score, away_score)
        with col2:
            if st.button("❌ Annuleren en wijzigen"):
                del st.session_state.show_duplicate_warning
                del st.session_state.duplicate_match_data
                del st.session_state.duplicate_elo_updates
                del st.session_state.duplicate_home_score
                del st.session_state.duplicate_away_score
                st.rerun()
        st.divider()

    if players_df.empty:
        st.warning("Er zijn nog geen spelers. Voeg eerst een speler toe via de 'Spelers' tab.")
    else:
        # Filter 'Niemand' en test-spelers uit - Case-insensitive
        filtered_players_df = players_df[~players_df['speler_naam'].str.lower().str.strip().isin(IGNORE_PLAYERS)]
        
        if filtered_players_df.empty:
            st.warning("Geen geldige spelers gevonden. Voeg spelers toe via de 'Spelers' tab.")
            return

        player_names = sorted(filtered_players_df['speler_naam'].tolist())
        player_elos = filtered_players_df.set_index('speler_naam')['rating'].to_dict()

        klink = st.radio("Zijn er klinkers gescoord?", ("Nee", "Ja"))

        selected_names = {
            'Thuis 1': {'name': None, 'klinkers': 0},
            'Thuis 2': {'name': None, 'klinkers': 0},
            'Uit 1':   {'name': None, 'klinkers': 0},
            'Uit 2':   {'name': None, 'klinkers': 0},
        }

        # Gebruik een stabiele session_key zodat Streamlit de state behoudt
        session_key = "wedstrijd_invoer"
        with st.form("formulier"):
            cols = st.columns(4)
            for i, title in enumerate(selected_names):
                with cols[i]:
                    selected_names[title]['name'] = st.selectbox(
                        title,
                        player_names,
                        key=f"sel_{title}_{session_key}",
                        index=i % len(player_names)
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

            from utils.utils import get_nl_now
            # Huidige datum en tijd in Nederlandse tijdzone ophalen
            now = get_nl_now()
            match_date = st.date_input("Datum van de wedstrijd", value=now.date(), key=f"date_{session_key}", help="Standaard vandaag. Kies een andere dag indien gewenst.")
            match_time = st.time_input("Tijd van de wedstrijd", value=now.time().replace(microsecond=0), key=f"time_{session_key}", help="Standaard huidige tijd. Kies een andere tijd indien gewenst.")

            if st.form_submit_button("Verstuur Uitslag"):
                match_datetime = datetime.combine(match_date, match_time)
                process_match_submission(selected_names, home_score, away_score, player_elos, match_datetime, matches_df)