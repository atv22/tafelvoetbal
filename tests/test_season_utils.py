import pytest
import pandas as pd
import utils.utils_seizoen as utils_seizoen

def test_get_prinsjesdag():
    assert isinstance(utils_seizoen.get_prinsjesdag(2025), pd.Timestamp)

def test_format_season_period():
    season = {'startdatum': pd.Timestamp('2024-09-01'), 'einddatum': pd.Timestamp('2025-09-01')}
    assert '2024' in utils_seizoen.format_season_period(season)
