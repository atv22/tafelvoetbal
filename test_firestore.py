# test_firestore.py

import firestore_service as db
import pandas as pd
import time

# TEST CONFIGURATIE
# We gebruiken unieke namen om conflicten met bestaande data te voorkomen
TEST_PLAYERS = {
    "TestSpelerAlpha": 1000,
    "TestSpelerBravo": 1000,
    "TestSpelerCharlie": 1000,
    "TestSpelerDelta": 1000,
}
player_ids_to_cleanup = []

def run_test():
    """Voert een reeks tests uit op de Firestore service."""
    
    print("START TEST")
    
    try:
        # === TEST 1: Spelers toevoegen ===
        print("\n Spelers toevoegen...")
        for name, elo in TEST_PLAYERS.items():
            result = db.add_player(name, elo)
            assert result == "Success", f"Kon speler {name} niet toevoegen."
        print(" -> SUCCES: Alle testspelers succesvol toegevoegd.")
        time.sleep(2) # Geef Firestore even de tijd om te synchroniseren

        # === TEST 2: Spelers ophalen en verifiëren ===
        print("\n Spelers ophalen en verifiëren...")
        df_players = db.get_players()
        assert not df_players.empty, "DataFrame met spelers is leeg."
        
        for name in TEST_PLAYERS.keys():
            assert name in df_players['name'].values, f"Testspeler {name} niet gevonden in database."
            # Sla de ID op voor de opruimactie
            player_id = df_players[df_players['name'] == name]['player_id'].iloc
            player_ids_to_cleanup.append(player_id)

        print(" -> SUCCES: Alle testspelers succesvol opgehaald en geverifieerd.")

        # === TEST 3: Wedstrijd toevoegen en ELO-update controleren ===
        print("\n Wedstrijd toevoegen en ELO-update controleren...")
        # Team 1 (winnaars): Alpha & Charlie
        # Team 2 (verliezers): Bravo & Delta
        
        # Haal de IDs en ELOs op
        player_dict = df_players.set_index('name').to_dict('index')
        id_alpha = player_dict['player_id']
        id_bravo = player_dict['player_id']
        id_charlie = player_dict['player_id']
        id_delta = player_dict['player_id']

        match_data = {
            'thuis_speler_1_id': id_alpha, 'thuis_speler_2_id': id_charlie,
            'uit_speler_1_id': id_bravo, 'uit_speler_2_id': id_delta,
            'Thuis_score': 10, 'Uit_score': 5, 'timestamp': "test_timestamp"
        }
        
        # Aangezien alle spelers starten met 1000 ELO, is de verwachte verandering +16 voor de winnaars en -16 voor de verliezers.
        elo_updates = [
            (1016, id_alpha), (1016, id_charlie),
            (984, id_bravo), (984, id_delta)
        ]

        success = db.add_match_and_update_elo(match_data, elo_updates)
        assert success, "Toevoegen van wedstrijd en updaten van ELO is mislukt."
        print(" -> SUCCES: Wedstrijd succesvol toegevoegd via batch write.")
        time.sleep(2)

        # Verifieer de nieuwe ELO-scores
        df_players_after = db.get_players()
        player_dict_after = df_players_after.set_index('name').to_dict('index')

        assert player_dict_after['elo'] == 1016
        assert player_dict_after['elo'] == 1016
        assert player_dict_after['elo'] == 984
        assert player_dict_after['elo'] == 984
        print(" -> SUCCES: ELO-scores zijn correct bijgewerkt.")

    except AssertionError as e:
        print(f"\n!!! TEST MISLUKT: {e}!!!")
    
    finally:
        # === STAP 4: Opruimen ===
        print("\n Testdata opruimen...")
        if not player_ids_to_cleanup:
            print(" -> Geen spelers om op te ruimen.")
        else:
            deleted_count = 0
            for player_id in player_ids_to_cleanup:
                if db.delete_player_by_id(player_id):
                    deleted_count += 1
            print(f" -> SUCCES: {deleted_count} van de {len(player_ids_to_cleanup)} testspelers verwijderd.")
            # N.B.: De wedstrijden blijven achter, maar bevatten nu ongeldige speler-ID's.
            # Voor een simpele test is dit acceptabel.

    print("\nEINDE TEST")


if __name__ == "__main__":
    run_test()