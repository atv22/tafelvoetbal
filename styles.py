import streamlit as st

# App configuratie constanten
APP_TITLE = "Tafelvoetbal Competitie ⚽"
APP_ICON = "⚽"
LAYOUT = "centered"

# Kleurenschema
COLORS = {
    'primary_blue': '#154273',      # Hoofdblauw
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
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': None
        },
    )
    
    # Injecteer aangepaste CSS
    st.markdown(_get_custom_css(), unsafe_allow_html=True)
    
    # Voeg JavaScript toe voor mobiele sidebar functionaliteit
    st.markdown(_get_mobile_js(), unsafe_allow_html=True)

def _get_mobile_js():
    """JavaScript voor mobiele sidebar met toggle functionaliteit."""
    return """
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        let sidebarVisible = false; // Track sidebar state
        
        // Sidebar toggle functie
        function toggleSidebar() {
            const sidebar = document.querySelector('[data-testid="stSidebar"]');
            const mobileOverlay = document.getElementById('mobile-sidebar-overlay');
            
            if (window.innerWidth <= 768 && sidebar) {
                sidebarVisible = !sidebarVisible;
                
                if (sidebarVisible) {
                    // Toon sidebar
                    sidebar.style.transform = 'translateX(0)';
                    sidebar.style.visibility = 'visible';
                    sidebar.style.opacity = '1';
                    
                    // Toon overlay
                    if (mobileOverlay) {
                        mobileOverlay.style.display = 'block';
                    }
                    
                    // Prevent body scroll
                    document.body.style.overflow = 'hidden';
                } else {
                    // Verberg sidebar
                    sidebar.style.transform = 'translateX(-100%)';
                    sidebar.style.visibility = 'hidden';
                    sidebar.style.opacity = '0';
                    
                    // Verberg overlay
                    if (mobileOverlay) {
                        mobileOverlay.style.display = 'none';
                    }
                    
                    // Restore body scroll
                    document.body.style.overflow = 'auto';
                }
            }
        }
        
        // Voeg overlay toe voor mobile sidebar
        function addMobileOverlay() {
            if (!document.getElementById('mobile-sidebar-overlay')) {
                const overlay = document.createElement('div');
                overlay.id = 'mobile-sidebar-overlay';
                overlay.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100vw;
                    height: 100vh;
                    background-color: rgba(0, 0, 0, 0.5);
                    z-index: 998;
                    display: none;
                    backdrop-filter: blur(2px);
                `;
                
                // Click overlay to close sidebar
                overlay.addEventListener('click', function() {
                    if (sidebarVisible) {
                        toggleSidebar();
                    }
                });
                
                document.body.appendChild(overlay);
            }
        }
        
        // Setup mobile sidebar
        function setupMobileSidebar() {
            const sidebar = document.querySelector('[data-testid="stSidebar"]');
            const collapsedControl = document.querySelector('[data-testid="collapsedControl"]');
            
            if (window.innerWidth <= 768) {
                addMobileOverlay();
                
                if (sidebar) {
                    // Initieel verborgen op mobiel
                    sidebar.style.position = 'fixed';
                    sidebar.style.top = '0';
                    sidebar.style.left = '0';
                    sidebar.style.height = '100vh';
                    sidebar.style.width = window.innerWidth <= 480 ? '85vw' : '300px';
                    sidebar.style.zIndex = '999';
                    sidebar.style.transform = 'translateX(-100%)';
                    sidebar.style.visibility = 'hidden';
                    sidebar.style.opacity = '0';
                    sidebar.style.transition = 'all 0.3s ease-in-out';
                    sidebar.style.boxShadow = '4px 0 20px rgba(0, 0, 0, 0.3)';
                    
                    // Reset sidebar state
                    sidebarVisible = false;
                }
                
                if (collapsedControl) {
                    collapsedControl.style.position = 'fixed';
                    collapsedControl.style.top = '1rem';
                    collapsedControl.style.left = '1rem';
                    collapsedControl.style.zIndex = '1001';
                    collapsedControl.style.display = 'flex';
                    collapsedControl.style.visibility = 'visible';
                    
                    // Remove old event listeners
                    collapsedControl.replaceWith(collapsedControl.cloneNode(true));
                    const newCollapsedControl = document.querySelector('[data-testid="collapsedControl"]');
                    
                    // Add new click handler
                    newCollapsedControl.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        toggleSidebar();
                    });
                }
                
                // Close sidebar when clicking sidebar links
                const sidebarLinks = sidebar?.querySelectorAll('a, [role="button"]');
                if (sidebarLinks) {
                    sidebarLinks.forEach(link => {
                        link.addEventListener('click', function() {
                            if (sidebarVisible) {
                                setTimeout(() => toggleSidebar(), 200); // Small delay for navigation
                            }
                        });
                    });
                }
            } else {
                // Desktop: herstel normale sidebar gedrag
                if (sidebar) {
                    sidebar.style.position = '';
                    sidebar.style.transform = '';
                    sidebar.style.visibility = '';
                    sidebar.style.opacity = '';
                    sidebar.style.transition = '';
                    sidebar.style.boxShadow = '';
                }
                
                // Verberg overlay op desktop
                const mobileOverlay = document.getElementById('mobile-sidebar-overlay');
                if (mobileOverlay) {
                    mobileOverlay.style.display = 'none';
                }
                
                // Restore body scroll
                document.body.style.overflow = 'auto';
                sidebarVisible = false;
            }
        }
        
        // Global toggle function
        window.toggleMobileSidebar = toggleSidebar;
        
        // Run setup
        setupMobileSidebar();
        
        // Listen for resize events
        window.addEventListener('resize', function() {
            setupMobileSidebar();
        });
        
        // Observer for dynamic content
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList') {
                    // Delay setup to allow DOM to update
                    setTimeout(setupMobileSidebar, 100);
                }
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
        
        // Extra setup after DOM is fully loaded
        setTimeout(setupMobileSidebar, 500);
    });
    </script>
    """

def _get_custom_css():
    """Genereer de complete CSS voor de applicatie."""
    return f"""
<style>
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
    
    /* FORCEER SIDEBAR GEDRAG - DESKTOP ALTIJD ZICHTBAAR */
    [data-testid="stSidebar"][aria-expanded="false"] {{
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        transform: translateX(0) !important;
    }}
    
    /* DESKTOP: Sidebar altijd zichtbaar */
    @media (min-width: 769px) {{
        [data-testid="stSidebar"] {{
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            position: relative !important;
            transform: translateX(0) !important;
        }}
    }}
    
    /* MOBIEL: Sidebar initieel verborgen, toggle via menu */
    @media (max-width: 768px) {{
        [data-testid="stSidebar"] {{
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            height: 100vh !important;
            width: 300px !important;
            z-index: 999 !important;
            transform: translateX(-100%) !important;
            visibility: hidden !important;
            opacity: 0 !important;
            transition: all 0.3s ease-in-out !important;
            box-shadow: 4px 0 20px rgba(0, 0, 0, 0.3) !important;
        }}
        
        /* Zorg dat sidebar toggle altijd werkt */
        [data-testid="collapsedControl"] {{
            display: flex !important;
            visibility: visible !important;
            position: fixed !important;
            top: 1rem !important;
            left: 1rem !important;
            z-index: 1001 !important;
        }}
    }}
    
    /* SMARTPHONE: Sidebar bijna volledige breedte */
    @media (max-width: 480px) {{
        [data-testid="stSidebar"] {{
            width: 85vw !important;
        }}
    }}
    
    /* Sidebar content blijft hetzelfde */
    [data-testid="stSidebar"] > div {{
        height: 100vh !important;
        overflow-y: auto !important;
        padding: 2rem 1rem !important;
    }}
    
    /* ===== ALGEMENE BODY STYLING ===== */
    .main .block-container {{
        padding-top: 2rem;
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
    
    /* Mobile optimizations voor main content */
    @media (max-width: 768px) {{
        .main .block-container {{
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 0.5rem;
            padding-right: 0.5rem;
            max-width: 98vw;
        }}
    }}
    
    @media (max-width: 480px) {{
        .main .block-container {{
            padding-top: 0.5rem;
            padding-bottom: 0.5rem;
            padding-left: 0.3rem;
            padding-right: 0.3rem;
            max-width: 100vw;
        }}
    }}
    
    /* ===== SIDEBAR ===== */
    [data-testid="stSidebar"] {{
        background-color: {COLORS['primary_blue']} !important;
        color: {COLORS['white']} !important;
        z-index: 999 !important;
    }}
    
    /* Zorg ervoor dat alle sidebar tekst wit is */
    [data-testid="stSidebar"] * {{
        color: {COLORS['white']} !important;
    }}
    
    /* Sidebar content wrapper */
    [data-testid="stSidebar"] > div {{
        background-color: {COLORS['primary_blue']} !important;
        padding: 1rem !important;
    }}
    
    /* Sidebar links styling */
    [data-testid="stSidebar"] .css-1d391kg,
    [data-testid="stSidebar"] a,
    [data-testid="stSidebar"] [role="button"],
    [data-testid="stSidebar"] .css-pkbazv {{
        color: {COLORS['white']} !important;
        text-decoration: none !important;
        padding: 0.8rem 1rem !important;
        display: block !important;
        border-radius: 8px !important;
        margin: 0.3rem 0 !important;
        transition: all 0.2s ease !important;
        background-color: transparent !important;
        border: none !important;
        width: 100% !important;
        text-align: left !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
        cursor: pointer !important;
    }}
    
    [data-testid="stSidebar"] .css-1d391kg:hover,
    [data-testid="stSidebar"] a:hover,
    [data-testid="stSidebar"] [role="button"]:hover,
    [data-testid="stSidebar"] .css-pkbazv:hover {{
        color: {COLORS['white']} !important;
        background-color: rgba(255, 255, 255, 0.15) !important;
        opacity: 1 !important;
        transform: translateX(5px) !important;
    }}
    
    /* Sidebar navigation container */
    [data-testid="stSidebar"] .css-17lntkn {{
        padding: 0 !important;
        margin: 0 !important;
    }}
    
    /* Sidebar toggle button (hamburger menu) - KRITIEK VOOR MOBIEL */
    [data-testid="collapsedControl"] {{
        color: {COLORS['white']} !important;
        background-color: {COLORS['primary_blue']} !important;
        border: 2px solid {COLORS['accent_purple']} !important;
        border-radius: 50% !important;
        padding: 0.8rem !important;
        margin: 0.5rem !important;
        z-index: 1001 !important;
        position: fixed !important;
        top: 1rem !important;
        left: 1rem !important;
        width: 60px !important;
        height: 60px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
        transition: all 0.3s ease !important;
    }}
    
    [data-testid="collapsedControl"]:hover {{
        background-color: {COLORS['accent_purple']} !important;
        transform: scale(1.1) !important;
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4) !important;
    }}
    
    [data-testid="collapsedControl"] svg {{
        width: 24px !important;
        height: 24px !important;
        color: {COLORS['white']} !important;
    }}
    
    /* MOBIELE OPTIMALISATIES - TABLET */
    @media (max-width: 768px) {{
        /* Grotere touch targets voor sidebar links */
        [data-testid="stSidebar"] .css-1d391kg,
        [data-testid="stSidebar"] a,
        [data-testid="stSidebar"] [role="button"],
        [data-testid="stSidebar"] .css-pkbazv {{
            font-size: 1.2rem !important;
            padding: 1rem 1.5rem !important;
            margin: 0.5rem 0 !important;
            min-height: 50px !important;
        }}
        
        /* Main content GEEN margin - sidebar is overlay */
        .main .block-container {{
            margin-left: 0 !important;
            max-width: 100vw !important;
        }}
    }}
    
    /* MOBIELE OPTIMALISATIES - SMARTPHONE */
    @media (max-width: 480px) {{
        [data-testid="stSidebar"] > div {{
            padding: 3rem 2rem !important;
        }}
        
        /* Extra grote touch targets */
        [data-testid="stSidebar"] .css-1d391kg,
        [data-testid="stSidebar"] a,
        [data-testid="stSidebar"] [role="button"],
        [data-testid="stSidebar"] .css-pkbazv {{
            font-size: 1.4rem !important;
            padding: 1.2rem 2rem !important;
            margin: 0.7rem 0 !important;
            min-height: 60px !important;
            border-radius: 12px !important;
        }}
        
        /* Main content volledige breedte - sidebar is overlay */
        .main .block-container {{
            margin-left: 0 !important;
            max-width: 100vw !important;
        }}
        
        /* Hamburger menu extra prominent */
        [data-testid="collapsedControl"] {{
            width: 70px !important;
            height: 70px !important;
            top: 2rem !important;
            left: 2rem !important;
        }}
        
        [data-testid="collapsedControl"] svg {{
            width: 30px !important;
            height: 30px !important;
        }}
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
        padding: 2rem 1.5rem;
        margin: 1rem auto;
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
        width: auto;
        min-height: 44px; /* Minimale touch target grootte */
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
        background-color: {COLORS['primary_blue']} !important;
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
        border-bottom: 1px solid {COLORS['soft_purple']};
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
        background-color: rgba(142, 108, 166, 0.1);
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
        border: 2px solid {COLORS['soft_purple']};
        position: relative;
        z-index: 2;
        min-height: 44px;
        font-size: 1rem;
    }}
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stNumberInput > div > div > input:focus {{
        border-color: {COLORS['accent_purple']};
        box-shadow: 0 0 0 2px rgba(142, 108, 166, 0.2);
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
        color: {COLORS['primary_blue']};
        position: relative;
        z-index: 2;
        line-height: 1.2;
    }}
    
    .main h1 {{
        border-bottom: 3px solid {COLORS['accent_purple']};
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

 