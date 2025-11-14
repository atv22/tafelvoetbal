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

    if not players_df.empty:
        # We only need the names for this table
        df_namen = players_df[['speler_naam']].rename(columns={'speler_naam': 'Huidige namen'}).sort_values(by='Huidige namen')
        st.table(df_namen)
    else:
        st.info("Geen spelers gevonden.")


def render_players_tab(players_df):
    """Render de complete Players tab"""
    render_add_player_form()
    
    st.markdown("<hr />", unsafe_allow_html=True)
    
    show_current_players(players_df)