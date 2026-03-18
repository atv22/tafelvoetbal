from tab_analytics import render_seizoenen_tab
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
from tab_home import render_home_tab, calculate_stats
from tab_invullen import render_input_tab
from tab_spelers import render_players_tab


from tab_verzoeken import render_verzoeken_tab
from tab_data import render_data_tab
from tab_beheer import render_admin_tab
from tab_colofon import render_colofon_tab

setup_page()

st.title("Tafelvoetbal Competitie ⚽")
st.caption("Versie 2.5")

# --- Data Loading (Cached) ---
# Versie-parameter om cache geforceerd te kunnen resetten bij logica-wijzigingen
CACHE_VERSION = "1.9" 

@st.cache_data(ttl=600)  # Cache voor 10 minuten
def load_all_data(version):
    load_start = time.perf_counter()
    p = db.get_players()
    m = db.get_matches()
    s = db.get_seasons()
    e = db.get_elo_logs()
    load_end = time.perf_counter()
    print(f"[TIMING] data load (v{version}): players={len(p) if p is not None else 0}, matches={len(m) if m is not None else 0}, seasons={len(s) if s is not None else 0}, elo={len(e) if e is not None else 0} in {load_end-load_start:.3f}s")
    return p, m, s, e

# --- Sidebar met Refresh optie ---
with st.sidebar:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    st.divider()

# --- Initialize data ---
players_df, matches_df, seasons_df, elo_df = load_all_data(CACHE_VERSION)

# --- Timing (server logs) ---
app_start = time.perf_counter()

# --- Offline alert ---
if hasattr(db, 'is_offline') and db.is_offline():
    st.error("Firestore is offline. Back-up CSV data wordt gebruikt en kan achterlopen.")
    st.caption("Ingevoerde gegevens worden in de wachtrij geplaatst en later gesynchroniseerd.")

# --- Tab navigatie ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🏠 Home", 
    "📝 Invullen", 
    "👥 Spelers", 
    "📈 Analytics",
    "📊 Ruwe Data", 
    "⚙️ Beheer", 
    "💬 Verzoeken",
    "ℹ️ Colofon"
])



# ===== TAB 1: HOME =====
with tab1:
    t0 = time.perf_counter()
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — CSV-backup actief")
    render_home_tab(players_df, matches_df, seasons_df, elo_df)
    t1 = time.perf_counter()
    print(f"[TIMING] tab HOME rendered in {t1-t0:.3f}s")

# ===== TAB 2: INVULLEN =====
with tab2:
    t0 = time.perf_counter()
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — invoer in wachtrij")
    render_input_tab(players_df)
    t1 = time.perf_counter()
    print(f"[TIMING] tab INVULLEN rendered in {t1-t0:.3f}s")

# ===== TAB 3: SPELERS =====

with tab3:
    t0 = time.perf_counter()
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — CSV-backup actief")
    render_players_tab(players_df, matches_df, seasons_df, elo_df)
    t1 = time.perf_counter()
    print(f"[TIMING] tab SPELERS rendered in {t1-t0:.3f}s")

# ===== TAB 4: ANALYTICS =====
with tab4:
    t0 = time.perf_counter()
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — CSV-backup actief")
    render_seizoenen_tab(matches_df, players_df, seasons_df, elo_df)
    t1 = time.perf_counter()
    print(f"[TIMING] tab ANALYTICS rendered in {t1-t0:.3f}s")

# ===== TAB 5: RUWE DATA =====

# ===== TAB 5: RUWE DATA =====
with tab5:
    t0 = time.perf_counter()
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — CSV-backup actief")
    render_data_tab()
    t1 = time.perf_counter()
    print(f"[TIMING] tab RUWE DATA rendered in {t1-t0:.3f}s")

# ===== TAB 6: BEHEER =====
with tab6:
    t0 = time.perf_counter()
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — beheer kan beperkt zijn")
    render_admin_tab(db, players_df, matches_df)
    t1 = time.perf_counter()
    print(f"[TIMING] tab BEHEER rendered in {t1-t0:.3f}s")

# ===== TAB 7: VERZOEKEN =====
with tab7:
    t0 = time.perf_counter()
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — CSV-backup actief")
    render_verzoeken_tab(matches_df)
    t1 = time.perf_counter()
    print(f"[TIMING] tab VERZOEKEN rendered in {t1-t0:.3f}s")

# ===== TAB 8: COLOFON =====
with tab8:
    t0 = time.perf_counter()
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — CSV-backup actief")
    render_colofon_tab()
    t1 = time.perf_counter()
    print(f"[TIMING] tab COLOFON rendered in {t1-t0:.3f}s")

app_end = time.perf_counter()
print(f"[TIMING] app run total {app_end-app_start:.3f}s")
