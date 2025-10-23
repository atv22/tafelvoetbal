import streamlit as st
import firestore_service as db # Import your Firestore service
# from config import get_uitslag_df, get_public_sheet_url # No longer needed for Firestore data
from utils import get_download_filename
from styles import setup_page

# Set up the Streamlit page layout and styles
setup_page()

# Change the title to reflect Firestore data
st.title("Ruwe data Firestore (Wedstrijden)")

# Fetch match data from Firestore using your service
df_matches = db.get_matches()

# Provide a download button for the fetched Firestore match data
st.download_button(
    label="💾 Download volledige log (Firestore Wedstrijden)",
    data=df_matches.to_csv(index=False).encode('utf-8'),
    # Use a dynamic filename, adjusting for the new data source
    file_name=get_download_filename('Tafelvoetbal_Firestore_Wedstrijden', 'csv'),
    mime='text/csv',
)

st.markdown("""<hr style=\"height:9px;border:none;color:#f0f2f6;background-color:#122f5b;opacity: 0.8;\" /> """, unsafe_allow_html=True)

# Display the Firestore data directly in the Streamlit app
# This replaces the iframe for the Google Sheet
if not df_matches.empty:
    st.dataframe(df_matches, use_container_width=True)
else:
    st.info("Geen wedstrijdgegevens gevonden in Firestore.")

# The following lines are removed as they were for embedding the Google Sheet:
# url = get_public_sheet_url()
# html = f'<iframe src="{url}" width="100%" height="100%" frameborder="0" scrolling="yes"></iframe>'
# st.markdown(html, unsafe_allow_html=True)
