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
        matches_per_day = matches_df.groupby(matches_df['datum'].dt.date).size()
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
        st.plotly_chart(fig_timeline, use_container_width=True)


def show_matches_bar_chart(season_matches):
    """Toon een bar chart van wedstrijden per speler in een seizoen"""
    all_players_matches = []
    for _, match in season_matches.iterrows():
        all_players_matches.extend([
            match['thuis_speler_1'], match['thuis_speler_2'],
            match['uit_speler_1'], match['uit_speler_2']
        ])
    
    matches_count = pd.Series(all_players_matches).value_counts()
    
    fig_matches = px.bar(
        x=matches_count.index,
        y=matches_count.values,
        labels={'x': 'Speler', 'y': 'Aantal wedstrijden'},
        title="Wedstrijden per speler",
        color_discrete_sequence=['#2ca02c']
    )
    fig_matches.update_layout(xaxis_title="Speler", yaxis_title="Aantal wedstrijden")
    st.plotly_chart(fig_matches, use_container_width=True)


def show_unique_players_bar_chart(season_matches):
    """Toon een bar chart van unieke spelers per dag"""
    daily_players = defaultdict(set)
    for _, match in season_matches.iterrows():
        day = match['datum'].date()
        daily_players[day].update([
            match['thuis_speler_1'], match['thuis_speler_2'],
            match['uit_speler_1'], match['uit_speler_2']
        ])
    
    daily_unique = {day: len(players) for day, players in daily_players.items()}
    daily_df = pd.DataFrame(list(daily_unique.items()), columns=['Datum', 'Unieke spelers'])
    
    fig_players = px.bar(
        daily_df,
        x='Datum',
        y='Unieke spelers',
        title="Unieke spelers per dag",
        color_discrete_sequence=['#ff7f0e']
    )
    fig_players.update_layout(xaxis_title="Datum", yaxis_title="Unieke spelers")
    st.plotly_chart(fig_players, use_container_width=True)


def show_goals_line_chart(season_matches):
    """Toon een lijn chart van gemiddelde goals per wedstrijd over tijd"""
    daily_goals = season_matches.groupby(season_matches['datum'].dt.date).agg({
        'thuis_score': 'sum',
        'uit_score': 'sum',
        'datum': 'count'  # aantal wedstrijden
    }).rename(columns={'datum': 'matches_count'})
    
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
    st.plotly_chart(fig_goals, use_container_width=True)


def show_all_time_goals_chart(all_matches):
    """Toon all-time goals chart voor alle seizoenen"""
    all_goals = defaultdict(int)
    
    for _, match in all_matches.iterrows():
        # Thuis team goals
        all_goals[match['thuis_speler_1']] += match['thuis_score']
        all_goals[match['thuis_speler_2']] += match['thuis_score']
        
        # Uit team goals
        all_goals[match['uit_speler_1']] += match['uit_score']
        all_goals[match['uit_speler_2']] += match['uit_score']
    
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
        st.plotly_chart(fig_all_goals, use_container_width=True)


def show_activity_vs_winrate_scatter(all_matches):
    """Toon scatter plot van activiteit vs winpercentage"""
    player_stats = defaultdict(lambda: {'matches': 0, 'wins': 0})
    
    for _, match in all_matches.iterrows():
        home_players = [match['thuis_speler_1'], match['thuis_speler_2']]
        away_players = [match['uit_speler_1'], match['uit_speler_2']]
        
        for player in home_players:
            player_stats[player]['matches'] += 1
            if match['thuis_score'] > match['uit_score']:
                player_stats[player]['wins'] += 1
        
        for player in away_players:
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
        st.plotly_chart(fig_scatter, use_container_width=True)


def show_season_distribution_pie(seasons_df):
    """Toon pie chart van seizoen distributie"""
    if not seasons_df.empty and 'aantal_wedstrijden' in seasons_df.columns:
        fig_pie = px.pie(
            seasons_df,
            values='aantal_wedstrijden',
            names='seizoen_naam',
            title="Distributie wedstrijden per seizoen"
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)


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
        st.plotly_chart(fig_elo, use_container_width=True)


def show_winrate_bar_chart(season_matches, min_matches=5):
    """Toon winpercentage bar chart voor een specifiek seizoen"""
    player_stats = defaultdict(lambda: {'matches': 0, 'wins': 0})
    
    for _, match in season_matches.iterrows():
        home_players = [match['thuis_speler_1'], match['thuis_speler_2']]
        away_players = [match['uit_speler_1'], match['uit_speler_2']]
        
        for player in home_players:
            player_stats[player]['matches'] += 1
            if match['thuis_score'] > match['uit_score']:
                player_stats[player]['wins'] += 1
        
        for player in away_players:
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
        st.plotly_chart(fig_winrate, use_container_width=True)


def show_goals_bar_chart_season(season_matches):
    """Toon goals bar chart voor een specifiek seizoen"""
    goals_stats = defaultdict(int)
    
    for _, match in season_matches.iterrows():
        # Thuis team goals
        goals_stats[match['thuis_speler_1']] += match['thuis_score']
        goals_stats[match['thuis_speler_2']] += match['thuis_score']
        
        # Uit team goals  
        goals_stats[match['uit_speler_1']] += match['uit_score']
        goals_stats[match['uit_speler_2']] += match['uit_score']
    
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
        st.plotly_chart(fig_goals, use_container_width=True)


def create_all_time_leaderboards(all_matches):
    """Maak alle all-time leaderboards"""
    
    # Statistieken verzamelen
    player_stats = defaultdict(lambda: {
        'matches': 0,
        'wins': 0, 
        'goals': 0,
        'max_elo': 1000  # Start ELO
    })
    
    for _, match in all_matches.iterrows():
        home_players = [match['thuis_speler_1'], match['thuis_speler_2']]
        away_players = [match['uit_speler_1'], match['uit_speler_2']]
        
        # Home team stats
        for player in home_players:
            player_stats[player]['matches'] += 1
            player_stats[player]['goals'] += match['thuis_score']
            if match['thuis_score'] > match['uit_score']:
                player_stats[player]['wins'] += 1
            
            # ELO tracking (zou uit ELO historie moeten komen, maar we schatten)
            if 'klinkers_thuis_1' in match and match['klinkers_thuis_1'] and player == match['thuis_speler_1']:
                estimated_elo = 1000 + (player_stats[player]['wins'] * 20)
                player_stats[player]['max_elo'] = max(player_stats[player]['max_elo'], estimated_elo)
        
        # Away team stats
        for player in away_players:
            player_stats[player]['matches'] += 1
            player_stats[player]['goals'] += match['uit_score']
            if match['uit_score'] > match['thuis_score']:
                player_stats[player]['wins'] += 1
            
            # ELO tracking
            if 'klinkers_uit_1' in match and match['klinkers_uit_1'] and player == match['uit_speler_1']:
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
    
    if all_matches.empty:
        return
        
    st.subheader("📊 Cross-Seizoen Analyses")
    
    # ELO ontwikkeling over seizoenen (geschatte versie)
    player_season_elo = defaultdict(lambda: defaultdict(int))
    player_season_matches = defaultdict(lambda: defaultdict(int))
    
    for _, match in all_matches.iterrows():
        match_date = pd.to_datetime(match['datum']).tz_localize(None)
        
        # Vind seizoen voor deze wedstrijd
        current_season = "Onbekend"
        for _, season in seasons_df.iterrows():
            season_start = pd.to_datetime(season['start_datum']).tz_localize(None)
            season_end = pd.to_datetime(season['eind_datum']).tz_localize(None)
            if season_start <= match_date <= season_end:
                current_season = season['seizoen_naam']
                break
        
        # Track matches per seizoen
        home_players = [match['thuis_speler_1'], match['thuis_speler_2']]
        away_players = [match['uit_speler_1'], match['uit_speler_2']]
        
        for player in home_players + away_players:
            player_season_matches[player][current_season] += 1
    
    # Seizoen vergelijking chart
    if len(seasons_df) > 1:
        season_comparison = []
        for _, season in seasons_df.iterrows():
            season_comparison.append({
                'Seizoen': season['seizoen_naam'],
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
                st.plotly_chart(fig_season_matches, use_container_width=True)
            
            with col2:
                if 'Gem. Goals' in comparison_df.columns and comparison_df['Gem. Goals'].sum() > 0:
                    fig_season_goals = px.line(
                        comparison_df,
                        x='Seizoen',
                        y='Gem. Goals',
                        title="Gemiddelde Goals per Seizoen",
                        markers=True
                    )
                    st.plotly_chart(fig_season_goals, use_container_width=True)