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

# ---------- ELO helpers ----------
def get_klinkers_for_player(player: str, row: pd.Series) -> int:
    """Helper to get klinkers for a player from a match row."""
    # Detect home/away columns
    if 'thuis_speler_1' in row:
        home_cols = ['thuis_speler_1', 'thuis_speler_2']
        away_cols = ['uit_speler_1', 'uit_speler_2']
        klinkers_home = ['klinkers_thuis_1', 'klinkers_thuis_2']
        klinkers_away = ['klinkers_uit_1', 'klinkers_uit_2']
    else:
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
        klinkers_home = ['klinkers_thuis_1', 'klinkers_thuis_2']
        klinkers_away = ['klinkers_uit_1', 'klinkers_uit_2']
    for i, col in enumerate(home_cols):
        if player == row.get(col):
            return int(row.get(klinkers_home[i], 0))
    for i, col in enumerate(away_cols):
        if player == row.get(col):
            return int(row.get(klinkers_away[i], 0))
    return 0

def elo_calculation(player_elo: float, opponent_elo: float, score: int, score_opp: int) -> float:
    """Calculates the new ELO rating for a player after a match."""
    # This is a simplified ELO calculation, you might want to adjust it.
    # It considers the score difference.
    expected_outcome = 1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))
    
    # The actual outcome is scaled based on the score difference.
    # A 10-0 win is a stronger win than a 10-9 win.
    if score > score_opp:
        actual_outcome = 0.5 + (score - score_opp) * 0.05 # Win
    elif score < score_opp:
        actual_outcome = 0.5 - (score_opp - score) * 0.05 # Loss
    else:
        actual_outcome = 0.5 # Draw

    # Ensure actual_outcome is within [0, 1]
    actual_outcome = max(0, min(1, actual_outcome))

    elo_change = K_FACTOR * (actual_outcome - expected_outcome)
    return round(player_elo + elo_change, 0)