"""
TAB: Verzoeken (Requests)
Eenvoudig formulier om een verzoek/feedback in te dienen en optioneel recente verzoeken te tonen.
"""
import streamlit as st
import pandas as pd
from utils.utils import add_request, get_download_filename
import firestore_service as db


def render_verzoeken_tab(requests_df):
    st.header("💬 Verzoeken")
    st.subheader("Verzoek indienen")
    st.write("Laat hier je suggestie, bugmelding of wens achter (max 250 tekens).")

    with st.form("request_form"):
        request_text = st.text_area(
            "Je verzoek",
            placeholder="Bijv. 'Graag een grafiek met winst/verlies per speler'",
            max_chars=250,
            help="Maximaal 250 tekens"
        )
        submitted = st.form_submit_button("Verstuur verzoek")
        if submitted:
            if request_text is None:
                request_text = ""
            request_text = request_text.strip()
            add_request(request_text)

    st.subheader("Recente verzoeken")
    if requests_df is not None and not requests_df.empty:
        st.download_button(
            label="💾 Download Verzoeken",
            data=requests_df.to_csv(index=False).encode('utf-8'),
            file_name=get_download_filename('Tafelvoetbal_Verzoeken', 'csv'),
            mime='text/csv',
            key='download-verzoeken'
        )
        # Zorg voor nette weergave
        if "Timestamp" in requests_df.columns:
            display_df = requests_df.sort_values(by="Timestamp", ascending=False)
        else:
            display_df = requests_df
            
        st.dataframe(display_df, width='stretch')
    else:
        st.info("Nog geen verzoeken ingediend.")
