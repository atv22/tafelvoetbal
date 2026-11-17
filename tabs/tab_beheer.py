from __future__ import annotations
import datetime
import hmac
import os
import time
import pandas as pd
import streamlit as st

# Typing hints (optional lightweight)
from typing import Optional


def _get_admin_password() -> str:
    """Haalt het beheerderswachtwoord op uit env, Streamlit secrets of fallback."""
    env_pw = os.environ.get("ADMIN_PASSWORD")
    if env_pw:
        return str(env_pw)
    try:
        if hasattr(st, "secrets") and "ADMIN_PASSWORD" in st.secrets:
            return str(st.secrets["ADMIN_PASSWORD"])
    except Exception:
        pass
    return "Klinker"


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
    if password:
        expected = _get_admin_password()
        if hmac.compare_digest(password.encode("utf-8"), expected.encode("utf-8")):
            st.session_state.authenticated = True
            st.success("Ingelogd – laden...")
            st.rerun()
        else:
            st.error("Ongeldig wachtwoord.")
    return False

# ---------------------------------------------------------------------------
# Wedstrijden verwijderen
# ---------------------------------------------------------------------------
def _render_match_delete(db, matches_df: pd.DataFrame):
    st.write("**Wedstrijd(en) verwijderen**")
    st.info("💡 Wedstrijden worden direct verwijderd. De ELO-scores worden vanavond om 23:00 uur automatisch herberekend om database-limieten te sparen.")

    if matches_df is None or matches_df.empty:
        st.info("Geen wedstrijden om te verwijderen.")
        return

    matches_display_df = matches_df.copy()
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
            st.session_state["confirm_delete_single_match"] = {
                "match_id": match_row.iloc[0]["match_id"],
                "display": match_to_delete,
            }

    pending_single = st.session_state.get("confirm_delete_single_match")
    if pending_single:
        st.warning(f"⚠️ Weet je zeker dat je deze wedstrijd definitief wilt verwijderen?\n\n`{pending_single['display']}`")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Ja, verwijder wedstrijd definitief", key="confirm_delete_single_btn", type="primary"):
                match_id = pending_single["match_id"]
                display_txt = pending_single["display"]
                st.session_state.pop("confirm_delete_single_match", None)
                with st.spinner("Wedstrijd wordt verwijderd..."):
                    try:
                        success = db.delete_match_with_elo_recalculation(match_id)
                        action_type = "delete_match_with_elo_recalculation"
                    except Exception as e:
                        st.error("Database niet bereikbaar: mogelijk budgetlimiet bereikt.")
                        with st.expander("Toon technische details"):
                            st.code(str(e.details) if hasattr(e, 'details') else str(e))
                        return
                    if success:
                        from utils.utils_beheer_log import log_admin_action
                        log_admin_action(
                            action_type=action_type,
                            user=st.session_state.get("user", "beheerder"),
                            details={"match_id": match_id, "display": display_txt},
                            db=db.db
                        )
                        st.success("Wedstrijd succesvol verwijderd. De ELO-scores worden vanavond om 23:00 uur automatisch herberekend.")
                        time.sleep(1.5)
                        st.rerun()
        with c2:
            if st.button("❌ Annuleren", key="cancel_delete_single_btn"):
                st.session_state.pop("confirm_delete_single_match", None)
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
        match_ids = []
        for match_display in matches_to_delete:
            match_row = matches_display_df[matches_display_df["display"] == match_display]
            if not match_row.empty:
                match_ids.append(match_row.iloc[0]["match_id"])
        if match_ids:
            st.session_state["confirm_delete_multi_matches"] = match_ids

    pending_multi = st.session_state.get("confirm_delete_multi_matches")
    if pending_multi:
        st.warning(f"⚠️ Weet je zeker dat je **{len(pending_multi)} wedstrijden** definitief wilt verwijderen?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button(f"✅ Ja, verwijder {len(pending_multi)} wedstrijden definitief", key="confirm_delete_multi_btn", type="primary"):
                match_ids = list(pending_multi)
                st.session_state.pop("confirm_delete_multi_matches", None)
                with st.spinner(f"Bezig met verwijderen van {len(match_ids)} wedstrijden..."):
                    try:
                        success = db.delete_multiple_matches_with_elo_recalculation(match_ids)
                    except Exception as e:
                        st.error(f"Fout bij verwijderen: {e}")
                        return
                    if success:
                        from utils.utils_beheer_log import log_admin_action
                        log_admin_action(
                            action_type="delete_multiple_matches_with_elo_recalculation",
                            user=st.session_state.get("user", "beheerder"),
                            details={"match_ids": match_ids},
                            db=db.db
                        )
                        st.success(f"{len(match_ids)} wedstrijden succesvol verwijderd. De ELO-scores worden vanavond om 23:00 uur automatisch herberekend.")
                        time.sleep(1.5)
                        st.rerun()
        with c2:
            if st.button("❌ Annuleren", key="cancel_delete_multi_btn"):
                st.session_state.pop("confirm_delete_multi_matches", None)
                st.rerun()

# ---------------------------------------------------------------------------
# Wedstrijd bewerken
# ---------------------------------------------------------------------------
def _render_match_edit(db, matches_df: pd.DataFrame, players_df: pd.DataFrame):
    st.write("**Wedstrijd bewerken**")
    st.info("💡 Wijzigingen worden direct opgeslagen. De ELO-scores worden vanavond om 23:00 uur automatisch herberekend om database-limieten te sparen.")
    
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
        max_idx = max(0, len(player_names) - 1)
        new_thuis_1 = edit_cols[0].selectbox(
            "Thuis 1", player_names,
            index=player_names.index(match_data.get("thuis_1")) if match_data.get("thuis_1") in player_names else 0,
        )
        new_thuis_2 = edit_cols[1].selectbox(
            "Thuis 2", player_names,
            index=player_names.index(match_data.get("thuis_2")) if match_data.get("thuis_2") in player_names else min(1, max_idx),
        )
        new_uit_1 = edit_cols[2].selectbox(
            "Uit 1", player_names,
            index=player_names.index(match_data.get("uit_1")) if match_data.get("uit_1") in player_names else min(2, max_idx),
        )
        new_uit_2 = edit_cols[3].selectbox(
            "Uit 2", player_names,
            index=player_names.index(match_data.get("uit_2")) if match_data.get("uit_2") in player_names else min(3, max_idx),
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
            if (new_klinkers_thuis_1 + new_klinkers_thuis_2) > new_thuis_score:
                st.error("Totaal aantal klinkers van het thuisteam kan niet hoger zijn dan de thuisscore.")
                return
            if (new_klinkers_uit_1 + new_klinkers_uit_2) > new_uit_score:
                st.error("Totaal aantal klinkers van het uitteam kan niet hoger zijn dan de uitscore.")
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
                success = db.update_match_with_elo_recalculation(match_data["match_id"], updated)
                action_type = "update_match_with_elo_recalculation"
                from utils.utils_beheer_log import log_admin_action
                log_admin_action(
                    action_type=action_type,
                    user=st.session_state.get("user", "onbekend"),
                    details={"match_id": match_data["match_id"], "updated": updated},
                    db=db.db
                )
                if success:
                    st.success("Wedstrijd succesvol bijgewerkt. De ELO-scores worden vanavond om 23:00 uur automatisch herberekend.")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error(
                        "Er is een fout opgetreden bij het bijwerken van de wedstrijd."
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
                # Controleer op nieuwe spelers en valideer scores (nog NIET toevoegen voor bevestiging!)
                current_players = set(players_df["speler_naam"].tolist()) if not players_df.empty else set()
                new_players = set()
                for row_idx in range(len(matches_upload_df)):
                    row = matches_upload_df.iloc[row_idx]
                    p = [str(row["thuis_1"]).strip(), str(row["thuis_2"]).strip(), str(row["uit_1"]).strip(), str(row["uit_2"]).strip()]
                    for player in p:
                        if player and player not in current_players:
                            new_players.add(player)
                    t_score = row["thuis_score"]
                    u_score = row["uit_score"]
                    if not (
                        (t_score == 10 and 0 <= u_score <= 9)
                        or (u_score == 10 and 0 <= t_score <= 9)
                    ):
                        validation_errors.append(f"Rij {row_idx+1}: Ongeldige score combinatie {t_score}-{u_score}")
                    if len(set(p)) != 4:
                        validation_errors.append(f"Rij {row_idx+1}: Niet alle spelers zijn uniek")
                    try:
                        kt1 = int(float(row.get("klinkers_thuis_1", 0) or 0))
                        kt2 = int(float(row.get("klinkers_thuis_2", 0) or 0))
                        ku1 = int(float(row.get("klinkers_uit_1", 0) or 0))
                        ku2 = int(float(row.get("klinkers_uit_2", 0) or 0))
                        if min(kt1, kt2, ku1, ku2) < 0:
                            validation_errors.append(f"Rij {row_idx+1}: Negatief aantal klinkers is niet toegestaan")
                        elif (kt1 + kt2) > int(t_score) or (ku1 + ku2) > int(u_score):
                            validation_errors.append(f"Rij {row_idx+1}: Aantal klinkers is hoger dan teamscore")
                    except (ValueError, TypeError):
                        validation_errors.append(f"Rij {row_idx+1}: Ongeldige klinkerwaarde")
                if validation_errors:
                    st.error("❌ Validatie fouten gevonden:")
                    for err in validation_errors[:10]:
                        st.error(f"• {err}")
                    if len(validation_errors) > 10:
                        st.error(f"• ... en {len(validation_errors) - 10} meer fouten")
                    return
                st.success("✅ Alle data is geldig!")
                if new_players:
                    st.info(f"👤 Nieuwe spelers die bij import worden aangemaakt ({len(new_players)}): {', '.join(sorted(new_players))}")
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
                        for player in sorted(new_players):
                            db.add_player(player, 1000)
                        added, duplicates = db.import_matches(matches_upload_df.to_dict("records"))
                        if elo_recalc_option.startswith("🔄") and added > 0:
                            from utils.utils_seizoen import get_current_season
                            curr_s = get_current_season(db.get_seasons())
                            if curr_s is not None:
                                db.recalculate_elos_for_season(curr_s['start_datum'], curr_s['eind_datum'])
                            else:
                                db.reset_all_elos()
                        st.success(f"🎉 Import voltooid! {added} toegevoegd, {duplicates} duplicaten genegeerd.")
                        if elo_recalc_option.startswith("🔄") and added > 0:
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
    # Seizoenen upload-tab: leg uit hoe de automatische Prinsjesdag / 15-maart seizoenen werken
    with upload_subtab3:
        st.subheader("📅 Seizoensindeling (Automatisch)")
        st.info(
            "💡 **Geen handmatige upload nodig:** Seizoenen worden in deze app volledig automatisch "
            "berekend op basis van de **ADR Controlejaar-systematiek** en de datums van de gespeelde wedstrijden."
        )
        st.markdown(
            """
            **Hoe werkt de automatische seizoensindeling?**
            - **☀️ Zomerseizoen (`CJ <Jaar> Zomer`):** Loopt van **15 maart (00:00 uur)** tot en met **Prinsjesdag** (de derde dinsdag van september, 23:59:59 uur).
            - **❄️ Winterseizoen (`CJ <Jaar> Winter`):** Loopt vanaf de nacht **na Prinsjesdag (woensdag 00:00 uur)** tot en met **14 maart van het volgende jaar (23:59:59 uur)**.
            - **🔄 Automatische ELO-reset:** Zodra de eerste wedstrijd van een nieuw seizoen wordt geregistreerd, worden alle ELO-scores automatisch gereset naar **1000 punten**.
            """
        )

# ---------------------------------------------------------------------------
# ELO Integriteitscheck & Database Inspectie
# ---------------------------------------------------------------------------
def _render_elo_audit_panel(db, matches_df: pd.DataFrame):
    """Toont een read-only ELO-integriteitscheck en opties om een seizoen te herberekenen."""
    with st.expander("🧮 ELO-Integriteitscheck & Seizoen Herberekening", expanded=False):
        st.caption(
            "Controleer per seizoen (read-only) of de opgeslagen ELO-scores overeenkomen met een schone "
            "berekening vanaf 1000 punten en herbereken het seizoen indien nodig."
        )
        seasons_df = db.get_seasons()
        if seasons_df is None or seasons_df.empty:
            st.info("Geen seizoenen gevonden.")
            return

        season_names = seasons_df["seizoen_naam"].tolist()
        selected_season_name = st.selectbox(
            "Selecteer seizoen voor controle",
            options=season_names,
            index=len(season_names) - 1,
            key="admin_elo_audit_season",
        )
        s_row = seasons_df[seasons_df["seizoen_naam"] == selected_season_name].iloc[0]
        s_start = s_row.get("start_datum") or s_row.get("startdatum")
        s_end = s_row.get("eind_datum") or s_row.get("einddatum")

        if st.button("🔍 Controleer ELO-berekening", key="btn_run_elo_audit"):
            with st.spinner(f"ELO-integriteit van {selected_season_name} controleren..."):
                audit_res = db.audit_season_elo(s_start, s_end, matches_df=matches_df)
                st.session_state["elo_audit_result"] = {
                    "season": selected_season_name,
                    "result": audit_res,
                }

        cached_audit = st.session_state.get("elo_audit_result")
        if cached_audit and cached_audit.get("season") == selected_season_name:
            res = cached_audit["result"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Wedstrijden", res["match_count"])
            c2.metric("Ontbrekende ELO-logs", res["missing_elo_logs"])
            c3.metric("Afwijkende log-entries", res["mismatched_logs_count"])
            c4.metric("Max. speler-verschil", f"{res['max_player_diff']:.2f}")

            diff_df = res.get("player_diffs")
            if diff_df is not None and not diff_df.empty:
                st.dataframe(diff_df, hide_index=True, width='stretch')

            if res["missing_elo_logs"] == 0 and res["mismatched_logs_count"] == 0 and res["max_player_diff"] <= 0.5:
                st.success("✅ Alle ELO-ratings in dit seizoen kloppen exact met de herberekening vanaf 1000.")
            else:
                st.warning(
                    "⚠️ Er zijn afwijkingen gevonden t.o.v. een schone seizoensberekening vanaf 1000. "
                    "Je kunt dit seizoen inplannen voor vanavond 23:00 uur of direct herberekenen."
                )

        col_sched, col_now = st.columns(2)
        with col_sched:
            if st.button("🕒 Plan herberekening voor 23:00 uur", key="btn_schedule_season_recalc"):
                st.session_state["confirm_schedule_season_recalc"] = selected_season_name
        with col_now:
            if st.button("⚡ Herbereken seizoen nu (direct)", key="btn_direct_season_recalc"):
                st.session_state["confirm_direct_season_recalc"] = selected_season_name

        if st.session_state.get("confirm_schedule_season_recalc") == selected_season_name:
            st.info(f"Weet je zeker dat je **{selected_season_name}** wilt inplannen voor ELO-herberekening om 23:00 uur?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Ja, plan in", key="confirm_schedule_recalc_yes", type="primary"):
                    db.set_recalc_needed_flag(s_start, s_end, selected_season_name, s_start)
                    from utils.utils_beheer_log import log_admin_action
                    log_admin_action(
                        action_type="schedule_season_elo_recalc",
                        user=st.session_state.get("user", "beheerder"),
                        details={"season_naam": selected_season_name},
                        db=db.db,
                    )
                    st.session_state.pop("confirm_schedule_season_recalc", None)
                    st.success(f"Herberekening voor '{selected_season_name}' ingepland voor 23:00 uur.")
                    time.sleep(1)
                    st.rerun()
            with c2:
                if st.button("❌ Annuleren", key="confirm_schedule_recalc_no"):
                    st.session_state.pop("confirm_schedule_season_recalc", None)
                    st.rerun()

        if st.session_state.get("confirm_direct_season_recalc") == selected_season_name:
            st.warning(
                f"⚠️ Let op: directe herberekening van **{selected_season_name}** overschrijft alle ELO-logs van dit seizoen "
                "(en werkt speler-ratings bij als dit het nieuwste seizoen is)."
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Ja, herbereken direct", key="confirm_direct_recalc_yes", type="primary"):
                    with st.spinner(f"Bezig met herberekenen van {selected_season_name}..."):
                        ok = db.recalculate_elos_for_season(s_start, s_end)
                    if ok:
                        from utils.utils_beheer_log import log_admin_action
                        log_admin_action(
                            action_type="recalculate_elos_for_season",
                            user=st.session_state.get("user", "beheerder"),
                            details={"season_naam": selected_season_name},
                            db=db.db,
                        )
                        st.session_state.pop("confirm_direct_season_recalc", None)
                        st.session_state.pop("elo_audit_result", None)
                        st.success(f"Seizoen '{selected_season_name}' succesvol herberekend!")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("Herberekening mislukt.")
            with c2:
                if st.button("❌ Annuleren", key="confirm_direct_recalc_no"):
                    st.session_state.pop("confirm_direct_season_recalc", None)
                    st.rerun()


def _render_schema_inspection_panel(db):
    """Toont een on-demand vergelijking tussen verwacht schema en Firestore steekproef."""
    with st.expander("🔎 Database Inspectie & Schema", expanded=False):
        st.caption("Bekijk welke collecties en velden in Firestore aanwezig zijn en vergelijk met wat de app verwacht.")
        if st.button("Analyseer Firestore schema", key="btn_analyze_schema"):
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
                            st.dataframe(pd.DataFrame(act["examples"]), width='stretch')
                        st.markdown("---")
                except Exception as e:
                    st.error(f"Schema inspectie mislukt: {e}")

# ---------------------------------------------------------------------------
# Hoofd entry
# ---------------------------------------------------------------------------
def render_admin_tab(db, players_df: pd.DataFrame, matches_df: pd.DataFrame):
    """Rendert de volledige beheer tab. Houdt de code in app.py minimaal."""
    st.header("⚙️ Beheer")
    st.caption(
        "Beveiligde beheeromgeving voor het synchroniseren van de Google Sheet back-up, "
        "het corrigeren of verwijderen van wedstrijden en spelers, en het importeren van CSV-bestanden."
    )
    if not _ensure_authentication():
        return

    # --- Synchronisatie Sectie ---
    st.subheader("🔄 Synchronisatie")
    st.info("Synchroniseer data tussen de Google Sheet backup en de Firestore database. Gebruik dit om offline ingevoerde data te herstellen.")
    if st.button("🚀 Start Synchronisatie"):
        with st.spinner("Bezig met synchroniseren... dit kan even duren bij veel data."):
            try:
                db.reconcile_data_sources(force=True)
                st.success("Synchronisatie voltooid!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Synchronisatie mislukt: {e}")

    _render_elo_audit_panel(db, matches_df)
    _render_schema_inspection_panel(db)
    st.divider()

    # Hoofd tabs in beheer
    tab_verwijderen, tab_bewerken, tab_upload = st.tabs([
        "🗑️ Verwijderen", "✏️ Bewerken", "📁 Upload"])

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
                    st.session_state["confirm_delete_player_admin"] = (pid, player_to_delete)
                else:
                    st.error("Kon de speler ID niet vinden.")

            pending_p = st.session_state.get("confirm_delete_player_admin")
            if pending_p and pending_p[1] == player_to_delete:
                pid, pname = pending_p
                st.warning(f"⚠️ Weet je zeker dat je **{pname}** en alle bijbehorende ELO-historie definitief wilt verwijderen?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button(f"✅ Ja, verwijder {pname} definitief", key="confirm_delete_player_admin_yes", type="primary"):
                        st.session_state.pop("confirm_delete_player_admin", None)
                        with st.spinner(f"Bezig met verwijderen van {pname}..."):
                            if db.delete_player_by_id(pid):
                                from utils.utils_beheer_log import log_admin_action
                                log_admin_action(
                                    action_type="delete_player",
                                    user=st.session_state.get("user", "beheerder"),
                                    details={"player_id": pid, "speler_naam": pname},
                                    db=db.db,
                                )
                                st.success(f"{pname} en alle bijbehorende data is verwijderd.")
                                st.rerun()
                            else:
                                st.error("Kon speler niet verwijderen.")
                with c2:
                    if st.button("❌ Annuleren", key="confirm_delete_player_admin_no"):
                        st.session_state.pop("confirm_delete_player_admin", None)
                        st.rerun()

    with tab_bewerken:
        st.header("✏️ Bewerken")
        _render_match_edit(db, matches_df, players_df)

        st.markdown("---")
        st.subheader("Spelerslijst namen corrigeren")
        spelers_df = players_df.copy()
        if spelers_df.empty:
            st.info("Geen spelers beschikbaar om te bewerken.")
        else:
            st.dataframe(spelers_df[['speler_naam', 'rating']], width='stretch')

            st.info("Hier kun je namen corrigeren. Voor het samenvoegen van dubbele spelers (merge), gebruik het admin-script 'admin/merge_players.py'.")

            speler_select = st.selectbox("Selecteer speler om naam aan te passen", sorted(spelers_df['speler_naam'].tolist()))
            nieuwe_naam_raw = st.text_input("Nieuwe naam", value=speler_select)
            if st.button("Pas naam aan"):
                ok, msg = db.rename_player(speler_select, nieuwe_naam_raw)
                if ok:
                    from utils.utils_beheer_log import log_admin_action
                    log_admin_action(
                        action_type="rename_player",
                        user=st.session_state.get("user", "beheerder"),
                        details={"old_name": speler_select, "new_name": nieuwe_naam_raw.strip()},
                        db=db.db
                    )
                    st.success(f"{msg} Alle data (inclusief back-up) is bijgewerkt.")
                    st.rerun()
                else:
                    st.error(msg)

    with tab_upload:
        st.header("📁 Upload")
        if matches_df is None or matches_df.empty:
            st.info("💡 Geen wedstrijden gevonden. Upload historische data om te beginnen!")
        _render_uploads(db, players_df)
