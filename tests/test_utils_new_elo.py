import math
import pandas as pd
import pytest
from utils import utils_new_elo


def test_calculate_point_factor():
    assert utils_new_elo.calculate_point_factor(0) == pytest.approx(2.0)
    assert utils_new_elo.calculate_point_factor(3) > 2.0
    assert utils_new_elo.calculate_point_factor(9) == pytest.approx(3.0)
    assert utils_new_elo.calculate_point_factor(10) == pytest.approx(2 + math.log10(11) ** 3)
    # Negatieve of ongeldige waarden blijven veilig
    assert utils_new_elo.calculate_point_factor(-5) == pytest.approx(utils_new_elo.calculate_point_factor(5))
    assert utils_new_elo.calculate_point_factor(None) == pytest.approx(2.0)
    assert utils_new_elo.calculate_point_factor(float("nan")) == pytest.approx(2.0)


def test_expected_score_against_player():
    assert utils_new_elo.expected_score_against_player(1500, 1500) == pytest.approx(0.5)
    assert utils_new_elo.expected_score_against_player(1500, 1000) == pytest.approx(10 / 11)
    e_ab = utils_new_elo.expected_score_against_player(1150, 980)
    e_ba = utils_new_elo.expected_score_against_player(980, 1150)
    assert e_ab + e_ba == pytest.approx(1.0)


def test_expected_score():
    assert utils_new_elo.expected_score(1500, 1500, 1500) == pytest.approx(0.5)
    expected_avg = (
        utils_new_elo.expected_score_against_player(1200, 1000)
        + utils_new_elo.expected_score_against_player(1200, 1400)
    ) / 2
    assert utils_new_elo.expected_score(1200, 1000, 1400) == pytest.approx(expected_avg)


def test_get_klinkers_for_player():
    row = pd.Series({
        'thuis_1': 'TestThuisA',
        'thuis_2': 'TestThuisB',
        'uit_1': 'TestUitA',
        'uit_2': 'TestUitB',
        'klinkers_thuis_1': float('nan'),
        'klinkers_thuis_2': None,
        'klinkers_uit_1': '2',
        'klinkers_uit_2': -1,
    })
    assert utils_new_elo.get_klinkers_for_player('TestThuisA', row) == 0
    assert utils_new_elo.get_klinkers_for_player('TestThuisB', row) == 0
    assert utils_new_elo.get_klinkers_for_player('TestUitA', row) == 2
    assert utils_new_elo.get_klinkers_for_player('TestUitB', row) == 0
    assert utils_new_elo.get_klinkers_for_player('Onbekend', row) == 0


def test_calculate_new_elo_zero_sum_and_margin():
    ratings = {p: [1000.0] for p in ['A', 'B', 'C', 'D']}
    close_match = {
        "Thuis_1": "A", "Thuis_2": "B", "Uit_1": "C", "Uit_2": "D",
        "Thuis_score": 10, "Uit_score": 9,
    }
    blowout_match = {
        "Thuis_1": "A", "Thuis_2": "B", "Uit_1": "C", "Uit_2": "D",
        "Thuis_score": 10, "Uit_score": 0,
    }

    res_close = utils_new_elo.calculate_new_elo(close_match, ratings).set_index("Speler")["ELO"].to_dict()
    res_blowout = utils_new_elo.calculate_new_elo(blowout_match, ratings).set_index("Speler")["ELO"].to_dict()

    # Zero-sum zonder klinkers bij gelijke K-factoren
    assert sum(res_close.values()) == pytest.approx(4000.0)
    assert sum(res_blowout.values()) == pytest.approx(4000.0)
    assert res_close["A"] == pytest.approx(res_close["B"])
    assert res_close["C"] == pytest.approx(res_close["D"])
    # Grotere overwinning levert meer ELO op
    assert res_blowout["A"] > res_close["A"] > 1000.0
    assert res_blowout["C"] < res_close["C"] < 1000.0


def test_calculate_new_elo_k_decay_and_klinkers():
    ratings = {
        "Nieuw": [1000.0],
        "Ervaren": [1000.0] * 101,
        "Uit1": [1000.0],
        "Uit2": [1000.0],
    }
    match = {
        "Thuis_1": "Nieuw", "Thuis_2": "Ervaren", "Uit_1": "Uit1", "Uit_2": "Uit2",
        "Thuis_score": 10, "Uit_score": 5,
        "klinkers_thuis_1": 0, "klinkers_thuis_2": 2,
        "klinkers_uit_1": 1, "klinkers_uit_2": 0,
    }
    res = utils_new_elo.calculate_new_elo(match, ratings).set_index("Speler")["ELO"].to_dict()

    # Ervaren speler heeft lagere K-factor -> lagere basiswinst (zonder klinkers) dan Nieuw
    ervaren_basis = res["Ervaren"] - 2 * 15
    assert 1000.0 < ervaren_basis < res["Nieuw"]
    # Klinkerbonus geldt ook voor verliezer (+15)
    assert res["Uit1"] - res["Uit2"] == pytest.approx(15.0)


def test_calculate_new_elo_nan_none_comma_resilience_and_draw():
    ratings = {
        "A": ["1050,5"],
        "B": [None],
        "C": [float("nan")],
        "D": [1000.0],
    }
    match = {
        "Thuis_1": "A", "Thuis_2": "B", "Uit_1": "C", "Uit_2": "D",
        "Thuis_score": 10, "Uit_score": 6,
        "klinkers_thuis_1": float("nan"),
        "klinkers_thuis_2": None,
        "klinkers_uit_1": "2",
        "klinkers_uit_2": 0,
    }
    res = utils_new_elo.calculate_new_elo(match, ratings)
    assert not res["ELO"].isna().any()

    # Gelijkspel bij gelijke ratings zonder klinkers -> 0 mutatie
    equal_ratings = {p: [1000.0] for p in ['A', 'B', 'C', 'D']}
    draw_match = {
        "Thuis_1": "A", "Thuis_2": "B", "Uit_1": "C", "Uit_2": "D",
        "Thuis_score": 5, "Uit_score": 5,
    }
    res_draw = utils_new_elo.calculate_new_elo(draw_match, equal_ratings)
    assert all(val == pytest.approx(1000.0) for val in res_draw["ELO"])

