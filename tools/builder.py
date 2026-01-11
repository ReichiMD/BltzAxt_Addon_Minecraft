import os
import json
import zipfile
import uuid
import shutil
from google import genai
import datetime

# ==========================================
# ⚙️ KONFIGURATION
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY")
REPO_ROOT = "."
DOCS_PATH = os.path.join(REPO_ROOT, "docs", "00_best_practices.txt")
BP_PATH = os.path.join(REPO_ROOT, "BP")
RP_PATH = os.path.join(REPO_ROOT, "RP")
OUTPUT_DIR = os.path.join(REPO_ROOT, "Addon")
ALLOW_SCRIPTS = False 

# LOG SYSTEM
summary_log = []     
appendix_log = []    
warnings_count = 0
errors_count = 0

def log(message, level="INFO"):
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
    print(entry)
    summary_log.append(entry)

def append_code_to_log(filename, content):
    pretty_json = json.dumps(content, indent=2)
    appendix_log.append(f"\n===========================================\n📄 DATEI: {filename}\n===========================================\n{pretty_json}")

def generate_ascii_tree(startpath):
    tree_str = "\n\n===========================================\n🌳 ORDNER STRUKTUR\n===========================================\nAddon/\n"
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
        with open(DOCS_PATH, 'r') as f: return f.read()
    return "Regeln nicht gefunden."

# HELFER
def register_texture_path(texture_name):
    texture_def_path = os.path.join(RP_PATH, "textures", "item_texture.json")
    os.makedirs(os.path.dirname(texture_def_path), exist_ok=True)
    data = {"resource_pack_name": "factory_rp", "texture_name": "atlas.items", "texture_data": {}}
    if os.path.exists(texture_def_path):
        try:
            with open(texture_def_path, 'r') as f: data = json.load(f)
        except: pass
    
    if texture_name not in data.get("texture_data", {}):
        if "texture_data" not in data: data["texture_data"] = {}
        data["texture_data"][texture_name] = {"textures": f"textures/items/{texture_name}"}
        with open(texture_def_path, 'w') as f: json.dump(data, f, indent=4)
        log(f"Textur '{texture_name}' registriert.", "INFO")
        append_code_to_log("RP/textures/item_texture.json", data)
    else:
        append_code_to_log("RP/textures/item_texture.json", data)

def update_language_file(item_id, display_name):
    lang_path = os.path.join(RP_PATH, "texts", "en_US.lang")
    os.makedirs(os.path.dirname(lang_path), exist_ok=True)
    key = f"item.{item_id}.name"
    line = f"{key}={display_name}\n"
    current = ""
    if os.path.exists(lang_path):
        with open(lang_path, 'r') as f: current = f.read()
    if key not in current:
        with open(lang_path, 'a') as f: f.write(line)
        log(f"Spracheintrag: '{display_name}'", "SUCCESS")
        appendix_log.append(f"\n[LANG]\n{line}")

def extract_info_and_fix(file_path, content):
    try:
        if "minecraft:item" in content:
            item_data = content["minecraft:item"]
            desc = item_data.get("description", {})
            comp = item_data.get("components", {})
            
            # 1. Version Force
            if content.get("format_version") != "1.21.0":
                content["format_version"] = "1.21.0"
                log("Format auf 1.21.0 gesetzt.", "FIX")
            
            # 2. Namespace Force
            orig_id = desc.get("identifier", "unknown:item")
            short = orig_id.split(":")[-1]
            new_id = f"factory:{short}"
            if orig_id != new_id:
                desc["identifier"] = new_id
                log(f"ID korrigiert: {orig_id} -> {new_id}", "FIX")

            # 3. Creative Menu Force
            desc["menu_category"] = {"category": "equipment", "group": "itemGroup.name.sword"}
            item_data["description"] = desc

            # 4. Icon & Name
            icon = comp.get("minecraft:icon")
            if icon:
                tname = icon if isinstance(icon, str) else icon.get("texture")
                if isinstance(icon, dict): comp["minecraft:icon"] = tname
                if tname: register_texture_path(tname)

            display = comp.get("minecraft:display_name")
            if display:
                val = display.get("value") if isinstance(display, dict) else display
                if isinstance(display, str): comp["minecraft:display_name"] = {"value": display}; val = display
                if val: update_language_file(new_id, val)
            
            content["minecraft:item"] = item_data
            return content
    except Exception as e:
        log(f"Fehler bei Fix: {e}", "ERROR")
    return content

def clean_up_old_files():
    log("Lösche alte Dateien (BP/items, BP/recipes)...", "INFO")
    folders = [os.path.join(BP_PATH, "items"), os.path.join(BP_PATH, "recipes")]
    if not ALLOW_SCRIPTS: folders.append(os.path.join(BP_PATH, "scripts"))
    for f in folders:
        if os.path.exists(f): shutil.rmtree(f)

def get_model(client):
    try:
        flash = [m.name for m in client.models.list() if "flash" in m.name.lower()]
        best = flash[0] if flash else "gemini-1.5-flash"
        return best.replace("models/", "") if best.startswith("models/") else best
    except: return "gemini-1.5-flash"

def manage_manifests():
    rp_path = os.path.join(RP_PATH, "manifest.json")
    bp_path = os.path.join(BP_PATH, "manifest.json")
    os.makedirs(RP_PATH, exist_ok=True); os.makedirs(BP_PATH, exist_ok=True)

    rp_uuid = str(uuid.uuid4()); rp_ver = [1, 0, 0]
    if os.path.exists(rp_path):
        try:
            with open(rp_path) as f: d=json.load(f); rp_uuid=d['header']['uuid']; rp_ver=d['header']['version']; rp_ver[2]+=1
        except: pass

    rp_data = {
        "format_version": 2,
        "header": {"name": "Factory RP", "description": "Visuals", "uuid": rp_uuid, "version": rp_ver, "min_engine_version": [1, 21, 0]},
        "modules": [{"type": "resources", "uuid": str(uuid.uuid4()), "version": rp_ver}]
    }
    with open(rp_path, 'w') as f: json.dump(rp_data, f, indent=4)
    append_code_to_log("RP/manifest.json", rp_data)

    bp_uuid = str(uuid.uuid4())
    if os.path.exists(bp_path):
        try:
            with open(bp_path) as f: d=json.load(f); bp_uuid=d['header']['uuid']
        except: pass

    log(f"Manifest Update: V {rp_ver}", "INFO")

    bp_data = {
        "format_version": 2,
        "header": {"name": "Factory BP", "description": "Logic", "uuid": bp_uuid, "version": rp_ver, "min_engine_version": [1, 21, 0]},
        "modules": [{"type": "data", "uuid": str(uuid.uuid4()), "version": rp_ver}],
        "dependencies": [{"uuid": rp_uuid, "version": rp_ver}]
    }
    with open(bp_path, 'w') as f: json.dump(bp_data, f, indent=4)
    append_code_to_log("BP/manifest.json", bp_data)
    return rp_ver

def create_mcaddon(name, version):
    v_str = f"{version[0]}.{version[1]}.{version[2]}"
    filename = f"{name}_v{v_str}.mcaddon"
    logname = f"build_log_v{v_str}.txt"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Cleanup Output
    for f in os.listdir(OUTPUT_DIR):
        try: os.unlink(os.path.join(OUTPUT_DIR, f))
        except: pass

    full_log_path = os.path.join(OUTPUT_DIR, logname)
    
    # Abschluss
    log("--- ABSCHLUSS ---", "INFO")
    if errors_count == 0 and warnings_count == 0: log("Build Sauber!", "SUCCESS")
    else: log(f"Build Warnungen: {warnings_count} | Fehler: {errors_count}", "WARN")

    full_content = ["--- VERLAUF (SUMMARY) ---"] + summary_log + [generate_ascii_tree(BP_PATH) + generate_ascii_tree(RP_PATH)] + ["\n💻 CODE DUMP"] + appendix_log
    
    with open(full_log_path, "w", encoding='utf-8') as f: f.write("\n".join(full_content))

    zip_path = os.path.join(OUTPUT_DIR, filename)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for folder in [BP_PATH, RP_PATH]:
            if os.path.exists(folder):
                for root, _, files in os.walk(folder):
                    for file in files:
                        abs = os.path.join(root, file)
                        rel = os.path.join(os.path.basename(folder), os.path.relpath(abs, folder))
                        zf.write(abs, rel)
        zf.write(full_log_path, logname)
    log(f"Fertig: {OUTPUT_DIR}", "SUCCESS")

def main():
    log("🏭 Factory Start (Data Detective Mode)...", "INFO")
    if not API_KEY: exit(1)
    clean_up_old_files()
    
    issue_body = "Erstelle ein Obsidian Schwert (obsidian_sword) mit 10 Schaden."
    client = genai.Client(api_key=API_KEY)
    
    prompt = f"""
    Du bist ein Minecraft Bedrock Experte (1.21.0).
    AUFGABE: {issue_body}
    REGELN: {load_rules()}
    
    Output NUR als JSON-Liste.
    """
    
    try:
        resp = client.models.generate_content(model=get_model(client), contents=prompt)
        text = resp.text.replace("```json", "").replace("```", "").strip()
        start, end = text.find('['), text.rfind(']') + 1
        files = json.loads(text[start:end])
        
        if len(files) == 0:
            log("KI hat 0 Dateien geliefert! CRITICAL ERROR.", "ERROR")
        
        for item in files:
            path = ""
            content = {}

            # 🕵️‍♂️ DETEKTIV-MODUS: Pfad erraten, wenn er fehlt
            if "path" in item:
                path = item["path"]
                content = item["content"]
            elif "minecraft:item" in item:
                # Aha! Die KI hat direkt das Item geschickt ohne "path" Wrapper
                content = item
                # Wir suchen den Identifier um den Pfad zu bauen
                try:
                    raw_id = content["minecraft:item"]["description"]["identifier"]
                    name = raw_id.split(":")[-1]
                    path = f"BP/items/{name}.json"
                    log(f"Pfad rekonstruiert aus Inhalt: {path}", "FIX")
                except:
                    log("Konnte Pfad nicht erraten. Überspringe.", "WARN")
                    continue
            else:
                log("Unbekanntes Datenformat. Überspringe.", "WARN")
                continue

            if not ALLOW_SCRIPTS and (".js" in path or "scripts" in path):
                log(f"Skript blockiert: {path}", "WARN"); continue
            
            full = os.path.join(REPO_ROOT, path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            content = extract_info_and_fix(path, content)
            append_code_to_log(path, content)
            
            # Merge Texture Defs
            if "item_texture.json" in path and os.path.exists(full):
                try: 
                    with open(full) as f: 
                        ex = json.load(f)
                        ex.setdefault("texture_data", {}).update(content.get("texture_data", {}))
                        content = ex
                except: pass

            with open(full, 'w') as f: json.dump(content, f, indent=4)
            log(f"Datei erstellt: {path}", "SUCCESS")

        ver = manage_manifests()
        create_mcaddon("MeinAddon", ver)

    except Exception as e:
        log(f"CRASH: {e}", "ERROR")
        exit(1)

if __name__ == "__main__":
    main()
            
