
import firestore_service as db
import pandas as pd

def check_both():
    print("--- FIRESTORE ---")
    try:
        p_fs = db.get_players()
        brenda_fs = p_fs[p_fs['speler_naam'] == 'Brenda']
        if not brenda_fs.empty:
            print(f"Brenda Rating: {brenda_fs['rating'].iloc[0]}")
        else:
            print("Brenda not found in Firestore.")
    except Exception as e:
        print(f"Firestore error: {e}")

    print("\n--- GOOGLE SHEET ---")
    try:
        p_gs = db._read_gsheet_fallback('Spelers')
        brenda_gs = p_gs[p_gs['speler_naam'] == 'Brenda']
        if not brenda_gs.empty:
            print(f"Brenda Rating: {brenda_gs['rating'].iloc[0]}")
        else:
            print("Brenda not found in GSheet.")
    except Exception as e:
        print(f"GSheet error: {e}")

if __name__ == "__main__":
    check_both()
