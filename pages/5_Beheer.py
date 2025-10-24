import streamlit as st
import pandas as pd
from datetime import date
import firestore_service as db # Use Firestore
from styles import setup_page

setup_page()

# --- Authenticatie ---
goede_wachtwoord = "Klinker" # Consider moving this to a more secure location
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("Login vereist")
    password = st.text_input("Voer wachtwoord in", type="password")
    if password == goede_wachtwoord:
        st.session_state.authenticated = True
        st.rerun()
    elif password:
        st.error("Ongeldig wachtwoord.")
    st.stop()

st.title("Beheer")

# --- Speler Verwijderen ---
st.subheader("Speler Verwijderen")

players_df = db.get_players()
if not players_df.empty:
    player_names = players_df['speler_naam'].tolist()
    player_ids = players_df['speler_id'].tolist()
    player_map = {name: id for name, id in zip(player_names, player_ids)}

    player_to_delete = st.selectbox("Selecteer een speler om te verwijderen", options=sorted(player_names))
    
    if st.button(f"Verwijder {player_to_delete} Permanent"):
        player_id_to_delete = player_map.get(player_to_delete)
        if player_id_to_delete:
            with st.spinner(f"Bezig met verwijderen van {player_to_delete}..."):
                if db.delete_player_by_id(player_id_to_delete):
                    st.success(f"{player_to_delete} en alle bijbehorende data is verwijderd.")
                    st.rerun()
                else:
                    st.error(f"Kon {player_to_delete} niet verwijderen.")
        else:
            st.error("Kon de speler ID niet vinden.")
else:
    st.info("Geen spelers om te beheren.")

st.markdown("""<hr>""", unsafe_allow_html=True)

# --- Seizoenen Beheer ---
st.subheader("Seizoenen")

# Haal seizoenen op uit Firestore
df_seizoenen = db.get_seasons()

def start_nieuw_seizoen(einddatum):
    startdatum = pd.to_datetime(date.today())
    result = db.add_season(startdatum, einddatum)
    if result == "Success":
        st.success("Nieuw seizoen succesvol gestart!")
        st.rerun()
    else:
        st.error(f"Kon nieuw seizoen niet starten: {result}")

with st.form("nieuw_seizoen_form"):
    st.write("Klik op de knop om een nieuw seizoen te starten.")
    einddatum_input = st.date_input("Einddatum seizoen")
    submit = st.form_submit_button("Start nieuw seizoen")

if submit:
    einddatum = pd.to_datetime(einddatum_input) + pd.Timedelta(hours=23, minutes=59, seconds=59)
    if einddatum <= pd.Timestamp(date.today()):
        st.error("Einddatum moet na vandaag liggen.")
    else:
        start_nieuw_seizoen(einddatum)

st.subheader("Alle seizoenen")
if not df_seizoenen.empty:
    st.dataframe(df_seizoenen, width='stretch')
else:
    st.info("Nog geen seizoenen aangemaakt.")
