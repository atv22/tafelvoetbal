"""
TAB 9: Colofon, Snelstart (Tutorial), Documentatie & ELO-uitleg voor de tafelvoetbal app.
Bevat ook de herbruikbare Snelstart-tutorial zodat deze zowel op de Home-tab als in de
documentatiesectie kan worden weergegeven.
"""
import streamlit as st


def render_quick_tutorial():
    """Rendert een beknopte, stapsgewijze Snelstart / Tutorial voor nieuwe gebruikers."""
    st.markdown(
        """
        Welkom bij de **Tafelvoetbal Competitie App**! In **4 simpele stappen** doe je mee aan de competitie:

        #### 1️⃣ Registreer jezelf als speler (éénmalig)
        * Sta je nog niet in de lijst? Ga naar het tabblad **👥 Spelers** en scrol naar beneden naar **Nieuwe speler toevoegen**.
        * Vul je voornaam in (beginnend met een **hoofdletter**, alleen letters, 2–50 tekens) en klik op **➕ Speler Toevoegen**.
        * Je start direct met een beginrating van **1000 ELO-punten**.

        #### 2️⃣ Speel een potje (2 tegen 2) & voer de uitslag in
        * Ga na jullie wedstrijd naar het tabblad **📝 Invullen**.
        * Selecteer de **4 unieke spelers** (*Thuis 1 & 2* tegen *Uit 1 & 2*).
        * Zijn er **klinkers** gescoord? Zet *"Zijn er klinkers gescoord?"* eerst op **Ja** en vul per speler het aantal klinkers in (**+15 ELO bonus** per klinker!).
        * Vul de eindstand in: een potje gaat altijd tot de **10 doelpunten** (één team heeft **10**, het andere team **0 t/m 9**).
        * Klik op **Verstuur Uitslag**. *(Bij een 10-0 overwinning trakteert de app op ballonnen! 🎈)*

        #### 3️⃣ Volg je positie op de ELO-ranglijst
        * Op het tabblad **🏠 Home** zie je direct de bijgewerkte stand van het **huidige seizoen** en de **laatste 10 uitslagen**.
        * **Kwalificatie (min. 3 potjes):** Pas vanaf **3 gespeelde wedstrijden** in het huidige seizoen ben je officieel *gerangschikt* en worden je **Win%** en **Gem. Goals** berekend. Spelers met minder dan 3 potjes staan cursief in het grijs; de top 3 gerangschikte spelers licht groen op.
        * De kolom **Trend** toont hoeveel ELO-punten je bij je laatste wedstrijd hebt gewonnen (`+` groen) of verloren (`-` rood).

        #### 4️⃣ Bekijk grafieken, records & heb je een foutje gemaakt?
        * **Grafieken & Records:** Bekijk je persoonlijke ELO-curve onder **👥 Spelers** of duik in alle seizoensrecords en Top-5 ranglijsten onder **📈 Analytics**.
        * **Foutje ingevoerd?** Geen probleem! Een beheerder kan via **⚙️ Beheer** een wedstrijd aanpassen of verwijderen (de ELO-ketting wordt dan 's avonds om **23:00 uur** automatisch herberekend).
        * **Idee of wens?** Laat een berichtje achter in het tabblad **💬 Verzoeken**!
        """
    )


def render_colofon_tab():
    """Rendert het volledige Colofon, Documentatie & Snelstart tabblad."""
    st.header("ℹ️ Colofon, Snelstart & Documentatie")
    st.write(
        "Alles wat je moet weten over het gebruik van de Tafelvoetbal Competitie App, "
        "de spelregels, het ELO-ratingsysteem, de seizoensindeling en de techniek achter de schermen."
    )

    doc_tab1, doc_tab2, doc_tab3, doc_tab4 = st.tabs([
        "🚀 Snelstart (Tutorial)",
        "📖 Handleiding & Spelregels",
        "🧮 ELO & Seizoenen",
        "🏆 Over deze App (Colofon)",
    ])

    # -----------------------------------------------------------------------
    # SUBTAB 1: SNELSTART (TUTORIAL)
    # -----------------------------------------------------------------------
    with doc_tab1:
        st.subheader("🚀 Snelstart voor Nieuwe Spelers")
        render_quick_tutorial()

    # -----------------------------------------------------------------------
    # SUBTAB 2: HANDLEIDING & SPELREGELS
    # -----------------------------------------------------------------------
    with doc_tab2:
        st.subheader("📖 Overzicht van alle Tabbladen")
        st.markdown(
            """
            De applicatie is opgebouwd uit **10 tabbladen**, elk met een eigen functie:

            | Tabblad | Waar gebruik je het voor? |
            | :--- | :--- |
            | **🏠 Home** | Bekijk de actuele **ELO-ranglijst** van het huidige seizoen, je recente **Trend** en de **laatste 10 uitslagen**. |
            | **📝 Invullen** | Registreer een nieuwe **2v2-wedstrijd** inclusief eindstand (tot de 10), datum/tijd en eventuele **klinkers**. Bevat automatische duplicaatdetectie (binnen 24 uur). |
            | **👥 Spelers** | Bekijk de interactieve **ELO-ontwikkeling** van elke speler over tijd (huidig seizoen of alle seizoenen) en voeg nieuwe spelers toe aan de competitie. |
            | **📈 Analytics** | Bewonder de **All-time Recordhouders** (*Peak ELO*), het overzicht van alle gespeelde seizoenen, **8 Top-5 ranglijsten** en uitgebreide grafieken. |
            | **📊 Ruwe Data** | Bekijk en download alle brontabellen (*Uitslagen*, *ELO Geschiedenis* en *Spelers*) rechtstreeks als **CSV-bestand** voor eigen analyses. |
            | **💬 Verzoeken** | Dien een idee, feature-wens of bugmelding in (max. 250 tekens) en bekijk eerder ingediende verzoeken. |
            | **📜 Commits** | Volg de laatste technische updates, bugfixes en nieuwe features in een vertaald overzicht van de Git-wijzigingshistorie. |
            | **🔍 Logging** | Transparant logboek van alle uitgevoerde **beheerdersacties** en de technische database-operaties van de huidige sessie. |
            | **ℹ️ Colofon** | Deze pagina! Met de **Snelstart-tutorial**, handleiding, wiskundige uitleg van het ELO-systeem en informatie over het ontwikkelteam. |
            | **⚙️ Beheer** | Beveiligde omgeving voor beheerders om wedstrijden te corrigeren/verwijderen, spelersnamen te wijzigen, CSV's te importeren en Google Sheets te synchroniseren. |

            ---

            ### ❓ Veelgestelde Vragen (FAQ)

            * **Waarom staan mijn Win% en Gem. Goals op `-` en is mijn naam grijs/cursief?**
              Om te voorkomen dat iemand na één gewonnen potje direct het hoogste winstpercentage opeist, ben je pas **gerangschikt** vanaf **3 gespeelde wedstrijden** in het huidige seizoen. Zodra je 3 potjes hebt gespeeld, worden al je statistieken zichtbaar en kun je meedingen naar de groen gemarkeerde Top 3!
            * **Wat is een 'Klinker'?**
              Een *klinker* is een spectaculair schot dat zo hard in het doel slaat dat het metaal van de doelbak hoorbaar klinkt (en de bal er vaak direct weer uit stuitert). Elke klinker telt als een geldig doelpunt voor je team én levert de schutter direct **+15 extra ELO-punten** op!
            * **Ik heb per ongeluk een verkeerde uitslag of speler ingevoerd. Wat nu?**
              Vraag een beheerder om de wedstrijd aan te passen of te verwijderen via **⚙️ Beheer**. Om database-limieten te sparen wordt de volledige ELO-geschiedenis daarna om **23:00 uur 's avonds** automatisch opnieuw doorgerekend.
            * **Wat betekent de melding 'Offline modus — Google Sheet backup actief'?**
              De app gebruikt Google Cloud Firestore als hoofddatabase. Als de dagelijkse gratis lees-/schrijflimiet tijdelijk is bereikt, schakelt de app automatisch en naadloos over op de live **Google Sheets back-up**. Je kunt dan gewoon standen bekijken en nieuwe potjes blijven invoeren!
            """
        )

    # -----------------------------------------------------------------------
    # SUBTAB 3: ELO & SEIZOENEN
    # -----------------------------------------------------------------------
    with doc_tab3:
        st.subheader("🧮 Het ELO Rating Systeem")
        st.markdown(
            """
            Het ELO-systeem bepaalt de relatieve sterkte van elke speler op basis van hun prestaties in 2v2-wedstrijden.
            Elke speler start een nieuw seizoen met **1000 punten**. Na elke wedstrijd wordt de ELO van alle vier de spelers direct aangepast.

            #### De Formule (zoals geïmplementeerd in de code)
            > **Nieuwe ELO** = Oude ELO + $K \\times \\text{Impact} \\times (\\text{Resultaat} - \\text{Verwachting}) + (\\text{Klinkers} \\times 15)$

            Waarbij de onderdelen als volgt worden berekend:
            1. **Verwachting (Winstkans):**
               Voor elke speler $X$ wordt de verwachte score berekend tegen beide tegenstanders ($Y$ en $Z$) afzonderlijk en daarna gemiddeld:
               $$E(X, Y) = \\frac{1}{1 + 10^{(R_Y - R_X) / 500}}, \\quad \\text{Verwachting}_X = \\frac{E(X, Y) + E(X, Z)}{2}$$
               *Speel je tegen een team met een veel hogere ELO? Dan is je verwachting laag: win je tóch, dan krijg je een flinke ELO-sprong!*
            2. **Resultaat:**
               `1.0` voor het winnende team, `0.0` voor het verliezende team (`0.5` bij gelijkspel).
            3. **Impact van het Scoreverschil (Logaritmisch):**
               Hoe groter het verschil in doelpunten ($\\Delta = |\\text{Thuis} - \\text{Uit}|$), hoe groter de ELO-aanpassing. De impact neemt logaritmisch toe zodat een 10-0 zwaarder telt dan 10-9, maar niet tien keer zo zwaar:
               $$\\text{Impact} = 2 + \\left(\\frac{\\log_{10}(\\Delta + 1)}{\\log_{10}(10)}\\right)^3$$
               *(Bij 10-9 is de impact $\\approx 2.03$; bij 10-5 is de impact $\\approx 2.47$; bij 10-0 is de impact $\\approx 3.13$.)*
            4. **Dynamische K-factor ($K$):**
               De aanpassingsfactor $K$ bepaalt hoe snel je rating beweegt op basis van het aantal gespeelde wedstrijden ($N$) in het huidige seizoen:
               $$K = \\frac{50}{1 + N / 300}$$
               *Nieuwe spelers ($N=0 \\Rightarrow K=50$) stijgen of dalen sneller om vlot hun echte niveau te bereiken; naarmate je meer speelt, wordt je ELO stabieler.*
            5. **Klinkers Bonus:**
               Elke gescoorde klinker geeft een directe individuele bonus van **+15 ELO-punten**, ongeacht of je team de wedstrijd wint of verliest.

            ---

            ### 📅 Controlejaar (CJ) & Seizoensindeling

            De competitie volgt de officiële **ADR Controlejaar-systematiek** (15 maart t/m 15 maart), verdeeld in twee seizoenen per jaar:

            * **☀️ Zomerseizoen (`CJ <Jaar> Zomer`):** Start op **15 maart (00:00 uur)** en loopt tot en met **Prinsjesdag** (de derde dinsdag van september, 23:59:59 uur).
            * **❄️ Winterseizoen (`CJ <Jaar> Winter`):** Start in de nacht **na Prinsjesdag (woensdag 00:00 uur)** en loopt tot en met **14 maart van het volgende jaar (23:59:59 uur)**.

            **🔄 Automatische Seizoensreset:**
            Zodra de allereerste wedstrijd van een nieuw seizoen wordt ingevoerd, zet het systeem de ELO-rating van alle spelers automatisch terug naar **1000 punten**. Zo begint iedereen elk halfjaar met gelijke kansen op de seizoenswinst, terwijl je all-time records (*Peak ELO*) bewaard blijven onder **📈 Analytics**!
            """
        )

    # -----------------------------------------------------------------------
    # SUBTAB 4: OVER DEZE APP (COLOFON)
    # -----------------------------------------------------------------------
    with doc_tab4:
        st.subheader("🏆 Over de Tafelvoetbal Competitie App")
        st.markdown(
            """
            Deze webapplicatie is oorspronkelijk ontwikkeld tijdens de **Hackatron van oktober 2025** (ADR / Ministerie van Financiën) en sindsdien continu doorontwikkeld.

            #### 👥 Het Ontwikkelteam (Hackatron 2025)
            * **Rick**
            * **Bernd**
            * **Dewi**
            * **Isis**
            * **Arthur**
            * **Johannes**

            #### 🛠️ Technische Architectuur & Stack
            * **Frontend & UI:** [Streamlit](https://streamlit.io/) met een op maat gemaakt ADR/MinFin-thema (`styles.py`), geoptimaliseerd voor zowel desktop als mobiel.
            * **Data-analyse & Visualisatie:** Gevectoriseerde [Pandas](https://pandas.pydata.org/) & [NumPy](https://numpy.org/) berekeningen gecombineerd met interactieve [Plotly](https://plotly.com/python/) grafieken.
            * **Hybride Cloud Database:**
              * **Google Cloud Firestore:** Primaire NoSQL cloud-database met real-time `on_snapshot` listeners.
              * **Google Sheets API (`gspread`):** Live [Google Sheet Back-up](https://docs.google.com/spreadsheets/d/1cCiNoYfro9SqS8qIjEKT8prsAvAA7wowvhzhh2ljHnA), historische oppak-cache bij het opstarten én automatische **Offline Fallback** wanneer database-quota worden bereikt.
              * **Slimme Quota-optimalisatie:** Uitgestelde ketting-herberekening van ELO-scores om **23:00 uur** na beheerderscorrecties.
            * **Kwaliteitsborging & Open Source:** Geautomatiseerde testsuite met `pytest`, gelicentieerd onder de **MIT License**.
            * **AI-ondersteuning:** Ontwikkeld en onderhouden met AI-assistentie van **Google Gemini**.
            """
        )