"""
Algemene hulpfuncties voor de tafelvoetbal-app.
Bevat validatie, tijdzone, naam/request helpers, bestandsnaam, enz.
"""

from datetime import datetime
import datetime as dt
import time
import zoneinfo
import streamlit as st
import firestore_service as db  # Use Firestore service

K_FACTOR = 32

# Lijst van spelers die we niet willen tonen in statistieken/ranglijsten (system players of test players)
IGNORE_PLAYERS = [
    'niemandin', 'niemanduit', 'niemand', 'none', '', ' ',
    'testthuisa', 'testthuisb', 'testuita', 'testuitb'
]

def get_nl_now():
    """Geeft de huidige datum en tijd in de Europe/Amsterdam tijdzone."""
    return datetime.now(zoneinfo.ZoneInfo("Europe/Amsterdam"))

# ---------- Helpers voor namen & verzoeken ----------
def add_name(name: str, rerun: bool = True):
    """Valideer en voeg nieuwe speler toe aan Firestore."""
    clean_name = name.strip() if name else ""
    if not clean_name or not clean_name.replace(" ", "").isalpha():
        st.error("De naam mag alleen letters bevatten. Verander de naam naar alleen letters.")
        return None
    if len(clean_name) < 2 or len(clean_name) > 50:
        st.error("De lengte van de naam moet tussen de 2 en de 50 tekens zijn. Pas de lengte van de naam aan.")
        return None
    if not clean_name[0].isupper():
        st.error("De eerste letter van de naam moet een hoofdletter zijn.")
        return None

    existing_players = db.get_players()
    norm = lambda s: s.replace(" ", "").lower()
    if existing_players is not None and not existing_players.empty and 'speler_naam' in existing_players.columns:
        if norm(clean_name) in [norm(n) for n in existing_players['speler_naam'].astype(str).tolist()]:
            st.error(f"De naam '{clean_name}' bestaat al (mogelijk met andere hoofdletters/spaties). Kies een unieke naam.")
            return None

    result = db.add_player(clean_name, start_elo=1000)

    if result == "Success":
        st.success(f"Naam '{clean_name}' toegevoegd.")
        if rerun:
            time.sleep(1)
            st.rerun()
        return clean_name
    else:
        st.error(result)
        return None

def add_request(request: str, rerun: bool = True):
    """Valideer en voeg verzoek toe aan Firestore."""
    clean_req = request.strip() if request else ""
    if len(clean_req) < 2 or len(clean_req) > 250:
        st.error("De lengte van het verzoek moet tussen de 2 en de 250 tekens zijn. Pas de lengte van het verzoek aan.")
        return None

    result = db.add_request(clean_req)
    if result == "Success":
        st.success("Verzoek is toegevoegd.")
        if rerun:
            time.sleep(1)
            st.rerun()
        return clean_req
    else:
        st.error(result)
        return None

def get_download_filename(filename: str, extension: str) -> str:
    return f"{filename}_{dt.datetime.now().strftime('%d-%m-%Y_%H%M%S')}.{extension}"

