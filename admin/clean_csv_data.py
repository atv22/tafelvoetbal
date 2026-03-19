import pandas as pd
import os
import glob

def clean_csv_files():
    csv_dir = 'csv/read'
    print(f"--- START OPSCHONEN CSV BESTANDEN IN {csv_dir} ---")
    
    # Definieer de mappings
    replacements = {
        'Fre': 'Fré',
        'Stephan': 'Stefan'
    }
    
    # Voor de LauraThni fix gebruiken we een speciale check ivm encoding
    def fix_laura_name(name):
        if not isinstance(name, str): return name
        # Als de naam 'Laura' bevat en 'Th' maar niet de correcte 'Thöni'
        if 'Laura' in name and 'Th' in name and 'Thöni' not in name:
            return 'LauraThöni'
        return name

    # Bestanden om te verwerken
    files = glob.glob(os.path.join(csv_dir, "*.csv"))
    
    for file_path in files:
        filename = os.path.basename(file_path)
        print(f"\nVerwerken van {filename}...")
        
        try:
            # Probeer in te lezen (detecteer encoding of gebruik utf-8)
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding='latin1')
            
            original_shape = df.shape
            
            # Pas replacements toe op alle object/string kolommen
            for col in df.columns:
                if df[col].dtype == 'object':
                    # 1. Standaard mappings (Fre, Stephan)
                    df[col] = df[col].replace(replacements)
                    
                    # 2. LauraThni fix via functie
                    df[col] = df[col].apply(fix_laura_name)
                    
                    # 3. Verwijder Niemand variaties uit spelers.csv
                    if filename == 'spelers.csv' and col == 'speler_naam':
                        niemand_mask = df[col].str.lower().str.strip().isin(['niemandin', 'niemanduit', 'niemand', 'none', ''])
                        df = df[~niemand_mask]

            # Sla het bestand weer op als UTF-8
            df.to_csv(file_path, index=False, encoding='utf-8')
            print(f"   ✅ {filename} opgeslagen. (Rijen: {original_shape[0]} -> {df.shape[0]})")
            
        except Exception as e:
            print(f"   ❌ Fout bij verwerken van {filename}: {e}")

    print("\n--- CSV OPSCHONING VOLTOOID ---")

if __name__ == "__main__":
    clean_csv_files()
