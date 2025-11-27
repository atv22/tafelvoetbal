import pytest
from utils import utils

def test_get_nl_now():
    result = utils.get_nl_now()
    assert result is not None

def test_add_name():
    assert utils.add_name('Jan') == 'Jan'

def test_add_request():
    assert utils.add_request('Test') == 'Test'

def test_get_download_filename():
    filename = utils.get_download_filename('bestand', 'csv')
    assert filename.startswith('bestand_') and filename.endswith('.csv')
