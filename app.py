import streamlit as st
import pandas as pd
import time
from datetime import date
import firestore_service as db # Use Firestore
from styles import setup_page
from utils import elo_calculation, add_name, get_download_filename

setup_page()

st.title("Tafelvoetbal Competitie ⚽")

# --- Tab navigatie ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏠 Home", 
    "📝 Invullen", 
    "👥 Spelers", 
    "📊 Ruwe Data", 
    "⚙️ Beheer", 
    "ℹ️ Colofon"
])

# --- Data ophalen (eenmalig) ---
players_df = db.get_players()
matches_df = db.get_matches()

# --- Hulpfuncties ---
def calculate_stats(players, matches):
    """Bereken statistieken voor alle spelers"""
    stats_list = []
    for index, player in players.iterrows():
        player_name = str(player['speler_naam']) if player['speler_naam'] is not None else ""
        
        # Veilige filtering om KeyError te voorkomen
        conditions = []
        for col in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
            if col in matches.columns:
                conditions.append(matches[col] == player_name)
        
        if not conditions:
            player_matches = pd.DataFrame()
        else:
            player_matches = matches[pd.concat(conditions, axis=1).any(axis=1)]

        if player_matches.empty:
            stats = {'Gespeeld': 0, 'Voor': 0, 'Tegen': 0, 'Doelsaldo': 0, 'Klinkers': 0, 'Speler': ""}
        else:
            goals_for = 0
            goals_against = 0
            klinkers = 0
            for _, match in player_matches.iterrows():
                thuis_spelers = [match.get('thuis_1'), match.get('thuis_2')]
                uit_spelers = [match.get('uit_1'), match.get('uit_2')]
                
                if player_name in thuis_spelers:
                    goals_for += int(match.get('thuis_score', 0) or 0)
                    goals_against += int(match.get('uit_score', 0) or 0)
                    if player_name == match.get('thuis_1'):
                        klinkers += int(match.get('klinkers_thuis_1', 0) or 0)
                    else:
                        klinkers += int(match.get('klinkers_thuis_2', 0) or 0)
                elif player_name in uit_spelers:
                    goals_for += int(match.get('uit_score', 0) or 0)
                    goals_against += int(match.get('thuis_score', 0) or 0)
                    if player_name == match.get('uit_1'):
                        klinkers += int(match.get('klinkers_uit_1', 0) or 0)
                    else:
                        klinkers += int(match.get('klinkers_uit_2', 0) or 0)
            
            stats = {
                'Gespeeld': len(player_matches),
                'Voor': int(goals_for),
                'Tegen': int(goals_against),
                'Doelsaldo': int(goals_for - goals_against),
                'Klinkers': int(klinkers),
                'Speler': ""  # Placeholder voor string type
            }
        
        stats['Speler'] = player_name
        # Veilige conversie van rating met fallback naar 1000 als default
        rating_value = player.get('rating', 1000)
        if rating_value is None or pd.isna(rating_value):
            rating_value = 1000
        stats['ELO'] = int(rating_value)
        stats_list.append(stats)
        
    return pd.DataFrame(stats_list)

# ===== TAB 1: HOME =====
with tab1:
    st.header(":crown: ELO Rating :crown:")
    
    if players_df.empty:
        st.info("Nog geen spelers geregistreerd. Ga naar 'Spelers' om spelers toe te voegen.")
    else:
        # --- Huidige ELO rating tonen ---
        st.subheader("Huidige ELO rating van alle spelers")
        
        stats_df = calculate_stats(players_df, matches_df)
        
        # Sorteer en selecteer kolommen voor weergave
        display_df = stats_df.sort_values(by='ELO', ascending=False)
        st.dataframe(display_df[['Speler', 'ELO', 'Gespeeld', 'Voor', 'Tegen', 'Doelsaldo', 'Klinkers']], use_container_width=True)
        
        # --- ELO ontwikkeling tonen ---
        st.subheader("Ontwikkeling ELO rating per speler")
        
        player_names = sorted(players_df['speler_naam'].tolist())
        selected_player = st.selectbox("Selecteer een speler:", player_names)
        
        if selected_player:
            # Haal de ELO geschiedenis op voor de geselecteerde speler
            history_df = db.get_elo_history(_ttl=60, speler_naam=selected_player)
            
            if not history_df.empty:
                history_df['match_num'] = range(1, len(history_df) + 1)
                st.line_chart(history_df, x='match_num', y='rating')
            else:
                st.info(f"Geen ELO geschiedenis gevonden voor {selected_player}.")

# ===== TAB 2: INVULLEN =====
with tab2:
    st.header("Tafelvoetbal Competitie ⚽ — Invullen")
    
    if players_df.empty:
        st.warning("Er zijn nog geen spelers. Voeg eerst een speler toe via de 'Spelers' tab.")
    else:
        player_names = sorted(players_df['speler_naam'].tolist())
        player_elos = players_df.set_index('speler_naam')['rating'].to_dict()

        # --- UI ---
        klink = st.radio("Zijn er klinkers gescoord?", ("Nee", "Ja"))

        selected_names = {
            'Thuis 1': {'name': None, 'klinkers': 0},
            'Thuis 2': {'name': None, 'klinkers': 0},
            'Uit 1':   {'name': None, 'klinkers': 0},
            'Uit 2':   {'name': None, 'klinkers': 0},
        }

        with st.form("formulier"):
            cols = st.columns(4)
            for i, title in enumerate(selected_names):
                with cols[i]:
                    selected_names[title]['name'] = st.selectbox(title, player_names, key=f"sel_{title}", index=i % len(player_names))

            if klink == "Ja":
                klinker_cols = st.columns(4)
                for i, title in enumerate(selected_names):
                    with klinker_cols[i]:
                        selected_names[title]['klinkers'] = st.number_input(f"Klinkers {title}", min_value=0, max_value=10, step=1, key=f"kl_{title}")

            score_cols = st.columns(2)
            with score_cols[0]:
                home_score = st.number_input("Score Thuis:", min_value=0, max_value=10, step=1)
            with score_cols[1]:
                away_score = st.number_input("Score Uit:",   min_value=0, max_value=10, step=1)

            if st.form_submit_button("Verstuur Uitslag"):
                # --- Validatie ---
                if home_score == 10 and away_score == 10:
                    st.error('Beide scores kunnen niet 10 zijn.')
                    st.stop()
                if home_score != 10 and away_score != 10:
                    st.error('Eén van de scores moet 10 zijn.')
                    st.stop()
                
                player_list = [p['name'] for p in selected_names.values()]
                if len(set(player_list)) < 4:
                    st.error("Selecteer vier unieke spelers.")
                    st.stop()

                # --- ELO Berekening ---
                home_team_names = [selected_names['Thuis 1']['name'], selected_names['Thuis 2']['name']]
                away_team_names = [selected_names['Uit 1']['name'], selected_names['Uit 2']['name']]

                home_team_elos = [player_elos[p] for p in home_team_names]
                away_team_elos = [player_elos[p] for p in away_team_names]

                avg_elo_home = sum(home_team_elos) / 2
                avg_elo_away = sum(away_team_elos) / 2

                new_elos = {}
                for player_name in home_team_names:
                    new_elos[player_name] = elo_calculation(player_elos[player_name], avg_elo_away, home_score, away_score)
                for player_name in away_team_names:
                    new_elos[player_name] = elo_calculation(player_elos[player_name], avg_elo_home, away_score, home_score)

                # --- Data voorbereiden voor Firestore ---
                match_data = {
                    'thuis_1': selected_names['Thuis 1']['name'],
                    'thuis_2': selected_names['Thuis 2']['name'],
                    'uit_1': selected_names['Uit 1']['name'],
                    'uit_2': selected_names['Uit 2']['name'],
                    'thuis_score': home_score,
                    'uit_score': away_score,
                    'klinkers_thuis_1': selected_names['Thuis 1']['klinkers'],
                    'klinkers_thuis_2': selected_names['Thuis 2']['klinkers'],
                    'klinkers_uit_1': selected_names['Uit 1']['klinkers'],
                    'klinkers_uit_2': selected_names['Uit 2']['klinkers'],
                }

                elo_updates = list(new_elos.items())

                # --- Opslaan in Firestore ---
                success = db.add_match_and_update_elo(match_data, elo_updates)

                if success:
                    st.success("Uitslag en nieuwe ELO ratings succesvol opgeslagen!")
                    if (home_score == 10 and away_score == 0) or (home_score == 0 and away_score == 10):
                        st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Er is een fout opgetreden bij het opslaan van de wedstrijd.")

# ===== TAB 3: SPELERS =====
with tab3:
    st.header("Voeg een speler toe")
    name = st.text_input("Vul een naam in:")
    if st.button("Voeg naam toe"):
        add_name(name)

    st.markdown("<hr />", unsafe_allow_html=True)

    st.header("Huidige spelerslijst")

    if not players_df.empty:
        # We only need the names for this table
        df_namen = players_df[['speler_naam']].rename(columns={'speler_naam': 'Huidige namen'}).sort_values(by='Huidige namen')
        st.table(df_namen)
    else:
        st.info("Geen spelers gevonden.")

# ===== TAB 4: RUWE DATA =====
with tab4:
    st.header("Ruwe Data uit Firestore")

    # --- Spelers ---
    st.subheader("Spelers")
    if not players_df.empty:
        st.dataframe(players_df, use_container_width=True)
    else:
        st.info("Geen spelers gevonden in Firestore.")

    # --- Uitslagen (Matches) ---
    st.subheader("Uitslagen (Wedstrijden)")
    st.download_button(
        label="💾 Download Uitslagen",
        data=matches_df.to_csv(index=False).encode('utf-8'),
        file_name=get_download_filename('Tafelvoetbal_Uitslagen', 'csv'),
        mime='text/csv',
    )
    st.dataframe(matches_df, use_container_width=True)

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

# ===== TAB 5: BEHEER =====
with tab5:
    st.header("Beheer")
    
    # --- Authenticatie ---
    goede_wachtwoord = "Klinker"
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.subheader("Login vereist")
        password = st.text_input("Voer wachtwoord in", type="password")
        if password == goede_wachtwoord:
            st.session_state.authenticated = True
            st.rerun()
        elif password:
            st.error("Ongeldig wachtwoord.")
    else:
        # --- Speler Verwijderen ---
        st.subheader("Speler Verwijderen")

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

        # --- Overige entries ---
        st.subheader("Overige Entries Verwijderen")

        if st.button("Verwijder alle 'Requests'"):
            with st.spinner("Alle requests worden verwijderd..."):
                if db.clear_collection('requests'):
                    st.success("Alle requests zijn succesvol verwijderd.")
                    st.rerun()
                else:
                    st.error("Kon de requests niet verwijderen.")

# ===== TAB 6: COLOFON =====
with tab6:
    st.header("Colofon")
    st.write("Deze webapp is gemaakt met behulp van ChatGPT door Rick en Arthur")