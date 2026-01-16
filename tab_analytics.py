import streamlit as st
import pandas as pd
from firestore_service import normalize_timestamp_series
from analytics import (
    show_cross_season_charts,
    show_individual_season_analysis,
    create_all_time_leaderboards,
    show_all_time_leaderboards
)

def render_seizoenen_tab(matches_df, players_df, seasons_df):
    st.header("📅 Seizoensanalyse")

    # Cross-seizoen analyses direct bovenaan
    st.subheader("📊 Cross-Seizoen Analyses")

    # Toon seizoenen tabel bovenaan
    if not seasons_df.empty:
        st.subheader("Seizoenen overzicht")
        seasons_display = seasons_df.copy()
        extra_metrics = []
        for _, row in seasons_display.iterrows():
            start = pd.to_datetime(row['startdatum'])
            end = pd.to_datetime(row['einddatum'])
            seizoen_matches = matches_df[(matches_df['timestamp'] >= start) & (matches_df['timestamp'] <= end)]
            totaal_goals = int(seizoen_matches['thuis_score'].sum() + seizoen_matches['uit_score'].sum())
            unieke_spelers = set()
            for _, m in seizoen_matches.iterrows():
                unieke_spelers.update([
                    m.get('thuis_1', None), m.get('thuis_2', None),
                    m.get('uit_1', None), m.get('uit_2', None)
                ])
            unieke_spelers = len([p for p in unieke_spelers if p])
            # Top 3 winnaars bepalen + ELO (herbruikbare logica)
            from analytics import get_season_top3_elo
            from firestore_service import get_elo_logs
            winnaar, tweede, derde = '-', '-', '-'
            winnaar_elo, tweede_elo, derde_elo = '', '', ''
            elo_df = get_elo_logs()
            top3 = get_season_top3_elo(elo_df, seizoen_matches)
            if len(top3) > 0:
                winnaar, winnaar_elo = top3[0][0], f" ({int(top3[0][1])})"
            if len(top3) > 1:
                tweede, tweede_elo = top3[1][0], f" ({int(top3[1][1])})"
            if len(top3) > 2:
                derde, derde_elo = top3[2][0], f" ({int(top3[2][1])})"
            extra_metrics.append({
                'totaal_goals': totaal_goals,
                'unieke_spelers': unieke_spelers,
                'winnaar': winnaar + winnaar_elo,
                'tweede': tweede + tweede_elo,
                'derde': derde + derde_elo
            })
        seasons_display['Totaal goals'] = [m['totaal_goals'] for m in extra_metrics]
        seasons_display['Unieke spelers'] = [m['unieke_spelers'] for m in extra_metrics]
        seasons_display['Winnaar'] = [m['winnaar'] for m in extra_metrics]
        seasons_display['2e plaats'] = [m['tweede'] for m in extra_metrics]
        seasons_display['3e plaats'] = [m['derde'] for m in extra_metrics]
        for col in ['startdatum', 'einddatum', 'start_datum', 'eind_datum']:
            if col in seasons_display.columns:
                seasons_display[col] = pd.to_datetime(seasons_display[col]).dt.strftime('%d-%m-%Y %H:%M')
        col_map = {
            'startdatum': 'Startdatum',
            'einddatum': 'Einddatum',
            'start_datum': 'Startdatum',
            'eind_datum': 'Einddatum',
            'seizoen_naam': 'Seizoen',
            'seizoen': 'Seizoen',
            'aantal_wedstrijden': 'Aantal wedstrijden',
            'Totaal goals': 'Totaal goals',
            'Unieke spelers': 'Unieke spelers',
            'Winnaar': 'Winnaar',
            '2e plaats': '2e plaats',
            '3e plaats': '3e plaats',
        }
        seasons_display = seasons_display.rename(columns=col_map)
        kolommen = ['Seizoen', 'Startdatum', 'Einddatum', 'Aantal wedstrijden', 'Totaal goals', 'Unieke spelers', 'Winnaar', '2e plaats', '3e plaats']
        seasons_display = seasons_display[[k for k in kolommen if k in seasons_display.columns]]
        st.dataframe(seasons_display, width='stretch')


    # All-time ranglijsten direct onder seizoenen tabel
    player_stats = create_all_time_leaderboards(matches_df)
    show_all_time_leaderboards(player_stats)

    # Extra analyses: timeline
    from analytics import show_timeline_chart

    # Geen extra subheaders, want de grafieken hebben titels
    show_timeline_chart(matches_df)

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
            # Toevoegen: activiteit vs winpercentage voor geselecteerd seizoen
            from analytics import show_activity_vs_winrate_scatter
            show_activity_vs_winrate_scatter(season_matches, key_suffix=f"seizoen_{selected}")
