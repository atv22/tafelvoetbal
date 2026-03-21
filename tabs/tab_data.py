import streamlit as st
import firestore_service as db
from utils.utils import get_download_filename

def render_data_tab(matches_df, df_elo, df_players, df_beheer_log, df_requests):
    st.header("📊 Ruwe Data uit Firestore")


    try:
        # --- Uitslagen (Wedstrijden) ---
        st.subheader("🏆 Uitslagen (Wedstrijden)")
        if not matches_df.empty:
            st.download_button(
                label="💾 Download Uitslagen",
                data=matches_df.to_csv(index=False).encode('utf-8'),
                file_name=get_download_filename('Tafelvoetbal_Uitslagen', 'csv'),
                mime='text/csv',
                key='download-uitslagen'
            )
            st.dataframe(matches_df, width='stretch')
        else:
            st.info("Geen wedstrijden gevonden.")

        # --- ELO Geschiedenis ---
        st.subheader("⚡ ELO Geschiedenis")
        if not df_elo.empty:
            st.download_button(
                label="💾 Download ELO Geschiedenis",
                data=df_elo.to_csv(index=False).encode('utf-8'),
                file_name=get_download_filename('Tafelvoetbal_ELO_Geschiedenis', 'csv'),
                mime='text/csv',
                key='download-elo'
            )
            st.dataframe(df_elo, width='stretch')
        else:
            st.info("Geen ELO geschiedenis gevonden.")

        # --- Spelers ---
        st.subheader("👤 Spelers")
        if not df_players.empty:
            st.download_button(
                label="💾 Download Spelers",
                data=df_players.to_csv(index=False).encode('utf-8'),
                file_name=get_download_filename('Tafelvoetbal_Spelers', 'csv'),
                mime='text/csv',
                key='download-spelers'
            )
            st.dataframe(df_players, width='stretch')
        else:
            st.info("Geen spelers gevonden in Firestore.")

        # --- Beheer Logging ---
        st.subheader("📝 Beheer Logging (Admin acties)")
        if not df_beheer_log.empty:
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

        # --- Verzoeken ---
        st.subheader("💬 Verzoeken (Requests)")
        if not df_requests.empty:
            st.download_button(
                label="💾 Download Verzoeken",
                data=df_requests.to_csv(index=False).encode('utf-8'),
                file_name=get_download_filename('Tafelvoetbal_Verzoeken', 'csv'),
                mime='text/csv',
                key='download-verzoeken'
            )
            st.dataframe(df_requests, width='stretch')
        else:
            st.info("Geen verzoeken gevonden.")
    except db.FirestoreUnavailable as e:
        st.error("Database niet bereikbaar: mogelijk budgetlimiet bereikt.")
        with st.expander("Toon technische details"):
            st.code(str(e.details) if hasattr(e, 'details') else str(e))
