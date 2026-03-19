from __future__ import annotations
import datetime
import time
import pandas as pd
import streamlit as st

# Typing hints (optional lightweight)
from typing import Optional

PASSWORD = "Klinker"  # TODO: verplaats naar secrets of env variabele

# ---------------------------------------------------------------------------
# Helper: Authenticatie
# ---------------------------------------------------------------------------
def _ensure_authentication() -> bool:
    """Toont een password prompt totdat de gebruiker ingelogd is.
    Return True indien geauthenticeerd.
    """
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True

    st.subheader("Login vereist")
    password = st.text_input("Voer wachtwoord in", type="password")
    if password == PASSWORD:
        st.session_state.authenticated = True
        st.success("Ingelogd – laden...")
        st.rerun()
    elif password:
        st.error("Ongeldig wachtwoord.")
    return False

# ---------------------------------------------------------------------------
# Wedstrijden verwijderen
# ---------------------------------------------------------------------------
def _render_match_delete(db, matches_df: pd.DataFrame):
    st.write("**Wedstrijd(en) verwijderen**")
    elo_delete_option = st.radio(
        "ELO herberekening bij verwijdering:",
        options=[
            "🔄 Automatisch herberekenen na verwijdering (aanbevolen)",
            "⚠️ Alleen verwijderen (geen ELO update)",
        ],
        help="Automatische herberekening zorgt voor correcte ELO scores na verwijdering.",
        key="elo_delete_option",
    )
    if elo_delete_option == "⚠️ Alleen verwijderen (geen ELO update)":
        st.warning("\n⚠️ **Let op:** Deze optie is alleen bedoeld voor testen of debuggen. Gebruik dit niet voor reguliere uitslagen! Het verwijderen van wedstrijden zonder ELO herberekening kan leiden tot inconsistente of foutieve ratings.\n")
    auto_recalc_delete = elo_delete_option.startswith("🔄")
    
    matches_display_df = matches_df.copy()
    # Detect home/away columns
    if not matches_display_df.empty:
        match_row = matches_display_df.iloc[0]
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    else:
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    
    matches_display_df["display"] = matches_display_df.apply(
        lambda row: f"{pd.to_datetime(row.get('timestamp')).strftime('%d-%m-%Y %H:%M') if row.get('timestamp') else 'Geen tijd'} - "
        f"{row.get(home_cols[0], 'N/A')}/{row.get(home_cols[1], 'N/A')} vs {row.get(away_cols[0], 'N/A')}/{row.get(away_cols[1], 'N/A')}: "
        f"{row.get('thuis_score', 'N/A')}-{row.get('uit_score', 'N/A')}",
        axis=1,
    )

    st.write("**Enkele wedstrijd verwijderen:**")
    match_to_delete = st.selectbox(
        "Selecteer een wedstrijd om te verwijderen",
        options=matches_display_df["display"].tolist(),
        key="single_match_delete",
    )
    if st.button("Verwijder geselecteerde wedstrijd", key="delete_single"):
        match_row = matches_display_df[matches_display_df["display"] == match_to_delete]
        if not match_row.empty:
            match_id = match_row.iloc[0]["match_id"]
            with st.spinner("Wedstrijd wordt verwijderd..."):
                try:
                    if auto_recalc_delete:
                        success = db.delete_match_with_elo_recalculation(match_id)
                        action_type = "delete_match_with_elo_recalculation"
                    else:
                        success = db.delete_match_by_id(match_id)
                        action_type = "delete_match"
                except db.FirestoreUnavailable as e:
                    st.error("Database niet bereikbaar: mogelijk budgetlimiet bereikt.")
                    with st.expander("Toon technische details"):
                        st.code(str(e.details) if hasattr(e, 'details') else str(e))
                    return
                if success:
                    from utils.utils_beheer_log import log_admin_action
                    log_admin_action(
                        action_type=action_type,
                        user=st.session_state.get("user", "onbekend"),
                        details={"match_id": match_id, "display": match_to_delete},
                        db=db.db
                    )
                    if auto_recalc_delete:
                        st.success("Wedstrijd succesvol verwijderd en ELO scores herberekend!")
                    else:
                        st.success("Wedstrijd succesvol verwijderd.")
                        st.warning("⚠️ ELO scores zijn niet herberekend.")
                    time.sleep(1)
                    st.rerun()

    st.write("**Meerdere wedstrijden verwijderen:**")
    matches_to_delete = st.multiselect(
        "Selecteer wedstrijden om te verwijderen",
        options=matches_display_df["display"].tolist(),
        key="multi_match_delete",
    )
    if matches_to_delete and st.button(
        "Verwijder geselecteerde wedstrijden", key="delete_multiple"
    ):
        with st.spinner(f"Bezig met verwijderen van {len(matches_to_delete)} wedstrijden..."):
            success_count = 0
            for match_display in matches_to_delete:
                match_row = matches_display_df[matches_display_df["display"] == match_display]
                if not match_row.empty:
                    match_id = match_row.iloc[0]["match_id"]
                    # Verwijder wedstrijd en bijbehorende ELO-logs
                    if db.delete_match_by_id(match_id):
                        # Verwijder ELO-logs met deze match_id
                        try:
                            from google.cloud.firestore_v1.base_query import FieldFilter
                            elo_docs = db.elo_ref.where(filter=FieldFilter('match_id', '==', match_id)).stream()
                            batch = db.db.batch()
                            batch_counter = 0
                            for doc in elo_docs:
                                batch.delete(doc.reference)
                                batch_counter += 1
                                if batch_counter >= 400:
                                    batch.commit()
                                    batch = db.db.batch()
                                    batch_counter = 0
                            if batch_counter > 0:
                                batch.commit()
                        except Exception as e:
                            st.warning(f"Kon ELO-logs voor match {match_id} niet verwijderen: {e}")
                        success_count += 1
            if success_count == len(matches_to_delete):
                st.success(f"Alle {success_count} wedstrijden en bijbehorende ELO-logs succesvol verwijderd.")
            else:
                st.warning(f"{success_count} van de {len(matches_to_delete)} wedstrijden verwijderd.")
            time.sleep(1)
            st.rerun()

# ---------------------------------------------------------------------------
# Wedstrijd bewerken
# ---------------------------------------------------------------------------
def _render_match_edit(db, matches_df: pd.DataFrame, players_df: pd.DataFrame):
    st.write("**Wedstrijd bewerken**")
    elo_option = st.radio(
        "ELO herberekening optie:",
        options=[
            "🔄 Automatisch herberekenen (aanbevolen)",
            "⚠️ Alleen wedstrijd aanpassen (geen ELO update)",
        ],
        help="Automatische herberekening zorgt for correcte ELO scores maar duurt langer.",
    )
    if elo_option == "⚠️ Alleen wedstrijd aanpassen (geen ELO update)":
        st.warning("\n⚠️ **Let op:** Deze optie is alleen bedoeld voor testen of debuggen. Gebruik dit niet voor reguliere uitslagen! Het aanpassen van wedstrijden zonder ELO herberekening kan leiden tot inconsistente of foutieve ratings.\n")
    auto_recalculate = elo_option.startswith("🔄")
    
    if players_df.empty:
        st.info("Geen spelers beschikbaar om wedstrijden mee te bewerken.")
        return

    player_names = sorted(players_df["speler_naam"].tolist())
    matches_display_df = matches_df.copy()
    # Detect home/away columns
    if not matches_display_df.empty:
        match_row = matches_display_df.iloc[0]
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    else:
        home_cols = ['thuis_1', 'thuis_2']
        away_cols = ['uit_1', 'uit_2']
    matches_display_df["display"] = matches_display_df.apply(
        lambda row: f"{pd.to_datetime(row.get('timestamp')).strftime('%d-%m-%Y %H:%M') if row.get('timestamp') else 'Geen tijd'} - "
        f"{row.get(home_cols[0], 'N/A')}/{row.get(home_cols[1], 'N/A')} vs {row.get(away_cols[0], 'N/A')}/{row.get(away_cols[1], 'N/A')}: "
        f"{row.get('thuis_score', 'N/A')}-{row.get('uit_score', 'N/A')}",
        axis=1,
    )
    match_to_edit = st.selectbox(
        "Selecteer een wedstrijd om te bewerken",
        options=matches_display_df["display"].tolist(),
        key="match_edit_select",
    )
    if not match_to_edit:
        return
    match_idx = matches_display_df[matches_display_df["display"] == match_to_edit].index[0]
    match_data = matches_display_df.loc[match_idx]

    st.write("**Huidige wedstrijd gegevens:**")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Thuis team:** {match_data.get('thuis_1')} & {match_data.get('thuis_2')}")
        st.write(f"**Thuis score:** {match_data.get('thuis_score')}")
        st.write(
            f"**Klinkers thuis:** {match_data.get('klinkers_thuis_1', 0)} & {match_data.get('klinkers_thuis_2', 0)}"
        )
    with col2:
        st.write(f"**Uit team:** {match_data.get('uit_1')} & {match_data.get('uit_2')}")
        st.write(f"**Uit score:** {match_data.get('uit_score')}")
        st.write(
            f"**Klinkers uit:** {match_data.get('klinkers_uit_1', 0)} & {match_data.get('klinkers_uit_2', 0)}"
        )

    st.write("**Bewerk wedstrijd:**")
    with st.form("edit_match_form"):
        edit_cols = st.columns(4)
        new_thuis_1 = edit_cols[0].selectbox(
            "Thuis 1", player_names,
            index=player_names.index(match_data.get("thuis_1")) if match_data.get("thuis_1") in player_names else 0,
        )
        new_thuis_2 = edit_cols[1].selectbox(
            "Thuis 2", player_names,
            index=player_names.index(match_data.get("thuis_2")) if match_data.get("thuis_2") in player_names else 1,
        )
        new_uit_1 = edit_cols[2].selectbox(
            "Uit 1", player_names,
            index=player_names.index(match_data.get("uit_1")) if match_data.get("uit_1") in player_names else 2,
        )
        new_uit_2 = edit_cols[3].selectbox(
            "Uit 2", player_names,
            index=player_names.index(match_data.get("uit_2")) if match_data.get("uit_2") in player_names else 3,
        )
        score_cols = st.columns(2)
        def safe_int(val, default=0):
            try:
                # Handle pandas Series, None, or direct int
                if isinstance(val, pd.Series):
                    val = val.iloc[0] if not val.empty else default
                if val is None or (isinstance(val, float) and pd.isna(val)):
                    return default
                return int(val)
            except Exception:
                return default

        new_thuis_score = score_cols[0].number_input(
            "Thuis Score", min_value=0, max_value=10, value=safe_int(match_data.get("thuis_score", 0)), step=1
        )
        new_uit_score = score_cols[1].number_input(
            "Uit Score", min_value=0, max_value=10, value=safe_int(match_data.get("uit_score", 0)), step=1
        )
        klinker_cols = st.columns(4)
        new_klinkers_thuis_1 = klinker_cols[0].number_input(
            "Klinkers Thuis 1", min_value=0, max_value=10, value=safe_int(match_data.get("klinkers_thuis_1", 0)), step=1
        )
        new_klinkers_thuis_2 = klinker_cols[1].number_input(
            "Klinkers Thuis 2", min_value=0, max_value=10, value=safe_int(match_data.get("klinkers_thuis_2", 0)), step=1
        )
        new_klinkers_uit_1 = klinker_cols[2].number_input(
            "Klinkers Uit 1", min_value=0, max_value=10, value=safe_int(match_data.get("klinkers_uit_1", 0)), step=1
        )
        new_klinkers_uit_2 = klinker_cols[3].number_input(
            "Klinkers Uit 2", min_value=0, max_value=10, value=safe_int(match_data.get("klinkers_uit_2", 0)), step=1
        )
        if st.form_submit_button("Bewaar wijzigingen"):
            if new_thuis_score == 10 and new_uit_score == 10:
                st.error("Beide scores kunnen niet 10 zijn.")
                return
            if new_thuis_score != 10 and new_uit_score != 10:
                st.error("Eén van de scores moet 10 zijn.")
                return
            if len({new_thuis_1, new_thuis_2, new_uit_1, new_uit_2}) < 4:
                st.error("Selecteer vier unieke spelers.")
                return
            updated = {
                "thuis_1": new_thuis_1,
                "thuis_2": new_thuis_2,
                "uit_1": new_uit_1,
                "uit_2": new_uit_2,
                "thuis_score": new_thuis_score,
                "uit_score": new_uit_score,
                "klinkers_thuis_1": new_klinkers_thuis_1,
                "klinkers_thuis_2": new_klinkers_thuis_2,
                "klinkers_uit_1": new_klinkers_uit_1,
                "klinkers_uit_2": new_klinkers_uit_2,
                "timestamp": match_data.get("timestamp"),
            }
            with st.spinner("Wedstrijd wordt bijgewerkt..."):
                if auto_recalculate:
                    success = db.update_match_with_elo_recalculation(match_data["match_id"], updated)
                    action_type = "update_match_with_elo_recalculation"
                else:
                    success = db.update_match(match_data["match_id"], updated)
                    action_type = "update_match"
                from utils.utils_beheer_log import log_admin_action
                log_admin_action(
                    action_type=action_type,
                    user=st.session_state.get("user", "onbekend"),
                    details={"match_id": match_data["match_id"], "updated": updated},
                    db=db.db
                )
                if success:
                    if auto_recalculate:
                        st.success("Wedstrijd succesvol bijgewerkt en ELO scores herberekend!")
                    else:
                        st.success("Wedstrijd succesvol bijgewerkt!")
                        st.warning(
                            "⚠️ **Belangrijk:** ELO scores zijn niet herberekend. Dit kan leiden tot inconsistenties."
                        )
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error(
                        "Er is een fout opgetreden bij het bijwerken van de wedstrijd (of herberekenen)."
                    )

# ---------------------------------------------------------------------------
# Upload sectie (wedstrijden, spelers, seizoenen)
# ---------------------------------------------------------------------------
def _render_uploads(db, players_df: pd.DataFrame):
    st.write("**Historische Data Upload**")
    st.info("📋 Upload historische wedstrijdgegevens en spelergegevens via CSV bestanden.")
    upload_subtab1, upload_subtab2, upload_subtab3 = st.tabs(
        ["🏆 Wedstrijden", "👥 Spelers", "📅 Seizoenen"]
    )
    # Wedstrijden
    with upload_subtab1:
        st.subheader("Wedstrijdgegevens Uploaden")
        st.markdown(
            """
            **📋 Vereist CSV formaat voor wedstrijden:**
            
            **Verplichte kolommen:**
            - thuis_1, thuis_2, uit_1, uit_2, thuis_score, uit_score
            
            **Optioneel:**
            - klinkers_thuis_1, klinkers_thuis_2, klinkers_uit_1, klinkers_uit_2, timestamp
            
            **Bestandsformaat:**
            - CSV gescheiden door komma (,) of puntkomma (;)
            - UTF-8 of Windows-1252 encoding
            
            **Let op:**
            - Spelersnamen moeten exact overeenkomen met bestaande spelers
            - Score: één team moet 10 scoren, andere 0-9
            - Timestamp mag leeg zijn, dan wordt huidige tijd gebruikt
            """
        )
        uploaded_matches = st.file_uploader(
            "📁 Upload wedstrijden CSV bestand",
            type=["csv"],
            key="matches_upload_main_uploads_tab",
            help="Upload een CSV bestand met historische wedstrijdgegevens",
        )
        if uploaded_matches is not None:
            try:
                import chardet
                raw = uploaded_matches.read()
                encoding_guess = chardet.detect(raw)
                encoding = encoding_guess['encoding'] if encoding_guess['confidence'] > 0.5 else 'utf-8'
                import io
                for sep in [';', ',']:
                    try:
                        matches_upload_df = pd.read_csv(io.BytesIO(raw), sep=sep, encoding=encoding)
                        if len(matches_upload_df.columns) >= 6:
                            break
                    except Exception:
                        continue
                else:
                    st.error("❌ Kan CSV niet inlezen. Controleer scheidingsteken en encoding.")
                    return
                # Check for timestamp, date, tijd columns
                has_timestamp = "timestamp" in matches_upload_df.columns
                has_date = "date" in matches_upload_df.columns
                has_tijd = "tijd" in matches_upload_df.columns
                if has_timestamp and (has_date or has_tijd):
                    st.info("Kolommen 'date' en/of 'tijd' worden genegeerd omdat 'timestamp' aanwezig is.")
                if not has_timestamp and (has_date and has_tijd):
                    # Combine date and tijd to timestamp
                    st.info("Kolommen 'date' en 'tijd' worden samengevoegd tot 'timestamp'.")
                    matches_upload_df["timestamp"] = matches_upload_df["date"].astype(str) + " " + matches_upload_df["tijd"].astype(str)
                if not ("timestamp" in matches_upload_df.columns):
                    st.error("❌ Geen 'timestamp' of 'date'+'tijd' kolommen gevonden. Een datum/tijd is verplicht.")
                    return
                st.dataframe(matches_upload_df.head(10), width='stretch')
                # Accept both old and new column names
                required_sets = [
                    ["thuis_1", "thuis_2", "uit_1", "uit_2", "thuis_score", "uit_score"],
                    ["thuis_1", "thuis_2", "uit_1", "uit_2", "thuis_score", "uit_score"]
                ]
                if not any(all(c in matches_upload_df.columns for c in req) for req in required_sets):
                    st.error("❌ Ontbrekende verplichte kolommen: upload moet (thuis_1, thuis_2, uit_1, uit_2) bevatten.")
                    return
                for opt in [
                    "klinkers_thuis_1",
                    "klinkers_thuis_2",
                    "klinkers_uit_1",
                    "klinkers_uit_2",
                ]:
                    if opt not in matches_upload_df.columns:
                        matches_upload_df[opt] = 0
                import re
                validation_errors = []
                timestamp_format = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
                import unicodedata
                def is_allowed_char(c):
                    # Toegestaan: standaard printable ASCII, plus alle letters met diakritische tekens (é, ö, ü, etc.)
                    if 32 <= ord(c) <= 126:
                        return True
                    cat = unicodedata.category(c)
                    # Letter (L*) of Mark (M*) (voor accenten)
                    return cat.startswith('L') or cat.startswith('M') or c in " -'"

                for idx in range(len(matches_upload_df)):
                    row = matches_upload_df.iloc[idx]
                    # Check timestamp format
                    ts = str(row["timestamp"]).strip()
                    if not timestamp_format.match(ts):
                        validation_errors.append(f"Rij {idx+1}: Ongeldig timestamp formaat '{ts}'. Verwacht: JJJJ-MM-DD UU:MM:SS")
                    # Check for strange characters in all string columns, allow diacritics
                    for col in matches_upload_df.columns:
                        val = str(row[col])
                        if any(not is_allowed_char(c) for c in val):
                            validation_errors.append(f"Rij {idx+1}, kolom '{col}': Vreemd teken aangetroffen")
                # Stop direct bij fouten
                # Add missing players automatically
                current_players = players_df["speler_naam"].tolist() if not players_df.empty else []
                new_players = set()
                for row_idx in range(len(matches_upload_df)):
                    row = matches_upload_df.iloc[row_idx]
                    p = [row["thuis_1"], row["thuis_2"], row["uit_1"], row["uit_2"]]
                    for player in p:
                        if player not in current_players and player not in new_players:
                            # Add player with rating 1000
                            from firestore_service import add_player
                            result = add_player(player, 1000)
                            if result == "Success":
                                new_players.add(player)
                                current_players.append(player)
                                st.info(f"Speler '{player}' toegevoegd aan spelerslijst.")
                            else:
                                validation_errors.append(f"Rij {row_idx+1}: Speler '{player}' kon niet worden toegevoegd: {result}")
                    t_score = row["thuis_score"]
                    u_score = row["uit_score"]
                    if not (
                        (t_score == 10 and 0 <= u_score <= 9)
                        or (u_score == 10 and 0 <= t_score <= 9)
                    ):
                        validation_errors.append(f"Rij {row_idx+1}: Ongeldige score combinatie {t_score}-{u_score}")
                    if len(set(p)) != 4:
                        validation_errors.append(f"Rij {row_idx+1}: Niet alle spelers zijn uniek")
                if validation_errors:
                    st.error("❌ Validatie fouten gevonden:")
                    for err in validation_errors[:10]:
                        st.error(f"• {err}")
                    if len(validation_errors) > 10:
                        st.error(f"• ... en {len(validation_errors) - 10} meer fouten")
                    return
                st.success("✅ Alle data is geldig!")
                elo_recalc_option = st.radio(
                    "ELO herberekening na upload:",
                    options=[
                        "🔄 Volledige ELO reset en herberekening (aanbevolen)",
                        "⚠️ Geen herberekening (sneller maar mogelijk inconsistent)",
                    ],
                    key="elo_recalc_upload",
                )
                st.info(f"📊 Upload samenvatting: {len(matches_upload_df)} wedstrijden klaar voor import")
                if st.button("🚀 Import Wedstrijden", type="primary"):
                    with st.spinner(f"Bezig met importeren van {len(matches_upload_df)} wedstrijden..."):
                        added, duplicates = db.import_matches(matches_upload_df.to_dict("records"))
                        if elo_recalc_option.startswith("🔄") and added > 0:
                            db.reset_all_elos()
                        st.success(f"🎉 Import voltooid! {added} toegevoegd, {duplicates} duplicaten genegeerd.")
                        if elo_recalc_option.startswith("🔄"):
                            st.success("✅ ELO scores zijn volledig herberekend!")
                        time.sleep(1.5)
                        st.rerun()
            except Exception as e:
                st.error(f"❌ Fout bij verwerken CSV: {e}")
    # Spelers
    with upload_subtab2:
        st.subheader("Spelergegevens Uploaden")
        st.markdown(
            """CSV kolommen: speler_naam (verplicht), rating (optioneel, default 1000)"""
        )
        uploaded_players = st.file_uploader(
            "📁 Upload spelers CSV bestand",
            type=["csv"],
            key="players_upload_main",
            help="Upload spelergegevens",
        )
        if uploaded_players is not None:
            try:
                players_upload_df = pd.read_csv(uploaded_players)
                st.dataframe(players_upload_df.head(10), width='stretch')
                if "speler_naam" not in players_upload_df.columns:
                    st.error("❌ Kolom 'speler_naam' is verplicht!")
                    return
                if "rating" not in players_upload_df.columns:
                    players_upload_df["rating"] = 1000
                invalid = []
                duplicate = []
                seen = set()
                for i in range(len(players_upload_df)):
                    name = str(players_upload_df.iloc[i]["speler_naam"]).strip()
                    if (
                        not name
                        or not name.replace(" ", "").isalpha()
                        or len(name) < 2
                        or len(name) > 50
                    ):
                        invalid.append(f"Rij {i+1}: '{name}'")
                    lname = name.lower()
                    if lname in seen:
                        duplicate.append(f"Rij {i+1}: '{name}'")
                    else:
                        seen.add(lname)
                if invalid or duplicate:
                    st.error("❌ Validatie fouten:")
                    for err in invalid[:5]:
                        st.error(f"• Ongeldige naam: {err}")
                    for err in duplicate[:5]:
                        st.error(f"• Duplicaat: {err}")
                    return
                st.success("✅ Alle spelergegevens zijn geldig!")
                st.info(
                    f"📊 Upload samenvatting: {len(players_upload_df)} spelers klaar for import"
                )
                if st.button("🚀 Import Spelers", type="primary"):
                    with st.spinner(
                        f"Bezig met importeren van {len(players_upload_df)} spelers..."
                    ):
                        added, duplicates = db.import_players(
                            players_upload_df.to_dict("records")
                        )
                        st.success(
                            f"🎉 Import voltooid! {added} toegevoegd, {duplicates} genegeerd."
                        )
                        time.sleep(1.5)
                        st.rerun()
            except Exception as e:
                st.error(f"❌ Fout bij verwerken CSV: {e}")
    # Seizoenen upload-tab verwijderd: seizoenen worden automatisch bepaald uit wedstrijddata

# ---------------------------------------------------------------------------
# Systeem beheer
# ---------------------------------------------------------------------------
def _render_system_management(db, players_df: pd.DataFrame):
    st.header("⚙️ Systeem Beheer")
    st.subheader("ELO Rating Beheer")
    # Optie voor complete ELO reset verwijderd om onbedoelde zware acties te voorkomen.

    st.markdown("<hr>", unsafe_allow_html=True)
    # Optie voor seizoensherberekening verwijderd. Gebruik scripts in 'admin' folder.
    st.markdown("<hr>", unsafe_allow_html=True)
        # Opmerking: complete ELO reset UI is verwijderd om onbedoelde zware acties te voorkomen.
    
    
    st.subheader("Speler Verwijderen")
    if players_df.empty:
        st.info("Geen spelers om te beheren.")
    else:
        names = players_df["speler_naam"].tolist()
        ids = players_df["speler_id"].tolist()
        mapping = {n: i for n, i in zip(names, ids)}
        player_to_delete = st.selectbox(
            "Selecteer een speler om te verwijderen", options=sorted(names)
        )
        if st.button(f"Verwijder {player_to_delete} Permanent"):
            pid = mapping.get(player_to_delete)
            if pid:
                with st.spinner(
                    f"Bezig met verwijderen van {player_to_delete}..."
                ):
                    if db.delete_player_by_id(pid):
                        st.success(
                            f"{player_to_delete} en alle bijbehorende data is verwijderd."
                        )
                        st.rerun()
                    else:
                        st.error("Kon speler niet verwijderen.")
            else:
                st.error("Kon de speler ID niet vinden.")
    st.markdown("<hr>", unsafe_allow_html=True)
    # Seizoen Verwijderen UI verwijderd. Gebruik scripts in 'admin' voor seizoensbeheer.
    st.markdown("<hr>", unsafe_allow_html=True)
    # Overige Database Cleanup - 'Verwijder alle Requests' optie verwijderd

    # Database Inspectie & Schema Vergelijking
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("🔎 Database Inspectie & Schema")
    st.caption("Bekijk welke collecties en velden in Firestore aanwezig zijn en vergelijk met wat de app verwacht.")

    if st.button("Analyseer Firestore schema"):
        with st.spinner("Firestore wordt geïnspecteerd..."):
            try:
                expected = db.expected_schema()
                actual = db.inspect_collections(max_docs=250)

                for coll in ["spelers", "uitslag", "elo", "requests"]:
                    st.markdown(f"**Collectie: `{coll}`**")
                    exp = expected.get(coll, {})
                    act = actual.get(coll, {"fields": [], "sample_size": 0, "examples": []})

                    exp_required = exp.get("required", set())
                    exp_optional = exp.get("optional", set())
                    exp_derived = exp.get("derived_only_in_app", set())
                    act_fields = set(act.get("fields", []))

                    missing = sorted(list((exp_required | exp_optional) - act_fields))
                    unexpected = sorted(list(act_fields - (exp_required | exp_optional)))

                    colA, colB, colC = st.columns(3)
                    with colA:
                        st.write("Verwacht (required):")
                        st.code(", ".join(sorted(list(exp_required))) or "—")
                    with colB:
                        st.write("Verwacht (optioneel):")
                        st.code(", ".join(sorted(list(exp_optional))) or "—")
                    with colC:
                        st.write("Alleen in app (afgeleid):")
                        st.code(", ".join(sorted(list(exp_derived))) or "—")

                    st.write("Aangetroffen velden (sample):")
                    st.code(", ".join(sorted(list(act_fields))) or "—")

                    info_cols = st.columns(2)
                    with info_cols[0]:
                        st.write("Ontbrekend t.o.v. verwachting:")
                        st.code(", ".join(missing) or "—")
                    with info_cols[1]:
                        st.write("Onverwacht (bestaat niet in app):")
                        st.code(", ".join(unexpected) or "—")

                    if act.get("examples"):
                        st.write("Voorbeelden (max 5):")
                        st.dataframe(pd.DataFrame(act["examples"]))
                    st.markdown("---")
            except Exception as e:
                st.error(f"Schema inspectie mislukt: {e}")

# ---------------------------------------------------------------------------
# Hoofd entry
# ---------------------------------------------------------------------------
def render_admin_tab(db, players_df: pd.DataFrame, matches_df: pd.DataFrame):
    """Rendert de volledige beheer tab. Houdt de code in app.py minimaal."""
    st.header("⚙️ Beheer")
    if not _ensure_authentication():
        return

    # Hoofd tabs in beheer
    tab_verwijderen, tab_bewerken, tab_upload = st.tabs([
        "🗑️ Verwijderen", "✏️ Bewerken", "📁 Upload"])


    # 'ELO beheer' is verplaatst naar admin scripts; UI verwijderd to prevent heavy operations.

    with tab_verwijderen:
        st.header("🗑️ Verwijderen")
        st.subheader("🗑️ Wedstrijden verwijderen")
        _render_match_delete(db, matches_df)


        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("🗑️ Speler Verwijderen")
        if players_df.empty:
            st.info("Geen spelers om te beheren.")
        else:
            names = players_df["speler_naam"].tolist()
            ids = players_df["speler_id"].tolist()
            mapping = {n: i for n, i in zip(names, ids)}
            player_to_delete = st.selectbox(
                "Selecteer een speler om te verwijderen", options=sorted(names)
            )
            if st.button(f"Verwijder {player_to_delete} Permanent", key="delete_player_perm"):
                pid = mapping.get(player_to_delete)
                if pid:
                    with st.spinner(
                        f"Bezig met verwijderen van {player_to_delete}..."
                    ):
                        if db.delete_player_by_id(pid):
                            st.success(
                                f"{player_to_delete} en alle bijbehorende data is verwijderd."
                            )
                            st.rerun()
                        else:
                            st.error("Kon speler niet verwijderen.")
                else:
                    st.error("Kon de speler ID niet vinden.")

        # Seizoen verwijderen optie verwijderd

    with tab_bewerken:
        st.header("✏️ Bewerken")
        _render_match_edit(db, matches_df, players_df)

        st.markdown("---")
        st.subheader("Spelerslijst namen corrigeren")
        spelers_df = players_df.copy()
        st.dataframe(spelers_df[['speler_naam', 'rating']], width='stretch')

        st.info("Hier kun je namen corrigeren. Voor het samenvoegen van dubbele spelers (merge), gebruik het admin-script 'admin/merge_players.py'.")

        speler_select = st.selectbox("Selecteer speler om naam aan te passen", sorted(spelers_df['speler_naam'].tolist()))
        nieuwe_naam = st.text_input("Nieuwe naam", value=speler_select)
        if st.button("Pas naam aan"):
            from firestore_service import players_ref, elo_ref, matches_ref
            from google.cloud.firestore_v1.base_query import FieldFilter
            # Update naam in spelers, elo, uitslag
            # 1. Speler document
            speler_docs = list(players_ref.where(filter=FieldFilter('speler_naam', '==', speler_select)).stream())
            for doc in speler_docs:
                doc.reference.update({'speler_naam': nieuwe_naam})
            # 2. ELO documenten
            elo_docs = list(elo_ref.where(filter=FieldFilter('speler_naam', '==', speler_select)).stream())
            for doc in elo_docs:
                doc.reference.update({'speler_naam': nieuwe_naam})
            # 3. Wedstrijden
            for field in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
                match_docs = list(matches_ref.where(filter=FieldFilter(field, '==', speler_select)).stream())
                for doc in match_docs:
                    doc.reference.update({field: nieuwe_naam})
            st.success(f"Naam van '{speler_select}' aangepast naar '{nieuwe_naam}'. Alle data is bijgewerkt.")
            db.clear_all_caches()
            st.rerun()

    with tab_upload:
        st.header("📁 Upload")
        st.info("💡 Geen wedstrijden gevonden. Upload historische data om te beginnen!")
        _render_uploads(db, players_df)

    # De inspectie-subtab is verplaatst naar admin/inspectie.py als zelfstandig script.
