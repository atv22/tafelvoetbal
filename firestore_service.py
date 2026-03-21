# --- Failsafe: Firestore bereikbaarheidscheck en custom exception ---
import streamlit as st
import os
import google.cloud.firestore
from google.oauth2 import service_account
import json
import pandas as pd
import uuid
from datetime import datetime
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

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
        return client.open_by_key(SHEET_ID)
    except Exception as e:
        print(f"[GSHEET OPEN] Fout bij openen van workbook: {e}")
        return None

@st.cache_data(ttl=3600) # Cache GSheet fallback voor 1 uur
def _read_gsheet_fallback(sheet_name):
    """Leest data uit Google Sheets als Firestore offline is of geen data geeft."""
    global LAST_FALLBACK_ERROR
    try:
        sh = _get_gsheet_workbook()
        if not sh:
            LAST_FALLBACK_ERROR = "Geen Google credentials gevonden voor GSheet fallback of sheet onbereikbaar."
            return pd.DataFrame()
        
        # Check of worksheet bestaat om spam-errors te voorkomen
        try:
            worksheet = sh.worksheet(sheet_name)
        except Exception:
            print(f"[GSHEET] Tabblad '{sheet_name}' niet gevonden.")
            return pd.DataFrame()
            
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
    """Leeg specifieke of alle Streamlit caches na mutaties."""
    try:
        if only_players:
            get_players.clear()
        elif only_matches:
            get_matches.clear()
            get_seasons.clear()
        elif only_elo:
            get_players.clear()
            get_elo_logs.clear()
            get_elo_history.clear()
        elif only_requests:
            get_requests.clear()
        else:
            st.cache_data.clear()
    except Exception as e:
        print(f"Fout bij cache invalidatie: {e}")
        try: st.cache_data.clear()
        except: pass

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
        log_list = [doc.to_dict() for doc in beheer_docs]
        if not log_list:
            return _read_gsheet_fallback("Beheer_Log")
        
        df = pd.DataFrame(log_list)
        if not df.empty and 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df['timestamp'] = normalize_timestamp_series(df['timestamp'])
        set_offline_mode(False)
        return df
    except Exception:
        return _read_gsheet_fallback("Beheer_Log")

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
    ts = match_data.get('timestamp') or pd.Timestamp.now()
    try:
        batch = db.batch()
        new_match_ref = matches_ref.document()
        match_id = new_match_ref.id
        batch.set(new_match_ref, {**match_data, 'timestamp': ts, 'match_id': match_id})

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
    try:
        # Verwijder uit Firestore
        matches_ref.document(mid).delete()
        # Verwijder bijbehorende ELO logs uit Firestore
        elo_docs = elo_ref.where(filter=FieldFilter('match_id', '==', mid)).stream()
        batch = db.batch()
        for doc in elo_docs: batch.delete(doc.reference)
        batch.commit()
        
        # Verwijder uit GSheet Backup
        _delete_gsheet_record("Wedstrijden", "match_id", mid)
        _delete_gsheet_record("ELO_Logs", "match_id", mid)
        
        clear_all_caches(only_matches=True, only_elo=True)
        return True
    except: return False

def update_match(mid, data):
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
        clear_all_caches(only_elo=True)
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
        clear_all_caches(only_matches=True, only_elo=True)
        return True
    except: return False
