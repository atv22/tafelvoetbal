import os
import sys
import pandas as pd
import unicodedata

# Voeg de root directory toe aan path voor firestore_service
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import firestore_service as db

def normalize_name(name):
    if not isinstance(name, str): return ""
    return "".join(c for c in unicodedata.normalize('NFKD', name) if not unicodedata.combining(c)).lower().strip()

def full_audit():
    print("--- START VOLLEDIGE SPELER AUDIT ---")
    
    # 1. Verzamelen uit Firestore
    print("\n[1/2] Data ophalen uit Firestore...")
    fs_players = set(db.get_players()['speler_naam'].tolist())
    
    matches = db.get_matches()
    fs_match_players = set()
    for col in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
        if col in matches.columns:
            fs_match_players.update(matches[col].dropna().unique())
            
    elo_logs = db.get_elo_logs()
    fs_elo_players = set(elo_logs['speler_naam'].unique()) if not elo_logs.empty else set()
    
    # 2. Verzamelen uit Back-up CSV
    print("[2/2] Data ophalen uit back-up CSV's...")
    csv_players = set()
    try:
        csv_p = pd.read_csv('csv/read/spelers.csv')
        csv_players.update(csv_p['speler_naam'].unique())
    except: pass
    
    csv_match_players = set()
    try:
        csv_m = pd.read_csv('csv/read/uitslag.csv')
        for col in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
            csv_match_players.update(csv_m[col].dropna().unique())
    except: pass

    # Combineer alles
    all_names = fs_players | fs_match_players | fs_elo_players | csv_players | csv_match_players
    all_names = {n for n in all_names if n and str(n).lower() not in ['niemandin', 'niemanduit', 'niemand', 'none', 'nan']}
    
    print(f"\nTotaal unieke spelersnamen gevonden: {len(all_names)}")

    # 3. Analyse: Dubbelgangers en Encoding
    print("\n--- ANALYSE RESULTATEN ---")
    
    # Check encoding fouten
    encoding_issues = [n for n in all_names if '' in n or '?' in n]
    if encoding_issues:
        print(f"\n⚠️ Mogelijke encoding fouten gevonden ({len(encoding_issues)}):")
        for n in encoding_issues:
            print(f"  - {n}")
    
    # Check op gelijkenis (case-insensitive + normalisatie)
    normalized_map = {}
    for name in sorted(all_names):
        norm = normalize_name(name)
        if norm not in normalized_map:
            normalized_map[norm] = []
        normalized_map[norm].append(name)
    
    potential_duplicates = {k: v for k, v in normalized_map.items() if len(v) > 1}
    if potential_duplicates:
        print(f"\n⚠️ Potentiële dubbele spelers gevonden ({len(potential_duplicates)} groepen):")
        for norm, names in potential_duplicates.items():
            print(f"  - Groep [{norm}]: {names}")

    # Check spelers in matches maar niet in de 'players' tabel
    missing_in_registry = (fs_match_players | fs_elo_players) - fs_players
    missing_in_registry = {n for n in missing_in_registry if n and str(n).lower() not in ['niemandin', 'niemanduit', 'niemand', 'none', 'nan']}
    if missing_in_registry:
        print(f"\n⚠️ Spelers gevonden in historie maar NIET in de spelerslijst ({len(missing_in_registry)}):")
        for n in sorted(missing_in_registry):
            print(f"  - {n}")

    print("\n--- EINDE AUDIT ---")

if __name__ == "__main__":
    full_audit()
