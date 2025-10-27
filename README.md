# Tafelvoetbal Competitie

## Streamlit Cloud Deployment

### 1. Firestore Credentials Configuratie

Voor Streamlit Cloud moet je de Firestore service account credentials configureren in de Streamlit secrets.

#### Stappen:

1. **Ga naar je Streamlit Cloud app dashboard**
2. **Klik op "Manage app" in de rechter onderhoek**
3. **Ga naar de "Secrets" tab**
4. **Voeg de volgende configuratie toe:**

```toml
[firestore_credentials]
type = "service_account"
project_id = "jouw-project-id"
private_key_id = "jouw-private-key-id"
etc
```

## Lokale Ontwikkeling

Voor lokale ontwikkeling plaats je het `firestore-key.json` bestand in de root van het project.

**Let op:** Dit bestand staat in `.gitignore` en wordt niet gecommit naar GitHub om security redenen.