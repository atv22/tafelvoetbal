"""
TAB 3: Spelers module voor tafelvoetbal app
Bevat speler beheer functionaliteit en ELO-verloop grafieken
"""
import streamlit as st
import pandas as pd
import firestore_service as db
import plotly.express as px
from utils.utils_seizoen import get_current_season
from utils.utils import IGNORE_PLAYERS, add_name

def render_players_tab(players_df, matches_df, seasons_df, elo_df):
    st.header("👥 Speler Beheer & Historie")
    st.caption(
        "Bekijk hier het historische ELO-verloop per speler of registreer een nieuwe speler voor de competitie."
    )

    if players_df is None or players_df.empty:
        st.info("Nog geen spelers geregistreerd.")
        render_add_player_section()
        return

    # --- ELO Ontwikkeling Sectie (Bovenaan) ---
    st.subheader("📈 ELO Ontwikkeling")
    
    # 1. Bepaal standaard speler (Nummer 1 van de ranglijst)
    # Filter eerst 'Niemand' en test-spelers uit - Case-insensitive
    valid_players = players_df[~players_df['speler_naam'].str.lower().str.strip().isin(IGNORE_PLAYERS)].drop_duplicates(subset=['speler_naam'], keep='first')
    
    if valid_players.empty:
        st.info("Geen geldige spelers gevonden.")
        return

    top_player_name = valid_players.sort_values('rating', ascending=False).iloc[0]['speler_naam']
    
    col1, col2 = st.columns(2)
    with col1:
        player_names = sorted(valid_players['speler_naam'].tolist())
        selected_player = st.selectbox(
            "Selecteer speler:", 
            player_names, 
            index=player_names.index(top_player_name) if top_player_name in player_names else 0,
            key="player_tab_select"
        )
    
    with col2:
        period_option = st.radio(
            "Periode:",
            ["Alle seizoenen", "Huidig seizoen"],
            horizontal=True,
            key="player_tab_period"
        )

    # 2. Filter ELO data voor de grafiek
    if selected_player and elo_df is not None and not elo_df.empty:
        # Haal historie op (gefilterd op speler)
        history_df = elo_df[elo_df['speler_naam'] == selected_player].copy()
        
        if not history_df.empty:
            history_df['timestamp'] = pd.to_datetime(history_df['timestamp'], utc=True)
            
            # Filter op huidig seizoen indien gevraagd
            if period_option == "Huidig seizoen":
                curr_season = get_current_season(seasons_df)
                if curr_season is not None:
                    # Normaliseer alles naar naive UTC voor vergelijking
                    start = pd.to_datetime(curr_season.get('start_datum', curr_season.get('startdatum')), utc=True).tz_localize(None)
                    history_df['ts_naive'] = history_df['timestamp'].dt.tz_localize(None)
                    history_df = history_df[history_df['ts_naive'] >= start]

            if not history_df.empty:
                history_df = history_df.sort_values('timestamp')
                history_df['rating_rounded'] = history_df['rating'].round(0).astype(int)
                
                fig = px.line(
                    history_df,
                    x='timestamp',
                    y='rating_rounded',
                    title=f"ELO verloop van {selected_player}",
                    labels={'timestamp': 'Datum', 'rating_rounded': 'ELO Rating'},
                    markers=True,
                    hover_data={'rating_rounded': True}
                )
                fig.update_layout(xaxis_title="Datum", yaxis_title="ELO Rating")
                st.plotly_chart(fig)
            else:
                st.info(f"Geen ELO-historie gevonden voor {selected_player} in het huidige seizoen.")
        else:
            st.info(f"Nog geen wedstrijddata beschikbaar voor {selected_player}.")

    st.divider()

    # --- Speler Beheer Sectie (Onderaan) ---
    render_player_list_and_management(valid_players)

def render_player_list_and_management(players_df):
    """Sectie voor het bekijken, toevoegen en verwijderen van spelers"""
    st.subheader("⚙️ Speler Lijst & Beheer")
    
    # Lijst met spelers
    st.write("**Geregistreerde spelers:**")
    display_df = players_df[['speler_naam', 'rating']].sort_values('speler_naam').copy()
    display_df['rating'] = pd.to_numeric(display_df['rating'], errors='coerce').fillna(1000).round(0).astype(int)
    display_df.columns = ['Naam', 'Huidige ELO']
    st.dataframe(display_df, hide_index=True, width='stretch')

    col_add, col_del = st.columns(2)
    
    with col_add:
        st.write("**Nieuwe speler toevoegen:**")
        new_player_name = st.text_input(
            "Naam van de speler:",
            key="new_player_name",
            placeholder="Bijv. 'Sanne'",
            help="Vereisten: begint met een hoofdletter, bevat alleen letters (en spaties), en is tussen de 2 en 50 tekens lang. Elke nieuwe speler start op 1000 ELO."
        )
        if st.button("➕ Speler Toevoegen"):
            if new_player_name and new_player_name.strip():
                add_name(new_player_name.strip())
            else:
                st.warning("Voer een naam in.")

    with col_del:
        st.write("**Speler verwijderen:**")
        player_to_del = st.selectbox(
            "Selecteer speler om te verwijderen:",
            [""] + sorted(players_df['speler_naam'].tolist()),
            key="del_player_select",
            help="Let op: dit verwijdert de speler en de bijbehorende ELO-historie definitief. Wil je alleen een spelfout corrigeren? Doe dat via het tabblad ⚙️ Beheer -> ✏️ Bewerken."
        )
        if st.button("🗑️ Verwijder Speler", type="secondary"):
            if player_to_del:
                st.session_state["confirm_del_player"] = player_to_del
            else:
                st.session_state.pop("confirm_del_player", None)
                st.warning("Selecteer een speler.")

        confirm_target = st.session_state.get("confirm_del_player")
        if confirm_target and confirm_target == player_to_del:
            st.warning(f"Weet je zeker dat je '{confirm_target}' wilt verwijderen? Alle historie wordt gewist!")
            c1, c2 = st.columns(2)
            with c1:
                if st.button(f"Ja, verwijder {confirm_target} definitief", key="confirm_del", type="primary"):
                    p_rows = players_df[players_df['speler_naam'] == confirm_target]
                    if not p_rows.empty:
                        p_id = p_rows.iloc[0]['speler_id']
                        with st.spinner("Verwijderen..."):
                            if db.delete_player_by_id(p_id):
                                st.session_state.pop("confirm_del_player", None)
                                st.success(f"Speler '{confirm_target}' verwijderd.")
                                st.rerun()
                            else:
                                st.error("Fout bij verwijderen.")
            with c2:
                if st.button("Annuleren", key="cancel_del_player"):
                    st.session_state.pop("confirm_del_player", None)
                    st.rerun()

def render_add_player_section():
    """Simpele sectie als er nog geen spelers zijn"""
    st.write("**Voeg je eerste speler toe:**")
    name = st.text_input("Naam:")
    if st.button("Toevoegen"):
        if name and name.strip():
            add_name(name.strip())

