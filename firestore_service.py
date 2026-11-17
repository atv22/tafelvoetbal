# --- Failsafe: Firestore bereikbaarheidscheck en custom exception ---
import streamlit as st
import os
import google.cloud.firestore
from google.oauth2 import service_account
import json
import math
import pandas as pd
import uuid
import traceback
import zoneinfo
from datetime import datetime, timedelta
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
        log_dict = {
            "Tijdstip": ts,
            "Type": op_type.upper(),
            "Collectie": collection,
            "Actie": action,
            "Aantal": count,
            "IP": ip
        }
        get_log_history().appendleft(log_dict)
    except Exception as e:
        print(f"[FIRESTORE LOG ERROR] {e}")

# Google Sheet ID voor fallback
DEFAULT_SHEET_ID = "1cCiNoYfro9SqS8qIjEKT8prsAvAA7wowvhzhh2ljHnA"
SHEET_ID = st.secrets.get("GSHEET_ID", DEFAULT_SHEET_ID)
GS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# Seizoen Configuratie
SEASON_TRANSITION_MONTH = 3
SEASON_TRANSITION_DAY = 15
PRINSJESDAG_OFFSET_DAYS = 15 # Prinsjesdag is 3e dinsdag van september. We tellen er 15 op om op woensdag 00:00 uit te komen (middernacht na Prinsjesdag)

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
                log_firestore_op("ERROR", "Firestore", "Quota/budget limit hit", 1)
                raise FirestoreUnavailable("Database niet bereikbaar: mogelijk budgetlimiet bereikt.", details=str(e))
            log_firestore_op("ERROR", "Firestore", "Database unavailable", 1)
            raise FirestoreUnavailable("Database niet bereikbaar.", details=str(e))
    return functools.wraps(func)(wrapper)

# --- OFFLINE STATUS & DIAGNOSTICS ---
OFFLINE_MODE = False
LAST_FALLBACK_ERROR = None

def set_offline_mode(value: bool):
    global OFFLINE_MODE
    new_value = bool(value)
    if new_value and not OFFLINE_MODE:
        log_firestore_op("SYSTEM", "Fallback", "Switched to Google Sheets", 1)
    elif not new_value and OFFLINE_MODE:
        log_firestore_op("SYSTEM", "Fallback", "Switched to Firestore", 1)
    OFFLINE_MODE = new_value

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
                row.extend([''] * (len(headers) - len(row)))
            elif len(row) > len(headers):
                row = row[:len(headers)]
            data_dicts.append(dict(zip(headers, row)))
            
        df = pd.DataFrame(data_dicts)
        
        # Normalize column names to lowercase for consistency
        df.columns = [c.lower() for c in df.columns]
        
        if not df.empty:
            if 'rating' in df.columns:
                df['rating'] = df['rating'].astype(str).str.replace(',', '.', regex=False)
                df['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(1000)

            numeric_cols = ['thuis_score', 'uit_score',
                            'klinkers_thuis_1', 'klinkers_thuis_2',
                            'klinkers_uit_1', 'klinkers_uit_2',
                            'score thuis', 'score uit']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            ts_cols = ['timestamp']
            for col in ts_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce', format='mixed')

            set_offline_mode(True)
            LAST_FALLBACK_ERROR = None
        return df
    except Exception as e:
        LAST_FALLBACK_ERROR = str(e)
        print(f"[GSHEET FALLBACK] Fout bij lezen van {sheet_name}: {e}")
        return pd.DataFrame()

def _rowcol_to_a1(row, col):
    """Zet 1-gebaseerde rij- en kolomnummers om naar een A1-celreferentie."""
    letters = ""
    c = int(col)
    while c > 0:
        c, rem = divmod(c - 1, 26)
        letters = chr(65 + rem) + letters
    return f"{letters}{int(row)}"

def _sanitize_gsheet_cell(val):
    """Maakt een celwaarde veilig voor JSON-serialisatie richting Google Sheets."""
    if val is None:
        return ""
    if val is SERVER_TIMESTAMP or type(val).__name__ == 'Sentinel':
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(val, (list, tuple, set)):
        items = [_sanitize_gsheet_cell(x) for x in val]
        return ", ".join(str(x) for x in items if x is not None and str(x) != "")
    if isinstance(val, dict):
        clean_dict = {str(k): _sanitize_gsheet_cell(v) for k, v in val.items()}
        return json.dumps(clean_dict, ensure_ascii=False, default=str)
    try:
        if pd.isna(val):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(val, (pd.Timestamp, datetime)):
        return val.strftime('%Y-%m-%d %H:%M:%S')
    if hasattr(val, 'item') and callable(val.item):
        val = val.item()
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return ""
    if not isinstance(val, (str, int, float, bool)):
        return str(val)
    return val

def _df_to_gsheet_rows(df):
    """Converteert een DataFrame inclusief headers naar Google Sheets-veilige rijen."""
    headers = [str(c) for c in df.columns.tolist()]
    rows = [headers]
    for row in df.itertuples(index=False, name=None):
        rows.append([_sanitize_gsheet_cell(v) for v in row])
    return rows

def _build_players_sync_df(fs_players, updated_player_elos=None):
    """Stelt een geordend Spelers-DataFrame samen vanuit Firestore spelersdata voor Google Sheets."""
    rows_data = []
    for pid, pdata in fs_players.items():
        row_d = {**(pdata or {}), 'speler_id': pid}
        if updated_player_elos:
            pname = str(row_d.get('speler_naam', ''))
            if pname in updated_player_elos:
                row_d['rating'] = updated_player_elos[pname]
        rows_data.append(row_d)
    p_sync_df = pd.DataFrame(rows_data)
    pref_cols = [c for c in ['speler_id', 'speler_naam', 'rating'] if c in p_sync_df.columns]
    rest_cols = [c for c in p_sync_df.columns if c not in pref_cols]
    return p_sync_df[pref_cols + rest_cols]

def _safe_replace_worksheet(ws, rows_with_header, existing_vals=None):
    """Vervangt worksheet-inhoud veilig zonder eerst te wissen (voorkomt dataverlies bij fouten)."""
    clean_rows = [
        [_sanitize_gsheet_cell(v) for v in row]
        for row in (rows_with_header or [])
    ]
    if not clean_rows:
        return True

    if existing_vals is None:
        try:
            existing_vals = ws.get_all_values()
        except Exception:
            existing_vals = []

    old_rows = len(existing_vals)
    old_cols = max((len(r) for r in existing_vals), default=0)

    ws.update(values=clean_rows, range_name='A1')

    new_rows = len(clean_rows)
    new_cols = max((len(r) for r in clean_rows), default=0)
    clear_ranges = []
    if old_rows > new_rows and max(old_cols, new_cols) > 0:
        end_col = max(old_cols, new_cols)
        clear_ranges.append(f"{_rowcol_to_a1(new_rows + 1, 1)}:{_rowcol_to_a1(old_rows, end_col)}")
    if old_cols > new_cols and new_rows > 0:
        clear_ranges.append(f"{_rowcol_to_a1(1, new_cols + 1)}:{_rowcol_to_a1(new_rows, old_cols)}")
    if clear_ranges and hasattr(ws, 'batch_clear'):
        ws.batch_clear(clear_ranges)
    return True

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
            worksheet.append_row([str(h) for h in headers])
        
        rows = []
        for d in data_dicts:
            rows.append([_sanitize_gsheet_cell(d.get(h, "")) for h in headers])
        
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
            _safe_replace_worksheet(worksheet, rows_to_keep, existing_vals=all_values)
        return True
    except Exception as e:
        print(f"[GSHEET DELETE] Fout bij verwijderen uit {sheet_name}: {e}")
        return False

@st.cache_resource
def get_sync_throttle():
    """Globale sync throttle."""
    return {"last_sync": datetime.min}

def reconcile_data_sources(force=False):
    """Synchroniseert data tussen Firestore en Google Sheets op een efficiënte manier."""
    try:
        # Throttling: Maximaal eens per 15 minuten syncen (Globaal), tenzij geforceerd
        now = datetime.now()
        throttle = get_sync_throttle()
        if not force and (now - throttle["last_sync"]).total_seconds() < 900:
            return
        throttle["last_sync"] = now

        print("[SYNC] Bezig met synchronisatie...")
        if hasattr(_fetch_all_gsheet_data, "clear"):
            _fetch_all_gsheet_data.clear()
        if hasattr(_read_gsheet_fallback, "clear"):
            _read_gsheet_fallback.clear()
        
        # 1. Sync Wedstrijden & ELO logs
        try:
            fs_matches = list(matches_ref.select(['match_id']).stream())
            fs_ids = {doc.to_dict().get('match_id') or doc.id for doc in fs_matches}
        except Exception:
            print("[SYNC] Firestore niet bereikbaar voor sync.")
            return

        gs_df = _read_gsheet_fallback.__wrapped__("Wedstrijden") if hasattr(_read_gsheet_fallback, "__wrapped__") else _read_gsheet_fallback("Wedstrijden")
        gs_ids = set(gs_df['match_id'].dropna().unique()) if not gs_df.empty else set()

        # A. GSheet -> Firestore (Offline recovery: alleen wedstrijden met OFFLINE_ prefix herstellen)
        missing_in_fs = {mid for mid in (gs_ids - fs_ids) if str(mid).startswith("OFFLINE_")}
        if missing_in_fs:
            print(f"[SYNC] {len(missing_in_fs)} nieuwe offline wedstrijden in GSheet gevonden.")
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

        # 2. Sync Spelers (inclusief bijgewerkte ratings & verwijderde/hernoemde spelers)
        fs_players = {p.id: p.to_dict() for p in players_ref.stream()}
        gs_players_df = _read_gsheet_fallback.__wrapped__("Spelers") if hasattr(_read_gsheet_fallback, "__wrapped__") else _read_gsheet_fallback("Spelers")
        gs_p_ids = set(gs_players_df['speler_id'].unique()) if not gs_players_df.empty and 'speler_id' in gs_players_df.columns else set()

        missing_p_in_gs = set(fs_players.keys()) - gs_p_ids
        players_mismatch = gs_players_df.empty and bool(fs_players)
        if not gs_players_df.empty and 'speler_id' in gs_players_df.columns:
            gs_map = {str(r['speler_id']): r for _, r in gs_players_df.iterrows()}
            for pid, pdata in fs_players.items():
                gs_row = gs_map.get(str(pid))
                if gs_row is None or str(gs_row.get('speler_naam', '')) != str(pdata.get('speler_naam', '')):
                    players_mismatch = True
                    break
                try:
                    if abs(float(gs_row.get('rating', 1000)) - float(pdata.get('rating', 1000))) > 0.01:
                        players_mismatch = True
                        break
                except (TypeError, ValueError):
                    players_mismatch = True
                    break
            if len(gs_p_ids - set(fs_players.keys())) > 0:
                players_mismatch = True

        if missing_p_in_gs or players_mismatch:
            sh = _get_gsheet_workbook()
            if sh and fs_players:
                try:
                    ws_p = sh.worksheet("Spelers")
                except Exception:
                    ws_p = sh.add_worksheet(title="Spelers", rows="100", cols="10")
                p_sync_df = _build_players_sync_df(fs_players)
                _safe_replace_worksheet(ws_p, _df_to_gsheet_rows(p_sync_df))

        set_offline_mode(False)
        print("[SYNC] Synchronisatie voltooid.")
        clear_all_caches()
    except Exception as e:
        print(f"[SYNC] Fout tijdens synchronisatie: {e}")

# --- HULPFUNCTIE: Cache volledig legen ---
def clear_all_caches(only_players=False, only_matches=False, only_elo=False, only_requests=False):
    """
    Leegt specifieke Streamlit caches en werkt de store timestamps bij zodat nieuwe reads direct verversen.
    """
    import time
    try:
        store = init_firestore_listeners()
        now_ts = time.time()
        all_flags = not (only_players or only_matches or only_elo or only_requests)
        if all_flags or only_players:
            store["last_updated"]["players"] = now_ts
            if hasattr(_build_players_df, "clear"):
                _build_players_df.clear()
        if all_flags or only_matches:
            store["last_updated"]["matches"] = now_ts
            if hasattr(_build_matches_df, "clear"):
                _build_matches_df.clear()
            if hasattr(get_seasons, "clear"):
                get_seasons.clear()
        if all_flags or only_elo:
            store["last_updated"]["elo"] = now_ts
            if hasattr(_build_elo_logs_df, "clear"):
                _build_elo_logs_df.clear()
        if all_flags or only_requests:
            store["last_updated"]["requests"] = now_ts
            if hasattr(_build_requests_df, "clear"):
                _build_requests_df.clear()
        if all_flags:
            store["last_updated"]["beheer_log"] = now_ts
            if hasattr(_build_beheer_log_df, "clear"):
                _build_beheer_log_df.clear()
        if is_offline() or all_flags:
            if hasattr(_fetch_all_gsheet_data, "clear"):
                _fetch_all_gsheet_data.clear()
            if hasattr(_read_gsheet_fallback, "clear"):
                _read_gsheet_fallback.clear()
    except Exception as e:
        print(f"Fout bij cache invalidatie: {e}")

# --- HULPFUNCTIES: Tijdzone, Seizoensgrenzen & ELO Replay ---
NL_TZ = zoneinfo.ZoneInfo("Europe/Amsterdam")

def _get_nl_now_aware():
    """Geeft de huidige datum en tijd in Europe/Amsterdam met tijdzone."""
    return datetime.now(NL_TZ)

def _get_nl_now_naive():
    """Geeft de huidige datum en tijd in Europe/Amsterdam als timezone-naive datetime."""
    return _get_nl_now_aware().replace(tzinfo=None)

def _to_nl_naive(ts):
    """Converteert een tz-aware timestamp naar Europe/Amsterdam naive; laat naive ongewijzigd."""
    if ts is None:
        return None
    t = pd.Timestamp(ts)
    if pd.isna(t):
        return None
    if t.tzinfo is not None:
        return t.tz_convert(NL_TZ).tz_localize(None).to_pydatetime()
    return t.to_pydatetime()

def _season_bounds_naive(season_start, season_end):
    """Normaliseert seizoensgrenzen naar naive pd.Timestamp [00:00:00 .. 23:59:59.999999] zonder dag-overflow."""
    s_start = pd.Timestamp(season_start)
    if s_start.tzinfo is not None:
        s_start = s_start.tz_localize(None)
    s_end = pd.Timestamp(season_end)
    if s_end.tzinfo is not None:
        s_end = s_end.tz_localize(None)
    if s_end.hour == 0 and s_end.minute == 0 and s_end.second == 0:
        s_end = s_end.replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        s_end = s_end.replace(microsecond=999999)
    return s_start, s_end

def _should_update_global_player_ratings(all_matches, s_end_naive):
    """Bepaalt of globale speler-ratings ('spelers.rating') bijgewerkt mogen worden (alleen bij het nieuwste seizoen)."""
    if all_matches is None or all_matches.empty or 'timestamp' not in all_matches.columns:
        return True
    ts = normalize_timestamp_series(
        pd.to_datetime(all_matches['timestamp'], errors='coerce', format='mixed', utc=True)
    ).dropna()
    if ts.empty:
        return True
    return not bool((ts > s_end_naive).any())

def replay_season_elos(season_matches, initial_elo=1000.0, initial_elos=None, initial_matches=None):
    """Speelt wedstrijden chronologisch af en berekent ELO-ratings, wedstrijdaantallen en ELO-log records."""
    from utils.utils_new_elo import calculate_new_elo

    player_elos = dict(initial_elos) if initial_elos is not None else {}
    player_matches = dict(initial_matches) if initial_matches is not None else {}
    records = []

    if season_matches is None or season_matches.empty:
        return player_elos, player_matches, records

    df = season_matches.copy()
    df['_ts_naive'] = normalize_timestamp_series(
        pd.to_datetime(df['timestamp'], errors='coerce', format='mixed', utc=True)
    )
    sort_cols = ['_ts_naive'] + (['match_id'] if 'match_id' in df.columns else [])
    df = df.sort_values(sort_cols, ascending=True, na_position='last', kind='mergesort')

    for idx, match in df.iterrows():
        m_dict = {
            "Thuis_1": match.get('thuis_1'),
            "Thuis_2": match.get('thuis_2'),
            "Uit_1": match.get('uit_1'),
            "Uit_2": match.get('uit_2'),
            "Thuis_score": match.get('thuis_score', 0),
            "Uit_score": match.get('uit_score', 0),
            "klinkers_thuis_1": match.get('klinkers_thuis_1', 0),
            "klinkers_thuis_2": match.get('klinkers_thuis_2', 0),
            "klinkers_uit_1": match.get('klinkers_uit_1', 0),
            "klinkers_uit_2": match.get('klinkers_uit_2', 0),
        }
        m_players = {
            m_dict[k]
            for k in ("Thuis_1", "Thuis_2", "Uit_1", "Uit_2")
            if m_dict[k] is not None and not pd.isna(m_dict[k]) and str(m_dict[k]).strip() != ""
        }
        if len(m_players) < 4:
            continue

        all_ratings = {
            p: [player_elos.get(p, float(initial_elo))] * (player_matches.get(p, 0) + 1)
            for p in m_players
        }
        new_df = calculate_new_elo(m_dict, all_ratings)
        match_id = match.get('match_id', idx)
        match_ts = match.get('timestamp')
        for _, row in new_df.iterrows():
            p = row['Speler']
            r = float(row['ELO'])
            player_elos[p] = r
            player_matches[p] = player_matches.get(p, 0) + 1
            records.append({
                'speler_naam': p,
                'rating': r,
                'timestamp': match_ts,
                'match_id': match_id,
            })

    return player_elos, player_matches, records

def audit_season_elo(season_start, season_end, matches_df=None, elo_df=None, players_df=None):
    """Vergelijkt (read-only) een schone ELO-replay vanaf 1000 met opgeslagen ELO-logs en spelerstabel."""
    from utils.utils import IGNORE_PLAYERS

    s_start, s_end = _season_bounds_naive(season_start, season_end)
    if matches_df is None:
        matches_df = get_matches()
    if elo_df is None:
        elo_df = get_elo_logs()
    if players_df is None:
        players_df = get_players()

    if matches_df is None or matches_df.empty:
        return {
            "match_count": 0,
            "missing_elo_logs": 0,
            "mismatched_logs_count": 0,
            "max_player_diff": 0.0,
            "player_diffs": pd.DataFrame(),
        }

    m_df = matches_df.copy()
    m_df['_ts_naive'] = normalize_timestamp_series(
        pd.to_datetime(m_df['timestamp'], errors='coerce', format='mixed', utc=True)
    )
    season_matches = m_df[(m_df['_ts_naive'] >= s_start) & (m_df['_ts_naive'] <= s_end)].copy()
    expected_elos, match_counts, expected_records = replay_season_elos(season_matches)

    e_df = elo_df.copy() if elo_df is not None else pd.DataFrame()
    season_elo = pd.DataFrame()
    if not e_df.empty and 'timestamp' in e_df.columns:
        e_df['_ts_naive'] = normalize_timestamp_series(
            pd.to_datetime(e_df['timestamp'], errors='coerce', format='mixed', utc=True)
        )
        season_elo = e_df[(e_df['_ts_naive'] >= s_start) & (e_df['_ts_naive'] <= s_end)].copy()

    missing_elo_logs = 0
    mismatched_logs_count = 0
    if not season_matches.empty:
        if season_elo.empty or 'match_id' not in season_elo.columns:
            missing_elo_logs = len(season_matches) * 4
        else:
            actual_map = {}
            for _, erow in season_elo.iterrows():
                mid = str(erow.get('match_id', ''))
                pname = str(erow.get('speler_naam', ''))
                if mid and mid != 'SEASON_RESET':
                    actual_map[(mid, pname)] = float(erow.get('rating', 1000.0))
            for rec in expected_records:
                key = (str(rec['match_id']), str(rec['speler_naam']))
                if key not in actual_map:
                    missing_elo_logs += 1
                elif abs(actual_map[key] - rec['rating']) > 0.5:
                    mismatched_logs_count += 1

    latest_season_elo = {}
    if not season_elo.empty:
        e_valid = season_elo.copy()
        if 'match_id' in e_valid.columns:
            e_valid = e_valid[e_valid['match_id'].fillna('').astype(str) != 'SEASON_RESET']
        if not e_valid.empty:
            sort_cols = ['_ts_naive'] + (['match_id'] if 'match_id' in e_valid.columns else [])
            e_valid = e_valid.sort_values(sort_cols, ascending=True, na_position='first', kind='mergesort')
            for _, erow in e_valid.drop_duplicates(subset=['speler_naam'], keep='last').iterrows():
                latest_season_elo[str(erow['speler_naam'])] = float(erow['rating'])

    player_table_map = {}
    if players_df is not None and not players_df.empty and 'speler_naam' in players_df.columns:
        for _, prow in players_df.iterrows():
            player_table_map[str(prow['speler_naam'])] = float(prow.get('rating', 1000.0))

    ignore_set = {p.lower().strip() for p in IGNORE_PLAYERS}
    rows = []
    for pname in sorted(expected_elos.keys()):
        if str(pname).lower().strip() in ignore_set:
            continue
        exp_val = round(float(expected_elos[pname]), 2)
        stored_season_val = latest_season_elo.get(pname)
        tbl_val = player_table_map.get(pname)
        cmp_val = stored_season_val if stored_season_val is not None else tbl_val
        diff = round(float(cmp_val) - exp_val, 2) if cmp_val is not None else None
        rows.append({
            "Speler": pname,
            "Wedstrijden": int(match_counts.get(pname, 0)),
            "Verwachte ELO (vanaf 1000)": exp_val,
            "Opgeslagen Seizoen-ELO": round(float(stored_season_val), 2) if stored_season_val is not None else None,
            "Spelerstabel ELO": round(float(tbl_val), 2) if tbl_val is not None else None,
            "Verschil": diff,
        })

    diff_df = pd.DataFrame(rows)
    max_diff = float(diff_df["Verschil"].abs().max()) if not diff_df.empty and diff_df["Verschil"].notna().any() else 0.0
    return {
        "match_count": int(len(season_matches)),
        "missing_elo_logs": int(missing_elo_logs),
        "mismatched_logs_count": int(mismatched_logs_count),
        "max_player_diff": round(max_diff, 2),
        "player_diffs": diff_df,
    }

def _sync_recalculated_elo_to_gsheet(range_start, range_end, new_records, updated_player_elos=None, include_season_reset=False):
    """Werkt best-effort de ELO_Logs (binnen [range_start, range_end]) en optioneel Spelers in Google Sheets bij."""
    try:
        sh = _get_gsheet_workbook()
        if not sh:
            return False

        try:
            ws_elo = sh.worksheet("ELO_Logs")
            all_vals = ws_elo.get_all_values()
            if all_vals:
                headers = [h.strip() for h in all_vals[0]]
                rows_df = pd.DataFrame(all_vals[1:], columns=headers) if len(all_vals) > 1 else pd.DataFrame(columns=headers)
            else:
                headers = ['speler_naam', 'rating', 'timestamp', 'match_id']
                rows_df = pd.DataFrame(columns=headers)

            if not rows_df.empty and 'timestamp' in rows_df.columns:
                ts_norm = normalize_timestamp_series(
                    pd.to_datetime(rows_df['timestamp'], errors='coerce', format='mixed', utc=True)
                )
                in_range = (ts_norm >= range_start) & (ts_norm <= range_end)
                if not include_season_reset and 'match_id' in rows_df.columns:
                    in_range = in_range & (rows_df['match_id'].astype(str).str.strip() != 'SEASON_RESET')
                kept_df = rows_df[~in_range].copy()
            else:
                kept_df = rows_df.copy()

            new_df = pd.DataFrame(new_records) if new_records else pd.DataFrame(columns=headers)
            if not new_df.empty and 'timestamp' in new_df.columns:
                new_ts = normalize_timestamp_series(
                    pd.to_datetime(new_df['timestamp'], errors='coerce', format='mixed', utc=True)
                )
                new_df['timestamp'] = new_ts.dt.strftime('%Y-%m-%d %H:%M:%S')

            for h in headers:
                if h not in new_df.columns:
                    new_df[h] = ""
            combined = pd.concat([kept_df[headers], new_df[headers]], ignore_index=True)
            _safe_replace_worksheet(ws_elo, _df_to_gsheet_rows(combined[headers]), existing_vals=all_vals)
        except Exception as e:
            print(f"[GSHEET SYNC] Kon ELO_Logs niet bijwerken: {e}")

        if updated_player_elos:
            try:
                try:
                    ws_players = sh.worksheet("Spelers")
                except Exception:
                    ws_players = sh.add_worksheet(title="Spelers", rows="100", cols="10")
                p_vals = ws_players.get_all_values()
                rebuilt = False
                if p_vals and len(p_vals) > 1:
                    p_headers = [h.strip() for h in p_vals[0]]
                    if 'speler_naam' in p_headers and 'rating' in p_headers:
                        name_idx = p_headers.index('speler_naam')
                        rating_idx = p_headers.index('rating')
                        updated_rows = [p_headers]
                        for row in p_vals[1:]:
                            row_padded = list(row) + [""] * max(0, len(p_headers) - len(row))
                            pname = row_padded[name_idx]
                            if pname in updated_player_elos:
                                row_padded[rating_idx] = updated_player_elos[pname]
                            updated_rows.append(row_padded[:len(p_headers)])
                        _safe_replace_worksheet(ws_players, updated_rows, existing_vals=p_vals)
                        rebuilt = True
                if not rebuilt:
                    fs_players = {p.id: p.to_dict() for p in players_ref.stream()}
                    if fs_players:
                        p_sync_df = _build_players_sync_df(fs_players, updated_player_elos=updated_player_elos)
                        _safe_replace_worksheet(ws_players, _df_to_gsheet_rows(p_sync_df), existing_vals=p_vals)
            except Exception as e:
                print(f"[GSHEET SYNC] Kon Spelers niet bijwerken: {e}")
        return True
    except Exception as e:
        print(f"[GSHEET SYNC] Fout bij synchronisatie na herberekening: {e}")
        return False

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
beheer_ref = db.collection('beheer_log')

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
            # Voor 'players' krijgen we altijd de volledige collectie uit Firestore:
            # bij de eerste snapshot wissen we eventuele verouderde GSheet player IDs
            if collection_name == "players" and not events["players"].is_set() and doc_snapshot:
                store["players"].clear()
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
            
            # Fetch from the last GSheet sync to reduce read quota without missing data
            last_gsheet_ts = None
            if 'Wedstrijden' in gsheet_data and len(gsheet_data['Wedstrijden']) > 1:
                try:
                    import pandas as pd
                    headers = gsheet_data['Wedstrijden'][0]
                    if 'timestamp' in headers:
                        ts_idx = headers.index('timestamp')
                        ts_list = [row[ts_idx] for row in gsheet_data['Wedstrijden'][1:] if len(row) > ts_idx]
                        if ts_list:
                            parsed_ts = pd.to_datetime(ts_list, errors='coerce', format='mixed', utc=True)
                            if not parsed_ts.isna().all():
                                last_gsheet_ts = parsed_ts.max()
                except Exception:
                    pass
            
            if last_gsheet_ts:
                # Gebruik de laatste GSheet sync tijd minus 1 dag (om timezone overlaps te vangen)
                last_week = last_gsheet_ts - timedelta(days=1)
                if hasattr(last_week, 'to_pydatetime'):
                    last_week = last_week.to_pydatetime()
            else:
                # Fallback als we geen GSheet data kunnen lezen
                last_week = datetime.now(pytz.utc) - timedelta(days=30)
            
            recent_matches_query = matches_ref.where(filter=FieldFilter('timestamp', '>=', last_week))
            recent_elo_query = elo_ref.where(filter=FieldFilter('timestamp', '>=', last_week))
            
            store["watchers"].append(recent_matches_query.on_snapshot(make_callback("matches", "match_id")))
            store["watchers"].append(recent_elo_query.on_snapshot(make_callback("elo", None)))
            store["watchers"].append(players_ref.on_snapshot(make_callback("players", "speler_id")))
            store["watchers"].append(requests_ref.on_snapshot(make_callback("requests", None)))
            store["watchers"].append(beheer_ref.on_snapshot(make_callback("beheer_log", None)))
            
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
    if 'speler_naam' in df.columns:
        # Ontdubbel op speler_naam (geef voorrang aan niet-OFFLINE speler_id en laatst geladen Firestore record)
        if 'speler_id' in df.columns:
            df['_is_offline'] = df['speler_id'].astype(str).str.startswith('OFFLINE_')
            df = df.sort_values('_is_offline', ascending=True).drop(columns=['_is_offline'])
        df = df.drop_duplicates(subset=['speler_naam'], keep='last').reset_index(drop=True)
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
            
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', format='mixed', utc=True)
    df['timestamp'] = normalize_timestamp_series(df['timestamp'])
    
    # Enforce column order
    existing_cols = [c for c in MATCH_COLUMNS if c in df.columns]
    other_cols = [c for c in df.columns if c not in MATCH_COLUMNS]
    df = df[existing_cols + other_cols]
    
    sort_cols = ['timestamp'] + (['match_id'] if 'match_id' in df.columns else [])
    df = df.sort_values(sort_cols, ascending=False, na_position='last', kind='mergesort').reset_index(drop=True)
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
        df['rating'] = df['rating'].astype(str).str.replace(',', '.', regex=False)
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(1000)

    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', format='mixed', utc=True)
    df['timestamp'] = normalize_timestamp_series(df['timestamp'])

    # Backfill ontbrekende (NaT) timestamps uit store["matches"] via match_id
    if not df.empty and 'match_id' in df.columns and df['timestamp'].isna().any() and store.get("matches"):
        raw_m_ts = {
            str(mid): m.get('timestamp')
            for mid, m in store["matches"].items()
            if isinstance(m, dict) and m.get('timestamp') is not None
        }
        if raw_m_ts:
            m_series = pd.to_datetime(pd.Series(raw_m_ts), errors='coerce', format='mixed', utc=True)
            m_series = normalize_timestamp_series(m_series).dropna()
            match_ts_map = m_series.to_dict()
            missing_mask = df['timestamp'].isna()
            df.loc[missing_mask, 'timestamp'] = df.loc[missing_mask, 'match_id'].astype(str).map(match_ts_map)

    # Filter spook-rijen weg (bijv. oude spelersnaam in GSheet ELO_Logs na naamswijziging in Firestore)
    if not df.empty and 'match_id' in df.columns and 'speler_naam' in df.columns and store.get("matches"):
        valid_match_players = {}
        for mid, m in store["matches"].items():
            if isinstance(m, dict):
                players_set = {
                    str(m.get(col, '')).strip().lower()
                    for col in ('thuis_1', 'thuis_2', 'uit_1', 'uit_2')
                    if m.get(col) is not None and str(m.get(col, '')).strip() != ''
                }
                if players_set:
                    valid_match_players[str(mid)] = players_set
        if valid_match_players:
            keep_mask = [
                True if (
                    pd.isna(mid)
                    or str(mid).strip() in ('', 'SEASON_RESET')
                    or str(mid) not in valid_match_players
                )
                else (str(pname).strip().lower() in valid_match_players[str(mid)])
                for mid, pname in zip(df['match_id'], df['speler_naam'])
            ]
            df = df[keep_mask]

    # Verwijder duplicaten (overlap tussen GSheet history en Firestore on_snapshot)
    # Behoud verschillende seizoensresets (SEASON_RESET) en losse logs zonder match_id
    if not df.empty and 'match_id' in df.columns and 'speler_naam' in df.columns:
        mid_str = df['match_id'].fillna('').astype(str).str.strip()
        is_match_row = (mid_str != '') & (mid_str != 'SEASON_RESET')
        is_reset_row = (mid_str == 'SEASON_RESET')
        is_other_row = (mid_str == '')

        df_match = df[is_match_row].drop_duplicates(subset=['match_id', 'speler_naam'], keep='last')
        df_reset = df[is_reset_row].drop_duplicates(subset=['match_id', 'speler_naam', 'timestamp'], keep='last')
        df_other = df[is_other_row]
        df = pd.concat([df_match, df_reset, df_other], ignore_index=True)

    sort_cols = ['timestamp'] + [c for c in ['match_id', 'speler_naam'] if c in df.columns]
    asc = [False] + ([False] if 'match_id' in df.columns else []) + ([True] if 'speler_naam' in df.columns else [])
    df = df.sort_values(sort_cols, ascending=asc, na_position='last', kind='mergesort').reset_index(drop=True)
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
    req_list = [dict(d) for d in store["requests"].values() if isinstance(d, dict)]
    for d in req_list:
        if 'Timestamp' in d and 'timestamp' not in d:
            d['timestamp'] = d.pop('Timestamp')
        elif 'Timestamp' in d:
            d.pop('Timestamp')

    if not req_list:
        return _read_gsheet_fallback("Verzoeken")
    
    df = pd.DataFrame(req_list)
    if not df.empty and 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', format='mixed', utc=True)
        df['timestamp'] = normalize_timestamp_series(df['timestamp'])
        df = df.sort_values("timestamp", ascending=False, na_position='last').reset_index(drop=True)
        
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
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', format='mixed', utc=True)
        df['timestamp'] = normalize_timestamp_series(df['timestamp'])
        df = df.sort_values("timestamp", ascending=False, na_position='last').reset_index(drop=True)
    
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
    now_nl = _get_nl_now_naive()
    min_year = 2022
    max_year = now_nl.year + 1

    seizoenen = []
    for y in range(min_year, max_year + 1):
        s1, e1 = get_march15(y), get_prinsjesdag(y) - timedelta(seconds=1)
        seizoenen.append({'seizoen_naam': f"CJ {y} Zomer", 'start_datum': s1, 'eind_datum': e1, 'aantal_wedstrijden': 0})
        
        s2, e2 = get_prinsjesdag(y), get_march15(y+1) - timedelta(seconds=1)
        seizoenen.append({'seizoen_naam': f"CJ {y} Winter", 'start_datum': s2, 'eind_datum': e2, 'aantal_wedstrijden': 0})

    df_s = pd.DataFrame([s for s in seizoenen if s['start_datum'] <= now_nl])
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
def add_match_and_update_elo(match_data, elo_updates, update_current_rating=True):
    log_firestore_op("WRITE", "uitslag", "add_match", 1)
    log_firestore_op("WRITE", "elo", "add_match_elo", len(elo_updates))
    ts = match_data.get('timestamp') or pd.Timestamp.now()
    if hasattr(ts, 'to_pydatetime'):
        ts = ts.to_pydatetime()

    final_match_data = {
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

    name_to_id = {}
    if update_current_rating:
        try:
            p_df = get_players()
            if p_df is not None and not p_df.empty and 'speler_naam' in p_df.columns and 'speler_id' in p_df.columns:
                for _, prow in p_df.iterrows():
                    pid = prow.get('speler_id')
                    pname = prow.get('speler_naam')
                    if pname and pid and not str(pid).startswith("OFFLINE_"):
                        name_to_id[str(pname)] = str(pid)
        except Exception:
            name_to_id = {}

    try:
        batch = db.batch()
        new_match_ref = matches_ref.document()
        match_id = new_match_ref.id
        final_match_data['match_id'] = match_id
        batch.set(new_match_ref, final_match_data)

        for naam, elo in elo_updates:
            batch.set(elo_ref.document(), {'speler_naam': naam, 'rating': elo, 'timestamp': ts, 'match_id': match_id})
            if update_current_rating:
                pid = name_to_id.get(str(naam))
                if pid:
                    batch.update(players_ref.document(pid), {'rating': elo})
                else:
                    p_docs = players_ref.where(filter=FieldFilter('speler_naam', '==', naam)).limit(1).get()
                    if p_docs:
                        batch.update(p_docs[0].reference, {'rating': elo})

        batch.commit()
        clear_all_caches(only_players=bool(update_current_rating), only_matches=True, only_elo=True)
        return True
    except Exception:
        match_id = f"OFFLINE_{uuid.uuid4().hex[:10]}"
        final_match_data['match_id'] = match_id
        m_success = _write_gsheet_record("Wedstrijden", final_match_data)
        if m_success:
            elo_records = [{'speler_naam': naam, 'rating': elo, 'timestamp': ts, 'match_id': match_id} for naam, elo in elo_updates]
            _write_gsheet_records("ELO_Logs", elo_records)
            try:
                store = init_firestore_listeners()
                store["matches"][match_id] = dict(final_match_data)
                for rec in elo_records:
                    store["elo"][f"{match_id}_{rec['speler_naam']}"] = dict(rec)
            except Exception:
                pass
            set_offline_mode(True)
            clear_all_caches(only_players=bool(update_current_rating), only_matches=True, only_elo=True)
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


def rename_player(old_name: str, new_name: str) -> tuple[bool, str]:
    """Hernoemt een speler in Firestore (spelers, elo, uitslag) én best-effort in Google Sheets."""
    from utils.utils import IGNORE_PLAYERS

    clean_new = (new_name or "").strip()
    if not clean_new:
        return False, "Nieuwe naam mag niet leeg zijn."
    if clean_new == old_name:
        return False, "De naam is ongewijzigd."
    if len(clean_new) < 2 or len(clean_new) > 50:
        return False, "De lengte van de naam moet tussen de 2 en 50 tekens liggen."
    if not clean_new[0].isupper():
        return False, "De eerste letter van de naam moet een hoofdletter zijn."
    if not all(c.isalpha() or c in " -'" for c in clean_new):
        return False, "De naam mag alleen letters (en eventueel spaties, streepjes of apostrof) bevatten."
    if clean_new.lower().strip() in IGNORE_PLAYERS:
        return False, f"De naam '{clean_new}' is gereserveerd en kan niet gebruikt worden."

    def _norm(val):
        return str(val).replace(" ", "").lower()

    try:
        players_df = get_players()
        if players_df is not None and not players_df.empty and 'speler_naam' in players_df.columns:
            for existing in players_df['speler_naam'].astype(str).tolist():
                if existing != old_name and _norm(existing) == _norm(clean_new):
                    return False, f"Er bestaat al een speler met de naam '{existing}'. Gebruik 'admin/merge_players.py' om spelers samen te voegen."
    except Exception:
        pass

    log_firestore_op("WRITE", "spelers", "rename_player", 1)
    try:
        batch = db.batch()
        ops = 0

        def _commit_if_full(b, count):
            if count >= 400:
                b.commit()
                return db.batch(), 0
            return b, count

        for doc in players_ref.where(filter=FieldFilter('speler_naam', '==', old_name)).stream():
            batch.update(doc.reference, {'speler_naam': clean_new})
            batch, ops = _commit_if_full(batch, ops + 1)

        for doc in elo_ref.where(filter=FieldFilter('speler_naam', '==', old_name)).stream():
            batch.update(doc.reference, {'speler_naam': clean_new})
            batch, ops = _commit_if_full(batch, ops + 1)

        for field in ('thuis_1', 'thuis_2', 'uit_1', 'uit_2'):
            for doc in matches_ref.where(filter=FieldFilter(field, '==', old_name)).stream():
                batch.update(doc.reference, {field: clean_new})
                batch, ops = _commit_if_full(batch, ops + 1)

        if ops > 0:
            batch.commit()
    except Exception as e:
        print(f"Fout bij hernoemen van speler in Firestore: {e}")
        return False, f"Fout bij hernoemen in database: {e}"

    # Best-effort sync naar Google Sheets zodat hernoemde namen niet als spook-rijen terugkomen
    try:
        sh = _get_gsheet_workbook()
        if sh:
            sheet_col_map = [
                ("Spelers", ["speler_naam"]),
                ("ELO_Logs", ["speler_naam"]),
                ("Wedstrijden", ["thuis_1", "thuis_2", "uit_1", "uit_2"]),
            ]
            for sname, cols in sheet_col_map:
                try:
                    ws = sh.worksheet(sname)
                    vals = ws.get_all_values()
                    if not vals or len(vals) < 2:
                        continue
                    headers = [h.strip() for h in vals[0]]
                    target_indices = [headers.index(c) for c in cols if c in headers]
                    if not target_indices:
                        continue
                    changed = False
                    new_rows = [vals[0]]
                    for row in vals[1:]:
                        r_copy = list(row)
                        for idx in target_indices:
                            if idx < len(r_copy) and r_copy[idx] == old_name:
                                r_copy[idx] = clean_new
                                changed = True
                        new_rows.append(r_copy)
                    if changed:
                        _safe_replace_worksheet(ws, new_rows, existing_vals=vals)
                except Exception as gs_err:
                    print(f"[GSHEET RENAME] Fout bij bijwerken van {sname}: {gs_err}")
    except Exception as e:
        print(f"[GSHEET RENAME] Fout bij openen workbook: {e}")

    # Werk in-memory store direct bij
    try:
        store = init_firestore_listeners()
        for pdata in store.get("players", {}).values():
            if isinstance(pdata, dict) and pdata.get("speler_naam") == old_name:
                pdata["speler_naam"] = clean_new
        for edata in store.get("elo", {}).values():
            if isinstance(edata, dict) and edata.get("speler_naam") == old_name:
                edata["speler_naam"] = clean_new
        for mdata in store.get("matches", {}).values():
            if isinstance(mdata, dict):
                for field in ("thuis_1", "thuis_2", "uit_1", "uit_2"):
                    if mdata.get(field) == old_name:
                        mdata[field] = clean_new
    except Exception:
        pass

    clear_all_caches()
    return True, f"Naam van '{old_name}' aangepast naar '{clean_new}'."

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
            if hasattr(ts, 'to_pydatetime'):
                ts = ts.to_pydatetime()
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
    """Herberekent alle ELO scores voor een seizoen vanaf 1000 zonder latere seizoenen te overschrijven."""
    try:
        s_start, s_end = _season_bounds_naive(start_date, end_date)
        all_matches = get_matches()
        players_df = get_players()

        if all_matches is not None and not all_matches.empty:
            m_df = all_matches.copy()
            m_df['_ts_naive'] = normalize_timestamp_series(
                pd.to_datetime(m_df['timestamp'], errors='coerce', format='mixed', utc=True)
            )
            season_matches = m_df[(m_df['_ts_naive'] >= s_start) & (m_df['_ts_naive'] <= s_end)].copy()
        else:
            season_matches = pd.DataFrame()

        should_update_players = _should_update_global_player_ratings(all_matches, s_end)

        player_names = players_df['speler_naam'].tolist() if players_df is not None and not players_df.empty else []
        player_elos = {name: 1000.0 for name in player_names}

        # Verwijder ALLE ELO logs in dit seizoen (exacte grenzen zonder dag-overflow)
        start_ts_utc = s_start.tz_localize('UTC')
        end_ts_utc = s_end.tz_localize('UTC')

        old_elos = elo_ref.where(filter=FieldFilter('timestamp', '>=', start_ts_utc)).where(filter=FieldFilter('timestamp', '<=', end_ts_utc)).stream()
        batch = db.batch()
        c = 0
        for doc in old_elos:
            batch.delete(doc.reference)
            c += 1
            if c >= 400:
                batch.commit()
                batch = db.batch()
                c = 0
        if c > 0:
            batch.commit()

        # Stap 1: Voeg voor iedereen een baseline 1000 toe aan het begin van het seizoen
        batch = db.batch()
        c = 0
        reset_records = []
        for name in player_elos.keys():
            rec = {
                'speler_naam': name,
                'rating': 1000,
                'timestamp': s_start,
                'match_id': 'SEASON_RESET'
            }
            reset_records.append(rec)
            batch.set(elo_ref.document(), rec)
            c += 1
            if c >= 400:
                batch.commit()
                batch = db.batch()
                c = 0
        if c > 0:
            batch.commit()

        # Stap 2: Bereken matches opnieuw via replay_season_elos
        replayed_elos, _, match_records = replay_season_elos(season_matches)
        player_elos.update(replayed_elos)

        batch = db.batch()
        c = 0
        for rec in match_records:
            batch.set(elo_ref.document(), rec)
            c += 1
            if c >= 400:
                batch.commit()
                batch = db.batch()
                c = 0

        # Werk spelerstabel alleen bij als dit het nieuwste/huidige seizoen is
        updated_player_map = None
        if should_update_players:
            updated_player_map = player_elos
            name_to_id = (
                dict(zip(players_df['speler_naam'], players_df['speler_id']))
                if players_df is not None and not players_df.empty and 'speler_id' in players_df.columns
                else {}
            )
            for name, rating in player_elos.items():
                pid = name_to_id.get(name)
                if pid and not str(pid).startswith("OFFLINE_"):
                    batch.update(players_ref.document(str(pid)), {'rating': rating})
                    c += 1
                else:
                    p_docs = players_ref.where(filter=FieldFilter('speler_naam', '==', name)).limit(1).get()
                    if p_docs:
                        batch.update(p_docs[0].reference, {'rating': rating})
                        c += 1
                if c >= 400:
                    batch.commit()
                    batch = db.batch()
                    c = 0

        if c > 0:
            batch.commit()

        _sync_recalculated_elo_to_gsheet(
            s_start,
            s_end,
            reset_records + match_records,
            updated_player_elos=updated_player_map,
            include_season_reset=True,
        )
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
    """Registreert een uitgestelde herberekening (ondersteunt meerdere seizoenen in een wachtrij)."""
    try:
        config_ref = db.collection("system_config").document("elo_recalc")
        doc = config_ref.get()

        new_ts = pd.Timestamp(modified_timestamp)
        if new_ts.tzinfo is not None:
            new_ts = new_ts.tz_localize(None)

        s_start_ts = pd.Timestamp(season_start)
        if s_start_ts.tzinfo is not None:
            s_start_ts = s_start_ts.tz_localize(None)
        s_end_ts = pd.Timestamp(season_end)
        if s_end_ts.tzinfo is not None:
            s_end_ts = s_end_ts.tz_localize(None)

        pending = {}
        if doc.exists:
            data = doc.to_dict() or {}
            if data.get("recalc_needed"):
                existing_pending = data.get("pending_recalcs")
                if isinstance(existing_pending, dict) and existing_pending:
                    pending = {k: dict(v) for k, v in existing_pending.items() if isinstance(v, dict)}
                elif data.get("season_naam") and data.get("earliest_modified_timestamp"):
                    prev_name = str(data.get("season_naam"))
                    pending[prev_name] = {
                        "season_start": pd.Timestamp(data.get("season_start")),
                        "season_end": pd.Timestamp(data.get("season_end")),
                        "season_naam": prev_name,
                        "earliest_modified_timestamp": pd.Timestamp(data.get("earliest_modified_timestamp")),
                    }

        season_key = str(season_naam)
        if season_key in pending and pending[season_key].get("earliest_modified_timestamp"):
            prev_ts = pd.Timestamp(pending[season_key]["earliest_modified_timestamp"])
            if prev_ts.tzinfo is not None:
                prev_ts = prev_ts.tz_localize(None)
            effective_ts = min(prev_ts, new_ts)
        else:
            effective_ts = new_ts

        pending[season_key] = {
            "season_start": s_start_ts,
            "season_end": s_end_ts,
            "season_naam": season_key,
            "earliest_modified_timestamp": effective_ts,
        }

        def _norm_naive(val):
            t = pd.Timestamp(val)
            return t.tz_localize(None) if t.tzinfo is not None else t

        earliest_item = min(
            pending.values(),
            key=lambda item: (_norm_naive(item["earliest_modified_timestamp"]), _norm_naive(item["season_start"]))
        )

        config_ref.set({
            "recalc_needed": True,
            "season_start": _norm_naive(earliest_item["season_start"]),
            "season_end": _norm_naive(earliest_item["season_end"]),
            "season_naam": earliest_item["season_naam"],
            "earliest_modified_timestamp": _norm_naive(earliest_item["earliest_modified_timestamp"]),
            "pending_recalcs": pending,
            "timestamp": pd.Timestamp.now()
        }, merge=True)
        get_recalc_status.clear()
    except Exception as e:
        print(f"Error setting recalc flag: {e}")

def recalculate_elos_from(start_timestamp, season_start, season_end):
    """Herberekent ELO scores incrementeel vanaf een specifiek tijdstip binnen een seizoen."""
    try:
        s_start, s_end = _season_bounds_naive(season_start, season_end)

        start_ts_pd = pd.Timestamp(start_timestamp)
        if start_ts_pd.tzinfo is not None:
            start_ts_pd = start_ts_pd.tz_localize(None)

        all_matches = get_matches()
        players_df = get_players()

        if all_matches is not None and not all_matches.empty:
            m_df = all_matches.copy()
            m_df['_ts_naive'] = normalize_timestamp_series(
                pd.to_datetime(m_df['timestamp'], errors='coerce', format='mixed', utc=True)
            )
            season_matches = m_df[(m_df['_ts_naive'] >= s_start) & (m_df['_ts_naive'] <= s_end)].copy()
        else:
            season_matches = pd.DataFrame()

        should_update_players = _should_update_global_player_ratings(all_matches, s_end)

        # Replay wedstrijden vóór start_ts_pd in memory voor exacte K-factor & start-ratings
        past_matches = season_matches[season_matches['_ts_naive'] < start_ts_pd] if not season_matches.empty else pd.DataFrame()
        future_matches = season_matches[season_matches['_ts_naive'] >= start_ts_pd] if not season_matches.empty else pd.DataFrame()

        past_elos, past_counts, _ = replay_season_elos(past_matches)
        final_elos, _, new_records = replay_season_elos(
            future_matches,
            initial_elos=past_elos,
            initial_matches=past_counts,
        )

        # Verwijder oude match-ELO logs vanaf start_ts_pd binnen [start_ts, s_end] (zonder dag-overflow en zonder SEASON_RESET te wissen)
        start_ts_utc = start_ts_pd.tz_localize('UTC')
        end_ts_utc = s_end.tz_localize('UTC')

        old_elos = elo_ref.where(filter=FieldFilter('timestamp', '>=', start_ts_utc)).where(filter=FieldFilter('timestamp', '<=', end_ts_utc)).stream()
        batch = db.batch()
        c = 0
        for doc in old_elos:
            doc_dict = doc.to_dict() or {}
            if doc_dict.get('match_id') == 'SEASON_RESET':
                continue
            batch.delete(doc.reference)
            c += 1
            if c >= 400:
                batch.commit()
                batch = db.batch()
                c = 0
        if c > 0:
            batch.commit()

        batch = db.batch()
        c = 0
        for rec in new_records:
            batch.set(elo_ref.document(), rec)
            c += 1
            if c >= 400:
                batch.commit()
                batch = db.batch()
                c = 0

        # Werk spelers-tabel alleen bij als dit het nieuwste/huidige seizoen is
        updated_player_map = None
        if should_update_players and players_df is not None and not players_df.empty:
            updated_player_map = {
                name: final_elos.get(name, 1000.0)
                for name in players_df['speler_naam'].tolist()
            }
            for p_name, r_val in final_elos.items():
                if p_name not in updated_player_map:
                    updated_player_map[p_name] = r_val

            name_to_id = (
                dict(zip(players_df['speler_naam'], players_df['speler_id']))
                if 'speler_id' in players_df.columns
                else {}
            )
            for name, rating in updated_player_map.items():
                pid = name_to_id.get(name)
                if pid and not str(pid).startswith("OFFLINE_"):
                    batch.update(players_ref.document(str(pid)), {'rating': rating})
                    c += 1
                else:
                    p_docs = players_ref.where(filter=FieldFilter('speler_naam', '==', name)).limit(1).get()
                    if p_docs:
                        batch.update(p_docs[0].reference, {'rating': rating})
                        c += 1
                if c >= 400:
                    batch.commit()
                    batch = db.batch()
                    c = 0

        if c > 0:
            batch.commit()

        _sync_recalculated_elo_to_gsheet(
            start_ts_pd,
            s_end,
            new_records,
            updated_player_elos=updated_player_map,
            include_season_reset=False,
        )
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
                
                is_earlier = False
                if earliest_ts is None:
                    earliest_ts = ts_pd
                    is_earlier = True
                else:
                    earliest_ts_naive = earliest_ts.replace(tzinfo=None) if earliest_ts.tzinfo is not None else earliest_ts
                    if ts_naive < earliest_ts_naive:
                        earliest_ts = ts_pd
                        is_earlier = True
                        
                # Zoek seizoen
                s_row = seasons[(seasons['start_datum'] <= ts_naive) & (seasons['eind_datum'] >= ts_naive)]
                if not s_row.empty and (earliest_season_info is None or is_earlier):
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
    """Controleert of er een ELO-herberekening gepland staat en voert deze uit na 23:00 uur (NL-tijd)."""
    try:
        import google.cloud.firestore

        transaction = db.transaction()

        @google.cloud.firestore.transactional
        def check_and_claim_recalc(tx):
            config_ref = db.collection("system_config").document("elo_recalc")
            snapshot = config_ref.get(transaction=tx)
            if not snapshot.exists:
                return None

            data = snapshot.to_dict() or {}
            if not data.get("recalc_needed"):
                return None

            now_aware = _get_nl_now_aware()
            now_nl = now_aware.replace(tzinfo=None)
            if now_nl.hour >= 23:
                last_scheduled = now_nl.replace(hour=23, minute=0, second=0, microsecond=0)
            else:
                last_scheduled = (now_nl - timedelta(days=1)).replace(hour=23, minute=0, second=0, microsecond=0)

            last_recalc = _to_nl_naive(data.get("last_recalc_time"))

            if not last_recalc or last_recalc < last_scheduled:
                tx.update(config_ref, {
                    "recalc_needed": False,
                    "last_recalc_time": now_aware
                })
                return data
            return None

        recalc_data = check_and_claim_recalc(transaction)
        if recalc_data:
            get_recalc_status.clear()
            pending_map = recalc_data.get("pending_recalcs") or {}
            failed_pending = {}

            if isinstance(pending_map, dict) and pending_map:
                items = sorted(
                    [v for v in pending_map.values() if isinstance(v, dict)],
                    key=lambda x: pd.Timestamp(x.get("season_start") or x.get("earliest_modified_timestamp"))
                )
                for item in items:
                    sname = str(item.get("season_naam") or "unknown")
                    print(f"[RECALC] Transactie geclaimd voor seizoen {sname}. Starten vanaf {item.get('earliest_modified_timestamp')}...")
                    ok = recalculate_elos_from(
                        item.get("earliest_modified_timestamp"),
                        item.get("season_start"),
                        item.get("season_end"),
                    )
                    if not ok:
                        failed_pending[sname] = item
                success = len(failed_pending) == 0
            else:
                print(f"[RECALC] Transactie geclaimd voor seizoen {recalc_data.get('season_naam')}. Starten met herberekenen vanaf {recalc_data.get('earliest_modified_timestamp')}...")
                success = recalculate_elos_from(
                    recalc_data.get("earliest_modified_timestamp"),
                    recalc_data.get("season_start"),
                    recalc_data.get("season_end")
                )

            config_ref = db.collection("system_config").document("elo_recalc")
            if success:
                config_ref.update({
                    "earliest_modified_timestamp": None,
                    "pending_recalcs": {},
                })
                get_recalc_status.clear()
                print("[RECALC] ELO-herberekening succesvol afgerond.")
            else:
                print("[RECALC] ELO-herberekening (deels) mislukt. Vlag teruggezet naar True.")
                payload = {"recalc_needed": True}
                if failed_pending:
                    def _norm_naive(val):
                        t = pd.Timestamp(val)
                        return t.tz_localize(None) if t.tzinfo is not None else t
                    earliest_fail = min(
                        failed_pending.values(),
                        key=lambda item: (_norm_naive(item["earliest_modified_timestamp"]), _norm_naive(item["season_start"]))
                    )
                    payload.update({
                        "pending_recalcs": failed_pending,
                        "season_start": _norm_naive(earliest_fail["season_start"]),
                        "season_end": _norm_naive(earliest_fail["season_end"]),
                        "season_naam": earliest_fail["season_naam"],
                        "earliest_modified_timestamp": _norm_naive(earliest_fail["earliest_modified_timestamp"]),
                    })
                config_ref.update(payload)
                get_recalc_status.clear()
    except Exception as e:
        print(f"Fout bij checken/uitvoeren geplande ELO-herberekening: {e}")

def expected_schema():
    """Retourneert de verwachte Firestore schema-definities per collectie."""
    return {
        "spelers": {
            "required": {"speler_naam", "rating"},
            "optional": {"speler_id"},
            "derived_only_in_app": {"speler_id"},
        },
        "uitslag": {
            "required": {
                "timestamp",
                "thuis_1",
                "thuis_2",
                "uit_1",
                "uit_2",
                "thuis_score",
                "uit_score",
            },
            "optional": {
                "match_id",
                "klinkers_thuis_1",
                "klinkers_thuis_2",
                "klinkers_uit_1",
                "klinkers_uit_2",
            },
            "derived_only_in_app": {"match_id"},
        },
        "elo": {
            "required": {"speler_naam", "rating", "timestamp"},
            "optional": {"match_id"},
            "derived_only_in_app": set(),
        },
        "requests": {
            "required": {"Verzoek", "Timestamp"},
            "optional": {"verzoek", "timestamp"},
            "derived_only_in_app": {"id"},
        },
    }

def inspect_collections(max_docs=250):
    """Inspecteert de Firestore collecties aan de hand van de huidige in-memory store of een beperkte stream."""
    store = init_firestore_listeners()
    mapping = {
        "spelers": ("players", players_ref),
        "uitslag": ("matches", matches_ref),
        "elo": ("elo", elo_ref),
        "requests": ("requests", requests_ref),
    }
    results = {}
    for coll_name, (store_key, ref) in mapping.items():
        docs_list = list(store.get(store_key, {}).values())[:max_docs]
        if not docs_list:
            try:
                docs_list = [d.to_dict() for d in ref.limit(max_docs).stream()]
            except Exception:
                docs_list = []
        fields = set()
        for d in docs_list:
            if isinstance(d, dict):
                fields.update(d.keys())
        results[coll_name] = {
            "sample_size": len(docs_list),
            "fields": sorted(list(fields)),
            "examples": docs_list[:5],
        }
    return results