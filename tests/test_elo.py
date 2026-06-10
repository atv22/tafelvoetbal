import sys
import os
# Voeg de hoofdmap toe aan sys.path zodat imports werken
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# test_elo.py
"""
Combineert ELO-checks, functionele tests en seizoensoverzichten voor de tafelvoetbal-app.
"""
import pandas as pd
import firestore_service as db
from firestore_service import normalize_timestamp_series
import time

def check_elo_per_season():
    """
    Controleer na ELO-herberekening of alle spelers die in een seizoen spelen, ook daadwerkelijk een ELO krijgen in elk seizoen waarin ze meedoen.
    Rapporteer ontbrekende ELO's.
    """
    seasons_df = db.get_seasons()
    matches_df = db.get_matches()
    players_df = db.get_players()
    missing_elo = []
    for _, season in seasons_df.iterrows():
        start = pd.to_datetime(season['startdatum'])
        end = pd.to_datetime(season['einddatum'])
        season_matches = matches_df[(matches_df['timestamp'] >= start) & (matches_df['timestamp'] <= end)]
        # Spelers die in dit seizoen gespeeld hebben
        season_players = set()
        for col in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
            if col in season_matches.columns:
                season_players.update(season_matches[col].dropna().astype(str).tolist())
        for speler in season_players:
            elo_hist = db.get_elo_history(_ttl=60, speler_naam=speler)
            if elo_hist.empty:
                missing_elo.append((speler, season['seizoen_naam']))
            else:
                # Check of er een ELO entry is binnen de seizoensgrenzen
                elo_hist['timestamp'] = pd.to_datetime(elo_hist['timestamp'], errors='coerce')
                elo_hist['timestamp'] = normalize_timestamp_series(elo_hist['timestamp'])
                in_season = elo_hist[(elo_hist['timestamp'] >= start) & (elo_hist['timestamp'] <= end)]
                if in_season.empty:
                    missing_elo.append((speler, season['seizoen_naam']))
    if missing_elo:
        print("[CHECK] Spelers zonder ELO in seizoen:")
        for speler, seizoen in missing_elo:
            print(f"  {speler} in {seizoen}")
    else:
        print("[CHECK] Alle spelers hebben een ELO in elk seizoen waarin ze speelden.")

def elo_overview_per_season():
    """
    Genereer een overzicht van spelers die in meerdere seizoenen actief zijn, met hun ELO-geschiedenis per seizoen.
    Toon per speler in welke seizoenen ze actief waren en hun ELO aan het begin en eind van elk seizoen.
    """
    seasons_df = db.get_seasons()
    matches_df = db.get_matches()
    players_df = db.get_players()
    overview = []
    for speler in players_df['speler_naam']:
        speler_info = {'speler_naam': speler, 'seizoenen': []}
        elo_hist = db.get_elo_history(_ttl=60, speler_naam=speler)
        if elo_hist.empty:
            continue
        elo_hist['timestamp'] = pd.to_datetime(elo_hist['timestamp'], errors='coerce')
        elo_hist['timestamp'] = normalize_timestamp_series(elo_hist['timestamp'])
        for _, season in seasons_df.iterrows():
            start = pd.to_datetime(season['startdatum'])
            end = pd.to_datetime(season['einddatum'])
            in_season = elo_hist[(elo_hist['timestamp'] >= start) & (elo_hist['timestamp'] <= end)]
            if not in_season.empty:
                elo_start = in_season.iloc[0]['rating']
                elo_end = in_season.iloc[-1]['rating']
                speler_info['seizoenen'].append({
                    'seizoen_naam': season['seizoen_naam'],
                    'elo_start': elo_start,
                    'elo_end': elo_end,
                    'aantal_entries': len(in_season)
                })
        if len(speler_info['seizoenen']) > 1:
            overview.append(speler_info)
    for speler in overview:
        print(f"Speler: {speler['speler_naam']}")
        for s in speler['seizoenen']:
            print(f"  {s['seizoen_naam']}: start={s['elo_start']}, eind={s['elo_end']} (entries: {s['aantal_entries']})")
        print()
    if not overview:
        print("Geen spelers met meerdere seizoenen gevonden.")

# TEST CONFIGURATIE
test_players = {
    "TestThuisA": 1000,
    "TestThuisB": 1000,
    "TestUitA": 1000,
    "TestUitB": 1000,
}
player_ids_to_cleanup = []

def cleanup_test_players():
    print("\n Vooraf opruimen...")
    try:
        df_players = db.get_players()
        if df_players.empty:
            print(" -> Geen spelers gevonden om op te ruimen.")
            return
        deleted_count = 0
        for index, player in df_players.iterrows():
            name = str(player.get('speler_naam', ''))
            if name.startswith("TestSpeler") or name in test_players:
                if db.delete_player_by_id(player['speler_id']):
                    deleted_count += 1
        if deleted_count > 0:
            print(f" -> {deleted_count} overgebleven testspelers en hun ELO-geschiedenis verwijderd.")
        else:
            print(" -> Geen overgebleven testspelers gevonden.")
    except Exception as e:
        print(f"Fout tijdens vooraf opruimen: {e}")

def run_elo_test():
    cleanup_test_players()
    time.sleep(3)
    print("\nSTART TEST")
    try:
        print("\n Spelers toevoegen...")
        for name, elo in test_players.items():
            result = db.add_player(name, elo)
            assert result == "Success", f"Kon speler {name} niet toevoegen. Resultaat: {result}"
        print(" -> SUCCES: Alle testspelers en hun initiële ELO succesvol toegevoegd.")
        time.sleep(2)
        print("\n Spelers ophalen en verifiëren...")
        df_players = db.get_players()
        assert not df_players.empty, "DataFrame met spelers is leeg."
        assert len(df_players) >= len(test_players), "Niet alle spelers zijn opgehaald."
        player_map = {row['speler_naam']: row for index, row in df_players.iterrows()}
        for name, elo in test_players.items():
            assert name in player_map, f"Testspeler {name} niet gevonden in database."
            assert player_map[name]['rating'] == elo, f"ELO voor {name} is incorrect."
            player_ids_to_cleanup.append(player_map[name]['speler_id'])
        print(" -> SUCCES: Alle testspelers succesvol opgehaald en geverifieerd.")
        print("\n Wedstrijd toevoegen en ELO-update controleren...")
        match_data = {
            'thuis_1': "TestThuisA", 'thuis_2': "TestUitA",
            'uit_1': "TestThuisB", 'uit_2': "TestUitB",
            'thuis_score': 10, 'uit_score': 5,
            'klinkers_thuis_1': 1, 'klinkers_thuis_2': 0,
            'klinkers_uit_1': 0, 'klinkers_uit_2': 2,
        }
        elo_updates = [
            ("TestThuisA", 1016), ("TestUitA", 1016),
            ("TestThuisB", 984), ("TestUitB", 984)
        ]
        success = db.add_match_and_update_elo(match_data, elo_updates)
        assert success, "Toevoegen van wedstrijd en loggen van ELO is mislukt."
        print(" -> SUCCES: Wedstrijd en nieuwe ELO-ratings succesvol gelogd.")
        time.sleep(2)
        df_players_after = db.get_players()
        player_map_after = {row['speler_naam']: row for index, row in df_players_after.iterrows()}
        assert player_map_after["TestThuisA"]['rating'] == 1016
        assert player_map_after["TestUitA"]['rating'] == 1016
        assert player_map_after["TestThuisB"]['rating'] == 984
        assert player_map_after["TestUitB"]['rating'] == 984

        # Controleer of de ELO-berekening in de database overeenkomt met de berekening in de code
        print("\nControleren of ELO-berekening overeenkomt met de code...")
        from utils.utils_new_elo import calculate_new_elo
        # Bouw all_ELO_ratings dict op basis van initiële ratings
        all_ELO_ratings = {name: [elo] for name, elo in test_players.items()}
        # Simuleer de testwedstrijd
        test_match = {
            "Thuis_1": "TestThuisA",
            "Thuis_2": "TestUitA",
            "Uit_1": "TestThuisB",
            "Uit_2": "TestUitB",
            "Thuis_score": 10,
            "Uit_score": 5
        }
        calculated = calculate_new_elo(test_match, all_ELO_ratings)
        # Haal ELO's uit de database/log
        db_elos = {row['speler_naam']: row['rating'] for row in df_players_after.to_dict('records') if row['speler_naam'] in test_players}
        for _, row in calculated.iterrows():
            speler = row['Speler']
            expected = round(row['ELO'], 0)
            actual = db_elos.get(speler)
            assert actual == expected, f"ELO voor {speler} klopt niet: verwacht {expected}, database {actual}"
        print(" -> SUCCES: ELO-berekening in database komt overeen met de code.")

        # Controle op dubbele ELO-entries per speler per wedstrijd
        print("\nControleren op dubbele ELO-entries per speler per wedstrijd...")
        elo_histories = []
        for name in test_players.keys():
            elo_hist = db.get_elo_history(_ttl=60, speler_naam=name)
            if not elo_hist.empty and 'match_id' in elo_hist.columns:
                elo_histories.append(elo_hist[['speler_naam', 'match_id']])
        if elo_histories:
            all_elo = pd.concat(elo_histories, ignore_index=True)
            dups = all_elo.duplicated(subset=['speler_naam', 'match_id'], keep=False)
            if dups.any():
                dup_rows = all_elo[dups]
                print("\n!!! FOUT: Dubbele ELO-entries gevonden per speler per wedstrijd:")
                print(dup_rows)
                raise AssertionError("Dubbele ELO-entries per speler per wedstrijd gevonden!")
            else:
                print(" -> SUCCES: Geen dubbele ELO-entries per speler per wedstrijd gevonden.")
        else:
            print(" -> Geen ELO-geschiedenis gevonden voor testspelers.")
    except AssertionError as e:
        print(f"\n!!! TEST MISLUKT: {e}!!!")
    finally:
        print("\n Testdata opruimen...")
        if not player_ids_to_cleanup:
            print(" -> Geen spelers om op te ruimen.")
        else:
            deleted_count = 0
            for player_id in player_ids_to_cleanup:
                if db.delete_player_by_id(player_id):
                    deleted_count += 1
            print(f" -> SUCCES: {deleted_count} van de {len(player_ids_to_cleanup)} testspelers (en hun ELO-geschiedenis) verwijderd.")
    print("\nEINDE TEST")


# === PYTEST TEST: invoeren van een nieuwe uitslag en ELO-controle ===

import pytest


# --- Pytest fixture voor testspelers setup en cleanup ---
@pytest.fixture
def testspelers_fixture():
    """
    Fixture die testspelers toevoegt vóór de test en altijd opruimt na afloop, ook bij failures.
    Geeft een dict met spelernaam -> speler_id terug.
    """
    cleanup_test_players()
    import time
    time.sleep(2)
    speler_ids = {}
    # Voeg testspelers toe
    for name, elo in test_players.items():
        result = db.add_player(name, elo)
        assert result == "Success", f"Kon speler {name} niet toevoegen. Resultaat: {result}"
    time.sleep(2)
    df_players = db.get_players()
    assert not df_players.empty, "DataFrame met spelers is leeg."
    player_map = {row['speler_naam']: row for index, row in df_players.iterrows()}
    for name, elo in test_players.items():
        assert name in player_map, f"Testspeler {name} niet gevonden in database."
        assert player_map[name]['rating'] == elo, f"ELO voor {name} is incorrect."
        speler_ids[name] = player_map[name]['speler_id']
    yield speler_ids
    # Cleanup na test, altijd uitvoeren
    for player_id in speler_ids.values():
        db.delete_player_by_id(player_id)
    player_ids_to_cleanup.clear()


@pytest.mark.integration
def test_invoeren_nieuwe_uitslag_en_elo(testspelers_fixture):
    """
    Test het invoeren van een nieuwe uitslag en controleer of de ELO en andere zaken correct worden aangepast.
    """
    speler_ids = testspelers_fixture

    # Voeg een wedstrijd toe en controleer ELO-update
    match_data = {
        'thuis_1': "TestThuisA", 'thuis_2': "TestUitA",
        'uit_1': "TestThuisB", 'uit_2': "TestUitB",
        'thuis_score': 10, 'uit_score': 5,
        'klinkers_thuis_1': 1, 'klinkers_thuis_2': 0,
        'klinkers_uit_1': 0, 'klinkers_uit_2': 2,
    }
    # Bepaal verwachte ELO's met de actuele logica
    from utils.utils_new_elo import calculate_new_elo
    all_ELO_ratings = {name: [elo] for name, elo in test_players.items()}
    test_match = {
        "Thuis_1": "TestThuisA",
        "Thuis_2": "TestUitA",
        "Uit_1": "TestThuisB",
        "Uit_2": "TestUitB",
        "Thuis_score": 10,
        "Uit_score": 5
    }
    calculated = calculate_new_elo(test_match, all_ELO_ratings)
    elo_updates = [(row['Speler'], round(row['ELO'], 0)) for _, row in calculated.iterrows()]
    success = db.add_match_and_update_elo(match_data, elo_updates)
    assert success, "Toevoegen van wedstrijd en loggen van ELO is mislukt."
    import time
    time.sleep(2)
    df_players_after = db.get_players()
    player_map_after = {row['speler_naam']: row for index, row in df_players_after.iterrows()}
    # Controleer dat de ELO's in de database overeenkomen met de berekende waarden
    for speler, expected_elo in elo_updates:
        actual_elo = player_map_after[speler]['rating']
        assert actual_elo == expected_elo, f"ELO voor {speler} klopt niet: verwacht {expected_elo}, database {actual_elo}"

    # Controle op dubbele ELO-entries per speler per wedstrijd
    elo_histories = []
    for name in test_players.keys():
        elo_hist = db.get_elo_history(_ttl=60, speler_naam=name)
        if not elo_hist.empty and 'match_id' in elo_hist.columns:
            elo_histories.append(elo_hist[['speler_naam', 'match_id']])
    if elo_histories:
        all_elo = pd.concat(elo_histories, ignore_index=True)
        dups = all_elo.duplicated(subset=['speler_naam', 'match_id'], keep=False)
        if dups.any():
            dup_rows = all_elo[dups]
            raise AssertionError(f"Dubbele ELO-entries per speler per wedstrijd gevonden! {dup_rows}")
