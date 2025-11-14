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
seasons_ref = db.collection('seizoenen')


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
    """Haalt alle wedstrijden op."""
    matches_docs = matches_ref.order_by("timestamp", direction=google.cloud.firestore.Query.DESCENDING).stream()
    matches = []
    for doc in matches_docs:
        match_data = doc.to_dict()
        match_data['match_id'] = doc.id
        matches.append(match_data)
    
    df = pd.DataFrame(matches)
    
    # Herorder kolommen in logische volgorde
    if not df.empty:
        desired_columns = [
            'thuis_1', 'thuis_2', 'uit_1', 'uit_2',
            'thuis_score', 'uit_score',
            'klinkers_thuis_1', 'klinkers_thuis_2', 'klinkers_uit_1', 'klinkers_uit_2',
            'timestamp', 'match_id'
        ]
        # Alleen kolommen gebruiken die daadwerkelijk bestaan
        available_columns = [col for col in desired_columns if col in df.columns]
        df = df[available_columns]
    
    return df

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
def get_seasons():
    """Haalt alle seizoenen op."""
    seasons_docs = seasons_ref.order_by("startdatum", direction=google.cloud.firestore.Query.DESCENDING).stream()
    seasons = []
    for doc in seasons_docs:
        season_data = doc.to_dict()
        season_data['seizoen_id'] = doc.id
        seasons.append(season_data)
    return pd.DataFrame(seasons)

@st.cache_data
def get_requests():
    """Haalt alle verzoeken op, gesorteerd op tijdstip."""
    docs = requests_ref.order_by("Timestamp", direction=google.cloud.firestore.Query.DESCENDING).stream()
    requests = [doc.to_dict() for doc in docs]
    return pd.DataFrame(requests)

# DATA SCHRIJFFUNCTIES
def add_season(startdatum, einddatum):
    """Voegt een nieuw seizoen toe."""
    try:
        # Haal het hoogste bestaande seizoen_id op
        seasons_query = seasons_ref.order_by("seizoen_id", direction=google.cloud.firestore.Query.DESCENDING).limit(1)
        last_season_docs = list(seasons_query.stream())
        
        new_id = 1
        if last_season_docs:
            last_season_data = last_season_docs[0].to_dict()
            if last_season_data and 'seizoen_id' in last_season_data:
                new_id = last_season_data['seizoen_id'] + 1

        # Voeg het nieuwe seizoen toe met het correcte ID
        new_season_ref = seasons_ref.document()
        new_season_ref.set({
            'seizoen_id': new_id,
            'startdatum': startdatum,
            'einddatum': einddatum
        })
        
        st.cache_data.clear()
        return "Success"
    except Exception as e:
        print(f"Fout bij toevoegen van seizoen: {e}")
        return f"Error: {e}"


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
    """Verwijdert een seizoen op basis van zijn ID."""
    try:
        seasons_ref.document(season_id).delete()
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"Fout bij verwijderen van seizoen {season_id}: {e}")
        return False

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
        from utils import elo_calculation
        
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
                # ELO berekening voor deze wedstrijd
                home_team = [match.get('thuis_1'), match.get('thuis_2')]
                away_team = [match.get('uit_1'), match.get('uit_2')]
                home_score = int(match.get('thuis_score', 0))
                away_score = int(match.get('uit_score', 0))
                
                # Bereken gemiddelde ELO's
                home_elos = [player_elos.get(player, 1000) for player in home_team if player]
                away_elos = [player_elos.get(player, 1000) for player in away_team if player]
                
                if len(home_elos) == 2 and len(away_elos) == 2:
                    avg_home_elo = sum(home_elos) / 2
                    avg_away_elo = sum(away_elos) / 2
                    
                    # Update ELO's voor thuisspelers
                    for player in home_team:
                        if player:
                            player_elos[player] = elo_calculation(
                                player_elos.get(player, 1000), avg_away_elo, home_score, away_score
                            )
                    
                    # Update ELO's voor uitspelers
                    for player in away_team:
                        if player:
                            player_elos[player] = elo_calculation(
                                player_elos.get(player, 1000), avg_home_elo, away_score, home_score
                            )
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
            home_team = [match.get('thuis_1'), match.get('thuis_2')]
            away_team = [match.get('uit_1'), match.get('uit_2')]
            home_score = int(match.get('thuis_score', 0))
            away_score = int(match.get('uit_score', 0))
            
            # Bereken gemiddelde ELO's
            home_elos = [player_elos.get(player, 1000) for player in home_team if player]
            away_elos = [player_elos.get(player, 1000) for player in away_team if player]
            
            if len(home_elos) == 2 and len(away_elos) == 2:
                avg_home_elo = sum(home_elos) / 2
                avg_away_elo = sum(away_elos) / 2
                
                # Update ELO's voor thuisspelers
                for player in home_team:
                    if player:
                        new_elo = elo_calculation(
                            player_elos.get(player, 1000), avg_away_elo, home_score, away_score
                        )
                        player_elos[player] = new_elo
                        
                        # Voeg nieuwe ELO toe aan batch
                        new_elo_ref = elo_ref.document()
                        batch.set(new_elo_ref, {
                            'speler_naam': player,
                            'rating': new_elo,
                            'timestamp': match.get('timestamp', SERVER_TIMESTAMP)
                        })
                        batch_counter += 1
                
                # Update ELO's voor uitspelers
                for player in away_team:
                    if player:
                        new_elo = elo_calculation(
                            player_elos.get(player, 1000), avg_home_elo, away_score, home_score
                        )
                        player_elos[player] = new_elo
                        
                        # Voeg nieuwe ELO toe aan batch
                        new_elo_ref = elo_ref.document()
                        batch.set(new_elo_ref, {
                            'speler_naam': player,
                            'rating': new_elo,
                            'timestamp': match.get('timestamp', SERVER_TIMESTAMP)
                        })
                        batch_counter += 1
                
                # Commit batch als deze te groot wordt
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
        from utils import elo_calculation
        
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
        
        # Haal alle spelers op
        players_df = get_players()
        if players_df.empty:
            return True
            
        # Start alle spelers met 1000 ELO
        player_elos = {}
        batch = db.batch()
        batch_counter = 0
        
        for _, player in players_df.iterrows():
            player_name = player['speler_naam']
            player_elos[player_name] = 1000
            
            # Voeg initiële ELO toe
            new_elo_ref = elo_ref.document()
            batch.set(new_elo_ref, {
                'speler_naam': player_name,
                'rating': 1000,
                'timestamp': pd.Timestamp.now()  # Vroege timestamp voor initiële waarden
            })
            batch_counter += 1
        
        # Commit initiële ELO's
        if batch_counter > 0:
            batch.commit()
            
        # Nu alle wedstrijden doorlopen en ELO's berekenen
        batch = db.batch()
        batch_counter = 0
        
        for match in all_matches:
            home_team = [match.get('thuis_1'), match.get('thuis_2')]
            away_team = [match.get('uit_1'), match.get('uit_2')]
            home_score = int(match.get('thuis_score', 0))
            away_score = int(match.get('uit_score', 0))
            
            # Bereken gemiddelde ELO's
            home_elos = [player_elos.get(player, 1000) for player in home_team if player]
            away_elos = [player_elos.get(player, 1000) for player in away_team if player]
            
            if len(home_elos) == 2 and len(away_elos) == 2:
                avg_home_elo = sum(home_elos) / 2
                avg_away_elo = sum(away_elos) / 2
                
                # Update ELO's voor thuisspelers
                for player in home_team:
                    if player:
                        new_elo = elo_calculation(
                            player_elos.get(player, 1000), avg_away_elo, home_score, away_score
                        )
                        player_elos[player] = new_elo
                        
                        # Voeg nieuwe ELO toe aan batch
                        new_elo_ref = elo_ref.document()
                        batch.set(new_elo_ref, {
                            'speler_naam': player,
                            'rating': new_elo,
                            'timestamp': match.get('timestamp', SERVER_TIMESTAMP)
                        })
                        batch_counter += 1
                
                # Update ELO's voor uitspelers
                for player in away_team:
                    if player:
                        new_elo = elo_calculation(
                            player_elos.get(player, 1000), avg_home_elo, away_score, home_score
                        )
                        player_elos[player] = new_elo
                        
                        # Voeg nieuwe ELO toe aan batch
                        new_elo_ref = elo_ref.document()
                        batch.set(new_elo_ref, {
                            'speler_naam': player,
                            'rating': new_elo,
                            'timestamp': match.get('timestamp', SERVER_TIMESTAMP)
                        })
                        batch_counter += 1
                
                # Commit batch als deze te groot wordt
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
            # Zorg ervoor dat de timestamp wordt geconverteerd als het een string is
            if 'timestamp' in match and isinstance(match['timestamp'], str):
                match['timestamp'] = pd.to_datetime(match['timestamp'])
            else:
                match['timestamp'] = SERVER_TIMESTAMP # Fallback

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
    Importeert seizoenen uit een lijst van dictionaries.
    Controleert op duplicaten op basis van start- en einddatum.
    """
    added_count = 0
    duplicate_count = 0
    
    existing_seasons_docs = seasons_ref.stream()
    existing_seasons = set()
    for doc in existing_seasons_docs:
        d = doc.to_dict()
        # Converteer Firestore timestamps naar vergelijkbare objecten
        start = pd.to_datetime(d.get('startdatum')).strftime('%Y-%m-%d')
        eind = pd.to_datetime(d.get('einddatum')).strftime('%Y-%m-%d')
        existing_seasons.add((start, eind))

    for season in seasons_data:
        start_str = pd.to_datetime(season.get('startdatum')).strftime('%Y-%m-%d')
        eind_str = pd.to_datetime(season.get('einddatum')).strftime('%Y-%m-%d')

        if (start_str, eind_str) in existing_seasons:
            duplicate_count += 1
        else:
            # Gebruik de bestaande add_season functie
            result = add_season(pd.to_datetime(season.get('startdatum')), pd.to_datetime(season.get('einddatum')))
            if result == "Success":
                added_count += 1
                existing_seasons.add((start_str, eind_str))

    st.cache_data.clear()
    return added_count, duplicate_count