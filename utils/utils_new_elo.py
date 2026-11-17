"""
ELO-berekeningen en hulpfuncties voor de tafelvoetbal-app.
"""

import math
import pandas as pd

KLINKER_BONUS = 15


def _safe_float(val, default: float = 0.0) -> float:
    """Converteert veilig een waarde (inclusief kommagetallen, None of NaN) naar float."""
    if val is None:
        return default
    try:
        if pd.isna(val):
            return default
    except (TypeError, ValueError):
        pass
    try:
        if isinstance(val, str):
            val = val.strip().replace(",", ".")
            if not val:
                return default
        result = float(val)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def _safe_int(val, default: int = 0) -> int:
    """Converteert veilig een waarde (inclusief float-strings, None of NaN) naar int."""
    return int(round(_safe_float(val, float(default))))


def get_klinkers_for_player(player: str, row: pd.Series) -> int:
    """
    Helper om het aantal klinkers voor een speler uit een wedstrijdregel te halen.
    """
    home_cols = ['thuis_1', 'thuis_2']
    away_cols = ['uit_1', 'uit_2']
    klinkers_home = ['klinkers_thuis_1', 'klinkers_thuis_2']
    klinkers_away = ['klinkers_uit_1', 'klinkers_uit_2']
    for i, col in enumerate(home_cols):
        if player == row.get(col):
            return max(0, _safe_int(row.get(klinkers_home[i], 0), 0))
    for i, col in enumerate(away_cols):
        if player == row.get(col):
            return max(0, _safe_int(row.get(klinkers_away[i], 0), 0))
    return 0


def calculate_point_factor(score_difference):
    """
    Bepaalt de impact van het scoreverschil op de ELO-aanpassing.
    Hoe groter het verschil, hoe groter de aanpassing. Gebaseerd op een logaritmische schaal.
    """
    diff = abs(_safe_float(score_difference, 0.0))
    return 2 + (math.log10(diff + 1)) ** 3


def expected_score_against_player(player_rating_x, player_rating_y):
    """
    Verwachte score van speler X tegen speler Y op basis van hun ratings.
    """
    rx = _safe_float(player_rating_x, 1000.0)
    ry = _safe_float(player_rating_y, 1000.0)
    return 1 / (1 + 10 ** ((ry - rx) / 500))


def expected_score(player_rating_x, player_rating_y, player_rating_z):
    """
    Verwachte score van speler X tegen het gemiddelde van spelers Y en Z (tegenstanders).
    """
    return (
        expected_score_against_player(player_rating_x, player_rating_y)
        + expected_score_against_player(player_rating_x, player_rating_z)
    ) / 2


def calculate_new_elo(match, all_ELO_ratings):
    """
    Berekent de nieuwe ELO ratings voor alle spelers in een 2v2-wedstrijd.
    Gebaseerd op een aangepaste ELO-formule voor teamsporten:
    - Verwachte score wordt bepaald t.o.v. beide tegenstanders.
    - Scoreverschil beïnvloedt de aanpassing (groter verschil = grotere aanpassing).
    - K-factor daalt naarmate een speler meer wedstrijden speelt (snellere stabilisatie).
      Conventie: ``all_ELO_ratings[speler]`` bevat ``[start_elo] + match_elos``
      (dus lengte ``N + 1`` bij ``N`` eerder gespeelde seizoenswedstrijden).

    Parameters:
        match: dict met spelersnamen en scores
        all_ELO_ratings: dict met per speler een lijst van ELO's (laatste = huidig)

    Returns:
        DataFrame met nieuwe ELO per speler
    """
    def _rating_and_k(player_name):
        history = all_ELO_ratings.get(player_name) if all_ELO_ratings else None
        if not history:
            history = [1000.0]
        rating = _safe_float(history[-1], 1000.0)
        k_val = 50 / (1 + len(history) / 300)
        return rating, k_val

    p1_name = match["Thuis_1"]
    p2_name = match["Thuis_2"]
    p3_name = match["Uit_1"]
    p4_name = match["Uit_2"]

    player1_rating, k1 = _rating_and_k(p1_name)
    player2_rating, k2 = _rating_and_k(p2_name)
    player3_rating, k3 = _rating_and_k(p3_name)
    player4_rating, k4 = _rating_and_k(p4_name)

    # 1. Verwachte scores per speler (tegen beide tegenstanders)
    player1_expected_score = expected_score(player1_rating, player3_rating, player4_rating)
    player2_expected_score = expected_score(player2_rating, player3_rating, player4_rating)
    player3_expected_score = expected_score(player3_rating, player1_rating, player2_rating)
    player4_expected_score = expected_score(player4_rating, player1_rating, player2_rating)

    # 2. Werkelijk resultaat per team
    # Thuis wint = 1, Uit wint = 0, Gelijk = 0.5
    thuis_score = _safe_float(match.get("Thuis_score", 0), 0.0)
    uit_score = _safe_float(match.get("Uit_score", 0), 0.0)
    if thuis_score > uit_score:
        result_thuis = 1.0
        result_uit = 0.0
    elif thuis_score < uit_score:
        result_thuis = 0.0
        result_uit = 1.0
    else:
        result_thuis = 0.5
        result_uit = 0.5

    # 3. Bepaal het scoreverschil en de impactfactor
    score_difference = abs(thuis_score - uit_score)
    point_factor = calculate_point_factor(score_difference)

    # 4. Klinkers veilig uitlezen
    klink_t1 = max(0, _safe_int(match.get("klinkers_thuis_1", 0), 0))
    klink_t2 = max(0, _safe_int(match.get("klinkers_thuis_2", 0), 0))
    klink_u1 = max(0, _safe_int(match.get("klinkers_uit_1", 0), 0))
    klink_u2 = max(0, _safe_int(match.get("klinkers_uit_2", 0), 0))

    # 5. Bereken de nieuwe ELO's voor alle spelers
    # Formule: nieuwe ELO = oude ELO + K * impact * (resultaat - verwachting) + (klinkers * bonus)
    rows = [
        [p1_name, player1_rating + k1 * point_factor * (result_thuis - player1_expected_score) + (klink_t1 * KLINKER_BONUS)],
        [p2_name, player2_rating + k2 * point_factor * (result_thuis - player2_expected_score) + (klink_t2 * KLINKER_BONUS)],
        [p3_name, player3_rating + k3 * point_factor * (result_uit - player3_expected_score) + (klink_u1 * KLINKER_BONUS)],
        [p4_name, player4_rating + k4 * point_factor * (result_uit - player4_expected_score) + (klink_u2 * KLINKER_BONUS)],
    ]
    totaal_overzicht = pd.DataFrame(rows, columns=["Speler", "ELO"])
    return totaal_overzicht

