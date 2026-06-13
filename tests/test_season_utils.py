import pytest
import pandas as pd
import utils.utils_seizoen as utils_seizoen

def test_get_prinsjesdag():
    assert isinstance(utils_seizoen.get_prinsjesdag(2025), pd.Timestamp)

def test_format_season_period():
    season = {'start_datum': pd.Timestamp('2024-09-01'), 'eind_datum': pd.Timestamp('2025-09-01')}
    assert '2024' in utils_seizoen.format_season_period(season)


def test_generate_prinsjesdag_seasons_split():
    matches = pd.DataFrame({'datum': ['2024-09-18', '2025-01-01', '2025-03-15', '2025-03-16', '2025-09-17']})
    seasons_df = utils_seizoen.generate_prinsjesdag_seasons(matches)

    assert any('Zomerseizoen' in s for s in seasons_df['seizoen_naam'])
    assert any('Winterseizoen' in s for s in seasons_df['seizoen_naam'])

    # 14 maart 2025 moet in het Winterseizoen zitten
    matched_14 = seasons_df[(seasons_df['start_datum'] <= pd.Timestamp('2025-03-14 23:59:59')) & (seasons_df['eind_datum'] >= pd.Timestamp('2025-03-14 23:59:59'))]
    assert not matched_14.empty
    assert 'Winterseizoen' in matched_14.iloc[0]['seizoen_naam']

    # 15 maart 2025 moet in het Zomerseizoen zitten
    matched_15 = seasons_df[(seasons_df['start_datum'] <= pd.Timestamp('2025-03-15 00:00:00')) & (seasons_df['eind_datum'] >= pd.Timestamp('2025-03-15 00:00:00'))]
    assert not matched_15.empty
    assert 'Zomerseizoen' in matched_15.iloc[0]['seizoen_naam']


def test_prinsjesdag_transition_is_non_overlapping():
    matches = pd.DataFrame({'datum': ['2025-03-14', '2025-03-15', '2025-03-16', '2025-09-17']})
    seasons_df = utils_seizoen.generate_prinsjesdag_seasons(matches)

    # Controle: de twee segmenten raken elkaar niet en overlappen niet
    dates = []
    for _, row in seasons_df.iterrows():
        dates.append((row['start_datum'], row['eind_datum']))

    for i in range(len(dates) - 1):
        end_this = dates[i][1]
        start_next = dates[i + 1][0]
        assert start_next >= end_this, f"Overlapping seasons: {dates[i]} and {dates[i+1]}"
