# --- Failsafe: Firestore bereikbaarheidscheck en custom exception ---
import streamlit as st
import os
import google.cloud.firestore
from google.oauth2 import service_account
import json
import pandas as pd
import uuid
import traceback
from datetime import datetime
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

# --- FIRESTORE LOGGING ---
import collections

@st.cache_resource
def get_log_history():
    return collections.deque(maxlen=1000)

def log_firestore_op(op_type, collection, action, count=1):
    """Logt Firestore operaties naar de console, inclusief het IP-adres van de gebruiker (indien beschikbaar)."""
    try:
        from datetime import datetime
        import streamlit as st
        ip = "Unknown IP"
        try:
            if hasattr(st, 'context') and hasattr(st.context, 'headers'):
                headers = st.context.headers
                ip = headers.get("X-Forwarded-For", headers.get("X-Real-IP", "Unknown IP"))
            else:
                try:
                    from streamlit.web.server.websocket_headers import _get_websocket_headers
                    headers = _get_websocket_headers()
                    if headers:
                        ip = headers.get("X-Forwarded-For", headers.get("X-Real-IP", "Unknown IP"))
                except:
                    pass
        except:
            pass
            
        if ip != "Unknown IP":
            ip = ip.split(',')[0].strip()
            
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_str = f"[{ts}] [FIRESTORE] {op_type.upper():<5} | Coll: {collection:<12} | Action: {action:<22} | Count: {count:<4} | IP: {ip}"
        print(log_str)
        get_log_history().appendleft(log_str)
    except Exception as e:
        print(f"[FIRESTORE LOG ERROR] {e}")

# Google Sheet ID voor fallback
DEFAULT_SHEET_ID = "1cCiNoYfro9SqS8qIjEKT8prsAvAA7wowvhzhh2ljHnA"
SHEET_ID = st.secrets.get("GSHEET_ID", DEFAULT_SHEET_ID)
GS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# Seizoen Configuratie
SEASON_TRANSITION_MONTH = 3
SEASON_TRANSITION_DAY = 15
PRINSJESDAG_OFFSET_DAYS = 14 # Prinsjesdag is 3e dinsdag van september (7 + 14 = 21 max)

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

    key_path = "firestore-key.json"
    if os.path.exists(key_path):
        if scopes:
            return service_account.Credentials.from_service_account_file(key_path, scopes=scopes)
        return service_account.Credentials.from_service_account_file(key_path)
    return None

@st.cache_resource
def _get_gsheet_client():
    """Maakt een gecachte verbinding met Google Sheets."""
    try:
        import gspread
        creds = get_google_creds(scopes=GS_SCOPES)
        if not creds: return None
        return gspread.authorize(creds)
    except Exception as e:
        print(f"[GSHEET AUTH] Fout bij authenticatie: {e}")
        return None

@st.cache_resource
def _get_gsheet_workbook():
    """Opent het Google Sheets werkboek en cacht dit."""
    client = _get_gsheet_client()
    if not client: return None
    try:
        # Extra check om te voorkomen dat we de API blijven hameren bij 429
        return client.open_by_key(SHEET_ID)
    except Exception as e:
        if "429" in str(e):
            print(f"[GSHEET QUOTA] Te veel aanvragen. Wacht even met refreshen.")
        else:
            print(f"[GSHEET OPEN] Fout bij openen van workbook: {e}")
        return None

@st.cache_data(ttl=3600)
def _fetch_all_gsheet_data():
    """Haalt alle relevante data uit Google Sheets in één keer op (indien mogelijk per sheet)."""
    sh = _get_gsheet_workbook()
    if not sh: return {}
    
    all_data = {}
    sheets_to_load = ["Wedstrijden", "Spelers", "ELO_Logs", "Verzoeken", "Beheer_Log"]
    for sheet_name in sheets_to_load:
        try:
            worksheet = sh.worksheet(sheet_name)
            all_data[sheet_name] = worksheet.get_all_values()
        except Exception:
            continue
    return all_data

@st.cache_data(ttl=300) # Kortere cache voor individuele sheets via de batch fetch
def _read_gsheet_fallback(sheet_name):
    """Leest data uit Google Sheets als Firestore offline is of geen data geeft."""
    global LAST_FALLBACK_ERROR
    try:
        # Gebruik de batch fetch om API calls te minimaliseren
        all_gs_data = _fetch_all_gsheet_data()
        
        if not all_gs_data or sheet_name not in all_gs_data:
            # Fallback naar directe call als batch leeg is (mocht het een andere sheet zijn)
            if not all_gs_data:
                sh = _get_gsheet_workbook()
                if not sh: 
                    LAST_FALLBACK_ERROR = "Geen Google credentials gevonden voor GSheet fallback."
                    return pd.DataFrame()
                try:
                    worksheet = sh.worksheet(sheet_name)
                    all_values = worksheet.get_all_values()
                except:
                    return pd.DataFrame()
            else:
                return pd.DataFrame()
        else:
            all_values = all_gs_data[sheet_name]

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
                row.extend([''] * (len(headers) - row))
            elif len(row) > len(headers):
                row = row[:len(headers)]
            data_dicts.append(dict(zip(headers, row)))
            
        df = pd.DataFrame(data_dicts)
        
        # Normalize column names to lowercase for consistency
        df.columns = [c.lower() for c in df.columns]
        
        if not df.empty:
            numeric_cols = ['rating', 'thuis_score', 'uit_score', 
                            'klinkers_thuis_1', 'klinkers_thuis_2', 
                            'klinkers_uit_1', 'klinkers_uit_2',
                            'score thuis', 'score uit']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            ts_cols = ['timestamp']
            for col in ts_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')

            set_offline_mode(True)
            LAST_FALLBACK_ERROR = None
        return df
    except Exception as e:
        LAST_FALLBACK_ERROR = str(e)
        print(f"[GSHEET FALLBACK] Fout bij lezen van {sheet_name}: {e}")
        return pd.DataFrame()

def _write_gsheet_records(sheet_name, data_dicts):
    """Schrijft meerdere records naar Google Sheets."""
    if not data_dicts: return True
    try:
        sh = _get_gsheet_workbook()
        if not sh: return False
        
        try:
            worksheet = sh.worksheet(sheet_name)
        except Exception:
            import gspread
            worksheet = sh.add_worksheet(title=sheet_name, rows="100", cols="20")
        
        # Ensure headers exist
        headers = worksheet.row_values(1)
        if not headers:
            headers = list(data_dicts[0].keys())
            worksheet.append_row(headers)
        
        rows = []
        for d in data_dicts:
            row = []
            for h in headers:
                val = d.get(h, "")
                if isinstance(val, (pd.Timestamp, datetime)):
                    val = val.strftime('%Y-%m-%d %H:%M:%S')
                row.append(val)
            rows.append(row)
        
        worksheet.append_rows(rows)
        return True
    except Exception as e:
        print(f"[GSHEET BATCH WRITE] Fout bij schrijven naar {sheet_name}: {e}")
        return False

def _write_gsheet_record(sheet_name, data_dict):
    return _write_gsheet_records(sheet_name, [data_dict])

def _delete_gsheet_record(sheet_name, key_col, value):
    """Verwijdert een record uit Google Sheets."""
    try:
        sh = _get_gsheet_workbook()
        if not sh: return False
        
        try:
            worksheet = sh.worksheet(sheet_name)
        except Exception:
            return True
            
        all_values = worksheet.get_all_values()
        if not all_values: return True
        
        headers = all_values[0]
        if key_col not in headers: return False
        
        idx = headers.index(key_col)
        rows_to_keep = [all_values[0]]
        for row in all_values[1:]:
            if len(row) > idx and row[idx] != str(value):
                rows_to_keep.append(row)
        
        if len(rows_to_keep) < len(all_values):
            worksheet.clear()
            worksheet.update('A1', rows_to_keep)
        return True
    except Exception as e:
        print(f"[GSHEET DELETE] Fout bij verwijderen uit {sheet_name}: {e}")
        return False

@st.cache_resource
def get_sync_throttle():
    """Globale sync throttle."""
    return {"last_sync": datetime.min}

def reconcile_data_sources():
    """Synchroniseert data tussen Firestore en Google Sheets op een efficiënte manier."""
    try:
        # Throttling: Maximaal eens per 15 minuten syncen (Globaal)
        now = datetime.now()
        throttle = get_sync_throttle()
        if (now - throttle["last_sync"]).total_seconds() < 900:
            return
        throttle["last_sync"] = now

        print("[SYNC] Bezig met synchronisatie...")
        
        # 1. Sync Wedstrijden & ELO logs
        try:
            fs_matches = list(matches_ref.select(['match_id']).stream())
            fs_ids = {doc.to_dict().get('match_id') for doc in fs_matches if doc.to_dict().get('match_id')}
        except Exception:
            print("[SYNC] Firestore niet bereikbaar voor sync.")
            return

        gs_df = _read_gsheet_fallback.__wrapped__("Wedstrijden") if hasattr(_read_gsheet_fallback, "__wrapped__") else _read_gsheet_fallback("Wedstrijden")
        gs_ids = set(gs_df['match_id'].dropna().unique()) if not gs_df.empty else set()

        # A. GSheet -> Firestore (Offline recovery)
        missing_in_fs = gs_ids - fs_ids
        if missing_in_fs:
            print(f"[SYNC] {len(missing_in_fs)} nieuwe wedstrijden in GSheet gevonden.")
            elo_gs = _read_gsheet_fallback.__wrapped__("ELO_Logs") if hasattr(_read_gsheet_fallback, "__wrapped__") else _read_gsheet_fallback("ELO_Logs")
            batch = db.batch()
            count = 0
            for mid in missing_in_fs:
                m_row = gs_df[gs_df['match_id'] == mid].iloc[0].to_dict()
                batch.set(matches_ref.document(mid), m_row)
                count += 1
                if not elo_gs.empty:
                    for _, erow in elo_gs[elo_gs['match_id'] == mid].iterrows():
                        batch.set(elo_ref.document(), erow.to_dict())
                        count += 1
                if count >= 400:
                    batch.commit()
                    batch = db.batch()
                    count = 0
            if count > 0: batch.commit()

        # B. Firestore -> GSheet (Backup update)
        missing_in_gs = fs_ids - gs_ids
        if missing_in_gs:
            print(f"[SYNC] {len(missing_in_gs)} nieuwe wedstrijden in Firestore gevonden.")
            m_records = []
            e_records = []
            for mid in missing_in_gs:
                m_doc = matches_ref.document(mid).get()
                if m_doc.exists:
                    m_records.append({**m_doc.to_dict(), 'match_id': mid})
                    elos = elo_ref.where(filter=FieldFilter('match_id', '==', mid)).stream()
                    for edoc in elos: e_records.append(edoc.to_dict())
            if m_records: _write_gsheet_records("Wedstrijden", m_records)
            if e_records: _write_gsheet_records("ELO_Logs", e_records)

        # 2. Sync Spelers
        fs_players = {p.id: p.to_dict() for p in players_ref.stream()}
        gs_players_df = _read_gsheet_fallback.__wrapped__("Spelers") if hasattr(_read_gsheet_fallback, "__wrapped__") else _read_gsheet_fallback("Spelers")
        gs_p_ids = set(gs_players_df['speler_id'].unique()) if not gs_players_df.empty else set()
        
        # Firestore -> GSheet Backup (alleen missende spelers)
        missing_p_in_gs = set(fs_players.keys()) - gs_p_ids
        if missing_p_in_gs:
            p_to_add = [{**fs_players[pid], 'speler_id': pid} for pid in missing_p_in_gs]
            _write_gsheet_records("Spelers", p_to_add)

        print("[SYNC] Synchronisatie voltooid.")
        clear_all_caches()
    except Exception as e:
        print(f"[SYNC] Fout tijdens synchronisatie: {e}")

# --- HULPFUNCTIE: Cache volledig legen ---
def clear_all_caches(only_players=False, only_matches=False, only_elo=False, only_requests=False):
    """
    Leegt specifieke Streamlit caches. Omdat data nu via real-time listeners wordt bijgehouden, 
    is harde invalidatie van data-query functies niet meer nodig (de 'last_updated' timestamp regelt dit).
    """
    try:
        if only_matches:
            if hasattr(get_seasons, "clear"):
                get_seasons.clear()
    except Exception as e:
        print(f"Fout bij cache invalidatie: {e}")

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

# --- FIRESTORE LISTENERS ---
@st.cache_resource
def init_firestore_listeners():
    import threading
    import time
    
    try:
        print("[INIT] Loading historical data from Google Sheets to save Firebase quota...")
        gsheet_data = _fetch_all_gsheet_data()
        
        def load_sheet(sheet_name, id_field=None):
            if sheet_name not in gsheet_data: return {}
            all_values = gsheet_data[sheet_name]
            if not all_values or len(all_values) < 2: return {}
            headers = all_values[0]
            res = {}
            import uuid
            for row in all_values[1:]:
                d = dict(zip(headers, row))
                if id_field and id_field in d and d[id_field]:
                    doc_id = d[id_field]
                else:
                    if 'match_id' in d and 'speler_naam' in d:
                        doc_id = f"{d['match_id']}_{d['speler_naam']}"
                    else:
                        doc_id = str(uuid.uuid4())
                res[doc_id] = d
            return res

        store_matches = load_sheet("Wedstrijden", "match_id")
        store_elo = load_sheet("ELO_Logs", None)
        store_players = load_sheet("Spelers", "speler_id")
    except Exception as e:
        print(f"[INIT] GSheet load failed: {e}")
        store_matches = {}
        store_elo = {}
        store_players = {}

    store = {
        "matches": store_matches,
        "elo": store_elo,
        "players": store_players,
        "requests": {},
        "beheer_log": {},
        "watchers": [],
        "last_updated": {
            "matches": time.time(),
            "elo": time.time(),
            "players": time.time(),
            "requests": 0,
            "beheer_log": 0
        }
    }

    events = {
        "matches": threading.Event(),
        "elo": threading.Event(),
        "players": threading.Event(),
        "requests": threading.Event(),
        "beheer_log": threading.Event()
    }
    
    def make_callback(collection_name, id_field=None):
        def callback(doc_snapshot, changes, read_time):
            for change in changes:
                doc_id = change.document.id
                if change.type.name in ('ADDED', 'MODIFIED'):
                    d = change.document.to_dict()
                    if id_field:
                        d[id_field] = doc_id
                    store[collection_name][doc_id] = d
                elif change.type.name == 'REMOVED':
                    store[collection_name].pop(doc_id, None)
            store["last_updated"][collection_name] = time.time()
            events[collection_name].set()
        return callback

    if not is_offline():
        try:
            from datetime import datetime, timedelta
            import pytz
            
            # Fetch only the last 7 days from Firestore to drastically reduce read quota
            last_week = datetime.now(pytz.utc) - timedelta(days=7)
            
            recent_matches_query = matches_ref.where(filter=FieldFilter('timestamp', '>=', last_week))
            recent_elo_query = elo_ref.where(filter=FieldFilter('timestamp', '>=', last_week))
            
            store["watchers"].append(recent_matches_query.on_snapshot(make_callback("matches", "match_id")))
            store["watchers"].append(recent_elo_query.on_snapshot(make_callback("elo", None)))
            store["watchers"].append(players_ref.on_snapshot(make_callback("players", "speler_id")))
            store["watchers"].append(requests_ref.on_snapshot(make_callback("requests", None)))
            store["watchers"].append(db.collection('beheer_log').on_snapshot(make_callback("beheer_log", None)))
            
            # Wacht op initiële snapshot zodat de app niet met lege data start
            events["matches"].wait(timeout=2)
            events["elo"].wait(timeout=2)
            events["players"].wait(timeout=2)
            log_firestore_op("READ", "all", "init_listeners", "~RECENT")
        except Exception as e:
            print(f"Error initializing firestore listeners: {e}")
            
    return store

# Kolomvolgorde voor uitslagen
MATCH_COLUMNS = [
    'match_id', 'timestamp', 'thuis_1', 'thuis_2', 'thuis_score',
    'uit_1', 'uit_2', 'uit_score', 'klinkers_thuis_1',
    'klinkers_thuis_2', 'klinkers_uit_1', 'klinkers_uit_2'
]

# DATA LEESFUNCTIES
@st.cache_data
def _build_players_df(last_updated):
    store = init_firestore_listeners()
    players_list = list(store["players"].values())
    if not players_list:
        return _read_gsheet_fallback("Spelers")
    df = pd.DataFrame(players_list)
    if 'rating' not in df.columns:
        df['rating'] = 1000
    df['rating'] = df['rating'].astype(str).str.replace(',', '.')
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(1000)
    set_offline_mode(False)
    return df

@handle_firestore_exceptions
def get_players():
    """Haalt alle spelers op."""
    try:
        store = init_firestore_listeners()
        return _build_players_df(store["last_updated"]["players"])
    except Exception:
        return _read_gsheet_fallback("Spelers")

@st.cache_data
def _build_matches_df(last_updated):
    store = init_firestore_listeners()
    matches = list(store["matches"].values())
    if not matches:
        df = _read_gsheet_fallback("Wedstrijden")
        if not df.empty and 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        return df

    df = pd.DataFrame(matches)
    
    # Force score and klinkers to be integers (handling string floats or empty strings from GSheets)
    numeric_cols = ['thuis_score', 'uit_score', 'klinkers_thuis_1', 'klinkers_thuis_2', 'klinkers_uit_1', 'klinkers_uit_2']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df['timestamp'] = normalize_timestamp_series(df['timestamp'])
    
    # Enforce column order
    existing_cols = [c for c in MATCH_COLUMNS if c in df.columns]
    other_cols = [c for c in df.columns if c not in MATCH_COLUMNS]
    df = df[existing_cols + other_cols]
    
    df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)
    set_offline_mode(False)
    return df

@handle_firestore_exceptions
def get_matches(start_ts=None, end_ts=None):
    """Haalt wedstrijden op."""
    try:
        store = init_firestore_listeners()
        df = _build_matches_df(store["last_updated"]["matches"])
        
        if start_ts and end_ts:
            start_pd = pd.to_datetime(start_ts)
            end_pd = pd.to_datetime(end_ts)
            if start_pd.tzinfo is not None and df['timestamp'].dt.tz is None:
                start_pd = start_pd.tz_localize(None)
            if end_pd.tzinfo is not None and df['timestamp'].dt.tz is None:
                end_pd = end_pd.tz_localize(None)
            df = df[(df['timestamp'] >= start_pd) & (df['timestamp'] <= end_pd)]
            
        return df
    except Exception:
        df = _read_gsheet_fallback("Wedstrijden")
        if not df.empty and 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        return df

@st.cache_data(show_spinner=False)
def _build_elo_logs_df(last_updated):
    store = init_firestore_listeners()
    elos = list(store["elo"].values())
    if not elos:
        df = _read_gsheet_fallback("ELO_Logs")
        if not df.empty and 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        return df

    df = pd.DataFrame(elos)
    if 'rating' in df.columns:
        df['rating'] = df['rating'].astype(str).str.replace(',', '.')
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(1000)
        
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df['timestamp'] = normalize_timestamp_series(df['timestamp'])
    
    # Verwijder duplicaten (overlap tussen GSheet history en Firestore on_snapshot)
    if not df.empty and 'match_id' in df.columns and 'speler_naam' in df.columns:
        df = df.drop_duplicates(subset=['match_id', 'speler_naam'], keep='last')
        
    df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)
    set_offline_mode(False)
    return df

@handle_firestore_exceptions
def get_elo_logs():
    """Haalt de ELO logs op."""
    try:
        store = init_firestore_listeners()
        return _build_elo_logs_df(store["last_updated"]["elo"])
    except Exception:
        df = _read_gsheet_fallback("ELO_Logs")
        if not df.empty and 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        return df

@st.cache_data
def _build_requests_df(last_updated):
    store = init_firestore_listeners()
    req_list = list(store["requests"].values())
    for d in req_list:
        if 'Timestamp' in d:
            d['timestamp'] = d.pop('Timestamp')
            
    if not req_list:
        return _read_gsheet_fallback("Verzoeken")
    
    df = pd.DataFrame(req_list)
    if not df.empty and 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df['timestamp'] = normalize_timestamp_series(df['timestamp'])
        df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)
        
    set_offline_mode(False)
    return df

@handle_firestore_exceptions
def get_requests():
    """Haalt verzoeken op."""
    try:
        store = init_firestore_listeners()
        return _build_requests_df(store["last_updated"]["requests"])
    except Exception:
        return _read_gsheet_fallback("Verzoeken")

@st.cache_data
def _build_beheer_log_df(last_updated):
    store = init_firestore_listeners()
    log_list = list(store["beheer_log"].values())
    if not log_list:
        return _read_gsheet_fallback("Beheer_Log")
    
    df = pd.DataFrame(log_list)
    if not df.empty and 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df['timestamp'] = normalize_timestamp_series(df['timestamp'])
        df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)
    
    if not df.empty:
        df.columns = [c.lower() for c in df.columns]
        
    set_offline_mode(False)
    return df

@handle_firestore_exceptions
def get_beheer_log():
    """Haalt alle beheer-log entries op uit Firestore."""
    try:
        store = init_firestore_listeners()
        return _build_beheer_log_df(store["last_updated"]["beheer_log"])
    except Exception:
        return _read_gsheet_fallback("Beheer_Log")

@handle_firestore_exceptions
def get_elo_history(_ttl, speler_naam):
    """Haalt de ELO geschiedenis voor een specifieke speler op."""
    try:
        df = get_elo_logs()
        if not df.empty and 'speler_naam' in df.columns:
            df = df[df['speler_naam'] == speler_naam]
            # Sorteer oplopend voor de history grafiek
            df = df.sort_values("timestamp", ascending=True).reset_index(drop=True)
            return df
        return pd.DataFrame()
    except Exception:
        set_offline_mode(True)
        return pd.DataFrame()

@st.cache_data
def get_seasons():
    """Bepaalt seizoenen automatisch op basis van vaste datums, zonder data te laden."""
    from datetime import date, timedelta, datetime

    def get_prinsjesdag(year):
        sept = date(year, 9, 1)
        first_tue = sept + timedelta(days=(1 - sept.weekday()) % 7)
        return datetime.combine(first_tue + timedelta(days=PRINSJESDAG_OFFSET_DAYS), datetime.min.time())

    def get_march15(year):
        return datetime(year, SEASON_TRANSITION_MONTH, SEASON_TRANSITION_DAY)

    # Vaste jaren om te voorkomen dat de hele match historie geladen moet worden
    min_year = 2022 
    max_year = datetime.now().year + 1

    seizoenen = []
    for y in range(min_year, max_year + 1):
        s1, e1 = get_march15(y), get_prinsjesdag(y) - timedelta(seconds=1)
        seizoenen.append({'seizoen_naam': f"CJ {y} Zomer", 'start_datum': s1, 'eind_datum': e1, 'aantal_wedstrijden': 0})
        
        s2, e2 = get_prinsjesdag(y), get_march15(y+1) - timedelta(seconds=1)
        seizoenen.append({'seizoen_naam': f"CJ {y} Winter", 'start_datum': s2, 'eind_datum': e2, 'aantal_wedstrijden': 0})

    df_s = pd.DataFrame([s for s in seizoenen if s['start_datum'] <= datetime.now()])
    return df_s.sort_values('start_datum').reset_index(drop=True)

# DATA SCHRIJFFUNCTIES
def add_player(name, start_elo):
    log_firestore_op("WRITE", "spelers", "add_player", 1)
    try:
        if players_ref.where(filter=FieldFilter('speler_naam', '==', name)).limit(1).get():
            return f"Error: Speler '{name}' bestaat al."
        batch = db.batch()
        batch.set(players_ref.document(), {'speler_naam': name, 'rating': start_elo})
        batch.set(elo_ref.document(), {'speler_naam': name, 'rating': start_elo, 'timestamp': SERVER_TIMESTAMP})
        batch.commit()
        clear_all_caches(only_players=True)
        return "Success"
    except Exception:
        res = _write_gsheet_record("Spelers", {'speler_naam': name, 'rating': start_elo, 'speler_id': f"OFFLINE_{uuid.uuid4().hex[:8]}"})
        if res:
            clear_all_caches(only_players=True)
            return "Success"
        return "Error: Database offline en GSheet schrijven mislukt."

def add_request(text):
    log_firestore_op("WRITE", "requests", "add_request", 1)
    try:
        requests_ref.add({'Verzoek': text, 'Timestamp': SERVER_TIMESTAMP})
        clear_all_caches(only_requests=True)
        return "Success"
    except Exception:
        res = _write_gsheet_record("Verzoeken", {'Verzoek': text, 'Timestamp': pd.Timestamp.now()})
        if res:
            clear_all_caches(only_requests=True)
            return "Success"
        return "Error: Database offline en GSheet schrijven mislukt."

@handle_firestore_exceptions
def add_match_and_update_elo(match_data, elo_updates):
    log_firestore_op("WRITE", "uitslag", "add_match", 1)
    log_firestore_op("WRITE", "elo", "add_match_elo", len(elo_updates))
    ts = match_data.get('timestamp') or pd.Timestamp.now()
    try:
        batch = db.batch()
        new_match_ref = matches_ref.document()
        match_id = new_match_ref.id
        
        # Geordende dict voor Firestore (Python 3.7+ behoudt volgorde)
        final_match_data = {
            'match_id': match_id,
            'timestamp': ts,
            'thuis_1': match_data.get('thuis_1'),
            'thuis_2': match_data.get('thuis_2'),
            'thuis_score': match_data.get('thuis_score'),
            'uit_1': match_data.get('uit_1'),
            'uit_2': match_data.get('uit_2'),
            'uit_score': match_data.get('uit_score'),
            'klinkers_thuis_1': match_data.get('klinkers_thuis_1', 0),
            'klinkers_thuis_2': match_data.get('klinkers_thuis_2', 0),
            'klinkers_uit_1': match_data.get('klinkers_uit_1', 0),
            'klinkers_uit_2': match_data.get('klinkers_uit_2', 0)
        }
        
        batch.set(new_match_ref, final_match_data)

        for naam, elo in elo_updates:
            batch.set(elo_ref.document(), {'speler_naam': naam, 'rating': elo, 'timestamp': ts, 'match_id': match_id})
            p_docs = players_ref.where(filter=FieldFilter('speler_naam', '==', naam)).limit(1).get()
            if p_docs: batch.update(p_docs[0].reference, {'rating': elo})

        batch.commit()
        clear_all_caches(only_matches=True, only_elo=True)
        return True
    except Exception:
        match_id = f"OFFLINE_{uuid.uuid4().hex[:10]}"
        m_success = _write_gsheet_record("Wedstrijden", {**match_data, 'timestamp': ts, 'match_id': match_id})
        if m_success:
            elo_records = [{'speler_naam': naam, 'rating': elo, 'timestamp': ts, 'match_id': match_id} for naam, elo in elo_updates]
            _write_gsheet_records("ELO_Logs", elo_records)
            clear_all_caches(only_matches=True, only_elo=True)
            return True
        return False

# Beheer functies
def delete_match_by_id(mid):
    log_firestore_op("WRITE", "uitslag", "delete_match", 1)
    log_firestore_op("WRITE", "elo", "delete_match_elo", 4)
    try:
        # Verwijder uit Firestore
        matches_ref.document(mid).delete()
        # Verwijder bijbehorende ELO logs uit Firestore
        elo_docs = elo_ref.where(filter=FieldFilter('match_id', '==', mid)).stream()
        batch = db.batch()
        count = 0
        for doc in elo_docs: 
            batch.delete(doc.reference)
            count += 1
        if count > 0:
            batch.commit()
        
        # Verwijder uit GSheet Backup
        _delete_gsheet_record("Wedstrijden", "match_id", mid)
        _delete_gsheet_record("ELO_Logs", "match_id", mid)
        
        clear_all_caches(only_matches=True, only_elo=True)
        return True
    except Exception as e:
        print(f"Error in delete_match_by_id: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_match(mid, data):
    log_firestore_op("WRITE", "uitslag", "update_match", 1)
    try:
        # Update Firestore
        matches_ref.document(mid).update(data)
        
        # Voor GSheet is update lastiger (delete + re-insert)
        doc = matches_ref.document(mid).get()
        if doc.exists:
            _delete_gsheet_record("Wedstrijden", "match_id", mid)
            _write_gsheet_record("Wedstrijden", {**doc.to_dict(), 'match_id': mid})
            
        clear_all_caches(only_matches=True)
        return True
    except: return False

def delete_player_by_id(player_id):
    """Verwijdert een speler en al zijn ELO-geschiedenis."""
    log_firestore_op("WRITE", "spelers", "delete_player", 1)
    batch = db.batch()
    try:
        player_doc = players_ref.document(player_id).get()
        if not player_doc.exists: return True
        player_name = player_doc.to_dict().get('speler_naam')
        
        # Firestore Deletions
        batch.delete(players_ref.document(player_id))
        if player_name:
            elo_docs = elo_ref.where(filter=FieldFilter('speler_naam', '==', player_name)).stream()
            for doc in elo_docs: batch.delete(doc.reference)
        batch.commit()
        
        # GSheet Deletions
        _delete_gsheet_record("Spelers", "speler_id", player_id)
        if player_name:
            _delete_gsheet_record("ELO_Logs", "speler_naam", player_name)
            
        clear_all_caches(only_players=True, only_elo=True)
        return True
    except Exception as e:
        print(f"Fout bij verwijderen: {e}")
        return False

def import_matches(matches_list):
    """Importeert een lijst met wedstrijden in Firestore."""
    try:
        batch = db.batch()
        added = 0
        duplicates = 0
        
        # Voor duplicaat-check: haal laatste 100 matches op
        existing_matches = get_matches().head(100)
        
        for m in matches_list:
            # Simpele duplicaat-check op basis van spelers en timestamp
            ts = pd.to_datetime(m.get('timestamp'))
            if not existing_matches.empty:
                is_dup = any((existing_matches['thuis_1'] == m.get('thuis_1')) & 
                             (existing_matches['uit_1'] == m.get('uit_1')) & 
                             (existing_matches['timestamp'] == ts))
                if is_dup:
                    duplicates += 1
                    continue
            
            new_ref = matches_ref.document()
            batch.set(new_ref, {**m, 'timestamp': ts, 'match_id': new_ref.id})
            added += 1
            if added % 400 == 0:
                batch.commit()
                batch = db.batch()
        
        batch.commit()
        clear_all_caches(only_matches=True)
        return added, duplicates
    except Exception as e:
        print(f"Import matches error: {e}")
        return 0, 0

def import_players(players_list):
    """Importeert een lijst met spelers in Firestore."""
    try:
        batch = db.batch()
        added = 0
        duplicates = 0
        
        existing_players = set(get_players()['speler_naam'].tolist())
        
        for p in players_list:
            name = p.get('speler_naam')
            if name in existing_players:
                duplicates += 1
                continue
            
            batch.set(players_ref.document(), p)
            added += 1
            if added % 400 == 0:
                batch.commit()
                batch = db.batch()
        
        batch.commit()
        clear_all_caches(only_players=True)
        return added, duplicates
    except Exception as e:
        print(f"Import players error: {e}")
        return 0, 0

def reset_all_elos(timestamp=None):
    """Reset alle ELO scores naar 1000 voor alle spelers."""
    try:
        if timestamp is None:
            timestamp = SERVER_TIMESTAMP
        
        players_df = get_players()
        batch = db.batch()
        c = 0
        for _, player in players_df.iterrows():
            # Update current rating in spelers collectie
            p_ref = players_ref.document(player['speler_id'])
            batch.update(p_ref, {'rating': 1000})
            
            # Voeg reset entry toe aan ELO logs
            e_ref = elo_ref.document()
            batch.set(e_ref, {
                'speler_naam': player['speler_naam'],
                'rating': 1000,
                'timestamp': timestamp,
                'match_id': 'SEASON_RESET'
            })
            
            c += 2
            if c >= 400:
                batch.commit()
                batch = db.batch()
                c = 0
        if c > 0: batch.commit()
        clear_all_caches(only_players=True, only_elo=True)
        return True
    except Exception as e:
        print(f"Reset ELO error: {e}")
        return False

def recalculate_elos_for_season(start_date, end_date):
    """Herberekent alle ELO scores voor een seizoen."""
    try:
        from utils.utils_new_elo import calculate_new_elo
        if isinstance(start_date, pd.Timestamp): start_date = start_date.date()
        if isinstance(end_date, pd.Timestamp): end_date = end_date.date()
        
        all_matches = get_matches().sort_values('timestamp', ascending=True)
        players_df = get_players()
        # Normaliseer timestamp voor vergelijking
        all_matches['ts_date'] = all_matches['timestamp'].dt.date
        mask = (all_matches['ts_date'] >= start_date) & (all_matches['ts_date'] <= end_date)
        season_matches = all_matches[mask]
        
        player_elos = {name: 1000 for name in players_df['speler_naam']}
        player_matches = {name: 0 for name in players_df['speler_naam']}
        batch = db.batch()
        
        # Verwijder ALLE ELO logs in dit seizoen
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        
        old_elos = elo_ref.where(filter=FieldFilter('timestamp', '>=', start_ts)).where(filter=FieldFilter('timestamp', '<=', end_ts)).stream()
        c = 0
        for doc in old_elos:
            batch.delete(doc.reference)
            c += 1
            if c >= 400:
                batch.commit()
                batch = db.batch()
                c = 0
        if c > 0: batch.commit()
        
        # Stap 1: Voeg voor iedereen een baseline 1000 toe aan het begin van het seizoen
        batch = db.batch()
        c = 0
        baseline_ts = pd.Timestamp(start_date)
        for name in player_elos.keys():
            batch.set(elo_ref.document(), {
                'speler_naam': name,
                'rating': 1000,
                'timestamp': baseline_ts,
                'match_id': 'SEASON_RESET'
            })
            c += 1
            if c >= 400:
                batch.commit()
                batch = db.batch()
                c = 0
        if c > 0: batch.commit()
        
        # Stap 2: Bereken matches opnieuw
        batch = db.batch()
        c = 0
        for _, match in season_matches.iterrows():
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
            # Belangrijk: all_ratings moet de HUIDIGE ratings van deze spelers bevatten
            # We voegen 'mock' history toe op basis van match_count om de K-factor correct te berekenen
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
        
        # Update current ratings in players table to match end of season
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
        print(f"Recalc error: {e}")
        return False

@st.cache_data(ttl=60)
def get_recalc_status():
    """Haalt de herberekeningsstatus op uit system_config."""
    try:
        config_ref = db.collection("system_config").document("elo_recalc")
        doc = config_ref.get()
        if doc.exists:
            return doc.to_dict()
    except Exception as e:
        print(f"Fout bij ophalen ELO herberekeningsstatus: {e}")
    return None

def set_recalc_needed_flag(season_start, season_end, season_naam, modified_timestamp):
    try:
        import pandas as pd
        config_ref = db.collection("system_config").document("elo_recalc")
        doc = config_ref.get()
        
        # Bepaal de vroegste wijzigingstijdstip
        new_ts = pd.Timestamp(modified_timestamp)
        if new_ts.tzinfo is not None:
            new_ts = new_ts.tz_localize(None)
            
        if doc.exists:
            data = doc.to_dict()
            if data.get("recalc_needed"):
                existing_ts = data.get("earliest_modified_timestamp")
                if existing_ts:
                    existing_ts = pd.Timestamp(existing_ts)
                    if existing_ts.tzinfo is not None:
                        existing_ts = existing_ts.tz_localize(None)
                    if existing_ts < new_ts:
                        new_ts = existing_ts
        
        config_ref.set({
            "recalc_needed": True,
            "season_start": pd.Timestamp(season_start),
            "season_end": pd.Timestamp(season_end),
            "season_naam": season_naam,
            "earliest_modified_timestamp": new_ts,
            "timestamp": pd.Timestamp.now()
        }, merge=True)
        get_recalc_status.clear()
    except Exception as e:
        print(f"Error setting recalc flag: {e}")

def recalculate_elos_from(start_timestamp, season_start, season_end):
    """Herberekent ELO scores incrementeel vanaf een specifiek tijdstip binnen een seizoen."""
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
        
        future_matches = season_matches[season_matches['ts_naive'] >= start_ts_pd].sort_values('ts_naive', ascending=True)
        
        if future_matches.empty:
            clear_all_caches(only_elo=True, only_players=True)
            return True

        elo_df = get_elo_logs()
        elo_df['ts_naive'] = elo_df['timestamp'].apply(lambda x: x.replace(tzinfo=None) if hasattr(x, 'tzinfo') and x.tzinfo is not None else x)
        
        season_start_pd = pd.Timestamp(season_start)
        if hasattr(season_start_pd, 'tzinfo') and season_start_pd.tzinfo is not None:
            season_start_pd = season_start_pd.tz_localize(None)
        
        past_elos = elo_df[(elo_df['ts_naive'] >= season_start_pd) & (elo_df['ts_naive'] < start_ts_pd)]
        
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
    """Verwijdert match en zet herberekeningsvlag (geen directe herberekening)."""
    try:
        from google.cloud.firestore_v1.base_query import FieldFilter
        import pandas as pd
        
        doc = matches_ref.document(match_id).get()
        if not doc.exists: 
            print(f"Match {match_id} not found in Firestore.")
            return True
        
        match_data = doc.to_dict()
        ts = match_data.get('timestamp')
        
        # Verwijder wedstrijd
        matches_ref.document(match_id).delete()
        
        # Verwijder direct de 4 bijbehorende ELO-logs van deze specifieke wedstrijd
        try:
            elo_docs = elo_ref.where(filter=FieldFilter('match_id', '==', match_id)).stream()
            b = db.batch()
            for edoc in elo_docs: 
                b.delete(edoc.reference)
            b.commit()
        except Exception as e:
            print(f"Kon ELO-logs voor wedstrijd {match_id} niet direct verwijderen: {e}")
        
        # Verwijder uit GSheet Backup
        try:
            _delete_gsheet_record("Wedstrijden", "match_id", match_id)
            _delete_gsheet_record("ELO_Logs", "match_id", match_id)
        except Exception as e:
            print(f"Kon niet uit GSheet verwijderen: {e}")
            
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
            
            # Zet de vlag en de vroegste wijzigingstijdstip (altijd uitgesteld)
            set_recalc_needed_flag(start_date, end_date, season_naam, ts)
            
        clear_all_caches(only_matches=True, only_elo=True)
        return "FLAGGED"
    except Exception as e:
        print(f"Error in delete_match_with_elo_recalculation: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_match_with_elo_recalculation(match_id, updated_data):
    """Update match en zet herberekeningsvlag (geen directe herberekening)."""
    try:
        from google.cloud.firestore_v1.base_query import FieldFilter
        import pandas as pd
        
        doc = matches_ref.document(match_id).get()
        if not doc.exists:
            print(f"Match {match_id} not found in Firestore.")
            return False
            
        orig_match_data = doc.to_dict()
        orig_ts = orig_match_data.get('timestamp')
        new_ts = updated_data.get('timestamp') or orig_ts
        
        # Bepaal het vroegste tijdstip tussen origineel en nieuw
        ts = orig_ts
        if orig_ts and new_ts:
            orig_ts_pd = pd.Timestamp(orig_ts)
            new_ts_pd = pd.Timestamp(new_ts)
            if orig_ts_pd.tzinfo is not None: orig_ts_pd = orig_ts_pd.tz_localize(None)
            if new_ts_pd.tzinfo is not None: new_ts_pd = new_ts_pd.tz_localize(None)
            if new_ts_pd < orig_ts_pd:
                ts = new_ts
        
        # Update wedstrijd in Firestore
        matches_ref.document(match_id).update(updated_data)
        
        # Verwijder de oude ELO-logs voor deze match
        try:
            elo_docs = elo_ref.where(filter=FieldFilter('match_id', '==', match_id)).stream()
            b = db.batch()
            for edoc in elo_docs: 
                b.delete(edoc.reference)
            b.commit()
        except Exception as e:
            print(f"Kon oude ELO-logs voor wedstrijd {match_id} niet verwijderen: {e}")
            
        # Update GSheet Backup
        try:
            _delete_gsheet_record("Wedstrijden", "match_id", match_id)
            updated_doc = matches_ref.document(match_id).get()
            if updated_doc.exists:
                _write_gsheet_record("Wedstrijden", {**updated_doc.to_dict(), 'match_id': match_id})
            _delete_gsheet_record("ELO_Logs", "match_id", match_id)
        except Exception as e:
            print(f"Kon GSheet niet updaten: {e}")
            
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
            
            # Zet de vlag en de vroegste wijzigingstijdstip (altijd uitgesteld)
            set_recalc_needed_flag(start_date, end_date, season_naam, ts)
            
        clear_all_caches(only_matches=True, only_elo=True)
        return "FLAGGED"
    except Exception as e:
        print(f"Error in update_match_with_elo_recalculation: {e}")
        import traceback
        traceback.print_exc()
        return False

def delete_multiple_matches_with_elo_recalculation(match_ids):
    """Verwijdert meerdere matches en zet de herberekeningsvlag op basis van de vroegste match."""
    try:
        from google.cloud.firestore_v1.base_query import FieldFilter
        import pandas as pd
        
        earliest_ts = None
        earliest_season_info = None
        
        seasons = get_seasons()
        
        for mid in match_ids:
            doc = matches_ref.document(mid).get()
            if not doc.exists:
                continue
                
            m_data = doc.to_dict()
            ts = m_data.get('timestamp')
            
            # Vergelijk timestamps om de vroegste te vinden
            if ts:
                ts_pd = pd.Timestamp(ts)
                ts_naive = ts_pd.replace(tzinfo=None) if ts_pd.tzinfo is not None else ts_pd
                
                if earliest_ts is None:
                    earliest_ts = ts_pd
                else:
                    earliest_ts_naive = earliest_ts.replace(tzinfo=None) if earliest_ts.tzinfo is not None else earliest_ts
                    if ts_naive < earliest_ts_naive:
                        earliest_ts = ts_pd
                        
                # Zoek seizoen
                s_row = seasons[(seasons['start_datum'] <= ts_naive) & (seasons['eind_datum'] >= ts_naive)]
                if not s_row.empty and (earliest_season_info is None or ts_naive < earliest_ts.replace(tzinfo=None)):
                    earliest_season_info = (
                        s_row.iloc[0]['start_datum'],
                        s_row.iloc[0]['eind_datum'],
                        s_row.iloc[0]['seizoen_naam']
                    )
            
            # Verwijder match
            matches_ref.document(mid).delete()
            
            # Verwijder ELO logs van deze match
            try:
                elo_docs = elo_ref.where(filter=FieldFilter('match_id', '==', mid)).stream()
                b = db.batch()
                for edoc in elo_docs: 
                    b.delete(edoc.reference)
                b.commit()
            except Exception:
                pass
                
            # Verwijder uit GSheet Backup
            try:
                _delete_gsheet_record("Wedstrijden", "match_id", mid)
                _delete_gsheet_record("ELO_Logs", "match_id", mid)
            except Exception:
                pass
                
        if earliest_ts and earliest_season_info:
            start_date, end_date, season_naam = earliest_season_info
            set_recalc_needed_flag(start_date, end_date, season_naam, earliest_ts)
            
        clear_all_caches(only_matches=True, only_elo=True)
        return "FLAGGED"
    except Exception as e:
        print(f"Error in delete_multiple_matches_with_elo_recalculation: {e}")
        return False

def check_and_run_scheduled_recalc():
    """Controleert of er een ELO-herberekening gepland staat en voert deze uit na 23:00 uur."""
    try:
        from datetime import datetime, timedelta
        import pandas as pd
        import google.cloud.firestore
        
        # We gebruiken een transactie om de controle en het claimen van de lock atomair uit te voeren
        transaction = db.transaction()
        
        @google.cloud.firestore.transactional
        def check_and_claim_recalc(tx):
            config_ref = db.collection("system_config").document("elo_recalc")
            snapshot = config_ref.get(transaction=tx)
            if not snapshot.exists:
                return None
                
            data = snapshot.to_dict()
            if not data.get("recalc_needed"):
                return None
                
            # Bepaal het meest recente geplande tijdstip (vandaag om 23:00, of gisteren om 23:00)
            now = datetime.now()
            if now.hour >= 23:
                last_scheduled = now.replace(hour=23, minute=0, second=0, microsecond=0)
            else:
                last_scheduled = (now - timedelta(days=1)).replace(hour=23, minute=0, second=0, microsecond=0)
                
            last_recalc = data.get("last_recalc_time")
            if last_recalc:
                last_recalc = pd.Timestamp(last_recalc).to_pydatetime()
                if last_recalc.tzinfo is not None:
                    last_recalc = last_recalc.replace(tzinfo=None)
                    
            if not last_recalc or last_recalc < last_scheduled:
                # Claim de herberekening: zet recalc_needed direct op False
                tx.update(config_ref, {
                    "recalc_needed": False,
                    "last_recalc_time": now
                })
                return data
            return None
            
        recalc_data = check_and_claim_recalc(transaction)
        if recalc_data:
            get_recalc_status.clear()
            print(f"[RECALC] Transactie geclaimd voor seizoen {recalc_data.get('season_naam')}. Starten met herberekenen vanaf {recalc_data.get('earliest_modified_timestamp')}...")
            success = recalculate_elos_from(
                recalc_data.get("earliest_modified_timestamp"),
                recalc_data.get("season_start"),
                recalc_data.get("season_end")
            )
            config_ref = db.collection("system_config").document("elo_recalc")
            if success:
                # Wis de vroegste wijzigingstijdstip nu de herberekening is gelukt
                config_ref.update({
                    "earliest_modified_timestamp": None
                })
                get_recalc_status.clear()
                print("[RECALC] ELO-herberekening succesvol afgerond.")
            else:
                # Bij fout: zet vlag terug op True zodat het later opnieuw wordt geprobeerd
                print("[RECALC] ELO-herberekening mislukt. Vlag teruggezet naar True.")
                config_ref.update({
                    "recalc_needed": True
                })
                get_recalc_status.clear()
    except Exception as e:
        print(f"Fout bij checken/uitvoeren geplande ELO-herberekening: {e}")