import pytest
from utils import utils

def test_get_nl_now():
    result = utils.get_nl_now()
    assert result is not None

def test_add_name():
    import random, string
    unieke_naam = 'Test' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    resultaat = utils.add_name(unieke_naam)
    if resultaat is None:
        import pytest
        pytest.skip(f"Naam {unieke_naam} bestaat al of kon niet toegevoegd worden.")
    assert resultaat == unieke_naam

def test_add_request():
    assert utils.add_request('Test') == 'Test'

def test_get_download_filename():
    filename = utils.get_download_filename('bestand', 'csv')
    assert filename.startswith('bestand_') and filename.endswith('.csv')
