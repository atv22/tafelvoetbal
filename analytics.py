"""
Analytics en visualisatie functies voor de tafelvoetbal app
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict


def show_timeline_chart(matches_df):
    """Toon een timeline chart van wedstrijden"""
    if not matches_df.empty:
        matches_per_day = matches_df.groupby(matches_df['timestamp'].dt.date).size()
        fig_timeline = px.bar(
            x=matches_per_day.index,
            y=matches_per_day.values,
            labels={'x': 'Datum', 'y': 'Aantal wedstrijden'},
            title="Wedstrijden per dag",
            color_discrete_sequence=['#1f77b4']
        )
        fig_timeline.update_layout(
            xaxis_title="Datum",
            yaxis_title="Aantal wedstrijden",
            showlegend=False
        )
        st.plotly_chart(fig_timeline, config={'responsive': True}, key="timeline_chart")



def show_unique_players_bar_chart(season_matches):
    """Toon een bar chart van unieke spelers per dag"""
    daily_players = defaultdict(set)
    # Detect home/away columns
    if not season_matches.empty:
        match_row = season_matches.iloc[0]
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    else:
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    for _, match in season_matches.iterrows():
        day = match['timestamp'].date()
        daily_players[day].update([
            match.get(home_cols[0], None), match.get(home_cols[1], None),
            match.get(away_cols[0], None), match.get(away_cols[1], None)
        ])
    daily_unique = {day: len([p for p in players if p is not None]) for day, players in daily_players.items()}
    daily_df = pd.DataFrame(list(daily_unique.items()), columns=['Datum', 'Unieke spelers'])
    
    fig_players = px.bar(
        daily_df,
        x='Datum',
        y='Unieke spelers',
        title="Unieke spelers per dag",
        color_discrete_sequence=['#ff7f0e']
    )
    fig_players.update_layout(xaxis_title="Datum", yaxis_title="Unieke spelers")
    st.plotly_chart(fig_players, config={'responsive': True}, key="unique_players_bar_chart")




def show_all_time_goals_chart(all_matches):
    """Toon all-time goals chart voor alle seizoenen"""
    all_goals = defaultdict(int)
    
    # Detect home/away columns
    if not all_matches.empty:
        match_row = all_matches.iloc[0]
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    else:
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    for _, match in all_matches.iterrows():
        # Thuis team goals
        for col in home_cols:
            player = match.get(col, None)
            if player is not None:
                all_goals[player] += match['thuis_score']
        # Uit team goals
        for col in away_cols:
            player = match.get(col, None)
            if player is not None:
                all_goals[player] += match['uit_score']
    
    goals_df = pd.DataFrame(list(all_goals.items()), columns=['Speler', 'Goals']).sort_values('Goals', ascending=False)
    
    if not goals_df.empty:
        fig_all_goals = px.bar(
            goals_df.head(10),
            x='Speler',
            y='Goals',
            title="Top 10 All-time Topscorers",
            color='Goals',
            color_continuous_scale='viridis'
        )
        fig_all_goals.update_layout(xaxis_title="Speler", yaxis_title="Goals")
        st.plotly_chart(fig_all_goals, config={'responsive': True}, key="all_time_goals_chart")


def show_activity_vs_winrate_scatter(all_matches, key_suffix=None):
    """Toon scatter plot van activiteit vs winpercentage, omvang bol = aantal goals, kleur = aantal wins"""
    player_stats = defaultdict(lambda: {'matches': 0, 'wins': 0, 'goals': 0})
    if not all_matches.empty:
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    else:
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    for _, match in all_matches.iterrows():
        home_players = [match.get(home_cols[0], None), match.get(home_cols[1], None)]
        away_players = [match.get(away_cols[0], None), match.get(away_cols[1], None)]
        for player in home_players:
            if player is not None:
                player_stats[player]['matches'] += 1
                player_stats[player]['goals'] += match['thuis_score']
                if match['thuis_score'] > match['uit_score']:
                    player_stats[player]['wins'] += 1
        for player in away_players:
            if player is not None:
                player_stats[player]['matches'] += 1
                player_stats[player]['goals'] += match['uit_score']
                if match['uit_score'] > match['thuis_score']:
                    player_stats[player]['wins'] += 1
    scatter_data = []
    for player, stats in player_stats.items():
        if stats['matches'] >= 5:
            win_rate = (stats['wins'] / stats['matches']) * 100
            scatter_data.append({
                'Speler': player,
                'Wedstrijden': stats['matches'],
                'Winpercentage': win_rate,
                'Goals': stats['goals'],
                'Wins': stats['wins']
            })
    if scatter_data:
        scatter_df = pd.DataFrame(scatter_data)
        fig_scatter = px.scatter(
            scatter_df,
            x='Wedstrijden',
            y='Winpercentage',
            size='Goals',
            color='Wins',
            color_continuous_scale='Blues',
            text='Speler',
            title="Activiteit vs Winpercentage (min. 5 wedstrijden)",
            hover_data=['Speler', 'Wedstrijden', 'Winpercentage', 'Goals', 'Wins']
        )
        fig_scatter.update_traces(textposition="top center")
        fig_scatter.update_layout(xaxis_title="Aantal Wedstrijden", yaxis_title="Winpercentage (%)")
        chart_key = f"activity_vs_winrate_scatter_{key_suffix}" if key_suffix else "activity_vs_winrate_scatter"
        st.plotly_chart(fig_scatter, config={'responsive': True}, key=chart_key)


def show_season_distribution_pie(seasons_df):
    """Toon pie chart van seizoen distributie"""
    if not seasons_df.empty and 'aantal_wedstrijden' in seasons_df.columns:
        # Detect season name column
        if 'seizoen_naam' in seasons_df.columns:
            name_col = 'seizoen_naam'
        elif 'seizoen' in seasons_df.columns:
            name_col = 'seizoen'
        else:
            name_col = seasons_df.columns[0]
        fig_pie = px.pie(
            seasons_df,
            values='aantal_wedstrijden',
            names=name_col,
            title="Distributie wedstrijden per seizoen"
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, config={'responsive': True}, key="season_distribution_pie")


def show_elo_bar_chart(season_elo):
    """Toon ELO bar chart voor een specifiek seizoen"""
    if not season_elo.empty:
        fig_elo = px.bar(
            season_elo.head(10),
            x='speler_naam',
            y='elo_rating',
            title="Top 10 ELO Ratings",
            color='elo_rating',
            color_continuous_scale='viridis'
        )
        fig_elo.update_layout(xaxis_title="Speler", yaxis_title="ELO Rating")
        st.plotly_chart(fig_elo, config={'responsive': True}, key="elo_bar_chart")


def show_winrate_bar_chart(season_matches, min_matches=5):
    """Toon winpercentage bar chart voor een specifiek seizoen"""
    player_stats = defaultdict(lambda: {'matches': 0, 'wins': 0})
    
    # Detect home/away columns
    if not season_matches.empty:
        match_row = season_matches.iloc[0]
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    else:
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    for _, match in season_matches.iterrows():
        home_players = [match.get(home_cols[0], None), match.get(home_cols[1], None)]
        away_players = [match.get(away_cols[0], None), match.get(away_cols[1], None)]
        for player in home_players:
            if player is not None:
                player_stats[player]['matches'] += 1
                if match['thuis_score'] > match['uit_score']:
                    player_stats[player]['wins'] += 1
        for player in away_players:
            if player is not None:
                player_stats[player]['matches'] += 1
                if match['uit_score'] > match['thuis_score']:
                    player_stats[player]['wins'] += 1
    
    winrate_data = []
    for player, stats in player_stats.items():
        if stats['matches'] >= min_matches:
            win_rate = (stats['wins'] / stats['matches']) * 100
            winrate_data.append({
                'Speler': player,
                'Winpercentage': win_rate,
                'Wedstrijden': stats['matches']
            })
    
    if winrate_data:
        winrate_df = pd.DataFrame(winrate_data).sort_values('Winpercentage', ascending=False)
        fig_winrate = px.bar(
            winrate_df.head(10),
            x='Speler',
            y='Winpercentage',
            title=f"Top 10 Winpercentages (min. {min_matches} wedstrijden)",
            color='Winpercentage',
            color_continuous_scale='RdYlGn'
        )
        fig_winrate.update_layout(xaxis_title="Speler", yaxis_title="Winpercentage (%)")
        st.plotly_chart(fig_winrate, config={'responsive': True}, key="winrate_bar_chart")


def show_goals_bar_chart_season(season_matches):
    """Toon goals bar chart voor een specifiek seizoen"""
    goals_stats = defaultdict(int)
    
    # Detect home/away columns
    if not season_matches.empty:
        match_row = season_matches.iloc[0]
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    else:
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    for _, match in season_matches.iterrows():
        # Thuis team goals
        for col in home_cols:
            player = match.get(col, None)
            if player is not None:
                goals_stats[player] += match['thuis_score']
        # Uit team goals
        for col in away_cols:
            player = match.get(col, None)
            if player is not None:
                goals_stats[player] += match['uit_score']
    
    goals_data = [{'Speler': player, 'Goals': goals} for player, goals in goals_stats.items()]
    if goals_data:
        goals_df = pd.DataFrame(goals_data).sort_values('Goals', ascending=False)
        fig_goals = px.bar(
            goals_df.head(10),
            x='Speler',
            y='Goals',
            title="Top 10 Topscorers",
            color='Goals',
            color_continuous_scale='Blues'
        )
        fig_goals.update_layout(xaxis_title="Speler", yaxis_title="Goals")
        st.plotly_chart(fig_goals, config={'responsive': True}, key="goals_bar_chart_season")


def create_all_time_leaderboards(all_matches):
    """Maak alle all-time leaderboards"""
    
    # Statistieken verzamelen
    player_stats = defaultdict(lambda: {
        'matches': 0,
        'wins': 0, 
        'goals': 0,
        'max_elo': 1000,  # Start ELO
        'klinkers': 0     # Totaal aantal klinkers
    })
    
    # Detect home/away columns
    if not all_matches.empty:
        match_row = all_matches.iloc[0]
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    else:
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    for _, match in all_matches.iterrows():
        home_players = [match.get(home_cols[0], None), match.get(home_cols[1], None)]
        away_players = [match.get(away_cols[0], None), match.get(away_cols[1], None)]
        # Home team stats
        for idx, player in enumerate(home_players):
            if player is not None:
                player_stats[player]['matches'] += 1
                player_stats[player]['goals'] += match['thuis_score']
                if match['thuis_score'] > match['uit_score']:
                    player_stats[player]['wins'] += 1
                # ELO tracking (zou uit ELO historie moeten komen, maar we schatten)
                klinker_col = f'klinkers_thuis_{idx+1}'
                if klinker_col in match:
                    player_stats[player]['klinkers'] += match.get(klinker_col, 0) or 0
                if klinker_col in match and match[klinker_col] and player == match.get(home_cols[idx], None):
                    estimated_elo = 1000 + (player_stats[player]['wins'] * 20)
                    player_stats[player]['max_elo'] = max(player_stats[player]['max_elo'], estimated_elo)
        # Away team stats
        for idx, player in enumerate(away_players):
            if player is not None:
                player_stats[player]['matches'] += 1
                player_stats[player]['goals'] += match['uit_score']
                if match['uit_score'] > match['thuis_score']:
                    player_stats[player]['wins'] += 1
                klinker_col = f'klinkers_uit_{idx+1}'
                if klinker_col in match:
                    player_stats[player]['klinkers'] += match.get(klinker_col, 0) or 0
                if klinker_col in match and match[klinker_col] and player == match.get(away_cols[idx], None):
                    estimated_elo = 1000 + (player_stats[player]['wins'] * 20)
                    player_stats[player]['max_elo'] = max(player_stats[player]['max_elo'], estimated_elo)
    
    return player_stats


def show_all_time_leaderboards(player_stats):
    """Toon alle all-time leaderboards, inclusief winpercentage en goal difference"""
    st.subheader("🏆 All-time Ranglijsten")

    # Data voorbereiden
    top_scorers = sorted(player_stats.items(), key=lambda x: x[1]['goals'], reverse=True)[:5]
    df_scorers = pd.DataFrame([
        {"#": i, "Speler": player, "Goals": stats['goals']} for i, (player, stats) in enumerate(top_scorers, 1)
    ])

    most_active = sorted(player_stats.items(), key=lambda x: x[1]['matches'], reverse=True)[:5]
    df_active = pd.DataFrame([
        {"#": i, "Speler": player, "Wedstrijden": stats['matches']} for i, (player, stats) in enumerate(most_active, 1)
    ])

    most_wins = sorted(player_stats.items(), key=lambda x: x[1]['wins'], reverse=True)[:5]
    df_wins = pd.DataFrame([
        {"#": i, "Speler": player, "Overwinningen": stats['wins']} for i, (player, stats) in enumerate(most_wins, 1)
    ])

    klinker_masters = sorted(player_stats.items(), key=lambda x: x[1]['max_elo'], reverse=True)[:5]
    df_klinkers = pd.DataFrame([
        {"#": i, "Speler": player, "Hoogste ELO": stats['max_elo'], "Klinkers totaal": stats['klinkers']} for i, (player, stats) in enumerate(klinker_masters, 1)
    ])

    # Nieuw: hoogste winpercentage (min 20 wedstrijden)
    win_pct_list = []
    for player, stats in player_stats.items():
        if stats['matches'] >= 20:
            win_pct = (stats['wins'] / stats['matches']) * 100 if stats['matches'] > 0 else 0
            win_pct_list.append((player, win_pct, stats['matches']))
    top_win_pct = sorted(win_pct_list, key=lambda x: x[1], reverse=True)[:5]
    df_win_pct = pd.DataFrame([
        {"#": i, "Speler": player, "Win%": f"{win_pct:.1f}", "Wedstrijden": matches} for i, (player, win_pct, matches) in enumerate(top_win_pct, 1)
    ])

    # Nieuw: beste goals per match (min 20 wedstrijden)
    goals_per_match_list = []
    for player, stats in player_stats.items():
        if stats['matches'] >= 20:
            gpm = stats['goals'] / stats['matches'] if stats['matches'] > 0 else 0
            goals_per_match_list.append((player, gpm, stats['matches']))
    top_gpm = sorted(goals_per_match_list, key=lambda x: x[1], reverse=True)[:5]
    df_gpm = pd.DataFrame([
        {"#": i, "Speler": player, "Goals/Wedstrijd": f"{gpm:.2f}", "Wedstrijden": matches} for i, (player, gpm, matches) in enumerate(top_gpm, 1)
    ])

    # Toon zes tabellen in 2 rijen van 3 kolommen
    row1 = st.columns(3)
    row2 = st.columns(3)
    with row1[0]:
        st.write("**🥅 Top 5 All-time Topscorers:**")
        st.dataframe(df_scorers, hide_index=True, use_container_width=True)
    with row1[1]:
        st.write("**⚽ Top 5 Meest Actief:**")
        st.dataframe(df_active, hide_index=True, use_container_width=True)
    with row1[2]:
        st.write("**🏅 Top 5 Meeste Overwinningen:**")
        st.dataframe(df_wins, hide_index=True, use_container_width=True)
    with row2[0]:
        st.write("**🎯 Top 5 Klinker Masters (hoogste ELO):**")
        st.dataframe(df_klinkers, hide_index=True, use_container_width=True)
    with row2[1]:
        st.write("**📈 Top 5 Hoogste Winpercentage (min. 20 wedstrijden):**")
        st.dataframe(df_win_pct, hide_index=True, use_container_width=True)
    with row2[2]:
        st.write("**🚀 Top 5 Goals per Wedstrijd (min. 20 wedstrijden):**")
        st.dataframe(df_gpm, hide_index=True, use_container_width=True)


def show_cross_season_charts(all_matches, seasons_df):
    """Toon cross-seizoen analyse charts"""
    import streamlit as st
    import pandas as pd
    from collections import defaultdict

    if all_matches.empty:
        return
    st.subheader("📊 Cross-Seizoen Analyses")
    # ELO ontwikkeling over seizoenen (geschatte versie)
    player_season_elo = defaultdict(lambda: defaultdict(int))
    player_season_matches = defaultdict(lambda: defaultdict(int))

    # Detect column names for start/end date and season name
    if not seasons_df.empty:
        season_row = seasons_df.iloc[0]
        start_col = 'start_datum' if 'start_datum' in season_row else 'startdatum'
        end_col = 'eind_datum' if 'eind_datum' in season_row else 'einddatum'
        if 'seizoen_naam' in season_row:
            name_col = 'seizoen_naam'
        elif 'seizoen' in season_row:
            name_col = 'seizoen'
        else:
            name_col = seasons_df.columns[0]  # fallback to first column
    else:
        start_col = 'start_datum'
        end_col = 'eind_datum'
        name_col = 'seizoen_naam'

    # Detect player column names
    if not all_matches.empty:
        match_row = all_matches.iloc[0]
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    else:
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']

    for _, match in all_matches.iterrows():
        match_date = pd.to_datetime(match['timestamp']).tz_localize(None)
        # Vind seizoen voor deze wedstrijd
        current_season = "Onbekend"
        for _, season in seasons_df.iterrows():
            season_start = pd.to_datetime(season[start_col]).tz_localize(None)
            season_end = pd.to_datetime(season[end_col]).tz_localize(None)
            if season_start <= match_date <= season_end:
                current_season = season[name_col]
                break
        # Track matches per seizoen
        home_players = [match[col] for col in home_cols]
        away_players = [match[col] for col in away_cols]
        for player in home_players + away_players:
            player_season_matches[player][current_season] += 1
    # Seizoen vergelijking chart
    if len(seasons_df) > 1:
        season_comparison = []
        for _, season in seasons_df.iterrows():
            season_comparison.append({
                'Seizoen': season[name_col],
                'Gem. Goals': season.get('gemiddelde_goals', 0)
            })
        if season_comparison:
            comparison_df = pd.DataFrame(season_comparison)
            if 'Gem. Goals' in comparison_df.columns and comparison_df['Gem. Goals'].sum() > 0:
                fig_season_goals = px.line(
                    comparison_df,
                    x='Seizoen',
                    y='Gem. Goals',
                    title="Gemiddelde Goals per Seizoen",
                    markers=True
                )
                st.plotly_chart(fig_season_goals, config={'responsive': True}, key="cross_season_goals_chart")


def show_individual_season_analysis(season_info, season_matches, season_elo=None):
    """Toon uitgebreide analyse voor een individueel seizoen"""
    import streamlit as st
    
    if season_matches.empty:
        st.warning("Geen wedstrijden gevonden voor dit seizoen.")
        return
    
    # Seizoen header
    seizoen_naam = season_info.get('seizoen_naam') or season_info.get('seizoen') or 'Onbekend Seizoen'
    st.subheader(f"📈 {seizoen_naam}")
    
    # Prinsjesdag info
    if 'prinsjesdag' in season_info:
        import pandas as pd
        prinsjesdag = pd.to_datetime(season_info['prinsjesdag'])
        st.info(f"🏛️ **Prinsjesdag {season_info.get('seizoen_jaar', 'N/A')}:** {prinsjesdag.strftime('%d %B %Y (%A)')} - Seizoen eindigt om 24:00")
    
    # Basis statistieken
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Totaal Wedstrijden", len(season_matches))
    
    with col2:
        total_goals = season_matches['thuis_score'].sum() + season_matches['uit_score'].sum()
        st.metric("Totaal Goals", total_goals)
    
    with col3:
        avg_goals = total_goals / len(season_matches) if len(season_matches) > 0 else 0
        st.metric("Gem. Goals/Wedstrijd", f"{avg_goals:.1f}")
    
    with col4:
        # Unieke spelers
        unique_players = set()
        # Detect home/away columns
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
        for _, match in season_matches.iterrows():
            unique_players.update([
                match.get(home_cols[0], None), match.get(home_cols[1], None),
                match.get(away_cols[0], None), match.get(away_cols[1], None)
            ])
        st.metric("Actieve Spelers", len([p for p in unique_players if p is not None]))
    
    # Visualisaties in columns
    st.subheader("📊 Seizoen Visualisaties")
    
    col1, col2 = st.columns(2)
    with col1:
        show_goals_bar_chart_season(season_matches)
    with col2:
        show_unique_players_bar_chart(season_matches)
        show_winrate_bar_chart(season_matches)

    import pandas as pd
    # Vierde grafiek: Meeste klinkers per speler in dit seizoen
    klinker_stats = defaultdict(int)
    home_cols = ['thuis_1', 'thuis_2']
    away_cols = ['uit_1', 'uit_2']
    for _, match in season_matches.iterrows():
        for idx, col in enumerate(home_cols):
            speler = match.get(col, None)
            if speler is not None:
                klinker_col = f'klinkers_thuis_{idx+1}'
                klinker_stats[speler] += match.get(klinker_col, 0) or 0
        for idx, col in enumerate(away_cols):
            speler = match.get(col, None)
            if speler is not None:
                klinker_col = f'klinkers_uit_{idx+1}'
                klinker_stats[speler] += match.get(klinker_col, 0) or 0
    klinker_df = pd.DataFrame(list(klinker_stats.items()), columns=['Speler', 'Klinkers']).sort_values('Klinkers', ascending=False)
    if not klinker_df.empty and klinker_df['Klinkers'].sum() > 0:
        st.subheader("🔔 Meeste klinkers dit seizoen")
        fig_klinkers = px.bar(
            klinker_df.head(10),
            x='Speler',
            y='Klinkers',
            title="Top 10 Klinkers dit seizoen",
            color='Klinkers',
            color_continuous_scale='OrRd'
        )
        fig_klinkers.update_layout(xaxis_title="Speler", yaxis_title="Klinkers")
        st.plotly_chart(fig_klinkers, config={'responsive': True}, key="klinkers_bar_chart_season")
    
    # ELO ratings als beschikbaar
    if season_elo is not None and not season_elo.empty:
        st.subheader("🏆 ELO Rankings")
        show_elo_bar_chart(season_elo)
    
    # (verwijderd: goals trend over tijd)