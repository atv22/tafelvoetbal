import os

def brute_force_fix_encoding():
    csv_dir = 'csv/read'
    # We zoeken de byte-representatie van het foute teken (vaak 0xEF 0xBF 0xBD in UTF-8 of 0xFD in Latin-1)
    # Gegeven de output 'LauraThni', zoeken we naar substrings die LauraTh bevatten en niet Thöni zijn.
    
    target = "LauraThöni"
    
    for filename in os.listdir(csv_dir):
        if not filename.endswith('.csv'): continue
        
        path = os.path.join(csv_dir, filename)
        print(f"Fixing {filename}...")
        
        # Lees als bytes om encoding issues te omzeilen
        with open(path, 'rb') as f:
            content = f.read()
            
        # Definieer wat we willen zoeken (verschillende mogelijke foute bytes)
        # We zoeken naar de prefix 'LauraTh' en kijken wat er volgt
        try:
            # Probeer verschillende encodings om de tekst te vinden
            text = content.decode('utf-8', errors='replace')
            if 'LauraTh' in text:
                import re
                # Zoek 'LauraTh' gevolgd door 1 of 2 niet-alfanumerieke tekens en dan 'ni'
                # Of gewoon alles wat lijkt op LauraTh...ni en niet de goede is
                # We doen een simpele regex replace op de gedecodeerde tekst
                new_text = re.sub(r'LauraTh.ni', target, text)
                new_text = re.sub(r'LauraTh..ni', target, new_text)
                
                if new_text != text:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_text)
                    print(f"   ✅ {filename} aangepast via regex.")
                else:
                    print(f"   ℹ️ Geen wijzigingen nodig in {filename}.")
        except Exception as e:
            print(f"   ❌ Fout in {filename}: {e}")

if __name__ == "__main__":
    brute_force_fix_encoding()
