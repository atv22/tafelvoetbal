import streamlit as st
from styles import setup_page, VERSIE
setup_page()
st.title("Tafelvoetbal Competitie ⚽")
st.caption(VERSIE)
st.write(
    "Gebruik de navigatie links om naar **Invullen**, **Ranglijst**, **Spelers**, **ELO**, **Ruwe data**, **Verzoeken** of **Colofon** te gaan."
)