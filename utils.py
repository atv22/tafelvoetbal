import time
import math
import datetime as dt
import streamlit as st
import pandas as pd
from typing import Dict
from config import get_client, SHEET_NAME
K_FACTOR = 32
# ---------- Helpers voor namen & verzoeken ----------
def add_name(name: str):
    """Valideer en voeg nieuwe speler toe aan sheet 'Namen'."""
    if not name or not name.isalpha():
        st.error("De naam mag alleen letters bevatten. Verander de naam naar alleen letters.")
        return
    if len(name) < 2 or len(name) > 50:
        st.error("De lengte van de naam moet tussen de 2 en de 50 tekens zijn. Pas de lengte van de naam aan.")
        return
    if not name[0].isupper():
        st.error("De eerste letter van de naam moet een hoofdletter zijn.")
        return
    client = get_client()
    ws = client.open(SHEET_NAME).worksheet("Namen")
    existing = ws.col_values(1)[1:]
    if name in existing:
        st.error("Naam bestaat al! Vul een andere naam in.")
        return
    ws.append_row([name])
    st.success(f"Naam '{name}' toegevoegd.")
    time.sleep(1)
    st.experimental_rerun()
def add_request(request: str):
    """Valideer en voeg verzoek toe aan sheet 'Verzoeken'."""
    if len(request) < 2 or len(request) > 250:
        st.error("De lengte van het verzoek moet tussen de 2 en de 250 tekens zijn. Pas de lengte van het verzoek aan.")
        return
    client = get_client()
    ws = client.open(SHEET_NAME).worksheet("Verzoeken")
    existing = ws.col_values(1)[1:]
    if request in existing:
        st.error("Verzoek bestaat al! Vul een andere verzoek in.")
        return
    timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row([request, timestamp])
    st.success("Verzoek is toegevoegd.")
    time.sleep(1)
    st.experimental_rerun()
def get_download_filename(filename: str, extension: str) -> str:
    return f"{filename}_{dt.datetime.now().strftime('%d-%m-%Y_%H%M%S')}.{extension}"
# ---------- ELO helpers ----------
def calculate_expected_result(ta: float, tb: float) -> float:
    return 1 / (1 + 10 ** ((tb - ta) / 400))
def calculate_new_rating(rating: float, s: float, expected: float, score_factor: float) -> float:
    return rating + K_FACTOR * (s - expected) * score_factor
def calculate_score_factor(score_a: int, score_b: int) -> float:
    return (score_a - score_b) / abs(score_a - score_b) if score_a != score_b else 0
def get_klinkers_for_player(player: str, row: pd.Series) -> int:
    if player == row.get('Thuis_1'):
        return int(row.get('Klinkers_thuis_1', 0))
    if player == row.get('Thuis_2'):
        return int(row.get('Klinkers_thuis_2', 0))
    if player == row.get('Uit_1'):
        return int(row.get('Klinkers_uit_1', 0))
    if player == row.get('Uit_2'):
        return int(row.get('Klinkers_uit_2', 0))
    return 0
def elo_calculation(player_elo: float, opponent_elo: float, score: int, score_opp: int) -> float:
    expected_outcome = 1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))
    score_difference = score - score_opp
    actual_outcome = 1 / (1 + 10 ** (-score_difference / 10))
    elo_change = K_FACTOR * (actual_outcome - expected_outcome)
    return round(player_elo + elo_change, 0)
 