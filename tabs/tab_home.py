"""
TAB 1: Home module voor tafelvoetbal app
Bevat ELO ranking tabel en speler geschiedenis functies
"""
import streamlit as st
import pandas as pd
import firestore_service as db
from utils.utils_seizoen import get_current_season, generate_prinsjesdag_seasons


from utils.utils import IGNORE_PLAYERS
from analytics import get_vectorized_player_stats

def _parse_elo_int(rating_value, default=1000):
    """Zet een ELO-waarde veilig om naar een afgerond geheel getal."""
    try:
        if rating_value is None or rating_value == '' or pd.isna(rating_value):
            return default
        return int(round(float(str(rating_value).replace(',', '.'))))
    except (ValueError, TypeError):
        return default

@st.cache_data
def calculate_stats(players, matches, elo_df=None, season_start=None, season_end=None):
    """Bereken statistieken voor alle spelers met vectorized Pandas operations"""
    if matches is None or matches.empty:
        # Fallback voor spelers zonder wedstrijden
        stats_list = []
        for _, player in players.iterrows():
            stats_list.append({
                'Speler': player.get('speler_naam', ''),
                'ELO': _parse_elo_int(player.get('rating', 1000)),
                'Gespeeld': 0, 'Voor': 0, 'Tegen': 0, 'Doelsaldo': 0, 'Klinkers': 0, 'Win%': 0.0, 'Gem. Goals': 0.0
            })
        return pd.DataFrame(stats_list)

    # Gebruik de geoptimaliseerde helper uit analytics.py
    vector_stats = get_vectorized_player_stats(matches)
    
    stats_list = []
    for _, player in players.iterrows():
        p_name = str(player['speler_naam'])
        # Case-insensitive match voor robuustheid
        p_stats = vector_stats[vector_stats['Speler'].str.lower() == p_name.lower()]
        
        if p_stats.empty:
            stats = {
                'Gespeeld': 0, 'Voor': 0, 'Tegen': 0, 'Doelsaldo': 0, 'Klinkers': 0, 
                'Win%': 0.0, 'Gem. Goals': 0.0, 'Speler': p_name
            }
        else:
            row = p_stats.iloc[0]
            stats = {
                'Gespeeld': int(row['Matches']),
                'Voor': int(row['Goals']),
                'Tegen': int(row['Goals_Tegen']),
                'Doelsaldo': int(row['Goal_Diff']),
                'Gem. Goals': round(float(row['Goals_Per_Match']), 2),
                'Klinkers': int(row['Klinkers']),
                'Win%': round(float(row['Winrate']), 1),
                'Speler': p_name
            }
        
        # Bepaal ELO rating voor dit specifieke seizoen
        rating_value = 1000 # Default ELO per seizoen
        if elo_df is not None and not elo_df.empty and season_start is not None and season_end is not None:
            # Converteer naar naive timestamps voor veilige vergelijking
            s_start = pd.to_datetime(season_start)
            if s_start.tzinfo is not None: s_start = s_start.tz_localize(None)
            s_end = pd.to_datetime(season_end)
            if s_end.tzinfo is not None: s_end = s_end.tz_localize(None)
            
            elo_ts = db.normalize_timestamp_series(
                pd.to_datetime(elo_df['timestamp'], errors='coerce', format='mixed', utc=True)
            )
            # Haal logs voor deze speler in dit seizoen
            p_elo_logs = elo_df[(elo_df['speler_naam'].str.lower() == p_name.lower()) &
                                (elo_ts >= s_start) &
                                (elo_ts <= s_end)]
            if not p_elo_logs.empty:
                p_valid = p_elo_logs
                if 'match_id' in p_valid.columns:
                    non_reset = p_valid[p_valid['match_id'].fillna('').astype(str) != 'SEASON_RESET']
                    if not non_reset.empty:
                        p_valid = non_reset
                p_valid = p_valid.assign(_ts_sort=elo_ts.loc[p_valid.index])
                sort_c = ['_ts_sort'] + (['match_id'] if 'match_id' in p_valid.columns else [])
                rating_value = p_valid.sort_values(sort_c, ascending=True, na_position='first', kind='mergesort').iloc[-1]['rating']
        else:
            # Fallback naar huidige all-time rating als we geen seizoensinfo hebben
            rating_value = player.get('rating', 1000)
            
        stats['ELO'] = _parse_elo_int(rating_value)
            
        stats_list.append(stats)
        
    return pd.DataFrame(stats_list)


@st.cache_data
def calculate_elo_trends(elo_df, season_start=None, season_end=None):
    """Bereken het verschil in ELO per speler op basis van de laatste wedstrijd (binnen seizoen indien opgegeven)."""
    if elo_df is None or elo_df.empty:
        return {}

    trends = {}
    df = elo_df.copy()
    df['speler_naam'] = df['speler_naam'].astype(str)
    df['_ts_naive'] = db.normalize_timestamp_series(
        pd.to_datetime(df['timestamp'], errors='coerce', format='mixed', utc=True)
    )

    has_mid = 'match_id' in df.columns
    if has_mid:
        mid_str = df['match_id'].fillna('').astype(str).str.strip()
        is_reset = mid_str == 'SEASON_RESET'
        is_match = (mid_str != '') & (~is_reset)
    else:
        is_reset = pd.Series(False, index=df.index)
        is_match = pd.Series(True, index=df.index)

    s_start = None
    if season_start is not None and season_end is not None:
        s_start, s_end = db._season_bounds_naive(season_start, season_end)
        in_season = (df['_ts_naive'] >= s_start) & (df['_ts_naive'] <= s_end)
        season_match_df = df[is_match & in_season].copy()
        season_reset_df = df[is_reset & in_season].copy()
        pre_season_match_df = df[is_match & (df['_ts_naive'] < s_start)].copy()
    else:
        season_match_df = df[is_match].copy()
        season_reset_df = df[is_reset].copy()
        pre_season_match_df = pd.DataFrame()

    sort_cols = ['_ts_naive'] + (['match_id'] if has_mid else [])
    season_match_df = season_match_df.sort_values(sort_cols, ascending=True, na_position='first', kind='mergesort')

    reset_map = {}
    if not season_reset_df.empty:
        season_reset_df = season_reset_df.sort_values(['_ts_naive'], ascending=True, na_position='first', kind='mergesort')
        for _, rrow in season_reset_df.drop_duplicates(subset=['speler_naam'], keep='last').iterrows():
            reset_map[rrow['speler_naam']] = float(rrow['rating'])

    pre_last_map = {}
    if not pre_season_match_df.empty:
        pre_season_match_df = pre_season_match_df.sort_values(sort_cols, ascending=True, na_position='first', kind='mergesort')
        for _, prow in pre_season_match_df.drop_duplicates(subset=['speler_naam'], keep='last').iterrows():
            pre_last_map[prow['speler_naam']] = float(prow['rating'])

    for speler, group in season_match_df.groupby('speler_naam'):
        ratings = group['rating'].tolist()
        if len(ratings) >= 2:
            trends[speler] = int(round(float(ratings[-1]) - float(ratings[-2])))
        elif len(ratings) == 1 and s_start is not None:
            r0 = float(ratings[0])
            if speler in reset_map:
                prev = reset_map[speler]
            elif speler not in pre_last_map or (850.0 <= r0 <= 1150.0):
                prev = 1000.0
            else:
                prev = pre_last_map[speler]
            trends[speler] = int(round(r0 - prev))
        else:
            trends[speler] = 0

    return trends



def show_elo_rankings(players_df, matches_df, elo_df=None, current_season=None):
    """Toon de huidige ELO rankings tabel"""
    if matches_df is None or matches_df.empty:
        st.info("Er zijn nog geen wedstrijden gespeeld.")
        return

    if current_season is not None:
        match_dates = db.normalize_timestamp_series(
            pd.to_datetime(matches_df['timestamp'], errors='coerce', format='mixed', utc=True)
        )
        season_start, season_end = db._season_bounds_naive(
            current_season.get('start_datum', current_season.get('startdatum')),
            current_season.get('eind_datum', current_season.get('einddatum'))
        )
        season_matches = matches_df[(match_dates >= season_start) & (match_dates <= season_end)]

        season_players = set()
        for col in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
            if col in season_matches.columns:
                season_players.update(season_matches[col].dropna().astype(str).tolist())

        filtered_players_df = players_df[players_df['speler_naam'].isin(season_players)].drop_duplicates(subset=['speler_naam'], keep='first')
        
        # Voor de berekening van stats gebruiken we alleen de matches van dit seizoen
        stats_df = calculate_stats(filtered_players_df, season_matches, elo_df, season_start, season_end)
    else:
        st.info("Geen actief seizoen geselecteerd voor ranglijst.")
        return

    # Sorteer en selecteer kolommen voor weergave
    if stats_df.empty:
        st.info("Geen spelers hebben dit seizoen een wedstrijd gespeeld.")
        return
        
    # Filter 'Niemand' spelers uit - Case-insensitive
    stats_df = stats_df[~stats_df['Speler'].str.lower().str.strip().isin(IGNORE_PLAYERS)]
    
    if stats_df.empty:
        st.info("Geen geldige spelers gevonden in dit seizoen.")
        return

    # Trend berekenen (numeriek binnen het huidige seizoen)
    trends = calculate_elo_trends(elo_df, season_start, season_end)
    stats_df['Trend'] = stats_df['Speler'].map(lambda x: int(round(trends.get(x, 0))))

        
    # Sortering: Puur op ELO (en tie-breakers), zoals gevraagd door de gebruiker
    # De 'Gerangschikt' status wordt alleen nog gebruikt voor visuele markering (grijs/italic)
    stats_df['Gerangschikt'] = stats_df['Gespeeld'] >= 3
    
    display_df = stats_df.copy().sort_values(
        by=['ELO', 'Doelsaldo', 'Win%'], 
        ascending=[False, False, False]
    ).reset_index(drop=True)
    
    display_df['ELO'] = display_df['ELO'].round(0).astype(int)
    display_df['Gem. Goals'] = display_df.apply(
        lambda r: f"{r['Gem. Goals']:.2f}" if r['Gespeeld'] >= 3 else "-", axis=1
    )
    display_df['Win%'] = display_df.apply(
        lambda r: f"{r['Win%']:.1f}%" if r['Gespeeld'] >= 3 else "-", axis=1
    )
    
    ranked_top3 = display_df[display_df['Gerangschikt']].index[:3].tolist()

    def highlight_ranked_and_top3(row):
        idx = row.name
        styles = [''] * len(row)
        
        # Markeer ongerangschikte spelers (minder dan 3 potjes)
        if not row.get('Gerangschikt', True):
            return ['color: #9e9e9e; font-style: italic'] * len(row)
        
        # Markeer de echte top 3 van gerangschikte spelers
        if len(ranked_top3) > 0 and idx == ranked_top3[0]:
            return ['background-color: #d4edda; font-weight: bold'] * len(row)
        elif len(ranked_top3) > 1 and idx == ranked_top3[1]:
            return ['background-color: #eafaf1'] * len(row)
        elif len(ranked_top3) > 2 and idx == ranked_top3[2]:
            return ['background-color: #f4fbf7'] * len(row)
        
        return styles

    def color_trend(val):
        try:
            v = int(val)
            if v > 0: return 'color: #28a745; font-weight: bold;' # Groen
            if v < 0: return 'color: #dc3545; font-weight: bold;' # Rood
        except Exception:
            pass
        return 'color: #6c757d;' # Grijs

    def format_trend(val):
        try:
            v = int(val)
            if v > 0: return f"+{v}"
            if v < 0: return f"{v}"
            return "0"
        except Exception:
            return "-"
            
    # Kolomvolgorde aanpassen: Trend naast ELO
    cols = ['Speler', 'ELO', 'Trend', 'Gespeeld', 'Win%', 'Gem. Goals', 'Voor', 'Tegen', 'Doelsaldo', 'Klinkers', 'Gerangschikt']
    styled = display_df[cols].style.apply(highlight_ranked_and_top3, axis=1).map(color_trend, subset=['Trend'])
    
    # Gebruik hide op de styler (werkt in nieuwere pandas)
    try:
        styled = styled.hide(['Gerangschikt'], axis=1)
    except Exception:
        pass
    
    styled = styled.format({
        'Trend': format_trend,
    })
    
    st.dataframe(
        styled,
        width='stretch',
        height=max(400, 35 * len(display_df) + 100),
        column_config={
            "Gerangschikt": None, # Forceer verbergen in Streamlit UI mocht styled.hide falen
            "ELO": st.column_config.NumberColumn("ELO", help="Huidige ELO-rating in dit seizoen (start op 1000 bij seizoensbegin)"),
            "Trend": st.column_config.TextColumn("Trend", help="ELO verschil t.o.v. vorige wedstrijd (exclusief seizoens-resets)"),
            "Gespeeld": st.column_config.NumberColumn("Gespeeld", help="Aantal gespeelde wedstrijden in dit seizoen (min. 3 nodig voor officiële rangschikking)"),
            "Win%": st.column_config.TextColumn("Win%", help="Winstpercentage (zichtbaar vanaf 3 gespeelde wedstrijden)"),
            "Gem. Goals": st.column_config.TextColumn("Gem. Goals", help="Gemiddeld aantal goals per wedstrijd (zichtbaar vanaf 3 gespeelde wedstrijden)"),
            "Doelsaldo": st.column_config.NumberColumn("Doelsaldo", help="Verschil tussen doelpunten vóór en tegen in dit seizoen"),
            "Klinkers": st.column_config.NumberColumn("Klinkers", help="Aantal gescoorde klinkers in dit seizoen (+15 ELO bonus per klinker)"),
        }
    )
    st.caption("💡 **Uitleg ranglijst:** Spelers zijn officieel *gerangschikt* vanaf **3 gespeelde wedstrijden** in het huidige seizoen (de top 3 is groen gemarkeerd). Spelers met minder dan 3 wedstrijden worden *cursief/grijs* weergegeven.")



def render_home_tab(players_df, matches_df, seasons_df=None, elo_df=None):
    """Render de complete Home tab"""
    st.header("🏆 ELO Ranglijst")

    with st.expander("👋 Nieuw hier? Bekijk de Snelstart & Spelregels (Tutorial)", expanded=False):
        from tabs.tab_colofon import render_quick_tutorial
        render_quick_tutorial()
        st.info("ℹ️ Meer weten over de wiskundige ELO-formule, alle tabbladen of veelgestelde vragen? Ga naar het tabblad **ℹ️ Colofon**.")

    if players_df is None or players_df.empty:
        st.info("Nog geen spelers geregistreerd. Ga naar 'Spelers' om spelers toe te voegen.")
        return

    # Gebruik de meegegeven seasons_df of genereer ze
    if seasons_df is None or seasons_df.empty:
        seasons_df = generate_prinsjesdag_seasons(matches_df)
        
    huidig_seizoen = get_current_season(seasons_df)

    if huidig_seizoen is not None:
        # Ondersteun beide formaten voor robuustheid
        start_dt = pd.to_datetime(huidig_seizoen.get('start_datum', huidig_seizoen.get('startdatum')))
        end_dt = pd.to_datetime(huidig_seizoen.get('eind_datum', huidig_seizoen.get('einddatum')))
        
        st.info(f"📅 **Huidig Seizoen:** {huidig_seizoen['seizoen_naam']} ({start_dt.strftime('%d-%m-%Y')} t/m {end_dt.strftime('%d-%m-%Y')})")

        # Ranglijst tonen
        show_elo_rankings(players_df, matches_df, elo_df, huidig_seizoen)
        
        # Laatste 10 uitslagen
        if not matches_df.empty:
            st.subheader("🕒 Laatste 10 uitslagen")
            
            # Selecteer en formatteer data (sorteer expliciet aflopend op timestamp)
            recent_matches = matches_df.sort_values('timestamp', ascending=False).head(10).copy()
            
            # Formatteer timestamp voor weergave
            if 'timestamp' in recent_matches.columns:
                recent_matches['timestamp'] = pd.to_datetime(recent_matches['timestamp']).dt.strftime('%d-%m-%Y %H:%M')
            
            # Kolomvolgorde forceren (timestamp eerst)
            display_cols = [
                'timestamp', 'thuis_1', 'thuis_2', 'uit_1', 'uit_2', 
                'thuis_score', 'uit_score', 
                'klinkers_thuis_1', 'klinkers_thuis_2', 'klinkers_uit_1', 'klinkers_uit_2'
            ]
            # Alleen kolommen tonen die daadwerkelijk bestaan
            cols_to_show = [c for c in display_cols if c in recent_matches.columns]
            
            st.dataframe(
                recent_matches[cols_to_show],
                hide_index=True,
                width='stretch'
            )
    else:
        st.warning("Geen actief Controlejaar gevonden voor de huidige datum.")
        if seasons_df is not None and not seasons_df.empty:
            st.write("Beschikbare seizoenen:")
            # Bepaal welke kolommen beschikbaar zijn voor weergave
            cols_to_show = ['seizoen_naam']
            if 'start_datum' in seasons_df.columns: cols_to_show.append('start_datum')
            elif 'startdatum' in seasons_df.columns: cols_to_show.append('startdatum')
            if 'eind_datum' in seasons_df.columns: cols_to_show.append('eind_datum')
            elif 'einddatum' in seasons_df.columns: cols_to_show.append('einddatum')
            
            st.dataframe(seasons_df[cols_to_show], width='stretch')

def show_elo_history_selector(players_df, matches_df=None):
    """Toon speler selectie voor ELO geschiedenis."""
    # (Bestaande implementatie was complex en redundant, we houden het hier simpel voor de home tab)
    player_names = sorted(players_df['speler_naam'].tolist())
    selected_player = st.selectbox("Bekijk ELO verloop van speler:", player_names, key="home_elo_history")
    
    if selected_player:
        history_df = db.get_elo_history(_ttl=60, speler_naam=selected_player)
        if history_df is not None and not history_df.empty:
            history_df = history_df.sort_values('timestamp')
            history_df['Match #'] = range(1, len(history_df) + 1)
            st.line_chart(history_df, x='Match #', y='rating', width='stretch')
        else:
            st.caption(f"Geen geschiedenis gevonden voor {selected_player}")
