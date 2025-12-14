import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
r"""
Ingest offline CSV writes from `csv/write` into Firestore.
Handles players, matches, elo logs, and requests with duplicate checks.

Usage (PowerShell):
  & .\.venv\Scripts\Activate.ps1
  python admin\import_offline_csv_writes.py --dry-run false

Defaults to dry-run. Set --dry-run false to actually write.
"""
import os
import sys
import argparse
import pandas as pd
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import firestore_service as db
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore

WRITE_DIR = os.path.join(ROOT, 'csv', 'write')


def read_csv(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    # Normalize timestamps
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df['timestamp'] = db.normalize_timestamp_series(df['timestamp'])
    if 'Timestamp' in df.columns:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        df['Timestamp'] = db.normalize_timestamp_series(df['Timestamp'])
    return df


def import_players(df: pd.DataFrame, dry_run: bool):
    if df.empty:
        return 0, 0
    added, duplicates = 0, 0
    # Existing set
    existing = {doc.to_dict().get('speler_naam') for doc in db.players_ref.stream()}
    batch = db.db.batch()
    for _, row in df.iterrows():
        name = row.get('speler_naam')
        if not name:
            continue
        if name in existing:
            duplicates += 1
            continue
        if dry_run:
            added += 1
            continue
        new_player_ref = db.players_ref.document()
        batch.set(new_player_ref, {'speler_naam': name})
        added += 1
    if not dry_run:
        batch.commit()
    return added, duplicates


def import_requests(df: pd.DataFrame, dry_run: bool):
    if df.empty:
        return 0
    count = 0
    batch = db.db.batch()
    for _, row in df.iterrows():
        verzoek = row.get('Verzoek')
        ts = row.get('Timestamp')
        ts_val = ts if pd.notnull(ts) else datetime.utcnow()
        if dry_run:
            count += 1
            continue
        new_req = db.requests_ref.document()
        batch.set(new_req, {'Verzoek': verzoek, 'Timestamp': ts_val})
        count += 1
    if not dry_run:
        batch.commit()
    return count


def import_matches_and_elos(matches_df: pd.DataFrame, elo_df: pd.DataFrame, dry_run: bool):
    if matches_df.empty:
        return 0, 0
    added_matches = 0
    added_elos = 0
    # Build duplicate check set from recent Firestore matches
    existing_matches = set()
    for doc in db.matches_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(5000).stream():
        d = doc.to_dict()
        # Filter None before sorting to satisfy type checker and ensure stable comparison
        players_list = [p for p in [d.get('thuis_1'), d.get('thuis_2'), d.get('uit_1'), d.get('uit_2')] if p is not None]
        players_tuple = tuple(sorted(players_list))
        scores_tuple = (d.get('thuis_score'), d.get('uit_score'))
        ts = pd.to_datetime(d.get('timestamp'), errors='coerce')
        existing_matches.add((players_tuple, scores_tuple, ts))

    batch = db.db.batch()
    elo_batch = db.db.batch()

    for _, m in matches_df.iterrows():
        thuis_1 = m.get('thuis_1'); thuis_2 = m.get('thuis_2'); uit_1 = m.get('uit_1'); uit_2 = m.get('uit_2')
        players_list = [p for p in [thuis_1, thuis_2, uit_1, uit_2] if p is not None]
        players_tuple = tuple(sorted(players_list))
        scores_tuple = (m.get('thuis_score'), m.get('uit_score'))
        ts = m.get('timestamp')
        ts_val = ts if pd.notnull(ts) else datetime.utcnow()
        if (players_tuple, scores_tuple, pd.to_datetime(ts_val)) in existing_matches:
            continue
        if dry_run:
            added_matches += 1
        else:
            new_match_ref = db.matches_ref.document()
            match_id = new_match_ref.id
            payload = {
                'thuis_1': thuis_1,
                'thuis_2': thuis_2,
                'uit_1': uit_1,
                'uit_2': uit_2,
                'thuis_score': int(m.get('thuis_score', 0) or 0),
                'uit_score': int(m.get('uit_score', 0) or 0),
                'timestamp': ts_val,
            }
            batch.set(new_match_ref, payload)
            added_matches += 1
            # Attach ELO rows with same timestamp for these players if present
            if not elo_df.empty:
                related = elo_df[elo_df['timestamp'] == ts]
                for _, e in related.iterrows():
                    elo_doc = db.elo_ref.document()
                    elo_batch.set(elo_doc, {
                        'speler_naam': e.get('speler_naam'),
                        'rating': float(e.get('rating')) if pd.notnull(e.get('rating')) else 1000,
                        'timestamp': ts_val,
                        'match_id': match_id
                    })
                    added_elos += 1
    if not dry_run:
        if added_matches:
            batch.commit()
        if added_elos:
            elo_batch.commit()
    return added_matches, added_elos


def main():
    parser = argparse.ArgumentParser(description='Import offline CSV writes into Firestore')
    parser.add_argument('--dry-run', type=lambda x: x.lower() != 'false', default=True,
                        help='Dry-run mode (default true). Set to false to write.')
    args = parser.parse_args()

    spelers_path = os.path.join(WRITE_DIR, 'spelers.csv')
    uitslag_path = os.path.join(WRITE_DIR, 'uitslag.csv')
    elo_path = os.path.join(WRITE_DIR, 'elo.csv')
    requests_path = os.path.join(WRITE_DIR, 'requests.csv')

    spelers_df = read_csv(spelers_path)
    uitslag_df = read_csv(uitslag_path)
    elo_df = read_csv(elo_path)
    requests_df = read_csv(requests_path)

    a,d = import_players(spelers_df, args.dry_run)
    print(f"Spelers: toegevoegd={a}, duplicaten={d}")
    r = import_requests(requests_df, args.dry_run)
    print(f"Requests: toegevoegd={r}")
    m,e = import_matches_and_elos(uitslag_df, elo_df, args.dry_run)
    print(f"Wedstrijden: toegevoegd={m}, ELO logs: toegevoegd={e}")
    print("Klaar.")


if __name__ == '__main__':
    main()
