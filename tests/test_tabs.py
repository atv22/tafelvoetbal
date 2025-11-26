import streamlit as st
import pytest
from streamlit.testing.v1 import AppTest

# Test alle tabs van de tafelvoetbal app op foutmeldingen
def test_all_tabs_run_without_errors():
    app = AppTest.from_file("app.py")
    app.run()
    # Controleer of alle tab-namen zichtbaar zijn
    tab_names = ["Home", "Spelers", "Seizoenen", "Data", "Verzoeken", "Colofon"]
    for tab in tab_names:
        assert app.get_by_text(tab).exists(), f"Tab '{tab}' niet gevonden"
    # Klik en controleer elke tab op errors
    for tab in tab_names:
        app.get_by_text(tab).click()
        # Controleer op Streamlit error messages
        assert not app.get_by_text("Fout").exists(), f"Foutmelding gevonden in tab '{tab}'"
        assert not app.get_by_text("KeyError").exists(), f"KeyError gevonden in tab '{tab}'"
        assert not app.get_by_text("Exception").exists(), f"Exception gevonden in tab '{tab}'"
        assert not app.get_by_text("Traceback").exists(), f"Traceback gevonden in tab '{tab}'"

if __name__ == "__main__":
    pytest.main([__file__])
