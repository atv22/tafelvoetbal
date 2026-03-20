# Tafelvoetbal Competitie App

Een webapplicatie voor het beheren van tafelvoetbal competities, ontwikkeld tijdens de **Hackatron van oktober 2025**. 

## 🚀 Features

### Wedstrijd Beheer
- ✅ Wedstrijden invoeren en bewerken
- ✅ Real-time score updates
- ✅ Automatische timestamp registratie
- 🏆 **Recordhouders:** Prominente weergave van peak ELO prestaties.

### ELO Rating Systeem
- 📊 Automatische ELO score berekening op basis van teamsterkte en scoreverschil.
- 🔄 ELO herberekening na wijzigingen of verwijderingen.
- 📉 **Trendindicatoren:** Direct inzicht in recente stijgingen of dalingen via gekleurde pijltjes (↑/↓).
- 📈 Real-time rankings per seizoen en all-time.

### Data Beheer & Backup (Nieuw!)
- 📊 **Google Sheets Sync:** Automatische backup van alle Firestore data naar een [Google Sheet](https://docs.google.com/spreadsheets/d/1cCiNoYfro9SqS8qIjEKT8prsAvAA7wowvhzhh2ljHnA). Dit dient als live backup en biedt de mogelijkheid voor eigen analyses buiten de app.
- ⚡ **Performance:** Vectorized Pandas operaties voor razendsnelle berekeningen.
- 💾 **Caching:** Streamlit caching (10 min TTL) voor een soepele ervaring.
- ⚙️ **Beheer:** Tools voor ELO resets, database cleanup en spelerbeheer.

### Controlejaar (CJ) & Seizoenen
De competitie volgt de ADR-systematiek (15 maart - 15 maart).
1. **Zomerseizoen**: 15 maart tot Prinsjesdag.
2. **Winterseizoen**: Prinsjesdag tot 15 maart.
*Bij de start van elk seizoen worden de ELO's gereset naar 1000 voor een eerlijke start.*

## 🔧 Installatie & Setup

### Lokale Ontwikkeling
1. **Clone repository:** `git clone https://github.com/atv22/tafelvoetbal.git`
2. **Dependencies:** `pip install -r requirements.txt`
3. **Google Auth:** Plaats `firestore-key.json` in de root. Zorg dat het service account rechten heeft op zowel Firestore als de Google Sheet.
4. **Run:** `streamlit run app.py`

## 🛠️ Technische Stack
- **Frontend:** Streamlit
- **Backend:** Python
- **Database:** Google Firestore (Cloud)
- **Backup:** Google Sheets API
- **Onderhoud:** Gemini CLI

## 🏆 Hackatron 2025
Ontwikkeld door Rick, Bernd, Dewi, Isis, Johannes & Arthur.
