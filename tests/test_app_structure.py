
import importlib
import pytest
import sys
import os

# Voeg de root van het project toe aan sys.path zodat imports werken
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Test of alle hoofd-tab modules en de app entrypoint correct importeren en de juiste functies bevatten
MODULES = [
    "app",
    "tab_home",
    "tab_invullen",
    "tab_spelers",
    "tab_analytics",
    "tab_data",
    "tab_beheer",
    "tab_verzoeken",
    "tab_colofon",
]

@pytest.mark.parametrize("module_name", MODULES)
def test_module_imports(module_name):
    try:
        importlib.import_module(module_name)
    except Exception as e:
        pytest.fail(f"Module {module_name} kon niet worden geïmporteerd: {e}")

def test_app_tabs():
    # Controleer of de tab-namen in de app overeenkomen met verwachting
    expected_tabs = [
        "🏠 Home", "📝 Invullen", "👥 Spelers", "� Analytics",
        "📊 Ruwe Data", "⚙️ Beheer", "💬 Verzoeken", "ℹ️ Colofon"
    ]
    app_path = os.path.join(os.path.dirname(__file__), "..", "app.py")
    with open(app_path, encoding="utf-8") as f:
        content = f.read()
    for tab in expected_tabs:
        assert tab in content, f"Tab '{tab}' niet gevonden in app.py"

def test_admin_subtabs():
    beheer_path = os.path.join(os.path.dirname(__file__), "..", "tab_beheer.py")
    with open(beheer_path, encoding="utf-8") as f:
        content = f.read()
    # Hoofd subtabs
    expected_subtabs = [
        "🗑️ Verwijderen", "✏️ Bewerken", "📁 Upload"
    ]
    for subtab in expected_subtabs:
        assert subtab in content, f"Subtab '{subtab}' niet gevonden in tab_beheer.py"
    # Upload subtabs
    expected_upload_subtabs = [
        "🏆 Wedstrijden", "👥 Spelers", "📅 Seizoenen"
    ]
    for subtab in expected_upload_subtabs:
        assert subtab in content, f"Upload subtab '{subtab}' niet gevonden in tab_beheer.py"
