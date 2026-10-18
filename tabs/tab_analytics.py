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
    show_activity_vs_winrate_scatter,
    show_goals_bar_chart_season,
    show_unique_players_bar_chart,
    show_winrate_bar_chart,
    get_vectorized_player_stats,
    get_absolute_top3_elo
)
from utils.utils import IGNORE_PLAYERS

def render_seizoenen_tab(matches_df, players_df, seasons_df, elo_df=None):
    st.header("📅 Seizoensanalyse")
    if elo_df is None:
        elo_df = get_elo_logs()

    # --- 1. All-time Recordhouders (Prominent bovenaan) ---
    st.subheader("🏆 All-time Recordhouders")
    abs_top3 = get_absolute_top3_elo(elo_df)
    if abs_top3:
        cols = st.columns(len(abs_top3))
        for i, (naam, elo) in enumerate(abs_top3):
            with cols[i]:
                st.metric(f"Recordhouder {i+1} (Peak ELO)", naam, f"{int(elo)} pts")
    st.divider()

    # --- 2. Seizoenen overzicht ---
    seasons_with_stats = pd.DataFrame()
    if not seasons_df.empty and matches_df is not None and not matches_df.empty:
        st.subheader("Seizoenen overzicht")
        
        # Voorbereiden extra metrics (Vectorized)
        all_matches_proc = matches_df.copy()
        all_matches_proc['timestamp'] = pd.to_datetime(all_matches_proc['timestamp'], utc=True)
        all_matches_proc['ts_naive'] = all_matches_proc['timestamp'].dt.tz_localize(None)
        
        seasons_display = seasons_df.copy()
        enriched_rows = []
        
        for _, row in seasons_display.iterrows():
            start_col = 'start_datum' if 'start_datum' in row else 'startdatum'
            end_col = 'eind_datum' if 'eind_datum' in row else 'einddatum'
            start = pd.to_datetime(row[start_col], utc=True).replace(tzinfo=None)
            end = pd.to_datetime(row[end_col], utc=True).replace(tzinfo=None)
            
            s_matches = all_matches_proc[(all_matches_proc['ts_naive'] >= start) & (all_matches_proc['ts_naive'] <= end)]
            match_count = len(s_matches)
            
            # Sla lege historische seizoenen zonder wedstrijden over (behalve als het het huidige seizoen is)
            now_naive = pd.Timestamp.now()
            is_current = start <= now_naive <= end
            if match_count == 0 and not is_current:
                continue
            
            # Goals & Players (Vectorized)
            totaal_goals = int(s_matches['thuis_score'].sum() + s_matches['uit_score'].sum()) if match_count > 0 else 0
            gem_goals = round(totaal_goals / match_count, 1) if match_count > 0 else 0.0
            p_cols = ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']
            existing_p_cols = [c for c in p_cols if c in s_matches.columns]
            u_players = pd.unique(s_matches[existing_p_cols].values.ravel()) if match_count > 0 else []
            u_players_count = len([p for p in u_players if p and not pd.isna(p) and str(p).lower().strip() not in IGNORE_PLAYERS])
            
            top3 = get_season_top3_elo(elo_df, s_matches) if match_count > 0 else []
            
            w = f"{top3[0][0]} ({int(top3[0][1])})" if len(top3) > 0 else "-"
            t2 = f"{top3[1][0]} ({int(top3[1][1])})" if len(top3) > 1 else "-"
            t3 = f"{top3[2][0]} ({int(top3[2][1])})" if len(top3) > 2 else "-"
            
            row_dict = row.to_dict()
            row_dict.update({
                'aantal_wedstrijden': match_count,
                'totaal_goals': totaal_goals,
                'gemiddelde_goals': gem_goals,
                'unieke_spelers': u_players_count,
                'Totaal goals': totaal_goals,
                'Unieke spelers': u_players_count,
                'Winnaar': w,
                '2e plaats': t2,
                '3e plaats': t3
            })
            enriched_rows.append(row_dict)
            
        seasons_with_stats = pd.DataFrame(enriched_rows)
        if not seasons_with_stats.empty:
            seasons_final = seasons_with_stats.copy()
            
            # Formattering van datums
            for col in ['startdatum', 'einddatum', 'start_datum', 'eind_datum']:
                if col in seasons_final.columns:
                    seasons_final[col] = pd.to_datetime(seasons_final[col], utc=True).dt.strftime('%d-%m-%Y %H:%M')
                    
            col_map = {
                'startdatum': 'Startdatum', 'einddatum': 'Einddatum',
                'start_datum': 'Startdatum', 'eind_datum': 'Einddatum',
                'seizoen_naam': 'Seizoen', 'seizoen': 'Seizoen',
                'aantal_wedstrijden': 'Aantal wedstrijden'
            }
            seasons_final = seasons_final.rename(columns=col_map)
            kolommen = ['Seizoen', 'Startdatum', 'Einddatum', 'Aantal wedstrijden', 'Totaal goals', 'Unieke spelers', 'Winnaar', '2e plaats', '3e plaats']
            
            st.dataframe(
                seasons_final[[k for k in kolommen if k in seasons_final.columns]], 
                hide_index=True, 
                width='stretch'
            )

    st.divider()

    # --- 3. Seizoenselectie: filtert de rest van de pagina ---
    active_seasons_df = seasons_with_stats if not seasons_with_stats.empty else seasons_df
    season_options = ["Alle seizoenen"]
    if not active_seasons_df.empty:
        for _, row in active_seasons_df.iterrows():
            season_name = row.get('seizoen_naam') or row.get('seizoen') or str(row.get('jaar', 'Onbekend'))
            season_options.append(season_name)
        
    selected = st.selectbox("Selecteer periode voor onderstaande analyses:", season_options, index=0)

    # Filter data
    filtered_matches = matches_df.copy()
    filtered_elo_df = elo_df.copy() if elo_df is not None else pd.DataFrame()
    if selected != "Alle seizoenen" and not active_seasons_df.empty:
        season_row = None
        for _, row in active_seasons_df.iterrows():
            season_name = row.get('seizoen_naam') or row.get('seizoen') or str(row.get('jaar', 'Onbekend'))
            if season_name == selected:
                season_row = row
                break
        
        if season_row is not None:
            start_col = 'start_datum' if 'start_datum' in season_row else 'startdatum'
            end_col = 'eind_datum' if 'eind_datum' in season_row else 'einddatum'
            season_start = pd.to_datetime(season_row[start_col], utc=True)
            season_end = pd.to_datetime(season_row[end_col], utc=True)
            season_start = normalize_timestamp_series(pd.Series([season_start])).iloc[0]
            season_end = normalize_timestamp_series(pd.Series([season_end])).iloc[0]
            ts = filtered_matches['timestamp']
            if hasattr(ts.dt, 'tz') and ts.dt.tz is not None:
                filtered_matches['timestamp'] = normalize_timestamp_series(ts)
            filtered_matches = filtered_matches[(filtered_matches['timestamp'] >= season_start) & (filtered_matches['timestamp'] <= season_end)]
            if not filtered_elo_df.empty and 'timestamp' in filtered_elo_df.columns:
                elo_ts = pd.to_datetime(filtered_elo_df['timestamp'], errors='coerce')
                if hasattr(elo_ts.dt, 'tz') and elo_ts.dt.tz is not None:
                    elo_ts = normalize_timestamp_series(elo_ts)
                filtered_elo_df = filtered_elo_df[(elo_ts >= season_start) & (elo_ts <= season_end)]

    # --- 4. Analyse resultaten ---
    st.subheader(f"📊 Analyse resultaten: {selected}")
    
    if filtered_matches.empty:
        st.info("Geen wedstrijden gevonden voor de geselecteerde periode.")
        return

    # Metrics
    total_m = len(filtered_matches)
    total_g = int(filtered_matches['thuis_score'].sum() + filtered_matches['uit_score'].sum())
    avg_g = total_g / total_m if total_m > 0 else 0
    p_cols = ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']
    existing_p_cols = [c for c in p_cols if c in filtered_matches.columns]
    u_players = len([p for p in pd.unique(filtered_matches[existing_p_cols].values.ravel()) if p and not pd.isna(p) and str(p).lower().strip() not in IGNORE_PLAYERS])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Wedstrijden", total_m)
    m2.metric("Totaal Goals", total_g)
    m3.metric("Gem. Goals", f"{avg_g:.1f}")
    m4.metric("Spelers", u_players)

    # Ranglijsten
    player_stats = create_all_time_leaderboards(filtered_matches)
    show_all_time_leaderboards(player_stats, elo_df=filtered_elo_df)

    # Visualisaties
    st.subheader("📈 Visualisaties")
    show_activity_vs_winrate_scatter(filtered_matches, key_suffix=f"filtered_{selected}")
    
    r1 = st.columns(2)
    r2 = st.columns(2)
    with r1[0]: show_goals_bar_chart_season(filtered_matches)
    with r1[1]: show_unique_players_bar_chart(filtered_matches)
    with r2[0]: show_winrate_bar_chart(filtered_matches)
    with r2[1]:
        stats = get_vectorized_player_stats(filtered_matches)
        if stats is not None and not stats.empty and stats['Klinkers'].sum() > 0:
            import plotly.express as px
            k_df = stats.sort_values('Klinkers', ascending=False).head(10)
            fig_k = px.bar(k_df, x='Speler', y='Klinkers', title="Top 10 Klinkers", color='Klinkers', color_continuous_scale='OrRd')
            st.plotly_chart(fig_k, key=f"k_chart_filtered_{selected}")

    show_timeline_chart(filtered_matches)

    if selected == "Alle seizoenen" and not active_seasons_df.empty:
        st.divider()
        show_cross_season_charts(matches_df, active_seasons_df)

