import os
import sys
import pandas as pd
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import firestore_service as db
from analytics import get_season_top3_elo
from tabs.tab_home import calculate_elo_trends
from tabs.tab_invullen import calculate_new_elos, validate_match_input
from utils.utils_new_elo import calculate_new_elo


def test_validate_match_input():
    valid_players = {
        'Thuis 1': {'name': 'Alice', 'klinkers': 1},
        'Thuis 2': {'name': 'Bob', 'klinkers': 1},
        'Uit 1': {'name': 'Charlie', 'klinkers': 0},
        'Uit 2': {'name': 'Dave', 'klinkers': 2},
    }
    assert validate_match_input(valid_players, 10, 5) is True
    # Beide 10 of geen 10 ongeldig
    assert validate_match_input(valid_players, 10, 10) is False
    assert validate_match_input(valid_players, 9, 8) is False

    # Klinkers hoger dan teamscore ongeldig
    too_many_klinkers = {
        'Thuis 1': {'name': 'Alice', 'klinkers': 2},
        'Thuis 2': {'name': 'Bob', 'klinkers': 2},
        'Uit 1': {'name': 'Charlie', 'klinkers': 0},
        'Uit 2': {'name': 'Dave', 'klinkers': 0},
    }
    assert validate_match_input(too_many_klinkers, 3, 10) is False

    # Dubbele speler ongeldig
    dup_players = {
        'Thuis 1': {'name': 'Alice', 'klinkers': 0},
        'Thuis 2': {'name': 'Alice', 'klinkers': 0},
        'Uit 1': {'name': 'Charlie', 'klinkers': 0},
        'Uit 2': {'name': 'Dave', 'klinkers': 0},
    }
    assert validate_match_input(dup_players, 10, 4) is False

    # Achterwaartse compatibiliteit zonder 'klinkers'-sleutel
    no_klinker_key = {
        'Thuis 1': {'name': 'Alice'},
        'Thuis 2': {'name': 'Bob'},
        'Uit 1': {'name': 'Charlie'},
        'Uit 2': {'name': 'Dave'},
    }
    assert validate_match_input(no_klinker_key, 10, 7) is True


def test_calculate_new_elos_season_start_1000_and_backdated_cutoff():
    seasons_df = pd.DataFrame([
        {
            'seizoen_naam': 'CJ 2026 Zomer',
            'start_datum': pd.Timestamp('2026-03-15 00:00:00'),
            'eind_datum': pd.Timestamp('2026-09-15 23:59:59'),
        },
        {
            'seizoen_naam': 'CJ 2026 Winter',
            'start_datum': pd.Timestamp('2026-09-16 00:00:00'),
            'eind_datum': pd.Timestamp('2027-03-14 23:59:59'),
        },
    ])
    matches_df = pd.DataFrame([
        {
            'match_id': 'm_zomer',
            'timestamp': pd.Timestamp('2026-09-10 12:00:00'),
            'thuis_1': 'Eve', 'thuis_2': 'Frank', 'uit_1': 'Grace', 'uit_2': 'Alice',
            'thuis_score': 10, 'uit_score': 4,
            'klinkers_thuis_1': 0, 'klinkers_thuis_2': 0, 'klinkers_uit_1': 0, 'klinkers_uit_2': 0,
        },
        {
            'match_id': 'm_winter_1',
            'timestamp': pd.Timestamp('2026-09-16 14:00:00'),
            'thuis_1': 'Alice', 'thuis_2': 'Bob', 'uit_1': 'Charlie', 'uit_2': 'Dave',
            'thuis_score': 10, 'uit_score': 6,
            'klinkers_thuis_1': 0, 'klinkers_thuis_2': 0, 'klinkers_uit_1': 0, 'klinkers_uit_2': 0,
        },
    ])
    elo_df = pd.DataFrame([
        {'match_id': 'SEASON_RESET', 'speler_naam': 'Alice', 'rating': 1000.0, 'timestamp': pd.Timestamp('2026-09-16 00:00:00')},
        {'match_id': 'm_zomer', 'speler_naam': 'Eve', 'rating': 1250.0, 'timestamp': pd.Timestamp('2026-09-10 12:00:00')},
        {'match_id': 'm_winter_1', 'speler_naam': 'Alice', 'rating': 1035.0, 'timestamp': pd.Timestamp('2026-09-16 14:00:00')},
    ])
    # Globale spelerstabel heeft zomer-ELO's staan
    player_elos = {'Alice': 1300.0, 'Eve': 1250.0, 'Frank': 1180.0, 'Grace': 920.0}
    selected = {
        'Thuis 1': {'name': 'Alice', 'klinkers': 0},
        'Thuis 2': {'name': 'Eve', 'klinkers': 0},
        'Uit 1': {'name': 'Frank', 'klinkers': 0},
        'Uit 2': {'name': 'Grace', 'klinkers': 0},
    }

    # Wedstrijd na m_winter_1: Alice gebruikt winter-ELO (1035, 1 eerder potje), Eve/Frank/Grace starten op 1000!
    res = calculate_new_elos(
        selected, 10, 5, player_elos,
        matches_df=matches_df,
        match_date=pd.Timestamp('2026-09-20 12:00:00'),
        seasons_df=seasons_df,
        elo_df=elo_df,
    )
    expected = calculate_new_elo(
        {"Thuis_1": "Alice", "Thuis_2": "Eve", "Uit_1": "Frank", "Uit_2": "Grace", "Thuis_score": 10, "Uit_score": 5},
        {"Alice": [1035.0, 1035.0], "Eve": [1000.0], "Frank": [1000.0], "Grace": [1000.0]},
    ).set_index("Speler")["ELO"].to_dict()
    for p, val in expected.items():
        assert res[p] == pytest.approx(val)

    # Backdated wedstrijd VÓÓR m_winter_1: ook Alice had nog 0 winterpotjes en start op 1000!
    res_back = calculate_new_elos(
        selected, 10, 5, player_elos,
        matches_df=matches_df,
        match_date=pd.Timestamp('2026-09-16 10:00:00'),
        seasons_df=seasons_df,
        elo_df=elo_df,
    )
    assert res_back["Alice"] == pytest.approx(res_back["Eve"])


def test_calculate_elo_trends_season_boundaries_and_ties():
    elo_df = pd.DataFrame([
        {'match_id': 'm_zomer', 'speler_naam': 'Arthur', 'rating': 1270.0, 'timestamp': pd.Timestamp('2026-09-15 15:00:00')},
        {'match_id': 'SEASON_RESET', 'speler_naam': 'Arthur', 'rating': 1000.0, 'timestamp': pd.Timestamp('2026-09-16 00:00:00')},
        {'match_id': 'm_win_1', 'speler_naam': 'Arthur', 'rating': 1030.0, 'timestamp': pd.Timestamp('2026-09-16 13:00:00')},
        # Gelijke timestamps met deterministische tie-breaker op match_id
        {'match_id': 'm_tie_a', 'speler_naam': 'Bernd', 'rating': 1030.0, 'timestamp': pd.Timestamp('2026-09-16 13:00:00')},
        {'match_id': 'm_tie_b', 'speler_naam': 'Bernd', 'rating': 1055.0, 'timestamp': pd.Timestamp('2026-09-16 13:00:00')},
    ])
    trends = calculate_elo_trends(elo_df, season_start='2026-09-16', season_end='2027-03-14')
    assert trends['Arthur'] == 30
    assert trends['Bernd'] == 25


def test_get_season_top3_elo_nat_and_qualification():
    seizoen_matches = pd.DataFrame([
        {'match_id': 'm1', 'thuis_1': 'Q1', 'thuis_2': 'Q2', 'uit_1': 'Q3', 'uit_2': 'U1', 'thuis_score': 10, 'uit_score': 5},
        {'match_id': 'm2', 'thuis_1': 'Q1', 'thuis_2': 'Q2', 'uit_1': 'Q3', 'uit_2': 'U2', 'thuis_score': 10, 'uit_score': 6},
        {'match_id': 'm3', 'thuis_1': 'Q1', 'thuis_2': 'Q2', 'uit_1': 'Q3', 'uit_2': 'U3', 'thuis_score': 10, 'uit_score': 7},
    ])
    elo_df = pd.DataFrame([
        {'match_id': 'm1', 'speler_naam': 'Q1', 'rating': 1500.0, 'timestamp': pd.NaT},
        {'match_id': 'm2', 'speler_naam': 'Q1', 'rating': 1080.0, 'timestamp': pd.Timestamp('2026-04-01 12:00:00')},
        {'match_id': 'm3', 'speler_naam': 'Q1', 'rating': 1090.0, 'timestamp': pd.Timestamp('2026-04-02 12:00:00')},
        {'match_id': 'm3', 'speler_naam': 'Q2', 'rating': 1060.0, 'timestamp': pd.Timestamp('2026-04-02 12:00:00')},
        {'match_id': 'm3', 'speler_naam': 'Q3', 'rating': 950.0, 'timestamp': pd.Timestamp('2026-04-02 12:00:00')},
        # Ongekwalificeerde speler heeft hoogste rating (1200) maar slechts 1 wedstrijd
        {'match_id': 'm1', 'speler_naam': 'U1', 'rating': 1200.0, 'timestamp': pd.Timestamp('2026-04-01 10:00:00')},
    ])
    top3 = get_season_top3_elo(elo_df, seizoen_matches)
    names = [name for name, _ in top3]
    ratings = dict(top3)
    assert names == ['Q1', 'Q2', 'Q3']
    assert ratings['Q1'] == pytest.approx(1090.0)


def test_recalculate_elos_from_boundaries_and_historical_isolation(monkeypatch):
    summer_start = pd.Timestamp('2026-03-15 00:00:00')
    summer_end = pd.Timestamp('2026-09-15 23:59:59')

    matches_df = pd.DataFrame([
        {
            'match_id': 'z1', 'timestamp': pd.Timestamp('2026-03-20 12:00:00'),
            'thuis_1': 'Alice', 'thuis_2': 'Bob', 'uit_1': 'Charlie', 'uit_2': 'Dave',
            'thuis_score': 10, 'uit_score': 5,
            'klinkers_thuis_1': 1, 'klinkers_thuis_2': 0, 'klinkers_uit_1': 0, 'klinkers_uit_2': 0,
        },
        {
            'match_id': 'z2', 'timestamp': pd.Timestamp('2026-05-01 12:00:00'),
            'thuis_1': 'Charlie', 'thuis_2': 'Alice', 'uit_1': 'Bob', 'uit_2': 'Dave',
            'thuis_score': 10, 'uit_score': 8,
            'klinkers_thuis_1': 0, 'klinkers_thuis_2': 0, 'klinkers_uit_1': 0, 'klinkers_uit_2': 0,
        },
        {
            'match_id': 'z3_lastday', 'timestamp': pd.Timestamp('2026-09-15 19:00:00'),
            'thuis_1': 'Bob', 'thuis_2': 'Dave', 'uit_1': 'Alice', 'uit_2': 'Charlie',
            'thuis_score': 10, 'uit_score': 7,
            'klinkers_thuis_1': 0, 'klinkers_thuis_2': 0, 'klinkers_uit_1': 0, 'klinkers_uit_2': 0,
        },
        {
            'match_id': 'w1', 'timestamp': pd.Timestamp('2026-09-16 12:00:00'),
            'thuis_1': 'Alice', 'thuis_2': 'Bob', 'uit_1': 'Charlie', 'uit_2': 'Dave',
            'thuis_score': 10, 'uit_score': 2,
            'klinkers_thuis_1': 0, 'klinkers_thuis_2': 0, 'klinkers_uit_1': 0, 'klinkers_uit_2': 0,
        },
    ])
    players_df = pd.DataFrame([
        {'speler_id': 'p1', 'speler_naam': 'Alice', 'rating': 1111.0},
        {'speler_id': 'p2', 'speler_naam': 'Bob', 'rating': 1122.0},
        {'speler_id': 'p3', 'speler_naam': 'Charlie', 'rating': 933.0},
        {'speler_id': 'p4', 'speler_naam': 'Dave', 'rating': 944.0},
    ])

    # In-memory mock van Firestore elo en spelers collecties
    elo_store = {
        'reset_z': {'speler_naam': 'Alice', 'rating': 1000.0, 'timestamp': pd.Timestamp('2026-03-15 00:00:00', tz='UTC'), 'match_id': 'SEASON_RESET'},
        'old_z2': {'speler_naam': 'Alice', 'rating': 999.0, 'timestamp': pd.Timestamp('2026-05-01 12:00:00', tz='UTC'), 'match_id': 'z2'},
        'reset_w': {'speler_naam': 'Alice', 'rating': 1000.0, 'timestamp': pd.Timestamp('2026-09-16 00:00:00', tz='UTC'), 'match_id': 'SEASON_RESET'},
        'win_w1': {'speler_naam': 'Alice', 'rating': 1050.0, 'timestamp': pd.Timestamp('2026-09-16 12:00:00', tz='UTC'), 'match_id': 'w1'},
    }
    player_updates = []
    id_counter = {'n': 0}

    class FakeDocSnap:
        def __init__(self, doc_id, data):
            self.id = doc_id
            self._data = data
            self.reference = ('elo', doc_id)

        def to_dict(self):
            return dict(self._data)

    class FakeQuery:
        def __init__(self, filters=None):
            self.filters = filters or []

        def where(self, filter=None):
            return FakeQuery(self.filters + [filter])

        def stream(self):
            res = []
            for did, ddata in list(elo_store.items()):
                ts = pd.Timestamp(ddata['timestamp'])
                ok = True
                for flt in self.filters:
                    val = pd.Timestamp(flt.value)
                    if flt.op_string == '>=' and not (ts >= val):
                        ok = False
                    elif flt.op_string == '<=' and not (ts <= val):
                        ok = False
                if ok:
                    res.append(FakeDocSnap(did, ddata))
            return res

    class FakeEloRef:
        def where(self, filter=None):
            return FakeQuery([filter])

        def document(self):
            id_counter['n'] += 1
            return ('elo', f"new_{id_counter['n']}")

    class FakePlayersRef:
        def document(self, pid):
            return ('players', pid)

    class FakeBatch:
        def __init__(self):
            self.ops = []

        def delete(self, ref):
            self.ops.append(('delete', ref, None))

        def set(self, ref, data):
            self.ops.append(('set', ref, data))

        def update(self, ref, data):
            self.ops.append(('update', ref, data))

        def commit(self):
            for op, ref, data in self.ops:
                coll, doc_id = ref
                if coll == 'elo':
                    if op == 'delete':
                        elo_store.pop(doc_id, None)
                    elif op == 'set':
                        elo_store[doc_id] = dict(data)
                elif coll == 'players' and op == 'update':
                    player_updates.append((doc_id, data))
            self.ops.clear()

    monkeypatch.setattr(db, 'elo_ref', FakeEloRef())
    monkeypatch.setattr(db, 'players_ref', FakePlayersRef())
    monkeypatch.setattr(db.db, 'batch', lambda: FakeBatch())
    monkeypatch.setattr(db, 'get_matches', lambda: matches_df)
    monkeypatch.setattr(db, 'get_players', lambda: players_df)
    monkeypatch.setattr(db, '_sync_recalculated_elo_to_gsheet', lambda *args, **kwargs: True)
    monkeypatch.setattr(db, 'clear_all_caches', lambda **kwargs: None)

    ok = db.recalculate_elos_from(pd.Timestamp('2026-04-01 00:00:00'), summer_start, summer_end)
    assert ok is True

    # Winter logs en Summer SEASON_RESET zijn intact gebleven
    assert 'reset_z' in elo_store
    assert 'reset_w' in elo_store
    assert 'win_w1' in elo_store
    assert 'old_z2' not in elo_store

    # Omdat het een historisch seizoen is, is spelers.rating NIET overschreven
    assert player_updates == []

    # Incrementele herberekening vanaf april komt exact overeen met volledige zomer-replay
    summer_matches = matches_df[matches_df['match_id'].str.startswith('z')]
    expected_elos, _, _ = db.replay_season_elos(summer_matches)
    z3_logs = {v['speler_naam']: v['rating'] for v in elo_store.values() if v.get('match_id') == 'z3_lastday'}
    for p, val in expected_elos.items():
        assert z3_logs[p] == pytest.approx(val, abs=1e-9)


def test_audit_season_elo_detects_drift():
    matches_df = pd.DataFrame([
        {
            'match_id': 'm1', 'timestamp': pd.Timestamp('2026-09-16 12:00:00'),
            'thuis_1': 'Alice', 'thuis_2': 'Bob', 'uit_1': 'Charlie', 'uit_2': 'Dave',
            'thuis_score': 10, 'uit_score': 5,
            'klinkers_thuis_1': 0, 'klinkers_thuis_2': 0, 'klinkers_uit_1': 0, 'klinkers_uit_2': 0,
        },
        {
            'match_id': 'm2', 'timestamp': pd.Timestamp('2026-09-17 12:00:00'),
            'thuis_1': 'Charlie', 'thuis_2': 'Dave', 'uit_1': 'Alice', 'uit_2': 'Bob',
            'thuis_score': 10, 'uit_score': 7,
            'klinkers_thuis_1': 0, 'klinkers_thuis_2': 0, 'klinkers_uit_1': 0, 'klinkers_uit_2': 0,
        },
    ])
    # Simuleer ontbrekende reset: opgeslagen ratings zijn 200 punten verschoven
    drifted_elo = pd.DataFrame([
        {'match_id': 'm1', 'speler_naam': 'Alice', 'rating': 1235.0, 'timestamp': pd.Timestamp('2026-09-16 12:00:00')},
        {'match_id': 'm1', 'speler_naam': 'Bob', 'rating': 1235.0, 'timestamp': pd.Timestamp('2026-09-16 12:00:00')},
        {'match_id': 'm1', 'speler_naam': 'Charlie', 'rating': 1165.0, 'timestamp': pd.Timestamp('2026-09-16 12:00:00')},
        {'match_id': 'm1', 'speler_naam': 'Dave', 'rating': 1165.0, 'timestamp': pd.Timestamp('2026-09-16 12:00:00')},
        {'match_id': 'm2', 'speler_naam': 'Alice', 'rating': 1200.0, 'timestamp': pd.Timestamp('2026-09-17 12:00:00')},
        {'match_id': 'm2', 'speler_naam': 'Bob', 'rating': 1200.0, 'timestamp': pd.Timestamp('2026-09-17 12:00:00')},
        {'match_id': 'm2', 'speler_naam': 'Charlie', 'rating': 1200.0, 'timestamp': pd.Timestamp('2026-09-17 12:00:00')},
        {'match_id': 'm2', 'speler_naam': 'Dave', 'rating': 1200.0, 'timestamp': pd.Timestamp('2026-09-17 12:00:00')},
    ])
    players_df = pd.DataFrame([{'speler_naam': p, 'rating': 1200.0} for p in ['Alice', 'Bob', 'Charlie', 'Dave']])

    audit = db.audit_season_elo(
        pd.Timestamp('2026-09-16'),
        pd.Timestamp('2027-03-14 23:59:59'),
        matches_df=matches_df,
        elo_df=drifted_elo,
        players_df=players_df,
    )
    assert audit['match_count'] == 2
    assert audit['missing_elo_logs'] == 0
    assert audit['mismatched_logs_count'] == 8
    assert audit['max_player_diff'] > 50.0


def test_rename_player_validation(monkeypatch):
    monkeypatch.setattr(
        db,
        'get_players',
        lambda: pd.DataFrame([
            {'speler_id': '1', 'speler_naam': 'Jan', 'rating': 1050},
            {'speler_id': '2', 'speler_naam': 'Piet', 'rating': 980},
        ]),
    )
    ok, _ = db.rename_player('Jan', '')
    assert ok is False
    ok, _ = db.rename_player('Jan', 'jan')
    assert ok is False
    ok, _ = db.rename_player('Jan', 'Piet')
    assert ok is False
    ok, _ = db.rename_player('Jan', 'Niemand')
    assert ok is False
    ok, _ = db.rename_player('Jan', 'Jan123')
    assert ok is False


def test_process_match_submission_timestamp_dedup_and_deferred_reset(monkeypatch):
    from tabs import tab_invullen

    seasons_df = pd.DataFrame([
        {
            'seizoen_naam': 'CJ 2026 Zomer',
            'start_datum': pd.Timestamp('2026-03-15 00:00:00'),
            'eind_datum': pd.Timestamp('2026-09-15 23:59:59'),
        },
        {
            'seizoen_naam': 'CJ 2026 Winter',
            'start_datum': pd.Timestamp('2026-09-16 00:00:00'),
            'eind_datum': pd.Timestamp('2027-03-14 23:59:59'),
        },
    ])
    # Alleen zomerwedstrijden -> winter is leeg (dus nieuw seizoen)
    matches_df = pd.DataFrame([
        {
            'match_id': 'z1',
            'timestamp': pd.Timestamp('2026-09-10 12:00:00'),
            'thuis_1': 'Alice', 'thuis_2': 'Bob', 'uit_1': 'Charlie', 'uit_2': 'Dave',
            'thuis_score': 10, 'uit_score': 5,
        }
    ])

    reset_calls = []
    added_calls = []
    monkeypatch.setattr(db, 'reset_all_elos', lambda ts=None: reset_calls.append(ts) or True)
    monkeypatch.setattr(
        db,
        'add_match_and_update_elo',
        lambda m, e, update_current_rating=True: added_calls.append((m, e, update_current_rating)) or True,
    )
    monkeypatch.setattr(db, 'get_elo_logs', lambda: pd.DataFrame())
    monkeypatch.setattr(tab_invullen.st, 'rerun', lambda: None)
    monkeypatch.setattr(tab_invullen.time, 'sleep', lambda *_: None)

    selected = {
        'Thuis 1': {'name': 'Alice', 'klinkers': 0},
        'Thuis 2': {'name': 'Bob', 'klinkers': 0},
        'Uit 1': {'name': 'Charlie', 'klinkers': 0},
        'Uit 2': {'name': 'Dave', 'klinkers': 0},
    }
    player_elos = {'Alice': 1200.0, 'Bob': 1100.0, 'Charlie': 950.0, 'Dave': 900.0}

    # Test 1: Nieuwe seizoenswedstrijd slaat reset op en reset ELO's naar 1000 vóór opslaan
    ok = tab_invullen.process_match_submission(
        selected, 10, 6, player_elos, pd.Timestamp('2026-09-16 12:00:00'),
        matches_df=matches_df, seasons_df=seasons_df, elo_df=pd.DataFrame(),
    )
    assert ok is True
    assert len(reset_calls) == 1
    assert len(added_calls) == 1
    # ELO-updates komen uit 1000.0-start (niet uit 1200/900)
    saved_elos = dict(added_calls[0][1])
    assert saved_elos['Alice'] == pytest.approx(saved_elos['Bob'])

    # Test 2: Tijdstempelbotsing op exact dezelfde seconde wordt met +1s ontdubbeld
    reset_calls.clear()
    added_calls.clear()
    matches_df_with_collision = pd.DataFrame([
        {
            'match_id': 'w1',
            'timestamp': pd.Timestamp('2026-09-20 12:00:00'),
            'thuis_1': 'Alice', 'thuis_2': 'Charlie', 'uit_1': 'Bob', 'uit_2': 'Dave',
            'thuis_score': 10, 'uit_score': 4,
        }
    ])
    ok2 = tab_invullen.process_match_submission(
        selected, 10, 8, player_elos, pd.Timestamp('2026-09-20 12:00:00'),
        matches_df=matches_df_with_collision, seasons_df=seasons_df, elo_df=pd.DataFrame(),
    )
    assert ok2 is True
    assert added_calls[0][0]['timestamp'] == pd.Timestamp('2026-09-20 12:00:01').to_pydatetime()


def test_gsheet_sanitization_handles_lists_timestamps_and_preserves_sheet_on_error():
    import json
    import numpy as np

    df = pd.DataFrame([
        {
            'speler_id': 'p1',
            'speler_naam': 'Léon',
            'rating': np.float64(1035.66),
            'aliassen': ['Léon', 'Lee'],
            'meta': {'a': 1},
            'ts': pd.Timestamp('2026-09-16 00:00:00', tz='UTC'),
        },
        {
            'speler_id': 'p2',
            'speler_naam': 'Johannes',
            'rating': np.nan,
            'aliassen': [],
            'meta': None,
            'ts': pd.NaT,
        },
    ])
    rows = db._df_to_gsheet_rows(df)
    # Strikte JSON-serialiseerbaarheid zonder geneste lijsten of NaN
    dumped = json.dumps(rows, allow_nan=False)
    assert '"L\\u00e9on, Lee"' in dumped or '"Léon, Lee"' in dumped
    assert rows[1] == ['p1', 'Léon', 1035.66, 'Léon, Lee', '{"a": 1}', '2026-09-16 00:00:00']
    assert rows[2] == ['p2', 'Johannes', '', '', '', '']

    class FakeWorksheet:
        def __init__(self, initial_rows, fail_on_update=False):
            self.rows = initial_rows
            self.fail_on_update = fail_on_update
            self.clear_called = False
            self.batch_cleared = []

        def get_all_values(self):
            return list(self.rows)

        def clear(self):
            self.clear_called = True

        def update(self, values=None, range_name='A1'):
            if self.fail_on_update:
                raise RuntimeError("API 400")
            self.rows = values

        def batch_clear(self, ranges):
            self.batch_cleared.extend(ranges)

    # Bij foutieve update mag oude inhoud nooit gewist worden
    ws_fail = FakeWorksheet([['a', 'b'], ['1', '2']], fail_on_update=True)
    with pytest.raises(RuntimeError):
        db._safe_replace_worksheet(ws_fail, [['x', 'y'], ['3', '4']])
    assert ws_fail.clear_called is False
    assert ws_fail.batch_cleared == []
    assert ws_fail.rows == [['a', 'b'], ['1', '2']]

    # Bij krimpende update (5x4 -> 3x3) worden overtollige rijen en kolommen achteraf opgeruimd
    ws_shrink = FakeWorksheet([['a', 'b', 'c', 'd']] * 5, fail_on_update=False)
    ok = db._safe_replace_worksheet(ws_shrink, [['h1', 'h2', 'h3'], ['1', '2', '3'], ['4', '5', '6']])
    assert ok is True
    assert ws_shrink.clear_called is False
    assert ws_shrink.batch_cleared == ['A4:D5', 'D1:D3']


def test_home_calculate_stats_rounds_elo_consistently():
    from tabs.tab_home import calculate_stats

    players_df = pd.DataFrame([
        {'speler_naam': 'Johannes', 'rating': 1035.66},
        {'speler_naam': 'Bernd', 'rating': 1031.70},
        {'speler_naam': 'Sander', 'rating': 1065.45},
    ])
    # 1) Fallback zonder wedstrijden rondt correct af naar dichtstbijzijnde integer
    fallback_stats = calculate_stats(players_df, pd.DataFrame())
    fb_map = dict(zip(fallback_stats['Speler'], fallback_stats['ELO']))
    assert fb_map['Johannes'] == 1036
    assert fb_map['Bernd'] == 1032
    assert fb_map['Sander'] == 1065

    # 2) Seizoens-ELO uit elo_df rondt ook af (1035.66 -> 1036, 1031.70 -> 1032)
    matches_df = pd.DataFrame([
        {
            'match_id': 'w1',
            'timestamp': pd.Timestamp('2026-09-20 12:00:00'),
            'thuis_1': 'Johannes', 'thuis_2': 'Bernd',
            'uit_1': 'Sander', 'uit_2': 'Laura',
            'thuis_score': 10, 'uit_score': 6,
            'klinkers_thuis_1': 0, 'klinkers_thuis_2': 0, 'klinkers_uit_1': 0, 'klinkers_uit_2': 0,
        }
    ])
    elo_df = pd.DataFrame([
        {'match_id': 'w1', 'speler_naam': 'Johannes', 'rating': 1035.66, 'timestamp': pd.Timestamp('2026-09-20 12:00:00')},
        {'match_id': 'w1', 'speler_naam': 'Bernd', 'rating': 1031.70, 'timestamp': pd.Timestamp('2026-09-20 12:00:00')},
        {'match_id': 'w1', 'speler_naam': 'Sander', 'rating': 1065.45, 'timestamp': pd.Timestamp('2026-09-20 12:00:00')},
    ])
    season_stats = calculate_stats(
        players_df,
        matches_df,
        elo_df=elo_df,
        season_start=pd.Timestamp('2026-09-16 00:00:00'),
        season_end=pd.Timestamp('2027-03-14 23:59:59'),
    )
    season_map = dict(zip(season_stats['Speler'], season_stats['ELO']))
    assert season_map['Johannes'] == 1036
    assert season_map['Bernd'] == 1032
    assert season_map['Sander'] == 1065


