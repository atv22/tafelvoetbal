# --- HULPFUNCTIE: Timestamp normalisatie ---
def normalize_timestamp_series(ts_series):
    """
    Zet een pandas Series met timestamps om naar tz-naive UTC (indien mogelijk).
    Werkt veilig voor zowel tz-aware als tz-naive series.
    """
    import pandas as pd
    if not pd.api.types.is_datetime64_any_dtype(ts_series):
        return ts_series
    try:
        # Als tz-aware, eerst naar UTC, dan tz-naive
        if hasattr(ts_series.dt, 'tz') and ts_series.dt.tz is not None:
            return ts_series.dt.tz_convert('UTC').dt.tz_localize(None)
        else:
            # Als al tz-naive, return as-is (of forceer zonder exceptie)
            return ts_series.dt.tz_localize(None)
    except (TypeError, ValueError):
        # Als al tz-naive, return as-is
        return ts_series

# Verwijder alle ELO geschiedenis
def delete_all_elo_history():
    """
    Verwijdert alle ELO entries uit Firestore.
    """
    batch = db.batch()
    batch_counter = 0
    elo_docs = elo_ref.stream()
    deleted_count = 0
    for doc in elo_docs:
        batch.delete(doc.reference)
        batch_counter += 1
        deleted_count += 1
        if batch_counter >= 400:
            batch.commit()
            batch = db.batch()
            batch_counter = 0
    if batch_counter > 0:
        batch.commit()
    st.cache_data.clear()
    return deleted_count
# Verwijder ELO entries voor een specifieke datum
def delete_elo_history_for_date(target_date):
    """
    Verwijdert alle ELO entries uit Firestore voor een specifieke datum (YYYY-MM-DD).
    target_date: datetime.date of string 'YYYY-MM-DD'
    """
    import pandas as pd
    from google.cloud.firestore_v1.base_query import FieldFilter
    if isinstance(target_date, str):
        target_date = pd.to_datetime(target_date).date()
    batch = db.batch()
    batch_counter = 0
    # Zoek alle ELO entries op de opgegeven datum
    elo_docs = elo_ref.where(filter=FieldFilter('timestamp', '>=', pd.Timestamp(target_date))).where(filter=FieldFilter('timestamp', '<=', pd.Timestamp(target_date))).stream()
    deleted_count = 0
    for doc in elo_docs:
        batch.delete(doc.reference)
        batch_counter += 1
        deleted_count += 1
        if batch_counter >= 400:
            batch.commit()
            batch = db.batch()
            batch_counter = 0
    if batch_counter > 0:
        batch.commit()
    st.cache_data.clear()
    return deleted_count
def recalculate_elos_for_season(start_date, end_date):
    """
    Herberekent alle ELO scores vanaf het begin van een gekozen seizoen, op basis van de gespeelde wedstrijden in dat seizoen.
    start_date en end_date moeten datetime.date of pandas.Timestamp zijn.
    """
    try:
        from utils_new_elo import calculate_new_elo
        # Haal ALLE wedstrijden op, gesorteerd op timestamp
        all_matches_docs = matches_ref.order_by("timestamp", direction=google.cloud.firestore.Query.ASCENDING).stream()
        all_matches = []
        for doc in all_matches_docs:
            match_data = doc.to_dict()
            match_data['match_id'] = doc.id
            all_matches.append(match_data)

        if not all_matches:
            print("[DEBUG] Geen wedstrijden gevonden.")
            return True

        # Haal alle spelers op
        players_df = get_players()
        if players_df.empty:
            print("[DEBUG] Geen spelers gevonden.")
            return True

        # Zorg dat start_date en end_date altijd datetime.date zijn
        if isinstance(start_date, pd.Timestamp):
            start_date = start_date.date()
        if isinstance(end_date, pd.Timestamp):
            end_date = end_date.date()

        matches_before_season = []
        matches_in_season = []
        for match in all_matches:
            ts = match.get('timestamp')
            match_ts = pd.to_datetime(ts) if not isinstance(ts, pd.Timestamp) else ts
            match_date = match_ts.date()
            if match_date < start_date:
                matches_before_season.append(match)
            elif start_date <= match_date <= end_date:
                matches_in_season.append(match)

        print(f"[DEBUG] Wedstrijden vóór seizoen: {len(matches_before_season)}")
        print(f"[DEBUG] Wedstrijden in seizoen: {len(matches_in_season)}")

        # 1. Bereken ELO's tot aan het begin van het seizoen
        player_elos = {player['speler_naam']: 1000 for _, player in players_df.iterrows()}
        for match in matches_before_season:
            match_dict = {
                "Thuis_1": match.get('thuis_1'),
                "Thuis_2": match.get('thuis_2'),
                "Uit_1": match.get('uit_1'),
                "Uit_2": match.get('uit_2'),
                "Thuis_score": int(match.get('thuis_score', 0)),
                "Uit_score": int(match.get('uit_score', 0))
            }
            all_ELO_ratings = {}
            for player in [match_dict["Thuis_1"], match_dict["Thuis_2"], match_dict["Uit_1"], match_dict["Uit_2"]]:
                all_ELO_ratings[player] = [player_elos.get(player, 1000)]
            new_elo_df = calculate_new_elo(match_dict, all_ELO_ratings)
            for _, row in new_elo_df.iterrows():
                player_elos[row["Speler"]] = row["ELO"]

        print(f"[DEBUG] Start-ELO's per speler aan begin seizoen:")
        for speler, elo in player_elos.items():
            print(f"  {speler}: {elo}")

        # 2. Verwijder bestaande ELO entries in het seizoen
        batch = db.batch()
        batch_counter = 0
        elo_docs = elo_ref.where(filter=FieldFilter('timestamp', '>=', pd.Timestamp(start_date))).where(filter=FieldFilter('timestamp', '<=', pd.Timestamp(end_date))).stream()
        for doc in elo_docs:
            batch.delete(doc.reference)
            batch_counter += 1
        if batch_counter > 0:
            batch.commit()
            batch = db.batch()
            batch_counter = 0

        # 3. Bereken ELO's voor alle wedstrijden in het seizoen, beginnend bij de juiste startwaarden
        for i, match in enumerate(matches_in_season):
            match_id = match.get('match_id')
            # Opschonen: verwijder bestaande ELO-logs voor deze match_id
            try:
                existing_elo_logs = list(elo_ref.where(filter=FieldFilter('match_id', '==', match_id)).stream())
                if len(existing_elo_logs) != 4:
                    for doc in existing_elo_logs:
                        batch.delete(doc.reference)
                    batch.commit()
                    batch = db.batch()
                    batch_counter = 0
            except Exception as e:
                print(f"[ELO CLEANUP] Fout bij opschonen ELO logs voor match {match_id}: {e}")

            match_dict = {
                "Thuis_1": match.get('thuis_1'),
                "Thuis_2": match.get('thuis_2'),
                "Uit_1": match.get('uit_1'),
                "Uit_2": match.get('uit_2'),
                "Thuis_score": int(match.get('thuis_score', 0)),
                "Uit_score": int(match.get('uit_score', 0))
            }
            all_ELO_ratings = {}
            for player in [match_dict["Thuis_1"], match_dict["Thuis_2"], match_dict["Uit_1"], match_dict["Uit_2"]]:
                all_ELO_ratings[player] = [player_elos.get(player, 1000)]
            print(f"[DEBUG] Wedstrijd {i+1}/{len(matches_in_season)}: {match_dict}")
            print(f"[DEBUG] ELO input: {all_ELO_ratings}")
            new_elo_df = calculate_new_elo(match_dict, all_ELO_ratings)
            print(f"[DEBUG] ELO output:")
            for _, row in new_elo_df.iterrows():
                print(f"  {row['Speler']}: {row['ELO']}")
                player_elos[row["Speler"]] = row["ELO"]
                new_elo_ref = elo_ref.document()
                batch.set(new_elo_ref, {
                    'speler_naam': row["Speler"],
                    'rating': row["ELO"],
                    'timestamp': match.get('timestamp', SERVER_TIMESTAMP),
                    'match_id': match_id
                })
                batch_counter += 1
            print(f"[DEBUG] ELO's na deze wedstrijd: {player_elos}")
            if batch_counter >= 400:
                batch.commit()
                batch = db.batch()
                batch_counter = 0
        if batch_counter > 0:
            batch.commit()
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Fout bij herberekenen van ELO's voor seizoen: {e}")
        return False
# firestore_service.py
import streamlit as st
import google.cloud.firestore
from google.oauth2 import service_account
import json
import pandas as pd
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

# FIRESTORE INITIALISATIE
def is_running_in_streamlit():
    """Controleert of de code wordt uitgevoerd binnen een Streamlit-sessie."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except ImportError:
        return False

@st.cache_resource
def initialize_firestore():
    """
    Maakt verbinding met Firestore.
    Gebruikt Streamlit secrets in de cloud, anders lokaal serviceaccountbestand.
    """
    project_id = None
    
    # Probeer eerst Streamlit secrets (voor cloud deployment)
    try:
        if hasattr(st, 'secrets') and 'firestore_credentials' in st.secrets:
            # Streamlit Cloud: gebruik secrets
            key_dict = dict(st.secrets["firestore_credentials"])
            project_id = key_dict.get("project_id")
            creds = service_account.Credentials.from_service_account_info(key_dict)
            print("Firestore credentials geladen vanuit Streamlit secrets")
        else:
            raise KeyError("Geen firestore_credentials gevonden in secrets")
    except (KeyError, AttributeError, ValueError) as e:
        print(f"Streamlit secrets niet beschikbaar ({e}), probeer lokaal bestand...")
        
        # Fallback naar lokaal bestand (voor lokale ontwikkeling)
        try:
            with open("firestore-key.json") as f:
                key_dict = json.load(f)
                project_id = key_dict.get("project_id")
            creds = service_account.Credentials.from_service_account_file("firestore-key.json")
            print("Firestore credentials geladen vanuit lokaal bestand")
        except FileNotFoundError:
            print("Fout: Noch Streamlit secrets noch 'firestore-key.json' beschikbaar.")
            print("Voor lokale ontwikkeling: voeg firestore-key.json toe aan de root.")
            print("Voor Streamlit Cloud: configureer firestore_credentials in secrets.")
            raise
        except Exception as e:
            print(f"Fout bij laden van lokale credentials: {e}")
            raise
            
    if not project_id:
        raise ValueError("Project ID kon niet worden gevonden in de credentials.")

    db = google.cloud.firestore.Client(credentials=creds, project=project_id)
    print(f"Firestore client succesvol geïnitialiseerd voor project: {project_id}")
    return db

db = initialize_firestore()

# Maak referenties naar de collecties
players_ref = db.collection('spelers')
matches_ref = db.collection('uitslag')
elo_ref = db.collection('elo')
requests_ref = db.collection('requests')
# seasons_ref = db.collection('seizoenen')  # Niet meer nodig - seizoenen worden automatisch bepaald


# DATA LEESFUNCTIES
@st.cache_data
def get_players():
    """Haalt alle spelers op en hun meest recente ELO-rating."""
    spelers_docs = players_ref.stream()
    players_list = []
    for doc in spelers_docs:
        player_data = doc.to_dict()
        player_data['speler_id'] = doc.id
        players_list.append(player_data)
    
    if not players_list:
        return pd.DataFrame()

    players_df = pd.DataFrame(players_list)

    elo_docs = elo_ref.order_by("timestamp", direction=google.cloud.firestore.Query.DESCENDING).stream()
    elo_list = [doc.to_dict() for doc in elo_docs]

    if not elo_list:
        players_df['rating'] = 1000
        return players_df

    elo_df = pd.DataFrame(elo_list)
    
    # Get the latest ELO for each player
    latest_elo_df = elo_df.loc[elo_df.groupby('speler_naam')['timestamp'].idxmax()]

    # Merge with players_df
    players_with_elo_df = pd.merge(players_df, latest_elo_df[['speler_naam', 'rating']], on='speler_naam', how='left')
    players_with_elo_df['rating'] = players_with_elo_df['rating'].fillna(1000)
    
    return players_with_elo_df

@st.cache_data
def get_matches():
    """Haalt alle wedstrijden op en normaliseert timestamps."""
    matches_docs = matches_ref.order_by("timestamp", direction=google.cloud.firestore.Query.DESCENDING).stream()
    matches = []
    for doc in matches_docs:
        match_data = doc.to_dict()
        match_data['match_id'] = doc.id
        matches.append(match_data)
    df = pd.DataFrame(matches)


    if not df.empty:
        # Normaliseer timestamp naar pandas datetime en maak altijd tz-naive
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df['timestamp'] = normalize_timestamp_series(df['timestamp'])

        # Verwijder overbodige kolommen indien aanwezig (oude kolommen worden alleen verwijderd, niet meer gebruikt)
        cols_to_remove = ['thuis_speler_1', 'thuis_speler_2', 'uit_speler_1', 'uit_speler_2', 'datum', 'tijd']
        for col in cols_to_remove:
            if col in df.columns:
                df = df.drop(columns=col)

        # Herorder kolommen in logische volgorde
        desired_columns = [
            'thuis_1', 'thuis_2', 'uit_1', 'uit_2',
            'thuis_score', 'uit_score',
            'klinkers_thuis_1', 'klinkers_thuis_2', 'klinkers_uit_1', 'klinkers_uit_2',
            'timestamp', 'match_id'
        ]
        available_columns = [col for col in desired_columns if col in df.columns]
        # Voeg overige kolommen toe die niet in desired_columns staan
        other_columns = [col for col in df.columns if col not in available_columns]
        df = df[available_columns + other_columns]

    return df

@st.cache_data
def get_elo_logs():
    """Haalt de volledige ELO geschiedenis op."""
    elo_docs = elo_ref.order_by("timestamp", direction=google.cloud.firestore.Query.DESCENDING).stream()
    elos = [doc.to_dict() for doc in elo_docs]
    return pd.DataFrame(elos)

@st.cache_data
def get_beheer_log():
    """Haalt alle beheer-log entries op uit Firestore."""
    beheer_docs = db.collection('beheer_log').order_by("timestamp", direction=google.cloud.firestore.Query.DESCENDING).stream()
    beheer_logs = [doc.to_dict() for doc in beheer_docs]
    return pd.DataFrame(beheer_logs)

def get_elo_history(_ttl, speler_naam):
    """Haalt de ELO geschiedenis voor een specifieke speler op."""
    elo_query = elo_ref.where(filter=FieldFilter('speler_naam', '==', speler_naam)).order_by("timestamp", direction=google.cloud.firestore.Query.ASCENDING)
    history_docs = elo_query.stream()
    history = [doc.to_dict() for doc in history_docs]
    return pd.DataFrame(history)

@st.cache_data
def get_seasons():
    """Bepaalt seizoenen automatisch op basis van kalenderjaar uit de wedstrijddata."""
    matches_docs = matches_ref.order_by("timestamp", direction=google.cloud.firestore.Query.ASCENDING).stream()
    matches = [doc.to_dict() for doc in matches_docs]
    if not matches:
        return pd.DataFrame()
    df = pd.DataFrame(matches)
    if 'timestamp' not in df.columns:
        return pd.DataFrame()
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp'])
    # Forceer alle timestamps naar tz-naive (UTC) als dtype klopt
    if pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        try:
            if hasattr(df['timestamp'].dt, 'tz') and df['timestamp'].dt.tz is not None:  # type: ignore
                df['timestamp'] = df['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)  # type: ignore
            else:
                df['timestamp'] = df['timestamp'].dt.tz_localize(None)  # type: ignore
        except Exception:
            pass

    from datetime import date, timedelta, datetime
    def get_prinsjesdag(year):
        september = date(year, 9, 1)
        weekday = september.weekday()
        first_tuesday = september + timedelta(days=(1 - weekday) % 7)
        prinsjesdag = first_tuesday + timedelta(days=14)
        dt = datetime.combine(prinsjesdag, datetime.min.time())
        return dt.replace(tzinfo=None)


    # Normaliseer timestamp kolom
    df['timestamp'] = normalize_timestamp_series(df['timestamp'])

    if pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        try:
            min_year = int(df['timestamp'].dt.year.min())  # type: ignore
            max_year = int(df['timestamp'].dt.year.max())  # type: ignore
        except Exception:
            min_year = max_year = None
    else:
        min_year = max_year = None
    if min_year is not None and max_year is not None:
        season_bounds = [get_prinsjesdag(y) for y in range(min_year - 1, max_year + 2)]
        season_bounds = sorted(season_bounds)
    else:
        season_bounds = []

    seizoenen = []
    for i in range(len(season_bounds) - 1):
        vorige_prinsjesdag = season_bounds[i]
        deze_prinsjesdag = season_bounds[i + 1]
        start = vorige_prinsjesdag + timedelta(days=1)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = deze_prinsjesdag.replace(hour=23, minute=59, second=59, microsecond=0)
        seizoen_naam = f"Seizoen {start.year}/{end.year}"
        mask = (df['timestamp'] >= start) & (df['timestamp'] <= end)
        seizoen_df = df[mask]
        n_matches = int(mask.sum())
        seizoenen.append({
            'startdatum': start,
            'einddatum': end,
            'jaar': end.year,
            'seizoen_naam': seizoen_naam,
            'aantal_wedstrijden': n_matches
        })
    seizoenen = [s for s in seizoenen if s['aantal_wedstrijden'] > 0 or (s['startdatum'] <= datetime.combine(date.today(), datetime.min.time()) <= s['einddatum'])]
    df_seizoenen = pd.DataFrame(seizoenen)
    if not df_seizoenen.empty:
        df_seizoenen = df_seizoenen.sort_values('startdatum').reset_index(drop=True)
    return df_seizoenen

@st.cache_data
def get_requests():
    """Haalt alle verzoeken op, gesorteerd op tijdstip."""
    docs = requests_ref.order_by("Timestamp", direction=google.cloud.firestore.Query.DESCENDING).stream()
    requests = [doc.to_dict() for doc in docs]
    return pd.DataFrame(requests)

# ---------------- Schema & Inspectie helpers ----------------
def expected_schema():
    """Geeft het verwachte schema terug dat de app gebruikt per collectie.

    Let op: sommige velden zoals 'match_id', 'speler_id' en 'datum' bestaan alleen in DataFrames (afgeleid),
    niet als daadwerkelijke Firestore-velden.
    """
    return {
        'spelers': {
            'required': {'speler_naam'},
            'optional': set(),
            'derived_only_in_app': {'speler_id'}
        },
        'elo': {
            'required': {'speler_naam', 'rating', 'timestamp'},
            'optional': set(),
            'derived_only_in_app': set()
        },
        'uitslag': {
            'required': {
                'thuis_1', 'thuis_2', 'uit_1', 'uit_2',
                'thuis_score', 'uit_score', 'timestamp'
            },
            'optional': {
                'klinkers_thuis_1', 'klinkers_thuis_2', 'klinkers_uit_1', 'klinkers_uit_2'
            },
            'derived_only_in_app': {'match_id'}
        },
        'requests': {
            'required': {'Verzoek', 'Timestamp'},
            'optional': set(),
            'derived_only_in_app': set()
        }
    }

def inspect_collections(max_docs: int = 200):
    """Inspecteer Firestore en retourneer een overzicht per collectie met voorbeeldvelden.

    Om performance/redenen beperken we ons tot maximaal `max_docs` voorbeeld-documenten per collectie.
    """
    summaries = {}
    collections = {
        'spelers': players_ref,
        'uitslag': matches_ref,
        'elo': elo_ref,
        'requests': requests_ref,
    }

    for name, ref in collections.items():
        sample_docs_iter = ref.limit(max_docs).stream()
        sample_docs = []
        field_union = set()
        try:
            for doc in sample_docs_iter:
                d = doc.to_dict() or {}
                sample_docs.append({k: d.get(k) for k in d.keys()})
                field_union.update(d.keys())
        except Exception as e:
            print(f"Inspectie fout voor collectie {name}: {e}")

        summaries[name] = {
            'sample_size': len(sample_docs),
            'fields': sorted(list(field_union)),
            'examples': sample_docs[:5],  # toon maximaal 5 voorbeelden
        }

    return summaries

# DATA SCHRIJFFUNCTIES
def add_season(startdatum, einddatum):
    """Seizoenen worden nu automatisch bepaald door Prinsjesdag - handmatige toevoeging niet meer nodig."""
    return "Success"  # Dummy return voor compatibiliteit


def add_player(name, start_elo):
    """Voegt een nieuwe speler en zijn initiële ELO-rating toe in een batch."""
    # Controleer eerst of de speler al bestaat
    existing_player_query = players_ref.where(filter=FieldFilter('speler_naam', '==', name)).limit(1)
    if len(list(existing_player_query.stream())) > 0:
        return f"Error: Speler '{name}' bestaat al."

    batch = db.batch()
    try:
        # 1. Voeg de speler toe aan de 'spelers' collectie
        new_player_ref = players_ref.document()
        batch.set(new_player_ref, {'speler_naam': name})

        # 2. Voeg de initiële ELO-rating toe aan de 'elo' collectie
        new_elo_ref = elo_ref.document()
        batch.set(new_elo_ref, {
            'speler_naam': name,
            'rating': start_elo,
            'timestamp': SERVER_TIMESTAMP
        })

        batch.commit()
        st.cache_data.clear()
        return "Success"
    except Exception as e:
        print(f"ERROR: Failed to add player '{name}'. Exception: {e}")
        return f"Error: Could not add player. {e}"

def add_request(request_text):
    """Voegt een nieuw verzoek toe aan de 'requests' collectie."""
    try:
        requests_ref.add({'Verzoek': request_text, 'Timestamp': SERVER_TIMESTAMP})
        st.cache_data.clear()
        return "Success"
    except Exception as e:
        return f"Error: {e}"

def add_match_and_update_elo(match_data, elo_updates):
    """
    Voegt een wedstrijd toe en logt de nieuwe ELO's in een atomaire batch write.
    Ondersteunt nu custom historische timestamp in match_data['timestamp'].
    Als historische wedstrijd toegevoegd wordt (datum < vandaag), herbereken ELO's vanaf begin.
    """
    batch = db.batch()
    from datetime import datetime, date

    try:
        # 1. Timestamp bepalen: gebruik aangeleverde timestamp indien aanwezig, anders server
        provided_ts = match_data.get('timestamp')
        if provided_ts is not None:
            # Zorg dat het een native datetime is
            if hasattr(provided_ts, 'to_pydatetime'):
                provided_ts = provided_ts.to_pydatetime()
            if isinstance(provided_ts, date) and not isinstance(provided_ts, datetime):
                provided_ts = datetime.combine(provided_ts, datetime.min.time())
        match_timestamp = provided_ts if provided_ts else SERVER_TIMESTAMP

        # 2. Voeg de nieuwe wedstrijd toe
        new_match_ref = matches_ref.document()
        match_id = new_match_ref.id
        match_data_with_timestamp = {**match_data, 'timestamp': match_timestamp, 'match_id': match_id}
        batch.set(new_match_ref, match_data_with_timestamp)

        # 3. Log ELO updates met de timestamp van de wedstrijd (voor correcte historie)
        for speler_naam, new_elo in elo_updates:
            new_elo_ref = elo_ref.document()
            batch.set(new_elo_ref, {
                'speler_naam': speler_naam,
                'rating': new_elo,
                'timestamp': match_timestamp
            })

        batch.commit()

        # 4. Indien historische wedstrijd (timestamp < vandaag) => volledige ELO herberekening
        need_recalc = False
        try:
            if isinstance(match_timestamp, datetime):
                today_midnight = datetime.combine(date.today(), datetime.min.time())
                if match_timestamp < today_midnight:
                    need_recalc = True
        except Exception:
            pass

        if need_recalc:
            # Volledige reset kan duur zijn; alternatief is recalc vanaf match_timestamp.
            # Kies recalc vanaf die timestamp voor efficiency.
            recalculate_elo_from_match(match_timestamp)

        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Error during batch commit: {e}")
        return False

def delete_player_by_id(player_id):
    """Verwijdert een speler en al zijn ELO-geschiedenis."""
    batch = db.batch()
    try:
        # 1. Haal de speler op om de naam te krijgen
        player_doc = players_ref.document(player_id).get()
        if not player_doc.exists:
            return True # Beschouw als succes als de speler al weg is
            
        player_data = player_doc.to_dict()
        player_name = player_data.get('speler_naam') if player_data else None

        # 2. Verwijder de speler uit de 'spelers' collectie
        batch.delete(players_ref.document(player_id))

        # 3. Zoek en verwijder alle ELO-entries voor die speler
        if player_name:
            elo_docs_query = elo_ref.where(filter=FieldFilter('speler_naam', '==', player_name))
            elo_docs = list(elo_docs_query.stream())
            for doc in elo_docs:
                batch.delete(doc.reference)
        
        batch.commit()
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Fout bij verwijderen van speler {player_id}: {e}")
        return False

def delete_season_by_id(season_id):
    """Seizoenen worden nu automatisch bepaald door Prinsjesdag - handmatige verwijdering niet meer nodig."""
    return True  # Dummy return voor compatibiliteit

def delete_match_by_id(match_id):
    """Verwijdert een wedstrijd op basis van zijn ID."""
    try:
        matches_ref.document(match_id).delete()
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Fout bij verwijderen van wedstrijd {match_id}: {e}")
        return False

def update_match(match_id, updated_match_data):
    """Werkt een wedstrijd bij op basis van zijn ID."""
    try:
        matches_ref.document(match_id).update(updated_match_data)
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Fout bij bijwerken van wedstrijd {match_id}: {e}")
        return False

def recalculate_elo_from_match(match_timestamp):
    """
    Herberekent alle ELO scores vanaf een bepaalde wedstrijd timestamp.
    Gebruikt voor het corrigeren van ELO's na het bewerken/verwijderen van wedstrijden.
    """
    try:
        from utils_new_elo import calculate_new_elo
        
        # Haal alle wedstrijden op, gesorteerd op timestamp
        all_matches_docs = matches_ref.order_by("timestamp", direction=google.cloud.firestore.Query.ASCENDING).stream()
        all_matches = []
        for doc in all_matches_docs:
            match_data = doc.to_dict()
            match_data['match_id'] = doc.id
            all_matches.append(match_data)
        
        if not all_matches:
            return True
            
        # Converteer naar DataFrame voor makkelijker werken
        matches_df = pd.DataFrame(all_matches)
        
        # Vind de index van de wedstrijd vanaf waar we moeten herberekenen
        target_index = 0
        for i, match in enumerate(all_matches):
            if match.get('timestamp') >= match_timestamp:
                target_index = i
                break
        
        # Haal huidige spelers op
        players_df = get_players()
        if players_df.empty:
            return True
            
        # Maak een dictionary van de ELO's zoals ze waren VOOR de te herberekenen wedstrijd
        if target_index > 0:
            # Er zijn eerdere wedstrijden - bereken ELO's tot aan het herpunt
            previous_matches = all_matches[:target_index]
            player_elos = {}
            
            # Start alle spelers met 1000 ELO
            for _, player in players_df.iterrows():
                player_elos[player['speler_naam']] = 1000
            
            # Bereken ELO's door alle wedstrijden vóór het herpunt
            for match in previous_matches:
                # Prepare match dict for new ELO calculation
                match_dict = {
                    "Thuis_1": match.get('thuis_1'),
                    "Thuis_2": match.get('thuis_2'),
                    "Uit_1": match.get('uit_1'),
                    "Uit_2": match.get('uit_2'),
                    "Thuis_score": int(match.get('thuis_score', 0)),
                    "Uit_score": int(match.get('uit_score', 0))
                }
                # Build ELO history dict (only latest rating for now)
                all_ELO_ratings = {}
                for player in [match_dict["Thuis_1"], match_dict["Thuis_2"], match_dict["Uit_1"], match_dict["Uit_2"]]:
                    all_ELO_ratings[player] = [player_elos.get(player, 1000)]
                new_elo_df = calculate_new_elo(match_dict, all_ELO_ratings)
                for _, row in new_elo_df.iterrows():
                    player_elos[row["Speler"]] = row["ELO"]
        else:
            # Geen eerdere wedstrijden - start met 1000 voor iedereen
            player_elos = {}
            for _, player in players_df.iterrows():
                player_elos[player['speler_naam']] = 1000
        
        # Nu herberekenen vanaf target_index
        matches_to_recalculate = all_matches[target_index:]
        
        # Batch voor ELO updates
        batch = db.batch()
        batch_counter = 0
        
        for match in matches_to_recalculate:
            match_dict = {
                "Thuis_1": match.get('thuis_1'),
                "Thuis_2": match.get('thuis_2'),
                "Uit_1": match.get('uit_1'),
                "Uit_2": match.get('uit_2'),
                "Thuis_score": int(match.get('thuis_score', 0)),
                "Uit_score": int(match.get('uit_score', 0))
            }
            all_ELO_ratings = {}
            for player in [match_dict["Thuis_1"], match_dict["Thuis_2"], match_dict["Uit_1"], match_dict["Uit_2"]]:
                all_ELO_ratings[player] = [player_elos.get(player, 1000)]
            new_elo_df = calculate_new_elo(match_dict, all_ELO_ratings)
            for _, row in new_elo_df.iterrows():
                player_elos[row["Speler"]] = row["ELO"]
                new_elo_ref = elo_ref.document()
                batch.set(new_elo_ref, {
                    'speler_naam': row["Speler"],
                    'rating': row["ELO"],
                    'timestamp': match.get('timestamp', SERVER_TIMESTAMP),
                    'match_id': match.get('match_id')
                })
                batch_counter += 1
            if batch_counter >= 400:
                batch.commit()
                batch = db.batch()
                batch_counter = 0
        
        # Commit resterende updates
        if batch_counter > 0:
            batch.commit()
        
        st.cache_data.clear()
        return True
        
    except Exception as e:
        print(f"Fout bij herberekenen van ELO's: {e}")
        return False

def reset_all_elos():
    """
    Reset alle ELO scores en herberekent ze opnieuw vanaf het begin.
    Gebruikt voor complete ELO reset.
    """
    try:
        import pandas as pd
        from utils_new_elo import calculate_new_elo
        # Verwijder alle bestaande ELO entries
        existing_elo_docs = elo_ref.stream()
        batch = db.batch()
        for doc in existing_elo_docs:
            batch.delete(doc.reference)
        batch.commit()

        # Haal alle wedstrijden op, gesorteerd op timestamp
        all_matches_docs = matches_ref.order_by("timestamp", direction=google.cloud.firestore.Query.ASCENDING).stream()
        all_matches = []
        for doc in all_matches_docs:
            match_data = doc.to_dict()
            match_data['match_id'] = doc.id
            all_matches.append(match_data)

        if not all_matches:
            return True

        # Haal alle spelers op
        players_df = get_players()
        if players_df.empty:
            return True

        # Bepaal seizoenen op basis van Prinsjesdag (zoals in get_seasons)
        matches_df = pd.DataFrame(all_matches)
        matches_df['timestamp'] = pd.to_datetime(matches_df['timestamp'], errors='coerce')
        matches_df = matches_df.dropna(subset=['timestamp'])
        matches_df['timestamp'] = normalize_timestamp_series(matches_df['timestamp'])
        if matches_df.empty:
            return True
        from datetime import date, timedelta, datetime
        def get_prinsjesdag(year):
            september = date(year, 9, 1)
            weekday = september.weekday()
            first_tuesday = september + timedelta(days=(1 - weekday) % 7)
            prinsjesdag = first_tuesday + timedelta(days=14)
            dt_prinsjesdag = datetime.combine(prinsjesdag, datetime.min.time())
            return dt_prinsjesdag.replace(tzinfo=None)

        min_year = matches_df['timestamp'].dt.year.min()  # type: ignore
        max_year = matches_df['timestamp'].dt.year.max()  # type: ignore
        season_bounds = [get_prinsjesdag(y) for y in range(min_year - 1, max_year + 2)]
        season_bounds = sorted([pd.Timestamp(s).to_pydatetime().replace(tzinfo=None) for s in season_bounds])


        # Doorloop alle wedstrijden chronologisch, reset ELO bij seizoensstart
        player_elos = {player['speler_naam']: 1000 for _, player in players_df.iterrows()}
        batch = db.batch()
        batch_counter = 0
        last_season_start = None
        season_idx = 0
        # Houd bij welke spelers in het huidige seizoen actief zijn
        seizoen_spelers = set()
        for _, match in matches_df.sort_values('timestamp').iterrows():
            ts = match['timestamp']
            # Forceer ook deze timestamp naar tz-naive
            if pd.notnull(ts) and hasattr(ts, 'tzinfo') and ts.tzinfo is not None:
                # Gebruik hulpfunctie voor losse timestamp
                import pandas as pd
                ts = pd.Series([ts])
                ts = normalize_timestamp_series(ts).iloc[0]
            # Check of we aan een nieuw seizoen beginnen
            while season_idx < len(season_bounds) - 1 and ts >= season_bounds[season_idx + 1]:
                season_idx += 1
                # Bij seizoenswissel: reset alleen voor spelers die in het vorige seizoen actief waren
                if last_season_start is not None and seizoen_spelers:
                    for speler in seizoen_spelers:
                        player_elos[speler] = 1000
                        new_elo_ref = elo_ref.document()
                        batch.set(new_elo_ref, {
                            'speler_naam': speler,
                            'rating': 1000,
                            'timestamp': ts,
                            'match_id': match.get('match_id') if 'match_id' in match else None
                        })
                        batch_counter += 1
                    if batch_counter >= 400:
                        batch.commit()
                        batch = db.batch()
                        batch_counter = 0
                seizoen_spelers = set()
                last_season_start = season_bounds[season_idx]
            # Verzamel spelers van deze wedstrijd
            for speler in [match.get('thuis_1'), match.get('thuis_2'), match.get('uit_1'), match.get('uit_2')]:
                if speler:
                    seizoen_spelers.add(speler)
            # Doorrekenen deze wedstrijd
            match_dict = {
                "Thuis_1": match.get('thuis_1'),
                "Thuis_2": match.get('thuis_2'),
                "Uit_1": match.get('uit_1'),
                "Uit_2": match.get('uit_2'),
                "Thuis_score": int(match.get('thuis_score', 0)),
                "Uit_score": int(match.get('uit_score', 0))
            }
            all_ELO_ratings = {}
            for player in [match_dict["Thuis_1"], match_dict["Thuis_2"], match_dict["Uit_1"], match_dict["Uit_2"]]:
                all_ELO_ratings[player] = [player_elos.get(player, 1000)]
            new_elo_df = calculate_new_elo(match_dict, all_ELO_ratings)
            for _, row in new_elo_df.iterrows():
                player_elos[row["Speler"]] = row["ELO"]
                new_elo_ref = elo_ref.document()
                batch.set(new_elo_ref, {
                    'speler_naam': row["Speler"],
                    'rating': row["ELO"],
                    'timestamp': match.get('timestamp', SERVER_TIMESTAMP),
                    'match_id': match.get('match_id')
                })
                batch_counter += 1
            if batch_counter >= 400:
                batch.commit()
                batch = db.batch()
                batch_counter = 0
        # Na de laatste wedstrijd: reset voor spelers die in het laatste seizoen actief waren
        if seizoen_spelers:
            # Bepaal een geldige timestamp voor de reset (gebruik laatste wedstrijd of nu)
            if not matches_df.empty:
                laatste_wedstrijd = matches_df.sort_values('timestamp').iloc[-1]
                ts_reset = laatste_wedstrijd['timestamp']
                match_id_reset = laatste_wedstrijd.get('match_id')
            else:
                from datetime import datetime
                ts_reset = datetime.utcnow()
                match_id_reset = None
            for speler in seizoen_spelers:
                player_elos[speler] = 1000
                new_elo_ref = elo_ref.document()
                batch.set(new_elo_ref, {
                    'speler_naam': speler,
                    'rating': 1000,
                    'timestamp': ts_reset,
                    'match_id': match_id_reset
                })
                batch_counter += 1
            if batch_counter > 0:
                batch.commit()
                batch = db.batch()
                batch_counter = 0

        # Commit resterende updates
        if batch_counter > 0:
            batch.commit()

        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Fout bij resetten van alle ELO's: {e}")
        return False

def update_match_with_elo_recalculation(match_id, updated_match_data):
    """
    Werkt een wedstrijd bij en herberekent automatisch alle ELO's vanaf die wedstrijd.
    """
    try:
        # Haal de originele wedstrijd op voor de timestamp
        original_match = matches_ref.document(match_id).get()
        if not original_match.exists:
            return False
        
        original_data = original_match.to_dict()
        if not original_data:
            return False
            
        original_timestamp = original_data.get('timestamp')
        
        # Update de wedstrijd
        matches_ref.document(match_id).update(updated_match_data)


        # Opschonen: verwijder alle ELO-logs vanaf deze timestamp (alleen als timestamp geldig is)
        if original_timestamp is not None:
            from google.cloud.firestore_v1.base_query import FieldFilter
            import pandas as pd
            batch = db.batch()
            batch_counter = 0
            elo_docs = elo_ref.where(filter=FieldFilter('timestamp', '>=', pd.Timestamp(original_timestamp))).stream()
            for doc in elo_docs:
                batch.delete(doc.reference)
                batch_counter += 1
                if batch_counter >= 400:
                    batch.commit()
                    batch = db.batch()
                    batch_counter = 0
            if batch_counter > 0:
                batch.commit()

        # Herberekenen ELO's vanaf deze wedstrijd
        success = recalculate_elo_from_match(original_timestamp)

        st.cache_data.clear()
        return success
        
    except Exception as e:
        print(f"Fout bij bijwerken van wedstrijd met ELO herberekening {match_id}: {e}")
        return False

def delete_match_with_elo_recalculation(match_id):
    """
    Verwijdert een wedstrijd en herberekent automatisch alle ELO's vanaf dat punt.
    """
    try:
        # Haal de wedstrijd op voor de timestamp
        match_doc = matches_ref.document(match_id).get()
        if not match_doc.exists:
            return True  # Al verwijderd
        
        match_data = match_doc.to_dict()
        if not match_data:
            return True
            
        match_timestamp = match_data.get('timestamp')
        
        # Verwijder de wedstrijd
        matches_ref.document(match_id).delete()
        
        # Herberekenen ELO's vanaf dit punt
        success = recalculate_elo_from_match(match_timestamp)
        
        st.cache_data.clear()
        return success
        
    except Exception as e:
        print(f"Fout bij verwijderen van wedstrijd met ELO herberekening {match_id}: {e}")
        return False

def clear_collection(collection_name):
    """Verwijdert alle documenten uit een collectie."""
    try:
        if collection_name == "requests":
            docs = requests_ref.stream()
            for doc in docs:
                doc.reference.delete()
            st.cache_data.clear()
            return True
        # Voeg hier eventueel andere collecties toe die geleegd mogen worden
        return False
    except Exception as e:
        print(f"Fout bij het legen van collectie {collection_name}: {e}")
        return False

# --- DATA IMPORT FUNCTIES ---
def import_players(players_data):
    """
    Importeert spelers uit een lijst van dictionaries.
    Controleert op duplicaten op basis van 'speler_naam'.
    Geeft een samenvatting terug van de importactie.
    """
    added_count = 0
    duplicate_count = 0
    
    # Haal alle bestaande spelernamen op in één query
    existing_players = {doc.to_dict()['speler_naam'] for doc in players_ref.stream()}

    for player in players_data:
        player_name = player.get('speler_naam')
        if not player_name:
            continue

        if player_name in existing_players:
            duplicate_count += 1
        else:
            # Gebruik de bestaande add_player functie die ook de initiële ELO toevoegt
            start_elo = player.get('rating', 1000) # Gebruik rating uit CSV of default naar 1000
            result = add_player(player_name, start_elo)
            if result == "Success":
                added_count += 1
                existing_players.add(player_name) # Voeg toe aan de set om duplicaten binnen dezelfde import te voorkomen
            else:
                # Optioneel: log de fout als add_player faalt
                print(f"Kon speler {player_name} niet importeren: {result}")

    st.cache_data.clear()
    return added_count, duplicate_count

def import_matches(matches_data):
    """
    Importeert wedstrijden uit een lijst van dictionaries.
    Controleert op duplicaten.
    Geeft een samenvatting terug.
    """
    added_count = 0
    duplicate_count = 0
    
    # Haal een subset van bestaande wedstrijden op om te controleren op duplicaten
    # Dit is een vereenvoudiging. Een robuustere aanpak is nodig voor grote datasets.
    existing_matches_docs = matches_ref.order_by("timestamp", direction=google.cloud.firestore.Query.DESCENDING).limit(5000).stream()
    existing_matches = set()
    for doc in existing_matches_docs:
        d = doc.to_dict()
        # Maak een unieke, sorteerbare tuple om de wedstrijd te identificeren
        players_tuple = tuple(sorted([d.get('thuis_1'), d.get('thuis_2'), d.get('uit_1'), d.get('uit_2')]))
        scores_tuple = (d.get('thuis_score'), d.get('uit_score'))
        existing_matches.add((players_tuple, scores_tuple))

    batch = db.batch()
    commit_counter = 0
    for match in matches_data:
        # Maak dezelfde unieke tuple voor de te importeren wedstrijd
        players_tuple = tuple(sorted([match.get('thuis_1'), match.get('thuis_2'), match.get('uit_1'), match.get('uit_2')]))
        scores_tuple = (match.get('thuis_score'), match.get('uit_score'))
        
        if (players_tuple, scores_tuple) in existing_matches:
            duplicate_count += 1
        else:
            new_match_ref = matches_ref.document()
            # Converteer aangeleverde timestamp naar python datetime indien aanwezig, anders gebruik server
            if 'timestamp' in match and match['timestamp'] is not None:
                try:
                    # pd.Timestamp, str of datetime worden naar native datetime geconverteerd
                    match['timestamp'] = pd.to_datetime(match['timestamp']).to_pydatetime()
                except Exception:
                    match['timestamp'] = SERVER_TIMESTAMP
            else:
                match['timestamp'] = SERVER_TIMESTAMP

            batch.set(new_match_ref, match)
            added_count += 1
            existing_matches.add((players_tuple, scores_tuple))
            commit_counter += 1

            # Commit de batch elke 400 writes om de limiet van 500 te vermijden
            if commit_counter >= 400:
                batch.commit()
                batch = db.batch() # Start een nieuwe batch
                commit_counter = 0

    if commit_counter > 0:
        batch.commit() # Commit de resterende writes

    st.cache_data.clear()
    return added_count, duplicate_count

def import_seasons(seasons_data):
    """
    Seizoenen worden nu automatisch bepaald door Prinsjesdag - import niet meer nodig.
    """
    return 0, 0  # Geen toegevoegd, geen duplicaten