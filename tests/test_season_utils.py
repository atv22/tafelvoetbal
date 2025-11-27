import pytest
import pandas as pd
import season_utils

def test_get_prinsjesdag():
    assert isinstance(season_utils.get_prinsjesdag(2025), pd.Timestamp)

def test_format_season_period():
    season = {'startdatum': pd.Timestamp('2024-09-01'), 'einddatum': pd.Timestamp('2025-09-01')}
    assert '2024' in season_utils.format_season_period(season)
