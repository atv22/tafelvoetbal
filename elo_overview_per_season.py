import pandas as pd
import firestore_service as db

def elo_overview_per_season():
    """
    Genereer een overzicht van spelers die in meerdere seizoenen actief zijn, met hun ELO-geschiedenis per seizoen.
    Toon per speler in welke seizoenen ze actief waren en hun ELO aan het begin en eind van elk seizoen.
    """
    seasons_df = db.get_seasons()
    matches_df = db.get_matches()
    players_df = db.get_players()
    overview = []
    for speler in players_df['speler_naam']:
        speler_info = {'speler_naam': speler, 'seizoenen': []}
        elo_hist = db.get_elo_history(_ttl=60, speler_naam=speler)
        if elo_hist.empty:
            continue
        elo_hist['timestamp'] = pd.to_datetime(elo_hist['timestamp'], errors='coerce')
        # Forceer alle timestamps naar tz-naive (UTC)
        if elo_hist['timestamp'].dt.tz is not None:
            elo_hist['timestamp'] = elo_hist['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
        else:
            try:
                elo_hist['timestamp'] = elo_hist['timestamp'].dt.tz_localize(None)
            except Exception:
                pass
        for _, season in seasons_df.iterrows():
            start = pd.to_datetime(season['startdatum'])
            end = pd.to_datetime(season['einddatum'])
            in_season = elo_hist[(elo_hist['timestamp'] >= start) & (elo_hist['timestamp'] <= end)]
            if not in_season.empty:
                elo_start = in_season.iloc[0]['rating']
                elo_end = in_season.iloc[-1]['rating']
                speler_info['seizoenen'].append({
                    'seizoen_naam': season['seizoen_naam'],
                    'elo_start': elo_start,
                    'elo_end': elo_end,
                    'aantal_entries': len(in_season)
                })
        if len(speler_info['seizoenen']) > 1:
            overview.append(speler_info)
    # Print overzicht
    for speler in overview:
        print(f"Speler: {speler['speler_naam']}")
        for s in speler['seizoenen']:
            print(f"  {s['seizoen_naam']}: start={s['elo_start']}, eind={s['elo_end']} (entries: {s['aantal_entries']})")
        print()
    if not overview:
        print("Geen spelers met meerdere seizoenen gevonden.")

if __name__ == "__main__":
    elo_overview_per_season()
