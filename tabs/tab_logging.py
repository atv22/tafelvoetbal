import streamlit as st
from firestore_service import get_log_history

def render_logging_tab():
    st.header("🔍 Systeem Logging")
    st.markdown("Hieronder zie je de meest recente database operaties (tot 1000 regels).")
    
    if st.button("🔄 Ververs Logs"):
        st.rerun()
        
    logs = get_log_history()
    
    if not logs:
        st.info("Nog geen logs beschikbaar in deze sessie.")
        return
        
    log_text = "\n".join(logs)
    st.code(log_text, language="text")
