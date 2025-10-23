import streamlit as st
 
APP_TITLE = "Tafelvoetbal Competitie ⚽"

APP_ICON = "⚽"

LAYOUT = "centered"
 
def setup_page():

    st.set_page_config(

        page_title=APP_TITLE,

        page_icon=APP_ICON,

        layout=LAYOUT,

        initial_sidebar_state="auto",

        menu_items=None,

    )
 
    CSS = """
<style>

    /* ===== SIDEBAR ===== */

    [data-testid="stSidebar"] {

        background-color: #154273 !important;  /* blauw */

        color: #FFFFFF !important;

    }

    [data-testid="stSidebar"] * { color: #FFFFFF !important; }
 
    /* ===== HEADER ===== */

    [data-testid="stHeader"] {

        background-color: #CA005D !important;  /* roze */

        border-bottom: none;

        height: 3.5rem;

        display: flex;

        align-items: center;

        justify-content: center;  /* midden in de balk */

    }

    [data-testid="stHeader"]::before {

        content: "⚽  Tafelvoetbal Competitie";

        font-size: 1.3rem;

        font-weight: 600;

        color: white;

        letter-spacing: 0.5px;

    }
 
    /* ===== GLITTER ACHTERGROND ===== */

    [data-testid="stAppViewContainer"] {

        background: linear-gradient(180deg, #FFFFFF 0%, #FAF8FC 60%, #F4EFF7 100%);

        position: relative;

        overflow: visible;

        z-index: 1;

    }

    [data-testid="stAppViewContainer"]::before {

        content: "";

        position: fixed;

        inset: 0;

        background-image:

            radial-gradient(white 1px, transparent 1px),

            radial-gradient(rgba(200, 180, 220, 0.4) 1px, transparent 1px);

        background-size: 60px 60px, 120px 120px;

        animation: sparkle 20s linear infinite;

        opacity: 0.45;

        pointer-events: none;

        z-index: 0;

    }

    @keyframes sparkle {

        0% { background-position: 0 0, 0 0; }

        50% { background-position: 100px 80px, 200px 160px; }

        100% { background-position: 0 0, 0 0; }

    }
 
    /* ===== KNOPPEN ===== */

    .stButton > button {

        background-color: #8E6CA6;

        color: #FFFFFF;

        border: 0;

        border-radius: 8px;

        padding: 0.5rem 0.9rem;

        transition: 0.2s;

        position: relative;

        z-index: 2;

    }

    .stButton > button:hover {

        background-color: #42145F;

        transform: translateY(-1px);

    }
 
    /* ===== TABS ===== */

    .stTabs [data-baseweb="tab-list"] { gap: .25rem; }

    .stTabs [data-baseweb="tab"] {

        background: #F4EFF7;

        border-radius: 10px 10px 0 0;

        padding: .4rem .8rem;

        color: #154273;

        position: relative;

        z-index: 2;

    }

    .stTabs [aria-selected="true"] {

        background-color: #CA005D !important;

        color: #FFFFFF !important;

    }
 
    /* ===== TABELLEN ===== */

    .stDataFrame, .stTable { border-radius: 10px; overflow: hidden; }
</style>

    """
 
    st.markdown(CSS, unsafe_allow_html=True)

 