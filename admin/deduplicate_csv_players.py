import pandas as pd

def deduplicate_players_csv():
    path = 'csv/read/spelers.csv'
    print(f"--- DEDUPLICATIE {path} ---")
    
    df = pd.read_csv(path)
    print(f"Rijen voor: {len(df)}")
    
    # Sorteer op rating (zodat we de meest actuele rating houden bij duplicaten)
    # en drop duplicaten op naam
    df = df.sort_values('rating', ascending=False).drop_duplicates('speler_naam', keep='first')
    
    # Sorteer weer op naam voor de netheid
    df = df.sort_values('speler_naam')
    
    df.to_csv(path, index=False)
    print(f"Rijen na: {len(df)}")
    print("✅ Duplicaten verwijderd uit spelers.csv")

if __name__ == "__main__":
    deduplicate_players_csv()
