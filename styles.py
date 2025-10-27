import streamlit as st

# App configuratie constanten
APP_TITLE = "Tafelvoetbal Competitie ⚽"
APP_ICON = "⚽"
LAYOUT = "centered"

# Kleurenschema
COLORS = {
    'primary_blue': '#154273',      # Hoofdblauw - nu voor beide sidebar en header
    'secondary_blue': '#1a4d80',    # Iets lichtere blauw voor variatie
    'accent_purple': '#8E6CA6',     # Accentpaars
    'dark_purple': '#42145F',       # Donkerpaars
    'light_background': '#FAF8FC',  # Lichte achtergrond
    'soft_purple': '#F4EFF7',       # Zachte paarse tint
    'white': '#FFFFFF',             # Wit
    'bright_sparkle': 'rgba(255, 215, 0, 0.8)',     # Gouden glitter
    'purple_sparkle': 'rgba(142, 108, 166, 0.9)',   # Paarse glitter
    'silver_sparkle': 'rgba(192, 192, 192, 0.9)',   # Zilveren glitter
}

def setup_page():
    """Configureer Streamlit pagina en styles."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout=LAYOUT,
        initial_sidebar_state="auto",
        menu_items=None,
    )
    
    # Injecteer aangepaste CSS
    st.markdown(_get_custom_css(), unsafe_allow_html=True)

def _get_custom_css():
    """Genereer de complete CSS voor de applicatie."""
    return f"""
<style>
    /* ===== ALGEMENE BODY STYLING ===== */
    .main .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }}
    
    /* ===== SIDEBAR ===== */
    [data-testid="stSidebar"] {{
        background-color: {COLORS['primary_blue']} !important;
        color: {COLORS['white']} !important;
    }}
    
    /* Zorg ervoor dat alle sidebar tekst wit is */
    [data-testid="stSidebar"] * {{
        color: {COLORS['white']} !important;
    }}
    
    /* Sidebar links styling */
    [data-testid="stSidebar"] .css-1d391kg,
    [data-testid="stSidebar"] a {{
        color: {COLORS['white']} !important;
        text-decoration: none;
    }}
    
    [data-testid="stSidebar"] a:hover {{
        color: {COLORS['light_background']} !important;
        opacity: 0.8;
    }}
    
    /* ===== HEADER ===== */
    [data-testid="stHeader"] {{
        background-color: {COLORS['primary_blue']} !important;
        border-bottom: 2px solid {COLORS['accent_purple']};
        height: 4rem;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0 1rem;
    }}
    
    [data-testid="stHeader"]::before {{
        content: "⚽  Tafelvoetbal Competitie";
        font-size: 1.8rem;
        font-weight: 700;
        color: {COLORS['white']};
        letter-spacing: 1px;
        text-align: center;
        white-space: nowrap;
        line-height: 1;
    }}
    
    /* ===== GLITTER ACHTERGROND ===== */
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(135deg, {COLORS['white']} 0%, {COLORS['light_background']} 40%, {COLORS['soft_purple']} 100%);
        position: relative;
        min-height: 100vh;
    }}
    
    /* Glitter effect - veel zichtbaarder */
    [data-testid="stAppViewContainer"]::before {{
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-image:
            radial-gradient(circle at 15% 25%, {COLORS['bright_sparkle']} 2px, transparent 2px),
            radial-gradient(circle at 85% 75%, {COLORS['purple_sparkle']} 1.5px, transparent 1.5px),
            radial-gradient(circle at 35% 45%, {COLORS['silver_sparkle']} 1px, transparent 1px),
            radial-gradient(circle at 65% 15%, {COLORS['bright_sparkle']} 1.2px, transparent 1.2px),
            radial-gradient(circle at 25% 85%, {COLORS['purple_sparkle']} 0.8px, transparent 0.8px),
            radial-gradient(circle at 75% 55%, {COLORS['silver_sparkle']} 1.3px, transparent 1.3px);
        background-size: 150px 150px, 200px 200px, 100px 100px, 120px 120px, 80px 80px, 180px 180px;
        animation: sparkle 15s ease-in-out infinite;
        opacity: 1;
        pointer-events: none;
        z-index: 0;
    }}
    
    @keyframes sparkle {{
        0% {{ 
            background-position: 0 0, 0 0, 0 0, 0 0, 0 0, 0 0;
            opacity: 0.7;
        }}
        20% {{ 
            background-position: 30px 30px, 50px 50px, 20px 20px, 25px 25px, 15px 15px, 35px 35px;
            opacity: 1;
        }}
        40% {{ 
            background-position: 60px 60px, 100px 100px, 40px 40px, 50px 50px, 30px 30px, 70px 70px;
            opacity: 0.8;
        }}
        60% {{ 
            background-position: 90px 90px, 150px 150px, 60px 60px, 75px 75px, 45px 45px, 105px 105px;
            opacity: 1;
        }}
        80% {{ 
            background-position: 120px 120px, 200px 200px, 80px 80px, 100px 100px, 60px 60px, 140px 140px;
            opacity: 0.9;
        }}
        100% {{ 
            background-position: 150px 150px, 250px 250px, 100px 100px, 125px 125px, 75px 75px, 175px 175px;
            opacity: 0.7;
        }}
    }}
    
    /* Zorg ervoor dat content boven glitter staat */
    .main .block-container {{
        position: relative;
        z-index: 1;
        background-color: rgba(255, 255, 255, 0.75);
        border-radius: 15px;
        padding: 2rem;
        margin: 1rem auto;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
        backdrop-filter: blur(1px);
    }}
    
    /* ===== KNOPPEN ===== */
    .stButton > button {{
        background-color: {COLORS['accent_purple']};
        color: {COLORS['white']};
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-weight: 500;
        transition: all 0.3s ease;
        position: relative;
        z-index: 2;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }}
    
    .stButton > button:hover {{
        background-color: {COLORS['dark_purple']};
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }}
    
    .stButton > button:active {{
        transform: translateY(0);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }}
    
    /* ===== FORM SUBMIT BUTTONS ===== */
    .stForm .stButton > button {{
        background-color: {COLORS['accent_purple']};
        font-weight: 600;
    }}
    
    .stForm .stButton > button:hover {{
        background-color: {COLORS['dark_purple']};
    }}
    
    /* ===== TABS ===== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0.5rem;
        border-bottom: none;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        background: {COLORS['soft_purple']};
        border-radius: 12px 12px 0 0;
        padding: 0.6rem 1rem;
        color: {COLORS['primary_blue']};
        font-weight: 500;
        border: none;
        position: relative;
        z-index: 2;
        transition: all 0.2s ease;
    }}
    
    .stTabs [data-baseweb="tab"]:hover {{
        background-color: {COLORS['light_background']};
    }}
    
    .stTabs [aria-selected="true"] {{
        background-color: {COLORS['primary_blue']} !important;
        color: {COLORS['white']} !important;
        font-weight: 600;
    }}
    
    /* ===== TABELLEN ===== */
    .stDataFrame,
    .stTable {{
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        position: relative;
        z-index: 2;
    }}
    
    /* Table headers */
    .stDataFrame thead th,
    .stTable thead th {{
        background-color: {COLORS['primary_blue']} !important;
        color: {COLORS['white']} !important;
        font-weight: 600;
        padding: 1rem 0.5rem;
    }}
    
    /* Table rows */
    .stDataFrame tbody tr:nth-child(even),
    .stTable tbody tr:nth-child(even) {{
        background-color: {COLORS['light_background']};
    }}
    
    /* ===== TEXT INPUT FIELDS ===== */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stNumberInput > div > div > input {{
        border-radius: 8px;
        border: 2px solid {COLORS['soft_purple']};
        position: relative;
        z-index: 2;
    }}
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stNumberInput > div > div > input:focus {{
        border-color: {COLORS['accent_purple']};
        box-shadow: 0 0 0 2px rgba(142, 108, 166, 0.2);
    }}
    
    /* ===== SUCCESS/ERROR MESSAGES ===== */
    .stSuccess {{
        background-color: rgba(40, 167, 69, 0.1);
        border: 1px solid #28a745;
        border-radius: 8px;
        color: #155724;
        position: relative;
        z-index: 2;
    }}
    
    .stError {{
        background-color: rgba(220, 53, 69, 0.1);
        border: 1px solid #dc3545;
        border-radius: 8px;
        color: #721c24;
        position: relative;
        z-index: 2;
    }}
    
    .stWarning {{
        background-color: rgba(255, 193, 7, 0.1);
        border: 1px solid #ffc107;
        border-radius: 8px;
        color: #856404;
        position: relative;
        z-index: 2;
    }}
    
    .stInfo {{
        background-color: rgba(23, 162, 184, 0.1);
        border: 1px solid #17a2b8;
        border-radius: 8px;
        color: #0c5460;
        position: relative;
        z-index: 2;
    }}
    
    /* ===== HEADERS EN TITLES ===== */
    h1, h2, h3 {{
        color: {COLORS['primary_blue']};
        position: relative;
        z-index: 2;
    }}
    
    .main h1 {{
        border-bottom: 3px solid {COLORS['accent_purple']};
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    }}
    
    /* ===== DIVIDERS ===== */
    hr {{
        border: none;
        height: 3px;
        background: linear-gradient(90deg, {COLORS['primary_blue']}, {COLORS['accent_purple']});
        border-radius: 2px;
        margin: 2rem 0;
        position: relative;
        z-index: 2;
    }}
    
    /* ===== SPINNER ===== */
    .stSpinner > div {{
        border-top-color: {COLORS['accent_purple']} !important;
    }}
</style>
"""

 