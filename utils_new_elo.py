"""
ELO-berekeningen en hulpfuncties voor de tafelvoetbal-app.
Bevat zowel de nieuwe als eenvoudige ELO-logica.
"""

import streamlit as st
import pandas as pd


# ELO-hulpfuncties
K_FACTOR = 32

def get_klinkers_for_player(player: str, row: pd.Series) -> int:
    """
    Helper om het aantal klinkers voor een speler uit een wedstrijdregel te halen.
    """
    # Detecteer thuis/uit-kolommen
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

import math
import pandas as pd

def calculate_point_factor(score_difference):
    """
    Bepaalt de impact van het scoreverschil op de ELO-aanpassing.
    Hoe groter het verschil, hoe groter de aanpassing. Gebaseerd op een logaritmische schaal.
    """
    return 2 + (math.log(score_difference + 1) / math.log(10)) ** 3

def expected_score_against_player(player_rating_x, player_rating_y):
    """
    Verwachte score van speler X tegen speler Y op basis van hun ratings.
    """
    return 1 / (1 + 10**((player_rating_y - player_rating_x) / 500))

def expected_score(player_rating_x, player_rating_y, player_rating_z):
    """
    Verwachte score van speler X tegen het gemiddelde van spelers Y en Z (tegenstanders).
    """
    return (expected_score_against_player(player_rating_x, player_rating_y) + expected_score_against_player(player_rating_x, player_rating_z)) / 2


def calculate_new_elo(match, all_ELO_ratings):
    """
    Berekent de nieuwe ELO ratings voor alle spelers in een 2v2-wedstrijd.
    Gebaseerd op een aangepaste ELO-formule voor teamsporten:
    - Verwachte score wordt bepaald t.o.v. beide tegenstanders.
    - Scoreverschil beïnvloedt de aanpassing (groter verschil = grotere aanpassing).
    - K-factor daalt naarmate een speler meer wedstrijden speelt (snellere stabilisatie).

    Parameters:
        match: dict met spelersnamen en scores
        all_ELO_ratings: dict met per speler een lijst van ELO's (laatste = huidig)

    Returns:
        DataFrame met nieuwe ELO per speler
    """
    # Haal de huidige ELO ratings op van alle spelers
    player1_rating = all_ELO_ratings[match["Thuis_1"]][-1]
    player2_rating = all_ELO_ratings[match["Thuis_2"]][-1]
    player3_rating = all_ELO_ratings[match["Uit_1"]][-1]
    player4_rating = all_ELO_ratings[match["Uit_2"]][-1]

    # 1. Verwachte scores per speler (tegen beide tegenstanders)
    player1_expected_score = expected_score(player1_rating, player3_rating, player4_rating)
    player2_expected_score = expected_score(player2_rating, player3_rating, player4_rating)
    player3_expected_score = expected_score(player3_rating, player1_rating, player2_rating)
    player4_expected_score = expected_score(player4_rating, player1_rating, player2_rating)

    # 2. Werkelijk resultaat per team
    # Thuis wint = 1, Uit wint = 0, Gelijk = 0.5
    if match["Thuis_score"] > match["Uit_score"]:
        result_thuis = 1
        result_uit = 0
    elif match["Thuis_score"] < match["Uit_score"]:
        result_thuis = 0
        result_uit = 1
    else:
        result_thuis = 0.5
        result_uit = 0.5

    # 3. Bepaal het scoreverschil en de impactfactor
    score_difference = abs(match["Thuis_score"] - match["Uit_score"])
    point_factor = calculate_point_factor(score_difference)

    # 4. K-factor: bepaalt hoe snel de ELO zich aanpast (meer wedstrijden = lagere K)
    k1 = 50 / (1 + len(all_ELO_ratings[match["Thuis_1"]]) / 300)
    k2 = 50 / (1 + len(all_ELO_ratings[match["Thuis_2"]]) / 300)
    k3 = 50 / (1 + len(all_ELO_ratings[match["Uit_1"]]) / 300)
    k4 = 50 / (1 + len(all_ELO_ratings[match["Uit_2"]]) / 300)

    # 5. Bereken de nieuwe ELO's voor alle spelers
    # Formule: nieuwe ELO = oude ELO + K * impact * (resultaat - verwachting)
    rows = [
        [match["Thuis_1"], player1_rating + k1 * point_factor * (result_thuis - player1_expected_score)],
        [match["Thuis_2"], player2_rating + k2 * point_factor * (result_thuis - player2_expected_score)],
        [match["Uit_1"], player3_rating + k3 * point_factor * (result_uit - player3_expected_score)],
        [match["Uit_2"], player4_rating + k4 * point_factor * (result_uit - player4_expected_score)],
    ]
    totaal_overzicht = pd.DataFrame(rows, columns=["Speler", "ELO"])
    return totaal_overzicht
