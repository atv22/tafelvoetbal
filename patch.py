import re

with open('firestore_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_code = '''def set_recalc_needed_flag(season_start, season_end, season_naam):
    try:
        import pandas as pd
        config_ref = db.collection("system_config").document("elo_recalc")
        config_ref.set({
            "recalc_needed": True,
            "season_start": pd.Timestamp(season_start),
            "season_end": pd.Timestamp(season_end),
            "season_naam": season_naam,
            "timestamp": pd.Timestamp.now()
        })
    except Exception as e:
        print(f"Error setting recalc flag: {e}")

def recalculate_elos_from(start_timestamp, season_start, season_end):
    \"\"\"Herberekent ELO scores incrementeel vanaf een specifiek tijdstip binnen een seizoen.\"\"\"
    try:
        import pandas as pd
        from google.cloud.firestore_v1.base_query import FieldFilter
        from utils.utils_new_elo import calculate_new_elo
        
        all_matches = get_matches().sort_values('timestamp', ascending=True)
        players_df = get_players()
        
        start_ts_pd = pd.Timestamp(start_timestamp)
        if start_ts_pd.tzinfo is not None:
            start_ts_pd = start_ts_pd.tz_localize(None)

        all_matches['ts_naive'] = all_matches['timestamp'].apply(lambda x: x.replace(tzinfo=None) if hasattr(x, 'tzinfo') and x.tzinfo is not None else x)
        
        season_mask = (all_matches['ts_naive'].dt.date >= pd.Timestamp(season_start).date()) & (all_matches['ts_naive'].dt.date <= pd.Timestamp(season_end).date())
        season_matches = all_matches[season_mask]
        
        future_matches = season_matches[season_matches['ts_naive'] >= start_ts_pd]
        
        if future_matches.empty:
            clear_all_caches(only_elo=True, only_players=True)
            return True

        elo_df = get_elo_logs()
        elo_df['ts_naive'] = elo_df['timestamp'].apply(lambda x: x.replace(tzinfo=None) if hasattr(x, 'tzinfo') and x.tzinfo is not None else x)
        
        past_elos = elo_df[(elo_df['ts_naive'] >= pd.Timestamp(season_start)) & (elo_df['ts_naive'] < start_ts_pd)]
        
        player_elos = {name: 1000 for name in players_df['speler_naam']}
        player_matches = {name: 0 for name in players_df['speler_naam']}
        
        for name in player_elos.keys():
            p_history = past_elos[past_elos['speler_naam'] == name]
            if not p_history.empty:
                last_record = p_history.loc[p_history['ts_naive'].idxmax()]
                player_elos[name] = last_record['rating']
                player_matches[name] = len(p_history) - 1
        
        batch = db.batch()
        
        start_ts_utc = start_timestamp
        end_ts_utc = pd.Timestamp(season_end)
        if not hasattr(end_ts_utc, 'tzinfo') or end_ts_utc.tzinfo is None:
            end_ts_utc = end_ts_utc.tz_localize('UTC')
        end_ts_utc = end_ts_utc + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        
        old_elos = elo_ref.where(filter=FieldFilter('timestamp', '>=', start_ts_utc)).where(filter=FieldFilter('timestamp', '<=', end_ts_utc)).stream()
        c = 0
        for doc in old_elos:
            batch.delete(doc.reference)
            c += 1
            if c >= 400:
                batch.commit()
                batch = db.batch()
                c = 0
        if c > 0: batch.commit()
        
        batch = db.batch()
        c = 0
        for _, match in future_matches.iterrows():
            m_dict = {
                "Thuis_1": match['thuis_1'], "Thuis_2": match['thuis_2'],
                "Uit_1": match['uit_1'], "Uit_2": match['uit_2'],
                "Thuis_score": match['thuis_score'], "Uit_score": match['uit_score'],
                "klinkers_thuis_1": match.get('klinkers_thuis_1', 0),
                "klinkers_thuis_2": match.get('klinkers_thuis_2', 0),
                "klinkers_uit_1": match.get('klinkers_uit_1', 0),
                "klinkers_uit_2": match.get('klinkers_uit_2', 0)
            }
            m_players = {m_dict[k] for k in ["Thuis_1", "Thuis_2", "Uit_1", "Uit_2"] if m_dict[k]}
            
            all_ratings = {p: [player_elos.get(p, 1000)] * (player_matches.get(p, 0) + 1) for p in m_players}
            
            new_df = calculate_new_elo(m_dict, all_ratings)
            for _, row in new_df.iterrows():
                p, r = row['Speler'], row['ELO']
                player_elos[p] = r
                player_matches[p] = player_matches.get(p, 0) + 1
                batch.set(elo_ref.document(), {
                    'speler_naam': p, 
                    'rating': r, 
                    'timestamp': match['timestamp'], 
                    'match_id': match['match_id']
                })
                c += 1
                if c >= 400:
                    batch.commit()
                    batch = db.batch()
                    c = 0
        
        for name, rating in player_elos.items():
            p_docs = players_ref.where(filter=FieldFilter('speler_naam', '==', name)).limit(1).get()
            if p_docs:
                batch.update(p_docs[0].reference, {'rating': rating})
                c += 1
                if c >= 400:
                    batch.commit()
                    batch = db.batch()
                    c = 0

        if c > 0: batch.commit()
        clear_all_caches(only_elo=True, only_players=True)
        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Incremental recalc error: {e}")
        return False

def delete_match_with_elo_recalculation(match_id):
    \"\"\"Verwijdert match en herbereken seizoen.\"\"\"
    try:
        from google.cloud.firestore_v1.base_query import FieldFilter
        import pandas as pd
        
        doc = matches_ref.document(match_id).get()
        if not doc.exists: 
            print(f"Match {match_id} not found in Firestore.")
            return True
        
        match_data = doc.to_dict()
        ts = match_data.get('timestamp')
        
        matches_ref.document(match_id).delete()
        
        try:
            elo_docs = elo_ref.where(filter=FieldFilter('match_id', '==', match_id)).stream()
            b = db.batch()
            for edoc in elo_docs: b.delete(edoc.reference)
            b.commit()
        except Exception:
            pass
        
        seasons = get_seasons()
        
        if hasattr(ts, 'tzinfo') and ts.tzinfo is not None:
            ts_naive = ts.replace(tzinfo=None)
        else:
            ts_naive = ts
            
        s_row = seasons[(seasons['start_datum'] <= ts_naive) & (seasons['eind_datum'] >= ts_naive)]
        
        if not s_row.empty:
            start_date = s_row.iloc[0]['start_datum']
            end_date = s_row.iloc[0]['eind_datum']
            season_naam = s_row.iloc[0]['seizoen_naam']
            
            today = pd.Timestamp.now().date()
            if ts_naive.date() == today:
                print(f"Match is from today. Incremental recalculation for {season_naam} from {ts_naive}")
                recalculate_elos_from(ts, start_date, end_date)
                return "INCREMENTAL"
            else:
                print(f"Match is older than today. Setting cron flag for {season_naam}")
                set_recalc_needed_flag(start_date, end_date, season_naam)
                clear_all_caches(only_matches=True, only_elo=True)
                return "FLAGGED"
        else:
            print(f"No matching season found for match at {ts_naive}. Skipping ELO recalculation.")
            
        clear_all_caches(only_matches=True, only_elo=True)
        return True
    except Exception as e:
        print(f"Error in delete_match_with_elo_recalculation: {e}")
        import traceback
        traceback.print_exc()
        return False'''

content = re.sub(
    r'def delete_match_with_elo_recalculation\(match_id\):.*?(?=\n\n|\Z)',
    new_code,
    content,
    flags=re.DOTALL
)

with open('firestore_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
