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
st.caption("Versie 2.1")

# --- Offline alert ---
if hasattr(db, 'is_offline') and db.is_offline():
    st.error("Firestore is offline. Back-up CSV data wordt gebruikt en kan achterlopen.")
    st.caption("Ingevoerde gegevens worden in de wachtrij geplaatst en later gesynchroniseerd.")

# --- Tab navigatie ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🏠 Home", 
    "📝 Invullen", 
    "👥 Spelers", 
    "📅 Seizoenen",
    "📊 Ruwe Data", 
    "⚙️ Beheer", 
    "💬 Verzoeken",
    "ℹ️ Colofon"
])



# ===== TAB 1: HOME =====
with tab1:
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — CSV-backup actief")
    players_df = db.get_players()
    matches_df = db.get_matches()
    render_home_tab(players_df, matches_df)

# ===== TAB 2: INVULLEN =====
with tab2:
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — invoer in wachtrij")
    players_df = db.get_players()
    render_input_tab(players_df)

# ===== TAB 3: SPELERS =====
with tab3:
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — CSV-backup actief")
    players_df = db.get_players()
    render_players_tab(players_df)

# ===== TAB 4: SEIZOENEN =====
with tab4:
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — CSV-backup actief")
    matches_df = db.get_matches()
    players_df = db.get_players()
    seasons_df = db.get_seasons()
    render_seizoenen_tab(matches_df, players_df, seasons_df)

# ===== TAB 5: RUWE DATA =====

# ===== TAB 5: RUWE DATA =====
with tab5:
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — CSV-backup actief")
    render_data_tab()

# ===== TAB 6: BEHEER =====
with tab6:
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — beheer kan beperkt zijn")
    players_df = db.get_players()
    matches_df = db.get_matches()
    render_admin_tab(db, players_df, matches_df)

# ===== TAB 7: VERZOEKEN =====
with tab7:
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — CSV-backup actief")
    matches_df = db.get_matches()
    render_verzoeken_tab(matches_df)

# ===== TAB 8: COLOFON =====
with tab8:
    if hasattr(db, 'is_offline') and db.is_offline():
        st.caption("🔴 Offline modus — CSV-backup actief")
    render_colofon_tab()