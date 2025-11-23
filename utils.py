from datetime import datetime
import zoneinfo

def get_nl_now():
    """Geeft de huidige datum en tijd in de Europe/Amsterdam tijdzone."""
    return datetime.now(zoneinfo.ZoneInfo("Europe/Amsterdam"))
import time
import math
import datetime as dt
import streamlit as st
import pandas as pd
from typing import Dict
import firestore_service as db # Use Firestore service

K_FACTOR = 32

# ---------- Helpers voor namen & verzoeken ----------
def add_name(name: str):
    """Valideer en voeg nieuwe speler toe aan Firestore."""
    # Strip whitespace and check for duplicate (case-insensitive, ignore spaces)
    clean_name = name.strip()
    if not clean_name or not clean_name.isalpha():
        st.error("De naam mag alleen letters bevatten. Verander de naam naar alleen letters.")
        return
    if len(clean_name) < 2 or len(clean_name) > 50:
        st.error("De lengte van de naam moet tussen de 2 en de 50 tekens zijn. Pas de lengte van de naam aan.")
        return
    if not clean_name[0].isupper():
        st.error("De eerste letter van de naam moet een hoofdletter zijn.")
        return

    # Check for duplicate (case-insensitive, ignore spaces)
    existing_players = db.get_players()
    norm = lambda s: s.replace(" ", "").lower()
    if not existing_players.empty:
        if norm(clean_name) in [norm(n) for n in existing_players['speler_naam'].astype(str).tolist()]:
            st.error(f"De naam '{clean_name}' bestaat al (mogelijk met andere hoofdletters/spaties). Kies een unieke naam.")
            return

    # Use firestore service to add player
    result = db.add_player(clean_name, start_elo=1000)

    if result == "Success":
        st.success(f"Naam '{clean_name}' toegevoegd.")
        time.sleep(1)
        st.rerun()
    else:
        st.error(result) # Display error from firestore_service

def add_request(request: str):
    """Valideer en voeg verzoek toe aan Firestore."""
    if len(request) < 2 or len(request) > 250:
        st.error("De lengte van het verzoek moet tussen de 2 en de 250 tekens zijn. Pas de lengte van het verzoek aan.")
        return

    result = db.add_request(request)
    if result == "Success":
        st.success("Verzoek is toegevoegd.")
        time.sleep(1)
        st.rerun()
    else:
        st.error(result)

def get_download_filename(filename: str, extension: str) -> str:
    return f"{filename}_{dt.datetime.now().strftime('%d-%m-%Y_%H%M%S')}.{extension}"


"""
Algemene utility-functies voor de tafelvoetbal-app.
Bevat validatie, tijdzone, naam/request helpers, bestandsnaam, enz.
"""