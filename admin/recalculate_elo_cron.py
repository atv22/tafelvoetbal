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
            data = doc.to_dict() or {}
            if data.get("recalc_needed"):
                pending_map = data.get("pending_recalcs") or {}
                if isinstance(pending_map, dict) and pending_map:
                    items = sorted(
                        [v for v in pending_map.values() if isinstance(v, dict)],
                        key=lambda x: pd.Timestamp(x.get("season_start") or x.get("earliest_modified_timestamp"))
                    )
                    failed_pending = {}
                    for item in items:
                        sname = str(item.get("season_naam") or "unknown")
                        print(f"Geforceerde herberekening uitvoeren voor seizoen {sname} vanaf {item.get('earliest_modified_timestamp')}")
                        ok = db_service.recalculate_elos_from(
                            item.get("earliest_modified_timestamp"),
                            item.get("season_start"),
                            item.get("season_end")
                        )
                        if not ok:
                            failed_pending[sname] = item
                    success = len(failed_pending) == 0
                else:
                    print(f"Geforceerde herberekening uitvoeren voor seizoen {data.get('season_naam')} vanaf {data.get('earliest_modified_timestamp')}")
                    success = db_service.recalculate_elos_from(
                        data.get("earliest_modified_timestamp"),
                        data.get("season_start"),
                        data.get("season_end")
                    )
                    failed_pending = {}

                if success:
                    config_ref.update({
                        "recalc_needed": False,
                        "earliest_modified_timestamp": None,
                        "pending_recalcs": {},
                        "last_recalc_time": db_service._get_nl_now_aware()
                    })
                    print("Herberekening succesvol voltooid.")
                else:
                    if failed_pending:
                        config_ref.update({"pending_recalcs": failed_pending})
                    print("Herberekening (deels) mislukt.")
            else:
                print("Geen herberekening nodig (recalc_needed is False).")
        else:
            print("Systeemconfiguratie-document system_config/elo_recalc bestaat niet.")
    else:
        # Normale geplande controle uitvoeren (na 23:00)
        db_service.check_and_run_scheduled_recalc()

if __name__ == "__main__":
    run_cron()
