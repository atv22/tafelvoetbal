"""
Analytics en visualisatie functies voor de tafelvoetbal app
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict
import numpy as np

# --- Helper voor het extraheren van spelerstatistieken (Vectorized) ---
@st.cache_data
def get_vectorized_player_stats(matches_df):
    """
    Transformeert de matches DataFrame naar een geaggregeerde speler-statistieken DataFrame.
    Gebruikt vectorisatie voor maximale performance.
    """
    if matches_df is None or matches_df.empty:
        return pd.DataFrame()

    # Lijst van kolommen
    home_players = ['thuis_1', 'thuis_2']
    away_players = ['uit_1', 'uit_2']
    home_klinkers = ['klinkers_thuis_1', 'klinkers_thuis_2']
    away_klinkers = ['klinkers_uit_1', 'klinkers_uit_2']

    # 1. Thuis spelers
    home_list = []
    for i, p_col in enumerate(home_players):
        # Controleer of kolommen bestaan
        cols = [p_col, 'thuis_score', 'uit_score']
        k_col = home_klinkers[i]
        if k_col in matches_df.columns:
            cols.append(k_col)
            
        temp = matches_df[cols].copy()
        if k_col not in matches_df.columns:
            temp['Klinkers'] = 0
            temp.columns = ['Speler', 'Goals_Voor', 'Goals_Tegen', 'Klinkers']
        else:
            temp.columns = ['Speler', 'Goals_Voor', 'Goals_Tegen', 'Klinkers']
            
        temp['Win'] = (temp['Goals_Voor'] > temp['Goals_Tegen']).astype(int)
        home_list.append(temp)
    
    # 2. Uit spelers
    away_list = []
    for i, p_col in enumerate(away_players):
        cols = [p_col, 'uit_score', 'thuis_score']
        k_col = away_klinkers[i]
        if k_col in matches_df.columns:
            cols.append(k_col)
            
        temp = matches_df[cols].copy()
        if k_col not in matches_df.columns:
            temp['Klinkers'] = 0
            temp.columns = ['Speler', 'Goals_Voor', 'Goals_Tegen', 'Klinkers']
        else:
            temp.columns = ['Speler', 'Goals_Voor', 'Goals_Tegen', 'Klinkers']
            
        temp['Win'] = (temp['Goals_Voor'] > temp['Goals_Tegen']).astype(int)
        away_list.append(temp)
    
    # Combineer alles
    all_player_events = pd.concat(home_list + away_list).dropna(subset=['Speler'])
    
    # Filter 'Niemand' spelers uit (gebruikt bij 1v1) - Case-insensitive
    niemand_base = ['niemandin', 'niemanduit', 'niemand', 'none', '']
    all_player_events = all_player_events[~all_player_events['Speler'].str.lower().str.strip().isin(niemand_base)]
    
    # Groepeer op speler
    stats = all_player_events.groupby('Speler').agg(
        Matches=('Speler', 'count'),
        Wins=('Win', 'sum'),
        Goals=('Goals_Voor', 'sum'),
        Goals_Tegen=('Goals_Tegen', 'sum'),
        Klinkers=('Klinkers', 'sum')
    ).reset_index()
    
    stats['Winrate'] = (stats['Wins'] / stats['Matches']) * 100
    stats['Goals_Per_Match'] = stats['Goals'] / stats['Matches']
    stats['Goal_Diff'] = stats['Goals'] - stats['Goals_Tegen']
    
    return stats

# --- Herbruikbare ELO-winnaar/top 3 logica per seizoen ---
@st.cache_data
def get_absolute_top3_elo(elo_df):
    """
    Bepaal de top 3 spelers met de hoogste ELO ooit bereikt op enig moment.
    """
    if elo_df is None or elo_df.empty:
        return []
    
    # Filter 'Niemand' spelers uit voor de zekerheid
    df = elo_df.copy()
    niemand_base = ['niemandin', 'niemanduit', 'niemand', 'none', '']
    df = df[~df['speler_naam'].str.lower().str.strip().isin(niemand_base)]
    
    # Pak de maximale rating per speler over de hele historie
    peak_elos = df.groupby('speler_naam')['rating'].max().reset_index()
    top3 = peak_elos.sort_values('rating', ascending=False).head(3)
    
    return list(zip(top3['speler_naam'], top3['rating']))


@st.cache_data
def get_season_top3_elo(elo_df, seizoen_matches):
    """
    Bepaal de top 3 spelers met hoogste laatst bekende ELO aan het einde van het seizoen.
    """
    if elo_df is None or elo_df.empty or seizoen_matches is None or seizoen_matches.empty:
        return []
    
    # Bepaal alle match_ids in het seizoen
    match_ids_in_season = set(seizoen_matches['match_id']) if 'match_id' in seizoen_matches.columns else set()
    
    # Filter ELO-logs op matches in seizoen
    elo_season = elo_df[elo_df['match_id'].isin(match_ids_in_season)].copy()
    
    # Filter 'Niemand' spelers uit
    niemand_variations = ['NiemandIn', 'NiemandUit', 'Niemand', 'None', '', ' ']
    elo_season = elo_season[~elo_season['speler_naam'].isin(niemand_variations)]
    
    if elo_season.empty:
        return []
    
    # Pak per speler de laatste ELO in het seizoen
    # Gebruik utc=True om ValueError met tz-aware datums te voorkomen
    elo_season['timestamp'] = pd.to_datetime(elo_season['timestamp'], utc=True).dt.tz_localize(None)
    latest_elo = elo_season.sort_values('timestamp').groupby('speler_naam').last().reset_index()
    top3 = latest_elo.sort_values('rating', ascending=False).head(3)
    return list(zip(top3['speler_naam'], top3['rating']))


def show_timeline_chart(matches_df):
    """Toon een timeline chart van wedstrijden"""
    if matches_df is None or matches_df.empty:
        return
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
    st.plotly_chart(fig_timeline, use_container_width=True, key="timeline_chart")


def show_unique_players_bar_chart(season_matches):
    """Toon een bar chart van unieke spelers per dag"""
    if season_matches is None or season_matches.empty:
        return

    # Gebruik melt om spelers te extraheren
    p_cols = ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']
    # Filter kolommen die daadwerkelijk bestaan
    existing_p_cols = [c for c in p_cols if c in season_matches.columns]
    if not existing_p_cols:
        return

    temp = season_matches[['timestamp'] + existing_p_cols].copy()
    temp['Datum'] = temp['timestamp'].dt.date
    melted = temp.melt(id_vars=['Datum'], value_vars=existing_p_cols, value_name='Speler').dropna(subset=['Speler'])
    
    daily_unique = melted.groupby('Datum')['Speler'].nunique().reset_index()
    daily_unique.columns = ['Datum', 'Unieke spelers']
    
    fig_players = px.bar(
        daily_unique,
        x='Datum',
        y='Unieke spelers',
        title="Unieke spelers per dag",
        color_discrete_sequence=['#ff7f0e']
    )
    fig_players.update_layout(xaxis_title="Datum", yaxis_title="Unieke spelers")
    st.plotly_chart(fig_players, use_container_width=True, key="unique_players_bar_chart")


def show_winrate_bar_chart(season_matches, min_matches=3):
    """Toon winpercentage bar chart voor een specifiek seizoen"""
    stats = get_vectorized_player_stats(season_matches)
    if stats is None or stats.empty:
        return
        
    winrate_df = stats[stats['Matches'] >= min_matches].sort_values('Winrate', ascending=False)
    
    if not winrate_df.empty:
        fig_winrate = px.bar(
            winrate_df.head(10),
            x='Speler',
            y='Winrate',
            title=f"Top 10 Win% (min. {min_matches})",
            color='Winrate',
            color_continuous_scale='RdYlGn',
            labels={'Winrate': 'Winpercentage (%)'}
        )
        fig_winrate.update_layout(xaxis_title="Speler", yaxis_title="Winpercentage (%)")
        st.plotly_chart(fig_winrate, use_container_width=True, key="winrate_bar_chart")


def show_activity_vs_winrate_scatter(all_matches, key_suffix=None):
    """Toon scatter plot van activiteit vs winpercentage"""
    stats = get_vectorized_player_stats(all_matches)
    if stats is None or stats.empty:
        return
        
    scatter_df = stats[stats['Matches'] >= 3].copy()
    
    if not scatter_df.empty:
        fig_scatter = px.scatter(
            scatter_df,
            x='Matches',
            y='Winrate',
            size='Goals',
            color='Wins',
            color_continuous_scale='Blues',
            text='Speler',
            title="Activiteit vs Winpercentage (min. 3 wedstrijden)",
            labels={'Matches': 'Aantal Wedstrijden', 'Winrate': 'Winpercentage (%)'},
            hover_data=['Speler', 'Matches', 'Winrate', 'Goals', 'Wins']
        )
        fig_scatter.update_traces(textposition="top center")
        fig_scatter.update_layout(xaxis_title="Aantal Wedstrijden", yaxis_title="Winpercentage (%)")
        chart_key = f"activity_vs_winrate_scatter_{key_suffix}" if key_suffix else "activity_vs_winrate_scatter"
        st.plotly_chart(fig_scatter, use_container_width=True, key=chart_key)


def show_cross_season_charts(all_matches, seasons_df, elo_df=None):
    """Toon cross-seizoen analyse charts."""
    if all_matches is None or all_matches.empty or seasons_df is None or seasons_df.empty:
        return
    
    # Gemiddelde goals trend
    if len(seasons_df) > 1:
        if 'gemiddelde_goals' in seasons_df.columns and seasons_df['gemiddelde_goals'].sum() > 0:
            st.subheader("📈 Trends over seizoenen")
            fig_season_goals = px.line(
                seasons_df,
                x='seizoen_naam' if 'seizoen_naam' in seasons_df.columns else seasons_df.columns[0],
                y='gemiddelde_goals',
                title="Gemiddelde Goals per Seizoen",
                markers=True
            )
            st.plotly_chart(fig_season_goals, use_container_width=True, key="cross_season_goals_chart")


def show_goals_bar_chart_season(season_matches):
    """Toon goals bar chart voor een specifiek seizoen"""
    stats = get_vectorized_player_stats(season_matches)
    if stats is None or stats.empty:
        return
        
    goals_df = stats.sort_values('Goals', ascending=False).head(10)
    
    if not goals_df.empty:
        fig_goals = px.bar(
            goals_df,
            x='Speler',
            y='Goals',
            title="Top 10 Topscorers",
            color='Goals',
            color_continuous_scale='Blues'
        )
        fig_goals.update_layout(xaxis_title="Speler", yaxis_title="Goals")
        st.plotly_chart(fig_goals, use_container_width=True, key="goals_bar_chart_season")


def create_all_time_leaderboards(all_matches):
    """Maak alle all-time leaderboards (Wrapper voor de vectorized functie)"""
    return get_vectorized_player_stats(all_matches)


def show_all_time_leaderboards(player_stats_df):
    """Toon alle ranglijsten met geoptimaliseerde DataFrame operations"""
    st.subheader("🏆 Ranglijsten")

    if player_stats_df is None or player_stats_df.empty:
        st.info("Geen data beschikbaar voor ranglijsten.")
        return

    # Data voorbereiden met Pandas
    def get_top_5(df, sort_col, display_name, format_str=None):
        top5 = df.sort_values(sort_col, ascending=False).head(5).reset_index(drop=True)
        top5.index += 1
        top5 = top5.reset_index().rename(columns={'index': '#', sort_col: display_name})
        if format_str:
            top5[display_name] = top5[display_name].map(lambda x: format_str.format(x))
        return top5[['#', 'Speler', display_name]]

    # ELO toevoegen indien aanwezig (uit globale players_df of laatst bekende uit elo_df)
    # Voor nu gebruiken we de kolommen die we hebben. 
    # NB: player_stats_df in analytics komt uit get_vectorized_player_stats, die heeft nog geen ELO.
    # We halen de ELO uit de firestore spelerslijst voor de meest actuele stand.
    from firestore_service import get_players
    p_df = get_players()
    if not p_df.empty:
        elo_map = dict(zip(p_df['speler_naam'], p_df['rating']))
        player_stats_df['ELO'] = player_stats_df['Speler'].map(lambda x: elo_map.get(x, 1000))
    else:
        player_stats_df['ELO'] = 1000

    # Gefilterde ranglijsten (min 3 matches)
    f3 = player_stats_df[player_stats_df['Matches'] >= 3]
    
    df_elo = get_top_5(f3, 'ELO', 'ELO')
    df_scorers = get_top_5(f3, 'Goals', 'Goals')
    df_active = get_top_5(f3, 'Matches', 'Wedstrijden')
    df_wins = get_top_5(f3, 'Wins', 'Overwinningen')
    
    # Tweede rij
    df_klinkers = get_top_5(player_stats_df, 'Klinkers', 'Klinkers') # Geen drempel voor klinkers
    
    df_win_pct = get_top_5(f3, 'Winrate', 'Win%', '{:.1f}%')
    df_gpm = get_top_5(f3, 'Goals_Per_Match', 'Goals/W', '{:.2f}')
    df_avg_goals = get_top_5(f3, 'Goals_Per_Match', 'Gem. Goals', '{:.2f}')

    # Toon acht tabellen in 2 rijen van 4
    row1 = st.columns(4)
    row2 = st.columns(4)
    
    tables_r1 = [
        (row1[0], "🥇 Top 5 ELO (min. 3)", df_elo),
        (row1[1], "🥅 Top 5 Topscorers (min. 3)", df_scorers),
        (row1[2], "⚽ Top 5 Meest Actief (min. 3)", df_active),
        (row1[3], "🏅 Top 5 Overwinningen (min. 3)", df_wins)
    ]
    
    tables_r2 = [
        (row2[0], "🎯 Top 5 Klinker Masters", df_klinkers),
        (row2[1], "📈 Top Win% (min. 3)", df_win_pct),
        (row2[2], "🚀 Goals per Wedstrijd (min. 3)", df_gpm),
        (row2[3], "⚖️ Gem. Goals (min. 3)", df_avg_goals)
    ]

    for col, title, df in tables_r1 + tables_r2:
        with col:
            st.write(f"**{title}:**")
            st.dataframe(df, hide_index=True, use_container_width=True)


def show_individual_season_analysis(season_info, season_matches, season_elo=None):
    """Toon uitgebreide analyse voor een individueel seizoen met geoptimaliseerde stats"""
    if season_matches is None or season_matches.empty:
        st.warning("Geen wedstrijden gevonden voor dit seizoen.")
        return
    
    seizoen_naam = season_info.get('seizoen_naam') or season_info.get('seizoen') or 'Onbekend Seizoen'
    st.subheader(f"📈 {seizoen_naam}")
    
    # Basis statistieken (Vectorized)
    total_matches = len(season_matches)
    total_goals = season_matches['thuis_score'].sum() + season_matches['uit_score'].sum()
    avg_goals = total_goals / total_matches if total_matches > 0 else 0
    
    # Unieke spelers via vectorized approach
    p_cols = ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']
    # Filter kolommen die daadwerkelijk bestaan
    existing_p_cols = [c for c in p_cols if c in season_matches.columns]
    unique_players = pd.unique(season_matches[existing_p_cols].values.ravel())
    unique_players_count = len([p for p in unique_players if p and not pd.isna(p)])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Totaal Wedstrijden", total_matches)
    col2.metric("Totaal Goals", int(total_goals))
    col3.metric("Gem. Goals/Wedstrijd", f"{avg_goals:.1f}")
    col4.metric("Actieve Spelers", unique_players_count)
    
    st.subheader("📊 Seizoen Visualisaties")
    show_activity_vs_winrate_scatter(season_matches, key_suffix=f"season_{seizoen_naam}")
    
    r1 = st.columns(2)
    r2 = st.columns(2)
    with r1[0]:
        show_goals_bar_chart_season(season_matches)
    with r1[1]:
        show_unique_players_bar_chart(season_matches)
    with r2[0]:
        show_winrate_bar_chart(season_matches)
    
    # Klinkers chart (Vectorized)
    with r2[1]:
        stats = get_vectorized_player_stats(season_matches)
        if stats is not None and not stats.empty and stats['Klinkers'].sum() > 0:
            k_df = stats.sort_values('Klinkers', ascending=False).head(10)
            fig_k = px.bar(k_df, x='Speler', y='Klinkers', title="Top 10 Klinkers", color='Klinkers', color_continuous_scale='OrRd')
            st.plotly_chart(fig_k, use_container_width=True, key=f"k_chart_{seizoen_naam}")

    # ELO ratings
    if season_elo is not None and not season_elo.empty:
        st.subheader("🏆 ELO Rankings")
        elo_top = season_elo.sort_values('rating', ascending=False).head(10)
        fig_elo = px.bar(elo_top, x='speler_naam', y='rating', title="Top 10 ELO Ratings", color='rating', color_continuous_scale='Viridis')
        st.plotly_chart(fig_elo, use_container_width=True, key=f"elo_chart_{seizoen_naam}")
