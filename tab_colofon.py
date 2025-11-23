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

    Het ELO-systeem bepaalt de sterkte van elke speler op basis van hun prestaties in wedstrijden. Elke speler start met **1000 punten**. Na elke wedstrijd wordt de ELO van alle vier de spelers aangepast. De ELO-score wordt beïnvloed door:

    - **Verwachte resultaat:** Het systeem berekent vooraf de kans dat elk team wint, op basis van de huidige ELO van de spelers.
    - **Scoreverschil:** Hoe groter het verschil in doelpunten, hoe groter de ELO-aanpassing (bonus/malus).
    - **Aantal gespeelde wedstrijden:** Nieuwe spelers krijgen grotere aanpassingen zodat hun ELO sneller convergeert (hoge K-factor).
    - **Reset:** Bij het begin van een nieuw seizoen worden alle ELO's weer op 1000 gezet. Zo begint iedereen elk seizoen gelijk.
    - **Handmatige correcties:** De beheerder kan ELO's resetten of corrigeren via de beheer-tab.

    **Formule (vereenvoudigd):**

    > Nieuwe ELO = Oude ELO + K × (Resultaat - Verwachting) × (1 + 0.1 × scoreverschil)

    Waarbij:
    - **K** = aanpassingsfactor (groter voor nieuwe spelers, daalt naarmate je meer speelt)
    - **Resultaat** = 1 voor winst, 0 voor verlies, 0.5 voor gelijkspel
    - **Verwachting** = kans op winst volgens ELO
    - **Scoreverschil** = aantal doelpunten verschil (maximale bonus/malus)

    **Praktisch voorbeeld:**
    - Team A (ELO 1100 & 1050) wint met 10-7 van Team B (ELO 1000 & 950)
    - Team A krijgt meer ELO erbij, Team B verliest ELO
    - Scoreverschil (3 punten) zorgt voor extra bonus
    - Nieuwe spelers zien hun ELO sneller stijgen/dalen

    **Wat beïnvloedt je ELO-score?**
    - Winnen van sterkere tegenstanders levert meer op
    - Grote uitslagen geven extra bonus/malus
    - Veel spelen maakt je ELO stabieler (lagere K-factor)
    - Elk seizoen begint iedereen weer op 1000 (reset)

    **Waarom ELO?**
    - Houdt rekening met sterkte van tegenstanders
    - Beloont verrassende overwinningen
    - Voorkomt dat één uitschieter de ranking domineert
    - Maakt rankings eerlijker en dynamischer

    **Meer info:** Zie de ruwe data tab voor ELO geschiedenis en de beheer-tab voor reset/correctie.
    """)