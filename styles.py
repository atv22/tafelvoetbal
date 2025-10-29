import streamlit as st

# App configuratie constanten
APP_TITLE = "Tafelvoetbal Competitie ⚽"
APP_ICON = "⚽"
LAYOUT = "centered"

# Kleurenschema - ADR roze en MinFin blauw
COLORS = {
    'primary_pink': '#ca005d',      # ADR roze (primair)
    'secondary_blue': '#154273',    # MinFin blauw (secundair)
    'light_pink': '#f5e6ed',        # Lichte roze achtergrond
    'soft_pink': '#f0d7e1',         # Zachte roze tint
    'dark_pink': '#9a0048',         # Donkere roze voor accenten
    'accent_blue': '#1a4d80',       # Accent blauw (iets lichter)
    'white': '#FFFFFF',             # Wit
    'light_background': '#fdfcfd',  # Zeer lichte achtergrond
    'bright_sparkle': 'rgba(202, 0, 93, 0.8)',      # Roze glitter
    'blue_sparkle': 'rgba(21, 66, 115, 0.7)',       # Blauwe glitter
    'silver_sparkle': 'rgba(192, 192, 192, 0.6)',   # Zilveren glitter
}

def setup_page():
    """Configureer Streamlit pagina en styles."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",  # Gebruik volledige breedte zonder sidebar
        initial_sidebar_state="collapsed",  # Zorg dat sidebar weg is
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': None
        },
    )
    
    # Forceer light mode
    st.markdown("""
    <script>
    // Force light theme
    const stApp = window.parent.document.querySelector('.stApp');
    if (stApp) {
        stApp.classList.remove('dark-theme');
        stApp.classList.add('light-theme');
    }
    </script>
    """, unsafe_allow_html=True)
    
    # Injecteer aangepaste CSS
    st.markdown(_get_custom_css(), unsafe_allow_html=True)
    
    # Voeg minimale JavaScript toe
    st.markdown(_get_mobile_js(), unsafe_allow_html=True)

def _get_mobile_js():
    """Minimale JavaScript - laat Streamlit sidebar met rust."""
    return """
    <script>
    // Alleen noodzakelijke mobile optimalisaties
    document.addEventListener('DOMContentLoaded', function() {
        // Zorg voor juiste viewport gedrag
        function optimizeViewport() {
            const viewport = document.querySelector('meta[name="viewport"]');
            if (!viewport) {
                const meta = document.createElement('meta');
                meta.name = 'viewport';
                meta.content = 'width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes';
                document.head.appendChild(meta);
            }
        }
        
        optimizeViewport();
    });
    </script>
    """

def _get_custom_css():
    """Genereer de complete CSS voor de applicatie."""
    return f"""
<style>
    /* ===== FORCEER LIGHT MODE ===== */
    .stApp {{
        background-color: {COLORS['white']} !important;
        color: #262730 !important;
    }}
    
    /* Verberg dark mode toggle als die er is */
    [data-testid="stSidebar"] button[title*="theme"] {{
        display: none !important;
    }}
    
    /* Forceer light theme op alle content */
    .main, .block-container, .element-container {{
        background-color: transparent !important;
        color: #262730 !important;
    }}
    
    /* ===== STREAMLIT HEADER/MENU STYLING ===== */
    /* Maak alle Streamlit header teksten wit voor contrast tegen roze */
    [data-testid="stHeader"] * {{
        color: {COLORS['white']} !important;
    }}
    
    /* GitHub link, Fork button, etc. in de header */
    [data-testid="stHeader"] a,
    [data-testid="stHeader"] button,
    [data-testid="stHeader"] span,
    [data-testid="stHeader"] div {{
        color: {COLORS['white']} !important;
    }}
    
    /* Menu items wit maken */
    [data-testid="stHeader"] svg {{
        fill: {COLORS['white']} !important;
    }}
    
    /* Zorg dat hover states ook wit blijven */
    [data-testid="stHeader"] a:hover,
    [data-testid="stHeader"] button:hover {{
        color: rgba(255, 255, 255, 0.8) !important;
    }}
    
    /* ===== MOBILE VIEWPORT EN TOUCH OPTIMALISATIE ===== */
    * {{
        -webkit-tap-highlight-color: transparent;
        -webkit-touch-callout: none;
        -webkit-user-select: none;
        -khtml-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
        user-select: none;
    }}
    
    input, textarea, select {{
        -webkit-user-select: text;
        -moz-user-select: text;
        -ms-user-select: text;
        user-select: text;
    }}
    
    html {{
        font-size: 16px;
        -webkit-text-size-adjust: 100%;
        -ms-text-size-adjust: 100%;
    }}
    
    body {{
        -webkit-overflow-scrolling: touch;
        overscroll-behavior: none;
    }}
    
    /* ===== ALGEMENE BODY STYLING ===== */
    .main .block-container {{
        padding-top: 0.5rem !important; /* Verminder lege ruimte */
        padding-bottom: 2rem;
        max-width: 95vw;
        width: 100%;
        padding-left: 1rem;
        padding-right: 1rem;
    }}
    
    /* Zorg ervoor dat content containers volledige breedte gebruiken */
    .stContainer > div,
    .element-container {{
        width: 100% !important;
        max-width: 100% !important;
    }}
    
    /* Verwijder extra marges van de app container */
    .stApp > div {{
        padding-top: 0 !important;
    }}
    
    /* Zorg dat de main content direct onder header begint */
    .main {{
        padding-top: 0 !important;
        margin-top: 0 !important;
    }}
    
    /* Mobile optimizations voor main content */
    @media (max-width: 768px) {{
        .main .block-container {{
            padding-top: 0.3rem !important; /* Nog minder ruimte op mobiel */
            padding-bottom: 1rem;
            padding-left: 0.5rem;
            padding-right: 0.5rem;
            max-width: 98vw;
        }}
    }}
    
    @media (max-width: 480px) {{
        .main .block-container {{
            padding-top: 0.2rem !important; /* Minimale ruimte op kleine schermen */
            padding-bottom: 0.5rem;
            padding-left: 0.3rem;
            padding-right: 0.3rem;
            max-width: 100vw;
        }}
    }}
    
    /* ===== VERBERG SIDEBAR COMPLEET ===== */
    [data-testid="stSidebar"] {{
        display: none !important;
    }}
    
    [data-testid="collapsedControl"] {{
        display: none !important;
    }}
    
    /* Zorg dat main content volledige breedte gebruikt */
    .main .block-container {{
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }}
    
    /* ===== TABS STYLING ===== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0.3rem;
        border-bottom: 2px solid {COLORS['primary_pink']};
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
        background: transparent;
        flex-wrap: wrap; /* Allow wrapping on mobile */
    }}
    
    .stTabs [data-baseweb="tab"] {{
        background: {COLORS['soft_pink']};
        border-radius: 12px 12px 0 0;
        padding: 0.8rem 1.2rem;
        color: {COLORS['primary_pink']};
        font-weight: 500;
        border: none;
        position: relative;
        z-index: 2;
        transition: all 0.2s ease;
        white-space: nowrap;
        min-height: 48px; /* Touch-friendly */
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    
    .stTabs [data-baseweb="tab"]:hover {{
        background-color: {COLORS['light_pink']};
        transform: translateY(-2px);
    }}
    
    .stTabs [aria-selected="true"] {{
        background-color: {COLORS['primary_pink']} !important;
        color: {COLORS['white']} !important;
        font-weight: 600;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }}
    
    /* Tab content styling */
    .stTabs [data-baseweb="tab-panel"] {{
        padding: 1.5rem 1rem;
        background: rgba(255, 255, 255, 0.7);
        border-radius: 0 12px 12px 12px;
        border: 1px solid {COLORS['soft_pink']};
        position: relative;
        z-index: 1;
    }}
    
    /* Mobile tab optimizations */
    @media (max-width: 768px) {{
        .stTabs [data-baseweb="tab-list"] {{
            justify-content: flex-start;
            overflow-x: auto;
            padding-bottom: 0.8rem;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            padding: 0.6rem 1rem;
            font-size: 0.9rem;
            min-width: 80px;
            flex-shrink: 0;
        }}
        
        .stTabs [data-baseweb="tab-panel"] {{
            padding: 1rem 0.5rem;
            border-radius: 0 8px 8px 8px;
        }}
    }}
    
    @media (max-width: 480px) {{
        .stTabs [data-baseweb="tab"] {{
            padding: 0.7rem 0.8rem;
            font-size: 0.8rem;
            min-width: 70px;
        }}
        
        .stTabs [data-baseweb="tab-list"] {{
            gap: 0.2rem;
        }}
        
        .stTabs [data-baseweb="tab-panel"] {{
            padding: 0.8rem 0.3rem;
        }}
    }}
    
    /* ===== HEADER ===== */
    [data-testid="stHeader"] {{
        background-color: {COLORS['primary_pink']} !important;
        border-bottom: 2px solid {COLORS['secondary_blue']};
        height: 4rem;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0 1rem;
        position: relative;
        z-index: 100;
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
    
    /* Mobile header optimizations */
    @media (max-width: 768px) {{
        [data-testid="stHeader"] {{
            height: 3.5rem;
            padding: 0 60px 0 0.5rem; /* Extra ruimte voor hamburger menu */
        }}
        
        [data-testid="stHeader"]::before {{
            font-size: 1.3rem;
            letter-spacing: 0.5px;
        }}
    }}
    
    @media (max-width: 480px) {{
        [data-testid="stHeader"] {{
            height: 3rem;
            padding: 0 60px 0 0.5rem;
        }}
        
        [data-testid="stHeader"]::before {{
            font-size: 1.1rem;
            letter-spacing: 0.3px;
            content: "⚽ Tafelvoetbal"; /* Kortere titel op zeer kleine schermen */
        }}
    }}
    
    /* ===== GLITTER ACHTERGROND ===== */
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(135deg, {COLORS['white']} 0%, {COLORS['light_background']} 40%, {COLORS['soft_pink']} 100%);
        position: relative;
        min-height: 100vh;
    }}
    
    /* Glitter effect - roze en blauw thema */
    [data-testid="stAppViewContainer"]::before {{
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-image:
            radial-gradient(circle at 15% 25%, {COLORS['bright_sparkle']} 2px, transparent 2px),
            radial-gradient(circle at 85% 75%, {COLORS['blue_sparkle']} 1.5px, transparent 1.5px),
            radial-gradient(circle at 35% 45%, {COLORS['silver_sparkle']} 1px, transparent 1px),
            radial-gradient(circle at 65% 15%, {COLORS['bright_sparkle']} 1.2px, transparent 1.2px),
            radial-gradient(circle at 25% 85%, {COLORS['blue_sparkle']} 0.8px, transparent 0.8px),
            radial-gradient(circle at 75% 55%, {COLORS['silver_sparkle']} 1.3px, transparent 1.3px);
        background-size: 150px 150px, 200px 200px, 100px 100px, 120px 120px, 80px 80px, 180px 180px;
        animation: sparkle 1s ease-in-out infinite;
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
        padding: 1.5rem 1.5rem; /* Verminder top padding */
        margin: 0.5rem auto; /* Verminder top margin */
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
        backdrop-filter: blur(1px);
        width: 100%;
        max-width: 95vw;
    }}
    
    /* Mobile content container optimizations */
    @media (max-width: 768px) {{
        .main .block-container {{
            padding: 1.5rem 1rem;
            margin: 0.5rem auto;
            border-radius: 12px;
            max-width: 98vw;
        }}
    }}
    
    @media (max-width: 480px) {{
        .main .block-container {{
            padding: 1rem 0.8rem;
            margin: 0.3rem auto;
            border-radius: 10px;
            max-width: 99vw;
        }}
    }}
    
    /* ===== KNOPPEN ===== */
    .stButton > button {{
        background-color: {COLORS['primary_pink']};
        color: {COLORS['white']};
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-weight: 500;
        transition: all 0.3s ease;
        position: relative;
        z-index: 2;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        width: auto;
        min-height: 44px; /* Minimale touch target grootte */
    }}
    
    .stButton > button:hover {{
        background-color: {COLORS['dark_pink']};
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }}
    
    .stButton > button:active {{
        transform: translateY(0);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }}
    
    /* Mobile button optimizations */
    @media (max-width: 768px) {{
        .stButton > button {{
            padding: 0.8rem 1.5rem;
            font-size: 1rem;
            min-height: 48px;
            width: 100%;
            margin: 0.5rem 0;
        }}
    }}
    
    @media (max-width: 480px) {{
        .stButton > button {{
            padding: 1rem 1.5rem;
            font-size: 1.1rem;
            min-height: 52px;
            width: 100%;
            margin: 0.7rem 0;
            border-radius: 12px;
        }}
    }}
    
    /* ===== FORM SUBMIT BUTTONS ===== */
    .stForm .stButton > button {{
        background-color: {COLORS['primary_pink']};
        font-weight: 600;
    }}
    
    .stForm .stButton > button:hover {{
        background-color: {COLORS['dark_pink']};
    }}
    
    /* ===== TABELLEN ===== */
    .stDataFrame,
    .stTable {{
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        position: relative;
        z-index: 2;
        width: 100% !important;
        max-width: 100% !important;
    }}
    
    /* DataFrames volledige breedte */
    .stDataFrame > div,
    .stTable > div {{
        width: 100% !important;
        max-width: 100% !important;
        overflow-x: auto;
    }}
    
    /* Table container volledige breedte */
    .stDataFrame table,
    .stTable table {{
        width: 100% !important;
        min-width: 100%;
        table-layout: auto;
        border-collapse: collapse;
    }}
    
    /* Table headers */
    .stDataFrame thead th,
    .stTable thead th {{
        background-color: {COLORS['primary_pink']} !important;
        color: {COLORS['white']} !important;
        font-weight: 600;
        padding: 1rem 0.8rem;
        text-align: left;
        white-space: nowrap;
        position: sticky;
        top: 0;
        z-index: 10;
    }}
    
    /* Table cells */
    .stDataFrame tbody td,
    .stTable tbody td {{
        padding: 0.8rem;
        border-bottom: 1px solid {COLORS['soft_pink']};
        text-align: left;
        word-wrap: break-word;
    }}
    
    /* Table rows */
    .stDataFrame tbody tr:nth-child(even),
    .stTable tbody tr:nth-child(even) {{
        background-color: {COLORS['light_background']};
    }}
    
    .stDataFrame tbody tr:hover,
    .stTable tbody tr:hover {{
        background-color: rgba(202, 0, 93, 0.1);
        transition: background-color 0.2s ease;
    }}
    
    /* Responsive table aanpassingen */
    @media (max-width: 768px) {{
        .stDataFrame thead th,
        .stTable thead th,
        .stDataFrame tbody td,
        .stTable tbody td {{
            padding: 0.5rem 0.3rem;
            font-size: 0.9rem;
        }}
        
        .stDataFrame,
        .stTable {{
            font-size: 0.85rem;
        }}
    }}
    
    @media (max-width: 480px) {{
        .stDataFrame thead th,
        .stTable thead th,
        .stDataFrame tbody td,
        .stTable tbody td {{
            padding: 0.4rem 0.2rem;
            font-size: 0.8rem;
        }}
        
        .stDataFrame,
        .stTable {{
            font-size: 0.75rem;
        }}
    }}
    
    /* ===== TEXT INPUT FIELDS ===== */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stNumberInput > div > div > input {{
        border-radius: 8px;
        border: 2px solid {COLORS['soft_pink']};
        position: relative;
        z-index: 2;
        min-height: 44px;
        font-size: 1rem;
    }}
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stNumberInput > div > div > input:focus {{
        border-color: {COLORS['primary_pink']};
        box-shadow: 0 0 0 2px rgba(202, 0, 93, 0.2);
    }}
    
    /* Mobile input field optimizations */
    @media (max-width: 768px) {{
        .stTextInput > div > div > input,
        .stSelectbox > div > div > select,
        .stNumberInput > div > div > input {{
            min-height: 48px;
            font-size: 1.1rem;
            padding: 0.8rem;
        }}
        
        .stSelectbox > div > div {{
            min-height: 48px;
        }}
    }}
    
    @media (max-width: 480px) {{
        .stTextInput > div > div > input,
        .stSelectbox > div > div > select,
        .stNumberInput > div > div > input {{
            min-height: 52px;
            font-size: 1.2rem;
            padding: 1rem;
            border-radius: 12px;
        }}
        
        .stSelectbox > div > div {{
            min-height: 52px;
        }}
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
        color: {COLORS['primary_pink']};
        position: relative;
        z-index: 2;
        line-height: 1.2;
    }}
    
    .main h1 {{
        border-bottom: 3px solid {COLORS['secondary_blue']};
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    }}
    
    /* Mobile typography optimizations */
    @media (max-width: 768px) {{
        h1 {{
            font-size: 1.8rem;
            margin-bottom: 1rem;
        }}
        
        h2 {{
            font-size: 1.5rem;
            margin-bottom: 0.8rem;
        }}
        
        h3 {{
            font-size: 1.3rem;
            margin-bottom: 0.6rem;
        }}
        
        .main h1 {{
            padding-bottom: 0.4rem;
            margin-bottom: 1.2rem;
        }}
    }}
    
    @media (max-width: 480px) {{
        h1 {{
            font-size: 1.6rem;
            margin-bottom: 0.8rem;
        }}
        
        h2 {{
            font-size: 1.3rem;
            margin-bottom: 0.6rem;
        }}
        
        h3 {{
            font-size: 1.1rem;
            margin-bottom: 0.5rem;
        }}
        
        .main h1 {{
            padding-bottom: 0.3rem;
            margin-bottom: 1rem;
        }}
    }}
    
    /* ===== DIVIDERS ===== */
    hr {{
        border: none;
        height: 3px;
        background: linear-gradient(90deg, {COLORS['primary_pink']}, {COLORS['secondary_blue']});
        border-radius: 2px;
        margin: 2rem 0;
        position: relative;
        z-index: 2;
    }}
    
    /* ===== SPINNER ===== */
    .stSpinner > div {{
        border-top-color: {COLORS['primary_pink']} !important;
    }}
</style>
"""

 