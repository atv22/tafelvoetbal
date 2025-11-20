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
    auto_recalc_delete = elo_delete_option.startswith("🔄")
    if not auto_recalc_delete:
        st.warning(
            "⚠️ **Let op:** Verwijderen zonder ELO herberekening kan leiden tot inconsistenties in de ratings."
        )

    matches_display_df = matches_df.copy()
    matches_display_df["display"] = matches_display_df.apply(
        lambda row: f"{pd.to_datetime(row.get('timestamp')).strftime('%d-%m-%Y %H:%M') if row.get('timestamp') else 'Geen tijd'} - "
        f"{row.get('thuis_1', 'N/A')}/{row.get('thuis_2', 'N/A')} vs {row.get('uit_1', 'N/A')}/{row.get('uit_2', 'N/A')}: "
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
                if auto_recalc_delete:
                    success = db.delete_match_with_elo_recalculation(match_id)
                    action_type = "delete_match_with_elo_recalculation"
                else:
                    success = db.delete_match_by_id(match_id)
                    action_type = "delete_match"
                if success:
                    from utils_beheer_log import log_admin_action
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
                    if db.delete_match_by_id(match_id):
                        success_count += 1
            if auto_recalc_delete and success_count > 0:
                with st.spinner("ELO scores worden herberekend..."):
                    db.reset_all_elos()
            if success_count == len(matches_to_delete):
                if auto_recalc_delete:
                    st.success(
                        f"Alle {success_count} wedstrijden succesvol verwijderd en ELO scores volledig herberekend!"
                    )
                else:
                    st.success(f"Alle {success_count} wedstrijden succesvol verwijderd.")
                    st.warning("⚠️ ELO scores zijn niet herberekend.")
            else:
                st.warning(
                    f"{success_count} van de {len(matches_to_delete)} wedstrijden verwijderd."
                )
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
        help="Automatische herberekening zorgt voor correcte ELO scores maar duurt langer.",
    )
    auto_recalculate = elo_option.startswith("🔄")
    if not auto_recalculate:
        st.warning(
            "⚠️ **Let op:** Het bewerken van wedstrijden zonder ELO herberekening kan leiden tot inconsistenties in de ratings."
        )

    if players_df.empty:
        st.info("Geen spelers beschikbaar om wedstrijden mee te bewerken.")
        return

    player_names = sorted(players_df["speler_naam"].tolist())
    matches_display_df = matches_df.copy()
    matches_display_df["display"] = matches_display_df.apply(
        lambda row: f"{pd.to_datetime(row.get('timestamp')).strftime('%d-%m-%Y %H:%M') if row.get('timestamp') else 'Geen tijd'} - "
        f"{row.get('thuis_1', 'N/A')}/{row.get('thuis_2', 'N/A')} vs {row.get('uit_1', 'N/A')}/{row.get('uit_2', 'N/A')}: "
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
                from utils_beheer_log import log_admin_action
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
            **📋 Vereist CSV formaat voor wedstrijden:** (zie originele documentatie in app)
            Minimaal vereiste kolommen: thuis_1, thuis_2, uit_1, uit_2, thuis_score, uit_score.
            Optioneel: klinkers_* kolommen en timestamp.
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
                matches_upload_df = pd.read_csv(uploaded_matches)
                st.dataframe(matches_upload_df.head(10), width='stretch')
                required_columns = [
                    "thuis_1",
                    "thuis_2",
                    "uit_1",
                    "uit_2",
                    "thuis_score",
                    "uit_score",
                ]
                missing = [c for c in required_columns if c not in matches_upload_df.columns]
                if missing:
                    st.error(
                        f"❌ Ontbrekende verplichte kolommen: {', '.join(missing)}"
                    )
                    return
                for opt in [
                    "klinkers_thuis_1",
                    "klinkers_thuis_2",
                    "klinkers_uit_1",
                    "klinkers_uit_2",
                ]:
                    if opt not in matches_upload_df.columns:
                        matches_upload_df[opt] = 0
                if "timestamp" not in matches_upload_df.columns:
                    st.info("📅 Geen timestamp kolom gevonden - huidige tijd wordt gebruikt")
                    matches_upload_df["timestamp"] = pd.Timestamp.now()
                else:
                    for idx in range(len(matches_upload_df)):
                        val = matches_upload_df.iloc[idx]["timestamp"]
                        if pd.isna(val) or val == "":
                            matches_upload_df.loc[idx, "timestamp"] = pd.Timestamp.now()
                        else:
                            try:
                                ts = str(val).strip()
                                if len(ts) == 10 and ts.count("-") == 2:
                                    parsed = pd.to_datetime(ts + " 12:00:00")
                                else:
                                    parsed = pd.to_datetime(ts)
                                matches_upload_df.loc[idx, "timestamp"] = parsed
                            except Exception:
                                matches_upload_df.loc[idx, "timestamp"] = pd.Timestamp.now()
                validation_errors = []
                current_players = (
                    players_df["speler_naam"].tolist() if not players_df.empty else []
                )
                for row_idx in range(len(matches_upload_df)):
                    row = matches_upload_df.iloc[row_idx]
                    p = [row["thuis_1"], row["thuis_2"], row["uit_1"], row["uit_2"]]
                    for player in p:
                        if player not in current_players:
                            validation_errors.append(
                                f"Rij {row_idx+1}: Speler '{player}' bestaat niet"
                            )
                    t_score = row["thuis_score"]
                    u_score = row["uit_score"]
                    if not (
                        (t_score == 10 and 0 <= u_score <= 9)
                        or (u_score == 10 and 0 <= t_score <= 9)
                    ):
                        validation_errors.append(
                            f"Rij {row_idx+1}: Ongeldige score combinatie {t_score}-{u_score}"
                        )
                    if len(set(p)) != 4:
                        validation_errors.append(
                            f"Rij {row_idx+1}: Niet alle spelers zijn uniek"
                        )
                if validation_errors:
                    st.error("❌ Validatie fouten gevonden:")
                    for err in validation_errors[:10]:
                        st.error(f"• {err}")
                    if len(validation_errors) > 10:
                        st.error(
                            f"• ... en {len(validation_errors) - 10} meer fouten"
                        )
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
                st.info(
                    f"📊 Upload samenvatting: {len(matches_upload_df)} wedstrijden klaar voor import"
                )
                if st.button("🚀 Import Wedstrijden", type="primary"):
                    with st.spinner(
                        f"Bezig met importeren van {len(matches_upload_df)} wedstrijden..."
                    ):
                        added, duplicates = db.import_matches(
                            matches_upload_df.to_dict("records")
                        )
                        if elo_recalc_option.startswith("🔄") and added > 0:
                            db.reset_all_elos()
                        st.success(
                            f"🎉 Import voltooid! {added} toegevoegd, {duplicates} duplicaten genegeerd."
                        )
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
                    f"📊 Upload samenvatting: {len(players_upload_df)} spelers klaar voor import"
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
    # Seizoenen
    with upload_subtab3:
        st.subheader("Seizoengegevens Uploaden")
        uploaded_seasons = st.file_uploader(
            "📁 Upload seizoenen CSV bestand",
            type=["csv"],
            key="seasons_upload_main",
            help="Upload seizoensdata",
        )
        if uploaded_seasons is not None:
            try:
                seasons_upload_df = pd.read_csv(uploaded_seasons)
                st.dataframe(seasons_upload_df.head(10), width='stretch')
                required = ["startdatum", "einddatum"]
                missing = [c for c in required if c not in seasons_upload_df.columns]
                if missing:
                    st.error(f"❌ Ontbrekende verplichte kolommen: {', '.join(missing)}")
                    return
                errors = []
                for idx in range(len(seasons_upload_df)):
                    row = seasons_upload_df.iloc[idx]
                    try:
                        start = pd.to_datetime(row["startdatum"])
                        end = pd.to_datetime(row["einddatum"])
                        if end <= start:
                            errors.append(
                                f"Rij {idx+1}: Einddatum moet na startdatum liggen"
                            )
                    except Exception:
                        errors.append(
                            f"Rij {idx+1}: Ongeldig datum formaat"
                        )
                if errors:
                    st.error("❌ Validatie fouten:")
                    for err in errors[:5]:
                        st.error(f"• {err}")
                    return
                st.success("✅ Alle seizoengegevens zijn geldig!")
                st.info(
                    f"📊 Upload samenvatting: {len(seasons_upload_df)} seizoenen klaar voor import"
                )
                if st.button("🚀 Import Seizoenen", type="primary"):
                    with st.spinner(
                        f"Bezig met importeren van {len(seasons_upload_df)} seizoenen..."
                    ):
                        added, duplicates = db.import_seasons(
                            seasons_upload_df.to_dict("records")
                        )
                        st.success(
                            f"🎉 Import voltooid! {added} toegevoegd, {duplicates} duplicaten genegeerd."
                        )
                        time.sleep(1.5)
                        st.rerun()
            except Exception as e:
                st.error(f"❌ Fout bij verwerken CSV: {e}")

# ---------------------------------------------------------------------------
# Systeem beheer
# ---------------------------------------------------------------------------
def _render_system_management(db, players_df: pd.DataFrame):
    st.header("⚙️ Systeem Beheer")
    st.subheader("ELO Rating Beheer")
    st.write("**Complete ELO Reset & Herberekening**")
    st.info("💡 Reset alle ELO scores naar 1000 en herberekent ze op basis van alle wedstrijden.")
    if st.button("🔄 Reset en herbereken alle ELO scores", type="secondary"):
        with st.spinner("Alle ELO scores worden gereset en herberekend... Dit kan even duren."):
            success = db.reset_all_elos()
            from utils_beheer_log import log_admin_action
            log_admin_action(
                action_type="reset_all_elos",
                user=st.session_state.get("user", "onbekend"),
                details={"action": "reset_all_elos"},
                db=db.db
            )
            if success:
                st.success("✅ Alle ELO scores succesvol gereset en herberekend!")
                st.balloons()
                time.sleep(1.5)
                st.rerun()
            else:
                st.error("❌ Fout bij resetten van de ELO scores.")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("Herbereken ELO voor een seizoen")
    seasons_df = db.get_seasons()
    if seasons_df.empty:
        st.info("Geen seizoenen gevonden. Voeg eerst wedstrijden toe.")
    else:
        season_options = []
        for idx, season in seasons_df.iterrows():
            season_str = f"{season['startdatum'].strftime('%Y-%m-%d')} tot {season['einddatum'].strftime('%Y-%m-%d')}"
            season_options.append((season_str, idx, season['startdatum'], season['einddatum']))
        season_names = [o[0] for o in season_options]
        selected = st.selectbox("Selecteer een seizoen voor ELO herberekening", options=season_names)
        if st.button("Herbereken ELO voor dit seizoen", type="primary"):
            # Vind de juiste start/einddatum
            selected_season = next(o for o in season_options if o[0] == selected)
            start_date = selected_season[2]
            end_date = selected_season[3]
            with st.spinner("ELO scores worden herberekend voor het gekozen seizoen... Dit kan even duren."):
                success = db.recalculate_elos_for_season(start_date, end_date)
                from utils_beheer_log import log_admin_action
                log_admin_action(
                    action_type="recalculate_elos_for_season",
                    user=st.session_state.get("user", "onbekend"),
                    details={"action": "recalculate_elos_for_season", "seizoen": selected},
                    db=db.db
                )
                if success:
                    st.success(f"✅ ELO scores succesvol herberekend voor seizoen: {selected}")
                    st.balloons()
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error(f"❌ Fout bij herberekenen van de ELO scores voor seizoen: {selected}")
    st.markdown("<hr>", unsafe_allow_html=True)
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
    st.subheader("Seizoen Verwijderen")
    seasons_df = db.get_seasons()
    if seasons_df.empty:
        st.info("Geen seizoenen om te beheren.")
    else:
        season_options = []
        for _, season in seasons_df.iterrows():
            season_str = f"{season['startdatum'].strftime('%Y-%m-%d')} tot {season['einddatum'].strftime('%Y-%m-%d')}"
            season_options.append((season_str, season.name))
        if season_options:
            season_names = [o[0] for o in season_options]
            selected = st.selectbox(
                "Selecteer een seizoen om te verwijderen", options=season_names
            )
            if st.button(f"Verwijder seizoen: {selected}"):
                season_index = next(o[1] for o in season_options if o[0] == selected)
                season_doc_id = seasons_df.iloc[season_index].name
                with st.spinner("Bezig met verwijderen van seizoen..."):
                    if db.delete_season_by_id(season_doc_id):
                        st.success(f"Seizoen {selected} is verwijderd.")
                        st.rerun()
                    else:
                        st.error("Kon het seizoen niet verwijderen.")
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("Overige Database Cleanup")
    if st.button("🗑️ Verwijder alle 'Requests'", type="secondary"):
        with st.spinner("Alle requests worden verwijderd..."):
            if db.clear_collection("requests"):
                st.success("Alle requests zijn succesvol verwijderd.")
                st.rerun()
            else:
                st.error("Kon de requests niet verwijderen.")

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
    tab_elo, tab_verwijderen, tab_bewerken, tab_upload, tab_inspectie = st.tabs([
        "⚡ ELO beheer", "🗑️ Verwijderen", "✏️ Bewerken", "📁 Upload", "🔍 Inspectie"])

    with tab_elo:
        st.header("⚡ ELO Beheer")
        st.subheader("🗑️ Hele ELO Geschiedenis wissen")
        if st.button("Wis alle ELO geschiedenis"):
            from firestore_service import delete_all_elo_history
            deleted_count = delete_all_elo_history()
            if deleted_count > 0:
                st.success(f"Alle ELO entries ({deleted_count}) zijn verwijderd.")
            else:
                st.info("Er was geen ELO geschiedenis om te verwijderen.")

        st.subheader("🗑️ ELO Geschiedenis verwijderen voor een specifieke datum")
        target_date = st.date_input("Kies een datum om ELO geschiedenis te verwijderen:", value=datetime.date.today(), key="elo_date_input")
        if st.button("Verwijder ELO geschiedenis voor deze datum", key="delete_elo_date"):
            from firestore_service import delete_elo_history_for_date
            deleted_count = delete_elo_history_for_date(target_date)
            if deleted_count > 0:
                st.success(f"{deleted_count} ELO entries verwijderd voor {target_date}.")
            else:
                st.info(f"Geen ELO entries gevonden voor {target_date}.")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("🔄 Complete ELO Reset & Herberekening")
        st.info("💡 Reset alle ELO scores naar 1000 en herberekent ze op basis van alle wedstrijden.")
        if st.button("🔄 Reset en herbereken alle ELO scores", key="reset_all_elos"):
            with st.spinner("Alle ELO scores worden gereset en herberekend... Dit kan even duren."):
                success = db.reset_all_elos()
                from utils_beheer_log import log_admin_action
                log_admin_action(
                    action_type="reset_all_elos",
                    user=st.session_state.get("user", "onbekend"),
                    details={"action": "reset_all_elos"},
                    db=db.db
                )
                if success:
                    st.success("✅ Alle ELO scores succesvol gereset en herberekend!")
                    st.balloons()
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error("❌ Fout bij resetten van de ELO scores.")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("🔄 Herbereken ELO voor een seizoen")
        seasons_df = db.get_seasons()
        if seasons_df.empty:
            st.info("Geen seizoenen gevonden. Voeg eerst wedstrijden toe.")
        else:
            season_options = []
            for idx, season in seasons_df.iterrows():
                season_str = f"{season['startdatum'].strftime('%Y-%m-%d')} tot {season['einddatum'].strftime('%Y-%m-%d')}"
                season_options.append((season_str, idx, season['startdatum'], season['einddatum']))
            season_names = [o[0] for o in season_options]
            selected = st.selectbox("Selecteer een seizoen voor ELO herberekening", options=season_names)
            if st.button("Herbereken ELO voor dit seizoen", key="recalc_elo_season"):
                selected_season = next(o for o in season_options if o[0] == selected)
                start_date = selected_season[2]
                end_date = selected_season[3]
                with st.spinner("ELO scores worden herberekend voor het gekozen seizoen... Dit kan even duren."):
                    success = db.recalculate_elos_for_season(start_date, end_date)
                    from utils_beheer_log import log_admin_action
                    log_admin_action(
                        action_type="recalculate_elos_for_season",
                        user=st.session_state.get("user", "onbekend"),
                        details={"action": "recalculate_elos_for_season", "seizoen": selected},
                        db=db.db
                    )
                    if success:
                        st.success(f"✅ ELO scores succesvol herberekend voor seizoen: {selected}")
                        st.balloons()
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error(f"❌ Fout bij herberekenen van de ELO scores voor seizoen: {selected}")

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

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("🗑️ Seizoen Verwijderen")
        seasons_df = db.get_seasons()
        if seasons_df.empty:
            st.info("Geen seizoenen om te beheren.")
        else:
            season_options = []
            for _, season in seasons_df.iterrows():
                season_str = f"{season['startdatum'].strftime('%Y-%m-%d')} tot {season['einddatum'].strftime('%Y-%m-%d')}"
                season_options.append((season_str, season.name))
            if season_options:
                season_names = [o[0] for o in season_options]
                selected = st.selectbox(
                    "Selecteer een seizoen om te verwijderen", options=season_names
                )
                if st.button(f"Verwijder seizoen: {selected}", key="delete_season"):
                    season_index = next(o[1] for o in season_options if o[0] == selected)
                    season_doc_id = seasons_df.iloc[season_index].name
                    with st.spinner("Bezig met verwijderen van seizoen..."):
                        if db.delete_season_by_id(season_doc_id):
                            st.success(f"Seizoen {selected} is verwijderd.")
                            st.rerun()
                        else:
                            st.error("Kon het seizoen niet verwijderen.")

    with tab_bewerken:
        st.header("✏️ Bewerken")
        _render_match_edit(db, matches_df, players_df)

    with tab_upload:
        st.header("📁 Upload")
        if matches_df.empty:
            st.info("Geen wedstrijden om te beheren.")
            st.subheader("📁 Historische Data Upload")
            st.info("💡 Geen wedstrijden gevonden. Upload historische data om te beginnen!")
        _render_uploads(db, players_df)

    with tab_inspectie:
        st.header("🔍 Inspectie")
        st.subheader("🧹 Overige Database Cleanup")
        if st.button("🗑️ Verwijder alle 'Requests'", type="secondary"):
            with st.spinner("Alle requests worden verwijderd..."):
                if db.clear_collection("requests"):
                    st.success("Alle requests zijn succesvol verwijderd.")
                    st.rerun()
                else:
                    st.error("Kon de requests niet verwijderen.")

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
