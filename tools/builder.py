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
    """
    Erstellt eine einfache 16x16 PNG Datei, damit Items nicht lila-schwarz sind.
    Das ist ein Platzhalter, bis du echte Bilder hochlädst.
    """
    texture_path = os.path.join(RP_PATH, "textures", "items", f"{texture_name}.png")
    os.makedirs(os.path.dirname(texture_path), exist_ok=True)
    
    if not os.path.exists(texture_path):
        # Wir erstellen ein extrem simples PNG (1x1 Pixel, schwarz) per Hex-Code
        # Das spart uns komplexe Bild-Bibliotheken.
        # Minimaler PNG Header + 1 schwarzer Pixel
        minimal_png = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\rIDATx\x9cc\x60\x60\x60\x00\x00\x00\x05\x00\x01\x0d\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        with open(texture_path, 'wb') as f:
            f.write(minimal_png)
        print(f"🎨 Platzhalter-Textur erstellt: {texture_path}")

def update_language_file(item_id, display_name):
    """
    Schreibt den Namen in die en_US.lang Datei, damit 'item.test:...' verschwindet.
    """
    lang_path = os.path.join(RP_PATH, "texts", "en_US.lang")
    os.makedirs(os.path.dirname(lang_path), exist_ok=True)
    
    # Format: item.test:obsidian_sword.name=Obsidian Schwert
    entry = f"item.{item_id}.name={display_name}\n"
    
    # Prüfen ob schon vorhanden
    content = ""
    if os.path.exists(lang_path):
        with open(lang_path, 'r') as f:
            content = f.read()
            
    if entry.strip() not in content:
        with open(lang_path, 'a') as f:
            f.write(entry)
        print(f"📝 Name eingetragen: {display_name}")

def clean_up_old_files():
    print("🧹 CLEANUP: Entferne alte JSONs...")
    folders = [os.path.join(BP_PATH, "items"), os.path.join(BP_PATH, "recipes")]
    for folder in folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            os.makedirs(folder)

def get_smart_model_name(client):
    try:
        all_models = list(client.models.list())
        flash = [m.name for m in all_models if "flash" in m.name.lower()]
        best = flash[0] if flash else "gemini-1.5-flash"
        return best.replace("models/", "") if best.startswith("models/") else best
    except: return "gemini-1.5-flash"

def manage_manifests():
    print("🔧 CHECK: Synchronisiere Manifeste...")
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
    
    # RP Manifest
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

    # BP Manifest
    bp_uuid = str(uuid.uuid4())
    if os.path.exists(bp_path):
        try:
            with open(bp_path, 'r') as f:
                d = json.load(f)
                bp_uuid = d['header']['uuid']
        except: pass

    # BP Manifest (Dependency strikt auf RP Version setzen)
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
    print("🏭 Factory startet (Visual Polish)...")
    if not API_KEY: exit(1)
    
    clean_up_old_files()
    
    issue_body = os.environ.get("ISSUE_BODY", "Test Item")
    client = genai.Client(api_key=API_KEY)
    model = get_smart_model_name(client)
    
    # Prompt fordert auch den Display Namen an für die Lang-Datei
    prompt = f"""
    Du bist ein Minecraft Bedrock Experte.
    AUFGABE: {issue_body}
    REGELN: {load_rules()}
    
    Generiere JSON für BP und RP.
    ZUSATZ: Gib mir für jedes Item auch den Namen der Textur-Datei (ohne .png) und den Display-Namen.
    
    OUTPUT FORMAT (JSON Liste):
    [
        {{
            "path": "BP/items/xyz.json", 
            "content": {{...}}, 
            "texture_name": "xyz_icon",
            "display_name": "Mein Item Name",
            "item_id": "test:xyz" 
        }},
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
            
            # ZUSATZ-FEATURES:
            # 1. Dummy Textur erstellen
            if "texture_name" in item:
                create_dummy_texture(item["texture_name"])
            
            # 2. Lang File Update
            if "display_name" in item and "item_id" in item:
                update_language_file(item["item_id"], item["display_name"])

        ver = manage_manifests()
        create_mcaddon("MeinAddon", ver)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        exit(1)

if __name__ == "__main__":
    main()
    
