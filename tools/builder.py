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

def load_rules():
    if os.path.exists(DOCS_PATH):
        with open(DOCS_PATH, 'r') as f:
            return f.read()
    return "Regeln nicht gefunden."

def register_texture_path(texture_name):
    """
    Registriert die Textur im System, ABER erstellt KEIN Bild.
    Ergebnis: Lila-Schwarzes Muster im Spiel -> Signalisiert 'ToDo'.
    """
    # Eintrag in item_texture.json sicherstellen
    texture_def_path = os.path.join(RP_PATH, "textures", "item_texture.json")
    os.makedirs(os.path.dirname(texture_def_path), exist_ok=True)
    
    data = {"resource_pack_name": "factory_rp", "texture_name": "atlas.items", "texture_data": {}}
    if os.path.exists(texture_def_path):
        try:
            with open(texture_def_path, 'r') as f:
                data = json.load(f)
        except: pass
    
    # Wir sagen dem Spiel: "Suche das Bild hier."
    # Da wir das Bild nicht erstellen, wird das Spiel das Karomuster zeigen.
    if texture_name not in data.get("texture_data", {}):
        if "texture_data" not in data: data["texture_data"] = {}
        data["texture_data"][texture_name] = {"textures": f"textures/items/{texture_name}"}
        with open(texture_def_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"📒 Textur-Pfad registriert: {texture_name} (Datei fehlt noch absichtlich)")

def update_language_file(item_id, display_name):
    """Übersetzt item.test:id.name -> Echter Name"""
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
        print(f"📝 Name '{display_name}' gespeichert.")

def extract_info_and_fix(file_path, content):
    """Repariert NUR die Syntax, damit das Item überhaupt lädt."""
    try:
        if "minecraft:item" in content:
            # FIX 1: Version muss stimmen, sonst lädt gar nichts
            content["format_version"] = "1.21.0"
            
            comp = content["minecraft:item"].get("components", {})
            desc = content["minecraft:item"].get("description", {})
            item_id = desc.get("identifier", "")
            
            # FIX 2: Icon Syntax korrigieren (String statt Objekt)
            icon = comp.get("minecraft:icon")
            if icon:
                tex_name = icon if isinstance(icon, str) else icon.get("texture")
                
                # Syntax reparieren
                if isinstance(icon, dict):
                    comp["minecraft:icon"] = tex_name
                
                # Pfad registrieren (damit lila Box erscheint), aber NICHT erstellen
                if tex_name: register_texture_path(tex_name)

            # FIX 3: Name eintragen (Optional, hilft bei der Übersicht)
            display = comp.get("minecraft:display_name")
            if display:
                name_val = display.get("value") if isinstance(display, dict) else display
                if isinstance(display, str):
                     comp["minecraft:display_name"] = { "value": display }
                     name_val = display
                if name_val: update_language_file(item_id, name_val)
                
            return content

    except Exception as e:
        print(f"⚠️ Fix fehlgeschlagen für {file_path}: {e}")
    return content

def clean_up_old_files():
    print("🧹 CLEANUP: Lösche alte Definitionen...")
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
    print("🔧 CHECK: Manifeste...")
    rp_path = os.path.join(RP_PATH, "manifest.json")
    bp_path = os.path.join(BP_PATH, "manifest.json")
    os.makedirs(RP_PATH, exist_ok=True)
    os.makedirs(BP_PATH, exist_ok=True)

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

    bp_uuid = str(uuid.uuid4())
    if os.path.exists(bp_path):
        try:
            with open(bp_path, 'r') as f:
                d = json.load(f)
                bp_uuid = d['header']['uuid']
        except: pass

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
    for f in os.listdir(REPO_ROOT):
        if f.endswith(".mcaddon") and name in f:
            try: os.remove(f)
            except: pass

    with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        for folder in [BP_PATH, RP_PATH]:
            if os.path.exists(folder):
                folder_name = os.path.basename(folder)
                for root, _, files in os.walk(folder):
                    for file in files:
                        abs_path = os.path.join(root, file)
                        rel_path = os.path.join(folder_name, os.path.relpath(abs_path, folder))
                        zf.write(abs_path, rel_path)
    print(f"📦 Add-On erstellt: {filename}")

def main():
    print("🏭 Factory startet (No-Fake Visuals)...")
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
            
            # Repariert Syntax, aber erstellt KEINE Bilder
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
            print(f"✅ Datei: {path}")

        ver = manage_manifests()
        create_mcaddon("MeinAddon", ver)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        exit(1)

if __name__ == "__main__":
    main()
    
