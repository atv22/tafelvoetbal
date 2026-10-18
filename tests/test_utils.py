import pandas as pd
import pytest
import firestore_service as db
from utils import utils
from utils import utils_seizoen


def test_get_nl_now():
    result = utils.get_nl_now()
    assert result is not None


def test_add_name(monkeypatch):
    added_players = []
    monkeypatch.setattr(db, "get_players", lambda: pd.DataFrame([{"speler_naam": "Bestaand", "rating": 1000}]))
    monkeypatch.setattr(db, "add_player", lambda name, elo=1000, **kwargs: (added_players.append((name, elo)) or "Success"))

    # Geldige naam met hoofdletter
    resultaat = utils.add_name("Nieuwe speler", rerun=False)
    assert resultaat == "Nieuwe speler"
    assert added_players == [("Nieuwe speler", 1000)]

    # Naam zonder hoofdletter wordt geweigerd
    assert utils.add_name("nieuwe speler", rerun=False) is None

    # Ongeldige naam met cijfers wordt geweigerd
    assert utils.add_name("Test1234", rerun=False) is None

    # Bestaande naam (case-insensitive) wordt geweigerd
    assert utils.add_name("Bestaand", rerun=False) is None



def test_add_request(monkeypatch):
    added_requests = []
    monkeypatch.setattr(db, "add_request", lambda text: (added_requests.append(text) or "Success"))

    assert utils.add_request("Test verzoek", rerun=False) == "Test verzoek"
    assert added_requests == ["Test verzoek"]
    assert utils.add_request("   ", rerun=False) is None


def test_get_download_filename():
    filename = utils.get_download_filename("bestand", "csv")
    assert filename.startswith("bestand_") and filename.endswith(".csv")


def test_season_utils_tz_and_stats():
    matches_df = pd.DataFrame([
        {
            "timestamp": pd.Timestamp("2025-04-10 12:00:00", tz="UTC"),
            "thuis_1": "Alice",
            "thuis_2": "Bob",
            "uit_1": "Charlie",
            "uit_2": "Dave",
            "thuis_score": 10,
            "uit_score": 6,
        }
    ])
    seasons_df = utils_seizoen.generate_prinsjesdag_seasons(matches_df)
    assert not seasons_df.empty

    season = seasons_df.iloc[0]
    season_matches = utils_seizoen.get_season_matches(matches_df, season)
    assert len(season_matches) == 1

    stats = utils_seizoen.calculate_season_stats(season_matches)
    assert stats["total_matches"] == 1
    assert stats["total_goals"] == 16
    assert stats["unique_players"] == 4

