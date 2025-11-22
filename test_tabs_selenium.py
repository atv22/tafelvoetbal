import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys

# Pas deze URL aan als je Streamlit op een andere poort draait
STREAMLIT_URL = "http://localhost:8501/"

TAB_NAMES = [
    "🏠 Home",
    "📝 Invullen",
    "👥 Spelers",
    "📅 Seizoenen",
    "📊 Ruwe Data",
    "⚙️ Beheer",
    "💬 Verzoeken",
    "ℹ️ Colofon"
]

@pytest.fixture(scope="module")
def browser():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

def test_all_tabs_no_errors(browser):
    browser.get(STREAMLIT_URL)
    # Wacht tot de app geladen is
    time.sleep(5)
    for tab in TAB_NAMES:
        # Zoek de tab-knop en klik
        tab_buttons = browser.find_elements(By.XPATH, f"//button[.='{tab}']")
        if not tab_buttons:
            # Soms zijn tabs als links (a) ipv buttons
            tab_buttons = browser.find_elements(By.XPATH, f"//a[.='{tab}']")
        assert tab_buttons, f"Tab '{tab}' niet gevonden"
        tab_buttons[0].click()
        time.sleep(2)
        # Controleer op foutmeldingen in de pagina
        page_source = browser.page_source
        assert "Fout" not in page_source, f"Foutmelding gevonden in tab '{tab}'"
        assert "KeyError" not in page_source, f"KeyError gevonden in tab '{tab}'"
        assert "Exception" not in page_source, f"Exception gevonden in tab '{tab}'"
        assert "Traceback" not in page_source, f"Traceback gevonden in tab '{tab}'"

if __name__ == "__main__":
    pytest.main([__file__])
