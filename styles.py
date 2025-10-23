import streamlit as st
APP_TITLE = "Tafelvoetbal"
APP_ICON = "⚽"
LAYOUT = "centered"
HIDE_ROW_INDEX_CSS = """
<style>
.row_heading.level0 {display:none}
.blank {display:none}
</style>
"""
VERSIE = "Beta versie 0.3.1 - 17 september 2023"
def setup_page():
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout=LAYOUT,
        initial_sidebar_state="auto",
        menu_items=None,
    )
    st.markdown(HIDE_ROW_INDEX_CSS, unsafe_allow_html=True)