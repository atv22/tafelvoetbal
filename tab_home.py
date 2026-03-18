"""
TAB 1: Home module voor tafelvoetbal app
Bevat ELO ranking tabel en speler geschiedenis functies
"""
import streamlit as st
import pandas as pd
import firestore_service as db
from utils.utils_seizoen import get_current_season, generate_prinsjesdag_seasons


from analytics import get_vectorized_player_stats

@st.cache_data
def calculate_stats(players, matches):
    """Bereken statistieken voor alle spelers met vectorized Pandas operations"""
    if matches is None or matches.empty:
        # Fallback voor spelers zonder wedstrijden
        stats_list = []
        for _, player in players.iterrows():
            stats_list.append({
                'Speler': player.get('speler_naam', ''),
                'ELO': int(player.get('rating', 1000)),
                'Gespeeld': 0, 'Voor': 0, 'Tegen': 0, 'Doelsaldo': 0, 'Klinkers': 0, 'Win%': 0.0, 'Gem. Goals': 0.0
            })
        return pd.DataFrame(stats_list)

    # Gebruik de geoptimaliseerde helper uit analytics.py
    vector_stats = get_vectorized_player_stats(matches)
    
    stats_list = []
    for _, player in players.iterrows():
        p_name = str(player['speler_naam'])
        p_stats = vector_stats[vector_stats['Speler'] == p_name]
        
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
        
        # Rating uit players_df halen (huidige rating)
        rating_value = player.get('rating', 1000)
        if rating_value is None or pd.isna(rating_value):
            rating_value = 1000
        stats['ELO'] = int(rating_value)
        stats_list.append(stats)
        
    return pd.DataFrame(stats_list)


@st.cache_data
def calculate_elo_trends(elo_df):
    """Bereken het verschil in ELO per speler op basis van de laatste 2 verschillende wedstrijden"""
    if elo_df is None or elo_df.empty:
        return {}
    
    trends = {}
    df = elo_df.copy()
    df['speler_naam'] = df['speler_naam'].astype(str)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    
    # Sorteer stabiel: op tijd en dan op de index (volgorde van creatie in DB)
    df = df.sort_values(['timestamp', 'speler_naam'], ascending=[True, True])
    
    for speler, group in df.groupby('speler_naam'):
        # Pak de unieke ratings in chronologische volgorde
        # We willen het verschil tussen de allerlaatste rating en de rating NA de vorige wedstrijd
        if len(group) >= 2:
            ratings = group['rating'].tolist()
            last_elo = ratings[-1]
            prev_elo = ratings[-2]
            trends[speler] = int(last_elo - prev_elo)
        else:
            trends[speler] = 0
            
    return trends


def show_elo_rankings(players_df, matches_df, elo_df=None, current_season=None):
    """Toon de huidige ELO rankings tabel"""
    import pandas as pd

    if matches_df is None or matches_df.empty:
        st.info("Er zijn nog geen wedstrijden gespeeld.")
        return

    if current_season is not None:
        match_dates = pd.to_datetime(matches_df['timestamp']).dt.tz_localize(None)
        season_start = pd.to_datetime(current_season.get('start_datum', current_season.get('startdatum')))
        season_end = pd.to_datetime(current_season.get('eind_datum', current_season.get('einddatum')))
        season_matches = matches_df[(match_dates >= season_start) & (match_dates <= season_end)]

        season_players = set()
        for col in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
            if col in season_matches.columns:
                season_players.update(season_matches[col].dropna().astype(str).tolist())

        filtered_players_df = players_df[players_df['speler_naam'].isin(season_players)]
        
        # Voor de berekening van stats gebruiken we alleen de matches van dit seizoen
        stats_df = calculate_stats(filtered_players_df, season_matches)
    else:
        st.info("Geen actief seizoen geselecteerd voor ranglijst.")
        return

    # Sorteer en selecteer kolommen voor weergave
    if stats_df.empty:
        st.info("Geen spelers hebben dit seizoen een wedstrijd gespeeld.")
        return
        
    # Trend berekenen (numeriek)
    trends = calculate_elo_trends(elo_df)
    stats_df['Trend'] = stats_df['Speler'].map(lambda x: trends.get(x, 0))
        
    display_df = stats_df.copy().sort_values(by='ELO', ascending=False).reset_index(drop=True)
    import numpy as np
    display_df['Gem. Goals'] = display_df.apply(lambda r: r['Gem. Goals'] if r['Gespeeld'] >= 3 else np.nan, axis=1)
    display_df['Win%'] = display_df.apply(lambda r: r['Win%'] if r['Gespeeld'] >= 3 else np.nan, axis=1)
    
    def highlight_top3_lightgreen(row):
        idx = row.name
        if idx == 0:
            return ['background-color: #d4edda'] * len(row)
        elif idx == 1:
            return ['background-color: #eafaf1'] * len(row)
        elif idx == 2:
            return ['background-color: #f4fbf7'] * len(row)
        else:
            return [''] * len(row)

    def color_trend(val):
        try:
            v = int(val)
            if v > 0: return 'color: #28a745; font-weight: bold;' # Groen
            if v < 0: return 'color: #dc3545; font-weight: bold;' # Rood
        except: pass
        return 'color: #6c757d;' # Grijs

    def format_trend(val):
        try:
            v = int(val)
            if v > 0: return f"+{v}"
            if v < 0: return f"{v}"
            return "0"
        except: return "-"
            
    # Kolomvolgorde aanpassen: Trend naast ELO
    cols = ['Speler', 'ELO', 'Trend', 'Gespeeld', 'Win%', 'Gem. Goals', 'Voor', 'Tegen', 'Doelsaldo', 'Klinkers']
    styled = display_df[cols].style.apply(highlight_top3_lightgreen, axis=1).map(color_trend, subset=['Trend'])
    
    styled = styled.format({
        'Trend': format_trend,
        'Win%': lambda x: f'{x:.1f}%' if isinstance(x, (int, float)) and not pd.isna(x) else '-', 
        'Gem. Goals': lambda x: f'{x:.2f}' if isinstance(x, (int, float)) and not pd.isna(x) else '-'
    })
    
    st.dataframe(
        styled,
        use_container_width=True,
        height=max(400, 35 * len(display_df) + 100)
    )


def render_home_tab(players_df, matches_df, seasons_df=None, elo_df=None):
    """Render de complete Home tab"""
    st.header("🏆 ELO Ranglijst")

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
        
        # Filter matches voor weergave van Top 3
        match_dates = pd.to_datetime(matches_df['timestamp']).dt.tz_localize(None)
        season_matches = matches_df[(match_dates >= start_dt) & (match_dates <= end_dt)]
        
        # Ranglijst tonen
        show_elo_rankings(players_df, matches_df, elo_df, huidig_seizoen)
        
        # Laatste 10 uitslagen
        if not matches_df.empty:
            st.subheader("🕒 Laatste 10 uitslagen")
            
            # Selecteer en formatteer data
            recent_matches = matches_df.head(10).copy()
            
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
                use_container_width=True
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
            
            st.dataframe(seasons_df[cols_to_show])

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
            st.line_chart(history_df, x='Match #', y='rating')
        else:
            st.caption(f"Geen geschiedenis gevonden voor {selected_player}")
