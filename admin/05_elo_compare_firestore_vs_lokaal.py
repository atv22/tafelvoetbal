import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
"""
Vergelijk ELO-historie uit Firestore-export en lokale herberekening.
- Toont verschillen per speler per match_id (rating, aanwezigheid, etc)
- Print samenvatting van afwijkingen en opvallende gevallen
"""
import pandas as pd
import os

def main():
    data_dir = 'data'
    # Zoek juiste bestanden
    files = os.listdir(data_dir)
    orig = sorted([f for f in files if f.startswith('Tafelvoetbal_ELO_Geschiedenis_') and f.endswith('.csv')])[-1]
    new = sorted([f for f in files if f.startswith('ELO_Herberekend_') and f.endswith('.csv')])[-1]
    print(f"Vergelijk: {orig} (Firestore) vs {new} (lokaal)")
    df_orig = pd.read_csv(os.path.join(data_dir, orig))
    df_new = pd.read_csv(os.path.join(data_dir, new))
    # Merge op match_id, speler_naam, timestamp
    merged = pd.merge(df_orig, df_new, on=['match_id','speler_naam','timestamp'], how='outer', suffixes=('_fs','_nieuw'), indicator=True)
    # 1. Check: zijn er spelers+match_id's die ontbreken in een van beide?
    ontbrekend_in_nieuw = merged[merged['_merge']=='left_only']
    ontbrekend_in_fs = merged[merged['_merge']=='right_only']
    if not ontbrekend_in_nieuw.empty:
        print(f"[!] {len(ontbrekend_in_nieuw)} entries uit Firestore ontbreken in nieuwe berekening:")
        print(ontbrekend_in_nieuw[['match_id','speler_naam','timestamp','rating_fs']].head(10))
    if not ontbrekend_in_fs.empty:
        print(f"[!] {len(ontbrekend_in_fs)} entries uit nieuwe berekening ontbreken in Firestore:")
        print(ontbrekend_in_fs[['match_id','speler_naam','timestamp','rating_nieuw']].head(10))
    # 2. Check: verschil in rating
    merged['abs_diff'] = (merged['rating_fs'] - merged['rating_nieuw']).abs()
    afwijkingen = merged[merged['abs_diff'] > 1e-3]
    if not afwijkingen.empty:
        print(f"[!] {len(afwijkingen)} ratings verschillen > 0.001:")
        print(afwijkingen[['match_id','speler_naam','timestamp','rating_fs','rating_nieuw','abs_diff']].head(10))
    else:
        print("[OK] Geen significante ratingverschillen gevonden.")
    # 3. Samenvatting
    print(f"Totaal vergeleken: {len(merged)} speler-wedstrijd entries.")
    print(f"Aantal afwijkingen > 0.001: {len(afwijkingen)}")
    print(f"Aantal alleen in Firestore: {len(ontbrekend_in_nieuw)}")
    print(f"Aantal alleen in nieuwe berekening: {len(ontbrekend_in_fs)}")

if __name__ == "__main__":
    main()
