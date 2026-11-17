"""
TAB 2: Input module voor tafelvoetbal app
Bevat wedstrijd invoer formulier, validatie en ELO berekeningen
"""

import streamlit as st
import time
import pandas as pd
import firestore_service as db
from utils.utils_new_elo import calculate_new_elo
from datetime import datetime, timedelta
from utils.utils import IGNORE_PLAYERS


def _find_season_for_timestamp(seasons_df, match_dt):
    """Zoekt het seizoen waarin match_dt valt, inclusief genormaliseerde eindgrens."""
    if seasons_df is None or seasons_df.empty or match_dt is None:
        return None
    m_ts = pd.Timestamp(match_dt)
    if m_ts.tzinfo is not None:
        m_ts = m_ts.tz_localize(None)
    for _, season in seasons_df.iterrows():
        s_start = pd.Timestamp(season.get('start_datum') or season.get('startdatum'))
        s_end = pd.Timestamp(season.get('eind_datum') or season.get('einddatum'))
        if s_start.tzinfo is not None:
            s_start = s_start.tz_localize(None)
        if s_end.tzinfo is not None:
            s_end = s_end.tz_localize(None)
        if s_end.hour == 0 and s_end.minute == 0 and s_end.second == 0:
            s_end = s_end.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            s_end = s_end.replace(microsecond=999999)
        if s_start <= m_ts <= s_end:
            return season
    return None


def validate_match_input(selected_names, home_score, away_score):
    """Valideer de wedstrijd invoer (scores, unieke spelers en klinkers)."""
    def is_tien(val):
        try:
            return abs(float(val) - 10) < 1e-6
        except Exception:
            return False

    try:
        h_val = float(home_score)
        a_val = float(away_score)
    except (TypeError, ValueError):
        st.error("Ongeldige score ingevuld.")
        return False

    if h_val < 0 or h_val > 10 or a_val < 0 or a_val > 10:
        st.error("Scores moeten tussen 0 en 10 liggen.")
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

    # Klinkers validatie (per team niet hoger dan het aantal teamdoelpunten)
    try:
        k_t1 = int(selected_names['Thuis 1'].get('klinkers', 0) or 0)
        k_t2 = int(selected_names['Thuis 2'].get('klinkers', 0) or 0)
        k_u1 = int(selected_names['Uit 1'].get('klinkers', 0) or 0)
        k_u2 = int(selected_names['Uit 2'].get('klinkers', 0) or 0)
    except (TypeError, ValueError):
        st.error("Ongeldig aantal klinkers ingevuld.")
        return False

    if min(k_t1, k_t2, k_u1, k_u2) < 0:
        st.error("Aantal klinkers kan niet negatief zijn.")
        return False
    if (k_t1 + k_t2) > int(round(h_val)):
        st.error("Totaal aantal klinkers van het thuisteam kan niet hoger zijn dan de thuisscore.")
        return False
    if (k_u1 + k_u2) > int(round(a_val)):
        st.error("Totaal aantal klinkers van het uitteam kan niet hoger zijn dan de uitscore.")
        return False

    return True


def calculate_new_elos(selected_names, home_score, away_score, player_elos, matches_df=None, match_date=None, seasons_df=None, elo_df=None):
    """Bereken nieuwe ELO ratings voor alle spelers binnen het juiste seizoen."""
    match = {
        "Thuis_1": selected_names['Thuis 1']['name'],
        "Thuis_2": selected_names['Thuis 2']['name'],
        "Uit_1": selected_names['Uit 1']['name'],
        "Uit_2": selected_names['Uit 2']['name'],
        "Thuis_score": home_score,
        "Uit_score": away_score,
        "klinkers_thuis_1": selected_names['Thuis 1'].get('klinkers', 0),
        "klinkers_thuis_2": selected_names['Thuis 2'].get('klinkers', 0),
        "klinkers_uit_1": selected_names['Uit 1'].get('klinkers', 0),
        "klinkers_uit_2": selected_names['Uit 2'].get('klinkers', 0)
    }

    match_counts = {}
    effective_elos = dict(player_elos) if player_elos else {}
    target_season = None

    if matches_df is not None:
        from analytics import get_vectorized_player_stats
        from utils.utils_seizoen import get_season_matches, get_current_season

        season_filtered_df = matches_df
        try:
            if seasons_df is None:
                seasons_df = db.get_seasons()
            if seasons_df is not None and not seasons_df.empty:
                if match_date is not None:
                    target_season = _find_season_for_timestamp(seasons_df, match_date)
                else:
                    target_season = get_current_season(seasons_df)
                if target_season is not None and not matches_df.empty:
                    season_filtered_df = get_season_matches(matches_df, target_season)
        except Exception:
            season_filtered_df = matches_df

        prior_season_matches = season_filtered_df
        m_ts_naive = None
        if match_date is not None:
            m_ts_naive = pd.to_datetime(match_date)
            if m_ts_naive.tzinfo is not None:
                m_ts_naive = m_ts_naive.tz_localize(None)
            if prior_season_matches is not None and not prior_season_matches.empty and 'timestamp' in prior_season_matches.columns:
                sm_ts = pd.to_datetime(prior_season_matches['timestamp'], errors='coerce', format='mixed', utc=True)
                sm_ts = db.normalize_timestamp_series(sm_ts)
                prior_season_matches = prior_season_matches[sm_ts <= m_ts_naive]

        if prior_season_matches is not None and not prior_season_matches.empty:
            stats = get_vectorized_player_stats(prior_season_matches)
            if not stats.empty:
                match_counts = dict(zip(stats['Speler'], stats['Matches']))

        # Zorg voor een schone seizoens-specifieke start-ELO (1000 voor spelers zonder eerdere potjes dit seizoen)
        if target_season is not None:
            s_start = pd.Timestamp(target_season.get('start_datum') or target_season.get('startdatum'))
            s_end = pd.Timestamp(target_season.get('eind_datum') or target_season.get('einddatum'))
            if s_start.tzinfo is not None:
                s_start = s_start.tz_localize(None)
            if s_end.tzinfo is not None:
                s_end = s_end.tz_localize(None)
            if s_end.hour == 0 and s_end.minute == 0 and s_end.second == 0:
                s_end = s_end.replace(hour=23, minute=59, second=59, microsecond=999999)
            else:
                s_end = s_end.replace(microsecond=999999)
            cutoff_ts = min(s_end, m_ts_naive) if m_ts_naive is not None else s_end

            if elo_df is None:
                try:
                    elo_df = db.get_elo_logs()
                except Exception:
                    elo_df = pd.DataFrame()

            season_elo_df = pd.DataFrame()
            if elo_df is not None and not elo_df.empty and 'timestamp' in elo_df.columns:
                e_ts = db.normalize_timestamp_series(
                    pd.to_datetime(elo_df['timestamp'], errors='coerce', format='mixed', utc=True)
                )
                mask = (e_ts >= s_start) & (e_ts <= cutoff_ts)
                if 'match_id' in elo_df.columns:
                    mask = mask & (elo_df['match_id'].fillna('').astype(str) != 'SEASON_RESET')
                season_elo_df = elo_df[mask].copy()
                if not season_elo_df.empty:
                    season_elo_df['_ts_sort'] = e_ts[mask]
                    sort_cols = ['_ts_sort'] + (['match_id'] if 'match_id' in season_elo_df.columns else [])
                    season_elo_df = season_elo_df.sort_values(sort_cols, ascending=True, kind='mergesort')

            for player in [match["Thuis_1"], match["Thuis_2"], match["Uit_1"], match["Uit_2"]]:
                if player is None:
                    continue
                if int(match_counts.get(player, 0)) == 0:
                    effective_elos[player] = 1000.0
                elif not season_elo_df.empty:
                    p_logs = season_elo_df[season_elo_df['speler_naam'] == player]
                    if not p_logs.empty:
                        effective_elos[player] = float(p_logs.iloc[-1]['rating'])

    all_ELO_ratings = {}
    for player in [match["Thuis_1"], match["Thuis_2"], match["Uit_1"], match["Uit_2"]]:
        if player is not None:
            # We voegen 'mock' history toe op basis van match_count om de K-factor correct te berekenen
            count = int(match_counts.get(player, 0))
            all_ELO_ratings[player] = [effective_elos.get(player, 1000.0)] * (count + 1)

    new_elo_df = calculate_new_elo(match, all_ELO_ratings)
    new_elos = dict(zip(new_elo_df["Speler"], new_elo_df["ELO"].astype(float)))
    return new_elos


def prepare_match_data(selected_names, home_score, away_score, match_date):
    """Bereid wedstrijd data voor om op te slaan inclusief custom datum"""
    return {
        'timestamp': match_date,
        'thuis_1': selected_names['Thuis 1']['name'],
        'thuis_2': selected_names['Thuis 2']['name'],
        'thuis_score': home_score,
        'uit_1': selected_names['Uit 1']['name'],
        'uit_2': selected_names['Uit 2']['name'],
        'uit_score': away_score,
        'klinkers_thuis_1': selected_names['Thuis 1'].get('klinkers', 0),
        'klinkers_thuis_2': selected_names['Thuis 2'].get('klinkers', 0),
        'klinkers_uit_1': selected_names['Uit 1'].get('klinkers', 0),
        'klinkers_uit_2': selected_names['Uit 2'].get('klinkers', 0),
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

    dt = pd.to_datetime(match_datetime)
    if dt.tzinfo is not None:
        dt = dt.tz_localize(None)

    matches_df_copy = matches_df.copy()
    ts_series = pd.to_datetime(matches_df_copy['timestamp'], errors='coerce')
    if ts_series.dt.tz is not None:
        ts_series = ts_series.dt.tz_localize(None)
    matches_df_copy['timestamp'] = ts_series

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

        if input_home == db_home and input_away == db_away:
            if home_score == db_home_score and away_score == db_away_score:
                return True

        if input_home == db_away and input_away == db_home:
            if home_score == db_away_score and away_score == db_home_score:
                return True

    return False


def _clear_input_form_state():
    """Reset invoervelden in session_state na succesvol opslaan zodat datum/tijd en scores verversen."""
    session_key = "wedstrijd_invoer"
    keys_to_clear = [
        f"date_{session_key}",
        f"time_{session_key}",
        f"score_thuis_{session_key}",
        f"score_uit_{session_key}",
        f"kl_Thuis 1_{session_key}",
        f"kl_Thuis 2_{session_key}",
        f"kl_Uit 1_{session_key}",
        f"kl_Uit 2_{session_key}",
    ]
    for k in keys_to_clear:
        st.session_state.pop(k, None)


def _clear_duplicate_warning_state():
    """Schoont alle tijdelijke session_state variabelen voor duplicaat-bevestiging op."""
    for key in (
        "show_duplicate_warning",
        "duplicate_match_data",
        "duplicate_elo_updates",
        "duplicate_home_score",
        "duplicate_away_score",
        "duplicate_season_reset_ts",
        "duplicate_season_reset_name",
        "duplicate_recalc_info",
        "duplicate_update_current_rating",
    ):
        st.session_state.pop(key, None)


def save_match_direct(
    match_data,
    elo_updates,
    home_score,
    away_score,
    season_reset_ts=None,
    season_reset_name=None,
    recalc_info=None,
    update_current_rating=True,
):
    """Slaat de wedstrijd op in de database en voert eventuele seizoensreset pas bij opslaan uit."""
    if season_reset_ts is not None:
        st.toast(f"Nieuw seizoen gedetecteerd: {season_reset_name or 'Nieuw seizoen'}. ELO's worden gereset naar 1000.")
        db.reset_all_elos(season_reset_ts)

    try:
        success = db.add_match_and_update_elo(
            match_data,
            elo_updates,
            update_current_rating=update_current_rating,
        )
    except db.FirestoreUnavailable as e:
        st.error("Database niet bereikbaar: mogelijk budgetlimiet bereikt.")
        with st.expander("Toon technische details"):
            st.code(str(e.details) if hasattr(e, 'details') else str(e))
        return False

    if success:
        if recalc_info is not None:
            r_start, r_end, r_naam, r_ts = recalc_info
            db.set_recalc_needed_flag(r_start, r_end, r_naam, r_ts)
            st.info(
                "ℹ️ Omdat deze wedstrijd eerder is gespeeld dan nieuwere wedstrijden in dit seizoen, "
                "worden opvolgende ELO-scores vanavond om 23:00 uur automatisch herberekend."
            )
        st.success("Uitslag en nieuwe ELO ratings succesvol opgeslagen!")
        if hasattr(db, 'is_offline') and db.is_offline():
            st.warning("De database is momenteel offline. De uitslag kon niet direct naar Firestore worden geschreven.")
        if (home_score == 10 and away_score == 0) or (home_score == 0 and away_score == 10):
            st.balloons()
        _clear_input_form_state()
        time.sleep(1)
        st.rerun()
        return True
    else:
        st.error("Er is een fout opgetreden bij het opslaan van de wedstrijd.")
        return False


def process_match_submission(
    selected_names,
    home_score,
    away_score,
    player_elos,
    match_date,
    matches_df=None,
    seasons_df=None,
    elo_df=None,
):
    """Proces de complete wedstrijd submissie met validatie, unieke tijdstempel en duplicaatcontrole."""
    if not validate_match_input(selected_names, home_score, away_score):
        return False

    # Normaliseer en ontdubbel exacte seconde-tijdstempel
    match_ts = pd.to_datetime(match_date)
    if match_ts.tzinfo is not None:
        match_ts = match_ts.tz_localize(None)
    match_dt = match_ts.to_pydatetime().replace(microsecond=0)

    if matches_df is not None and not matches_df.empty and 'timestamp' in matches_df.columns:
        all_ts = db.normalize_timestamp_series(
            pd.to_datetime(matches_df['timestamp'], errors='coerce', format='mixed', utc=True)
        ).dropna()
        existing_ts_set = {t.to_pydatetime().replace(microsecond=0) for t in all_ts}
        while match_dt in existing_ts_set:
            match_dt += timedelta(seconds=1)
    else:
        all_ts = pd.Series([], dtype='datetime64[ns]')

    pending_season_reset_ts = None
    pending_season_naam = None
    recalc_info = None
    update_current_rating = True
    effective_player_elos = dict(player_elos) if player_elos else {}

    try:
        from utils.utils_seizoen import get_season_matches
        if seasons_df is None:
            seasons_df = db.get_seasons()
        target_season = _find_season_for_timestamp(seasons_df, match_dt)
        if target_season is not None:
            s_start = pd.Timestamp(target_season.get('start_datum') or target_season.get('startdatum'))
            s_end = pd.Timestamp(target_season.get('eind_datum') or target_season.get('einddatum'))
            if s_start.tzinfo is not None:
                s_start = s_start.tz_localize(None)
            if s_end.tzinfo is not None:
                s_end = s_end.tz_localize(None)
            if s_end.hour == 0 and s_end.minute == 0 and s_end.second == 0:
                s_end = s_end.replace(hour=23, minute=59, second=59, microsecond=999999)
            else:
                s_end = s_end.replace(microsecond=999999)

            season_matches = get_season_matches(matches_df, target_season) if matches_df is not None else pd.DataFrame()
            if matches_df is not None and not matches_df.empty and season_matches.empty:
                pending_season_reset_ts = s_start
                pending_season_naam = target_season.get('seizoen_naam')
                effective_player_elos = {k: 1000.0 for k in effective_player_elos.keys()}
            elif not season_matches.empty and 'timestamp' in season_matches.columns:
                sm_ts = db.normalize_timestamp_series(
                    pd.to_datetime(season_matches['timestamp'], errors='coerce', format='mixed', utc=True)
                ).dropna()
                if (sm_ts > pd.Timestamp(match_dt)).any():
                    recalc_info = (s_start, s_end, target_season.get('seizoen_naam'), match_dt)
                    update_current_rating = False

            if not all_ts.empty and (all_ts > s_end).any():
                update_current_rating = False
    except Exception as e:
        print(f"Fout bij automatische seizoenscontrole: {e}")

    # Bereken nieuwe ELO ratings
    new_elos = calculate_new_elos(
        selected_names,
        home_score,
        away_score,
        effective_player_elos,
        matches_df,
        match_date=match_dt,
        seasons_df=seasons_df,
        elo_df=elo_df,
    )

    match_data = prepare_match_data(selected_names, home_score, away_score, match_dt)
    elo_updates = list(new_elos.items())

    # Check voor duplicaten binnen 24 uur (pas reset toepassen bij definitief opslaan!)
    if check_duplicate_match(selected_names, home_score, away_score, match_dt, matches_df):
        st.session_state.show_duplicate_warning = True
        st.session_state.duplicate_match_data = match_data
        st.session_state.duplicate_elo_updates = elo_updates
        st.session_state.duplicate_home_score = home_score
        st.session_state.duplicate_away_score = away_score
        st.session_state.duplicate_season_reset_ts = pending_season_reset_ts
        st.session_state.duplicate_season_reset_name = pending_season_naam
        st.session_state.duplicate_recalc_info = recalc_info
        st.session_state.duplicate_update_current_rating = update_current_rating
        st.rerun()
        return False

    return save_match_direct(
        match_data,
        elo_updates,
        home_score,
        away_score,
        season_reset_ts=pending_season_reset_ts,
        season_reset_name=pending_season_naam,
        recalc_info=recalc_info,
        update_current_rating=update_current_rating,
    )


def render_input_tab(players_df, matches_df=None, seasons_df=None, elo_df=None):
    """Render de complete Input tab"""
    st.header("Tafelvoetbal Competitie ⚽ — Invullen")
    st.caption(
        "Registreer hier een gespeelde 2v2-wedstrijd. Kies 4 unieke spelers, "
        "geef aan of er klinkers zijn gescoord (+15 ELO bonus per klinker) en vul de eindstand in (één team scoort 10)."
    )

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
                reset_ts = st.session_state.get("duplicate_season_reset_ts")
                reset_name = st.session_state.get("duplicate_season_reset_name")
                recalc_info = st.session_state.get("duplicate_recalc_info")
                update_curr = st.session_state.get("duplicate_update_current_rating", True)

                _clear_duplicate_warning_state()

                save_match_direct(
                    match_data,
                    elo_updates,
                    home_score,
                    away_score,
                    season_reset_ts=reset_ts,
                    season_reset_name=reset_name,
                    recalc_info=recalc_info,
                    update_current_rating=update_curr,
                )
        with col2:
            if st.button("❌ Annuleren en wijzigen"):
                _clear_duplicate_warning_state()
                st.rerun()
        st.divider()

    if players_df.empty:
        st.warning("Er zijn nog geen spelers. Voeg eerst een speler toe via de 'Spelers' tab.")
    else:
        # Filter 'Niemand' en test-spelers uit - Case-insensitive
        filtered_players_df = players_df[~players_df['speler_naam'].str.lower().str.strip().isin(IGNORE_PLAYERS)].drop_duplicates(subset=['speler_naam'], keep='first')
        
        if filtered_players_df.empty:
            st.warning("Geen geldige spelers gevonden. Voeg spelers toe via de 'Spelers' tab.")
            return

        player_names = sorted(filtered_players_df['speler_naam'].tolist())
        player_elos = filtered_players_df.set_index('speler_naam')['rating'].to_dict()


        klink = st.radio(
            "Zijn er klinkers gescoord?",
            ("Nee", "Ja"),
            help="Kies 'Ja' om per speler het aantal gescoorde klinkers in te vullen. Elke klinker levert direct +15 extra ELO-punten op!"
        )

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
                        index=i % len(player_names),
                        help="Selecteer een unieke speler (alle 4 de spelers moeten verschillend zijn)."
                    )

            if klink == "Ja":
                klinker_cols = st.columns(4)
                for i, title in enumerate(selected_names):
                    with klinker_cols[i]:
                        selected_names[title]['klinkers'] = st.number_input(
                            f"Klinkers {title}",
                            min_value=0,
                            max_value=10,
                            step=1,
                            key=f"kl_{title}_{session_key}",
                            help="Aantal klinkers gescoord door deze speler (+15 ELO bonus per klinker)."
                        )

            score_cols = st.columns(2)
            with score_cols[0]:
                home_score = st.number_input(
                    "Score Thuis:",
                    min_value=0,
                    max_value=10,
                    step=1,
                    key=f"score_thuis_{session_key}",
                    help="Eindscore van het thuisteam (0 t/m 10). Eén van beide teams moet 10 hebben."
                )
            with score_cols[1]:
                away_score = st.number_input(
                    "Score Uit:",
                    min_value=0,
                    max_value=10,
                    step=1,
                    key=f"score_uit_{session_key}",
                    help="Eindscore van het uitteam (0 t/m 10). Eén van beide teams moet 10 hebben."
                )

            from utils.utils import get_nl_now
            # Huidige datum en tijd in Nederlandse tijdzone ophalen
            now = get_nl_now()
            match_date = st.date_input("Datum van de wedstrijd", value=now.date(), key=f"date_{session_key}", help="Standaard vandaag. Kies een andere dag indien gewenst.")
            match_time = st.time_input("Tijd van de wedstrijd", value=now.time().replace(microsecond=0), key=f"time_{session_key}", help="Standaard huidige tijd. Kies een andere tijd indien gewenst.")

            if st.form_submit_button("Verstuur Uitslag"):
                match_datetime = datetime.combine(match_date, match_time)
                process_match_submission(
                    selected_names,
                    home_score,
                    away_score,
                    player_elos,
                    match_datetime,
                    matches_df,
                    seasons_df=seasons_df,
                    elo_df=elo_df,
                )