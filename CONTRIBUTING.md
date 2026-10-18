# 🤝 Bijdragen aan de Tafelvoetbal Competitie App (Contributing)

Bedankt voor je interesse om bij te dragen aan de **Tafelvoetbal Competitie App**! Of je nu een bug wilt melden, een nieuwe visualisatie wilt bouwen, of de documentatie wilt verbeteren: elke bijdrage is welkom.

---

## 💬 Ideeën & Bugs Melden (Zonder Code)

Speel je mee in de competitie en heb je een goed idee of zie je een foutje?
- Gebruik direct in de app het tabblad **💬 Verzoeken** om een suggestie of bugmelding achter te laten (maximaal 250 tekens).
- Of open een **Issue** op GitHub met een duidelijke beschrijving van het probleem of je feature-verzoek.

---

## 💻 Zelf Code Bijdragen (Ontwikkelaars)

### 1. Ontwikkelomgeving Opzetten

1. **Fork & Clone** de repository:
   ```bash
   git clone https://github.com/atv22/tafelvoetbal.git
   cd tafelvoetbal
   ```
2. **Maak een virtuele omgeving (`.venv`)** aan en installeer de dependencies:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. **Database configuratie:**
   - Plaats een geldig `firestore-key.json` bestand in de root, óf configureer `.streamlit/secrets.toml`.
   - **Let op:** Commit **nooit** `firestore-key.json`, `.streamlit/secrets.toml` of andere API-sleutels naar Git!

---

### 2. Architectuur & Code-richtlijnen

- **Modulaire Tabbladen (`tabs/`):**
  Elke tab in de Streamlit-app heeft zijn eigen bestand in de map `tabs/` (bijv. `tabs/tab_home.py`, `tabs/tab_invullen.py`). Houd `app.py` zo slank mogelijk en plaats tab-specifieke logica in het bijbehorende tab-bestand.
- **Database & Quota-bewustzijn (`firestore_service.py`):**
  Google Cloud Firestore heeft dagelijkse gratis limieten (reads/writes).
  - Gebruik voor het lezen van data altijd de gecachte functies uit `firestore_service.py` (`get_players()`, `get_matches()`, `get_elo_logs()`, `get_seasons()`, `get_requests()`).
  - Roep na schrijfacties `clear_all_caches(...)` aan met alléén de relevante vlaggen (`only_matches=True`, `only_players=True`, etc.) zodat niet onnodig alle caches worden gewist.
- **Vectorisatie boven Loops (`analytics.py`):**
  Gebruik voor statistieken en ranglijsten gevectoriseerde Pandas-operaties (`get_vectorized_player_stats`) in plaats van trage `iterrows()` loops.
- **Taal & Stijl:**
  - De gebruikersinterface (UI) en documentatie zijn in het **Nederlands**.
  - Volg **PEP 8** voor Python-code en voeg duidelijke docstrings toe aan nieuwe functies.

---

### 3. Testen vóór een Pull Request

Wijzigingen mogen bestaande functionaliteit of de ELO-berekening niet breken. Voer altijd de testsuite uit voordat je een Pull Request indient:

```powershell
# Voer de snelle unit- en structuurtests uit:
pytest -m "not integration"
```

Controleer met name:
- `tests/test_app_structure.py`: Controleert of alle modules foutloos importeren en alle verwachte tabs en subtabs aanwezig zijn.
- `tests/test_utils_new_elo.py` & `tests/test_elo.py`: Verifiëren de wiskundige juistheid van de 2v2 ELO-formule en klinker-bonussen.
- `tests/test_season_utils.py`: Controleert de Prinsjesdag- en 15-maart seizoensgrenzen.
- `tests/test_deferred_recalc.py`: Controleert de uitgestelde 23:00-uur ELO-herberekening.

---

### 4. Pull Request Indienen

1. Maak een nieuwe branch aan voor je feature of bugfix:
   ```bash
   git checkout -b feat/mijn-nieuwe-feature
   ```
2. Gebruik duidelijke commit-berichten met een prefix (deze worden automatisch netjes gecategoriseerd in het tabblad **📜 Commits**):
   - `feat:` of `Nieuw:` voor nieuwe functionaliteit
   - `fix:` of `Herstel:` voor bugfixes
   - `perf:` of `Optimalisatie:` voor snelheids- of quota-verbeteringen
   - `refactor:` of `Refactoring:` voor code-opschoning
   - `docs:` of `Onderhoud:` voor documentatie en onderhoud
   - `test:` of `Test:` voor het toevoegen of aanpassen van tests
3. Push je branch en open een **Pull Request** op GitHub.
