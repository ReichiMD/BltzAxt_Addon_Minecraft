import os
import json
import zipfile
import uuid
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

def get_smart_model_name(client):
    """Sucht das passende Flash-Modell."""
    try:
        all_models = list(client.models.list())
        flash_candidates = [m.name for m in all_models if "flash" in m.name.lower()]
        
        best_choice = None
        if flash_candidates:
            for cand in flash_candidates:
                if "1.5" in cand and "flash" in cand:
                    best_choice = cand
                    break
            if not best_choice: best_choice = flash_candidates[0]
        else:
            return "gemini-1.5-flash"

        if best_choice.startswith("models/"):
             best_choice = best_choice.replace("models/", "")
        return best_choice
    except:
        return "gemini-1.5-flash"

def manage_manifests(target_version=None):
    """
    Verwaltet Manifeste intelligent:
    1. Behält UUIDs bei, wenn Dateien existieren (wichtig für Updates!).
    2. Erstellt neue UUIDs nur beim ersten Mal.
    3. Verlinkt BP korrekt mit RP (Dependency Fix).
    4. Setzt Versionen hoch.
    """
    print("🔧 CHECK: Synchronisiere Manifeste & Versionen...")
    
    # Pfade
    rp_path = os.path.join(RP_PATH, "manifest.json")
    bp_path = os.path.join(BP_PATH, "manifest.json")
    
    os.makedirs(RP_PATH, exist_ok=True)
    os.makedirs(BP_PATH, exist_ok=True)

    # --- 1. RESOURCE PACK (RP) ---
    rp_uuid = str(uuid.uuid4())
    rp_version = [1, 0, 0]
    
    # Lese existierendes RP
    if os.path.exists(rp_path):
        try:
            with open(rp_path, 'r') as f:
                data = json.load(f)
                rp_uuid = data['header']['uuid'] # UUID BEHALTEN!
                rp_version = data['header']['version']
                # Version erhöhen
                rp_version[2] += 1
        except: pass
    
    # Schreibe RP neu (saubere Struktur)
    rp_data = {
        "format_version": 2,
        "header": {
            "name": "Factory Addon RP",
            "description": "Visuals (Auto-Generated)",
            "uuid": rp_uuid,
            "version": rp_version,
            "min_engine_version": [1, 21, 0]
        },
        "modules": [
            {
                "type": "resources",
                "uuid": str(uuid.uuid4()), # Modul UUID darf neu sein
                "version": rp_version
            }
        ]
    }
    with open(rp_path, 'w') as f:
        json.dump(rp_data, f, indent=4)

    # --- 2. BEHAVIOR PACK (BP) ---
    bp_uuid = str(uuid.uuid4())
    bp_version = rp_version # Sync Version
    
    if os.path.exists(bp_path):
        try:
            with open(bp_path, 'r') as f:
                data = json.load(f)
                bp_uuid = data['header']['uuid'] # UUID BEHALTEN!
        except: pass

    # BP muss RP kennen (Dependency)
    bp_data = {
        "format_version": 2,
        "header": {
            "name": "Factory Addon BP",
            "description": "Logic (Auto-Generated)",
            "uuid": bp_uuid,
            "version": bp_version,
            "min_engine_version": [1, 21, 0]
        },
        "modules": [
            {
                "type": "data",
                "uuid": str(uuid.uuid4()),
                "version": bp_version
            }
        ],
        "dependencies": [
            {
                "uuid": rp_uuid, # WICHTIG: Link zur RP UUID
                "version": rp_version
            }
        ]
    }
    with open(bp_path, 'w') as f:
        json.dump(bp_data, f, indent=4)
        
    print(f"✅ Manifeste aktualisiert. Version: {rp_version}")
    return rp_version

def create_mcaddon(name, version):
    v_str = f"{version[0]}.{version[1]}.{version[2]}"
    filename = f"{name}_v{v_str}.mcaddon"
    
    # Alte Addons löschen
    for f in os.listdir(REPO_ROOT):
        if f.endswith(".mcaddon") and name in f:
            try: os.remove(f)
            except: pass

    with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Ordner BP und RP in das Root des Zips packen
        for folder in [BP_PATH, RP_PATH]:
            if os.path.exists(folder):
                folder_name = os.path.basename(folder) # "BP" oder "RP"
                for root, _, files in os.walk(folder):
                    for file in files:
                        abs_path = os.path.join(root, file)
                        # Relativer Pfad im Zip: BP/manifest.json etc.
                        rel_path = os.path.join(folder_name, os.path.relpath(abs_path, folder))
                        zf.write(abs_path, rel_path)
    print(f"📦 Add-On erstellt: {filename}")

def main():
    print("🏭 Factory startet (Stability Edition)...")
    if not API_KEY:
        print("❌ FEHLER: GEMINI_API_KEY fehlt!")
        exit(1)

    issue_body = os.environ.get("ISSUE_BODY", "Test Item")
    rules = load_rules()
    
    client = genai.Client(api_key=API_KEY)
    model_name = get_smart_model_name(client)
    print(f"🚀 Nutze Modell: {model_name}")

    # VERBESSERTER PROMPT (Gegen Syntax-Fehler)
    prompt_parts = [
        "Du bist ein Minecraft Bedrock Add-On Experte (Version 1.21.0+).",
        "REGELN:", rules,
        "WICHTIGE SYNTAX REGELN (Vermeide diese Fehler):",
        "1. 'minecraft:icon' in components muss ein String sein (Textur-Name), KEIN Objekt!",
        "   RICHTIG: 'minecraft:icon': 'obsidian_sword'",
        "   FALSCH: 'minecraft:icon': { 'texture': ... }",
        "2. Events wie 'on_tool_damaged' dürfen KEINE Properties wie 'damage' direkt enthalten.",
        "   Nutze Events um Commands auszuführen oder Molang, aber halte dich an die Schema-Doku.",
        "3. Nutze 'minecraft:digger' nur mit korrekten Parametern.",
        "4. Erfinde keine Felder in 'description' (kein 'category').",
        "",
        "AUFGABE:", issue_body,
        "Generiere JSON für BP und RP.",
        "WICHTIG: Output NUR als JSON-Liste. Format:",
        '[{"path": "BP/items/x.json", "content": {...}}, {"path": "RP/...", "content": {...}}]'
    ]
    full_prompt = "\n".join(prompt_parts)

    try:
        response = client.models.generate_content(
            model=model_name, 
            contents=full_prompt
        )
        
        text = response.text.replace("```json", "").replace("```", "").strip()
        start, end = text.find('['), text.rfind(']') + 1
        if start != -1 and end != -1: text = text[start:end]
        
        files = json.loads(text)
        
        for item in files:
            path = item['path']
            if ".." in path: continue
            
            full_path = os.path.join(REPO_ROOT, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            content = item['content']
            # Merge Logic für Texturen
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

        # Manifest Update & Packaging
        final_version = manage_manifests()
        create_mcaddon("MeinAddon", final_version)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        exit(1)

if __name__ == "__main__":
    main()
    
