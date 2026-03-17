import streamlit as st
import pandas as pd
from firestore_service import normalize_timestamp_series, get_elo_logs
from analytics import (
    show_cross_season_charts,
    show_individual_season_analysis,
    create_all_time_leaderboards,
    show_all_time_leaderboards,
    get_season_top3_elo,
    show_timeline_chart,
    show_activity_vs_winrate_scatter
)

def render_seizoenen_tab(matches_df, players_df, seasons_df, elo_df=None):
    st.header("📅 Seizoensanalyse")
    if elo_df is None:
        elo_df = get_elo_logs()

    # Cross-seizoen analyses direct bovenaan
    st.subheader("📊 Cross-Seizoen Analyses")

    # Toon seizoenen tabel bovenaan
    if not seasons_df.empty:
        st.subheader("Seizoenen overzicht")
        
        # Voorbereiden extra metrics (Vectorized)
        all_matches_proc = matches_df.copy()
        all_matches_proc['ts_naive'] = all_matches_proc['timestamp'].dt.tz_localize(None)
        
        seasons_display = seasons_df.copy()
        extra_metrics = []
        
        for _, row in seasons_display.iterrows():
            start_col = 'start_datum' if 'start_datum' in row else 'startdatum'
            end_col = 'eind_datum' if 'eind_datum' in row else 'einddatum'
            start = pd.to_datetime(row[start_col]).replace(tzinfo=None)
            end = pd.to_datetime(row[end_col]).replace(tzinfo=None)
            
            s_matches = all_matches_proc[(all_matches_proc['ts_naive'] >= start) & (all_matches_proc['ts_naive'] <= end)]
            
            # Goals & Players (Vectorized)
            totaal_goals = int(s_matches['thuis_score'].sum() + s_matches['uit_score'].sum())
            p_cols = ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']
            existing_p_cols = [c for c in p_cols if c in s_matches.columns]
            u_players = pd.unique(s_matches[existing_p_cols].values.ravel())
            u_players_count = len([p for p in u_players if p and not pd.isna(p)])
            
            top3 = get_season_top3_elo(elo_df, s_matches)
            
            w = f"{top3[0][0]} ({int(top3[0][1])})" if len(top3) > 0 else "-"
            t2 = f"{top3[1][0]} ({int(top3[1][1])})" if len(top3) > 1 else "-"
            t3 = f"{top3[2][0]} ({int(top3[2][1])})" if len(top3) > 2 else "-"
            
            extra_metrics.append({
                'Totaal goals': totaal_goals,
                'Unieke spelers': u_players_count,
                'Winnaar': w,
                '2e plaats': t2,
                '3e plaats': t3
            })
            
        metrics_df = pd.DataFrame(extra_metrics)
        seasons_display = pd.concat([seasons_display.reset_index(drop=True), metrics_df], axis=1)
        
        # Formattering
        for col in ['startdatum', 'einddatum', 'start_datum', 'eind_datum']:
            if col in seasons_display.columns:
                seasons_display[col] = pd.to_datetime(seasons_display[col]).dt.strftime('%d-%m-%Y %H:%M')
                
        col_map = {
            'startdatum': 'Startdatum', 'einddatum': 'Einddatum',
            'start_datum': 'Startdatum', 'eind_datum': 'Einddatum',
            'seizoen_naam': 'Seizoen', 'seizoen': 'Seizoen',
            'aantal_wedstrijden': 'Aantal wedstrijden'
        }
        seasons_display = seasons_display.rename(columns=col_map)
        kolommen = ['Seizoen', 'Startdatum', 'Einddatum', 'Aantal wedstrijden', 'Totaal goals', 'Unieke spelers', 'Winnaar', '2e plaats', '3e plaats']
        st.dataframe(seasons_display[[k for k in kolommen if k in seasons_display.columns]], hide_index=True, use_container_width=True)


    # All-time ranglijsten direct onder seizoenen tabel
    player_stats = create_all_time_leaderboards(matches_df)
    show_all_time_leaderboards(player_stats)

    # Extra analyses: timeline, activiteit vs winpercentage (all-time)
    # Geen extra subheaders, want de grafieken hebben titels
    show_timeline_chart(matches_df)
    show_activity_vs_winrate_scatter(matches_df, key_suffix="seizoenen")

    # Toon cross-seizoen analyses altijd (zonder extra subheader)
    show_cross_season_charts(matches_df, seasons_df)

    # Seizoenselectie: alle of specifiek seizoen (nu na algemene grafieken)
    season_options = ["Alle seizoenen"]
    if not seasons_df.empty:
        for _, row in seasons_df.iterrows():
            season_name = row.get('seizoen_naam') or row.get('seizoen') or str(row.get('jaar', 'Onbekend'))
            season_options.append(season_name)
        from datetime import date
        today = date.today()
        default_idx = 0
        for i, row in seasons_df.iterrows():
            start_col = 'start_datum' if 'start_datum' in row else 'startdatum'
            end_col = 'eind_datum' if 'eind_datum' in row else 'einddatum'
            season_start = pd.to_datetime(row[start_col]).date()
            season_end = pd.to_datetime(row[end_col]).date()
            if season_start <= today <= season_end:
                default_idx = i + 1
                break
        selected = st.selectbox("Selecteer seizoen:", season_options, index=default_idx)
    else:
        selected = season_options[0]

    # Toon analyses voor geselecteerd seizoen of alle seizoenen
    if selected == "Alle seizoenen":
        st.subheader("Analyse: Alle seizoenen")
        show_individual_season_analysis({'seizoen_naam': 'Alle seizoenen'}, matches_df)
    elif not seasons_df.empty:
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
            # Normaliseer seizoensgrenzen
            season_start = normalize_timestamp_series(pd.Series([season_start])).iloc[0]
            season_end = normalize_timestamp_series(pd.Series([season_end])).iloc[0]
            ts = matches_df['timestamp']
            if hasattr(ts.dt, 'tz') and ts.dt.tz is not None:
                matches_df = matches_df.copy()
                matches_df['timestamp'] = normalize_timestamp_series(ts)
            season_matches = matches_df[(matches_df['timestamp'] >= season_start) & (matches_df['timestamp'] <= season_end)]
            show_individual_season_analysis(season_row, season_matches)
