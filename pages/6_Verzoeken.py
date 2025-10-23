import streamlit as st
from config import get_uitslag_df, get_public_sheet_url
from utils import get_download_filename
st.title("Ruwe data google sheet")
df = get_uitslag_df()
st.download_button(
    label="💾 Download volledige log",
    data=df.to_csv(index=False).encode('utf-8'),
    file_name=get_download_filename('Tafelvoetbal_volledige_log', 'csv'),
    mime='text/csv',
)
st.markdown("""<hr style=\"height:9px;border:none;color:#f0f2f6;background-color:#122f5b;opacity: 0.8;\" /> """, unsafe_allow_html=True)
url = get_public_sheet_url()
html = f'<iframe src="{url}" width="100%" height="100%" frameborder="0" scrolling="yes"></iframe>'
st.markdown(html, unsafe_allow_html=True)
 