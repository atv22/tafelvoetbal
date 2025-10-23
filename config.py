import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
SHEET_NAME = "Tafelvoetbal"
@st.cache_resource(show_spinner=False)
def get_client():
    skey = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(skey, scopes=SCOPES)
    return gspread.authorize(credentials)
@st.cache_data(show_spinner=False)
def get_players_list():
    client = get_client()
    names_ws = client.open(SHEET_NAME).worksheet("Namen")
    players = names_ws.col_values(1)[1:]  # skip header
    return players
@st.cache_data(show_spinner=False)
def get_uitslag_df() -> pd.DataFrame:
    client = get_client()
    ws = client.open(SHEET_NAME).worksheet("Uitslag")
    all_values = ws.get_all_values()
    df = pd.DataFrame(all_values[1:], columns=all_values[0])
    # type casting
    int_cols = [
        "Thuis_score","Uit_score",
        "Klinkers_thuis_1","Klinkers_thuis_2","Klinkers_uit_1","Klinkers_uit_2",
    ]
    for c in int_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df
@st.cache_data(show_spinner=False)
def get_verzoeken_df() -> pd.DataFrame:
    client = get_client()
    ws = client.open(SHEET_NAME).worksheet("Verzoeken")
    all_values = ws.get_all_values()
    return pd.DataFrame(all_values[1:], columns=all_values[0])
@st.cache_data(show_spinner=False)
def get_public_sheet_url() -> str:
    return st.secrets["private_gsheets_url"].public_gsheets_url