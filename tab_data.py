import streamlit as st
import firestore_service as db
from utils import get_download_filename

def render_data_tab():
    st.header("Ruwe Data uit Firestore")

    # --- Spelers ---
    st.subheader("Spelers")
    df_players = db.get_players()
    if not df_players.empty:
        st.dataframe(df_players, use_container_width=True)
    else:
        st.info("Geen spelers gevonden in Firestore.")

    # --- Uitslagen (Matches) ---
    st.subheader("Uitslagen (Wedstrijden)")
    df_matches = db.get_matches()
    st.download_button(
        label="💾 Download Uitslagen",
        data=df_matches.to_csv(index=False).encode('utf-8'),
        file_name=get_download_filename('Tafelvoetbal_Uitslagen', 'csv'),
        mime='text/csv',
    )
    st.dataframe(df_matches, use_container_width=True)

    # --- ELO Geschiedenis ---
    st.subheader("ELO Geschiedenis")
    df_elo = db.get_elo_logs()
    st.download_button(
        label="💾 Download ELO Geschiedenis",
        data=df_elo.to_csv(index=False).encode('utf-8'),
        file_name=get_download_filename('Tafelvoetbal_ELO_Geschiedenis', 'csv'),
        mime='text/csv',
    )
    st.dataframe(df_elo, use_container_width=True)

    # --- Beheer Logging ---
    st.subheader("Beheer Logging (Admin acties)")
    df_beheer_log = db.get_beheer_log()
    if not df_beheer_log.empty:
        st.dataframe(df_beheer_log, use_container_width=True)
        st.download_button(
            label="💾 Download Beheer Logging",
            data=df_beheer_log.to_csv(index=False).encode('utf-8'),
            file_name=get_download_filename('Tafelvoetbal_Beheer_Log', 'csv'),
            mime='text/csv',
        )
    else:
        st.info("Geen beheer-log entries gevonden.")
