"""
TAB: Verzoeken (Requests)
Eenvoudig formulier om een verzoek/feedback in te dienen en optioneel recente verzoeken te tonen.
"""
import streamlit as st
import pandas as pd
from utils.utils import add_request, get_download_filename


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
        display_df = requests_df.copy()
        ts_col = next((c for c in ('timestamp', 'Timestamp') if c in display_df.columns), None)
        text_col = next((c for c in ('Verzoek', 'verzoek') if c in display_df.columns), None)

        if ts_col is not None:
            parsed_ts = pd.to_datetime(display_df[ts_col], errors='coerce', format='mixed', utc=True).dt.tz_localize(None)
            display_df['_sort_ts'] = parsed_ts
            display_df = display_df.sort_values(by='_sort_ts', ascending=False, na_position='last')
            display_df['Datum'] = parsed_ts.loc[display_df.index].dt.strftime('%d-%m-%Y %H:%M').fillna('-')
        else:
            display_df['Datum'] = '-'

        if text_col is not None:
            display_df['Verzoek'] = display_df[text_col]
        else:
            display_df['Verzoek'] = ''

        st.dataframe(display_df[['Datum', 'Verzoek']], hide_index=True, width='stretch')
    else:
        st.info("Nog geen verzoeken ingediend.")
