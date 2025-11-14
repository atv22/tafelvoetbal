# 🏓 Tafelvoetbal Competitie App

Een moderne webapplicatie voor het beheren van tafelvoetbal competities, ontwikkeld tijdens de **Hackatron van oktober 2025**.

## 👥 Team

Ontwikkeld door:
- **Rick**
- **Bernd**
- **Dewi**
- **Isis**
- **Johannes**
- **Arthur**

## 🚀 Features

### Wedstrijd Beheer
- ✅ Wedstrijden invoeren en bewerken
- ✅ Real-time score updates
- ✅ Wedstrijden verwijderen (individueel of bulk)
- ✅ Automatische timestamp registratie

### ELO Rating Systeem
- 📊 Automatische ELO score berekening (K-factor 32)
- 🔄 ELO herberekening na wijzigingen
- 📈 Real-time rankings
- 🎯 Team-gebaseerde ELO updates

### Data Beheer
- 📁 CSV import voor historische data
- 👥 Speler beheer en registratie
- 📅 Seizoen organisatie
- 🗑️ Bulk delete functionaliteit
- ⚙️ Database maintenance tools

### User Interface
- 📱 Responsive Streamlit interface
- 🎨 Georganiseerde tab structuur
- 📊 Interactieve dataframes
- ⚡ Real-time updates

## 🛠️ Technische Stack

- **Frontend:** Streamlit
- **Backend:** Python
- **Database:** Google Firestore
- **Data Processing:** Pandas
- **Deployment:** Streamlit Cloud

## 🔧 Installatie & Setup

### Lokale Ontwikkeling

1. **Clone de repository:**
```bash
git clone https://github.com/atv22/tafelvoetbal.git
cd tafelvoetbal
```

2. **Installeer dependencies:**
```bash
pip install -r requirements.txt
```

3. **Firestore configuratie:**
   - Plaats je `firestore-key.json` in de project root
   - Dit bestand staat in `.gitignore` voor security

4. **Start de applicatie:**
```bash
streamlit run app.py
```

### Streamlit Cloud Deployment

#### Firestore Credentials Configuratie

Voor Streamlit Cloud configureer de credentials in de app secrets:

1. **Ga naar je Streamlit Cloud app dashboard**
2. **Klik op "Manage app"**
3. **Ga naar de "Secrets" tab**
4. **Voeg toe:**

```toml
[firestore_credentials]
type = "service_account"
project_id = "jouw-project-id"
private_key_id = "jouw-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\njouw-private-key\n-----END PRIVATE KEY-----\n"
client_email = "jouw-service-account@jouw-project.iam.gserviceaccount.com"
client_id = "jouw-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/jouw-service-account%40jouw-project.iam.gserviceaccount.com"
```

## 📊 Database Schema

### Collections:
- **players:** Speler informatie en ELO scores
- **matches:** Wedstrijd resultaten en timestamps  
- **seasons:** Seizoen definities
- **elo_history:** ELO score historie
- **requests:** Tijdelijke data opslag

### CSV Import Formaten:

**Wedstrijden:**
```csv
datum,thuisteam_id,thuisteam_naam,uitteam_id,uitteam_naam,thuisteam_score,uitteam_score,timestamp
2025-01-15,1,Rick,2,Arthur,3,2,2025-01-15 14:30:00
```

**Spelers:**
```csv
speler_id,speler_naam,elo_score
1,Rick,1050
2,Arthur,980
```

## 🎯 Gebruik

### 1. **Home Tab**
- Overzicht van recente wedstrijden
- Quick stats en rankings

### 2. **Invullen Tab**
- Nieuwe wedstrijden registreren
- Speler selectie en score invoer

### 3. **Spelers Tab**
- ELO rankings bekijken
- Speler statistieken

### 4. **Ruwe Data Tab**
- Alle wedstrijden in tabelvorm
- Exporteer mogelijkheden

### 5. **Beheer Tab**
- **Verwijderen:** Wedstrijden/spelers verwijderen
- **Bewerken:** Wedstrijden aanpassen
- **Data Upload:** CSV imports
- **Systeem Beheer:** ELO reset, database cleanup

## 🏆 Hackatron 2025

Deze app werd ontwikkeld tijdens de Hackatron van oktober 2025 als een teamproject. Het combineert moderne web development met praktische functionaliteit voor competitie beheer.

## 📝 Licentie

Ontwikkeld door het Hackatron 2025 team. Alle rechten voorbehouden.