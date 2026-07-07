# Force redeploy to clear cache - 2026-03-23 (v2.6)
from tabs.tab_analytics import render_seizoenen_tab
import streamlit as st
import pandas as pd
import time
from datetime import date, datetime
import firestore_service as db # Use Firestore
from styles import setup_page
from utils.utils import add_name, get_download_filename
import plotly.express as px
import plotly.graph_objects as go
# Import nieuwe modules
from analytics import show_timeline_chart, show_cross_season_charts, show_individual_season_analysis, create_all_time_leaderboards
import utils.utils_seizoen as utils_seizoen  # Import hele module om functie parameters correct te kunnen gebruiken
# Import TAB modules
from tabs.tab_home import render_home_tab, calculate_stats
from tabs.tab_invullen import render_input_tab
from tabs.tab_spelers import render_players_tab


from tabs.tab_verzoeken import render_verzoeken_tab
from tabs.tab_data import render_data_tab
from tabs.tab_beheer import render_admin_tab
from tabs.tab_colofon import render_colofon_tab
from tabs.tab_commits import render_commits_tab
from tabs.tab_logging import render_logging_tab

setup_page()

import threading

st.title("Tafelvoetbal Competitie ⚽")
st.caption("Versie 2.5")

# Check of ELO herberekening gepland is
recalc_status = db.get_recalc_status()
if recalc_status and recalc_status.get("recalc_needed"):
    st.warning("⚠️ **ELO-herberekening gepland:** Er zijn recente wijzigingen in de wedstrijden. De ELO-scores en ranglijsten worden vanavond om 23:00 uur automatisch herberekend.")
    
    import pandas as pd
    from datetime import datetime, timedelta
    now = datetime.now()
    if now.hour >= 23:
        last_scheduled = now.replace(hour=23, minute=0, second=0, microsecond=0)
    else:
        last_scheduled = (now - timedelta(days=1)).replace(hour=23, minute=0, second=0, microsecond=0)
        
    last_recalc = recalc_status.get("last_recalc_time")
    if last_recalc:
        last_recalc = pd.Timestamp(last_recalc).to_pydatetime()
        if last_recalc.tzinfo is not None:
            last_recalc = last_recalc.replace(tzinfo=None)
            
    if not last_recalc or last_recalc < last_scheduled:
        threading.Thread(target=db.check_and_run_scheduled_recalc, daemon=True).start()

# --- Data Loading (Cached) ---
# Versie-parameter om cache geforceerd te kunnen resetten bij logica-wijzigingen
CACHE_VERSION = "2.1" 

# Bij een nieuwe versie, leeg de cache (voorzichtiger om quota te sparen)
if 'cache_version' not in st.session_state or st.session_state.cache_version != CACHE_VERSION:
    # Leeg de gehele Streamlit cache bij een nieuwe versie
    if 'cache_version' in st.session_state:
        st.cache_data.clear()
    st.session_state.cache_version = CACHE_VERSION

def load_all_data(version):
    load_start = time.perf_counter()

    p = db.get_players()
    m = db.get_matches()
    s = db.get_seasons()
    e = db.get_elo_logs()
    b = db.get_beheer_log()
    r = db.get_requests()
    
    load_end = time.perf_counter()
    print(f"[TIMING] data load (v{version}): players={len(p) if p is not None else 0}, matches={len(m) if m is not None else 0}, seasons={len(s) if s is not None else 0}, elo={len(e) if e is not None else 0} in {load_end-load_start:.3f}s")
    return p, m, s, e, b, r





# --- Sidebar met Refresh optie ---
with st.sidebar:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    st.divider()

# --- Initialize data ---
players_df, matches_df, seasons_df, elo_df, beheer_log_df, requests_df = load_all_data(CACHE_VERSION)

# --- Diagnostics ---
if (players_df is None or players_df.empty) and (matches_df is None or matches_df.empty):
    st.warning("⚠️ Geen data kunnen laden uit Firestore of Google Sheets.")
    if hasattr(db, 'is_offline') and db.is_offline():
        st.info("De app staat momenteel in OFFLINE modus.")
        fallback_error = db.get_last_fallback_error()
        if fallback_error:
            st.error(f"Specifieke GSheet fout: `{fallback_error}`")
        else:
            st.info("De Google Sheet fallback gaf geen fout, maar ook geen data. Controleer de tabbladen in de Sheet.")
    else:
        st.info("De app denkt dat Firestore ONLINE is, maar krijgt geen records terug. Controleer de database-verbinding.")

# --- Timing (server logs) ---
app_start = time.perf_counter()

# --- Offline alert ---
if hasattr(db, 'is_offline') and db.is_offline():
    st.error("⚠️ De database is momenteel offline (waarschijnlijk door het overschrijden van de dagelijkse quota).")
    st.info(f"📊 De meest recente data is nog steeds inzichtelijk via de [Google Sheet Backup](https://docs.google.com/spreadsheets/d/1cCiNoYfro9SqS8qIjEKT8prsAvAA7wowvhzhh2ljHnA). Nieuwe invoer is nog steeds mogelijk.")

# --- Tab navigatie ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "🏠 Home", 
    "📝 Invullen", 
    "👥 Spelers", 
    "📈 Analytics",
    "📊 Ruwe Data", 
    "💬 Verzoeken",
    "📜 Commits",
    "🔍 Logging",
    "ℹ️ Colofon",
    "⚙️ Beheer"
])



# ===== TAB 1: HOME =====
with tab1:
    t0 = time.perf_counter()
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — Google Sheet backup actief")
    render_home_tab(players_df, matches_df, seasons_df, elo_df)
    t1 = time.perf_counter()
    print(f"[TIMING] tab HOME rendered in {t1-t0:.3f}s")

# ===== TAB 2: INVULLEN =====
with tab2:
    t0 = time.perf_counter()
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — invoer in wachtrij")
    render_input_tab(players_df, matches_df)
    t1 = time.perf_counter()
    print(f"[TIMING] tab INVULLEN rendered in {t1-t0:.3f}s")

# ===== TAB 3: SPELERS =====

with tab3:
    t0 = time.perf_counter()
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — Google Sheet backup actief")
    render_players_tab(players_df, matches_df, seasons_df, elo_df)
    t1 = time.perf_counter()
    print(f"[TIMING] tab SPELERS rendered in {t1-t0:.3f}s")

# ===== TAB 4: ANALYTICS =====
with tab4:
    t0 = time.perf_counter()
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — Google Sheet backup actief")
    render_seizoenen_tab(matches_df, players_df, seasons_df, elo_df)
    t1 = time.perf_counter()
    print(f"[TIMING] tab ANALYTICS rendered in {t1-t0:.3f}s")

# ===== TAB 5: RUWE DATA =====

# ===== TAB 5: RUWE DATA =====
with tab5:
    t0 = time.perf_counter()
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — Google Sheet backup actief")
    render_data_tab(matches_df, elo_df, players_df, beheer_log_df, requests_df)
    t1 = time.perf_counter()
    print(f"[TIMING] tab RUWE DATA rendered in {t1-t0:.3f}s")

# ===== TAB 10: BEHEER =====
with tab10:
    t0 = time.perf_counter()
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — beheer kan beperkt zijn")
    render_admin_tab(db, players_df, matches_df)
    t1 = time.perf_counter()
    print(f"[TIMING] tab BEHEER rendered in {t1-t0:.3f}s")

# ===== TAB 6: VERZOEKEN =====
with tab6:
    t0 = time.perf_counter()
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — Google Sheet backup actief")
    render_verzoeken_tab(requests_df)
    t1 = time.perf_counter()
    print(f"[TIMING] tab VERZOEKEN rendered in {t1-t0:.3f}s")

# ===== TAB 7: COMMITS =====
with tab7:
    t0 = time.perf_counter()
    render_commits_tab()
    t1 = time.perf_counter()
    print(f"[TIMING] tab COMMITS rendered in {t1-t0:.3f}s")

# ===== TAB 8: LOGGING =====
with tab8:
    t0 = time.perf_counter()
    render_logging_tab(beheer_log_df)
    t1 = time.perf_counter()
    print(f"[TIMING] tab LOGGING rendered in {t1-t0:.3f}s")

# ===== TAB 9: COLOFON =====
with tab9:
    t0 = time.perf_counter()
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — Google Sheet backup actief")
    render_colofon_tab()
    t1 = time.perf_counter()
    print(f"[TIMING] tab COLOFON rendered in {t1-t0:.3f}s")

app_end = time.perf_counter()
print(f"[TIMING] app run total {app_end-app_start:.3f}s")
