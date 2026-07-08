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
        
    logs = list(get_log_history())
    
    if not logs:
        st.info("Nog geen systeem logs beschikbaar in deze sessie.")
        return
        
    import pandas as pd
    
    parsed_logs = []
    for log in logs:
        if isinstance(log, dict):
            parsed_logs.append(log)
        elif isinstance(log, str):
            try:
                # Voorbeeld: [2026-07-08 10:37:00] [FIRESTORE] READ  | Coll: matches      | Action: get                  | Count: 1    | IP: Unknown IP
                if " | " in log:
                    parts = log.split(" | ")
                    ts_and_type = parts[0].split("] [FIRESTORE] ")
                    ts = ts_and_type[0].strip("[")
                    op_type = ts_and_type[1].strip() if len(ts_and_type) > 1 else ""
                    
                    coll = parts[1].replace("Coll:", "").strip() if len(parts) > 1 else ""
                    action = parts[2].replace("Action:", "").strip() if len(parts) > 2 else ""
                    count = parts[3].replace("Count:", "").strip() if len(parts) > 3 else ""
                    ip = parts[4].replace("IP:", "").strip() if len(parts) > 4 else "Unknown IP"
                    
                    parsed_logs.append({
                        "Tijdstip": ts,
                        "Type": op_type,
                        "Collectie": coll,
                        "Actie": action,
                        "Aantal": count,
                        "IP": ip
                    })
                else:
                    parsed_logs.append({"Bericht": log})
            except Exception:
                parsed_logs.append({"Bericht": log})
                
    if parsed_logs:
        df_logs = pd.DataFrame(parsed_logs)
        st.dataframe(df_logs, width='stretch')
    else:
        st.info("Nog geen systeem logs beschikbaar in deze sessie.")
