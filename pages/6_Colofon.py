import streamlit as st
from styles import VERSIE
from styles import setup_page

setup_page()

st.title("Colofon")
st.write(Versie := VERSIE)
st.write("Deze webapp is gemaakt met behulp van ChatGPT door Rick en Arthur")
 