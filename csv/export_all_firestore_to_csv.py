r"""
Export all Firestore collections used by the app to CSV files.
Outputs:
- spelers.csv
- elo.csv
- uitslag.csv
- requests.csv
- seizoenen_afgeleid.csv (derived from matches)

Usage (Windows PowerShell):
  # Activate venv first
  & .\.venv\Scripts\Activate.ps1
  python admin\export_all_firestore_to_csv.py --outdir data\exports

If --outdir is omitted, files are written to data\exports\YYYYMMDD_HHMMSS.
Requires valid Firestore credentials via Streamlit secrets or firestore-key.json.
"""
import os
import sys
import argparse
import datetime as dt
import pandas as pd

# Ensure workspace root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import firestore_service as db  # noqa: E402


def ensure_outdir(base_outdir: str | None) -> str:
    """Create output directory; default under data/exports/<timestamp>."""
    if base_outdir:
        outdir = base_outdir
    else:
        ts = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
        outdir = os.path.join(ROOT, 'data', 'exports', ts)
    os.makedirs(outdir, exist_ok=True)
    return outdir


def df_to_csv(df: pd.DataFrame, path: str) -> None:
    # Normalize timestamps to tz-naive ISO where possible
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            # Ensure timezone-aware conversion, then drop tz to make naive
            df[col] = pd.to_datetime(df[col], errors='coerce', utc=True).dt.tz_localize(None)
    df.to_csv(path, index=False, encoding='utf-8')
    print(f"Saved {path} ({len(df)} rows)")


def export_all(outdir: str) -> None:
    # spelers
    try:
        players = db.get_players()
        if players is None or getattr(players, 'empty', False):
            raise Exception('Lege spelers DataFrame')
        df_to_csv(players, os.path.join(outdir, 'spelers.csv'))
    except Exception as e:
        print(f"[WARN] Kon spelers niet exporteren via get_players: {e}")
        # Fallback: direct uit Firestore collectieref om toch een export te hebben
        try:
            rows = []
            for doc in db.players_ref.stream():
                d = doc.to_dict() or {}
                d['speler_id'] = doc.id
                rows.append(d)
            players_df = pd.DataFrame(rows)
            if not players_df.empty:
                # Probeer laatste ELO per speler mee te mergen indien mogelijk
                try:
                    elo_df = db.get_elo_logs()
                    if not elo_df.empty and 'speler_naam' in elo_df.columns and 'timestamp' in elo_df.columns:
                        latest_elo = elo_df.loc[elo_df.groupby('speler_naam')['timestamp'].idxmax()]
                        players_df = players_df.merge(latest_elo[['speler_naam','rating']], on='speler_naam', how='left')
                        players_df['rating'] = players_df['rating'].fillna(1000)
                except Exception:
                    pass
                df_to_csv(players_df, os.path.join(outdir, 'spelers.csv'))
            else:
                print('[WARN] Geen spelersdocumenten gevonden in Firestore.')
        except Exception as e2:
            print(f"[WARN] Fallback spelers-export mislukt: {e2}")

    # elo logs
    try:
        elo = db.get_elo_logs()
        df_to_csv(elo, os.path.join(outdir, 'elo.csv'))
    except Exception as e:
        print(f"[WARN] Kon elo niet exporteren: {e}")

    # uitslag (matches)
    try:
        matches = db.get_matches()
        df_to_csv(matches, os.path.join(outdir, 'uitslag.csv'))
    except Exception as e:
        print(f"[WARN] Kon uitslag niet exporteren: {e}")

    # requests
    try:
        requests = db.get_requests()
        df_to_csv(requests, os.path.join(outdir, 'requests.csv'))
    except Exception as e:
        print(f"[WARN] Kon requests niet exporteren: {e}")

    # Derived seasons from matches
    try:
        seasons = db.get_seasons()
        df_to_csv(seasons, os.path.join(outdir, 'seizoenen_afgeleid.csv'))
    except Exception as e:
        print(f"[WARN] Kon seizoenen niet exporteren: {e}")


def main():
    parser = argparse.ArgumentParser(description='Export Firestore collections to CSV files')
    parser.add_argument('--outdir', type=str, default=None, help='Output directory (default: data/exports/<timestamp>)')
    args = parser.parse_args()
    outdir = ensure_outdir(args.outdir)
    export_all(outdir)
    print('Export voltooid.')


if __name__ == '__main__':
    main()
