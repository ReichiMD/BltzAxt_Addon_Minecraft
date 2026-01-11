import os
import json
import zipfile
import uuid
import shutil
from google import genai
import datetime

# KONFIGURATION
API_KEY = os.environ.get("GEMINI_API_KEY")
REPO_ROOT = "."
DOCS_PATH = os.path.join(REPO_ROOT, "docs", "00_best_practices.txt")
BP_PATH = os.path.join(REPO_ROOT, "BP")
RP_PATH = os.path.join(REPO_ROOT, "RP")
OUTPUT_DIR = os.path.join(REPO_ROOT, "Addon")

# SPEICHER FÜR DAS LOGBUCH
summary_log = []     # Der saubere Verlauf (oben)
appendix_log = []    # Der komplette Code (unten)
warnings_count = 0
errors_count = 0

def log(message, level="INFO"):
    """Schreibt in den sauberen Verlauf (Oben)."""
    global warnings_count, errors_count
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    icon = "ℹ️"
    if level == "WARN": 
        icon = "⚠️"
        warnings_count += 1
    elif level == "ERROR": 
        icon = "❌"
        errors_count += 1
    elif level == "SUCCESS":
        icon = "✅"
    elif level == "FIX":
        icon = "🔧"

    entry = f"[{timestamp}] {icon} {message}"
    print(entry) # Auch in der Konsole anzeigen
    summary_log.append(entry)

def append_code_to_log(filename, content):
    """Speichert den Code NUR für den Anhang (Unten)."""
    pretty_json = json.dumps(content, indent=2)
    appendix_log.append(f"\n===========================================")
    appendix_log.append(f"📄 DATEI: {filename}")
    appendix_log.append(f"===========================================\n")
    appendix_log.append(pretty_json)

def generate_ascii_tree(startpath):
    """Erstellt den Ordner-Baum."""
    tree_str = "\n\n===========================================\n"
    tree_str += "🌳 ORDNER STRUKTUR (Visualisierung)\n"
    tree_str += "===========================================\nAddon/\n"
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        base_name = os.path.basename(root)
        if base_name == ".": continue
        tree_str += '{}{}/\n'.format(indent, base_name)
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            tree_str += '{}{}\n'.format(subindent, f)
    return tree_str

def load_rules():
    if os.path.exists(DOCS_PATH):
        with open(DOCS_PATH, 'r') as f:
            return f.read()
    return "Regeln nicht gefunden."

def register_texture_path(texture_name):
    texture_def_path = os.path.join(RP_PATH, "textures", "item_texture.json")
    os.makedirs(os.path.dirname(texture_def_path), exist_ok=True)
    
    data = {"resource_pack_name": "factory_rp", "texture_name": "atlas.items", "texture_data": {}}
    if os.path.exists(texture_def_path):
        try:
            with open(texture_def_path, 'r') as f:
                data = json.load(f)
        except: pass
    
    if texture_name not in data.get("texture_data", {}):
        if "texture_data" not in data: data["texture_data"] = {}
        data["texture_data"][texture_name] = {"textures": f"textures/items/{texture_name}"}
        with open(texture_def_path, 'w') as f:
            json.dump(data, f, indent=4)
        log(f"Textur '{texture_name}' neu registriert (Bilddatei fehlt noch -> Lila/Schwarz).", "INFO")
        append_code_to_log("RP/textures/item_texture.json", data)
    else:
        # Nur anhängen, nicht loggen (damit der Verlauf sauber bleibt)
        append_code_to_log("RP/textures/item_texture.json", data)

def update_language_file(item_id, display_name):
    lang_path = os.path.join(RP_PATH, "texts", "en_US.lang")
    os.makedirs(os.path.dirname(lang_path), exist_ok=True)
    
    key = f"item.{item_id}.name"
    line_to_add = f"{key}={display_name}\n"
    
    current_content = ""
    if os.path.exists(lang_path):
        with open(lang_path, 'r') as f:
            current_content = f.read()
            
    if key not in current_content:
        with open(lang_path, 'a') as f:
            f.write(line_to_add)
        log(f"Sprachdatei Update: {key} -> '{display_name}'", "SUCCESS")
        appendix_log.append(f"\n[LANG FILE UPDATE]\n{line_to_add}")

def extract_info_and_fix(file_path, content):
    """Repariert Code und loggt Fixes im Verlauf."""
    try:
        if "minecraft:item" in content:
            item_data = content["minecraft:item"]
            desc = item_data.get("description", {})
            comp = item_data.get("components", {})
            
            # 1. VERSION
            old_ver = content.get("format_version", "old")
            if old_ver != "1.21.0":
                log(f"Format-Version korrigiert: {old_ver} -> 1.21.0", "FIX")
                content["format_version"] = "1.21.0"
            
            # 2. ID ENFORCEMENT
            original_id = desc.get("identifier", "unknown:item")
            short_name = original_id.split(":")[-1]
            new_id = f"factory:{short_name}"
            
            if original_id != new_id:
                desc["identifier"] = new_id
                log(f"ID korrigiert: '{original_id}' zu '{new_id}' (Namespace Enforcement)", "FIX")

            # 3. KREATIV MENÜ
            if "menu_category" not in desc:
                desc["menu_category"] = {"category": "equipment", "group": "itemGroup.name.sword"}
                item_data["description"] = desc
                log("Kreativ-Menü Eintrag fehlte und wurde hinzugefügt.", "FIX")

            # 4. ICON
            icon = comp.get("minecraft:icon")
            if icon:
                tex_name = icon if isinstance(icon, str) else icon.get("texture")
                if isinstance(icon, dict):
                    comp["minecraft:icon"] = tex_name
                    log("Icon-Syntax korrigiert (Objekt -> String).", "FIX")
                if tex_name: register_texture_path(tex_name)

            # 5. NAME
            display = comp.get("minecraft:display_name")
            if display:
                name_val = display.get("value") if isinstance(display, dict) else display
                if isinstance(display, str):
                     comp["minecraft:display_name"] = { "value": display }
                     name_val = display
                if name_val: update_language_file(new_id, name_val)
            
            content["minecraft:item"] = item_data
            return content

    except Exception as e:
        log(f"Fehler bei Analyse von {file_path}: {e}", "ERROR")
    return content

def clean_up_old_files():
    log("Starte Aufräumarbeiten...", "INFO")
    folders = [os.path.join(BP_PATH, "items"), os.path.join(BP_PATH, "recipes")]
    for folder in folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)

def get_smart_model_name(client):
    try:
        all_models = list(client.models.list())
        flash = [m.name for m in all_models if "flash" in m.name.lower()]
        best = flash[0] if flash else "gemini-1.5-flash"
        clean = best.replace("models/", "") if best.startswith("models/") else best
        log(f"Modell ausgewählt: {clean}", "SUCCESS")
        return clean
    except: return "gemini-1.5-flash"

def manage_manifests():
    # Wir loggen im Verlauf nur das Wichtigste, Details kommen in den Anhang
    rp_path = os.path.join(RP_PATH, "manifest.json")
    bp_path = os.path.join(BP_PATH, "manifest.json")
    os.makedirs(RP_PATH, exist_ok=True)
    os.makedirs(BP_PATH, exist_ok=True)

    # RP
    rp_uuid = str(uuid.uuid4())
    rp_version = [1, 0, 0]
    if os.path.exists(rp_path):
        try:
            with open(rp_path, 'r') as f:
                d = json.load(f)
                rp_uuid = d['header']['uuid']
                rp_version = d['header']['version']
                rp_version[2] += 1
        except: pass

    rp_data = {
        "format_version": 2,
        "header": {
            "name": "Factory Addon RP",
            "description": "Visuals",
            "uuid": rp_uuid,
            "version": rp_version,
            "min_engine_version": [1, 21, 0]
        },
        "modules": [{"type": "resources", "uuid": str(uuid.uuid4()), "version": rp_version}]
    }
    with open(rp_path, 'w') as f: json.dump(rp_data, f, indent=4)
    append_code_to_log("RP/manifest.json", rp_data)

    # BP
    bp_uuid = str(uuid.uuid4())
    if os.path.exists(bp_path):
        try:
            with open(bp_path, 'r') as f:
                d = json.load(f)
                bp_uuid = d['header']['uuid']
        except: pass

    log(f"Resource Pack: UUID={rp_uuid}, Version={rp_version}", "INFO")

    bp_data = {
        "format_version": 2,
        "header": {
            "name": "Factory Addon BP",
            "description": "Logic",
            "uuid": bp_uuid,
            "version": rp_version,
            "min_engine_version": [1, 21, 0]
        },
        "modules": [{"type": "data", "uuid": str(uuid.uuid4()), "version": rp_version}],
        "dependencies": [{"uuid": rp_uuid, "version": rp_version}]
    }
    with open(bp_path, 'w') as f: json.dump(bp_data, f, indent=4)
    append_code_to_log("BP/manifest.json", bp_data)
        
    return rp_version

def create_mcaddon(name, version):
    v_str = f"{version[0]}.{version[1]}.{version[2]}"
    filename = f"{name}_v{v_str}.mcaddon"
    log_filename = f"build_log_v{v_str}.txt"
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Cleanup Output (Hier war der Fehler!)
    for f in os.listdir(OUTPUT_DIR):
        file_path = os.path.join(OUTPUT_DIR, f)
        try: 
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except: pass

    full_mcaddon_path = os.path.join(OUTPUT_DIR, filename)
    full_log_path = os.path.join(OUTPUT_DIR, log_filename)

    # Abschluss im Verlauf
    log("--- ABSCHLUSS-BERICHT ---", "INFO")
    if errors_count == 0:
        log("Build erfolgreich! Keine Fehler, keine Warnungen.", "SUCCESS")
    else:
        log(f"Build abgeschlossen mit {errors_count} Fehlern.", "WARN")

    # FILE ZUSAMMENBAUEN: 1. Verlauf | 2. Baum | 3. Code
    full_content = []
    full_content.append("--- VERLAUF (SUMMARY) ---")
    full_content.extend(summary_log)
    
    # Baum generieren
    tree_view = generate_ascii_tree(BP_PATH) + generate_ascii_tree(RP_PATH)
    full_content.append(tree_view)
    
    full_content.append("\n\n===========================================")
    full_content.append("💻 COMPLETE CODE DUMP (APPENDIX)")
    full_content.append("===========================================")
    full_content.extend(appendix_log)

    # Schreiben
    with open(full_log_path, "w", encoding='utf-8') as f:
        f.write("\n".join(full_content))

    # Zip
    with zipfile.ZipFile(full_mcaddon_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for folder in [BP_PATH, RP_PATH]:
            if os.path.exists(folder):
                folder_name = os.path.basename(folder)
                for root, _, files in os.walk(folder):
                    for file in files:
                        abs_path = os.path.join(root, file)
                        rel_path = os.path.join(folder_name, os.path.relpath(abs_path, folder))
                        zf.write(abs_path, rel_path)
        zf.write(full_log_path, log_filename)
        
    log(f"Fertig! Dateien in: {OUTPUT_DIR}", "SUCCESS")

def main():
    log("🏭 Factory Start (Clean Summary + Full Appendix)...", "INFO")
    if not API_KEY: exit(1)
    
    clean_up_old_files()
    
    issue_body = os.environ.get("ISSUE_BODY", "Test Item")
    client = genai.Client(api_key=API_KEY)
    model = get_smart_model_name(client)
    
    prompt = f"""
    Du bist ein Minecraft Bedrock Experte (Version 1.21.0+).
    AUFGABE: {issue_body}
    REGELN: {load_rules()}
    
    Output NUR als JSON-Liste.
    """
    
    try:
        response = client.models.generate_content(model=model, contents=prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        start, end = text.find('['), text.rfind(']') + 1
        text = text[start:end]
        
        files = json.loads(text)
        
        for item in files:
            if "path" not in item: continue
            path = item['path']
            if ".." in path: continue
            
            full_path = os.path.join(REPO_ROOT, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            content = item['content']
            
            # FIX & LOGGING
            content = extract_info_and_fix(path, content)
            
            # Code für Anhang speichern (Silent)
            append_code_to_log(path, content)
            
            if "item_texture.json" in path and os.path.exists(full_path):
                try:
                    with open(full_path, 'r') as f:
                        existing = json.load(f)
                        if "texture_data" in content:
                            existing.setdefault("texture_data", {}).update(content["texture_data"])
                            content = existing
                except: pass

            with open(full_path, 'w') as f:
                json.dump(content, f, indent=4)
            log(f"Datei geschrieben: {path}", "SUCCESS")

        ver = manage_manifests()
        create_mcaddon("MeinAddon", ver)

    except Exception as e:
        log(f"CRASH: {e}", "ERROR")
        exit(1)

if __name__ == "__main__":
    main()
    
