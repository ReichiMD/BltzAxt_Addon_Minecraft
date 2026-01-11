import os
import json

# KONFIGURATION
NAMESPACE = "factory"

def enforce_namespace(data, logs):
    """Ersetzt rekursiv Namespaces und protokolliert Änderungen"""
    changed = False
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            new_k = k
            if ":" in k and not k.startswith("minecraft:"):
                new_k = f"{NAMESPACE}:{k.split(':')[1]}"
                if new_k != k: changed = True
            
            res_v, res_changed = enforce_namespace(v, logs)
            if res_changed: changed = True
            new_data[new_k] = res_v
        return new_data, changed
    elif isinstance(data, list):
        new_list = []
        for item in data:
            res_item, res_changed = enforce_namespace(item, logs)
            if res_changed: changed = True
            new_list.append(res_item)
        return new_list, changed
    elif isinstance(data, str):
        if ":" in data and not data.startswith("minecraft:") and not data.startswith("textures/"):
             if data not in ["1.21.0", "1.20.0", "1.12.0"]:
                new_str = f"{NAMESPACE}:{data.split(':')[1]}"
                if new_str != data:
                    # logs.append(f"🔧 ID korrigiert: {data} -> {new_str}") # Optional: sehr detailliert
                    return new_str, True
        return data, False
    else:
        return data, False

def fix_recipe(data, filename, logs):
    item_name = os.path.splitext(os.path.basename(filename))[0]
    target_id = f"{NAMESPACE}:{item_name}"
    changed = False
    
    for tag in data.keys():
        if "minecraft:recipe_" in tag and "result" in data[tag]:
            current = data[tag]["result"]
            if isinstance(current, dict):
                if current.get("item") != target_id:
                    logs.append(f"🔧 Rezept-Ergebnis korrigiert: {current.get('item')} -> {target_id}")
                    data[tag]["result"]["item"] = target_id
                    changed = True
            elif isinstance(current, str):
                if current != target_id:
                    data[tag]["result"] = target_id
                    changed = True
    return data, changed

def generate_lang_file(bp_dir, rp_dir):
    lang_entries = []
    items_dir = os.path.join(bp_dir, "items")
    if os.path.exists(items_dir):
        for f in os.listdir(items_dir):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(items_dir, f), 'r') as json_file:
                        data = json.load(json_file)
                        # Display Name suchen
                        desc = data.get("minecraft:item", {}).get("description", {})
                        ident = desc.get("identifier", "unknown")
                        
                        comps = data.get("minecraft:item", {}).get("components", {})
                        disp = comps.get("minecraft:display_name")
                        
                        if disp:
                            raw_name = disp.get("value") if isinstance(disp, dict) else disp
                            lang_entries.append(f"item.{ident}.name={raw_name}")
                except: pass

    lang_path = os.path.join(rp_dir, "texts")
    os.makedirs(lang_path, exist_ok=True)
    with open(os.path.join(lang_path, "en_US.lang"), "w") as f:
        f.write("\n".join(lang_entries))
    
    return lang_entries

def process_all(bp_dir, rp_dir):
    logs = []
    
    # 1. JSON Verarbeitung
    for root_dir in [bp_dir, rp_dir]:
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.endswith(".json") and file != "manifest.json":
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r') as f: data = json.load(f)
                        
                        # Logik anwenden
                        data, changed_ns = enforce_namespace(data, logs)
                        
                        changed_recipe = False
                        if "recipes" in path:
                            data, changed_recipe = fix_recipe(data, file, logs)
                            
                        # Speichern nur wenn nötig oder um Formatierung zu sichern
                        with open(path, 'w') as f: json.dump(data, f, indent=2)
                        
                        if changed_ns or changed_recipe:
                            logs.append(f"✅ Datei optimiert: {file}")
                        else:
                            logs.append(f"✅ Datei geprüft: {file}")
                            
                    except Exception as e:
                        logs.append(f"❌ Fehler in {file}: {e}")

    # 2. Lang File
    entries = generate_lang_file(bp_dir, rp_dir)
    for entry in entries:
        logs.append(f"✅ Spracheintrag: '{entry.split('=')[1]}'")
    
    return logs
        
