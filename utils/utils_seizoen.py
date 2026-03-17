"""
Seizoen utilities voor de tafelvoetbal app - Prinsjesdag gebaseerd systeem
"""
import pandas as pd
import streamlit as st
from datetime import date, timedelta, datetime


def get_prinsjesdag(year):
    """Bereken Prinsjesdag (derde dinsdag van september) voor een gegeven jaar"""
    # Eerste dag van september
    first_september = date(year, 9, 1)
    # Vind de eerste dinsdag (weekday 1 = dinsdag)
    days_until_tuesday = (1 - first_september.weekday()) % 7
    first_tuesday = first_september + timedelta(days=days_until_tuesday)
    # Derde dinsdag is twee weken later
    prinsjesdag = first_tuesday + timedelta(days=14)
    # Altijd als pd.Timestamp retourneren
    return pd.Timestamp(prinsjesdag)


def get_march15(year):
    """Start van 15 maart"""
    return pd.Timestamp(datetime(year, 3, 15, 0, 0, 0))


def generate_prinsjesdag_seasons(matches_df):
    """Genereer automatische seizoenen op basis van Prinsjesdag + 15 maart split"""
    prinsjesdag_seasons = []

    try:
        current_year = date.today().year

        # Bepaal jaar bereik
        if not matches_df.empty:
            if 'timestamp' in matches_df.columns:
                date_series = pd.to_datetime(matches_df['timestamp'], errors='coerce')
            elif 'datum' in matches_df.columns:
                date_series = pd.to_datetime(matches_df['datum'], errors='coerce')
            else:
                return pd.DataFrame()

            min_year = max(2020, date_series.min().year - 1)
            max_year = current_year + 1
        else:
            min_year = 2020
            max_year = current_year + 1

        for year in range(min_year, max_year + 1):
            p_day = get_prinsjesdag(year)
            next_p_day = get_prinsjesdag(year + 1)
            m15 = get_march15(year + 1)

            # Seizoen 1: Prinsjesdag tot 15 maart (exclusief 15 maart 00:00)
            # Dus t/m 14 maart 23:59:59
            prinsjesdag_seasons.append({
                'seizoen_naam': f"Seizoen {year}/{year + 1} (P→15 mrt)",
                'start_datum': p_day,
                'eind_datum': m15 - timedelta(seconds=1),
                'prinsjesdag': p_day,
                'seizoen_jaar': year + 1
            })

            # Seizoen 2: 15 maart tot volgende Prinsjesdag
            prinsjesdag_seasons.append({
                'seizoen_naam': f"Seizoen {year}/{year + 1} (15 mrt→P)",
                'start_datum': m15,
                'eind_datum': next_p_day - timedelta(seconds=1),
                'prinsjesdag': p_day,
                'seizoen_jaar': year + 1
            })

        seasons_df = pd.DataFrame(prinsjesdag_seasons)

        if not seasons_df.empty and not matches_df.empty:
            seasons_with_stats = []

            for _, season in seasons_df.iterrows():
                try:
                    if 'datum' in matches_df.columns:
                        match_dates_tz_naive = pd.to_datetime(matches_df['datum'], errors='coerce')
                    elif 'timestamp' in matches_df.columns:
                        match_dates_tz_naive = pd.to_datetime(matches_df['timestamp'], errors='coerce')
                    else:
                        match_dates_tz_naive = pd.Series([], dtype='datetime64[ns]')

                    try:
                        if hasattr(match_dates_tz_naive.dt, 'tz') and match_dates_tz_naive.dt.tz is not None:
                            match_dates_tz_naive = match_dates_tz_naive.dt.tz_convert('UTC').dt.tz_localize(None)
                        else:
                            match_dates_tz_naive = match_dates_tz_naive.dt.tz_localize(None)
                    except Exception:
                        pass

                    season_start_tz_naive = pd.to_datetime(season.get('start_datum') or season.get('start_datum'), errors='coerce')
                    season_end_tz_naive = pd.to_datetime(season.get('eind_datum') or season.get('eind_datum'), errors='coerce')
                    season_matches = matches_df[
                        (match_dates_tz_naive >= season_start_tz_naive) &
                        (match_dates_tz_naive <= season_end_tz_naive)
                    ]

                    if len(season_matches) == 0:
                        continue

                    if season_start_tz_naive.date() > date.today():
                        continue

                    if 'thuis_score' in season_matches.columns and 'uit_score' in season_matches.columns:
                        total_goals = season_matches['thuis_score'].sum() + season_matches['uit_score'].sum()
                    else:
                        total_goals = 0
                    avg_goals = total_goals / len(season_matches) if len(season_matches) > 0 else 0

                    unique_players = set()
                    for _, match in season_matches.iterrows():
                        for p in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
                            if p in match and pd.notna(match[p]):
                                unique_players.add(match[p])

                    if 'seizoen_naam' in season:
                        season_name = season['seizoen_naam']
                    elif 'seizoen' in season:
                        season_name = season['seizoen']
                    else:
                        season_name = f"Seizoen {season.get('seizoen_jaar', '?')}"
                    seasons_with_stats.append({
                        'seizoen_naam': season_name,
                        'start_datum': season['start_datum'],
                        'eind_datum': season['eind_datum'],
                        'prinsjesdag': season['prinsjesdag'],
                        'seizoen_jaar': season['seizoen_jaar'],
                        'aantal_wedstrijden': len(season_matches),
                        'total_goals': total_goals,
                        'gemiddelde_goals': round(avg_goals, 1),
                        'unieke_spelers': len(unique_players)
                    })
                    
                except Exception as stats_error:
                    # Skip dit seizoen bij stats problemen
                    continue
            
            return pd.DataFrame(seasons_with_stats)
        
        return seasons_df
        
    except Exception as e:
        st.error(f"Probleem bij het genereren van Prinsjesdag seizoenen: {e}")
        return pd.DataFrame()


def get_season_matches(matches_df, season_info):
    """Filter wedstrijden voor een specifiek seizoen"""
    try:
        # Converteer alle datums naar timezone-naive voor vergelijking
        if 'datum' in matches_df.columns:
            match_dates = pd.to_datetime(matches_df['datum'], errors='coerce')
        elif 'timestamp' in matches_df.columns:
            match_dates = pd.to_datetime(matches_df['timestamp'], errors='coerce')
        else:
            match_dates = pd.Series([], dtype='datetime64[ns]')

        try:
            if hasattr(match_dates.dt, 'tz') and match_dates.dt.tz is not None:
                match_dates = match_dates.dt.tz_convert('UTC').dt.tz_localize(None)
            else:
                match_dates = match_dates.dt.tz_localize(None)
        except Exception:
            pass

        season_start = pd.to_datetime(season_info.get('start_datum') or season_info.get('startdatum'), errors='coerce')
        season_end = pd.to_datetime(season_info.get('eind_datum') or season_info.get('einddatum'), errors='coerce')
        try:
            if hasattr(season_start.dt, 'tz') and season_start.dt.tz is not None:
                season_start = season_start.dt.tz_convert('UTC').dt.tz_localize(None)
        except Exception:
            pass
        try:
            if hasattr(season_end.dt, 'tz') and season_end.dt.tz is not None:
                season_end = season_end.dt.tz_convert('UTC').dt.tz_localize(None)
        except Exception:
            pass
        
        # Filter wedstrijden binnen seizoen periode
        season_mask = (match_dates >= season_start) & (match_dates <= season_end)
        season_matches = matches_df[season_mask].copy()
        
        return season_matches
        
    except Exception as e:
        st.error(f"Fout bij filteren seizoen wedstrijden: {e}")
        return pd.DataFrame()


def calculate_season_stats(season_matches):
    """Bereken uitgebreide statistieken voor een seizoen"""
    if season_matches.empty:
        return {}
    
    stats = {}
    
    try:
        # Basis statistieken
        stats['total_matches'] = len(season_matches)
        stats['total_goals'] = season_matches['thuis_score'].sum() + season_matches['uit_score'].sum()
        stats['avg_goals_per_match'] = stats['total_goals'] / stats['total_matches'] if stats['total_matches'] > 0 else 0
        
        # Speler statistieken
        all_players = set()
        player_matches = {}
        player_goals = {}
        player_wins = {}
        
        # Detect home/away columns
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
        for _, match in season_matches.iterrows():
            home_players = [match.get(home_cols[0], None), match.get(home_cols[1], None)]
            away_players = [match.get(away_cols[0], None), match.get(away_cols[1], None)]
            # Track alle spelers
            all_players.update([p for p in home_players + away_players if p is not None])
            # Track matches per speler
            for player in home_players + away_players:
                if player is not None:
                    player_matches[player] = player_matches.get(player, 0) + 1
                    player_goals[player] = player_goals.get(player, 0)
            # Track goals per speler
            for player in home_players:
                if player is not None:
                    player_goals[player] += match['thuis_score']
                    player_wins[player] = player_wins.get(player, 0)
                    if match['thuis_score'] > match['uit_score']:
                        player_wins[player] += 1
            for player in away_players:
                if player is not None:
                    player_goals[player] += match['uit_score']
                    player_wins[player] = player_wins.get(player, 0)
                    if match['uit_score'] > match['thuis_score']:
                        player_wins[player] += 1
        
        stats['unique_players'] = len(all_players)
        stats['most_active_player'] = max(player_matches.items(), key=lambda x: x[1]) if player_matches else ("N/A", 0)
        stats['top_scorer'] = max(player_goals.items(), key=lambda x: x[1]) if player_goals else ("N/A", 0)
        stats['most_wins'] = max(player_wins.items(), key=lambda x: x[1]) if player_wins else ("N/A", 0)
        
        # Datum statistieken
        stats['first_match'] = season_matches['datum'].min()
        stats['last_match'] = season_matches['datum'].max()
        
        # Hoogste uitslag
        max_total_goals_idx = (season_matches['thuis_score'] + season_matches['uit_score']).idxmax()
        highest_scoring_match = season_matches.loc[max_total_goals_idx]
        stats['highest_scoring_match'] = {
            'thuis_score': highest_scoring_match['thuis_score'],
            'uit_score': highest_scoring_match['uit_score'],
            'total': highest_scoring_match['thuis_score'] + highest_scoring_match['uit_score']
        }
        
    except Exception as e:
        st.error(f"Fout bij berekenen seizoen statistieken: {e}")
        
    return stats


def format_season_period(season_info):
    """Formatteer seizoen periode voor weergave"""
    try:
        # Ondersteun zowel 'startdatum'/'einddatum' als 'start_datum'/'eind_datum'
        if 'startdatum' in season_info and 'einddatum' in season_info:
            start_date = pd.to_datetime(season_info['startdatum']).strftime('%d-%m-%Y')
            end_date = pd.to_datetime(season_info['einddatum']).strftime('%d-%m-%Y')
        else:
            start_date = pd.to_datetime(season_info['start_datum']).strftime('%d-%m-%Y')
            end_date = pd.to_datetime(season_info['eind_datum']).strftime('%d-%m-%Y')
        return f"{start_date} tot {end_date}"
    except Exception:
        return "Onbekende periode"


def is_season_current(season_info):
    """Check of een seizoen het huidige seizoen is"""
    try:
        today = date.today()
        season_start = pd.to_datetime(season_info['start_datum']).date()
        season_end = pd.to_datetime(season_info['eind_datum']).date()
        
        return season_start <= today <= season_end
    except:
        return False


def get_current_season(seasons_df):
    """Vind het huidige actieve seizoen"""
    if seasons_df.empty:
        return None
        
    for _, season in seasons_df.iterrows():
        if is_season_current(season):
            return season
            
    return None


def create_season_options(seasons_df, matches_df):
    """Maak seizoen opties voor selectbox met match counts"""
    season_options = []
    current_date = date.today()
    current_season_id = None
    
    for idx, season in seasons_df.iterrows():
        try:
            start_date = pd.to_datetime(season['start_datum']).date()
            end_date = pd.to_datetime(season['eind_datum']).date()
            
            # Check of er wedstrijden zijn in dit seizoen
            season_matches = get_season_matches(matches_df, season)
            
            # Alleen toevoegen als er wedstrijden zijn
            if len(season_matches) > 0:
                season_name = season.get('seizoen_naam', f"{start_date.strftime('%Y-%m-%d')} tot {end_date.strftime('%Y-%m-%d')}")
                match_count = len(season_matches)
                season_options.append((f"{season_name} ({match_count} wedstrijden)", idx))
                
                # Check of dit het huidige seizoen is
                if start_date <= current_date <= end_date:
                    current_season_id = len(season_options) - 1
                    
        except Exception:
            continue  # Skip seizoenen met problemen
    
    # Voeg "Alle seizoenen" optie toe
    if season_options:
        season_options.insert(0, ("📊 Alle Seizoenen", "all"))
        if current_season_id is not None:
            season_options.insert(1, ("⭐ Huidig Seizoen", current_season_id))
    
    return season_options, current_season_id


def process_all_seasons_metrics(seasons_df, matches_df):
    """Verwerk metrics voor alle seizoenen"""
    season_metrics = []
    
    for idx, season in seasons_df.iterrows():
        try:
            season_matches = get_season_matches(matches_df, season)
            
            if len(season_matches) == 0:
                continue  # Skip seizoenen zonder wedstrijden
                
            # Bereken metrics
            total_goals = season_matches['thuis_score'].sum() + season_matches['uit_score'].sum()
            avg_goals = total_goals / len(season_matches) if len(season_matches) > 0 else 0
            
            # Unieke spelers
            unique_players = set()
            for _, match in season_matches.iterrows():
                unique_players.update([
                    match['thuis_1'], match['thuis_2'],
                    match['uit_1'], match['uit_2']
                ])
            
            season_metrics.append({
                'Seizoen': season.get('seizoen_naam', f"Seizoen {idx+1}"),
                'Aantal Wedstrijden': len(season_matches),
                'Aantal Spelers': len(unique_players),
                'Totaal Goals': total_goals,
                'Gem. Goals per Wedstrijd': round(avg_goals, 1)
            })
            
        except Exception:
            continue  # Skip seizoenen met problemen
    
    return pd.DataFrame(season_metrics)