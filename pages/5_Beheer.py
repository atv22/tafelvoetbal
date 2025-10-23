import streamlit as st
import pandas as pd
from datetime import date

goede_wachtwoord = "Klinker"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("Login vereist")
    password = st.text_input("Voer wachtwoord in", type="password")
    if password == goede_wachtwoord:
        st.session_state.authenticated = True
        st.success("Toegang verleend!")
        st.rerun()
    elif password:
        st.error("Ongeldig wachtwoord.")
    st.stop()

st.title("Beheer")
# --- DataFrame bewaren in session_state
if "seizoenen" not in st.session_state:
    st.session_state.seizoenen = pd.DataFrame([
        {"seizoen_id": 1, "startdatum": pd.to_datetime('2025-03-15 00:00:00.0000000000',

               format='%Y-%m-%d %H:%M:%S.%f'), "einddatum": pd.to_datetime('2025-09-16 23:59:59.0000000000',

               format='%Y-%m-%d %H:%M:%S.%f')}
    ])
    st.session_state.seizoenen["startdatum"] = pd.to_datetime(st.session_state.seizoenen["startdatum"])
    st.session_state.seizoenen["einddatum"] = pd.to_datetime(st.session_state.seizoenen["einddatum"])
df_seizoenen = st.session_state.seizoenen
# --- Functie die een nieuw seizoen toevoegt
def start_nieuw_seizoen(einddatum):
    if not df_seizoenen.empty:
        nieuw_id = df_seizoenen['seizoen_id'].max() + 1
    else:
        nieuw_id = 1
    nieuwe_rij = {
        "seizoen_id": nieuw_id,
        "startdatum": pd.to_datetime(date.today()),
        "einddatum": einddatum
    }
    st.session_state.seizoenen = pd.concat(
        [df_seizoenen, pd.DataFrame([nieuwe_rij])],
        ignore_index=True
    )
    st.success(f"Nieuw seizoen gestart (Seizoen {nieuw_id})")
# --- UI voor nieuw seizoen starten
st.subheader("Nieuw seizoen starten")
with st.form("nieuw_seizoen_form"):
    st.write("Klik op de knop om een nieuw seizoen te starten.")
    einddatum = st.date_input("Einddatum seizoen", format="YYYY-MM-DD")
    einddatum = pd.to_datetime(einddatum) + pd.Timedelta(hours=23, minutes=59, seconds=59)
    submit = st.form_submit_button("Start nieuw seizoen")
if submit:
    if einddatum <= pd.Timestamp(date.today()):
        st.error("Einddatum moet na vandaag liggen.")
    else:
        start_nieuw_seizoen(einddatum)
# --- Toon resultaten
st.subheader("Alle seizoenen")
st.dataframe(st.session_state.seizoenen)