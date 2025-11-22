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

    # Toon seizoenen tabel bovenaan
    if not seasons_df.empty:
        st.subheader("Seizoenen overzicht")
        seasons_display = seasons_df.copy()
        # Format start/einddatum netjes
        for col in ['startdatum', 'einddatum', 'start_datum', 'eind_datum']:
            if col in seasons_display.columns:
                seasons_display[col] = pd.to_datetime(seasons_display[col]).dt.strftime('%d-%m-%Y')
        st.dataframe(seasons_display, use_container_width=True)

    # Seizoenselectie: alle of specifiek seizoen
    season_options = ["Alle seizoenen"]
    if not seasons_df.empty:
        # Toon seizoensnaam of jaar
        for _, row in seasons_df.iterrows():
            season_name = row.get('seizoen_naam') or row.get('seizoen') or str(row.get('jaar', 'Onbekend'))
            season_options.append(season_name)

        # Default: huidig seizoen
        from datetime import date
        today = date.today()
        default_idx = 0
        for i, row in seasons_df.iterrows():
            # Detect start/eind kolommen
            start_col = 'start_datum' if 'start_datum' in row else 'startdatum'
            end_col = 'eind_datum' if 'eind_datum' in row else 'einddatum'
            season_start = pd.to_datetime(row[start_col]).date()
            season_end = pd.to_datetime(row[end_col]).date()
            if season_start <= today <= season_end:
                default_idx = i + 1  # +1 vanwege "Alle seizoenen"
                break
        selected = st.selectbox("Selecteer seizoen:", season_options, index=default_idx)
    else:
        selected = season_options[0]

    # Extra analyses bovenaan: timeline, all-time goals, activiteit vs winrate, seizoen distributie
    from analytics import show_timeline_chart, show_all_time_goals_chart, show_activity_vs_winrate_scatter, show_season_distribution_pie

    st.subheader("📈 Wedstrijden per dag (timeline)")
    show_timeline_chart(matches_df)

    st.subheader("🥅 All-time Topscorers")
    show_all_time_goals_chart(matches_df)

    st.subheader("📊 Activiteit vs Winpercentage")
    show_activity_vs_winrate_scatter(matches_df)

    st.subheader("🥧 Distributie wedstrijden per seizoen")
    show_season_distribution_pie(seasons_df)

    # Toon cross-seizoen analyses altijd
    show_cross_season_charts(matches_df, seasons_df)
    # Toon all-time leaderboards altijd
    player_stats = create_all_time_leaderboards(matches_df)
    show_all_time_leaderboards(player_stats)

    # Toon analyses voor geselecteerd seizoen of alle seizoenen
    if selected == "Alle seizoenen":
        st.subheader("Analyse: Alle seizoenen")
        # Toon gecombineerde analyse over alle wedstrijden
        show_individual_season_analysis({'seizoen_naam': 'Alle seizoenen'}, matches_df)
    elif not seasons_df.empty:
        # Zoek de juiste rij
        season_row = None
        for _, row in seasons_df.iterrows():
            season_name = row.get('seizoen_naam') or row.get('seizoen') or str(row.get('jaar', 'Onbekend'))
            if season_name == selected:
                season_row = row
                break
        if season_row is not None:
            start_col = 'start_datum' if 'start_datum' in season_row else 'startdatum'
            end_col = 'eind_datum' if 'eind_datum' in season_row else 'einddatum'
            season_start = pd.to_datetime(season_row[start_col])
            season_end = pd.to_datetime(season_row[end_col])
            season_matches = matches_df[(matches_df['timestamp'] >= season_start) & (matches_df['timestamp'] <= season_end)]
            show_individual_season_analysis(season_row, season_matches)
