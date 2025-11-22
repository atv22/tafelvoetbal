import pandas as pd
import firestore_service as db

def check_elo_per_season():
    """
    Controleer na ELO-herberekening of alle spelers die in een seizoen spelen, ook daadwerkelijk een ELO krijgen in elk seizoen waarin ze meedoen.
    Rapporteer ontbrekende ELO's.
    """
    seasons_df = db.get_seasons()
    matches_df = db.get_matches()
    players_df = db.get_players()
    missing_elo = []
    for _, season in seasons_df.iterrows():
        start = pd.to_datetime(season['startdatum'])
        end = pd.to_datetime(season['einddatum'])
        season_matches = matches_df[(matches_df['timestamp'] >= start) & (matches_df['timestamp'] <= end)]
        # Spelers die in dit seizoen gespeeld hebben
        season_players = set()
        for col in ['thuis_1', 'thuis_2', 'uit_1', 'uit_2']:
            if col in season_matches.columns:
                season_players.update(season_matches[col].dropna().astype(str).tolist())
        for speler in season_players:
            elo_hist = db.get_elo_history(_ttl=60, speler_naam=speler)
            if elo_hist.empty:
                missing_elo.append((speler, season['seizoen_naam']))
            else:
                # Check of er een ELO entry is binnen de seizoensgrenzen
                elo_hist['timestamp'] = pd.to_datetime(elo_hist['timestamp'], errors='coerce')
                # Forceer alle timestamps naar tz-naive (UTC)
                if elo_hist['timestamp'].dt.tz is not None:
                    elo_hist['timestamp'] = elo_hist['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
                else:
                    try:
                        elo_hist['timestamp'] = elo_hist['timestamp'].dt.tz_localize(None)
                    except Exception:
                        pass
                in_season = elo_hist[(elo_hist['timestamp'] >= start) & (elo_hist['timestamp'] <= end)]
                if in_season.empty:
                    missing_elo.append((speler, season['seizoen_naam']))
    if missing_elo:
        print("[CHECK] Spelers zonder ELO in seizoen:")
        for speler, seizoen in missing_elo:
            print(f"  {speler} in {seizoen}")
    else:
        print("[CHECK] Alle spelers hebben een ELO in elk seizoen waarin ze speelden.")

if __name__ == "__main__":
    check_elo_per_season()
