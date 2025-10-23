import time
import datetime as dt
import streamlit as st
from config import get_client, get_players_list, SHEET_NAME
from utils import get_download_filename
st.title("Tafelvoetbal Competitie ⚽ — Invullen")
klink = st.radio("Zijn er klinkers gescoord? (Als ja, draai dan je scherm op 📱)", ("Nee", "Ja"))
players = sorted(get_players_list())
selected_names = {
    'Thuis speler 1': {'name': None, 'klinkers': 0},
    'Thuis speler 2': {'name': None, 'klinkers': 0},
    'Uit speler 1':   {'name': None, 'klinkers': 0},
    'Uit speler 2':   {'name': None, 'klinkers': 0},
}
with st.form("formulier"):
    if klink == "Ja":
        c1, c2 = st.columns([2, 1])
        for title in selected_names:
            with c1:
                selected_name = st.selectbox(title, players, key=f"sel_{title}")
            with c2:
                selected_klinkers = st.number_input(f"Aantal klinkers {title}:", min_value=0, max_value=10, step=1, key=f"kl_{title}")
            selected_names[title] = {'name': selected_name, 'klinkers': selected_klinkers}
    else:
        for title in selected_names:
            selected_name = st.selectbox(title, players, key=f"sel_{title}")
            selected_names[title] = {'name': selected_name, 'klinkers': 0}
    home_score = st.number_input("Score Thuis team:", min_value=0, max_value=10, step=1)
    away_score = st.number_input("Score Uit team:",   min_value=0, max_value=10, step=1)
    if st.form_submit_button("Verstuur"):
        # validaties
        if home_score == 10 and away_score == 10:
            st.error('Wijzig de einduitslag. Beide scores kunnen niet 10 zijn.')
            st.stop()
        if home_score != 10 and away_score != 10:
            st.error('Wijzig de einduitslag. Eén van de scores moet 10 zijn.')
            st.stop()
        if len({v['name'] for v in selected_names.values()}) < len(selected_names):
            st.error("Selecteer elke speler slechts één keer.")
            st.stop()
        client = get_client()
        ws = client.open(SHEET_NAME).worksheet('Uitslag')
        timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        values = [
            selected_names['Thuis speler 1']['name'],
            selected_names['Thuis speler 2']['name'],
            selected_names['Uit speler 1']['name'],
            selected_names['Uit speler 2']['name'],
            home_score,
            away_score,
            timestamp,
            selected_names['Thuis speler 1']['klinkers'],
            selected_names['Thuis speler 2']['klinkers'],
            selected_names['Uit speler 1']['klinkers'],
            selected_names['Uit speler 2']['klinkers'],
        ]
        ws.append_row(values)
        for team, player in selected_names.items():
            if player['name'] == 'Kwint':
                if ('Thuis' in team and away_score > home_score) or ('Uit' in team and home_score > away_score):
                    st.balloons()
        st.success("Uitslag toegevoegd!")
        time.sleep(1)
        st.experimental_rerun()
 