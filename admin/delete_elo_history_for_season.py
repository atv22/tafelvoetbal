def delete_elo_history_for_season(start_date, end_date):
    """
    Verwijdert alle ELO entries uit Firestore voor een specifiek seizoen.
    start_date en end_date moeten datetime.date of pandas.Timestamp zijn.
    """
    import pandas as pd
    from google.cloud.firestore_v1.base_query import FieldFilter
    batch = db.batch()
    batch_counter = 0
    elo_docs = elo_ref.where(filter=FieldFilter('timestamp', '>=', pd.Timestamp(start_date))).where(filter=FieldFilter('timestamp', '<=', pd.Timestamp(end_date))).stream()
    deleted_count = 0
    for doc in elo_docs:
        batch.delete(doc.reference)
        batch_counter += 1
        deleted_count += 1
        if batch_counter >= 400:
            batch.commit()
            batch = db.batch()
            batch_counter = 0
    if batch_counter > 0:
        batch.commit()
    clear_all_caches()
    return deleted_count
