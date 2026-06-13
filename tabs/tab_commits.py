"""
TAB COMMITS: Module om de laatste GitHub commits te tonen
"""
import streamlit as st
import subprocess
import pandas as pd

def get_git_commits(limit=100):
    """Haal de laatste git commits op via de command line."""
    try:
        # Gebruik git log om commits op te halen in een specifiek formaat
        # %h: short hash, %ad: author date, %an: author name, %s: subject
        cmd = ["git", "log", "-n", str(limit), "--pretty=format:%h|%ad|%an|%s", "--date=short"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        lines = result.stdout.strip().split("\n")
        commits = []
        for line in lines:
            if "|" in line:
                parts = line.split("|", 3)
                if len(parts) >= 4:
                    commits.append({
                        "Hash": parts[0],
                        "Datum": parts[1],
                        "Auteur": parts[2],
                        "Bericht": parts[3]
                    })
        return pd.DataFrame(commits)
    except Exception as e:
        st.error(f"Fout bij het ophalen van commits: {e}")
        return pd.DataFrame()

def clean_and_translate_commit(hash_val, message):
    """Clean, translate, and categorize commit messages to Dutch."""
    translations = {
        "486a5b1": "Samenvoegen van feature: ELO-herberekening uitstellen naar 23:00 uur",
        "2aafa83": "Samenvoegen van feature: ELO-herberekening uitstellen naar 23:00 uur (deel 1)",
        "c3afc1d": "Herstel: NameError in Google Sheets fallback-functie en trigger redeploy",
        "3ec7ebc": "Onderhoud: Redeploy getriggerd om Streamlit Cloud-cache te legen",
        "0330476": "Herstel: ELO-reset per seizoen geïmplementeerd en ELO van Brenda gecorrigeerd",
        "d6e90dc": "Herstel: Kolomnamen genormaliseerd en Google Sheets quota-verbruik geoptimaliseerd",
        "eeb932a": "Optimalisatie: Laden van gegevens en seizoensberekening geoptimaliseerd",
        "bfb1a09": "Herstel: IndentationError opgelost en Google Sheets optimalisatie voltooid",
        "c77c695": "Optimalisatie: Google Sheets verbindingen geoptimaliseerd en cache-versieverschillen opgelost",
        "8596678": "Test: Import-pad van tab_home bijgewerkt in de prestatietesten",
        "bcd83f6": "Refactoring: Overbodige tab-scripts verwijderd uit de hoofdmap",
        "881c3b8": "Refactoring: Tab-scripts verplaatst naar een aparte tabs/ map",
        "677f686": "Nieuw: Hardcoded SHEET_ID verplaatst naar omgevingsvariabelen voor betere beveiliging",
        "a0dfd2d": "Test: Integratietest-markering geregistreerd in pytest.ini",
        "6366ab9": "Refactoring: Constanten gebruikt voor seizoenslogica en gerichte cache-invalidatie geïmplementeerd",
        "e7a7319": "Refactoring: Ongebruikt database.json schema-bestand verwijderd",
        "9b83777": "Nieuw: Synchronisatielogica verbeterd met globale throttling en batch-updates voor back-ups",
        "93d3f65": "Nieuw: Verwijderingen en updates van wedstrijden en spelers gesynchroniseerd met Google Sheets back-up",
        "943bc39": "Nieuw: Batch-schrijven voor Google Sheets back-up geïmplementeerd ter verbetering van data-integriteit",
        "2787d91": "Optimalisatie: Seizoensgrenzen bijgewerkt naar 15-16 maart, prestatie-timing toegevoegd en tests bijgewerkt",
        "9ba8582": "Refactoring: Subtabs voor Inspectie en ELO-beheer verwijderd; inspectie verplaatst naar admin/inspectie.py en tests bijgewerkt",
        "e6ba84c": "Onderhoud: Versies van packages vastgezet (gepind) voor stabiele Cloud-deployments",
        "9add4d3": "Test: Test-commit voor configuratieverificatie",
        "4d20bbc": "Nieuw: Voorkeur voor st.secrets voor Firestore-inloggegevens en verbetering van fallback-meldingen",
        "4c48993": "Herstel: Unicode emoji encoding-fout opgelost in analytics subheader",
        "f045453": "Onderhoud: Dev Container-map toegevoegd",
        "a931827": "Samenvoegen: Wijzigingen van remote repository",
        "ac75cf0": "Onderhoud: Thema vastgezet op altijd light",
        "b3aaaec": "Test: Testnamen gecorrigeerd",
        "587de94": "Herstel: Bestandsnaam gecorrigeerd",
        "0cdc5bf": "Herstel: Bestandsnaam gecorrigeerd",
        "9cac667": "Refactoring: Tab-label hernoemd van Seizoenen naar Analytics",
        "49067ea": "Refactoring: tab_seizoenen hernoemd naar tab_analytics",
        "a68f330": "Herstel: Winpercentage als percentage weergegeven op startpagina; Beheer: seizoensverwijder-UI verwijderd",
        "ea50cb5": "Herstel: ELO-beheer verwijderd uit de app",
        "382bc4f": "Herstel: Offline modus aangepast en geoptimaliseerd",
        "0f93b49": "Onderhoud: FieldFilter gebruikt inplaats van positionele where() in add_match_and_update_elo",
        "f3f11b4": "Herstel: Fallback get_players zorgt voor ELO-rating door samenvoegen van laatste ELO-gegevens",
        "ffe2643": "Onderhoud: README bijgewerkt met offline CSV-modus en gebruik",
        "972080f": "Onderhoud: README bijgewerkt met offline CSV-modus en gebruik",
    }
    
    # Check by short hash first
    for short_hash, trans in translations.items():
        if hash_val.startswith(short_hash) or short_hash.startswith(hash_val):
            message = trans
            break
            
    message = message.strip()
    
    # Handle standard merge messages
    if message.startswith("Merge pull request") or message.startswith("Merge branch"):
        if "from atv22/" in message:
            branch = message.split("from atv22/")[-1]
            message = f"Samenvoegen: Aanpassingen van branch '{branch}' geïntegreerd"
        else:
            message = f"Samenvoegen: {message}"
            
    lower_msg = message.lower()
    
    # List of direct prefixes to normalize
    prefixes = [
        ("fix:", "Herstel:"),
        ("feat:", "Nieuw:"),
        ("perf:", "Optimalisatie:"),
        ("refactor:", "Refactoring:"),
        ("test:", "Test:"),
        ("chore:", "Onderhoud:"),
        ("debug:", "Debug:"),
        ("fix performance:", "Optimalisatie:"),
        ("optimaliseer sync logica:", "Optimalisatie:"),
        ("implementeer bi-directionele sync:", "Nieuw:"),
        ("optimaliseer alle visualisaties:", "Optimalisatie:"),
        ("fix analytics:", "Herstel:"),
        ("codebase opgeschoond:", "Onderhoud:"),
        ("optimaliseer snelheid:", "Optimalisatie:"),
        ("verbeter diagnostics:", "Nieuw:"),
        ("forceer cache refresh:", "Onderhoud:"),
        ("herstel:", "Herstel:"),
        ("hetstel:", "Herstel:"),
        ("verplaats:", "Refactoring:"),
        ("verwijder:", "Refactoring:"),
        ("update:", "Nieuw:"),
    ]
    
    matched_prefix = None
    for pref, nl_pref in prefixes:
        if lower_msg.startswith(pref):
            content = message[len(pref):].strip()
            if content:
                content = content[0].upper() + content[1:]
            matched_prefix = nl_pref
            break
            
    if matched_prefix:
        message = f"{matched_prefix} {content}"
    else:
        # Substring replacements to keep the actual content of the message
        found_custom = False
        for eng_term, nl_term in [
            ("fix google sheets fallback:", "Herstel: Google Sheets fallback:"),
            ("verbeter google sheets fallback:", "Optimalisatie: Google Sheets fallback verbeterd:"),
            ("maak gspread import optioneel:", "Optimalisatie: gspread-import optioneel gemaakt:"),
            ("herstel get_beheer_log:", "Herstel: get_beheer_log:"),
            ("migreer csv-backup naar google sheets:", "Nieuw: CSV-back-up gemigreerd naar Google Sheets:"),
            ("refactor analytics:", "Refactoring: Analytics:"),
            ("schoon admin map op:", "Onderhoud: Admin map opgeschoond:"),
        ]:
            if lower_msg.startswith(eng_term):
                content = message[len(eng_term):].strip()
                if content:
                    content = content[0].upper() + content[1:]
                message = f"{nl_term} {content}".strip()
                found_custom = True
                break
                
        if not found_custom:
            if lower_msg.startswith("testspeler") or lower_msg.startswith("filter testspeler"):
                message = f"Refactoring: {message[0].upper() + message[1:]}"
            elif lower_msg.startswith("uitslagentabel-caching"):
                message = f"Herstel: {message[0].upper() + message[1:]}"
            elif lower_msg.startswith("controle op dubbele"):
                message = f"Nieuw: {message[0].upper() + message[1:]}"
            elif lower_msg.startswith("functie toegevoegd"):
                message = f"Nieuw: {message[0].upper() + message[1:]}"
            elif lower_msg.startswith("kolomvolgorde"):
                message = f"Herstel: {message[0].upper() + message[1:]}"
            elif lower_msg.startswith("optimaliseer"):
                message = f"Optimalisatie: {message[0].upper() + message[1:]}"
            elif lower_msg.startswith("implementeer"):
                message = f"Nieuw: {message[0].upper() + message[1:]}"
            elif lower_msg.startswith("schoon"):
                message = f"Onderhoud: {message[0].upper() + message[1:]}"
            elif lower_msg.startswith("debughast") or lower_msg.startswith("debug:"):
                message = f"Debug: {message[0].upper() + message[1:]}"
            
    # Assign category based on the final message prefix
    category = "Overig"
    if message.startswith("Herstel:"):
        category = "Herstel"
    elif message.startswith("Nieuw:"):
        category = "Nieuw"
    elif message.startswith("Optimalisatie:"):
        category = "Optimalisatie"
    elif message.startswith("Refactoring:"):
        category = "Refactoring"
    elif message.startswith("Onderhoud:"):
        category = "Onderhoud"
    elif message.startswith("Test:"):
        category = "Test"
    elif message.startswith("Debug:"):
        category = "Debug"
    elif message.startswith("Samenvoegen:"):
        category = "Samenvoegen"
    elif message.startswith("Samenvoegen"):
        category = "Samenvoegen"
        
    return message, category

def render_commits_tab():
    """Render de Commits tab met een premium visualisatie en filters."""
    st.header("📜 Wijzigingshistorie")
    st.write("Een overzicht van de laatste aanpassingen en updates van de tafelvoetbal-app.")

    # Haal de commits op
    with st.spinner("Commits ophalen..."):
        commits_df = get_git_commits(limit=100)

    if commits_df.empty:
        st.info("Geen commit-historie gevonden of Git is niet beschikbaar.")
        return

    # Pas opschoning en vertaling toe
    cleaned_data = []
    for _, row in commits_df.iterrows():
        cleaned_msg, category = clean_and_translate_commit(row["Hash"], row["Bericht"])
        cleaned_data.append({
            "Hash": row["Hash"],
            "Datum": row["Datum"],
            "Auteur": row["Auteur"],
            "Origineel": row["Bericht"],
            "Bericht": cleaned_msg,
            "Categorie": category
        })
    df = pd.DataFrame(cleaned_data)

    # Categories filter met counts
    category_counts = df["Categorie"].value_counts().to_dict()
    
    category_options = ["Alles (%d)" % len(df)]
    category_map = {"Alles (%d)" % len(df): "Alles"}
    
    for cat in sorted(list(df["Categorie"].unique())):
        label = f"{cat} ({category_counts.get(cat, 0)})"
        category_options.append(label)
        category_map[label] = cat

    # Search filter and category filter side-by-side
    col1, col2 = st.columns([1, 2])
    with col1:
        selected_option = st.selectbox("Filter op categorie:", category_options)
        selected_category = category_map[selected_option]
    with col2:
        search_query = st.text_input("🔍 Zoek in commit-berichten:", "").strip().lower()

    # Filter data
    filtered_df = df.copy()
    if selected_category != "Alles":
        filtered_df = filtered_df[filtered_df["Categorie"] == selected_category]
    if search_query:
        filtered_df = filtered_df[
            filtered_df["Bericht"].str.lower().str.contains(search_query) | 
            filtered_df["Hash"].str.lower().str.contains(search_query) |
            filtered_df["Auteur"].str.lower().str.contains(search_query)
        ]

    # CSS for premium commit cards
    st.markdown("""
        <style>
        .commit-card {
            background-color: var(--secondary-background-color);
            border: 1px solid rgba(128, 128, 128, 0.15);
            border-radius: 10px;
            padding: 14px 18px;
            margin-bottom: 12px;
            transition: all 0.2s ease-in-out;
        }
        .commit-card:hover {
            transform: translateY(-2px);
            border-color: var(--primary-color);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        .commit-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .commit-badge {
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }
        .badge-nieuw { background-color: rgba(46, 204, 113, 0.15); color: #2ecc71; border: 1px solid rgba(46, 204, 113, 0.25); }
        .badge-herstel { background-color: rgba(231, 76, 60, 0.15); color: #e74c3c; border: 1px solid rgba(231, 76, 60, 0.25); }
        .badge-optimalisatie { background-color: rgba(52, 152, 219, 0.15); color: #3498db; border: 1px solid rgba(52, 152, 219, 0.25); }
        .badge-refactoring { background-color: rgba(155, 89, 182, 0.15); color: #9b59b6; border: 1px solid rgba(155, 89, 182, 0.25); }
        .badge-onderhoud { background-color: rgba(149, 165, 166, 0.15); color: #95a5a6; border: 1px solid rgba(149, 165, 166, 0.25); }
        .badge-test { background-color: rgba(26, 188, 156, 0.15); color: #1abc9c; border: 1px solid rgba(26, 188, 156, 0.25); }
        .badge-debug { background-color: rgba(241, 196, 15, 0.15); color: #f1c40f; border: 1px solid rgba(241, 196, 15, 0.25); }
        .badge-samenvoegen { background-color: rgba(230, 126, 34, 0.15); color: #e67e22; border: 1px solid rgba(230, 126, 34, 0.25); }
        .badge-overig { background-color: rgba(127, 140, 141, 0.15); color: #95a5a6; border: 1px solid rgba(127, 140, 141, 0.25); }
        
        a.commit-hash {
            text-decoration: none;
            font-family: monospace;
            font-size: 0.8rem;
            color: var(--text-color);
            opacity: 0.6;
            background: rgba(128, 128, 128, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
            transition: opacity 0.2s, background-color 0.2s;
        }
        a.commit-hash:hover {
            opacity: 1.0;
            background: rgba(128, 128, 128, 0.25);
            color: var(--primary-color);
        }
        .commit-message {
            font-size: 0.95rem;
            line-height: 1.4;
            color: var(--text-color);
            margin: 6px 0;
            font-weight: 500;
        }
        .commit-footer {
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            color: var(--text-color);
            opacity: 0.55;
            margin-top: 8px;
            border-top: 1px solid rgba(128, 128, 128, 0.08);
            padding-top: 6px;
        }
        </style>
    """, unsafe_allow_html=True)

    if filtered_df.empty:
        st.warning("Geen commits gevonden die voldoen aan de filters.")
        return

    # Render commits als kaarten
    for _, row in filtered_df.iterrows():
        badge_class = f"badge-{row['Categorie'].lower()}"
        github_url = f"https://github.com/atv22/tafelvoetbal/commit/{row['Hash']}"
        
        st.markdown(f"""
            <div class="commit-card">
                <div class="commit-meta">
                    <span class="commit-badge {badge_class}">{row['Categorie']}</span>
                    <a href="{github_url}" target="_blank" class="commit-hash" title="Bekijk commit op GitHub">#{row['Hash']}</a>
                </div>
                <div class="commit-message">{row['Bericht']}</div>
                <div class="commit-footer">
                    <span>👤 {row['Auteur']}</span>
                    <span>📅 {row['Datum']}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
