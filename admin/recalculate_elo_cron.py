import sys
import os
import pandas as pd

# Voeg de root-map toe aan sys.path om firestore_service te kunnen importeren
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import firestore_service as db_service

def run_cron():
    print("Controleren of ELO-herberekening gepland/nodig is...")
    
    # We kunnen forceren als we worden aangeroepen met --force
    force = "--force" in sys.argv
    if force:
        print("Forceer-vlag gedetecteerd. Herberekening wordt direct uitgevoerd als recalc_needed True is (negeert 23:00 tijdcheck)...")
        config_ref = db_service.db.collection("system_config").document("elo_recalc")
        doc = config_ref.get()
        if doc.exists:
            data = doc.to_dict()
            if data.get("recalc_needed"):
                print(f"Geforceerde herberekening uitvoeren voor seizoen {data.get('season_naam')} vanaf {data.get('earliest_modified_timestamp')}")
                success = db_service.recalculate_elos_from(
                    data.get("earliest_modified_timestamp"),
                    data.get("season_start"),
                    data.get("season_end")
                )
                if success:
                    from datetime import datetime
                    config_ref.update({
                        "recalc_needed": False,
                        "earliest_modified_timestamp": None,
                        "last_recalc_time": datetime.now()
                    })
                    print("Herberekening succesvol voltooid.")
                else:
                    print("Herberekening mislukt.")
            else:
                print("Geen herberekening nodig (recalc_needed is False).")
        else:
            print("Systeemconfiguratie-document system_config/elo_recalc bestaat niet.")
    else:
        # Normale geplande controle uitvoeren (na 23:00)
        db_service.check_and_run_scheduled_recalc()

if __name__ == "__main__":
    run_cron()
