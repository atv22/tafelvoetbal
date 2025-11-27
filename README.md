# Tafelvoetbal Competitie App

Een webapplicatie voor het beheren van tafelvoetbal competities, ontwikkeld tijdens de **Hackatron van oktober 2025**.

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

- 📊 Automatische ELO score berekening
- 🔄 ELO herberekening na wijzigingen
- 📈 Real-time rankings
- 🎯 Team-gebaseerde ELO updates

#### Uitleg ELO Berekening

Het ELO-systeem in deze app is speciaal aangepast voor 2v2 tafelvoetbal. Elke speler start met 1000 punten. Na elke wedstrijd wordt de ELO van alle vier de spelers aangepast op basis van:

- Het verwachte resultaat (op basis van de ELO van beide teams)
- Het daadwerkelijke scoreverschil
- Het aantal eerder gespeelde wedstrijden (K-factor daalt bij meer ervaring)

De berekening is geïnspireerd op [dit artikel](https://towardsdatascience.com/developing-an-elo-based-data-driven-ranking-system-for-2v2-multiplayer-games-7689f7d42a53) en houdt rekening met teamdynamiek en scoreverschillen. Zo ontstaat een eerlijke en dynamische ranglijst.

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

**Installeer dependencies:**

```bash
pip install -r requirements.txt
```

**Firestore configuratie:**

- Plaats je `firestore-key.json` in de project root
- Dit bestand staat in `.gitignore` voor security

**Start de applicatie:**

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

## 📊 Database Schema & Veldnamen

### Collections (Firestore)

- **spelers:** Speler informatie en ELO scores
- **uitslag:** Wedstrijd resultaten en timestamps  
- **elo:** ELO score historie
- **requests:** Tijdelijke data opslag
- **seizoenen:** Seizoen definities (afgeleid, niet als losse collectie)

> **Let op:** In de code en app wordt soms de Engelse term 'matches' gebruikt als alias voor de Firestore-collectie 'uitslag'. In Firestore zelf heet de collectie altijd **uitslag**.

### Veldnamen: Firestore vs. DataFrame/app

- Sommige velden bestaan **alleen in de app of in DataFrames** en niet als veld in Firestore. Dit zijn zogeheten "afgeleide velden" (bijv. `match_id`, `speler_id`).
- Firestore-documenten hebben standaard een automatisch ID (`doc.id`), dat in de app als `match_id` of `speler_id` wordt toegevoegd aan DataFrames voor makkelijke verwerking.
- Verwacht dus **niet** dat deze velden als veld in Firestore-documenten staan; ze worden alleen in de app toegevoegd.

#### Overzicht per collectie

| Collectie   | Vereiste velden (Firestore) | Optioneel | Alleen in app/DataFrame |
|-------------|----------------------------|-----------|------------------------|
| spelers     | speler_naam                |           | speler_id              |
| elo         | speler_naam, rating, timestamp |       |                        |
| uitslag     | thuis_1, thuis_2, uit_1, uit_2, thuis_score, uit_score, timestamp | klinkers_thuis_1, klinkers_thuis_2, klinkers_uit_1, klinkers_uit_2 | match_id |
| requests    | Verzoek, Timestamp         |           |                        |

#### CSV Import Formaten

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

#### Naming Conventies

- Gebruik in code en documentatie consequent de naam **uitslag** voor de Firestore-collectie met wedstrijden.
- Gebruik **match_id** en **speler_id** alleen als DataFrame/app-veld, niet als Firestore-veld.
- Controleer bij import/export altijd of deze velden wel/niet in de brondata staan.

#### Mogelijke valkuilen

- Externe tools of scripts die direct Firestore-data exporteren/importeren missen deze afgeleide velden. Voeg ze toe in de app of bij verwerking in pandas.
- Bugs kunnen ontstaan als code verwacht dat `match_id` of `speler_id` altijd als veld aanwezig is. Controleer altijd op aanwezigheid of voeg ze toe via `doc.id`.

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
