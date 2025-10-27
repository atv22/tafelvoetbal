# Deployment Instructies - Tafelvoetbal Competitie

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
private_key = "-----BEGIN PRIVATE KEY-----\njouw-private-key-hier\n-----END PRIVATE KEY-----\n"
client_email = "jouw-service-account@jouw-project-id.iam.gserviceaccount.com"
client_id = "jouw-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/jouw-service-account%40jouw-project-id.iam.gserviceaccount.com"
```

#### Belangrijke Opmerkingen:

- Vervang alle `jouw-*` waarden met de echte waarden uit je `firestore-key.json` bestand
- Zorg ervoor dat de `private_key` correct geformatteerd is met `\n` voor line breaks
- Test de deployment na het opslaan van de secrets

### 2. Requirements

Zorg ervoor dat `requirements.txt` alle benodigde packages bevat:

```txt
streamlit
pandas
google-cloud-firestore
google-auth
numpy
```

## Lokale Ontwikkeling

Voor lokale ontwikkeling plaats je het `firestore-key.json` bestand in de root van het project.

**Let op:** Dit bestand staat in `.gitignore` en wordt niet gecommit naar GitHub om security redenen.

## Troubleshooting

### Fout: "FileNotFoundError"
- **Cloud**: Controleer of de Streamlit secrets correct zijn geconfigureerd
- **Lokaal**: Zorg dat `firestore-key.json` in de project root staat

### Fout: "AttributeError" of "ValueError"
- Controleer of alle velden in de secrets correct zijn ingevuld
- Verifieer dat de `private_key` correct geformatteerd is

### Fout: "Project ID niet gevonden"
- Zorg dat `project_id` correct is ingesteld in de secrets
- Verifieer dat het Firebase project bestaat en toegankelijk is

## Beveiliging

- **Nooit** service account keys committen naar Git
- Gebruik alleen de minimaal benodigde permissions voor de service account
- Roteer service account keys regelmatig