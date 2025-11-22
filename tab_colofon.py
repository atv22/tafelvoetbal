import streamlit as st

def render_colofon_tab():
    st.header("Colofon")
    st.markdown("""
    ### 🏆 Tafelvoetbal Competitie App
    
    Deze webapp is ontwikkeld tijdens de **Hackatron van oktober 2025** door:
    
    **Team Leden:**
    - Rick
    - Bernd  
    - Dewi
    - Isis
    - Arthur
    - Johannes
    
    **Technische Details:**
    - 🐍 **Python** met Streamlit framework
    - 🔥 **Firestore** database voor data opslag
    - 🤖 **AI-assistentie** van ChatGPT, Gemini, Copilot en Perplexity voor ontwikkeling
    - 📊 **ELO rating systeem** voor speler rankings
    - 📁 **CSV import/export** functionaliteit
    
    **Features:**
    - Wedstrijd registratie en beheer
    - Automatische ELO score berekening
    - Speler en seizoen beheer
    - Historische data import
    - Real-time statistieken en rankings
    
    ---
    
    ### 📊 ELO Rating Systeem
    
    Het ELO-systeem bepaalt de sterkte van elke speler op basis van hun prestaties in wedstrijden. Elke speler start met **1000 punten**. Na elke wedstrijd wordt de ELO van alle vier de spelers aangepast:
    
    - **Verwachte resultaat:** Het systeem berekent vooraf de kans dat elk team wint, op basis van de huidige ELO van de spelers.
    - **Scoreverschil:** Hoe groter het verschil in doelpunten, hoe groter de ELO-aanpassing.
    - **Aantal gespeelde wedstrijden:** Nieuwe spelers krijgen grotere aanpassingen zodat hun ELO sneller convergeert.
    
    **Formule (vereenvoudigd):**
    
    > Nieuwe ELO = Oude ELO + K × (Resultaat - Verwachting)
    
    Waarbij:
    - **K** = aanpassingsfactor (groter voor nieuwe spelers)
    - **Resultaat** = 1 voor winst, 0 voor verlies, 0.5 voor gelijkspel
    - **Verwachting** = kans op winst volgens ELO
    
    **Voorbeeld:**
    - Team A (ELO 1100 & 1050) wint met 10-7 van Team B (ELO 1000 & 950)
    - Team A krijgt meer ELO erbij, Team B verliest ELO
    - Scoreverschil (3 punten) zorgt voor extra bonus
    
    **Waarom ELO?**
    - Houdt rekening met sterkte van tegenstanders
    - Beloont verrassende overwinningen
    - Voorkomt dat één uitschieter de ranking domineert
    - Maakt rankings eerlijker en dynamischer
    
    **Meer info:** Zie de ruwe data tab voor ELO geschiedenis.
    """)