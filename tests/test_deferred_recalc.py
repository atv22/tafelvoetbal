import sys
import os
import time
from datetime import datetime, timedelta
import pandas as pd
import pytest

# Voeg de root-map toe aan sys.path om firestore_service te kunnen importeren
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import firestore_service as db

@pytest.fixture(autouse=True)
def clean_config():
    """Zorgt voor een schone start en opschoning van de system_config collectie."""
    # Bewaar eventuele originele config
    config_ref = db.db.collection("system_config").document("elo_recalc")
    orig_doc = config_ref.get()
    orig_data = orig_doc.to_dict() if orig_doc.exists else None
    
    yield
    
    # Herstel originele config na afloop
    if orig_data:
        config_ref.set(orig_data)
    else:
        config_ref.delete()

def test_set_recalc_needed_flag():
    # Test 1: Schrijf eerste vlag
    start_ts = pd.Timestamp("2026-01-01 10:00:00")
    end_ts = pd.Timestamp("2026-06-30 23:59:59")
    ts1 = pd.Timestamp("2026-03-15 12:00:00")
    
    db.set_recalc_needed_flag(start_ts, end_ts, "CJ 2026 Test", ts1)
    
    status = db.get_recalc_status()
    assert status is not None
    assert status.get("recalc_needed") is True
    assert status.get("season_naam") == "CJ 2026 Test"
    
    # Controleer timestamp
    stored_ts = pd.Timestamp(status.get("earliest_modified_timestamp"))
    # Vergelijk na normalisatie (naive)
    if stored_ts.tzinfo is not None:
        stored_ts = stored_ts.tz_localize(None)
    assert stored_ts == ts1
    
    # Test 2: Schrijf een NIEEUWER tijdstip (moet het OUDERE tijdstip behouden)
    ts_newer = pd.Timestamp("2026-03-20 15:30:00")
    db.set_recalc_needed_flag(start_ts, end_ts, "CJ 2026 Test", ts_newer)
    
    status = db.get_recalc_status()
    stored_ts = pd.Timestamp(status.get("earliest_modified_timestamp"))
    if stored_ts.tzinfo is not None:
        stored_ts = stored_ts.tz_localize(None)
    assert stored_ts == ts1  # Moet nog steeds de oudste (ts1) zijn!
    
    # Test 3: Schrijf een OUDER tijdstip (moet updaten naar het oudere tijdstip)
    ts_older = pd.Timestamp("2026-03-10 09:15:00")
    db.set_recalc_needed_flag(start_ts, end_ts, "CJ 2026 Test", ts_older)
    
    status = db.get_recalc_status()
    stored_ts = pd.Timestamp(status.get("earliest_modified_timestamp"))
    if stored_ts.tzinfo is not None:
        stored_ts = stored_ts.tz_localize(None)
    assert stored_ts == ts_older  # Moet nu de nieuwste oudste (ts_older) zijn!

def test_check_and_run_scheduled_recalc():
    # Bereid config voor: zet recalc_needed op True en last_recalc_time ver in het verleden
    config_ref = db.db.collection("system_config").document("elo_recalc")
    
    start_ts = pd.Timestamp("2026-01-01")
    end_ts = pd.Timestamp("2026-06-30")
    # We gebruiken een fictieve match-tijd
    earliest_ts = pd.Timestamp("2026-06-10 10:00:00")
    
    # Schrijf de config
    config_ref.set({
        "recalc_needed": True,
        "season_start": start_ts,
        "season_end": end_ts,
        "season_naam": "CJ 2026 Test",
        "earliest_modified_timestamp": earliest_ts,
        "last_recalc_time": datetime.now() - timedelta(days=2), # 2 dagen geleden (vóór 23:00 gisteren)
        "timestamp": datetime.now()
    })
    
    # Om de test direct te kunnen draaien zonder te wachten tot 23:00 uur,
    # kunnen we check_and_run_scheduled_recalc aanroepen.
    # Als de lokale tijd bijvoorbeeld 12:00 is, dan is last_scheduled 23:00 gisteren.
    # Onze last_recalc_time (2 dagen geleden) is kleiner dan last_scheduled (gisteren 23:00),
    # dus de transactie zal de herberekening starten!
    
    # We mocken recalculate_elos_from om database writes/reads tijdens deze test te voorkomen
    original_recalc = db.recalculate_elos_from
    called = []
    
    def mock_recalc(ts, start, end):
        called.append((ts, start, end))
        return True
        
    db.recalculate_elos_from = mock_recalc
    
    try:
        # Voer de check uit
        db.check_and_run_scheduled_recalc()
        
        # Controleer of mock_recalc is aangeroepen
        assert len(called) == 1
        # Controleer of status is bijgewerkt in database
        doc = config_ref.get()
        assert doc.exists
        data = doc.to_dict()
        assert data.get("recalc_needed") is False
        assert data.get("earliest_modified_timestamp") is None
        assert data.get("last_recalc_time") is not None
        
    finally:
        db.recalculate_elos_from = original_recalc
