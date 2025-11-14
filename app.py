import streamlit as st
import pandas as pd
import time
from datetime import date, datetime
import firestore_service as db # Use Firestore
from styles import setup_page
from utils import elo_calculation, add_name, get_download_filename
import plotly.express as px
import plotly.graph_objects as go
# Import nieuwe modules
from analytics import show_timeline_chart, show_cross_season_charts, show_individual_season_analysis, create_all_time_leaderboards
import season_utils  # Import hele module om functie parameters correct te kunnen gebruiken
# Import TAB modules
from tab_home import render_home_tab, calculate_stats
from tab_input import render_input_tab
from tab_players import render_players_tab
from tab_requests import render_requests_tab

setup_page()

st.title("Tafelvoetbal Competitie ⚽")

# --- Tab navigatie ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🏠 Home", 
    "📝 Invullen", 
    "👥 Spelers", 
    "📅 Seizoenen",
    "📊 Ruwe Data", 
    "⚙️ Beheer", 
    "💬 Verzoeken",
    "ℹ️ Colofon"
])

# --- Data ophalen (eenmalig) ---
players_df = db.get_players()
matches_df = db.get_matches()
seasons_df = db.get_seasons()

# ===== TAB 1: HOME =====
with tab1:
    render_home_tab(players_df, matches_df)

# ===== TAB 2: INVULLEN =====
with tab2:
    render_input_tab(players_df)

# ===== TAB 3: SPELERS =====
with tab3:
    render_players_tab(players_df)

# ===== TAB 4: SEIZOENEN =====
with tab4:
    st.header("📅 Seizoenen Overzicht")
    
    # Functie om Prinsjesdag te berekenen
    def get_prinsjesdag(year):
        """Bereken Prinsjesdag (derde dinsdag van september) voor een gegeven jaar"""
        from datetime import date, timedelta
        
        # Eerste dag van september
        first_september = date(year, 9, 1)
        
        # Vind de eerste dinsdag (weekday 1 = dinsdag)
        days_until_tuesday = (1 - first_september.weekday()) % 7
        first_tuesday = first_september + timedelta(days=days_until_tuesday)
        
        # Derde dinsdag is twee weken later
        prinsjesdag = first_tuesday + timedelta(days=14)
        
        return prinsjesdag
    
    # Genereer Prinsjesdag seizoenen op basis van wedstrijd data
    def generate_prinsjesdag_seasons():
        """Genereer automatische seizoenen op basis van Prinsjesdag"""
        prinsjesdag_seasons = []
        
        try:
            from datetime import date
            current_year = date.today().year
            
            # Bepaal jaar bereik - alleen seizoenen tot huidig jaar
            if not matches_df.empty:
                try:
                    # Converteer datum kolom naar datetime en haal timezone info weg
                    match_dates = pd.to_datetime(matches_df['datum']).dt.tz_localize(None)
                    min_year = max(2020, match_dates.min().year - 1)  # Vanaf 2020 of eerste match jaar
                    max_year = min(current_year + 1, match_dates.max().year + 1)  # Tot huidig jaar
                except Exception as date_error:
                    # Alleen waarschuwen bij daadwerkelijke data problemen
                    if not matches_df.empty:
                        st.warning(f"Probleem met datum conversie: {date_error}")
                    # Fallback naar huidige datum bereik
                    min_year = 2020
                    max_year = current_year + 1
            else:
                # Geen wedstrijden - geen seizoenen tonen
                return pd.DataFrame()
            
            for year in range(min_year, max_year + 1):
                try:
                    # Skip jaar 1900 of andere ongeldige jaren, en toekomstige jaren
                    if year < 1900 or year > current_year + 1:
                        continue
                        
                    prinsjesdag = get_prinsjesdag(year)
                    prev_prinsjesdag = get_prinsjesdag(year - 1)
                    
                    # Seizoen loopt van vorige Prinsjesdag tot huidige Prinsjesdag 24:00
                    season_start = prev_prinsjesdag
                    season_end = prinsjesdag
                    
                    prinsjesdag_seasons.append({
                        'startdatum': season_start,
                        'einddatum': season_end,
                        'seizoen_naam': f'Prinsjesdag Seizoen {year-1}-{year}',
                        'prinsjesdag': prinsjesdag,
                        'jaar': year
                    })
                except Exception as e:
                    # Log specifieke fout alleen als er wedstrijddata is - anders te veel noise
                    if not matches_df.empty:
                        st.warning(f"⚠️ Fout bij jaar {year}: {str(e)} (type: {type(e).__name__})")
                    continue
            
            return pd.DataFrame(prinsjesdag_seasons)
        
        except Exception as e:
            # Toon alleen error bij daadwerkelijk probleem met beschikbare data
            if not matches_df.empty:
                st.error(f"Algemene fout bij genereren Prinsjesdag seizoenen: {str(e)}")
                # Debug info voor troubleshooting
                st.write(f"🔍 Debug info - Error type: {type(e).__name__}")
                st.write(f"📊 Matches data shape: {matches_df.shape}")
                st.write(f"📅 Datum column type: {matches_df['datum'].dtype}")
                st.write(f"📋 Sample datum values: {matches_df['datum'].head()}")
                st.write(f"🏛️ Column names: {list(matches_df.columns)}")
            return pd.DataFrame()
    
    # Info sectie over Prinsjesdag seizoenen
    st.info("""
    🏛️ **Prinsjesdag Seizoen Systeem**
    
    Dit systeem gebruikt **Prinsjesdag** (derde dinsdag van september) als seizoensgrens:
    - **Seizoen loopt:** van Prinsjesdag 24:00 tot de volgende Prinsjesdag 24:00
    - **Automatisch berekend:** voor alle jaren met wedstrijddata
    """)
    
    # Genereer Prinsjesdag seizoenen
    prinsjesdag_seasons_df = generate_prinsjesdag_seasons()
    
    # Combineer database seizoenen met Prinsjesdag seizoenen
    if not prinsjesdag_seasons_df.empty:
        combined_seasons_df = prinsjesdag_seasons_df
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
            fig_timeline = px.bar(
                timeline_df,
                x='Jaar',
                y='Wedstrijden', 
                title='⚽ Wedstrijden per Prinsjesdag Seizoen',
                hover_data=['Seizoen', 'Prinsjesdag'],
                color='Wedstrijden',
                color_continuous_scale='Blues'
            )
            fig_timeline.update_layout(
                xaxis_title="Seizoen Jaar",
                yaxis_title="Aantal Wedstrijden"
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
    
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
            season_options = []
            current_date = date.today()
            current_season_id = None
            
            for idx, season in combined_seasons_df.iterrows():
                try:
                    start_date = pd.to_datetime(season['startdatum']).date()
                    end_date = pd.to_datetime(season['einddatum']).date()
                    # Bepaal of dit het huidige seizoen is o.b.v. huidige datum
                    is_current_season = (start_date <= current_date <= end_date)
                    
                    # Check of er wedstrijden zijn in dit seizoen
                    try:
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
                        ]
                        # Voeg toe wanneer er wedstrijden zijn OF wanneer dit het huidige seizoen is (ook als 0 wedstrijden)
                        if is_current_season or len(season_matches) > 0:
                            season_name = season.get('seizoen_naam', f"{start_date.strftime('%Y-%m-%d')} tot {end_date.strftime('%Y-%m-%d')}")
                            match_count = len(season_matches)
                            season_options.append((f"{season_name} ({match_count} wedstrijden)", idx))
                            # Onthoud het 'huidige' seizoen via de DataFrame index (idx), niet via positie in season_options
                            if is_current_season:
                                current_season_id = idx
                                
                    except Exception:
                        continue  # Skip seizoenen met datum problemen
                except Exception:
                    continue
            
            if not season_options:
                st.error("❌ Geen geldige seizoenen gevonden.")
            else:
                # Voeg "Alle seizoenen" optie toe voor algemene vergelijking
                season_options.insert(0, ("📊 Alle Seizoenen", "all"))

                # Bepaal het standaard te selecteren seizoen
                default_option_index = 0  # Fallback naar "Alle Seizoenen"
                display_options = [option[0] for option in season_options]

                if current_season_id is not None:
                    # Zoek de optie die overeenkomt met het huidige seizoen via de DataFrame index (idx)
                    for i, option in enumerate(season_options):
                        if option[1] == current_season_id:
                            original_name = option[0]
                            display_options[i] = f"⭐ Huidig: {original_name}"
                            default_option_index = i
                            break
                elif len(season_options) > 1: # Als er geen huidig seizoen is, neem de meest recente (meer dan alleen "Alle seizoenen")
                    # De meest recente is de laatste die is toegevoegd
                    default_option_index = len(season_options) - 1
                    original_name = season_options[-1][0]
                    display_options[-1] = f"🕰️ Meest Recent: {original_name}"

                selected_season_display = st.selectbox(
                    "Kies een seizoen om te analyseren:",
                    options=display_options,
                    index=default_option_index
                )

                # Vind de originele naam en de geselecteerde seizoen ID
                selected_season_id = "all" # Default
                if selected_season_display:
                    original_selected_name = selected_season_display
                    if "⭐ Huidig: " in selected_season_display:
                        original_selected_name = selected_season_display.replace("⭐ Huidig: ", "")
                    elif "🕰️ Meest Recent: " in selected_season_display:
                        # Typo fix: selected_seizoen_display -> selected_season_display
                        original_selected_name = selected_season_display.replace("🕰️ Meest Recent: ", "")

                    # Zoek de ID die bij de originele naam hoort
                    selected_season_id = next((option[1] for option in season_options if option[0] == original_selected_name), "all")
                
                if selected_season_id == "all":
                    # Alle seizoenen analyse
                    st.subheader("📈 Overzicht Alle Prinsjesdag Seizoenen")
                    
                    # Seizoen metrics
                    season_metrics = []
                    for idx, season in combined_seasons_df.iterrows():
                        try:
                            start_date = pd.to_datetime(season['startdatum'])
                            end_date = pd.to_datetime(season['einddatum'])
                            
                            # Filter wedstrijden voor dit seizoen
                            try:
                                # Zorg voor consistente timezone handling
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
                                ]
                            except Exception:
                                season_matches = pd.DataFrame()
                            
                            # Bereken metrics
                            total_matches = len(season_matches)
                            unique_players = set()
                            if total_matches > 0:
                                # Gebruik correcte kolom namen
                                for _, match in season_matches.iterrows():
                                    if pd.notna(match.get('thuis_1')):
                                        unique_players.add(match['thuis_1'])
                                    if pd.notna(match.get('thuis_2')):
                                        unique_players.add(match['thuis_2'])
                                    if pd.notna(match.get('uit_1')):
                                        unique_players.add(match['uit_1'])
                                    if pd.notna(match.get('uit_2')):
                                        unique_players.add(match['uit_2'])
                            
                            total_goals = 0
                            if total_matches > 0:
                                total_goals = season_matches['thuis_score'].sum() + season_matches['uit_score'].sum()
                            
                            avg_goals_per_match = total_goals / total_matches if total_matches > 0 else 0
                            
                            prinsjesdag_str = season['prinsjesdag'].strftime('%d-%m-%Y') if 'prinsjesdag' in season else 'N/A'
                            
                            season_metrics.append({
                                'Seizoen': season.get('seizoen_naam', f"{start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}"),
                                'Prinsjesdag': prinsjesdag_str,
                                'Aantal Wedstrijden': total_matches,
                                'Aantal Spelers': len(unique_players),
                                'Totaal Doelpunten': total_goals,
                                'Gem. Doelpunten/Wedstrijd': round(avg_goals_per_match, 2),
                                'Seizoen Actief': '✅' if start_date.date() <= current_date <= end_date.date() else '❌'
                            })
                        except Exception:
                            continue
                    
                    if season_metrics:
                        metrics_df = pd.DataFrame(season_metrics)
                        st.dataframe(metrics_df, use_container_width=True)
                        
                        # Visualisaties voor alle seizoenen
                        if len(metrics_df) > 0:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # Wedstrijden per seizoen
                                try:
                                    fig_matches = px.bar(
                                        metrics_df, 
                                        x='Seizoen', 
                                        y='Aantal Wedstrijden',
                                        title='📊 Wedstrijden per Seizoen',
                                        color='Aantal Wedstrijden',
                                        color_continuous_scale='Blues'
                                    )
                                    fig_matches.update_layout(xaxis_tickangle=45)
                                    st.plotly_chart(fig_matches, use_container_width=True)
                                except Exception as e:
                                    st.error(f"Fout bij maken van wedstrijden chart: {e}")
                            
                            with col2:
                                # Spelers per seizoen
                                try:
                                    fig_players = px.bar(
                                        metrics_df, 
                                        x='Seizoen', 
                                        y='Aantal Spelers',
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
                                        # Zorg dat alle kolommen numeriek zijn voor de scatter
                                        for col in ['Wedstrijden', 'Win Rate %', 'Totaal Goals']:
                                            scatter_df[col] = pd.to_numeric(scatter_df[col], errors='coerce')
                                        scatter_df['Size'] = scatter_df['Totaal Goals'].fillna(0).clip(lower=0)

                                        fig_scatter = px.scatter(
                                            scatter_df,
                                            x='Wedstrijden',
                                            y='Win Rate %',
                                            size='Size',
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
                        # Gebruik .loc met de index uit de tuple, niet .iloc
                        season = combined_seasons_df.loc[selected_season_id]
                        # Helper om Firestore Timestamp / string / datetime robuust naar python datetime te converteren
                        def _to_datetime(v):
                            try:
                                if hasattr(v, 'to_datetime'):
                                    v = v.to_datetime()
                                return pd.to_datetime(v).to_pydatetime()
                            except Exception:
                                return pd.to_datetime(str(v)).to_pydatetime()

                        start_dt = _to_datetime(season['startdatum'])
                        end_dt = _to_datetime(season['einddatum'])
                        today_date = date.today()
                        is_current = (start_dt.date() <= today_date <= end_dt.date())
                        analysis_end = datetime.combine(today_date, datetime.min.time()) if is_current else end_dt
                        
                        # Seizoen header met Prinsjesdag info
                        seizoen_naam = season.get('seizoen_naam', f"Seizoen {start_dt.strftime('%Y-%m-%d')} tot {end_dt.strftime('%Y-%m-%d')}")
                        st.subheader(f"📈 {seizoen_naam}")
                        # Toon gebruikte periode voor deze analyse
                        if is_current:
                            st.caption(f"🔍 Analyse periode: {start_dt.strftime('%d-%m-%Y')} t/m {today_date.strftime('%d-%m-%Y')} (tot vandaag)")
                        else:
                            st.caption(f"🔍 Analyse periode: {start_dt.strftime('%d-%m-%Y')} t/m {end_dt.strftime('%d-%m-%Y')}")
                        
                        # Prinsjesdag info
                        if 'prinsjesdag' in season:
                            prinsjesdag_dt = _to_datetime(season['prinsjesdag'])
                            st.info(f"🏛️ **Prinsjesdag {season.get('jaar', 'N/A')}:** {prinsjesdag_dt.strftime('%d %B %Y (%A)')} - Seizoen eindigt om 24:00")
                        
                        # Filter wedstrijden voor dit seizoen
                        try:
                            # Zorg voor consistente timezone handling
                            match_dates = pd.to_datetime(matches_df['datum'])
                            if match_dates.dt.tz is not None:
                                match_dates = match_dates.dt.tz_localize(None)
                            
                            # Gebruik directe timestamps (tz lokaal maken indien nodig)
                            start_date_naive = pd.to_datetime(start_dt)
                            end_date_naive = pd.to_datetime(end_dt)
                            
                            # Gebruik analysis_end voor huidige seizoen
                            season_matches = matches_df[
                                (match_dates >= start_date_naive) & 
                                (match_dates <= pd.to_datetime(analysis_end))
                            ]
                        except Exception as date_error:
                            st.error(f"Datum vergelijkingsfout: {date_error}")
                            season_matches = pd.DataFrame()
                        
                        if not season_matches.empty:
                            # Basis statistieken
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("📊 Totaal Wedstrijden", len(season_matches))
                            
                            with col2:
                                unique_players = set()
                                # Gebruik de correcte kolom namen van Firestore
                                for _, match in season_matches.iterrows():
                                    if pd.notna(match.get('thuis_1')):
                                        unique_players.add(match['thuis_1'])
                                    if pd.notna(match.get('thuis_2')):
                                        unique_players.add(match['thuis_2'])
                                    if pd.notna(match.get('uit_1')):
                                        unique_players.add(match['uit_1'])
                                    if pd.notna(match.get('uit_2')):
                                        unique_players.add(match['uit_2'])
                                st.metric("👥 Actieve Spelers", len(unique_players))
                            
                            with col3:
                                total_goals = season_matches['thuis_score'].sum() + season_matches['uit_score'].sum()
                                st.metric("⚽ Totaal Doelpunten", int(total_goals))
                            
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
                                    # Zorg voor numerieke en niet-negatieve grootte voor markers
                                    ranking_df = ranking_df.copy()
                                    ranking_df['DoelsaldoAbs'] = pd.to_numeric(ranking_df['Doelsaldo'], errors='coerce').abs().fillna(0)
                                    ranking_df['Wedstrijden'] = pd.to_numeric(ranking_df['Wedstrijden'], errors='coerce').fillna(0)
                                    ranking_df['Huidige ELO'] = pd.to_numeric(ranking_df['Huidige ELO'], errors='coerce').fillna(0)
                                    ranking_df['Win %'] = pd.to_numeric(ranking_df['Win %'], errors='coerce').fillna(0)

                                    fig_scatter = px.scatter(
                                        ranking_df,
                                        x='Wedstrijden',
                                        y='Huidige ELO',
                                        size='DoelsaldoAbs',
                                        color='Win %',
                                        hover_name='Speler',
                                        hover_data={'Doelsaldo': True},
                                        title='Wedstrijden vs ELO Rating (grootte = |doelsaldo|, kleur = win %)',
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
from tab_admin import render_admin_tab
with tab6:
    render_admin_tab(db, players_df, matches_df)

# ===== TAB 7: VERZOEKEN =====
with tab7:
    render_requests_tab()

# ===== TAB 8: COLOFON =====
with tab8:
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