import streamlit as st
import pandas as pd
import time
from datetime import date, datetime
import firestore_service as db # Use Firestore
from styles import setup_page
from utils import elo_calculation, add_name, get_download_filename
import analytics
import season_utils
import plotly.express as px
import plotly.graph_objects as go

setup_page()

st.title("Tafelvoetbal Competitie ⚽")

# --- Tab navigatie ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏠 Home", 
    "📝 Invullen", 
    "👥 Spelers", 
    "📅 Seizoenen",
    "📊 Ruwe Data", 
    "⚙️ Beheer", 
    "ℹ️ Colofon"
])

# --- Data ophalen (eenmalig) ---
players_df = db.get_players()
matches_df = db.get_matches()
seasons_df = db.get_seasons()

# --- Hulpfuncties ---
def calculate_stats(players, matches):
    """Bereken statistieken voor alle spelers"""
    stats_list = []
    for index, player in players.iterrows():
        player_name = str(player['speler_naam']) if player['speler_naam'] is not None else ""
        
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
            stats = {'Gespeeld': 0, 'Voor': 0, 'Tegen': 0, 'Doelsaldo': 0, 'Klinkers': 0, 'Speler': ""}
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

# ===== TAB 1: HOME =====
with tab1:
    st.header(":crown: ELO Rating :crown:")
    
    if players_df.empty:
        st.info("Nog geen spelers geregistreerd. Ga naar 'Spelers' om spelers toe te voegen.")
    else:
        # --- Huidige ELO rating tonen ---
        st.subheader("Huidige ELO rating van alle spelers")
        
        stats_df = calculate_stats(players_df, matches_df)
        
        # Sorteer en selecteer kolommen voor weergave
        display_df = stats_df.sort_values(by='ELO', ascending=False)
        st.dataframe(display_df[['Speler', 'ELO', 'Gespeeld', 'Voor', 'Tegen', 'Doelsaldo', 'Klinkers']], use_container_width=True)
        
        # --- ELO ontwikkeling tonen ---
        st.subheader("Ontwikkeling ELO rating per speler")
        
        player_names = sorted(players_df['speler_naam'].tolist())
        selected_player = st.selectbox("Selecteer een speler:", player_names)
        
        if selected_player:
            # Haal de ELO geschiedenis op voor de geselecteerde speler
            history_df = db.get_elo_history(_ttl=60, speler_naam=selected_player)
            
            if not history_df.empty:
                history_df['match_num'] = range(1, len(history_df) + 1)
                st.line_chart(history_df, x='match_num', y='rating')
            else:
                st.info(f"Geen ELO geschiedenis gevonden voor {selected_player}.")

# ===== TAB 2: INVULLEN =====
with tab2:
    st.header("Tafelvoetbal Competitie ⚽ — Invullen")
    
    if players_df.empty:
        st.warning("Er zijn nog geen spelers. Voeg eerst een speler toe via de 'Spelers' tab.")
    else:
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

# ===== TAB 3: SPELERS =====
with tab3:
    st.header("Voeg een speler toe")
    name = st.text_input("Vul een naam in:")
    if st.button("Voeg naam toe"):
        add_name(name)

    st.markdown("<hr />", unsafe_allow_html=True)

    st.header("Huidige spelerslijst")

    if not players_df.empty:
        # We only need the names for this table
        df_namen = players_df[['speler_naam']].rename(columns={'speler_naam': 'Huidige namen'}).sort_values(by='Huidige namen')
        st.table(df_namen)
    else:
        st.info("Geen spelers gevonden.")

# ===== TAB 4: SEIZOENEN =====
with tab4:
    st.header("📅 Seizoenen Overzicht")
    
    # Info sectie over Prinsjesdag seizoenen
    st.info("""
    🏛️ **Prinsjesdag Seizoen Systeem**
    
    Dit systeem gebruikt **Prinsjesdag** (derde dinsdag van september) als seizoensgrens:
    - **Seizoen loopt:** van Prinsjesdag vorig jaar tot Prinsjesdag dit jaar (24:00)
    - **Automatisch berekend:** voor alle jaren met wedstrijddata
    - **Traditioneel Nederlands:** gebaseerd op de opening van het parlementaire jaar
    """)
    
    # Genereer Prinsjesdag seizoenen
    prinsjesdag_seasons_df = season_utils.generate_prinsjesdag_seasons(matches_df)
    
    # Combineer database seizoenen met Prinsjesdag seizoenen
    if not prinsjesdag_seasons_df.empty:
        combined_seasons_df = prinsjesdag_seasons_df
        st.success(f"✅ {len(combined_seasons_df)} Prinsjesdag seizoenen automatisch gegenereerd met wedstrijddata")
    else:
        combined_seasons_df = pd.DataFrame()
        if matches_df.empty:
            st.info("💡 Voeg wedstrijddata toe om Prinsjesdag seizoenen te genereren.")
        else:
            st.warning("⚠️ Kon geen Prinsjesdag seizoenen genereren.")
    
    # Toon alleen Prinsjesdag data voor seizoenen met wedstrijden
    if not matches_df.empty and not combined_seasons_df.empty:
        st.subheader("🗓️ Prinsjesdag Seizoenen Met Wedstrijddata")
        
        # Maak Prinsjesdag data op basis van gegenereerde seizoenen
        prinsjesdag_info = []
        
        for _, season in combined_seasons_df.iterrows():
            try:
                year = season['jaar']
                prinsjesdag = season['prinsjesdag']
                seizoen_naam = season['seizoen_naam']
                
                # Check of er wedstrijden zijn in dit seizoen
                try:
                    # Converteer datums naar vergelijkbaar formaat (zonder timezone)
                    match_dates = pd.to_datetime(matches_df['datum']).dt.tz_localize(None).dt.date
                    season_matches = matches_df[
                        (match_dates >= season['startdatum']) & 
                        (match_dates <= season['einddatum'])
                    ]
                except Exception as date_error:
                    if not matches_df.empty:
                        st.warning(f"Probleem bij seizoen {year} datum vergelijking: {date_error}")
                    season_matches = pd.DataFrame()
                
                # Alleen tonen als er wedstrijden zijn
                if len(season_matches) > 0:
                    prinsjesdag_info.append({
                        'Jaar': year,
                        'Prinsjesdag': prinsjesdag.strftime('%d-%m-%Y (%A)'),
                        'Seizoen': seizoen_naam,
                        'Wedstrijden': len(season_matches),
                        'Status': '🏆 Actief'
                    })
            except Exception as e:
                # Skip seizoenen met fouten
                continue
        
        if prinsjesdag_info:
            prinsjesdag_df = pd.DataFrame(prinsjesdag_info)
            st.dataframe(prinsjesdag_df, use_container_width=True)
        else:
            st.info("Geen seizoenen met wedstrijddata gevonden.")
    else:
        st.info("💡 Voeg wedstrijddata toe om Prinsjesdag seizoenen te zien.")
    
    # Visualisatie van Prinsjesdag data
    if not matches_df.empty and not prinsjesdag_seasons_df.empty:
        st.subheader("📊 Prinsjesdag Seizoenen Visualisatie")
        
        # Maak timeline data
        timeline_data = []
        for _, season in prinsjesdag_seasons_df.iterrows():
            try:
                # Verbeterde datum vergelijking
                match_dates = pd.to_datetime(matches_df['datum']).dt.tz_localize(None).dt.date
                season_matches = matches_df[
                    (match_dates >= season['startdatum']) & 
                    (match_dates <= season['einddatum'])
                ]
            except Exception as viz_error:
                if not matches_df.empty:
                    st.warning(f"Visualisatie fout voor seizoen {season['seizoen_naam']}: {viz_error}")
                season_matches = pd.DataFrame()
            
            timeline_data.append({
                'Jaar': season['jaar'],
                'Prinsjesdag': season['prinsjesdag'], 
                'Wedstrijden': len(season_matches),
                'Seizoen': season['seizoen_naam']
            })
        
        timeline_df = pd.DataFrame(timeline_data)
        
        if not timeline_df.empty:
            # Wedstrijden per Prinsjesdag seizoen
            analytics.show_timeline_chart(matches_df)
    
    # Controleer of er data beschikbaar is voor analyse
    if combined_seasons_df.empty:
        st.warning("⚠️ Geen seizoenen kunnen worden gegenereerd.")
        st.info("💡 Voeg eerst wedstrijden toe om automatische Prinsjesdag seizoenen te genereren.")
    elif matches_df.empty:
        st.warning("⚠️ Geen wedstrijden gevonden voor seizoen analyse.")
        st.info("💡 Upload wedstrijddata om seizoen analyses te kunnen maken.")
    else:
        try:
            # Seizoen selectie
            st.subheader("🎯 Seizoen Selectie")
            
            # Maak seizoen opties - alleen seizoenen met wedstrijden
            season_options, current_season_id = season_utils.create_season_options(combined_seasons_df, matches_df)
            
            if not season_options:
                st.error("❌ Geen geldige seizoenen gevonden.")
            else:
                selected_season_display = st.selectbox(
                    "Kies een seizoen om te analyseren:",
                    options=[option[0] for option in season_options],
                    index=1 if current_season_id is not None else 0
                )
                
                # Vind de geselecteerde seizoen ID
                selected_season_id = next(option[1] for option in season_options if option[0] == selected_season_display)
                
                if selected_season_id == "all":
                    # Alle seizoenen analyse
                    st.subheader("📈 Overzicht Alle Prinsjesdag Seizoenen")
                    
                    # Seizoen metrics
                    metrics_df = season_utils.process_all_seasons_metrics(combined_seasons_df, matches_df)
                    
                    if not metrics_df.empty:
                        st.dataframe(metrics_df, use_container_width=True)
                        
                        # Visualisaties voor alle seizoenen met analytics module
                        analytics.show_cross_season_charts(matches_df, combined_seasons_df)
                                        title='👥 Actieve Spelers per Seizoen',
                                        color='Aantal Spelers',
                                        color_continuous_scale='Greens'
                                    )
                                    fig_players.update_layout(xaxis_tickangle=45)
                                    st.plotly_chart(fig_players, use_container_width=True)
                                except Exception as e:
                                    st.error(f"Fout bij maken van spelers chart: {e}")
                            
                            # Goals trend
                            try:
                                fig_goals = px.line(
                                    metrics_df, 
                                    x='Seizoen', 
                                    y='Gem. Doelpunten/Wedstrijd',
                                    title='⚽ Gemiddeld Doelpunten per Wedstrijd Trend',
                                    markers=True
                                )
                                fig_goals.update_layout(xaxis_tickangle=45)
                                st.plotly_chart(fig_goals, use_container_width=True)
                            except Exception as e:
                                st.error(f"Fout bij maken van goals trend: {e}")
                        
                        # UITGEBREIDE CROSS-SEIZOEN ANALYSE
                        st.markdown("---")
                        st.subheader("📊 Uitgebreide Cross-Seizoen Analyse")
                        
                        # Bereken cross-seizoen statistieken
                        all_season_players = {}  # player -> {goals, matches, wins, etc}
                        all_season_matches = pd.DataFrame()
                        
                        # Verzamel data van alle seizoenen
                        for idx, season in combined_seasons_df.iterrows():
                            try:
                                start_date = pd.to_datetime(season['startdatum'])
                                end_date = pd.to_datetime(season['einddatum'])
                                
                                # Filter matches voor dit seizoen
                                match_dates = pd.to_datetime(matches_df['datum'])
                                if match_dates.dt.tz is not None:
                                    match_dates = match_dates.dt.tz_localize(None)
                                
                                start_date_naive = pd.to_datetime(start_date)
                                if start_date_naive.tz is not None:
                                    start_date_naive = start_date_naive.tz_localize(None)
                                
                                end_date_naive = pd.to_datetime(end_date) 
                                if end_date_naive.tz is not None:
                                    end_date_naive = end_date_naive.tz_localize(None)
                                
                                season_matches = matches_df[
                                    (match_dates >= start_date_naive) & 
                                    (match_dates <= end_date_naive)
                                ].copy()
                                
                                if not season_matches.empty:
                                    season_matches['seizoen'] = season.get('seizoen_naam', f"Seizoen {start_date.year}")
                                    all_season_matches = pd.concat([all_season_matches, season_matches], ignore_index=True)
                                    
                                    # Verzamel speler statistieken
                                    for _, match in season_matches.iterrows():
                                        # Process alle spelers in deze wedstrijd
                                        players = []
                                        if pd.notna(match.get('thuis_1')):
                                            players.append((match['thuis_1'], 'thuis'))
                                        if pd.notna(match.get('thuis_2')):
                                            players.append((match['thuis_2'], 'thuis'))
                                        if pd.notna(match.get('uit_1')):
                                            players.append((match['uit_1'], 'uit'))
                                        if pd.notna(match.get('uit_2')):
                                            players.append((match['uit_2'], 'uit'))
                                        
                                        for player, team_type in players:
                                            if player not in all_season_players:
                                                all_season_players[player] = {
                                                    'total_goals': 0, 'total_matches': 0, 'total_wins': 0, 
                                                    'total_klinkers': 0, 'seizoenen': set()
                                                }
                                            
                                            # Update statistieken
                                            all_season_players[player]['total_matches'] += 1
                                            all_season_players[player]['seizoenen'].add(season.get('seizoen_naam', f"Seizoen {start_date.year}"))
                                            
                                            if team_type == 'thuis':
                                                all_season_players[player]['total_goals'] += int(match.get('thuis_score', 0))
                                                if int(match.get('thuis_score', 0)) > int(match.get('uit_score', 0)):
                                                    all_season_players[player]['total_wins'] += 1
                                                # Klinkers
                                                if player == match.get('thuis_1') and pd.notna(match.get('klinkers_thuis_1')):
                                                    all_season_players[player]['total_klinkers'] += int(match.get('klinkers_thuis_1', 0))
                                                elif player == match.get('thuis_2') and pd.notna(match.get('klinkers_thuis_2')):
                                                    all_season_players[player]['total_klinkers'] += int(match.get('klinkers_thuis_2', 0))
                                            else:  # uit
                                                all_season_players[player]['total_goals'] += int(match.get('uit_score', 0))
                                                if int(match.get('uit_score', 0)) > int(match.get('thuis_score', 0)):
                                                    all_season_players[player]['total_wins'] += 1
                                                # Klinkers
                                                if player == match.get('uit_1') and pd.notna(match.get('klinkers_uit_1')):
                                                    all_season_players[player]['total_klinkers'] += int(match.get('klinkers_uit_1', 0))
                                                elif player == match.get('uit_2') and pd.notna(match.get('klinkers_uit_2')):
                                                    all_season_players[player]['total_klinkers'] += int(match.get('klinkers_uit_2', 0))
                            except Exception:
                                continue
                        
                        # Toon Top performers across alle seizoenen
                        if all_season_players:
                            st.markdown("**🏆 All-Time Leaders (Alle Seizoenen)**")
                            
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.markdown("**🎯 Top 5 All-Time Scorers**")
                                top_scorers = sorted(all_season_players.items(), key=lambda x: x[1]['total_goals'], reverse=True)[:5]
                                for i, (player, stats) in enumerate(top_scorers, 1):
                                    emoji = "🥇🥈🥉🏅🏅"[i-1]
                                    st.write(f"{emoji} {player}: {stats['total_goals']} goals")
                            
                            with col2:
                                st.markdown("**💪 Top 5 Most Active**")
                                most_active = sorted(all_season_players.items(), key=lambda x: x[1]['total_matches'], reverse=True)[:5]
                                for i, (player, stats) in enumerate(most_active, 1):
                                    emoji = "🥇🥈🥉🏅🏅"[i-1]
                                    st.write(f"{emoji} {player}: {stats['total_matches']} wedstrijden")
                            
                            with col3:
                                st.markdown("**🏆 Top 5 Most Wins**")
                                most_wins = sorted(all_season_players.items(), key=lambda x: x[1]['total_wins'], reverse=True)[:5]
                                for i, (player, stats) in enumerate(most_wins, 1):
                                    emoji = "🥇🥈🥉🏅🏅"[i-1]
                                    st.write(f"{emoji} {player}: {stats['total_wins']} overwinningen")
                            
                            with col4:
                                st.markdown("**🎪 Top 5 Klinker Masters**")
                                most_klinkers = sorted(all_season_players.items(), key=lambda x: x[1]['total_klinkers'], reverse=True)[:5]
                                for i, (player, stats) in enumerate(most_klinkers, 1):
                                    if stats['total_klinkers'] > 0:
                                        emoji = "🥇🥈🥉🏅🏅"[i-1]
                                        st.write(f"{emoji} {player}: {stats['total_klinkers']} klinkers")
                        
                            # CROSS-SEIZOEN VISUALISATIES
                            st.markdown("**📈 Cross-Seizoen Performance Charts**")
                            
                            chart_col1, chart_col2 = st.columns(2)
                            
                            with chart_col1:
                                # All-time goals leaders chart
                                try:
                                    goals_data = [{'Speler': player, 'Totaal Goals': stats['total_goals']} 
                                                for player, stats in sorted(all_season_players.items(), 
                                                key=lambda x: x[1]['total_goals'], reverse=True)[:10]]
                                    goals_df = pd.DataFrame(goals_data)
                                    
                                    fig_all_goals = px.bar(
                                        goals_df,
                                        x='Speler',
                                        y='Totaal Goals',
                                        title='🎯 Top 10 All-Time Goal Scorers',
                                        color='Totaal Goals',
                                        color_continuous_scale='Reds'
                                    )
                                    fig_all_goals.update_layout(xaxis_tickangle=45)
                                    st.plotly_chart(fig_all_goals, use_container_width=True)
                                except Exception as e:
                                    st.error(f"Error bij all-time goals chart: {e}")
                            
                            with chart_col2:
                                # Win rate vs activity scatter
                                try:
                                    scatter_data = []
                                    for player, stats in all_season_players.items():
                                        if stats['total_matches'] >= 3:  # Min 3 matches
                                            win_rate = (stats['total_wins'] / stats['total_matches']) * 100
                                            scatter_data.append({
                                                'Speler': player,
                                                'Wedstrijden': stats['total_matches'],
                                                'Win Rate %': win_rate,
                                                'Totaal Goals': stats['total_goals']
                                            })
                                    
                                    if scatter_data:
                                        scatter_df = pd.DataFrame(scatter_data)
                                        fig_scatter = px.scatter(
                                            scatter_df,
                                            x='Wedstrijden',
                                            y='Win Rate %',
                                            size='Totaal Goals',
                                            hover_name='Speler',
                                            title='🏆 Activiteit vs Win Rate (grootte = goals)',
                                            color='Win Rate %',
                                            color_continuous_scale='RdYlBu_r'
                                        )
                                        st.plotly_chart(fig_scatter, use_container_width=True)
                                except Exception as e:
                                    st.error(f"Error bij scatter plot: {e}")
                            
                            # Seizoen vergelijking pie chart
                            try:
                                seizoen_counts = {}
                                for player, stats in all_season_players.items():
                                    for seizoen in stats['seizoenen']:
                                        seizoen_counts[seizoen] = seizoen_counts.get(seizoen, 0) + 1
                                
                                if seizoen_counts:
                                    pie_data = [{'Seizoen': k, 'Unieke Spelers': v} for k, v in seizoen_counts.items()]
                                    pie_df = pd.DataFrame(pie_data)
                                    
                                    fig_pie = px.pie(
                                        pie_df, 
                                        values='Unieke Spelers', 
                                        names='Seizoen',
                                        title='👥 Speler Distributie per Seizoen'
                                    )
                                    st.plotly_chart(fig_pie, use_container_width=True)
                            except Exception as e:
                                st.error(f"Error bij pie chart: {e}")
                        else:
                            st.info("Geen cross-seizoen data beschikbaar.")
                    else:
                        st.info("Geen seizoen data beschikbaar voor analyse.")
                
                else:
                    # Specifiek seizoen analyse
                    try:
                        season = combined_seasons_df.iloc[selected_season_id]
                        season_matches = season_utils.get_season_matches(matches_df, season)
                        
                        # Haal ELO data op voor dit seizoen (indien beschikbaar)
                        season_elo = None  # TODO: implement season ELO lookup
                        
                        # Roep de analytics functie aan
                        analytics.show_individual_season_analysis(season, season_matches, season_elo)
                        
                    except Exception as e:
                        st.error(f"Fout bij laden van seizoen data: {e}")
        
        except Exception as e:
            st.error(f"Algemene fout bij seizoen analyse: {e}")

# ===== TAB 5: RUWE DATA =====
with tab5:
    st.header("Ruwe Data uit Firestore")

    # --- Spelers ---
    st.subheader("Spelers")
    if not players_df.empty:
        st.dataframe(players_df, use_container_width=True)
    else:
        st.info("Geen spelers gevonden in Firestore.")
                            
                            with col4:
                                avg_goals = total_goals / len(season_matches)
                                st.metric("📈 Gem. Doelpunten/Wedstrijd", f"{avg_goals:.2f}")
                            
                            # Uitgebreide seizoen statistieken
                            st.markdown("---")
                            st.subheader("📈 Uitgebreide Seizoen Statistieken")
                            
                            # Bereken uitgebreide statistieken
                            goal_stats = {}
                            klinker_stats = {}
                            elo_changes = {}
                            
                            # Initialiseer statistieken voor alle spelers
                            for player in unique_players:
                                goal_stats[player] = 0
                                klinker_stats[player] = 0
                                
                            # Bereken goal en klinker statistieken
                            for _, match in season_matches.iterrows():
                                # Reguliere goals
                                if pd.notna(match.get('thuis_1')):
                                    goal_stats[match['thuis_1']] += int(match.get('thuis_score', 0))
                                if pd.notna(match.get('thuis_2')):
                                    goal_stats[match['thuis_2']] += int(match.get('thuis_score', 0))
                                if pd.notna(match.get('uit_1')):
                                    goal_stats[match['uit_1']] += int(match.get('uit_score', 0))
                                if pd.notna(match.get('uit_2')):
                                    goal_stats[match['uit_2']] += int(match.get('uit_score', 0))
                                
                                # Klinker goals
                                if pd.notna(match.get('klinkers_thuis_1')):
                                    klinker_stats[match.get('thuis_1', '')] += int(match.get('klinkers_thuis_1', 0))
                                if pd.notna(match.get('klinkers_thuis_2')):
                                    klinker_stats[match.get('thuis_2', '')] += int(match.get('klinkers_thuis_2', 0))
                                if pd.notna(match.get('klinkers_uit_1')):
                                    klinker_stats[match.get('uit_1', '')] += int(match.get('klinkers_uit_1', 0))
                                if pd.notna(match.get('klinkers_uit_2')):
                                    klinker_stats[match.get('uit_2', '')] += int(match.get('klinkers_uit_2', 0))
                            
                            # Bereken ELO veranderingen (vereenvoudigd - zou eigenlijk seizoen start/eind ELO moeten vergelijken)
                            for player in unique_players:
                                # Haal huidige ELO op
                                current_elo = 1000
                                if not players_df.empty:
                                    player_row = players_df[players_df['speler_naam'] == player]
                                    if not player_row.empty:
                                        current_elo = player_row.iloc[0].get('rating', 1000)
                                
                                # Schatting van seizoen start ELO (zou beter kunnen met ELO geschiedenis)
                                estimated_start_elo = 1000  # Simplified - zou uit ELO geschiedenis moeten komen
                                elo_changes[player] = current_elo - estimated_start_elo
                            
                            # Toon Top 3 statistieken
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.markdown("**🏆 Top 3 ELO Rating**")
                                # Haal ELO scores voor alle spelers
                                player_elos = []
                                for player in unique_players:
                                    current_elo = 1000
                                    if not players_df.empty:
                                        player_row = players_df[players_df['speler_naam'] == player]
                                        if not player_row.empty:
                                            current_elo = player_row.iloc[0].get('rating', 1000)
                                    player_elos.append((player, current_elo))
                                
                                top_elo_players = sorted(player_elos, key=lambda x: x[1], reverse=True)[:3]
                                for i, (player, elo) in enumerate(top_elo_players, 1):
                                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                                    st.write(f"{emoji} {player}: {elo:.0f} ELO")
                            
                            with col2:
                                st.markdown("**🎯 Top 3 Doelpunten Makers**")
                                top_scorers = sorted(goal_stats.items(), key=lambda x: x[1], reverse=True)[:3]
                                for i, (player, goals) in enumerate(top_scorers, 1):
                                    if goals > 0:
                                        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                                        st.write(f"{emoji} {player}: {goals} doelpunten")
                                    else:
                                        st.write(f"{i}. Geen doelpunten data")
                            
                            with col3:
                                st.markdown("**🎪 Top 3 Klinker Scorers**")
                                top_klinkers = sorted(klinker_stats.items(), key=lambda x: x[1], reverse=True)[:3]
                                for i, (player, klinkers) in enumerate(top_klinkers, 1):
                                    if klinkers > 0:
                                        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                                        st.write(f"{emoji} {player}: {klinkers} klinkers")
                                    else:
                                        st.write(f"{i}. Geen klinker data")
                            
                            with col4:
                                st.markdown("**📈 Top 3 ELO Stijging (geschat)**")
                                top_elo_gains = sorted(elo_changes.items(), key=lambda x: x[1], reverse=True)[:3]
                                for i, (player, change) in enumerate(top_elo_gains, 1):
                                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                                    sign = "+" if change >= 0 else ""
                                    st.write(f"{emoji} {player}: {sign}{change:.0f} ELO")
                                    
                                if len(top_elo_gains) == 0 or all(change == 0 for _, change in top_elo_gains):
                                    st.caption("*Vereist ELO geschiedenis data*")
                            
                            st.markdown("---")
                            
                            # Seizoen ranking berekenen
                            st.subheader("🏆 Seizoen Ranking")
                            
                            # Speler statistieken berekenen
                            season_players_stats = {}
                            for player in unique_players:
                                try:
                                    wins = 0
                                    losses = 0
                                    goals_for = 0
                                    goals_against = 0
                                    matches_played = 0
                                    
                                    for _, match in season_matches.iterrows():
                                        player_is_home = match.get('thuis_1') == player or match.get('thuis_2') == player
                                        player_is_away = match.get('uit_1') == player or match.get('uit_2') == player
                                        
                                        if player_is_home:
                                            matches_played += 1
                                            goals_for += int(match.get('thuis_score', 0))
                                            goals_against += int(match.get('uit_score', 0))
                                            if int(match.get('thuis_score', 0)) > int(match.get('uit_score', 0)):
                                                wins += 1
                                            else:
                                                losses += 1
                                        elif player_is_away:
                                            matches_played += 1
                                            goals_for += int(match.get('uit_score', 0))
                                            goals_against += int(match.get('thuis_score', 0))
                                            if int(match.get('uit_score', 0)) > int(match.get('thuis_score', 0)):
                                                wins += 1
                                            else:
                                                losses += 1
                                    
                                    # Huidige ELO score
                                    current_elo = 1000  # Default
                                    if not players_df.empty:
                                        player_row = players_df[players_df['speler_naam'] == player]
                                        if not player_row.empty:
                                            current_elo = player_row.iloc[0].get('rating', 1000)
                                    
                                    season_players_stats[player] = {
                                        'Speler': player,
                                        'Wedstrijden': matches_played,
                                        'Gewonnen': wins,
                                        'Verloren': losses,
                                        'Win %': round((wins / matches_played) * 100, 1) if matches_played > 0 else 0,
                                        'Doelpunten Voor': int(goals_for),
                                        'Doelpunten Tegen': int(goals_against),
                                        'Doelsaldo': int(goals_for - goals_against),
                                        'Huidige ELO': int(current_elo)
                                    }
                                except Exception:
                                    continue
                            
                            if season_players_stats:
                                ranking_df = pd.DataFrame(list(season_players_stats.values()))
                                ranking_df = ranking_df.sort_values(['Huidige ELO'], ascending=False).reset_index(drop=True)
                                ranking_df.index = ranking_df.index + 1  # Start ranking bij 1
                                
                                st.dataframe(ranking_df, use_container_width=True)
                                
                                # VISUALISATIES SECTIE
                                st.markdown("---")
                                st.subheader("📊 Seizoen Visualisaties")
                                
                                # Maak data voor charts
                                chart_col1, chart_col2 = st.columns(2)
                                
                                with chart_col1:
                                    # ELO Ranking Chart
                                    try:
                                        top_10_elo = ranking_df.head(10)
                                        fig_elo = px.bar(
                                            top_10_elo,
                                            x='Speler',
                                            y='Huidige ELO',
                                            title='🏆 Top 10 Spelers (ELO Rating)',
                                            color='Huidige ELO',
                                            color_continuous_scale='Blues'
                                        )
                                        fig_elo.update_layout(xaxis_tickangle=45)
                                        st.plotly_chart(fig_elo, use_container_width=True)
                                    except Exception as e:
                                        st.error(f"Fout bij ELO chart: {e}")
                                
                                with chart_col2:
                                    # Win Percentage Chart
                                    try:
                                        active_players = ranking_df[ranking_df['Wedstrijden'] >= 3]  # Min 3 wedstrijden
                                        if not active_players.empty:
                                            fig_winrate = px.bar(
                                                active_players.head(10),
                                                x='Speler',
                                                y='Win %',
                                                title='📈 Win Percentage (min. 3 wedstrijden)',
                                                color='Win %',
                                                color_continuous_scale='Greens'
                                            )
                                            fig_winrate.update_layout(xaxis_tickangle=45)
                                            st.plotly_chart(fig_winrate, use_container_width=True)
                                        else:
                                            st.info("Onvoldoende data voor win percentage chart")
                                    except Exception as e:
                                        st.error(f"Fout bij win rate chart: {e}")
                                
                                # Doelpunten statistieken
                                chart_col3, chart_col4 = st.columns(2)
                                
                                with chart_col3:
                                    # Goals per speler
                                    try:
                                        goals_data = []
                                        for player, goals in goal_stats.items():
                                            if goals > 0:  # Alleen spelers met doelpunten
                                                goals_data.append({'Speler': player, 'Doelpunten': goals})
                                        
                                        if goals_data:
                                            goals_df = pd.DataFrame(goals_data).sort_values('Doelpunten', ascending=False).head(10)
                                            fig_goals = px.bar(
                                                goals_df,
                                                x='Speler',
                                                y='Doelpunten',
                                                title='⚽ Top 10 Doelpunten Makers',
                                                color='Doelpunten',
                                                color_continuous_scale='Reds'
                                            )
                                            fig_goals.update_layout(xaxis_tickangle=45)
                                            st.plotly_chart(fig_goals, use_container_width=True)
                                        else:
                                            st.info("Geen doelpunten data beschikbaar")
                                    except Exception as e:
                                        st.error(f"Fout bij goals chart: {e}")
                                
                                with chart_col4:
                                    # Klinker goals
                                    try:
                                        klinker_data = []
                                        for player, klinkers in klinker_stats.items():
                                            if klinkers > 0:  # Alleen spelers met klinkers
                                                klinker_data.append({'Speler': player, 'Klinkers': klinkers})
                                        
                                        if klinker_data:
                                            klinker_df = pd.DataFrame(klinker_data).sort_values('Klinkers', ascending=False).head(10)
                                            fig_klinkers = px.bar(
                                                klinker_df,
                                                x='Speler',
                                                y='Klinkers',
                                                title='🎪 Top 10 Klinker Scorers',
                                                color='Klinkers',
                                                color_continuous_scale='Oranges'
                                            )
                                            fig_klinkers.update_layout(xaxis_tickangle=45)
                                            st.plotly_chart(fig_klinkers, use_container_width=True)
                                        else:
                                            st.info("Geen klinker data beschikbaar")
                                    except Exception as e:
                                        st.error(f"Fout bij klinker chart: {e}")
                                
                                # Activiteit en Performance Chart
                                try:
                                    st.markdown("**📈 Speler Activiteit vs Performance**")
                                    fig_scatter = px.scatter(
                                        ranking_df,
                                        x='Wedstrijden',
                                        y='Huidige ELO',
                                        size='Doelsaldo',
                                        color='Win %',
                                        hover_name='Speler',
                                        title='Wedstrijden vs ELO Rating (grootte = doelsaldo, kleur = win %)',
                                        color_continuous_scale='RdYlBu_r'
                                    )
                                    st.plotly_chart(fig_scatter, use_container_width=True)
                                except Exception as e:
                                    st.error(f"Fout bij scatter plot: {e}")
                                    
                            else:
                                st.info("Geen speler statistieken beschikbaar voor ranking.")
                        else:
                            st.info(f"Geen wedstrijden gevonden voor het geselecteerde seizoen.")
                    
                    except Exception as e:
                        st.error(f"Fout bij seizoen analyse: {e}")
        
        except Exception as e:
            st.error(f"❌ Algemene fout bij seizoen verwerking: {e}")
            st.info("Probeer de pagina te vernieuwen of neem contact op met de beheerder.")

# ===== TAB 5: RUWE DATA =====
with tab5:
    st.header("Ruwe Data uit Firestore")

    # --- Spelers ---
    st.subheader("Spelers")
    if not players_df.empty:
        st.dataframe(players_df, use_container_width=True)
    else:
        st.info("Geen spelers gevonden in Firestore.")

    # --- Uitslagen (Matches) ---
    st.subheader("Uitslagen (Wedstrijden)")
    st.download_button(
        label="💾 Download Uitslagen",
        data=matches_df.to_csv(index=False).encode('utf-8'),
        file_name=get_download_filename('Tafelvoetbal_Uitslagen', 'csv'),
        mime='text/csv',
    )
    st.dataframe(matches_df, use_container_width=True)

    # --- ELO Geschiedenis ---
    st.subheader("ELO Geschiedenis")
    df_elo = db.get_elo_logs()
    st.download_button(
        label="💾 Download ELO Geschiedenis",
        data=df_elo.to_csv(index=False).encode('utf-8'),
        file_name=get_download_filename('Tafelvoetbal_ELO_Geschiedenis', 'csv'),
        mime='text/csv',
    )
    st.dataframe(df_elo, use_container_width=True)

# ===== TAB 6: BEHEER =====
with tab6:
    st.header("Beheer")
    
    # --- Authenticatie ---
    goede_wachtwoord = "Klinker"
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.subheader("Login vereist")
        password = st.text_input("Voer wachtwoord in", type="password")
        if password == goede_wachtwoord:
            st.session_state.authenticated = True
            st.rerun()
        elif password:
            st.error("Ongeldig wachtwoord.")
    else:
        # --- Wedstrijd Beheer ---
        st.subheader("Wedstrijd Beheer")
        
        if not matches_df.empty:
            # Maak tabs voor verschillende beheer functies
            beheer_tab1, beheer_tab2, beheer_tab3, beheer_tab4 = st.tabs(["🗑️ Verwijderen", "✏️ Bewerken", "📁 Data Upload", "⚙️ Systeem Beheer"])
            
            with beheer_tab1:
                st.write("**Wedstrijd(en) verwijderen**")
                
                # Keuze voor ELO herberekening bij verwijdering
                elo_delete_option = st.radio(
                    "ELO herberekening bij verwijdering:",
                    options=[
                        "🔄 Automatisch herberekenen na verwijdering (aanbevolen)",
                        "⚠️ Alleen verwijderen (geen ELO update)"
                    ],
                    help="Automatische herberekening zorgt voor correcte ELO scores na verwijdering.",
                    key="elo_delete_option"
                )
                
                auto_recalc_delete = elo_delete_option.startswith("🔄")
                
                if not auto_recalc_delete:
                    st.warning("⚠️ **Let op:** Verwijderen zonder ELO herberekening kan leiden tot inconsistenties in de ratings.")
                
                # Maak een leesbare weergave voor de matches
                matches_display_df = matches_df.copy()
                matches_display_df['display'] = matches_display_df.apply(
                    lambda row: f"{pd.to_datetime(row.get('timestamp')).strftime('%d-%m-%Y %H:%M') if row.get('timestamp') else 'Geen tijd'} - {row.get('thuis_1', 'N/A')}/{row.get('thuis_2', 'N/A')} vs {row.get('uit_1', 'N/A')}/{row.get('uit_2', 'N/A')}: {row.get('thuis_score', 'N/A')}-{row.get('uit_score', 'N/A')}",
                    axis=1
                )
                
                # Optie voor enkelvoudige verwijdering
                st.write("**Enkele wedstrijd verwijderen:**")
                match_to_delete = st.selectbox(
                    "Selecteer een wedstrijd om te verwijderen",
                    options=matches_display_df['display'].tolist(),
                    key="single_match_delete"
                )
                
                if st.button("Verwijder geselecteerde wedstrijd", key="delete_single"):
                    match_idx = matches_display_df[matches_display_df['display'] == match_to_delete].index[0]
                    match_id = matches_display_df.loc[match_idx, 'match_id']
                    
                    with st.spinner("Wedstrijd wordt verwijderd..."):
                        if auto_recalc_delete:
                            success = db.delete_match_with_elo_recalculation(match_id)
                            if success:
                                st.success("Wedstrijd succesvol verwijderd en ELO scores herberekend!")
                            else:
                                st.error("Kon de wedstrijd niet verwijderen of ELO scores herberekenen.")
                        else:
                            success = db.delete_match_by_id(match_id)
                            if success:
                                st.success("Wedstrijd succesvol verwijderd.")
                                st.warning("⚠️ ELO scores zijn niet herberekend.")
                            else:
                                st.error("Kon de wedstrijd niet verwijderen.")
                        
                        if success:
                            time.sleep(1)
                            st.rerun()
                
                st.write("**Meerdere wedstrijden verwijderen:**")
                matches_to_delete = st.multiselect(
                    "Selecteer wedstrijden om te verwijderen",
                    options=matches_display_df['display'].tolist(),
                    key="multi_match_delete"
                )
                
                if matches_to_delete and st.button("Verwijder geselecteerde wedstrijden", key="delete_multiple"):
                    with st.spinner(f"Bezig met verwijderen van {len(matches_to_delete)} wedstrijden..."):
                        success_count = 0
                        deleted_match_ids = []
                        
                        # Eerst alle wedstrijden verwijderen
                        for match_display in matches_to_delete:
                            match_idx = matches_display_df[matches_display_df['display'] == match_display].index[0]
                            match_id = matches_display_df.loc[match_idx, 'match_id']
                            
                            if db.delete_match_by_id(match_id):
                                success_count += 1
                                deleted_match_ids.append(match_id)
                        
                        # Als auto herberekening is ingeschakeld en er wedstrijden zijn verwijderd
                        if auto_recalc_delete and success_count > 0:
                            with st.spinner("ELO scores worden herberekend..."):
                                # Voor bulk verwijdering: herberekenen vanaf het begin (veiligste optie)
                                db.reset_all_elos()
                        
                        if success_count == len(matches_to_delete):
                            if auto_recalc_delete:
                                st.success(f"Alle {success_count} wedstrijden succesvol verwijderd en ELO scores volledig herberekend!")
                            else:
                                st.success(f"Alle {success_count} wedstrijden succesvol verwijderd.")
                                st.warning("⚠️ ELO scores zijn niet herberekend.")
                        else:
                            st.warning(f"{success_count} van de {len(matches_to_delete)} wedstrijden verwijderd.")
                        time.sleep(1)
                        st.rerun()
            
            with beheer_tab2:
                st.write("**Wedstrijd bewerken**")
                
                # Keuze voor ELO herberekening
                elo_option = st.radio(
                    "ELO herberekening optie:",
                    options=[
                        "🔄 Automatisch herberekenen (aanbevolen)",
                        "⚠️ Alleen wedstrijd aanpassen (geen ELO update)"
                    ],
                    help="Automatische herberekening zorgt voor correcte ELO scores maar duurt langer."
                )
                
                auto_recalculate = elo_option.startswith("🔄")
                
                if not auto_recalculate:
                    st.warning("⚠️ **Let op:** Het bewerken van wedstrijden zonder ELO herberekening kan leiden tot inconsistenties in de ratings.")
                
                if not players_df.empty:
                    player_names = sorted(players_df['speler_naam'].tolist())
                    
                    # Selecteer wedstrijd om te bewerken
                    match_to_edit = st.selectbox(
                        "Selecteer een wedstrijd om te bewerken",
                        options=matches_display_df['display'].tolist(),
                        key="match_edit_select"
                    )
                    
                    if match_to_edit:
                        match_idx = matches_display_df[matches_display_df['display'] == match_to_edit].index[0]
                        match_data = matches_display_df.loc[match_idx]
                        
                        st.write("**Huidige wedstrijd gegevens:**")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Thuis team:** {match_data.get('thuis_1')} & {match_data.get('thuis_2')}")
                            st.write(f"**Thuis score:** {match_data.get('thuis_score')}")
                            st.write(f"**Klinkers thuis:** {match_data.get('klinkers_thuis_1', 0)} & {match_data.get('klinkers_thuis_2', 0)}")
                        with col2:
                            st.write(f"**Uit team:** {match_data.get('uit_1')} & {match_data.get('uit_2')}")
                            st.write(f"**Uit score:** {match_data.get('uit_score')}")
                            st.write(f"**Klinkers uit:** {match_data.get('klinkers_uit_1', 0)} & {match_data.get('klinkers_uit_2', 0)}")
                        
                        st.write("**Bewerk wedstrijd:**")
                        
                        with st.form("edit_match_form"):
                            # Speler selecties
                            edit_cols = st.columns(4)
                            with edit_cols[0]:
                                new_thuis_1 = st.selectbox("Thuis 1", player_names, 
                                                         index=player_names.index(match_data.get('thuis_1')) if match_data.get('thuis_1') in player_names else 0)
                            with edit_cols[1]:
                                new_thuis_2 = st.selectbox("Thuis 2", player_names,
                                                         index=player_names.index(match_data.get('thuis_2')) if match_data.get('thuis_2') in player_names else 1)
                            with edit_cols[2]:
                                new_uit_1 = st.selectbox("Uit 1", player_names,
                                                        index=player_names.index(match_data.get('uit_1')) if match_data.get('uit_1') in player_names else 2)
                            with edit_cols[3]:
                                new_uit_2 = st.selectbox("Uit 2", player_names,
                                                        index=player_names.index(match_data.get('uit_2')) if match_data.get('uit_2') in player_names else 3)
                            
                            # Scores
                            score_cols = st.columns(2)
                            with score_cols[0]:
                                new_thuis_score = st.number_input("Thuis Score", min_value=0, max_value=10, 
                                                                value=int(match_data.get('thuis_score', 0)), step=1)
                            with score_cols[1]:
                                new_uit_score = st.number_input("Uit Score", min_value=0, max_value=10, 
                                                               value=int(match_data.get('uit_score', 0)), step=1)
                            
                            # Klinkers
                            klinker_cols = st.columns(4)
                            with klinker_cols[0]:
                                new_klinkers_thuis_1 = st.number_input("Klinkers Thuis 1", min_value=0, max_value=10, 
                                                                     value=int(match_data.get('klinkers_thuis_1', 0)), step=1)
                            with klinker_cols[1]:
                                new_klinkers_thuis_2 = st.number_input("Klinkers Thuis 2", min_value=0, max_value=10, 
                                                                     value=int(match_data.get('klinkers_thuis_2', 0)), step=1)
                            with klinker_cols[2]:
                                new_klinkers_uit_1 = st.number_input("Klinkers Uit 1", min_value=0, max_value=10, 
                                                                   value=int(match_data.get('klinkers_uit_1', 0)), step=1)
                            with klinker_cols[3]:
                                new_klinkers_uit_2 = st.number_input("Klinkers Uit 2", min_value=0, max_value=10, 
                                                                   value=int(match_data.get('klinkers_uit_2', 0)), step=1)
                            
                            if st.form_submit_button("Bewaar wijzigingen"):
                                # Validaties
                                if new_thuis_score == 10 and new_uit_score == 10:
                                    st.error('Beide scores kunnen niet 10 zijn.')
                                elif new_thuis_score != 10 and new_uit_score != 10:
                                    st.error('Eén van de scores moet 10 zijn.')
                                elif len(set([new_thuis_1, new_thuis_2, new_uit_1, new_uit_2])) < 4:
                                    st.error("Selecteer vier unieke spelers.")
                                else:
                                    # Update wedstrijd in Firestore
                                    updated_match_data = {
                                        'thuis_1': new_thuis_1,
                                        'thuis_2': new_thuis_2,
                                        'uit_1': new_uit_1,
                                        'uit_2': new_uit_2,
                                        'thuis_score': new_thuis_score,
                                        'uit_score': new_uit_score,
                                        'klinkers_thuis_1': new_klinkers_thuis_1,
                                        'klinkers_thuis_2': new_klinkers_thuis_2,
                                        'klinkers_uit_1': new_klinkers_uit_1,
                                        'klinkers_uit_2': new_klinkers_uit_2,
                                        'timestamp': match_data.get('timestamp')  # Behoud originele timestamp
                                    }
                                    
                                    with st.spinner("Wedstrijd wordt bijgewerkt..."):
                                        if auto_recalculate:
                                            success = db.update_match_with_elo_recalculation(match_data['match_id'], updated_match_data)
                                            if success:
                                                st.success("Wedstrijd succesvol bijgewerkt en ELO scores herberekend!")
                                            else:
                                                st.error("Er is een fout opgetreden bij het bijwerken van de wedstrijd of herberekenen van ELO scores.")
                                        else:
                                            success = db.update_match(match_data['match_id'], updated_match_data)
                                            if success:
                                                st.success("Wedstrijd succesvol bijgewerkt!")
                                                st.warning("⚠️ **Belangrijk:** ELO scores zijn niet herberekend. Dit kan leiden tot inconsistenties in de ratings.")
                                            else:
                                                st.error("Er is een fout opgetreden bij het bijwerken van de wedstrijd.")
                                        
                                        if success:
                                            time.sleep(2)
                                            st.rerun()
                else:
                    st.info("Geen spelers beschikbaar om wedstrijden mee te bewerken.")
            
            with beheer_tab3:
                st.write("**Historische Data Upload**")
                st.info("📋 Upload historische wedstrijdgegevens en spelergegevens via CSV bestanden.")
                
                # Sub-tabs voor verschillende soorten data
                upload_subtab1, upload_subtab2, upload_subtab3 = st.tabs(["🏆 Wedstrijden", "👥 Spelers", "📅 Seizoenen"])
                
                with upload_subtab1:
                    st.subheader("Wedstrijdgegevens Uploaden")
                    
                    st.markdown("""
                    **📋 Vereist CSV formaat voor wedstrijden:**
                    
                    **⚠️ BELANGRIJK: Kolom volgorde moet exact overeenkomen met onderstaande tabel voor compatibiliteit met de Firestore database.**
                    
                    | Kolom # | Kolom Naam | Type | Verplicht | Beschrijving | Voorbeeld |
                    |---------|------------|------|-----------|--------------|-----------|
                    | 1 | `thuis_1` | tekst | ✅ | Naam eerste thuisspeler | "Afwasborstel" |
                    | 2 | `thuis_2` | tekst | ✅ | Naam tweede thuisspeler | "Julius Ceasar" |
                    | 3 | `uit_1` | tekst | ✅ | Naam eerste uitspeler | "Repelsteeltje" |
                    | 4 | `uit_2` | tekst | ✅ | Naam tweede uitspeler | "Chairman Xi" |
                    | 5 | `thuis_score` | getal | ✅ | Score thuisteam (0-10) | 10 |
                    | 6 | `uit_score` | getal | ✅ | Score uitteam (0-10) | 7 |
                    | 7 | `klinkers_thuis_1` | getal | ❌ | Klinkers speler 1 thuis | 2 |
                    | 8 | `klinkers_thuis_2` | getal | ❌ | Klinkers speler 2 thuis | 0 |
                    | 9 | `klinkers_uit_1` | getal | ❌ | Klinkers speler 1 uit | 1 |
                    | 10 | `klinkers_uit_2` | getal | ❌ | Klinkers speler 2 uit | 3 |
                    | 11 | `timestamp` | datum/tijd | ❌ | Wedstrijdtijdstip | Zie timestamp info ⬇️ |
                    
                    **📅 Timestamp Informatie:**
                    - **Database formaat:** `YYYY-MM-DD HH:MM:SS.ffffff+TZ` (bijv. `2025-10-28 15:42:27.614000+00:00`)
                    - **Geaccepteerde formaten:**
                      - Volledig: `2025-10-28 15:42:27.614000+00:00`
                      - Eenvoudig: `2025-10-28 15:42:27`
                      - Alleen datum: `2025-10-28` *(tijd wordt automatisch 12:00:00 UTC)*
                    - **Indien leeg:** Huidige uploadtijd wordt gebruikt
                    
                    **📝 Correct CSV Voorbeeld:**
                    ```csv
                    thuis_1,thuis_2,uit_1,uit_2,thuis_score,uit_score,klinkers_thuis_1,klinkers_thuis_2,klinkers_uit_1,klinkers_uit_2,timestamp
                    Afwasborstel,Julius Ceasar,Repelsteeltje,Chairman Xi,10,7,2,0,1,3,2025-10-28 15:42:27
                    Arthur,Rick,Lisa,Tom,8,10,1,2,4,0,2025-10-28
                    Sophie,Max,Nina,Paul,10,6,0,1,2,0,
                    ```
                    
                    **⚠️ Belangrijke opmerkingen:**
                    - Alle spelers moeten al bestaan in de database (voeg ze eerst toe via de Spelers upload)
                    - Scores moeten geldig zijn (één team moet 10 hebben, ander team 0-9)
                    - Klinkers zijn optioneel en standaard 0 indien niet opgegeven
                    - Kolom volgorde is cruciaal voor database compatibiliteit
                    """)
                    
                    uploaded_matches = st.file_uploader(
                        "📁 Upload wedstrijden CSV bestand",
                        type=["csv"],
                        key="matches_upload_main",
                        help="Upload een CSV bestand met historische wedstrijdgegevens"
                    )
                    
                    if uploaded_matches is not None:
                        try:
                            matches_upload_df = pd.read_csv(uploaded_matches)
                            
                            st.write("**Preview van geüploade data:**")
                            st.dataframe(matches_upload_df.head(10), use_container_width=True)
                            
                            # Validatie
                            required_columns = ['thuis_1', 'thuis_2', 'uit_1', 'uit_2', 'thuis_score', 'uit_score']
                            missing_columns = [col for col in required_columns if col not in matches_upload_df.columns]
                            
                            if missing_columns:
                                st.error(f"❌ Ontbrekende verplichte kolommen: {', '.join(missing_columns)}")
                            else:
                                # Optionele kolommen toevoegen als ze ontbreken
                                optional_columns = ['klinkers_thuis_1', 'klinkers_thuis_2', 'klinkers_uit_1', 'klinkers_uit_2']
                                for col in optional_columns:
                                    if col not in matches_upload_df.columns:
                                        matches_upload_df[col] = 0
                                
                                # Timestamp verwerking
                                if 'timestamp' not in matches_upload_df.columns:
                                    st.info("📅 Geen timestamp kolom gevonden - huidige tijd wordt gebruikt")
                                    matches_upload_df['timestamp'] = pd.Timestamp.now()
                                else:
                                    # Timestamp verwerking met ondersteuning voor verschillende formaten
                                    for idx in range(len(matches_upload_df)):
                                        timestamp_val = matches_upload_df.iloc[idx]['timestamp']
                                        if pd.isna(timestamp_val) or timestamp_val == '':
                                            # Leeg - gebruik huidige tijd
                                            matches_upload_df.loc[idx, 'timestamp'] = pd.Timestamp.now()
                                        else:
                                            try:
                                                # Probeer verschillende formaten te parsen
                                                timestamp_str = str(timestamp_val).strip()
                                                
                                                # Check voor alleen datum (YYYY-MM-DD)
                                                if len(timestamp_str) == 10 and timestamp_str.count('-') == 2:
                                                    # Alleen datum - voeg standaard tijd toe
                                                    parsed_ts = pd.to_datetime(timestamp_str + ' 12:00:00')
                                                else:
                                                    # Volledige timestamp
                                                    parsed_ts = pd.to_datetime(timestamp_str)
                                                
                                                matches_upload_df.loc[idx, 'timestamp'] = parsed_ts
                                            except Exception as e:
                                                st.warning(f"⚠️ Ongeldige timestamp op rij {idx + 1}: '{timestamp_val}' - huidige tijd wordt gebruikt")
                                                matches_upload_df.loc[idx, 'timestamp'] = pd.Timestamp.now()
                                
                                # Data validatie
                                validation_errors = []
                                current_players = players_df['speler_naam'].tolist() if not players_df.empty else []
                                
                                for row_idx in range(len(matches_upload_df)):
                                    row = matches_upload_df.iloc[row_idx]
                                    row_num = row_idx + 1
                                    
                                    # Check spelers bestaan
                                    players_in_match = [row['thuis_1'], row['thuis_2'], row['uit_1'], row['uit_2']]
                                    for player in players_in_match:
                                        if player not in current_players:
                                            validation_errors.append(f"Rij {row_num}: Speler '{player}' bestaat niet in database")
                                    
                                    # Check scores
                                    thuis_score = row['thuis_score']
                                    uit_score = row['uit_score']
                                    if not ((thuis_score == 10 and 0 <= uit_score <= 9) or (uit_score == 10 and 0 <= thuis_score <= 9)):
                                        validation_errors.append(f"Rij {row_num}: Ongeldige score combinatie {thuis_score}-{uit_score}")
                                    
                                    # Check unieke spelers
                                    if len(set(players_in_match)) != 4:
                                        validation_errors.append(f"Rij {row_num}: Niet alle spelers zijn uniek")
                                
                                if validation_errors:
                                    st.error("❌ **Validatie fouten gevonden:**")
                                    for error in validation_errors[:10]:  # Toon max 10 fouten
                                        st.error(f"• {error}")
                                    if len(validation_errors) > 10:
                                        st.error(f"• ... en {len(validation_errors) - 10} meer fouten")
                                else:
                                    st.success("✅ Alle data is geldig!")
                                    
                                    # ELO herberekening optie
                                    elo_recalc_option = st.radio(
                                        "ELO herberekening na upload:",
                                        options=[
                                            "🔄 Volledige ELO reset en herberekening (aanbevolen voor historische data)",
                                            "⚠️ Geen herberekening (sneller maar mogelijk inconsistent)"
                                        ],
                                        key="elo_recalc_upload"
                                    )
                                    
                                    col1, col2 = st.columns([2, 1])
                                    with col1:
                                        st.info(f"📊 **Upload samenvatting:** {len(matches_upload_df)} wedstrijden klaar voor import")
                                    
                                    with col2:
                                        if st.button("🚀 Import Wedstrijden", type="primary"):
                                            with st.spinner(f"Bezig met importeren van {len(matches_upload_df)} wedstrijden..."):
                                                matches_data = matches_upload_df.to_dict('records')
                                                added, duplicates = db.import_matches(matches_data)
                                                
                                                if elo_recalc_option.startswith("🔄") and added > 0:
                                                    with st.spinner("ELO scores worden herberekend..."):
                                                        db.reset_all_elos()
                                                
                                                st.success(f"🎉 Import voltooid! {added} wedstrijden toegevoegd, {duplicates} duplicaten genegeerd.")
                                                if elo_recalc_option.startswith("🔄"):
                                                    st.success("✅ ELO scores zijn volledig herberekend!")
                                                
                                                time.sleep(2)
                                                st.rerun()
                        
                        except Exception as e:
                            st.error(f"❌ Fout bij het verwerken van het CSV bestand: {e}")
                
                with upload_subtab2:
                    st.subheader("Spelergegevens Uploaden")
                    
                    st.markdown("""
                    **📋 Vereist CSV formaat voor spelers:**
                    
                    | Kolom | Type | Verplicht | Beschrijving | Voorbeeld |
                    |-------|------|-----------|--------------|-----------|
                    | `speler_naam` | tekst | ✅ | Naam van de speler | "Afwasborstel" |
                    | `rating` | getal | ❌ | Start ELO rating (standaard 1000) | 1050 |
                    
                    **📝 CSV Voorbeeld:**
                    ```csv
                    speler_naam,rating
                    Afwasborstel,1050
                    Julius Ceasar,980
                    Repelsteeltje,1200
                    ```
                    
                    **⚠️ Opmerkingen:**
                    - Speler namen moeten uniek zijn
                    - ELO rating is optioneel, standaard wordt 1000 gebruikt
                    - Bestaande spelers worden overgeslagen (geen duplicaten)
                    """)
                    
                    uploaded_players = st.file_uploader(
                        "📁 Upload spelers CSV bestand",
                        type=["csv"],
                        key="players_upload_main",
                        help="Upload een CSV bestand met spelergegevens"
                    )
                    
                    if uploaded_players is not None:
                        try:
                            players_upload_df = pd.read_csv(uploaded_players)
                            
                            st.write("**Preview van geüploade data:**")
                            st.dataframe(players_upload_df.head(10), use_container_width=True)
                            
                            # Validatie
                            if 'speler_naam' not in players_upload_df.columns:
                                st.error("❌ Kolom 'speler_naam' is verplicht!")
                            else:
                                # Rating kolom toevoegen als deze ontbreekt
                                if 'rating' not in players_upload_df.columns:
                                    st.info("📊 Geen rating kolom gevonden - standaard ELO 1000 wordt gebruikt")
                                    players_upload_df['rating'] = 1000
                                
                                # Validatie van namen
                                invalid_names = []
                                duplicate_names = []
                                seen_names = set()
                                
                                for row_idx in range(len(players_upload_df)):
                                    row = players_upload_df.iloc[row_idx]
                                    name = str(row['speler_naam']).strip()
                                    row_num = row_idx + 1
                                    
                                    # Check voor geldige naam
                                    if not name or not name.replace(' ', '').isalpha() or len(name) < 2 or len(name) > 50:
                                        invalid_names.append(f"Rij {row_num}: '{name}'")
                                    
                                    # Check voor duplicaten in upload
                                    if name.lower() in seen_names:
                                        duplicate_names.append(f"Rij {row_num}: '{name}'")
                                    else:
                                        seen_names.add(name.lower())
                                
                                validation_errors = []
                                if invalid_names:
                                    validation_errors.extend([f"Ongeldige naam: {name}" for name in invalid_names[:5]])
                                if duplicate_names:
                                    validation_errors.extend([f"Duplicaat in upload: {name}" for name in duplicate_names[:5]])
                                
                                if validation_errors:
                                    st.error("❌ **Validatie fouten gevonden:**")
                                    for error in validation_errors:
                                        st.error(f"• {error}")
                                else:
                                    st.success("✅ Alle spelergegevens zijn geldig!")
                                    
                                    col1, col2 = st.columns([2, 1])
                                    with col1:
                                        st.info(f"📊 **Upload samenvatting:** {len(players_upload_df)} spelers klaar voor import")
                                    
                                    with col2:
                                        if st.button("🚀 Import Spelers", type="primary"):
                                            with st.spinner(f"Bezig met importeren van {len(players_upload_df)} spelers..."):
                                                players_data = players_upload_df.to_dict('records')
                                                added, duplicates = db.import_players(players_data)
                                                
                                                st.success(f"🎉 Import voltooid! {added} spelers toegevoegd, {duplicates} bestaande spelers genegeerd.")
                                                time.sleep(2)
                                                st.rerun()
                        
                        except Exception as e:
                            st.error(f"❌ Fout bij het verwerken van het CSV bestand: {e}")
                
                with upload_subtab3:
                    st.subheader("Seizoengegevens Uploaden")
                    
                    st.markdown("""
                    **📋 Vereist CSV formaat voor seizoenen:**
                    
                    | Kolom | Type | Verplicht | Beschrijving | Voorbeeld |
                    |-------|------|-----------|--------------|-----------|
                    | `startdatum` | datum | ✅ | Start van het seizoen (YYYY-MM-DD) | "2023-01-01" |
                    | `einddatum` | datum | ✅ | Einde van het seizoen (YYYY-MM-DD) | "2023-06-30" |
                    
                    **📝 CSV Voorbeeld:**
                    ```csv
                    startdatum,einddatum
                    2023-01-01,2023-06-30
                    2023-07-01,2023-12-31
                    2024-01-01,2024-06-30
                    ```
                    
                    **⚠️ Opmerkingen:**
                    - Datums moeten in YYYY-MM-DD formaat zijn
                    - Einddatum moet na startdatum liggen
                    - Overlappende seizoenen zijn toegestaan
                    """)
                    
                    uploaded_seasons = st.file_uploader(
                        "📁 Upload seizoenen CSV bestand",
                        type=["csv"],
                        key="seasons_upload_main",
                        help="Upload een CSV bestand met seizoengegevens"
                    )
                    
                    if uploaded_seasons is not None:
                        try:
                            seasons_upload_df = pd.read_csv(uploaded_seasons)
                            
                            st.write("**Preview van geüploade data:**")
                            st.dataframe(seasons_upload_df.head(10), use_container_width=True)
                            
                            # Validatie
                            required_cols = ['startdatum', 'einddatum']
                            missing_cols = [col for col in required_cols if col not in seasons_upload_df.columns]
                            
                            if missing_cols:
                                st.error(f"❌ Ontbrekende verplichte kolommen: {', '.join(missing_cols)}")
                            else:
                                validation_errors = []
                                
                                for row_idx in range(len(seasons_upload_df)):
                                    row = seasons_upload_df.iloc[row_idx]
                                    row_num = row_idx + 1
                                    try:
                                        start_date = pd.to_datetime(row['startdatum'])
                                        end_date = pd.to_datetime(row['einddatum'])
                                        
                                        if end_date <= start_date:
                                            validation_errors.append(f"Rij {row_num}: Einddatum moet na startdatum liggen")
                                    
                                    except Exception:
                                        validation_errors.append(f"Rij {row_num}: Ongeldige datum formaat")
                                
                                if validation_errors:
                                    st.error("❌ **Validatie fouten gevonden:**")
                                    for error in validation_errors[:5]:
                                        st.error(f"• {error}")
                                else:
                                    st.success("✅ Alle seizoengegevens zijn geldig!")
                                    
                                    col1, col2 = st.columns([2, 1])
                                    with col1:
                                        st.info(f"📊 **Upload samenvatting:** {len(seasons_upload_df)} seizoenen klaar voor import")
                                    
                                    with col2:
                                        if st.button("🚀 Import Seizoenen", type="primary"):
                                            with st.spinner(f"Bezig met importeren van {len(seasons_upload_df)} seizoenen..."):
                                                seasons_data = seasons_upload_df.to_dict('records')
                                                added, duplicates = db.import_seasons(seasons_data)
                                                
                                                st.success(f"🎉 Import voltooid! {added} seizoenen toegevoegd, {duplicates} duplicaten genegeerd.")
                                                time.sleep(2)
                                                st.rerun()
                        
                        except Exception as e:
                            st.error(f"❌ Fout bij het verwerken van het CSV bestand: {e}")

            with beheer_tab4:
                st.header("⚙️ Systeem Beheer")
                
                # --- ELO Beheer ---
                st.subheader("ELO Rating Beheer")
                
                st.write("**Complete ELO Reset & Herberekening**")
                st.info("💡 Dit reset alle ELO scores naar 1000 en herberekent ze opnieuw op basis van alle wedstrijden in chronologische volgorde.")
                
                if st.button("🔄 Reset en herbereken alle ELO scores", type="secondary"):
                    with st.spinner("Alle ELO scores worden gereset en herberekend... Dit kan even duren."):
                        success = db.reset_all_elos()
                        if success:
                            st.success("✅ Alle ELO scores succesvol gereset en herberekend!")
                            st.balloons()
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("❌ Er is een fout opgetreden bij het resetten van de ELO scores.")

                st.markdown("""<hr>""", unsafe_allow_html=True)

                # --- Speler Verwijderen ---
                st.subheader("Speler Verwijderen")

                if not players_df.empty:
                    player_names = players_df['speler_naam'].tolist()
                    player_ids = players_df['speler_id'].tolist()
                    player_map = {name: id for name, id in zip(player_names, player_ids)}

                    player_to_delete = st.selectbox("Selecteer een speler om te verwijderen", options=sorted(player_names))
                    
                    if st.button(f"Verwijder {player_to_delete} Permanent"):
                        player_id_to_delete = player_map.get(player_to_delete)
                        if player_id_to_delete:
                            with st.spinner(f"Bezig met verwijderen van {player_to_delete}..."):
                                if db.delete_player_by_id(player_id_to_delete):
                                    st.success(f"{player_to_delete} en alle bijbehorende data is verwijderd.")
                                    st.rerun()
                                else:
                                    st.error(f"Kon {player_to_delete} niet verwijderen.")
                        else:
                            st.error("Kon de speler ID niet vinden.")
                else:
                    st.info("Geen spelers om te beheren.")

                st.markdown("""<hr>""", unsafe_allow_html=True)

                # --- Seizoen Verwijderen ---
                st.subheader("Seizoen Verwijderen")
                
                seasons_df = db.get_seasons()
                if not seasons_df.empty:
                    season_options = []
                    for _, season in seasons_df.iterrows():
                        season_str = f"{season['startdatum'].strftime('%Y-%m-%d')} tot {season['einddatum'].strftime('%Y-%m-%d')}"
                        season_options.append((season_str, season.name))
                    
                    if season_options:
                        season_names = [opt[0] for opt in season_options]
                        selected_season = st.selectbox("Selecteer een seizoen om te verwijderen", options=season_names)
                        
                        if st.button(f"Verwijder seizoen: {selected_season}"):
                            season_index = next(opt[1] for opt in season_options if opt[0] == selected_season)
                            season_doc_id = seasons_df.iloc[season_index].name
                            
                            with st.spinner(f"Bezig met verwijderen van seizoen..."):
                                if db.delete_season_by_id(season_doc_id):
                                    st.success(f"Seizoen {selected_season} is verwijderd.")
                                    st.rerun()
                                else:
                                    st.error("Kon het seizoen niet verwijderen.")
                else:
                    st.info("Geen seizoenen om te beheren.")

                st.markdown("""<hr>""", unsafe_allow_html=True)

                # --- Overige Entries ---
                st.subheader("Overige Database Cleanup")

                if st.button("🗑️ Verwijder alle 'Requests'", type="secondary"):
                    with st.spinner("Alle requests worden verwijderd..."):
                        if db.clear_collection('requests'):
                            st.success("Alle requests zijn succesvol verwijderd.")
                            st.rerun()
                        else:
                            st.error("Kon de requests niet verwijderen.")
                    
        else:
            st.info("Geen wedstrijden om te beheren.")
            
            # Ook data upload beschikbaar maken als er nog geen wedstrijden zijn
            st.subheader("📁 Historische Data Upload")
            st.info("💡 Geen wedstrijden gevonden. Upload historische data om te beginnen!")
            
            upload_tabs = st.tabs(["👥 Spelers", "🏆 Wedstrijden", "📅 Seizoenen"])
            
            with upload_tabs[0]:
                st.write("**Start met het uploaden van spelers voordat je wedstrijden kunt toevoegen.**")
                
            with upload_tabs[1]:
                st.write("**Voeg eerst spelers toe voordat je wedstrijden kunt uploaden.**")
                
            with upload_tabs[2]:
                st.write("**Upload seizoengegevens voor betere organisatie.**")

# ===== TAB 7: COLOFON =====
with tab7:
    st.header("Colofon")
    
    st.markdown("""
    ### 🏆 Tafelvoetbal Competitie App
    
    Deze webapp is ontwikkeld tijdens de **Hackatron van oktober 2025** door:
    
    **Team Leden:**
    - Rick
    - Bernd  
    - Dewi
    - Isis
    - Johannes
    - Arthur
    
    **Technische Details:**
    - 🐍 **Python** met Streamlit framework
    - 🔥 **Firestore** database voor data opslag
    - 🤖 **AI-assistentie** van ChatGPT, Gemini, Copilot en Perplexity voor ontwikkeling
    - 📊 **ELO rating systeem** voor speler rankings
    - 📁 **CSV import/export** functionaliteit
    
    **Features:**
    - Wedstrijd registratie en beheer
    - Automatische ELO score berekening
    - Speler en seizoen beheer
    - Historische data import
    - Real-time statistieken en rankings
    
    """)