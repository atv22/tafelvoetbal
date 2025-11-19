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
