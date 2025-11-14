"""
TAB 1: Home module voor tafelvoetbal app
Bevat ELO ranking tabel en speler geschiedenis functies
"""
import streamlit as st
import pandas as pd
import firestore_service as db


def calculate_stats(players, matches):
    """Bereken statistieken voor alle spelers"""
    stats_list = []
    for index, player in players.iterrows():
        player_name = str(player['speler_naam']) if player['speler_naam'] is not None else ""
        
        # Veilige filtering om KeyError te voorkomen
        conditions = []
        for col in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
            if col in matches.columns:
                conditions.append(matches[col] == player_name)
        
        if not conditions:
            player_matches = pd.DataFrame()
        else:
            player_matches = matches[pd.concat(conditions, axis=1).any(axis=1)]

        if player_matches.empty:
            stats = {'Gespeeld': 0, 'Voor': 0, 'Tegen': 0, 'Doelsaldo': 0, 'Klinkers': 0, 'Speler': ""}
        else:
            goals_for = 0
            goals_against = 0
            klinkers = 0
            for _, match in player_matches.iterrows():
                thuis_spelers = [match.get('thuis_1'), match.get('thuis_2')]
                uit_spelers = [match.get('uit_1'), match.get('uit_2')]
                
                if player_name in thuis_spelers:
                    goals_for += int(match.get('thuis_score', 0) or 0)
                    goals_against += int(match.get('uit_score', 0) or 0)
                    if player_name == match.get('thuis_1'):
                        klinkers += int(match.get('klinkers_thuis_1', 0) or 0)
                    else:
                        klinkers += int(match.get('klinkers_thuis_2', 0) or 0)
                elif player_name in uit_spelers:
                    goals_for += int(match.get('uit_score', 0) or 0)
                    goals_against += int(match.get('thuis_score', 0) or 0)
                    if player_name == match.get('uit_1'):
                        klinkers += int(match.get('klinkers_uit_1', 0) or 0)
                    else:
                        klinkers += int(match.get('klinkers_uit_2', 0) or 0)
            
            stats = {
                'Gespeeld': len(player_matches),
                'Voor': int(goals_for),
                'Tegen': int(goals_against),
                'Doelsaldo': int(goals_for - goals_against),
                'Klinkers': int(klinkers),
                'Speler': ""  # Placeholder voor string type
            }
        
        stats['Speler'] = player_name
        # Veilige conversie van rating met fallback naar 1000 als default
        rating_value = player.get('rating', 1000)
        if rating_value is None or pd.isna(rating_value):
            rating_value = 1000
        stats['ELO'] = int(rating_value)
        stats_list.append(stats)
        
    return pd.DataFrame(stats_list)


def show_elo_rankings(players_df, matches_df):
    """Toon de huidige ELO rankings tabel"""
    stats_df = calculate_stats(players_df, matches_df)
    
    # Sorteer en selecteer kolommen voor weergave
    display_df = stats_df.sort_values(by='ELO', ascending=False)
    st.dataframe(display_df[['Speler', 'ELO', 'Gespeeld', 'Voor', 'Tegen', 'Doelsaldo', 'Klinkers']], use_container_width=True)


def show_elo_history_selector(players_df):
    """Toon speler selectie voor ELO geschiedenis"""
    player_names = sorted(players_df['speler_naam'].tolist())
    selected_player = st.selectbox("Selecteer een speler:", player_names)
    
    if selected_player:
        # Haal de ELO geschiedenis op voor de geselecteerde speler
        history_df = db.get_elo_history(_ttl=60, speler_naam=selected_player)
        
        if not history_df.empty:
            history_df['match_num'] = range(1, len(history_df) + 1)
            st.line_chart(history_df, x='match_num', y='rating')
        else:
            st.info(f"Geen ELO geschiedenis gevonden voor {selected_player}.")


def render_home_tab(players_df, matches_df):
    """Render de complete Home tab"""
    st.header(":crown: ELO Rating :crown:")
    
    if players_df.empty:
        st.info("Nog geen spelers geregistreerd. Ga naar 'Spelers' om spelers toe te voegen.")
    else:
        # --- Huidige ELO rating tonen ---
        st.subheader("Huidige ELO rating van alle spelers")
        show_elo_rankings(players_df, matches_df)
        
        # --- ELO ontwikkeling tonen ---
        st.subheader("Ontwikkeling ELO rating per speler")
        show_elo_history_selector(players_df)