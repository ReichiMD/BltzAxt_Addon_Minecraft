import os
import json
import zipfile
import uuid
import shutil
from google import genai

# KONFIGURATION
API_KEY = os.environ.get("GEMINI_API_KEY")
REPO_ROOT = "."
DOCS_PATH = os.path.join(REPO_ROOT, "docs", "00_best_practices.txt")
BP_PATH = os.path.join(REPO_ROOT, "BP")
RP_PATH = os.path.join(REPO_ROOT, "RP")
OUTPUT_DIR = os.path.join(REPO_ROOT, "Addon") # Hier landen die fertigen Dateien

# GLOBALES LOGBUCH
build_log = []

def log(message):
    """Schreibt in die Konsole UND in das interne Logbuch."""
    print(message)
    build_log.append(message)

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
        log(f"📒 Textur registriert: {texture_name}")

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
        log(f"📝 Name '{display_name}' für ID '{item_id}' gespeichert.")

def extract_info_and_fix(file_path, content):
    """Repariert Item-Definitionen und ERZWINGT Namespace 'factory:'."""
    try:
        if "minecraft:item" in content:
            # FIX 1: Version erzwingen
            content["format_version"] = "1.21.0"
            
            item_data = content["minecraft:item"]
            desc = item_data.get("description", {})
            comp = item_data.get("components", {})
            
            # FIX 2: Namespace Enforcer (ID Umbenennung)
            original_id = desc.get("identifier", "unknown:item")
            short_name = original_id.split(":")[-1]
            new_id = f"factory:{short_name}"
            
            if original_id != new_id:
                desc["identifier"] = new_id
                log(f"🛡️ ID geändert: {original_id} -> {new_id}")
            
            # FIX 3: Menu Kategorie erzwingen
            desc["menu_category"] = {
                "category": "equipment",
                "group": "itemGroup.name.sword" 
            }
            item_data["description"] = desc

            # FIX 4: Icon Syntax
            icon = comp.get("minecraft:icon")
            if icon:
                tex_name = icon if isinstance(icon, str) else icon.get("texture")
                if isinstance(icon, dict):
                    comp["minecraft:icon"] = tex_name
                if tex_name: register_texture_path(tex_name)

            # FIX 5: Name & Lang
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
        log(f"⚠️ Fix fehlgeschlagen für {file_path}: {e}")
    return content

def clean_up_old_files():
    log("🧹 CLEANUP: Lösche alte JSONs...")
    folders = [os.path.join(BP_PATH, "items"), os.path.join(BP_PATH, "recipes")]
    for folder in folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)

def get_smart_model_name(client):
    try:
        all_models = list(client.models.list())
        flash = [m.name for m in all_models if "flash" in m.name.lower()]
        best = flash[0] if flash else "gemini-1.5-flash"
        return best.replace("models/", "") if best.startswith("models/") else best
    except: return "gemini-1.5-flash"

def manage_manifests():
    log("🔧 CHECK: Synchronisiere Manifeste...")
    rp_path = os.path.join(RP_PATH, "manifest.json")
    bp_path = os.path.join(BP_PATH, "manifest.json")
    os.makedirs(RP_PATH, exist_ok=True)
    os.makedirs(BP_PATH, exist_ok=True)

    # 1. RP (Resource Pack)
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
    
    log(f"📄 RP UUID: {rp_uuid} | Version: {rp_version}")

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

    # 2. BP (Behavior Pack)
    bp_uuid = str(uuid.uuid4())
    if os.path.exists(bp_path):
        try:
            with open(bp_path, 'r') as f:
                d = json.load(f)
                bp_uuid = d['header']['uuid']
        except: pass

    log(f"📄 BP UUID: {bp_uuid} | Dependency Exact: {rp_version}")

    # FIX: Exakte Versionsübereinstimmung für Dependency
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
        
    return rp_version

def create_mcaddon(name, version):
    v_str = f"{version[0]}.{version[1]}.{version[2]}"
    filename = f"{name}_v{v_str}.mcaddon"
    log_filename = f"build_log_v{v_str}.txt"
    
    # Ordner 'Addon' vorbereiten
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. Alte Dateien im Root löschen (Aufräumen)
    for f in os.listdir(REPO_ROOT):
        if f.endswith(".mcaddon") and name in f:
            try: os.remove(f)
            except: pass

    # 2. Alte Dateien im Addon-Ordner löschen (Damit nur das Neueste da ist)
    for f in os.listdir(OUTPUT_DIR):
        file_path = os.path.join(OUTPUT_DIR, f)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Fehler beim Aufräumen von {OUTPUT_DIR}: {e}")

    # Pfade für neue Dateien
    full_mcaddon_path = os.path.join(OUTPUT_DIR, filename)
    full_log_path = os.path.join(OUTPUT_DIR, log_filename)

    # Log-Datei in den Ordner schreiben
    with open(full_log_path, "w") as f:
        f.write("\n".join(build_log))

    # Add-On Packen
    with zipfile.ZipFile(full_mcaddon_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Ordner BP und RP packen
        for folder in [BP_PATH, RP_PATH]:
            if os.path.exists(folder):
                folder_name = os.path.basename(folder)
                for root, _, files in os.walk(folder):
                    for file in files:
                        abs_path = os.path.join(root, file)
                        rel_path = os.path.join(folder_name, os.path.relpath(abs_path, folder))
                        zf.write(abs_path, rel_path)
        
        # Log-Datei auch IN das Zip packen (für Handy-User bequem)
        zf.write(full_log_path, log_filename)
        
    log(f"📦 FERTIG! Dateien gespeichert in Ordner: {OUTPUT_DIR}")
    log(f"   - Addon: {filename}")
    log(f"   - Log:   {log_filename}")

def main():
    log("🏭 Factory startet (Organizer Mode)...")
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
            
            # FIX & ENFORCE
            content = extract_info_and_fix(path, content)
            
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
            log(f"✅ Datei: {path}")

        ver = manage_manifests()
        create_mcaddon("MeinAddon", ver)

    except Exception as e:
        log(f"❌ ERROR: {e}")
        exit(1)

if __name__ == "__main__":
    main()
                    
