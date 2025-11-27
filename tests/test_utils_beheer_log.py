import pytest
from utils import utils_beheer_log

def test_log_admin_action(monkeypatch):
    calls = {}
    class DummyDB:
        def collection(self, name):
            calls['collection'] = name
            class DummyCol:
                def add(self, data):
                    calls['add'] = data
            return DummyCol()
    utils_beheer_log.log_admin_action('type', 'user', {'x':1}, DummyDB())
    assert calls['collection'] == 'beheer_log'
    assert 'add' in calls
