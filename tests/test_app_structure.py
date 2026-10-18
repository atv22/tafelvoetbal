
import importlib
import pytest
import sys
import os

# Voeg de root van het project toe aan sys.path zodat imports werken
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Test of alle hoofd-tab modules en de app entrypoint correct importeren en de juiste functies bevatten
MODULES = [
    "app",
    "tabs.tab_home",
    "tabs.tab_invullen",
    "tabs.tab_spelers",
    "tabs.tab_analytics",
    "tabs.tab_data",
    "tabs.tab_beheer",
    "tabs.tab_verzoeken",
    "tabs.tab_commits",
    "tabs.tab_logging",
    "tabs.tab_colofon",
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
        "🏠 Home", "📝 Invullen", "👥 Spelers", "📈 Analytics",
        "📊 Ruwe Data", "💬 Verzoeken", "📜 Commits", "🔍 Logging",
        "ℹ️ Colofon", "⚙️ Beheer"
    ]
    app_path = os.path.join(os.path.dirname(__file__), "..", "app.py")
    with open(app_path, encoding="utf-8") as f:
        content = f.read()
    for tab in expected_tabs:
        assert tab in content, f"Tab '{tab}' niet gevonden in app.py"

def test_admin_subtabs():
    beheer_path = os.path.join(os.path.dirname(__file__), "..", "tabs", "tab_beheer.py")
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

def test_expected_schema():
    import firestore_service as db
    schema = db.expected_schema()
    assert set(schema.keys()) == {"spelers", "uitslag", "elo", "requests"}

def test_colofon_and_tutorial_functions():
    from tabs import tab_colofon
    assert hasattr(tab_colofon, "render_colofon_tab"), "render_colofon_tab ontbreekt in tab_colofon"
    assert hasattr(tab_colofon, "render_quick_tutorial"), "render_quick_tutorial ontbreekt in tab_colofon"
    assert callable(tab_colofon.render_colofon_tab)
    assert callable(tab_colofon.render_quick_tutorial)

    colofon_path = os.path.join(os.path.dirname(__file__), "..", "tabs", "tab_colofon.py")
    with open(colofon_path, encoding="utf-8") as f:
        content = f.read()
    expected_doc_subtabs = [
        "🚀 Snelstart (Tutorial)",
        "📖 Handleiding & Spelregels",
        "🧮 ELO & Seizoenen",
        "🏆 Over deze App (Colofon)",
    ]
    for subtab in expected_doc_subtabs:
        assert subtab in content, f"Documentatie-subtab '{subtab}' niet gevonden in tab_colofon.py"

def test_open_source_documentation_files():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    required_files = ["README.md", "LICENSE", "CONTRIBUTING.md", os.path.join("admin", "README.md")]
    for rel_path in required_files:
        full_path = os.path.join(root_dir, rel_path)
        assert os.path.exists(full_path), f"Vereist documentatiebestand '{rel_path}' ontbreekt"
        with open(full_path, encoding="utf-8") as f:
            text = f.read().strip()
        assert len(text) > 200, f"Documentatiebestand '{rel_path}' lijkt leeg of onvolledig"


