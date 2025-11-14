"""
TAB: Verzoeken (Requests)
Eenvoudig formulier om een verzoek/feedback in te dienen en optioneel recente verzoeken te tonen.
"""
import streamlit as st
import pandas as pd
from utils import add_request
import firestore_service as db


def render_requests_tab():
    st.header("💬 Verzoeken")
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

    with st.expander("Toon recente verzoeken (laatste 10)"):
        try:
            df = db.get_requests()
            if df is not None and not df.empty:
                # Zorg voor nette weergave
                if "Timestamp" in df.columns:
                    df = df.sort_values(by="Timestamp", ascending=False)
                st.dataframe(df.head(10), use_container_width=True)
            else:
                st.info("Nog geen verzoeken ingediend.")
        except Exception as e:
            st.warning(f"Kon verzoeken niet laden: {e}")
