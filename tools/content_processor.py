import os
import json
import re

# KONFIGURATION
NAMESPACE = "factory"

def enforce_namespace(data):
    """Ersetzt rekursiv alle Namespaces durch 'factory:'"""
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            # Schlüssel prüfen (z.B. "minecraft:item" bleibt, aber "test:sword" wird "factory:sword")
            if ":" in k and not k.startswith("minecraft:"):
                k = f"{NAMESPACE}:{k.split(':')[1]}"
            new_data[k] = enforce_namespace(v)
        return new_data
    elif isinstance(data, list):
        return [enforce_namespace(item) for item in data]
    elif isinstance(data, str):
        # Strings prüfen (z.B. "test:my_item")
        if ":" in data and not data.startswith("minecraft:") and not data.startswith("textures/"):
             # Ausnahme für Standard-Werte
             if data not in ["1.21.0", "1.20.0", "1.12.0"]:
                return f"{NAMESPACE}:{data.split(':')[1]}"
        return data
    else:
        return data

def fix_recipe(data, filename):
    """Stellt sicher, dass das Rezept-Ergebnis existiert"""
    # Einfache Heuristik: Der Dateiname (ohne .json) ist meist die Item-ID
    item_name = os.path.splitext(os.path.basename(filename))[0]
    target_id = f"{NAMESPACE}:{item_name}"
    
    # Suche nach 'result' in shaped/shapeless recipes
    for tag in data.keys():
        if "minecraft:recipe_" in tag:
            if "result" in data[tag]:
                # Erzwinge, dass das Ergebnis dem Dateinamen entspricht
                if isinstance(data[tag]["result"], dict):
                    data[tag]["result"]["item"] = target_id
                elif isinstance(data[tag]["result"], str):
                     # Veraltetes Format, aber sicherheitshalber
                    data[tag]["result"] = target_id
    return data

def generate_lang_file(bp_dir, rp_dir):
    """Erstellt automatisch die en_US.lang basierend auf Item-Namen"""
    lang_entries = []
    
    # Scanne BP Items
    items_dir = os.path.join(bp_dir, "items")
    if os.path.exists(items_dir):
        for f in os.listdir(items_dir):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(items_dir, f), 'r') as json_file:
                        data = json.load(json_file)
                        # Suche Display Name
                        for comp in data.get("minecraft:item", {}).get("components", {}):
                            if comp == "minecraft:display_name":
                                val = data["minecraft:item"]["components"][comp]
                                raw_name = val.get("value", "Unknown") if isinstance(val, dict) else val
                                # ID extrahieren (factory:name)
                                ident = data["minecraft:item"]["description"]["identifier"]
                                lang_entries.append(f"item.{ident}.name={raw_name}")
                except Exception as e:
                    print(f"Warnung beim Lang-Scan von {f}: {e}")

    # Schreibe Datei
    lang_path = os.path.join(rp_dir, "texts")
    os.makedirs(lang_path, exist_ok=True)
    with open(os.path.join(lang_path, "en_US.lang"), "w") as f:
        f.write("\n".join(lang_entries))
        f.write("\n") # Empty line at end
    
    return len(lang_entries)

def process_all(bp_dir, rp_dir):
    """Hauptfunktion: Wendet alle Regeln auf alle Dateien an"""
    log = []
    
    # 1. Bearbeite alle JSONs im BP und RP
    for root_dir in [bp_dir, rp_dir]:
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.endswith(".json") and file != "manifest.json":
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r') as f:
                            data = json.load(f)
                        
                        # Apply Namespace Fix
                        data = enforce_namespace(data)
                        
                        # Apply Recipe Fix
                        if "recipes" in path:
                            data = fix_recipe(data, file)
                            
                        with open(path, 'w') as f:
                            json.dump(data, f, indent=4)
                            
                    except Exception as e:
                        log.append(f"Fehler in {file}: {e}")

    # 2. Lang File
    count = generate_lang_file(bp_dir, rp_dir)
    log.append(f"Sprachdatei generiert mit {count} Einträgen.")
    
    return log
  
