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
        # Extra metrics per seizoen
        extra_metrics = []
        for _, row in seasons_display.iterrows():
            # Filter wedstrijden voor dit seizoen
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
            # Winnaar bepalen: speler met hoogste ELO in het seizoen (debug info toegevoegd)
            winnaar = None
            debug_info = ""
            if not seizoen_matches.empty:
                # Verzamel ALLE spelers die in het seizoen hebben gespeeld
                alle_spelers = set()
                for _, m in seizoen_matches.iterrows():
                    alle_spelers.update([
                        m.get('thuis_1', None), m.get('thuis_2', None),
                        m.get('uit_1', None), m.get('uit_2', None)
                    ])
                alle_spelers = {p for p in alle_spelers if p}
                # Zoek ELO's van deze spelers op of vóór de laatste dag van het seizoen, gebruik match_id voor robuustheid
                from firestore_service import get_elo_logs
                elo_df = get_elo_logs()
                if not elo_df.empty and 'timestamp' in elo_df.columns:
                    elo_df['timestamp'] = pd.to_datetime(elo_df['timestamp'], errors='coerce')
                    try:
                        elo_df['timestamp'] = elo_df['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
                    except Exception:
                        elo_df['timestamp'] = elo_df['timestamp'].dt.tz_localize(None)
                    # Filter alleen ELO's tot en met de laatste wedstrijd van het seizoen
                    laatste_dag = seizoen_matches['timestamp'].max()
                    laatste_dag_naive = pd.to_datetime(laatste_dag)
                    if hasattr(laatste_dag_naive, 'tzinfo') and laatste_dag_naive.tzinfo is not None:
                        try:
                            laatste_dag_naive = laatste_dag_naive.tz_convert('UTC').tz_localize(None)
                        except Exception:
                            laatste_dag_naive = laatste_dag_naive.tz_localize(None)
                    # Pak alle match_ids van dit seizoen tot en met de laatste dag
                    match_ids_in_season = set(seizoen_matches[seizoen_matches['timestamp'] <= laatste_dag_naive]['match_id'])
                    elo_df = elo_df[(elo_df['match_id'].isin(match_ids_in_season)) & (elo_df['speler_naam'].isin(alle_spelers))]
                    # Voor elke speler: pak de ELO met de hoogste timestamp (laatste ELO in seizoen)
                    laatste_elo = elo_df.sort_values('timestamp').groupby('speler_naam').last().reset_index()
                    debug_info += f"<details><summary>Debug: ELO's op laatste dag voor alle spelers in seizoen</summary>"
                    debug_info += f"<br>Laatste dag: {laatste_dag_naive}"
                    debug_info += f"<br>Spelers in seizoen: {sorted(list(alle_spelers))}"
                    debug_info += f"<br>ELO-log entries gevonden: {len(laatste_elo)}"
                    if not laatste_elo.empty:
                        debug_info += "<br><table><tr><th>Speler</th><th>ELO</th><th>Tijdstip</th></tr>"
                        for _, row_elo in laatste_elo.iterrows():
                            debug_info += f"<tr><td>{row_elo['speler_naam']}</td><td>{row_elo['rating']}</td><td>{row_elo['timestamp']}</td></tr>"
                        debug_info += "</table>"
                        winnaar_row = laatste_elo.sort_values('rating', ascending=False).iloc[0]
                        winnaar = winnaar_row['speler_naam']
                    else:
                        debug_info += "<br><b>Geen ELO-log entries gevonden voor deze spelers tot en met laatste dag van het seizoen.</b>"
                    debug_info += "</details>"
                else:
                    debug_info += f"<details><summary>Debug: ELO-log leeg of geen 'timestamp' kolom</summary>"
                    debug_info += f"<br>Spelers in seizoen: {sorted(list(alle_spelers))}"
                    debug_info += f"<br>ELO-log is leeg of bevat geen 'timestamp' kolom."
                    debug_info += "</details>"
            # Toon debug info in Streamlit
            if debug_info:
                st.markdown(debug_info, unsafe_allow_html=True)
            extra_metrics.append({
                'totaal_goals': totaal_goals,
                'unieke_spelers': unieke_spelers,
                'winnaar': winnaar or "-"
            })
        # Voeg toe aan DataFrame
        seasons_display['Totaal goals'] = [m['totaal_goals'] for m in extra_metrics]
        seasons_display['Unieke spelers'] = [m['unieke_spelers'] for m in extra_metrics]
        seasons_display['Winnaar'] = [m['winnaar'] for m in extra_metrics]
        # Format start/einddatum netjes
        for col in ['startdatum', 'einddatum', 'start_datum', 'eind_datum']:
            if col in seasons_display.columns:
                seasons_display[col] = pd.to_datetime(seasons_display[col]).dt.strftime('%d-%m-%Y %H:%M')
        # Vertaal kolomnamen
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
        }
        seasons_display = seasons_display.rename(columns=col_map)
        # Kolomvolgorde: Seizoen, Startdatum, Einddatum, Aantal wedstrijden, Totaal goals, Unieke spelers, Winnaar
        kolommen = ['Seizoen', 'Startdatum', 'Einddatum', 'Aantal wedstrijden', 'Totaal goals', 'Unieke spelers', 'Winnaar']
        seasons_display = seasons_display[[k for k in kolommen if k in seasons_display.columns]]
        st.dataframe(seasons_display, width='stretch')

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

    # All-time ranglijsten direct onder seizoenen tabel en selectie
    player_stats = create_all_time_leaderboards(matches_df)
    show_all_time_leaderboards(player_stats)

    # Extra analyses: timeline, activiteit vs winpercentage
    from analytics import show_timeline_chart, show_activity_vs_winrate_scatter

    st.subheader("📈 Wedstrijden per dag (tijdlijn)")
    show_timeline_chart(matches_df)

    st.subheader("📊 Activiteit vs Winpercentage")
    show_activity_vs_winrate_scatter(matches_df, key_suffix="seizoenen")

    # Toon cross-seizoen analyses altijd
    show_cross_season_charts(matches_df, seasons_df)

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
            # Maak grenzen timezone-naive
            if hasattr(season_start, 'tzinfo') and season_start.tzinfo is not None:
                season_start = season_start.tz_convert('UTC').tz_localize(None)
            if hasattr(season_end, 'tzinfo') and season_end.tzinfo is not None:
                season_end = season_end.tz_convert('UTC').tz_localize(None)
            # Zorg dat de timestamps in matches_df ook naive zijn
            ts = matches_df['timestamp']
            if hasattr(ts.dt, 'tz') and ts.dt.tz is not None:
                matches_df = matches_df.copy()
                matches_df['timestamp'] = ts.dt.tz_convert('UTC').dt.tz_localize(None)
            season_matches = matches_df[(matches_df['timestamp'] >= season_start) & (matches_df['timestamp'] <= season_end)]
            show_individual_season_analysis(season_row, season_matches)
