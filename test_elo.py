# test_elo.py
"""
Combineert ELO-checks en ELO-testcases voor de tafelvoetbal-app.
"""
import pandas as pd
import firestore_service as db
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
                # Forceer alle timestamps naar tz-naive (UTC)
                if elo_hist['timestamp'].dt.tz is not None:
                    elo_hist['timestamp'] = elo_hist['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
                else:
                    try:
                        elo_hist['timestamp'] = elo_hist['timestamp'].dt.tz_localize(None)
                    except Exception:
                        pass
                in_season = elo_hist[(elo_hist['timestamp'] >= start) & (elo_hist['timestamp'] <= end)]
                if in_season.empty:
                    missing_elo.append((speler, season['seizoen_naam']))
    if missing_elo:
        print("[CHECK] Spelers zonder ELO in seizoen:")
        for speler, seizoen in missing_elo:
            print(f"  {speler} in {seizoen}")
    else:
        print("[CHECK] Alle spelers hebben een ELO in elk seizoen waarin ze speelden.")

# TEST CONFIGURATIE
test_players = {
    "TestSpelerAlpha": 1000,
    "TestSpelerBravo": 1000,
    "TestSpelerCharlie": 1000,
    "TestSpelerDelta": 1000,
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
            if 'speler_naam' in player and 'speler_id' in player and str(player['speler_naam']).startswith("TestSpeler"):
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
            'thuis_1': "TestSpelerAlpha", 'thuis_2': "TestSpelerCharlie",
            'uit_1': "TestSpelerBravo", 'uit_2': "TestSpelerDelta",
            'thuis_score': 10, 'uit_score': 5,
            'klinkers_thuis_1': 1, 'klinkers_thuis_2': 0,
            'klinkers_uit_1': 0, 'klinkers_uit_2': 2,
        }
        elo_updates = [
            ("TestSpelerAlpha", 1016), ("TestSpelerCharlie", 1016),
            ("TestSpelerBravo", 984), ("TestSpelerDelta", 984)
        ]
        success = db.add_match_and_update_elo(match_data, elo_updates)
        assert success, "Toevoegen van wedstrijd en loggen van ELO is mislukt."
        print(" -> SUCCES: Wedstrijd en nieuwe ELO-ratings succesvol gelogd.")
        time.sleep(2)
        df_players_after = db.get_players()
        player_map_after = {row['speler_naam']: row for index, row in df_players_after.iterrows()}
        assert player_map_after["TestSpelerAlpha"]['rating'] == 1016
        assert player_map_after["TestSpelerCharlie"]['rating'] == 1016
        assert player_map_after["TestSpelerBravo"]['rating'] == 984
        assert player_map_after["TestSpelerDelta"]['rating'] == 984
        print(" -> SUCCES: ELO-scores zijn correct bijgewerkt en opgehaald.")
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

if __name__ == "__main__":
    print("=== ELO CHECK PER SEIZOEN ===")
    check_elo_per_season()
    print("\n=== ELO FUNCTIONELE TESTS ===")
    run_elo_test()
