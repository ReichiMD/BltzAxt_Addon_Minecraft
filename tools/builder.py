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

def create_dummy_texture(texture_name):
    """Erstellt ein 16x16 PNG (Schwarz), falls es fehlt."""
    # Textur-Pfad muss im RP sein
    texture_path = os.path.join(RP_PATH, "textures", "items", f"{texture_name}.png")
    os.makedirs(os.path.dirname(texture_path), exist_ok=True)
    
    if not os.path.exists(texture_path):
        # Minimaler PNG Header + 1 Pixel
        minimal_png = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\rIDATx\x9cc\x60\x60\x60\x00\x00\x00\x05\x00\x01\x0d\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        with open(texture_path, 'wb') as f:
            f.write(minimal_png)
        print(f"🎨 Auto-Textur erstellt: {texture_name}.png")
        
    # Eintrag in item_texture.json sicherstellen
    texture_def_path = os.path.join(RP_PATH, "textures", "item_texture.json")
    os.makedirs(os.path.dirname(texture_def_path), exist_ok=True)
    
    data = {"resource_pack_name": "factory_rp", "texture_name": "atlas.items", "texture_data": {}}
    if os.path.exists(texture_def_path):
        try:
            with open(texture_def_path, 'r') as f:
                data = json.load(f)
        except: pass
    
    # Eintrag hinzufügen, wenn er fehlt
    if texture_name not in data.get("texture_data", {}):
        if "texture_data" not in data: data["texture_data"] = {}
        data["texture_data"][texture_name] = {"textures": f"textures/items/{texture_name}"}
        with open(texture_def_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"📒 Textur registriert: {texture_name}")

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
        print(f"📝 Name '{display_name}' für {item_id} gespeichert.")

def extract_info_and_fix(file_path, content):
    """
    Analysiert das generierte JSON. 
    Wenn es ein Item ist, extrahieren wir Icon und Name
    und erstellen automatisch die fehlenden Dateien.
    """
    try:
        # Prüfen ob es ein Item ist (Format 1.21.0)
        if "minecraft:item" in content:
            comp = content["minecraft:item"].get("components", {})
            desc = content["minecraft:item"].get("description", {})
            
            # 1. ID holen
            item_id = desc.get("identifier", "")
            
            # 2. Icon holen & Textur erstellen
            icon = comp.get("minecraft:icon")
            if icon and isinstance(icon, str):
                create_dummy_texture(icon)
            elif icon and isinstance(icon, dict) and "texture" in icon:
                # Falls KI doch ein Objekt schreibt, fangen wir das ab
                create_dummy_texture(icon["texture"])

            # 3. Name holen & Lang File schreiben
            display = comp.get("minecraft:display_name")
            if display and isinstance(display, dict) and "value" in display:
                update_language_file(item_id, display["value"])
            elif display and isinstance(display, str):
                update_language_file(item_id, display)
                
    except Exception as e:
        print(f"⚠️ Konnte Item-Info nicht extrahieren: {e}")

def clean_up_old_files():
    print("🧹 CLEANUP: Lösche alte Definitionen...")
    # Wir löschen Items und Rezepte, damit keine veralteten Dateien (mit minecraft:weapon) übrig bleiben
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
    print("🏭 Factory startet (Auto-Extract Fix)...")
    if not API_KEY: exit(1)
    
    clean_up_old_files()
    
    issue_body = os.environ.get("ISSUE_BODY", "Test Item")
    client = genai.Client(api_key=API_KEY)
    model = get_smart_model_name(client)
    
    # AGGRESSIVER PROMPT gegen veraltete Syntax
    prompt = f"""
    Du bist ein Minecraft Bedrock Experte (Version 1.21.0+).
    AUFGABE: {issue_body}
    REGELN: {load_rules()}
    
    🚨 WICHTIGE VERBOTE (STRIKT EINHALTEN):
    1. NIEMALS 'minecraft:weapon' benutzen! Das ist deprecated. Nutze Komponenten.
    2. NIEMALS 'category' in 'description' benutzen.
    3. 'minecraft:icon' muss ein String sein (z.B. "sword_icon").
    4. 'minecraft:display_name' muss ein Objekt sein: {{ "value": "Name" }}.
    
    Output NUR als JSON-Liste. Format:
    [
        {{ "path": "BP/items/xyz.json", "content": {{...}} }},
        {{ "path": "RP/...", "content": {{...}} }}
    ]
    """
    
    try:
        response = client.models.generate_content(model=model, contents=prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        start, end = text.find('['), text.rfind(']') + 1
        text = text[start:end]
        
        files = json.loads(text)
        
        for item in files:
            path = item['path']
            if ".." in path: continue
            
            full_path = os.path.join(REPO_ROOT, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            content = item['content']
            
            # Textur-Daten mergen falls nötig
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
            
            # AUTOMATISCHER FIX: Wir schauen in den Inhalt der Datei
            # und generieren Textur + Name, ohne die KI zu fragen.
            extract_info_and_fix(path, content)

        ver = manage_manifests()
        create_mcaddon("MeinAddon", ver)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        exit(1)

if __name__ == "__main__":
    main()
    
