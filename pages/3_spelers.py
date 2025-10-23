import streamlit as st
import pandas as pd
from config import get_players_list, get_client, SHEET_NAME
from utils import add_name
from styles import setup_page

setup_page()

st.header("Voeg een speler toe")
name = st.text_input("Vul een naam in:")
if st.button("Voeg naam toe"):
    add_name(name)
st.markdown("""<hr style=\"height:9px;border:none;color:#f0f2f6;background-color:#122f5b;opacity:0.8;\" />""", unsafe_allow_html=True)
st.header("Huidige namelijst")
players = sorted(get_players_list())
df_namen = pd.DataFrame(players, columns=['Huidige namen'])
st.table(df_namen)
 