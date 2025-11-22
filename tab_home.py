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
        if 'thuis_speler_1' in match_row:
            home_cols = ['thuis_speler_1', 'thuis_speler_2']
            away_cols = ['uit_speler_1', 'uit_speler_2']
            klinkers_home = ['klinkers_thuis_1', 'klinkers_thuis_2']
            klinkers_away = ['klinkers_uit_1', 'klinkers_uit_2']
        else:
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
            stats = {'Gespeeld': 0, 'Voor': 0, 'Tegen': 0, 'Doelsaldo': 0, 'Klinkers': 0, 'Speler': ""}
        else:
            goals_for = 0
            goals_against = 0
            klinkers = 0
            for _, match in player_matches.iterrows():
                thuis_spelers = [match.get(col) for col in home_cols]
                uit_spelers = [match.get(col) for col in away_cols]
                if player_name in thuis_spelers:
                    goals_for += int(match.get('thuis_score', 0) or 0)
                    goals_against += int(match.get('uit_score', 0) or 0)
                    # Klinkers
                    for i, col in enumerate(home_cols):
                        if player_name == match.get(col):
                            klinkers += int(match.get(klinkers_home[i], 0) or 0)
                elif player_name in uit_spelers:
                    goals_for += int(match.get('uit_score', 0) or 0)
                    goals_against += int(match.get('thuis_score', 0) or 0)
                    for i, col in enumerate(away_cols):
                        if player_name == match.get(col):
                            klinkers += int(match.get(klinkers_away[i], 0) or 0)
            stats = {
                'Gespeeld': len(player_matches),
                'Voor': int(goals_for),
                'Tegen': int(goals_against),
                'Doelsaldo': int(goals_for - goals_against),
                'Klinkers': int(klinkers),
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
    if not matches_df.empty:
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
    else:
        filtered_players_df = players_df.iloc[0:0]

    stats_df = calculate_stats(filtered_players_df, matches_df)
    # Sorteer en selecteer kolommen voor weergave
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
    if not display_df.empty:
        st.dataframe(
            display_df[['Speler', 'ELO', 'Gespeeld', 'Voor', 'Tegen', 'Doelsaldo', 'Klinkers']]
            .style.apply(highlight_top3_lightgreen, axis=1),
            width='stretch'
        )
    else:
        st.info("Geen spelers hebben dit seizoen een wedstrijd gespeeld.")


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
        if not matches_df.empty:
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
        else:
            filtered_players_df = players_df.iloc[0:0]
        player_names = sorted(filtered_players_df['speler_naam'].tolist())
        # Gebruik een unieke key gebaseerd op het id van matches_df indien aanwezig
        key = None
        if matches_df is not None:
            key = f"elo_select_{id(matches_df)}"
        selected_player = st.selectbox("Selecteer een speler:", player_names, key=key)
        if selected_player:
            # Haal de ELO geschiedenis op voor de geselecteerde speler
            history_df = db.get_elo_history(_ttl=60, speler_naam=selected_player)
            if not history_df.empty:
                history_df['match_num'] = range(1, len(history_df) + 1)
                st.line_chart(history_df, x='match_num', y='rating')
            else:
                st.info(f"Geen ELO geschiedenis gevonden voor {selected_player}.")
    else:
        # Gebruik alleen spelers en wedstrijden van het opgegeven matches_df (bijv. specifiek seizoen)
        if matches_df.empty:
            st.info("Geen wedstrijden in dit seizoen.")
            return
        # Bepaal spelers die in deze matches_df voorkomen
        season_players = set()
        for col in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
            if col in matches_df.columns:
                season_players.update(matches_df[col].dropna().astype(str).tolist())
        filtered_players_df = players_df[players_df['speler_naam'].isin(season_players)]
        player_names = sorted(filtered_players_df['speler_naam'].tolist())
        selected_player = st.selectbox("Selecteer een speler:", player_names)
        if selected_player:
            # Haal de ELO geschiedenis op voor de geselecteerde speler, filter op dit seizoen
            history_df = db.get_elo_history(_ttl=60, speler_naam=selected_player)
            if not history_df.empty:
                # Filter op alleen wedstrijden in dit seizoen
                match_ids = set(matches_df['wedstrijd_id'].astype(str)) if 'wedstrijd_id' in matches_df.columns else set()
                if match_ids:
                    history_df = history_df[history_df['wedstrijd_id'].astype(str).isin(match_ids)]
                history_df = history_df.reset_index(drop=True)
                history_df['match_num'] = range(1, len(history_df) + 1)
                if not history_df.empty:
                    st.line_chart(history_df, x='match_num', y='rating')
                else:
                    st.info(f"Geen ELO geschiedenis voor {selected_player} in dit seizoen.")
            else:
                st.info(f"Geen ELO geschiedenis gevonden voor {selected_player}.")


def render_home_tab(players_df, matches_df):
    """Render de complete Home tab"""
    st.header(":crown: ELO Rating :crown:")
    
    if players_df.empty:
        st.info("Nog geen spelers geregistreerd. Ga naar 'Spelers' om spelers toe te voegen.")
    else:
        # --- Huidige ELO rating tonen ---
        st.subheader("Huidige ELO rating van alle spelers")
        show_elo_rankings(players_df, matches_df)

        # --- Activiteit vs Win Rate (alleen huidig seizoen) ---
        from datetime import date
        import pandas as pd
        import plotly.express as px
        today = date.today()
        def get_prinsjesdag(year):
            from datetime import date, timedelta
            first_september = date(year, 9, 1)
            days_until_tuesday = (1 - first_september.weekday()) % 7
            first_tuesday = first_september + timedelta(days=days_until_tuesday)
            prinsjesdag = first_tuesday + timedelta(days=14)
            return prinsjesdag
        if not matches_df.empty:
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
                # Bepaal spelers die dit seizoen gespeeld hebben
                season_players = set()
                for col in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
                    if col in season_matches.columns:
                        season_players.update(season_matches[col].dropna().astype(str).tolist())
                filtered_players_df = players_df[players_df['speler_naam'].isin(season_players)]
                # Stats per speler
                stats = []
                for _, player in filtered_players_df.iterrows():
                    name = player['speler_naam']
                    player_matches = pd.DataFrame()
                    conditions = []
                    for col in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
                        if col in season_matches.columns:
                            conditions.append(season_matches[col] == name)
                    if conditions:
                        player_matches = season_matches[pd.concat(conditions, axis=1).any(axis=1)]
                    matches_played = len(player_matches)
                    wins = 0
                    goals = 0
                    for _, match in player_matches.iterrows():
                        player_is_home = match.get('thuis_1') == name or match.get('thuis_2') == name
                        player_is_away = match.get('uit_1') == name or match.get('uit_2') == name
                        if player_is_home:
                            if int(match.get('thuis_score', 0)) > int(match.get('uit_score', 0)):
                                wins += 1
                            goals += int(match.get('thuis_score', 0))
                        elif player_is_away:
                            if int(match.get('uit_score', 0)) > int(match.get('thuis_score', 0)):
                                wins += 1
                            goals += int(match.get('uit_score', 0))
                    win_rate = (wins / matches_played) * 100 if matches_played > 0 else 0
                    stats.append({
                        'Speler': name,
                        'Wedstrijden': matches_played,
                        'Win Rate %': win_rate,
                        'Goals': goals
                    })
                df_stats = pd.DataFrame(stats)
                if not df_stats.empty:
                    st.subheader("Activiteit vs Win Rate (huidig seizoen)")
                    fig = px.scatter(
                        df_stats,
                        x='Wedstrijden',
                        y='Win Rate %',
                        size='Goals',
                        hover_name='Speler',
                        title='Activiteit vs Win Rate (huidig seizoen)',
                        color='Win Rate %',
                        color_continuous_scale='Greens',
                        size_max=18
                    )
                    st.plotly_chart(fig, config={'responsive': True})