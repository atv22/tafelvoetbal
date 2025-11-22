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
        st.plotly_chart(fig_timeline, config={'responsive': True})


def show_matches_bar_chart(season_matches):
    """Toon een bar chart van wedstrijden per speler in een seizoen"""
    all_players_matches = []
    # Detect home/away columns
    if not season_matches.empty:
        match_row = season_matches.iloc[0]
        if 'thuis_speler_1' in match_row:
            home_cols = ['thuis_speler_1', 'thuis_speler_2']
            away_cols = ['uit_speler_1', 'uit_speler_2']
        else:
            home_cols = ['thuis_1', 'thuis_2']
            away_cols = ['uit_1', 'uit_2']
    else:
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    for _, match in season_matches.iterrows():
        all_players_matches.extend([
            match.get(home_cols[0], None), match.get(home_cols[1], None),
            match.get(away_cols[0], None), match.get(away_cols[1], None)
        ])
    matches_count = pd.Series([p for p in all_players_matches if p is not None]).value_counts()
    
    fig_matches = px.bar(
        x=matches_count.index,
        y=matches_count.values,
        labels={'x': 'Speler', 'y': 'Aantal wedstrijden'},
        title="Wedstrijden per speler",
        color_discrete_sequence=['#2ca02c']
    )
    fig_matches.update_layout(xaxis_title="Speler", yaxis_title="Aantal wedstrijden")
    st.plotly_chart(fig_matches, config={'responsive': True})


def show_unique_players_bar_chart(season_matches):
    """Toon een bar chart van unieke spelers per dag"""
    daily_players = defaultdict(set)
    # Detect home/away columns
    if not season_matches.empty:
        match_row = season_matches.iloc[0]
        if 'thuis_speler_1' in match_row:
            home_cols = ['thuis_speler_1', 'thuis_speler_2']
            away_cols = ['uit_speler_1', 'uit_speler_2']
        else:
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
    st.plotly_chart(fig_players, config={'responsive': True})


def show_goals_line_chart(season_matches):
    """Toon een lijn chart van gemiddelde goals per wedstrijd over tijd"""
    daily_goals = season_matches.groupby(season_matches['timestamp'].dt.date).agg({
        'thuis_score': 'sum',
        'uit_score': 'sum',
        'timestamp': 'count'  # aantal wedstrijden
    }).rename(columns={'timestamp': 'matches_count'})
    
    daily_goals['total_goals'] = daily_goals['thuis_score'] + daily_goals['uit_score']
    daily_goals['avg_goals_per_match'] = daily_goals['total_goals'] / daily_goals['matches_count']
    
    fig_goals = px.line(
        x=daily_goals.index,
        y=daily_goals['avg_goals_per_match'],
        title="Gemiddelde goals per wedstrijd over tijd",
        color_discrete_sequence=['#d62728']
    )
    fig_goals.update_layout(
        xaxis_title="Datum", 
        yaxis_title="Gemiddelde goals per wedstrijd"
    )
    st.plotly_chart(fig_goals, config={'responsive': True})


def show_all_time_goals_chart(all_matches):
    """Toon all-time goals chart voor alle seizoenen"""
    all_goals = defaultdict(int)
    
    # Detect home/away columns
    if not all_matches.empty:
        match_row = all_matches.iloc[0]
        if 'thuis_speler_1' in match_row:
            home_cols = ['thuis_speler_1', 'thuis_speler_2']
            away_cols = ['uit_speler_1', 'uit_speler_2']
        else:
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
        st.plotly_chart(fig_all_goals, config={'responsive': True})


def show_activity_vs_winrate_scatter(all_matches):
    """Toon scatter plot van activiteit vs winpercentage"""
    player_stats = defaultdict(lambda: {'matches': 0, 'wins': 0})
    
    # Detect home/away columns
    if not all_matches.empty:
        match_row = all_matches.iloc[0]
        if 'thuis_speler_1' in match_row:
            home_cols = ['thuis_speler_1', 'thuis_speler_2']
            away_cols = ['uit_speler_1', 'uit_speler_2']
        else:
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
                if match['thuis_score'] > match['uit_score']:
                    player_stats[player]['wins'] += 1
        for player in away_players:
            if player is not None:
                player_stats[player]['matches'] += 1
                if match['uit_score'] > match['thuis_score']:
                    player_stats[player]['wins'] += 1
    
    scatter_data = []
    for player, stats in player_stats.items():
        if stats['matches'] >= 5:  # Minimaal 5 wedstrijden voor betrouwbaarheid
            win_rate = (stats['wins'] / stats['matches']) * 100
            scatter_data.append({
                'Speler': player,
                'Wedstrijden': stats['matches'],
                'Winpercentage': win_rate
            })
    
    if scatter_data:
        scatter_df = pd.DataFrame(scatter_data)
        fig_scatter = px.scatter(
            scatter_df,
            x='Wedstrijden',
            y='Winpercentage',
            text='Speler',
            title="Activiteit vs Winpercentage (min. 5 wedstrijden)",
            hover_data=['Speler', 'Wedstrijden', 'Winpercentage']
        )
        fig_scatter.update_traces(textposition="top center")
        fig_scatter.update_layout(xaxis_title="Aantal Wedstrijden", yaxis_title="Winpercentage (%)")
        st.plotly_chart(fig_scatter, config={'responsive': True})


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
        st.plotly_chart(fig_pie, config={'responsive': True})


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
        st.plotly_chart(fig_elo, config={'responsive': True})


def show_winrate_bar_chart(season_matches, min_matches=5):
    """Toon winpercentage bar chart voor een specifiek seizoen"""
    player_stats = defaultdict(lambda: {'matches': 0, 'wins': 0})
    
    # Detect home/away columns
    if not season_matches.empty:
        match_row = season_matches.iloc[0]
        if 'thuis_speler_1' in match_row:
            home_cols = ['thuis_speler_1', 'thuis_speler_2']
            away_cols = ['uit_speler_1', 'uit_speler_2']
        else:
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
        st.plotly_chart(fig_winrate, config={'responsive': True})


def show_goals_bar_chart_season(season_matches):
    """Toon goals bar chart voor een specifiek seizoen"""
    goals_stats = defaultdict(int)
    
    # Detect home/away columns
    if not season_matches.empty:
        match_row = season_matches.iloc[0]
        if 'thuis_speler_1' in match_row:
            home_cols = ['thuis_speler_1', 'thuis_speler_2']
            away_cols = ['uit_speler_1', 'uit_speler_2']
        else:
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
        st.plotly_chart(fig_goals, config={'responsive': True})


def create_all_time_leaderboards(all_matches):
    """Maak alle all-time leaderboards"""
    
    # Statistieken verzamelen
    player_stats = defaultdict(lambda: {
        'matches': 0,
        'wins': 0, 
        'goals': 0,
        'max_elo': 1000  # Start ELO
    })
    
    # Detect home/away columns
    if not all_matches.empty:
        match_row = all_matches.iloc[0]
        if 'thuis_speler_1' in match_row:
            home_cols = ['thuis_speler_1', 'thuis_speler_2']
            away_cols = ['uit_speler_1', 'uit_speler_2']
        else:
            home_cols = ['thuis_1', 'thuis_2']
            away_cols = ['uit_1', 'uit_2']
    else:
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    for _, match in all_matches.iterrows():
        home_players = [match.get(home_cols[0], None), match.get(home_cols[1], None)]
        away_players = [match.get(away_cols[0], None), match.get(away_cols[1], None)]
        # Home team stats
        for player in home_players:
            if player is not None:
                player_stats[player]['matches'] += 1
                player_stats[player]['goals'] += match['thuis_score']
                if match['thuis_score'] > match['uit_score']:
                    player_stats[player]['wins'] += 1
                # ELO tracking (zou uit ELO historie moeten komen, maar we schatten)
                if 'klinkers_thuis_1' in match and match['klinkers_thuis_1'] and player == match.get(home_cols[0], None):
                    estimated_elo = 1000 + (player_stats[player]['wins'] * 20)
                    player_stats[player]['max_elo'] = max(player_stats[player]['max_elo'], estimated_elo)
        # Away team stats
        for player in away_players:
            if player is not None:
                player_stats[player]['matches'] += 1
                player_stats[player]['goals'] += match['uit_score']
                if match['uit_score'] > match['thuis_score']:
                    player_stats[player]['wins'] += 1
                # ELO tracking
                if 'klinkers_uit_1' in match and match['klinkers_uit_1'] and player == match.get(away_cols[0], None):
                    estimated_elo = 1000 + (player_stats[player]['wins'] * 20)
                    player_stats[player]['max_elo'] = max(player_stats[player]['max_elo'], estimated_elo)
    
    return player_stats


def show_all_time_leaderboards(player_stats):
    """Toon alle all-time leaderboards"""
    
    st.subheader("🏆 All-time Leaderboards")
    
    # Top 5 Scorers
    top_scorers = sorted(player_stats.items(), key=lambda x: x[1]['goals'], reverse=True)[:5]
    st.write("**🥅 Top 5 All-time Scorers:**")
    for i, (player, stats) in enumerate(top_scorers, 1):
        st.write(f"{i}. {player}: {stats['goals']} goals")
    
    # Top 5 Most Active
    most_active = sorted(player_stats.items(), key=lambda x: x[1]['matches'], reverse=True)[:5]
    st.write("**⚽ Top 5 Most Active:**")
    for i, (player, stats) in enumerate(most_active, 1):
        st.write(f"{i}. {player}: {stats['matches']} wedstrijden")
    
    # Top 5 Most Wins
    most_wins = sorted(player_stats.items(), key=lambda x: x[1]['wins'], reverse=True)[:5]
    st.write("**🏅 Top 5 Most Wins:**")
    for i, (player, stats) in enumerate(most_wins, 1):
        st.write(f"{i}. {player}: {stats['wins']} overwinningen")
    
    # Top 5 Klinker Masters (highest ELO)
    klinker_masters = sorted(player_stats.items(), key=lambda x: x[1]['max_elo'], reverse=True)[:5]
    st.write("**🎯 Top 5 Klinker Masters (Hoogste ELO):**")
    for i, (player, stats) in enumerate(klinker_masters, 1):
        st.write(f"{i}. {player}: {stats['max_elo']} ELO")


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
        if 'thuis_speler_1' in match_row:
            home_cols = ['thuis_speler_1', 'thuis_speler_2']
            away_cols = ['uit_speler_1', 'uit_speler_2']
        else:
            home_cols = ['thuis_1', 'thuis_2']
            away_cols = ['uit_1', 'uit_2']
    else:
        home_cols = ['thuis_speler_1', 'thuis_speler_2']
        away_cols = ['uit_speler_1', 'uit_speler_2']

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
                'Wedstrijden': season.get('aantal_wedstrijden', 0),
                'Gem. Goals': season.get('gemiddelde_goals', 0)
            })
        if season_comparison:
            comparison_df = pd.DataFrame(season_comparison)
            col1, col2 = st.columns(2)
            with col1:
                fig_season_matches = px.bar(
                    comparison_df,
                    x='Seizoen',
                    y='Wedstrijden',
                    title="Wedstrijden per Seizoen",
                    color='Wedstrijden',
                    color_continuous_scale='Blues'
                )
                st.plotly_chart(fig_season_matches, config={'responsive': True})
            with col2:
                if 'Gem. Goals' in comparison_df.columns and comparison_df['Gem. Goals'].sum() > 0:
                    fig_season_goals = px.line(
                        comparison_df,
                        x='Seizoen',
                        y='Gem. Goals',
                        title="Gemiddelde Goals per Seizoen",
                        markers=True
                    )
                    st.plotly_chart(fig_season_goals, config={'responsive': True})


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
        if not season_matches.empty:
            match_row = season_matches.iloc[0]
            if 'thuis_speler_1' in match_row:
                home_cols = ['thuis_speler_1', 'thuis_speler_2']
                away_cols = ['uit_speler_1', 'uit_speler_2']
            else:
                home_cols = ['thuis_1', 'thuis_2']
                away_cols = ['uit_1', 'uit_2']
        else:
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
        show_matches_bar_chart(season_matches)
        show_goals_bar_chart_season(season_matches)
    
    with col2:
        show_unique_players_bar_chart(season_matches)
        show_winrate_bar_chart(season_matches)
    
    # ELO ratings als beschikbaar
    if season_elo is not None and not season_elo.empty:
        st.subheader("🏆 ELO Rankings")
        show_elo_bar_chart(season_elo)
    
    # Goals trend over tijd
    show_goals_line_chart(season_matches)