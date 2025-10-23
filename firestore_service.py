# firestore_service.py
import streamlit as st
import google.cloud.firestore
from google.oauth2 import service_account
import json
import pandas as pd

# FIRESTORE INITIALISATIE
@st.cache_resource
def initialize_firestore():
    """Maakt verbinding met Firestore met behulp van de Streamlit secrets."""
    # Converteer de TOML-string uit secrets.toml naar een dictionary
    key_dict = json.loads(st.secrets["firestore_credentials"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    db = google.cloud.firestore.Client(credentials=creds)
    return db

db = initialize_firestore()

# Maak referenties naar de collecties
players_ref = db.collection('players')
matches_ref = db.collection('matches')
requests_ref = db.collection('requests')

# DATA LEESFUNCTIES
def get_players():
    """Haalt alle spelers op uit Firestore en retourneert een Pandas DataFrame."""
    docs = players_ref.stream()
    players = []
    for doc in docs:
        player_data = doc.to_dict()
        player_data['player_id'] = doc.id  # Het unieke ID van het document
        players.append(player_data)
    return pd.DataFrame(players)

def get_matches():
    """Haalt alle wedstrijden op en voegt spelersnamen samen voor weergave."""
    matches_docs = matches_ref.order_by("timestamp", direction=google.cloud.firestore.Query.DESCENDING).stream()
    players_df = get_players()
    
    if players_df.empty:
        return pd.DataFrame()
        
    # Maak een dictionary om snel ID's naar namen om te zetten
    player_id_to_name = players_df.set_index('player_id')['name'].to_dict()

    matches = []
    for doc in matches_docs:
        match_data = doc.to_dict()
        # Vervang de speler-ID's door de daadwerkelijke namen
        match_data = player_id_to_name.get(match_data.get('thuis_speler_1_id'), 'Onbekend')
        match_data = player_id_to_name.get(match_data.get('thuis_speler_2_id'), 'Onbekend')
        match_data['Uit_1'] = player_id_to_name.get(match_data.get('uit_speler_1_id'), 'Onbekend')
        match_data['Uit_2'] = player_id_to_name.get(match_data.get('uit_speler_2_id'), 'Onbekend')
        matches.append(match_data)
        
    return pd.DataFrame(matches)

def get_requests():
    """Haalt alle verzoeken op, gesorteerd op tijdstip."""
    docs = requests_ref.order_by("Timestamp", direction=google.cloud.firestore.Query.DESCENDING).stream()
    requests = [doc.to_dict() for doc in docs]
    return pd.DataFrame(requests)

# DATA SCHRIJFFUNCTIES
def add_player(name, start_elo):
    """Voegt een nieuwe speler toe aan de 'players' collectie."""
    # Controleer eerst of de speler al bestaat om duplicaten te voorkomen
    existing_player = players_ref.where('name', '==', name).limit(1).get()
    if len(list(existing_player)) > 0:
        return "Error: Naam bestaat al."
    
    players_ref.add({'name': name, 'elo': start_elo})
    return "Success"

def add_request(request_text, timestamp):
    """Voegt een nieuw verzoek toe aan de 'requests' collectie."""
    requests_ref.add({'Verzoek': request_text, 'Timestamp': timestamp})

def add_match_and_update_elo(match_data, elo_updates):
    """
    Voegt een wedstrijd toe en update ELO's in een atomaire batch write.
    Dit zorgt ervoor dat ofwel alle operaties slagen, ofwel geen enkele.
    match_data: dict met wedstrijdinfo
    elo_updates: lijst van tuples, elk (new_elo, player_id)
    """
    batch = db.batch()

    # 1. Voeg de nieuwe wedstrijd toe aan de 'matches' collectie
    new_match_ref = matches_ref.document()
    batch.set(new_match_ref, match_data)

    # 2. Update de ELO-score voor elke betrokken speler
    for new_elo, player_id in elo_updates:
        player_doc_ref = players_ref.document(player_id)
        batch.update(player_doc_ref, {'elo': new_elo})

    # 3. Voer alle operaties in de batch in één keer uit
    try:
        batch.commit()
        return True
    except Exception as e:
        print(f"Error during batch commit: {e}")
        return False

def delete_player_by_id(player_id):
    """Verwijdert een speler op basis van zijn document ID."""
    try:
        players_ref.document(player_id).delete()
        return True
    except Exception as e:
        print(f"Fout bij verwijderen van speler {player_id}: {e}")
        return False

def delete_matches_by_player_name(player_name):
    """Verwijdert alle wedstrijden waar een specifieke speler aan meedeed."""
    # Deze functie is complexer omdat we eerst moeten queryen.
    # Voor een simpele test laten we dit even achterwege en focussen we op het verwijderen van spelers.
    # In een productie-omgeving zou je hier een query bouwen.
    print(f"Opruimen van wedstrijden voor {player_name} is niet geïmplementeerd in deze simpele test.")
    pass