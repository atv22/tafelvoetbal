# test_firestore.py

import firestore_service as db
import pandas as pd
import time

# TEST CONFIGURATIE
TEST_PLAYERS = {
    "TestSpelerAlpha": 1000,
    "TestSpelerBravo": 1000,
    "TestSpelerCharlie": 1000,
    "TestSpelerDelta": 1000,
}
player_ids_to_cleanup = []

def cleanup_test_players():
    """Ruimt eventuele overgebleven testspelers en hun ELO-geschiedenis van eerdere runs op."""
    print("\n Vooraf opruimen...")
    try:
        df_players = db.get_players()
        if df_players.empty:
            print(" -> Geen spelers gevonden om op te ruimen.")
            return

        deleted_count = 0
        # Gebruik .iterrows() om door de rijen van de DataFrame te itereren
        for index, player in df_players.iterrows():
            # Zorg ervoor dat 'speler_naam' en 'speler_id' bestaan in de rij
            if 'speler_naam' in player and 'speler_id' in player and str(player['speler_naam']).startswith("TestSpeler"):
                if db.delete_player_by_id(player['speler_id']):
                    deleted_count += 1
        
        if deleted_count > 0:
            print(f" -> {deleted_count} overgebleven testspelers en hun ELO-geschiedenis verwijderd.")
        else:
            print(" -> Geen overgebleven testspelers gevonden.")
            
    except Exception as e:
        print(f"Fout tijdens vooraf opruimen: {e}")


def run_test():
    """Voert een reeks tests uit op de Firestore service volgens de nieuwe databasestructuur."""
    
    cleanup_test_players()
    time.sleep(3) # Geef Firestore de tijd om de verwijderingen te verwerken

    print("\nSTART TEST")
    
    try:
        # === TEST 1: Spelers toevoegen ===
        print("\n Spelers toevoegen...")
        for name, elo in TEST_PLAYERS.items():
            result = db.add_player(name, elo)
            assert result == "Success", f"Kon speler {name} niet toevoegen. Resultaat: {result}"
        print(" -> SUCCES: Alle testspelers en hun initiële ELO succesvol toegevoegd.")
        time.sleep(2)

        # === TEST 2: Spelers ophalen en verifiëren ===
        print("\n Spelers ophalen en verifiëren...")
        df_players = db.get_players()
        assert not df_players.empty, "DataFrame met spelers is leeg."
        assert len(df_players) >= len(TEST_PLAYERS), "Niet alle spelers zijn opgehaald."

        # Maak een dictionary voor makkelijke toegang
        player_map = {row['speler_naam']: row for index, row in df_players.iterrows()}

        for name, elo in TEST_PLAYERS.items():
            assert name in player_map, f"Testspeler {name} niet gevonden in database."
            assert player_map[name]['rating'] == elo, f"ELO voor {name} is incorrect."
            # Sla de ID op voor de opruimactie
            player_ids_to_cleanup.append(player_map[name]['speler_id'])

        print(" -> SUCCES: Alle testspelers succesvol opgehaald en geverifieerd.")

        # === TEST 3: Wedstrijd toevoegen en ELO-update controleren ===
        print("\n Wedstrijd toevoegen en ELO-update controleren...")
        # Team 1 (winnaars): Alpha & Charlie
        # Team 2 (verliezers): Bravo & Delta
        
        match_data = {
            'thuis_1': "TestSpelerAlpha", 'thuis_2': "TestSpelerCharlie",
            'uit_1': "TestSpelerBravo", 'uit_2': "TestSpelerDelta",
            'thuis_score': 10, 'uit_score': 5,
            'klinkers_thuis_1': 1, 'klinkers_thuis_2': 0,
            'klinkers_uit_1': 0, 'klinkers_uit_2': 2,
        }
        
        # De nieuwe ELO-ratings die gelogd moeten worden
        elo_updates = [
            ("TestSpelerAlpha", 1016), ("TestSpelerCharlie", 1016),
            ("TestSpelerBravo", 984), ("TestSpelerDelta", 984)
        ]

        success = db.add_match_and_update_elo(match_data, elo_updates)
        assert success, "Toevoegen van wedstrijd en loggen van ELO is mislukt."
        print(" -> SUCCES: Wedstrijd en nieuwe ELO-ratings succesvol gelogd.")
        time.sleep(2)

        # Verifieer de nieuwe ELO-scores door get_players opnieuw aan te roepen
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
        # === STAP 4: Opruimen ===
        print("\n Testdata opruimen...")
        if not player_ids_to_cleanup:
            print(" -> Geen spelers om op te ruimen.")
        else:
            deleted_count = 0
            # We gebruiken de opgeslagen IDs voor de opruimactie
            for player_id in player_ids_to_cleanup:
                if db.delete_player_by_id(player_id):
                    deleted_count += 1
            print(f" -> SUCCES: {deleted_count} van de {len(player_ids_to_cleanup)} testspelers (en hun ELO-geschiedenis) verwijderd.")

    print("\nEINDE TEST")


if __name__ == "__main__":
    run_test()