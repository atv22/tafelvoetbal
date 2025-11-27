# TODO: Verbeterpunten Tafelvoetbal App

## 1. ELO-logica en synchronisatie

- [x] ELO-logs krijgen nu altijd de timestamp van de bijbehorende wedstrijd, niet meer SERVER_TIMESTAMP.
- [ ] Controleer of alle bestaande ELO-historie in de database nog logisch klopt qua tijdlijn (optioneel: migratiescript).

## 2. Seizoensbepaling en ELO-reset

- [ ] Log alleen een ELO-reset (1000) voor spelers die daadwerkelijk in het seizoen spelen.
- [ ] Voeg validatie toe op correcte timestamps bij seizoensbepaling.

## 3. Testdata en cleanup

- [ ] Implementeer een pytest fixture of teardown die testdata altijd opruimt, ook bij test-failures.
- [ ] Maak testdata uniek per test-run (bijv. met een UUID-suffix).

## 4. Schema en veldnamen

- [ ] Maak naming van collecties en velden consistent tussen code en documentatie (README).
- [ ] Documenteer duidelijk welke velden alleen in DataFrames bestaan en niet in Firestore.

## 5. Timestamp normalisatie

- [ ] Centraliseer timestamp-normalisatie in een hulpfunctie en gebruik deze overal.
- [ ] Voeg extra validatie toe op ontbrekende of foutieve timestamps.

## 6. Edge cases bij wedstrijdinvoer

- [ ] Voeg validatie toe op dubbele wedstrijden (zelfde spelers, score, tijd).
- [ ] Controleer op dataconsistentie vóór ELO-herberekeningen (bijv. ontbrekende spelers).

## 7. Gebruik van cache in Streamlit

- [ ] Controleer of cache altijd wordt geleegd na mutaties.
- [ ] Overweeg robuustere cache-invalidering bij externe wijzigingen.

## 8. Overige

- [ ] Voeg meer automatische integratietests toe voor edge cases (bijv. historische wedstrijden, seizoensovergangen).
- [ ] Voeg logging toe voor belangrijke mutaties (optioneel: beheer-log uitbreiden).
