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
    Gebruikt Streamlit secrets indien beschikbaar, anders een lokaal serviceaccountbestand.
    """
    project_id = None
    if is_running_in_streamlit():
        # Streamlit-omgeving: gebruik st.secrets
        try:
            key_dict = json.loads(st.secrets["firestore_credentials"])
            project_id = key_dict.get("project_id")
            creds = service_account.Credentials.from_service_account_info(key_dict)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Fout bij laden van Streamlit secrets: {e}")
            raise
    else:
        # Niet-Streamlit omgeving (bv. lokale test): gebruik lokaal bestand
        try:
            with open("firestore-key.json") as f:
                key_dict = json.load(f)
                project_id = key_dict.get("project_id")
            creds = service_account.Credentials.from_service_account_file("firestore-key.json")
        except FileNotFoundError:
            print("Fout: 'firestore-key.json' niet gevonden. Zorg dat dit bestand in de root van je project staat.")
            raise
        except Exception as e:
            print(f"Een onverwachte fout is opgetreden bij het laden van de lokale credentials: {e}")
            raise
            
    if not project_id:
        raise ValueError("Project ID kon niet worden gevonden in de credentials.")

    db = google.cloud.firestore.Client(credentials=creds, project=project_id)
    return db

db = initialize_firestore()

# Maak referenties naar de collecties
players_ref = db.collection('spelers')
matches_ref = db.collection('uitslag')
elo_ref = db.collection('elo')
requests_ref = db.collection('requests')


# DATA LEESFUNCTIES
@st.cache_data
def get_players():
    """Haalt alle spelers op en hun meest recente ELO-rating."""
    spelers_docs = players_ref.stream()
    players = []
    for doc in spelers_docs:
        player_data = doc.to_dict()
        player_data['speler_id'] = doc.id

        # Haal de meest recente ELO-rating op voor deze speler
        elo_query = elo_ref.where(filter=FieldFilter('speler_naam', '==', player_data['speler_naam'])).order_by(
            "timestamp", direction=google.cloud.firestore.Query.DESCENDING
        ).limit(1)
        elo_docs = list(elo_query.stream())

        if elo_docs:
            player_data['rating'] = elo_docs[0].to_dict().get('rating', 1000)
        else:
            player_data['rating'] = 1000 # Default ELO if none found

        players.append(player_data)
        
    return pd.DataFrame(players)

@st.cache_data
def get_matches():
    """Haalt alle wedstrijden op."""
    matches_docs = matches_ref.order_by("timestamp", direction=google.cloud.firestore.Query.DESCENDING).stream()
    matches = [doc.to_dict() for doc in matches_docs]
    return pd.DataFrame(matches)

@st.cache_data
def get_elo_logs():
    """Haalt de volledige ELO geschiedenis op."""
    elo_docs = elo_ref.order_by("timestamp", direction=google.cloud.firestore.Query.DESCENDING).stream()
    elos = [doc.to_dict() for doc in elo_docs]
    return pd.DataFrame(elos)

@st.cache_data
def get_elo_history(_ttl, speler_naam):
    """Haalt de ELO geschiedenis voor een specifieke speler op."""
    elo_query = elo_ref.where(filter=FieldFilter('speler_naam', '==', speler_naam)).order_by("timestamp", direction=google.cloud.firestore.Query.ASCENDING)
    history_docs = elo_query.stream()
    history = [doc.to_dict() for doc in history_docs]
    return pd.DataFrame(history)

@st.cache_data
def get_requests():
    """Haalt alle verzoeken op, gesorteerd op tijdstip."""
    docs = requests_ref.order_by("Timestamp", direction=google.cloud.firestore.Query.DESCENDING).stream()
    requests = [doc.to_dict() for doc in docs]
    return pd.DataFrame(requests)

# DATA SCHRIJFFUNCTIES
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
    match_data: dict met wedstrijdinfo (volgens 'uitslag' structuur)
    elo_updates: lijst van tuples, elk (speler_naam, new_elo)
    """
    batch = db.batch()

    try:
        # 1. Voeg de nieuwe wedstrijd toe aan de 'uitslag' collectie
        new_match_ref = matches_ref.document()
        match_data_with_timestamp = {**match_data, 'timestamp': SERVER_TIMESTAMP}
        batch.set(new_match_ref, match_data_with_timestamp)

        # 2. Log de nieuwe ELO-score voor elke betrokken speler in de 'elo' collectie
        for speler_naam, new_elo in elo_updates:
            new_elo_ref = elo_ref.document()
            batch.set(new_elo_ref, {
                'speler_naam': speler_naam,
                'rating': new_elo,
                'timestamp': SERVER_TIMESTAMP
            })

        batch.commit()
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
            
        player_name = player_doc.to_dict().get('speler_naam')

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