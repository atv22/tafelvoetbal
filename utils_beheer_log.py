import streamlit as st
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

def log_admin_action(action_type, user, details, db):
    """
    Logt een beheeractie naar de Firestore collectie 'beheer_log'.
    :param action_type: Type handeling (bijv. 'delete_match', 'reset_elo', 'add_player', ...)
    :param user: Gebruikersnaam of id (indien beschikbaar)
    :param details: Extra details over de actie (dict of string)
    :param db: Firestore client
    """
    log_ref = db.collection('beheer_log')
    log_entry = {
        'action_type': action_type,
        'user': user,
        'details': details,
        'timestamp': SERVER_TIMESTAMP
    }
    log_ref.add(log_entry)
