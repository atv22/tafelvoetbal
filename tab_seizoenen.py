import streamlit as st
import pandas as pd
from analytics import (
    show_cross_season_charts,
    show_individual_season_analysis,
    create_all_time_leaderboards,
    show_all_time_leaderboards
)

def render_seizoenen_tab(matches_df, players_df, seasons_df):
    st.header("📅 Seizoensanalyse")
    # Toon cross-seizoen analyses
    show_cross_season_charts(matches_df, seasons_df)
    # Toon all-time leaderboards
    player_stats = create_all_time_leaderboards(matches_df)
    show_all_time_leaderboards(player_stats)
    # Voor individuele seizoen analyse, voorbeeld: eerste seizoen
    if not seasons_df.empty:
        first_season = seasons_df.iloc[0]
        # Gebruik juiste kolomnamen (startdatum/einddatum of fallback)
        start_col = 'start_datum' if 'start_datum' in first_season else 'startdatum'
        end_col = 'eind_datum' if 'eind_datum' in first_season else 'einddatum'
        season_start = pd.to_datetime(first_season[start_col])
        season_end = pd.to_datetime(first_season[end_col])
        season_matches = matches_df[(matches_df['timestamp'] >= season_start) & (matches_df['timestamp'] <= season_end)]
        show_individual_season_analysis(first_season, season_matches)
