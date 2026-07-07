import streamlit as st
from firestore_service import get_log_history
from utils.utils import get_download_filename

def render_logging_tab(df_beheer_log):
    st.header("🔍 Systeem Logging & Beheer Acties")
    
    st.subheader("📝 Beheer Logging (Admin acties)")
    if df_beheer_log is not None and not df_beheer_log.empty:
        st.download_button(
            label="💾 Download Beheer Logging",
            data=df_beheer_log.to_csv(index=False).encode('utf-8'),
            file_name=get_download_filename('Tafelvoetbal_Beheer_Log', 'csv'),
            mime='text/csv',
            key='download-beheer-log'
        )
        st.dataframe(df_beheer_log, width='stretch')
    else:
        st.info("Geen beheer-log entries gevonden.")

    st.divider()

    st.subheader("⚙️ Technische Systeem Logging")
    st.markdown("Hieronder zie je de meest recente database operaties (tot 1000 regels) van deze sessie.")
    
    if st.button("🔄 Ververs Systeem Logs"):
        st.rerun()
        
    logs = get_log_history()
    
    if not logs:
        st.info("Nog geen systeem logs beschikbaar in deze sessie.")
        return
        
    log_text = "\n".join(logs)
    st.code(log_text, language="text")
