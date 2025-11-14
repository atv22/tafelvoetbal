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
st.subheader("Wedstrijd Beheer")
df_matches_delete = db.get_matches()
if not df_matches_delete.empty:
    # Maak tabs voor verschillende beheer functies
    match_beheer_tab1, match_beheer_tab2 = st.tabs(["🗑️ Verwijderen", "✏️ Bewerken"])
    
    with match_beheer_tab1:
        st.write("**Wedstrijd(en) verwijderen**")
        
        # Maak een leesbare weergave voor de selectbox
        df_matches_delete['display'] = df_matches_delete.apply(
            lambda row: f"{pd.to_datetime(row.get('timestamp')).strftime('%d-%m-%Y %H:%M') if row.get('timestamp') else 'No Timestamp'} - {row.get('thuis_1', 'N/A')}/{row.get('thuis_2', 'N/A')} vs {row.get('uit_1', 'N/A')}/{row.get('uit_2', 'N/A')}: {row.get('thuis_score', 'N/A')}-{row.get('uit_score', 'N/A')}",
            axis=1
        )
        
        # Optie voor enkelvoudige verwijdering
        st.write("**Enkele wedstrijd verwijderen:**")
        match_to_delete_display = st.selectbox("Selecteer een wedstrijd om te verwijderen", 
                                             options=df_matches_delete['display'].tolist(),
                                             key="single_delete_beheer")
        
        if st.button("Verwijder geselecteerde wedstrijd", key="delete_single_beheer"):
            match_idx = df_matches_delete[df_matches_delete['display'] == match_to_delete_display].index[0]
            match_id = df_matches_delete.loc[match_idx, 'match_id']
            
            with st.spinner("Wedstrijd wordt verwijderd..."):
                if db.delete_match_by_id(match_id):
                    st.success("Wedstrijd succesvol verwijderd.")
                    st.rerun()
                else:
                    st.error("Kon de wedstrijd niet verwijderen.")
        
        # Optie voor meerdere verwijderingen
        st.write("**Meerdere wedstrijden verwijderen:**")
        matches_to_delete = st.multiselect("Selecteer wedstrijden om te verwijderen",
                                         options=df_matches_delete['display'].tolist(),
                                         key="multi_delete_beheer")
        
        if matches_to_delete and st.button("Verwijder geselecteerde wedstrijden", key="delete_multi_beheer"):
            with st.spinner(f"Bezig met verwijderen van {len(matches_to_delete)} wedstrijden..."):
                success_count = 0
                for match_display in matches_to_delete:
                    match_idx = df_matches_delete[df_matches_delete['display'] == match_display].index[0]
                    match_id = df_matches_delete.loc[match_idx, 'match_id']
                    
                    if db.delete_match_by_id(match_id):
                        success_count += 1
                
                if success_count == len(matches_to_delete):
                    st.success(f"Alle {success_count} wedstrijden succesvol verwijderd.")
                else:
                    st.warning(f"{success_count} van de {len(matches_to_delete)} wedstrijden verwijderd.")
                st.rerun()
    
    with match_beheer_tab2:
        st.write("**Wedstrijd bewerken**")
        st.warning("⚠️ **Let op:** Het bewerken van wedstrijden wijzigt alleen de wedstrijdgegevens in de database. ELO scores worden niet automatisch herberekend.")
        
        players_df = db.get_players()
        if not players_df.empty:
            player_names = sorted(players_df['speler_naam'].tolist())
            
            # Selecteer wedstrijd om te bewerken
            match_to_edit = st.selectbox(
                "Selecteer een wedstrijd om te bewerken",
                options=df_matches_delete['display'].tolist(),
                key="match_edit_select_beheer"
            )
            
            if match_to_edit:
                match_idx = df_matches_delete[df_matches_delete['display'] == match_to_edit].index[0]
                match_data = df_matches_delete.loc[match_idx]
                
                st.write("**Huidige wedstrijd gegevens:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Thuis team:** {match_data.get('thuis_1')} & {match_data.get('thuis_2')}")
                    st.write(f"**Thuis score:** {match_data.get('thuis_score')}")
                    st.write(f"**Klinkers thuis:** {match_data.get('klinkers_thuis_1', 0)} & {match_data.get('klinkers_thuis_2', 0)}")
                with col2:
                    st.write(f"**Uit team:** {match_data.get('uit_1')} & {match_data.get('uit_2')}")
                    st.write(f"**Uit score:** {match_data.get('uit_score')}")
                    st.write(f"**Klinkers uit:** {match_data.get('klinkers_uit_1', 0)} & {match_data.get('klinkers_uit_2', 0)}")
                
                st.write("**Bewerk wedstrijd:**")
                
                with st.form("edit_match_form_beheer"):
                    # Speler selecties
                    edit_cols = st.columns(4)
                    with edit_cols[0]:
                        new_thuis_1 = st.selectbox("Thuis 1", player_names, 
                                                 index=player_names.index(match_data.get('thuis_1')) if match_data.get('thuis_1') in player_names else 0,
                                                 key="edit_thuis_1_beheer")
                    with edit_cols[1]:
                        new_thuis_2 = st.selectbox("Thuis 2", player_names,
                                                 index=player_names.index(match_data.get('thuis_2')) if match_data.get('thuis_2') in player_names else 1,
                                                 key="edit_thuis_2_beheer")
                    with edit_cols[2]:
                        new_uit_1 = st.selectbox("Uit 1", player_names,
                                                index=player_names.index(match_data.get('uit_1')) if match_data.get('uit_1') in player_names else 2,
                                                key="edit_uit_1_beheer")
                    with edit_cols[3]:
                        new_uit_2 = st.selectbox("Uit 2", player_names,
                                                index=player_names.index(match_data.get('uit_2')) if match_data.get('uit_2') in player_names else 3,
                                                key="edit_uit_2_beheer")
                    
                    # Scores
                    score_cols = st.columns(2)
                    with score_cols[0]:
                        new_thuis_score = st.number_input("Thuis Score", min_value=0, max_value=10, 
                                                        value=int(match_data.get('thuis_score', 0)), step=1,
                                                        key="edit_thuis_score_beheer")
                    with score_cols[1]:
                        new_uit_score = st.number_input("Uit Score", min_value=0, max_value=10, 
                                                       value=int(match_data.get('uit_score', 0)), step=1,
                                                       key="edit_uit_score_beheer")
                    
                    # Klinkers
                    klinker_cols = st.columns(4)
                    with klinker_cols[0]:
                        new_klinkers_thuis_1 = st.number_input("Klinkers Thuis 1", min_value=0, max_value=10, 
                                                             value=int(match_data.get('klinkers_thuis_1', 0)), step=1,
                                                             key="edit_klinkers_thuis_1_beheer")
                    with klinker_cols[1]:
                        new_klinkers_thuis_2 = st.number_input("Klinkers Thuis 2", min_value=0, max_value=10, 
                                                             value=int(match_data.get('klinkers_thuis_2', 0)), step=1,
                                                             key="edit_klinkers_thuis_2_beheer")
                    with klinker_cols[2]:
                        new_klinkers_uit_1 = st.number_input("Klinkers Uit 1", min_value=0, max_value=10, 
                                                           value=int(match_data.get('klinkers_uit_1', 0)), step=1,
                                                           key="edit_klinkers_uit_1_beheer")
                    with klinker_cols[3]:
                        new_klinkers_uit_2 = st.number_input("Klinkers Uit 2", min_value=0, max_value=10, 
                                                           value=int(match_data.get('klinkers_uit_2', 0)), step=1,
                                                           key="edit_klinkers_uit_2_beheer")
                    
                    if st.form_submit_button("Bewaar wijzigingen"):
                        # Validaties
                        if new_thuis_score == 10 and new_uit_score == 10:
                            st.error('Beide scores kunnen niet 10 zijn.')
                        elif new_thuis_score != 10 and new_uit_score != 10:
                            st.error('Eén van de scores moet 10 zijn.')
                        elif len(set([new_thuis_1, new_thuis_2, new_uit_1, new_uit_2])) < 4:
                            st.error("Selecteer vier unieke spelers.")
                        else:
                            # Update wedstrijd in Firestore
                            updated_match_data = {
                                'thuis_1': new_thuis_1,
                                'thuis_2': new_thuis_2,
                                'uit_1': new_uit_1,
                                'uit_2': new_uit_2,
                                'thuis_score': new_thuis_score,
                                'uit_score': new_uit_score,
                                'klinkers_thuis_1': new_klinkers_thuis_1,
                                'klinkers_thuis_2': new_klinkers_thuis_2,
                                'klinkers_uit_1': new_klinkers_uit_1,
                                'klinkers_uit_2': new_klinkers_uit_2,
                                'timestamp': match_data.get('timestamp')  # Behoud originele timestamp
                            }
                            
                            with st.spinner("Wedstrijd wordt bijgewerkt..."):
                                success = db.update_match(match_data['match_id'], updated_match_data)
                                
                                if success:
                                    st.success("Wedstrijd succesvol bijgewerkt!")
                                    st.warning("⚠️ **Belangrijk:** Het bewerken van wedstrijden wijzigt alleen de wedstrijdgegevens. ELO scores van spelers worden niet automatisch herberekend. Dit kan leiden tot inconsistenties in de ratings.")
                                    st.rerun()
                                else:
                                    st.error("Er is een fout opgetreden bij het bijwerken van de wedstrijd.")
        else:
            st.info("Geen spelers beschikbaar om wedstrijden mee te bewerken.")
else:
    st.info("Geen wedstrijden om te beheren.")

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