"""
TAB 1: Home module voor tafelvoetbal app
Bevat ELO ranking tabel en speler geschiedenis functies
"""
import streamlit as st
import pandas as pd
import firestore_service as db


def calculate_stats(players, matches):
    """Bereken statistieken voor alle spelers"""
    stats_list = []
    # Detect column names for home/away players
    if not matches.empty:
        match_row = matches.iloc[0]
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
        klinkers_home = ['klinkers_thuis_1', 'klinkers_thuis_2']
        klinkers_away = ['klinkers_uit_1', 'klinkers_uit_2']
    else:
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
        klinkers_home = ['klinkers_thuis_1', 'klinkers_thuis_2']
        klinkers_away = ['klinkers_uit_1', 'klinkers_uit_2']

    for index, player in players.iterrows():
        player_name = str(player['speler_naam']) if player['speler_naam'] is not None else ""
        # Veilige filtering om KeyError te voorkomen
        conditions = []
        for col in home_cols + away_cols:
            if col in matches.columns:
                conditions.append(matches[col] == player_name)
        if not conditions:
            player_matches = pd.DataFrame()
        else:
            player_matches = matches[pd.concat(conditions, axis=1).any(axis=1)]

        if player_matches.empty:
            stats = {'Gespeeld': 0, 'Voor': 0, 'Tegen': 0, 'Doelsaldo': 0, 'Klinkers': 0, 'Win%': 0.0, 'Speler': ""}
        else:
            goals_for = 0
            goals_against = 0
            klinkers = 0
            wins = 0
            for _, match in player_matches.iterrows():
                thuis_spelers = [match.get(col) for col in home_cols]
                uit_spelers = [match.get(col) for col in away_cols]
                if player_name in thuis_spelers:
                    goals_for += int(match.get('thuis_score', 0) or 0)
                    goals_against += int(match.get('uit_score', 0) or 0)
                    if match.get('thuis_score', 0) > match.get('uit_score', 0):
                        wins += 1
                    # Klinkers
                    for i, col in enumerate(home_cols):
                        if player_name == match.get(col):
                            klinkers += int(match.get(klinkers_home[i], 0) or 0)
                elif player_name in uit_spelers:
                    goals_for += int(match.get('uit_score', 0) or 0)
                    goals_against += int(match.get('thuis_score', 0) or 0)
                    if match.get('uit_score', 0) > match.get('thuis_score', 0):
                        wins += 1
                    for i, col in enumerate(away_cols):
                        if player_name == match.get(col):
                            klinkers += int(match.get(klinkers_away[i], 0) or 0)
            gespeeld = len(player_matches)
            win_pct = (wins / gespeeld * 100) if gespeeld > 0 else 0.0
            stats = {
                'Gespeeld': gespeeld,
                'Voor': int(goals_for),
                'Tegen': int(goals_against),
                'Doelsaldo': int(goals_for - goals_against),
                'Klinkers': int(klinkers),
                'Win%': round(win_pct, 1),
                'Speler': ""  # Placeholder voor string type
            }
        stats['Speler'] = player_name
        # Veilige conversie van rating met fallback naar 1000 als default
        rating_value = player.get('rating', 1000)
        if rating_value is None or pd.isna(rating_value):
            rating_value = 1000
        stats['ELO'] = int(rating_value)
        stats_list.append(stats)
    return pd.DataFrame(stats_list)


def show_elo_rankings(players_df, matches_df):
    """Toon de huidige ELO rankings tabel"""
    # --- Filter: alleen spelers die dit seizoen gespeeld hebben ---
    from datetime import date
    import pandas as pd
    # Bepaal huidige datum
    today = date.today()
    # Zoek alle unieke seizoenen op basis van Prinsjesdag (zoals in app.py)
    def get_prinsjesdag(year):
        from datetime import date, timedelta
        first_september = date(year, 9, 1)
        days_until_tuesday = (1 - first_september.weekday()) % 7
        first_tuesday = first_september + timedelta(days=days_until_tuesday)
        prinsjesdag = first_tuesday + timedelta(days=14)
        return prinsjesdag

    # Genereer seizoenen
    if matches_df is None or matches_df.empty:
        st.info("Er zijn nog geen wedstrijden gespeeld.")
        return

    # Gebruik 'timestamp' als datumkolom
    match_dates = pd.to_datetime(matches_df['timestamp']).dt.tz_localize(None)
    min_year = max(2020, match_dates.min().year - 1)
    max_year = min(today.year + 1, match_dates.max().year + 1)
    current_season = None
    for year in range(min_year, max_year + 1):
        start = get_prinsjesdag(year - 1)
        end = get_prinsjesdag(year)
        if start <= today <= end:
            current_season = (start, end)
            break
    # Filter wedstrijden van dit seizoen
    if current_season:
        match_dates = pd.to_datetime(matches_df['timestamp']).dt.tz_localize(None).dt.date
        season_matches = matches_df[(match_dates >= current_season[0]) & (match_dates <= current_season[1])]
        # Bepaal spelers die dit seizoen gespeeld hebben
        season_players = set()
        for col in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
            if col in season_matches.columns:
                season_players.update(season_matches[col].dropna().astype(str).tolist())
        # Filter players_df op deze namen
        filtered_players_df = players_df[players_df['speler_naam'].isin(season_players)]
    else:
        filtered_players_df = players_df.iloc[0:0]  # Geen huidig seizoen

    stats_df = calculate_stats(filtered_players_df, matches_df)
    # Sorteer en selecteer kolommen voor weergave
    if stats_df.empty:
        st.info("Geen spelers hebben dit seizoen een wedstrijd gespeeld.")
        return
    display_df = stats_df.sort_values(by='ELO', ascending=False).reset_index(drop=True)
    # Top 3 lichtgroen kleuren
    def highlight_top3_lightgreen(row):
        idx = row.name
        if idx == 0:
            return ['background-color: #d4edda'] * len(row)
        elif idx == 1:
            return ['background-color: #eafaf1'] * len(row)
        elif idx == 2:
            return ['background-color: #f4fbf7'] * len(row)
        else:
            return [''] * len(row)
    # Toon de tabel met voldoende hoogte zodat alle rijen zichtbaar zijn (of met verticale scroll)
    st.dataframe(
        display_df[['Speler', 'ELO', 'Gespeeld', 'Win%', 'Voor', 'Tegen', 'Doelsaldo', 'Klinkers']]
        .style.apply(highlight_top3_lightgreen, axis=1),
        width='stretch',
        height=max(600, 40 * len(display_df))  # 40px per rij, minimaal 600px
    )


def show_elo_history_selector(players_df, matches_df=None):
    """Toon speler selectie voor ELO geschiedenis. Optioneel: alleen spelers en wedstrijden van een specifiek seizoen."""
    import pandas as pd
    if matches_df is None:
        # Standaard: alleen spelers van huidig seizoen (zoals in show_elo_rankings)
        from datetime import date
        matches_df = db.get_matches()
        today = date.today()
        def get_prinsjesdag(year):
            from datetime import date, timedelta
            first_september = date(year, 9, 1)
            days_until_tuesday = (1 - first_september.weekday()) % 7
            first_tuesday = first_september + timedelta(days=days_until_tuesday)
            prinsjesdag = first_tuesday + timedelta(days=14)
            return prinsjesdag
        if matches_df is None or matches_df.empty:
            st.info("Er zijn nog geen wedstrijden gespeeld.")
            return
        match_dates = pd.to_datetime(matches_df['timestamp']).dt.tz_localize(None)
        min_year = max(2020, match_dates.min().year - 1)
        max_year = min(today.year + 1, match_dates.max().year + 1)
        current_season = None
        for year in range(min_year, max_year + 1):
            start = get_prinsjesdag(year - 1)
            end = get_prinsjesdag(year)
            if start <= today <= end:
                current_season = (start, end)
                break
        if current_season:
            match_dates = pd.to_datetime(matches_df['timestamp']).dt.tz_localize(None).dt.date
            season_matches = matches_df[(match_dates >= current_season[0]) & (match_dates <= current_season[1])]
            season_players = set()
            for col in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
                if col in season_matches.columns:
                    season_players.update(season_matches[col].dropna().astype(str).tolist())
            filtered_players_df = players_df[players_df['speler_naam'].isin(season_players)]
        else:
            filtered_players_df = players_df.iloc[0:0]
        player_names = sorted(filtered_players_df['speler_naam'].tolist())
        # Gebruik een unieke key gebaseerd op het id van matches_df indien aanwezig
        key = None
        if matches_df is not None:
            key = f"elo_select_{id(matches_df)}"
        if not player_names:
            st.info("Er zijn nog geen spelers met gespeelde wedstrijden.")
            return
        selected_player = st.selectbox("Selecteer een speler:", player_names, key=key)
        if selected_player:
            # Haal de ELO geschiedenis op voor de geselecteerde speler
            history_df = db.get_elo_history(_ttl=60, speler_naam=selected_player)
            if history_df is None or history_df.empty:
                st.info(f"Geen ELO geschiedenis gevonden voor {selected_player}.")
                return
            history_df['match_num'] = range(1, len(history_df) + 1)
            st.line_chart(history_df, x='match_num', y='rating')
    else:
        # Gebruik alleen spelers en wedstrijden van het opgegeven matches_df (bijv. specifiek seizoen)
        if matches_df is None or matches_df.empty:
            st.info("Geen wedstrijden in dit seizoen.")
            return
        # Bepaal spelers die in deze matches_df voorkomen
        season_players = set()
        for col in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
            if col in matches_df.columns:
                season_players.update(matches_df[col].dropna().astype(str).tolist())
        filtered_players_df = players_df[players_df['speler_naam'].isin(season_players)]
        player_names = sorted(filtered_players_df['speler_naam'].tolist())
        if not player_names:
            st.info("Er zijn nog geen spelers met gespeelde wedstrijden in dit seizoen.")
            return
        selected_player = st.selectbox("Selecteer een speler:", player_names)
        if selected_player:
            # Haal de ELO geschiedenis op voor de geselecteerde speler, filter op dit seizoen
            history_df = db.get_elo_history(_ttl=60, speler_naam=selected_player)
            if history_df is None or history_df.empty:
                st.info(f"Geen ELO geschiedenis gevonden voor {selected_player}.")
                return
            # Filter op alleen wedstrijden in dit seizoen
            match_ids = set(matches_df['wedstrijd_id'].astype(str)) if 'wedstrijd_id' in matches_df.columns else set()
            if match_ids:
                history_df = history_df[history_df['wedstrijd_id'].astype(str).isin(match_ids)]
            history_df = history_df.reset_index(drop=True)
            if history_df.empty:
                st.info(f"Geen ELO geschiedenis voor {selected_player} in dit seizoen.")
                return
            history_df['match_num'] = range(1, len(history_df) + 1)
            st.line_chart(history_df, x='match_num', y='rating')


def render_home_tab(players_df, matches_df):
    """Render de complete Home tab"""
    st.header(":crown: ELO Rating :crown:")

    if players_df is None or players_df.empty:
        st.info("Nog geen spelers geregistreerd. Ga naar 'Spelers' om spelers toe te voegen.")
        return

    # --- Huidig seizoen bepalen ---
    from firestore_service import get_seasons
    import datetime
    seasons_df = get_seasons()
    today = datetime.date.today()
    huidig_seizoen = None
    if not seasons_df.empty:
        for _, row in seasons_df.iterrows():
            start = pd.to_datetime(row['startdatum']).date()
            end = pd.to_datetime(row['einddatum']).date()
            if start <= today <= end:
                huidig_seizoen = row
                break
    if huidig_seizoen is not None:
        st.markdown(f"**Huidig seizoen:** {huidig_seizoen['seizoen_naam']}  ")
        st.markdown(f"Periode: {pd.to_datetime(huidig_seizoen['startdatum']).strftime('%d-%m-%Y %H:%M')} t/m {pd.to_datetime(huidig_seizoen['einddatum']).strftime('%d-%m-%Y %H:%M')}")
        # Filter wedstrijden op huidig seizoen
        start = pd.to_datetime(huidig_seizoen['startdatum'])
        end = pd.to_datetime(huidig_seizoen['einddatum'])
        matches_df = matches_df[(matches_df['timestamp'] >= start) & (matches_df['timestamp'] <= end)]
    else:
        st.markdown("**Geen huidig seizoen gevonden.**")

    # --- Huidige ELO rating tonen (alleen huidig seizoen) ---
    st.subheader("Huidige ELO rating van alle spelers (huidig seizoen)")
    show_elo_rankings(players_df, matches_df)