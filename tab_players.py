"""
TAB 3: Players module voor tafelvoetbal app
Bevat speler toevoegen functionaliteit en speler lijst
"""
import streamlit as st
from utils import add_name


def render_add_player_form():
    """Render het speler toevoegen formulier"""
    st.header("Voeg een speler toe")
    name = st.text_input("Vul een naam in:")
    if st.button("Voeg naam toe"):
        add_name(name)


def show_current_players(players_df):
    """Toon de huidige spelers lijst"""
    st.header("Huidige spelerslijst")

    import pandas as pd
    import firestore_service as db

    matches_df = db.get_matches()

    if not players_df.empty:
        # Prepare stats: id, name, matches played, active since
        stats = []
        for _, row in players_df.iterrows():
            name = row['speler_naam']
            player_id = row.get('speler_id', '')
            # Count matches played
            matches_played = 0
            first_match = None
            if not matches_df.empty:
                player_matches = pd.DataFrame()
                conditions = []
                for col in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
                    if col in matches_df.columns:
                        conditions.append(matches_df[col] == name)
                if conditions:
                    player_matches = matches_df[pd.concat(conditions, axis=1).any(axis=1)]
                matches_played = len(player_matches)
                if not player_matches.empty and 'datum' in player_matches.columns:
                    first_match = pd.to_datetime(player_matches['datum']).min().date()
            stats.append({
                'ID': player_id,
                'Naam': name,
                'Gespeeld': matches_played,
                'Actief sinds': first_match.strftime('%d-%m-%Y') if first_match else '-'
            })
        df_stats = pd.DataFrame(stats).sort_values(by='Naam')
        st.dataframe(df_stats, width='stretch')
    else:
        st.info("Geen spelers gevonden.")


def render_players_tab(players_df):
    """Render de complete Players tab"""
    render_add_player_form()
    
    st.markdown("<hr />", unsafe_allow_html=True)
    
    show_current_players(players_df)