"""
ELO-berekeningen en helpers voor de tafelvoetbal-app.
Bevat zowel nieuwe als eenvoudige ELO-logica.
"""

import streamlit as st
import pandas as pd

# ---------- ELO helpers (verplaatst uit utils.py) ----------
K_FACTOR = 32

def get_klinkers_for_player(player: str, row: pd.Series) -> int:
    """Helper to get klinkers for a player from a match row."""
    # Detect home/away columns (alleen nieuwe structuur)
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
import math
import pandas as pd

def calculate_point_factor(score_difference):
    return 2 + (math.log(score_difference + 1) / math.log(10)) ** 3

def expected_score_against_player(player_rating_x, player_rating_y):
    return 1 / (1 + 10**((player_rating_y - player_rating_x) / 500))

def expected_score(player_rating_x, player_rating_y, player_rating_z):
    return (expected_score_against_player(player_rating_x, player_rating_y) + expected_score_against_player(player_rating_x, player_rating_z)) / 2


def calculate_new_elo(match, all_ELO_ratings):
    player1_rating = all_ELO_ratings[match["Thuis_1"]][-1]
    player2_rating = all_ELO_ratings[match["Thuis_2"]][-1]
    player3_rating = all_ELO_ratings[match["Uit_1"]][-1]
    player4_rating = all_ELO_ratings[match["Uit_2"]][-1]

    # Verwachte scores
    player1_expected_score = expected_score(player1_rating, player3_rating, player4_rating)
    player2_expected_score = expected_score(player2_rating, player3_rating, player4_rating)
    player3_expected_score = expected_score(player3_rating, player1_rating, player2_rating)
    player4_expected_score = expected_score(player4_rating, player1_rating, player2_rating)

    # Werkelijk resultaat per speler
    if match["Thuis_score"] > match["Uit_score"]:
        result_thuis = 1
        result_uit = 0
    elif match["Thuis_score"] < match["Uit_score"]:
        result_thuis = 0
        result_uit = 1
    else:
        result_thuis = 0.5
        result_uit = 0.5

    score_difference = abs(match["Thuis_score"] - match["Uit_score"])
    point_factor = calculate_point_factor(score_difference)

    # K-factor
    k1 = 50 / (1 + len(all_ELO_ratings[match["Thuis_1"]]) / 300)
    k2 = 50 / (1 + len(all_ELO_ratings[match["Thuis_2"]]) / 300)
    k3 = 50 / (1 + len(all_ELO_ratings[match["Uit_1"]]) / 300)
    k4 = 50 / (1 + len(all_ELO_ratings[match["Uit_2"]]) / 300)

    # Nieuwe ELO's
    rows = [
        [match["Thuis_1"], player1_rating + k1 * point_factor * (result_thuis - player1_expected_score)],
        [match["Thuis_2"], player2_rating + k2 * point_factor * (result_thuis - player2_expected_score)],
        [match["Uit_1"], player3_rating + k3 * point_factor * (result_uit - player3_expected_score)],
        [match["Uit_2"], player4_rating + k4 * point_factor * (result_uit - player4_expected_score)],
    ]
    totaal_overzicht = pd.DataFrame(rows, columns=["Speler", "ELO"])
    return totaal_overzicht
