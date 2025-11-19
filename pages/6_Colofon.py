import streamlit as st
from styles import setup_page

setup_page()


st.title("Colofon")
st.write("Deze webapp is gemaakt met behulp van ChatGPT door Rick en Arthur")

st.markdown("""
### ELO Berekening

Het ELO-systeem is speciaal aangepast voor 2v2 tafelvoetbal. Elke speler start met 1000 punten. Na elke wedstrijd wordt de ELO van alle vier de spelers aangepast op basis van:

- Het verwachte resultaat (op basis van de ELO van beide teams)
- Het daadwerkelijke scoreverschil
- Het aantal eerder gespeelde wedstrijden (K-factor daalt bij meer ervaring)

De berekening is geïnspireerd op [dit artikel](https://towardsdatascience.com/developing-an-elo-based-data-driven-ranking-system-for-2v2-multiplayer-games-7689f7d42a53) en houdt rekening met teamdynamiek en scoreverschillen. Zo ontstaat een eerlijke en dynamische ranglijst.
""")
 