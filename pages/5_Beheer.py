import streamlit as st
import pandas as pd
from datetime import date
import firestore_service as db # Use Firestore
from styles import setup_page

setup_page()

# --- Authenticatie ---
goede_wachtwoord = "Klinker"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("Login vereist")
    password = st.text_input("Voer wachtwoord in", type="password")
    if password == goede_wachtwoord:
        st.session_state.authenticated = True
        st.rerun()
    elif password:
        st.error("Ongeldig wachtwoord.")
    st.stop()

st.title("Beheer")

# --- Speler Verwijderen ---
st.subheader("Speler Verwijderen")

players_df = db.get_players()
if not players_df.empty:
    player_names = players_df['speler_naam'].tolist()
    player_ids = players_df['speler_id'].tolist()
    player_map = {name: id for name, id in zip(player_names, player_ids)}

    player_to_delete = st.selectbox("Selecteer een speler om te verwijderen", options=sorted(player_names))
    
    if st.button(f"Verwijder {player_to_delete} Permanent"):
        player_id_to_delete = player_map.get(player_to_delete)
        if player_id_to_delete:
            with st.spinner(f"Bezig met verwijderen van {player_to_delete}..."):
                if db.delete_player_by_id(player_id_to_delete):
                    st.success(f"{player_to_delete} en alle bijbehorende data is verwijderd.")
                    st.rerun()
                else:
                    st.error(f"Kon {player_to_delete} niet verwijderen.")
        else:
            st.error("Kon de speler ID niet vinden.")
else:
    st.info("Geen spelers om te beheren.")

st.markdown("""<hr>""", unsafe_allow_html=True)

# --- Seizoen Verwijderen ---
st.subheader("Seizoen Verwijderen")
df_seizoenen_delete = db.get_seasons()
if not df_seizoenen_delete.empty:
    # Maak een leesbare weergave voor de selectbox
    df_seizoenen_delete['display'] = df_seizoenen_delete.apply(
        lambda row: f"Seizoen {row.get('seizoen_id', 'N/A')}: {pd.to_datetime(row['startdatum']).strftime('%d-%m-%Y')} - {pd.to_datetime(row['einddatum']).strftime('%d-%m-%Y')}",
        axis=1
    )
    season_display_list = df_seizoenen_delete['display'].tolist()
    season_id_map = {display: id for display, id in zip(season_display_list, df_seizoenen_delete['seizoen_id'].tolist())}

    season_to_delete_display = st.selectbox("Selecteer een seizoen om te verwijderen", options=season_display_list)
    
    if st.button(f"Verwijder geselecteerd seizoen permanent"):
        season_id_to_delete = season_id_map.get(season_to_delete_display)
        if season_id_to_delete:
            with st.spinner("Seizoen wordt verwijderd..."):
                if db.delete_season_by_id(season_id_to_delete):
                    st.success("Seizoen succesvol verwijderd.")
                    st.rerun()
                else:
                    st.error("Kon het seizoen niet verwijderen.")
        else:
            st.error("Kon het seizoen ID niet vinden.")
else:
    st.info("Geen seizoenen om te verwijderen.")

st.markdown("""<hr>""", unsafe_allow_html=True)

# --- Wedstrijd Verwijderen ---
st.subheader("Wedstrijd Verwijderen")
df_matches_delete = db.get_matches()
if not df_matches_delete.empty:
    # Maak een leesbare weergave voor de selectbox
    df_matches_delete['display'] = df_matches_delete.apply(
        lambda row: f"{pd.to_datetime(row.get('timestamp')).strftime('%d-%m-%Y %H:%M') if row.get('timestamp') else 'No Timestamp'} - {row.get('thuis_1', 'N/A')}/{row.get('thuis_2', 'N/A')} vs {row.get('uit_1', 'N/A')}/{row.get('uit_2', 'N/A')}: {row.get('thuis_score', 'N/A')}-{row.get('uit_score', 'N/A')}",
        axis=1
    )
    match_display_list = df_matches_delete['display'].tolist()
    match_id_map = {display: id for display, id in zip(match_display_list, df_matches_delete['match_id'].tolist())}

    match_to_delete_display = st.selectbox("Selecteer een wedstrijd om te verwijderen", options=match_display_list)
    
    if st.button(f"Verwijder geselecteerde wedstrijd permanent"):
        match_id_to_delete = match_id_map.get(match_to_delete_display)
        if match_id_to_delete:
            with st.spinner("Wedstrijd wordt verwijderd..."):
                if db.delete_match_by_id(match_id_to_delete):
                    st.success("Wedstrijd succesvol verwijderd.")
                    st.rerun()
                else:
                    st.error("Kon de wedstrijd niet verwijderen.")
        else:
            st.error("Kon de wedstrijd ID niet vinden.")
else:
    st.info("Geen wedstrijden om te verwijderen.")

st.markdown("""<hr>""", unsafe_allow_html=True)

# --- Overige Entries Verwijderen ---
st.subheader("Overige Entries Verwijderen")

if st.button("Verwijder alle 'Requests'"):
    with st.spinner("Alle requests worden verwijderd..."):
        if db.clear_collection('requests'):
            st.success("Alle requests zijn succesvol verwijderd.")
            st.rerun()
        else:
            st.error("Kon de requests niet verwijderen.")

st.markdown("""<hr>""", unsafe_allow_html=True)

# --- Seizoenen Beheer ---
st.subheader("Seizoenen")

# Haal seizoenen op uit Firestore
df_seizoenen = db.get_seasons()

def start_nieuw_seizoen(einddatum):
    startdatum = pd.to_datetime(date.today())
    result = db.add_season(startdatum, einddatum)
    if result == "Success":
        st.success("Nieuw seizoen succesvol gestart!")
        st.rerun()
    else:
        st.error(f"Kon nieuw seizoen niet starten: {result}")

with st.form("nieuw_seizoen_form"):
    st.write("Klik op de knop om een nieuw seizoen te starten.")
    einddatum_input = st.date_input("Einddatum seizoen")
    submit = st.form_submit_button("Start nieuw seizoen")

if submit:
    einddatum = pd.to_datetime(einddatum_input) + pd.Timedelta(hours=23, minutes=59, seconds=59)
    if einddatum <= pd.Timestamp(date.today()):
        st.error("Einddatum moet na vandaag liggen.")
    else:
        start_nieuw_seizoen(einddatum)

st.subheader("Alle seizoenen")
if not df_seizoenen.empty:
    st.dataframe(df_seizoenen, width='stretch')
else:
    st.info("Nog geen seizoenen aangemaakt.")

st.markdown("""<hr>""", unsafe_allow_html=True)

# --- Data Importeren ---
st.subheader("Data Importeren")

with st.expander("Spelers Importeren"):
    st.markdown("""
    **Vereist CSV formaat:**
    - Kolom 1: `speler_naam` (verplicht)
    - Kolom 2: `rating` (optioneel, standaard is 1000)
    
    *Voorbeeld:*
    ```csv
    speler_naam,rating
    Jan,1050
    Piet,980
    ```
    """)
    uploaded_players = st.file_uploader("Upload spelers CSV", type=["csv"], key="players_uploader")
    if uploaded_players is not None:
        try:
            players_df = pd.read_csv(uploaded_players)
            st.write("Voorbeeld van de geüploade data:")
            st.dataframe(players_df.head())

            if 'speler_naam' not in players_df.columns:
                st.error("De kolom 'speler_naam' is verplicht in het CSV-bestand.")
            else:
                if st.button("Importeer Spelers"):
                    with st.spinner("Spelers aan het importeren..."):
                        players_data = players_df.to_dict('records')
                        added, duplicates = db.import_players(players_data)
                        st.success(f"Import voltooid! {added} spelers toegevoegd, {duplicates} duplicaten gevonden.")
                        st.rerun()
        except Exception as e:
            st.error(f"Er is een fout opgetreden bij het verwerken van het bestand: {e}")

with st.expander("Uitslagen Importeren"):
    st.markdown("""
    **Vereist CSV formaat:**
    De kolomnamen moeten exact overeenkomen.
    - `thuis_1`, `thuis_2`, `uit_1`, `uit_2`
    - `thuis_score`, `uit_score`
    - `timestamp` (optioneel, formaat: `YYYY-MM-DD HH:MM:SS`)

    *Voorbeeld:*
    ```csv
    thuis_1,thuis_2,uit_1,uit_2,thuis_score,uit_score,timestamp
    Jan,Piet,Klaas,Marie,10,5,2023-10-27 14:30:00
    ```
    """)
    uploaded_matches = st.file_uploader("Upload uitslagen CSV", type=["csv"], key="matches_uploader")
    if uploaded_matches is not None:
        try:
            matches_df = pd.read_csv(uploaded_matches)
            st.write("Voorbeeld van de geüploade data:")
            st.dataframe(matches_df.head())

            required_cols = ['thuis_1', 'thuis_2', 'uit_1', 'uit_2', 'thuis_score', 'uit_score']
            if not all(col in matches_df.columns for col in required_cols):
                st.error(f"Het CSV-bestand moet de volgende kolommen bevatten: {required_cols}")
            else:
                if st.button("Importeer Uitslagen"):
                    with st.spinner("Uitslagen aan het importeren..."):
                        matches_data = matches_df.to_dict('records')
                        added, duplicates = db.import_matches(matches_data)
                        st.success(f"Import voltooid! {added} uitslagen toegevoegd, {duplicates} duplicaten gevonden.")
                        st.rerun()
        except Exception as e:
            st.error(f"Er is een fout opgetreden bij het verwerken van het bestand: {e}")

with st.expander("Seizoenen Importeren"):
    st.markdown("""
    **Vereist CSV formaat:**
    - `startdatum` (formaat: `YYYY-MM-DD`)
    - `einddatum` (formaat: `YYYY-MM-DD`)

    *Voorbeeld:*
    ```csv
    startdatum,einddatum
    2023-01-01,2023-06-30
    2023-07-01,2023-12-31
    ```
    """)
    uploaded_seasons = st.file_uploader("Upload seizoenen CSV", type=["csv"], key="seasons_uploader")
    if uploaded_seasons is not None:
        try:
            seasons_df = pd.read_csv(uploaded_seasons)
            st.write("Voorbeeld van de geüploade data:")
            st.dataframe(seasons_df.head())

            required_cols = ['startdatum', 'einddatum']
            if not all(col in seasons_df.columns for col in required_cols):
                st.error(f"Het CSV-bestand moet de volgende kolommen bevatten: {required_cols}")
            else:
                if st.button("Importeer Seizoenen"):
                    with st.spinner("Seizoenen aan het importeren..."):
                        seasons_data = seasons_df.to_dict('records')
                        added, duplicates = db.import_seasons(seasons_data)
                        st.success(f"Import voltooid! {added} seizoenen toegevoegd, {duplicates} duplicaten gevonden.")
                        st.rerun()
        except Exception as e:
            st.error(f"Er is een fout opgetreden bij het verwerken van het bestand: {e}")