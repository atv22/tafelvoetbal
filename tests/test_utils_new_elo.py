import pytest
from utils import utils_new_elo
import pandas as pd

def test_calculate_point_factor():
    assert utils_new_elo.calculate_point_factor(3) > 0

def test_expected_score_against_player():
    assert 0 <= utils_new_elo.expected_score_against_player(1500, 1500) <= 1

def test_expected_score():
    assert 0 <= utils_new_elo.expected_score(1500, 1500, 1500) <= 1

def test_get_klinkers_for_player():
    row = pd.Series({'thuis_1': 'TestThuisA', 'thuis_2': 'TestThuisB', 'uit_1': 'TestUitA', 'uit_2': 'TestUitB'})
    assert isinstance(utils_new_elo.get_klinkers_for_player('TestThuisA', row), int)
