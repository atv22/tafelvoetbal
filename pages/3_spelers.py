import streamlit as st
import pandas as pd
import firestore_service as db # Use Firestore service
from utils import add_name
from styles import setup_page

setup_page()

st.header("Voeg een speler toe")
name = st.text_input("Vul een naam in:")
if st.button("Voeg naam toe"):
    add_name(name)

st.markdown("<hr style=\"height:9px;border:none;color:#f0f2f6;background-color:#122f5b;opacity:0.8;\" />", unsafe_allow_html=True)

st.header("Huidige spelerslijst")

# Get players from Firestore
df_players = db.get_players()

if not df_players.empty:
    # We only need the names for this table
    df_namen = df_players[['speler_naam']].rename(columns={'speler_naam': 'Huidige namen'}).sort_values(by='Huidige namen')
    st.table(df_namen)
else:
    st.info("Geen spelers gevonden.")