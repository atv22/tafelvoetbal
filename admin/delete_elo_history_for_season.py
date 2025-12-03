from __future__ import annotations
from datetime import datetime
from typing import Optional

import pandas as pd

try:
    # Prefer local service if available
    import firestore_service as fs
except Exception:
    fs = None


def delete_elo_history_for_season(start_date: datetime, end_date: datetime, dry_run: bool = False) -> int:
    """
    Delete ELO history documents whose timestamp falls within [start_date, end_date].

    Returns the count of deleted documents. If dry_run=True, no deletions occur
    and the function returns how many would be removed.
    """
    if fs is None:
        raise RuntimeError("firestore_service module not available")

    # Normalize to tz-naive for consistent comparisons
    def to_naive(dt: datetime) -> datetime:
        if isinstance(dt, pd.Timestamp):
            dt = dt.to_pydatetime()
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt

    start = to_naive(start_date)
    end = to_naive(end_date)
    if end < start:
        raise ValueError("end_date must be on or after start_date")

    # Fetch ELO logs; use service helper if available
    try:
        elo_df = fs.get_elo_logs()
    except Exception:
        # Fallback to direct collection if helper fails
        elo_ref = getattr(fs, 'elo_ref', None)
        db = getattr(fs, 'db', None)
        if elo_ref is None or db is None:
            raise RuntimeError("Firestore ELO reference not available")
        docs = list(elo_ref.stream())
        rows = []
        for d in docs:
            data = d.to_dict() or {}
            data['doc_ref'] = d.reference
            rows.append(data)
        elo_df = pd.DataFrame(rows)

    if elo_df.empty:
        return 0

    # Ensure timestamp column exists and is comparable
    if 'timestamp' not in elo_df.columns:
        return 0

    ts = pd.to_datetime(elo_df['timestamp'], errors='coerce')
    ts = ts.dt.tz_localize(None) if getattr(ts.dt, 'tz', None) is not None else ts
    elo_df = elo_df.assign(_ts=ts)

    mask = (elo_df['_ts'] >= start) & (elo_df['_ts'] <= end)
    target_df = elo_df.loc[mask]

    if target_df.empty:
        return 0

    if dry_run:
        return len(target_df)

    # Delete in batches for safety
    batch_size = 400
    deleted = 0

    # Try using db.batch() if available; otherwise delete one-by-one
    db = getattr(fs, 'db', None)
    if db is not None:
        batch = db.batch()
        counter = 0
        for _, row in target_df.iterrows():
            ref = row.get('doc_ref')
            if ref is None:
                # Resolve by query fallback
                try:
                    from google.cloud.firestore_v1.base_query import FieldFilter
                    elo_ref = getattr(fs, 'elo_ref', None)
                    match_id = row.get('match_id')
                    speler_naam = row.get('speler_naam')
                    if elo_ref is not None and match_id is not None and speler_naam is not None:
                        for d in elo_ref.where(filter=FieldFilter('match_id', '==', match_id)).where(filter=FieldFilter('speler_naam', '==', speler_naam)).stream():
                            batch.delete(d.reference)
                            counter += 1
                            deleted += 1
                            if counter >= batch_size:
                                batch.commit()
                                batch = db.batch()
                                counter = 0
                        continue
                except Exception:
                    pass
                # If still not found, skip
                continue
            batch.delete(ref)
            counter += 1
            deleted += 1
            if counter >= batch_size:
                batch.commit()
                batch = db.batch()
                counter = 0
        if counter > 0:
            batch.commit()
    else:
        # No batch available, attempt direct deletes
        for _, row in target_df.iterrows():
            ref = row.get('doc_ref')
            if ref is not None:
                ref.delete()
                deleted += 1

    return deleted
