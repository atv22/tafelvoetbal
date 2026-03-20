# --- Failsafe: Firestore bereikbaarheidscheck en custom exception ---
import streamlit as st
import os
import google.cloud.firestore
from google.oauth2 import service_account
import json
import pandas as pd
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

# Google Sheet ID voor fallback
SHEET_ID = "1cCiNoYfro9SqS8qIjEKT8prsAvAA7wowvhzhh2ljHnA"
GS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

class FirestoreUnavailable(Exception):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details

def handle_firestore_exceptions(func):
    """Decorator: Vang Firestore exceptions en geef een duidelijke foutmelding."""
    import functools
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            import google.api_core.exceptions
            # Herken typische Firestore quota/budget errors
            if isinstance(e, (google.api_core.exceptions.ResourceExhausted, google.api_core.exceptions.PermissionDenied)) or 'quota' in str(e).lower() or 'budget' in str(e).lower():
                raise FirestoreUnavailable("Database niet bereikbaar: mogelijk budgetlimiet bereikt.", details=str(e))
            raise FirestoreUnavailable("Database niet bereikbaar.", details=str(e))
    return functools.wraps(func)(wrapper)

# --- OFFLINE STATUS & DIAGNOSTICS ---
OFFLINE_MODE = False
LAST_FALLBACK_ERROR = None

def set_offline_mode(value: bool):
    global OFFLINE_MODE
    OFFLINE_MODE = bool(value)

def is_offline():
    return OFFLINE_MODE

def get_last_fallback_error():
    return LAST_FALLBACK_ERROR

def get_google_creds(scopes=None):
    """Centrale functie om Google credentials op te halen uit secrets of lokaal bestand."""
    # 1. Probeer Streamlit Secrets (Cloud)
    try:
        if hasattr(st, 'secrets'):
            creds_data = st.secrets.get("firestore_credentials")
            if creds_data:
                key_dict = json.loads(json.dumps(dict(creds_data)))
                if scopes:
                    return service_account.Credentials.from_service_account_info(key_dict, scopes=scopes)
                return service_account.Credentials.from_service_account_info(key_dict)
    except Exception:
        pass

    # 2. Probeer lokaal bestand (Dev)
    key_path = "firestore-key.json"
    if os.path.exists(key_path):
        if scopes:
            return service_account.Credentials.from_service_account_file(key_path, scopes=scopes)
        return service_account.Credentials.from_service_account_file(key_path)
    
    return None

def _read_gsheet_fallback(sheet_name):
    """Leest data uit Google Sheets als Firestore offline is of geen data geeft."""
    global LAST_FALLBACK_ERROR
    try:
        import gspread
        creds = get_google_creds(scopes=GS_SCOPES)
        if not creds:
            LAST_FALLBACK_ERROR = "Geen Google credentials gevonden voor GSheet fallback."
            return pd.DataFrame()
        
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)
        worksheet = sh.worksheet(sheet_name)
        
        all_values = worksheet.get_all_values()
        if not all_values or len(all_values) < 1:
            return pd.DataFrame()
            
        headers = [h.strip() for h in all_values[0]]
        if len(all_values) < 2:
            return pd.DataFrame(columns=headers)
            
        rows = all_values[1:]
        data_dicts = []
        for row in rows:
            if not any(row): continue
            if len(row) < len(headers):
                row.extend([''] * (len(headers) - len(row)))
            elif len(row) > len(headers):
                row = row[:len(headers)]
            data_dicts.append(dict(zip(headers, row)))
            
        df = pd.DataFrame(data_dicts)
        
        if not df.empty:
            numeric_cols = ['rating', 'thuis_score', 'uit_score', 
                            'klinkers_thuis_1', 'klinkers_thuis_2', 
                            'klinkers_uit_1', 'klinkers_uit_2',
                            'Score Thuis', 'Score Uit']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            ts_cols = ['timestamp', 'Timestamp']
            for col in ts_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')

            print(f"[GSHEET FALLBACK] Succesvol {len(df)} rijen gelezen uit tab '{sheet_name}'")
            set_offline_mode(True)
            LAST_FALLBACK_ERROR = None # Reset error bij succes
        return df
    except Exception as e:
        LAST_FALLBACK_ERROR = str(e)
        print(f"[GSHEET FALLBACK] Fout bij lezen van {sheet_name}: {e}")
        return pd.DataFrame()

# --- HULPFUNCTIE: Cache volledig legen ---
def clear_all_caches():
    """Leeg alle relevante Streamlit caches na mutaties."""
    try:
        st.cache_data.clear()
    except Exception:
        pass

# --- HULPFUNCTIE: Timestamp normalisatie ---
def normalize_timestamp_series(ts_series):
    """Zet een pandas Series met timestamps om naar tz-naive UTC."""
    import pandas as pd
    if not pd.api.types.is_datetime64_any_dtype(ts_series):
        return ts_series
    try:
        if hasattr(ts_series.dt, 'tz') and ts_series.dt.tz is not None:
            return ts_series.dt.tz_convert('UTC').dt.tz_localize(None)
        else:
            return ts_series.dt.tz_localize(None)
    except (TypeError, ValueError):
        return ts_series

# FIRESTORE INITIALISATIE
@st.cache_resource
def initialize_firestore():
    """Maakt verbinding met Firestore."""
    creds = get_google_creds()
    if not creds:
        raise ValueError("Geen Google credentials gevonden (firestore-key.json of st.secrets)")
    db = google.cloud.firestore.Client(credentials=creds)
    return db

db = initialize_firestore()

# Referenties
players_ref = db.collection('spelers')
matches_ref = db.collection('uitslag')
elo_ref = db.collection('elo')
requests_ref = db.collection('requests')

# DATA LEESFUNCTIES
@handle_firestore_exceptions
@st.cache_data
def get_players():
    """Haalt alle spelers op."""
    try:
        spelers_docs = players_ref.stream()
        players_list = []
        for doc in spelers_docs:
            d = doc.to_dict()
            d['speler_id'] = doc.id
            if 'rating' not in d: d['rating'] = 1000
            players_list.append(d)
        
        if not players_list:
            return _read_gsheet_fallback("Spelers")
            
        set_offline_mode(False)
        return pd.DataFrame(players_list)
    except Exception:
        return _read_gsheet_fallback("Spelers")

@handle_firestore_exceptions
@st.cache_data
def get_matches(start_ts=None, end_ts=None):
    """Haalt wedstrijden op."""
    try:
        query = matches_ref.order_by("timestamp", direction=google.cloud.firestore.Query.DESCENDING)
        if start_ts and end_ts:
            query = matches_ref.where(filter=FieldFilter('timestamp', '>=', pd.to_datetime(start_ts))).where(filter=FieldFilter('timestamp', '<=', pd.to_datetime(end_ts)))
        
        matches_docs = query.stream()
        matches = []
        for doc in matches_docs:
            d = doc.to_dict()
            d['match_id'] = doc.id
            matches.append(d)
        
        if not matches:
             df = _read_gsheet_fallback("Wedstrijden")
        else:
            df = pd.DataFrame(matches)

        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df['timestamp'] = normalize_timestamp_series(df['timestamp'])
        
        if matches:
            set_offline_mode(False)
        return df
    except Exception:
        df = _read_gsheet_fallback("Wedstrijden")
        if not df.empty and 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        return df

@handle_firestore_exceptions
@st.cache_data
def get_elo_logs():
    """Haalt de ELO logs op."""
    try:
        elo_docs = elo_ref.order_by("timestamp", direction=google.cloud.firestore.Query.DESCENDING).stream()
        elos = [doc.to_dict() for doc in elo_docs]
        
        if not elos:
            df = _read_gsheet_fallback("ELO_Logs")
        else:
            df = pd.DataFrame(elos)

        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df['timestamp'] = normalize_timestamp_series(df['timestamp'])
        
        if elos:
            set_offline_mode(False)
        return df
    except Exception:
        df = _read_gsheet_fallback("ELO_Logs")
        if not df.empty and 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        return df

@handle_firestore_exceptions
@st.cache_data
def get_requests():
    """Haalt verzoeken op."""
    try:
        docs = requests_ref.order_by("Timestamp", direction=google.cloud.firestore.Query.DESCENDING).stream()
        req_list = [doc.to_dict() for doc in docs]
        if not req_list:
            return _read_gsheet_fallback("Verzoeken")
        
        set_offline_mode(False)
        return pd.DataFrame(req_list)
    except Exception:
        return _read_gsheet_fallback("Verzoeken")

@handle_firestore_exceptions
@st.cache_data
def get_beheer_log():
    """Haalt alle beheer-log entries op uit Firestore."""
    try:
        beheer_docs = db.collection('beheer_log').order_by("timestamp", direction=google.cloud.firestore.Query.DESCENDING).stream()
        df = pd.DataFrame([doc.to_dict() for doc in beheer_docs])
        if not df.empty and 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df['timestamp'] = normalize_timestamp_series(df['timestamp'])
        set_offline_mode(False)
        return df
    except Exception:
        set_offline_mode(True)
        return pd.DataFrame()

@handle_firestore_exceptions
@st.cache_data
def get_elo_history(_ttl, speler_naam):
    """Haalt de ELO geschiedenis voor een specifieke speler op."""
    try:
        elo_query = elo_ref.where(filter=FieldFilter('speler_naam', '==', speler_naam)).order_by("timestamp", direction=google.cloud.firestore.Query.ASCENDING)
        history_docs = elo_query.stream()
        history = [doc.to_dict() for doc in history_docs]
        
        if not history:
            df = _read_gsheet_fallback("ELO_Logs")
            if not df.empty and 'speler_naam' in df.columns:
                df = df[df['speler_naam'] == speler_naam]
        else:
            df = pd.DataFrame(history)

        if not df.empty and 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df['timestamp'] = normalize_timestamp_series(df['timestamp'])
        
        if history:
            set_offline_mode(False)
        return df
    except Exception:
        set_offline_mode(True)
        return pd.DataFrame()

@handle_firestore_exceptions
@st.cache_data
def get_seasons():
    """Bepaalt seizoenen automatisch op basis van de data."""
    matches_df = get_matches()
    if matches_df.empty or 'timestamp' not in matches_df.columns:
        return pd.DataFrame()

    from datetime import date, timedelta, datetime
    def get_prinsjesdag(year):
        sept = date(year, 9, 1)
        first_tue = sept + timedelta(days=(1 - sept.weekday()) % 7)
        return datetime.combine(first_tue + timedelta(days=14), datetime.min.time())

    def get_march15(year):
        return datetime(year, 3, 15)

    min_year = int(matches_df['timestamp'].dt.year.min())
    max_year = int(matches_df['timestamp'].dt.year.max())

    seizoenen = []
    for y in range(min_year - 1, max_year + 2):
        s1, e1 = get_march15(y), get_prinsjesdag(y) - timedelta(seconds=1)
        m1 = (matches_df['timestamp'] >= s1) & (matches_df['timestamp'] <= e1)
        seizoenen.append({'seizoen_naam': f"CJ {y} Zomer", 'start_datum': s1, 'eind_datum': e1, 'aantal_wedstrijden': int(m1.sum())})
        s2, e2 = get_prinsjesdag(y), get_march15(y+1) - timedelta(seconds=1)
        m2 = (matches_df['timestamp'] >= s2) & (matches_df['timestamp'] <= e2)
        seizoenen.append({'seizoen_naam': f"CJ {y} Winter", 'start_datum': s2, 'eind_datum': e2, 'aantal_wedstrijden': int(m2.sum())})

    df_s = pd.DataFrame([s for s in seizoenen if s['aantal_wedstrijden'] > 0 or (s['start_datum'] <= datetime.now() <= s['eind_datum'])])
    return df_s.sort_values('start_datum').reset_index(drop=True)

# DATA SCHRIJFFUNCTIES
def add_player(name, start_elo):
    try:
        if players_ref.where(filter=FieldFilter('speler_naam', '==', name)).limit(1).get():
            return f"Error: Speler '{name}' bestaat al."
        batch = db.batch()
        batch.set(players_ref.document(), {'speler_naam': name, 'rating': start_elo})
        batch.set(elo_ref.document(), {'speler_naam': name, 'rating': start_elo, 'timestamp': SERVER_TIMESTAMP})
        batch.commit()
        clear_all_caches()
        return "Success"
    except Exception as e:
        return f"Error: {e}"

def add_request(text):
    try:
        requests_ref.add({'Verzoek': text, 'Timestamp': SERVER_TIMESTAMP})
        clear_all_caches()
        return "Success"
    except Exception as e:
        return f"Error: {e}"

@handle_firestore_exceptions
def add_match_and_update_elo(match_data, elo_updates):
    batch = db.batch()
    try:
        ts = match_data.get('timestamp') or pd.Timestamp.now()
        new_match_ref = matches_ref.document()
        match_id = new_match_ref.id
        batch.set(new_match_ref, {**match_data, 'timestamp': ts, 'match_id': match_id})

        for naam, elo in elo_updates:
            batch.set(elo_ref.document(), {'speler_naam': naam, 'rating': elo, 'timestamp': ts, 'match_id': match_id})
            p_docs = players_ref.where(filter=FieldFilter('speler_naam', '==', naam)).limit(1).get()
            if p_docs: batch.update(p_docs[0].reference, {'rating': elo})

        batch.commit()
        clear_all_caches()
        return True
    except Exception as e:
        print(f"Batch error: {e}")
        return False

# Beheer functies
def delete_match_by_id(mid):
    try:
        matches_ref.document(mid).delete()
        clear_all_caches()
        return True
    except: return False

def update_match(mid, data):
    try:
        matches_ref.document(mid).update(data)
        clear_all_caches()
        return True
    except: return False

def delete_player_by_id(player_id):
    """Verwijdert een speler en al zijn ELO-geschiedenis."""
    batch = db.batch()
    try:
        player_doc = players_ref.document(player_id).get()
        if not player_doc.exists: return True
        player_name = player_doc.to_dict().get('speler_naam')
        batch.delete(players_ref.document(player_id))
        if player_name:
            elo_docs = elo_ref.where(filter=FieldFilter('speler_naam', '==', player_name)).stream()
            for doc in elo_docs: batch.delete(doc.reference)
        batch.commit()
        clear_all_caches()
        return True
    except Exception as e:
        print(f"Fout bij verwijderen: {e}")
        return False

def recalculate_elos_for_season(start_date, end_date):
    """Herberekent alle ELO scores voor een seizoen."""
    try:
        from utils.utils_new_elo import calculate_new_elo
        if isinstance(start_date, pd.Timestamp): start_date = start_date.date()
        if isinstance(end_date, pd.Timestamp): end_date = end_date.date()
        
        all_matches = get_matches().sort_values('timestamp', ascending=True)
        players_df = get_players()
        mask = (all_matches['timestamp'].dt.date >= start_date) & (all_matches['timestamp'].dt.date <= end_date)
        season_matches = all_matches[mask]
        
        player_elos = {name: 1000 for name in players_df['speler_naam']}
        batch = db.batch()
        old_elos = elo_ref.where(filter=FieldFilter('timestamp', '>=', pd.Timestamp(start_date))).where(filter=FieldFilter('timestamp', '<=', pd.Timestamp(end_date))).stream()
        for doc in old_elos: batch.delete(doc.reference)
        batch.commit()
        
        batch = db.batch()
        c = 0
        for _, match in season_matches.iterrows():
            m_dict = {
                "Thuis_1": match['thuis_1'], "Thuis_2": match['thuis_2'],
                "Uit_1": match['uit_1'], "Uit_2": match['uit_2'],
                "Thuis_score": match['thuis_score'], "Uit_score": match['uit_score']
            }
            m_players = {m_dict[k] for k in ["Thuis_1", "Thuis_2", "Uit_1", "Uit_2"] if m_dict[k]}
            all_ratings = {p: [player_elos.get(p, 1000)] for p in m_players}
            new_df = calculate_new_elo(m_dict, all_ratings)
            for _, row in new_df.iterrows():
                p, r = row['Speler'], row['ELO']
                player_elos[p] = r
                batch.set(elo_ref.document(), {'speler_naam': p, 'rating': r, 'timestamp': match['timestamp'], 'match_id': match['match_id']})
                c += 1
                if c >= 400:
                    batch.commit()
                    batch = db.batch()
                    c = 0
        if c > 0: batch.commit()
        clear_all_caches()
        return True
    except Exception as e:
        print(f"Recalc error: {e}")
        return False

def delete_match_with_elo_recalculation(match_id):
    """Verwijdert match en herbereken seizoen."""
    try:
        doc = matches_ref.document(match_id).get()
        if not doc.exists: return True
        ts = doc.to_dict().get('timestamp')
        matches_ref.document(match_id).delete()
        seasons = get_seasons()
        s_row = seasons[(seasons['start_datum'] <= ts) & (seasons['eind_datum'] >= ts)]
        if not s_row.empty:
            recalculate_elos_for_season(s_row.iloc[0]['start_datum'], s_row.iloc[0]['eind_datum'])
        clear_all_caches()
        return True
    except: return False
