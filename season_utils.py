"""
Seizoen utilities voor de tafelvoetbal app - Prinsjesdag gebaseerd systeem
"""
import pandas as pd
import streamlit as st
from datetime import date, timedelta


def get_prinsjesdag(year):
    """Bereken Prinsjesdag (derde dinsdag van september) voor een gegeven jaar"""
    # Eerste dag van september
    first_september = date(year, 9, 1)
    
    # Vind de eerste dinsdag (weekday 1 = dinsdag)
    days_until_tuesday = (1 - first_september.weekday()) % 7
    first_tuesday = first_september + timedelta(days=days_until_tuesday)
    
    # Derde dinsdag is twee weken later
    prinsjesdag = first_tuesday + timedelta(days=14)
    
    return prinsjesdag


def generate_prinsjesdag_seasons(matches_df):
    """Genereer automatische seizoenen op basis van Prinsjesdag"""
    prinsjesdag_seasons = []
    
    try:
        current_year = date.today().year
        
        # Bepaal jaar bereik - alleen seizoenen tot huidig jaar
        if not matches_df.empty:
            try:
                # Converteer datum kolom naar datetime en haal timezone info weg
                match_dates = pd.to_datetime(matches_df['datum']).dt.tz_localize(None)
                min_year = max(2020, match_dates.min().year - 1)  # Vanaf 2020 of eerste match jaar
                max_year = min(current_year + 1, match_dates.max().year + 1)  # Tot huidig jaar
            except Exception as date_error:
                # Alleen waarschuwen bij daadwerkelijke data problemen
                if not matches_df.empty:
                    st.warning(f"Probleem met datum conversie: {date_error}")
                # Fallback naar huidige datum bereik
                min_year = 2020
                max_year = current_year + 1
        else:
            # Geen wedstrijden - geen seizoenen tonen
            return pd.DataFrame()
        
        for year in range(min_year, max_year + 1):
            try:
                # Skip jaar 1900 of andere ongeldige jaren, en toekomstige jaren
                if year < 1900 or year > current_year + 1:
                    continue
                    
                prinsjesdag = get_prinsjesdag(year)
                prev_prinsjesdag = get_prinsjesdag(year - 1)
                
                # Seizoen loopt van vorige Prinsjesdag tot huidige Prinsjesdag 24:00
                season_start = prev_prinsjesdag
                season_end = prinsjesdag
                
                prinsjesdag_seasons.append({
                    'seizoen_naam': f"Seizoen {year - 1}/{year}",
                    'start_datum': season_start,
                    'eind_datum': season_end,
                    'prinsjesdag': prinsjesdag,
                    'seizoen_jaar': year
                })
            except Exception as season_error:
                # Skip dit seizoen bij problemen
                continue
        
        seasons_df = pd.DataFrame(prinsjesdag_seasons)
        
        if not seasons_df.empty and not matches_df.empty:
            # Voeg statistieken toe per seizoen
            seasons_with_stats = []
            
            for _, season in seasons_df.iterrows():
                try:
                    # Filter wedstrijden voor dit seizoen
                    match_dates_tz_naive = pd.to_datetime(matches_df['datum']).dt.tz_localize(None)
                    season_start_tz_naive = pd.to_datetime(season['start_datum']).tz_localize(None) if pd.api.types.is_datetime64_any_dtype(pd.to_datetime(season['start_datum'])) else pd.to_datetime(season['start_datum'])
                    season_end_tz_naive = pd.to_datetime(season['eind_datum']).tz_localize(None) if pd.api.types.is_datetime64_any_dtype(pd.to_datetime(season['eind_datum'])) else pd.to_datetime(season['eind_datum'])
                    
                    season_matches = matches_df[
                        (match_dates_tz_naive >= season_start_tz_naive) & 
                        (match_dates_tz_naive <= season_end_tz_naive)
                    ]
                    
                    # Skip seizoenen zonder wedstrijden of in de toekomst
                    if len(season_matches) == 0:
                        continue
                    
                    # Skip seizoenen die volledig in de toekomst liggen
                    if season_start_tz_naive.date() > date.today():
                        continue
                    
                    # Bereken statistieken
                    total_goals = season_matches['thuis_score'].sum() + season_matches['uit_score'].sum()
                    avg_goals = total_goals / len(season_matches) if len(season_matches) > 0 else 0
                    
                    # Unieke spelers
                    unique_players = set()
                    for _, match in season_matches.iterrows():
                        unique_players.update([
                            match['thuis_speler_1'], match['thuis_speler_2'],
                            match['uit_speler_1'], match['uit_speler_2']
                        ])
                    
                    seasons_with_stats.append({
                        'seizoen_naam': season['seizoen_naam'],
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
        match_dates = pd.to_datetime(matches_df['datum']).dt.tz_localize(None)
        season_start = pd.to_datetime(season_info['start_datum']).tz_localize(None) if pd.api.types.is_datetime64_any_dtype(pd.to_datetime(season_info['start_datum'])) else pd.to_datetime(season_info['start_datum'])
        season_end = pd.to_datetime(season_info['eind_datum']).tz_localize(None) if pd.api.types.is_datetime64_any_dtype(pd.to_datetime(season_info['eind_datum'])) else pd.to_datetime(season_info['eind_datum'])
        
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
        
        for _, match in season_matches.iterrows():
            home_players = [match['thuis_speler_1'], match['thuis_speler_2']]
            away_players = [match['uit_speler_1'], match['uit_speler_2']]
            
            # Track alle spelers
            all_players.update(home_players + away_players)
            
            # Track matches per speler
            for player in home_players + away_players:
                player_matches[player] = player_matches.get(player, 0) + 1
                player_goals[player] = player_goals.get(player, 0)
            
            # Track goals per speler
            for player in home_players:
                player_goals[player] += match['thuis_score']
                player_wins[player] = player_wins.get(player, 0)
                if match['thuis_score'] > match['uit_score']:
                    player_wins[player] += 1
            
            for player in away_players:
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
        start_date = pd.to_datetime(season_info['start_datum']).strftime('%d-%m-%Y')
        end_date = pd.to_datetime(season_info['eind_datum']).strftime('%d-%m-%Y')
        return f"{start_date} tot {end_date}"
    except:
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
                    match['thuis_speler_1'], match['thuis_speler_2'],
                    match['uit_speler_1'], match['uit_speler_2']
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