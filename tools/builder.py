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
    """Sucht das passende Flash-Modell, um 404 Fehler zu vermeiden."""
    print("🔎 DIAGNOSE: Scanne verfügbare Modelle...")
    try:
        all_models = list(client.models.list())
        flash_candidates = [m.name for m in all_models if "flash" in m.name.lower()]
        
        best_choice = None
        if flash_candidates:
            # Bevorzuge Modelle mit '1.5' und 'flash'
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

def ensure_manifests_exist():
    """
    PRÜFT UND REPARIERT FEHLENDE MANIFESTE.
    Dies ist der Fix für 'Unbekannter Paketname'.
    """
    print("🔧 CHECK: Prüfe Manifeste...")
    
    # UUIDs generieren (für Behavior und Resource Pack)
    bp_uuid = str(uuid.uuid4())
    rp_uuid = str(uuid.uuid4())
    
    # 1. Resource Pack Manifest (RP)
    rp_manifest_path = os.path.join(RP_PATH, "manifest.json")
    if not os.path.exists(rp_manifest_path):
        print("⚠️ RP Manifest fehlt. Erstelle neu...")
        os.makedirs(RP_PATH, exist_ok=True)
        rp_data = {
            "format_version": 2,
            "header": {
                "name": "Factory Addon RP",
                "description": "Erstellt von der Add-On Factory",
                "uuid": rp_uuid,
                "version": [1, 0, 0],
                "min_engine_version": [1, 21, 0]
            },
            "modules": [
                {
                    "type": "resources",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0]
                }
            ]
        }
        with open(rp_manifest_path, 'w') as f:
            json.dump(rp_data, f, indent=4)

    # Lese RP UUID aus (falls es schon existierte), damit BP darauf verweisen kann
    with open(rp_manifest_path, 'r') as f:
        rp_data = json.load(f)
        actual_rp_uuid = rp_data['header']['uuid']

    # 2. Behavior Pack Manifest (BP)
    bp_manifest_path = os.path.join(BP_PATH, "manifest.json")
    if not os.path.exists(bp_manifest_path):
        print("⚠️ BP Manifest fehlt. Erstelle neu...")
        os.makedirs(BP_PATH, exist_ok=True)
        bp_data = {
            "format_version": 2,
            "header": {
                "name": "Factory Addon BP",
                "description": "Logik für Factory Addon",
                "uuid": bp_uuid,
                "version": [1, 0, 0],
                "min_engine_version": [1, 21, 0]
            },
            "modules": [
                {
                    "type": "data",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0]
                }
            ],
            "dependencies": [
                {
                    "uuid": actual_rp_uuid,
                    "version": [1, 0, 0]
                }
            ]
        }
        with open(bp_manifest_path, 'w') as f:
            json.dump(bp_data, f, indent=4)
            
    print("✅ Manifeste sind bereit.")

def bump_version(manifest_path):
    if not os.path.exists(manifest_path): return [1, 0, 0]
    try:
        with open(manifest_path, 'r') as f:
            data = json.load(f)
        v = data['header']['version']
        v[2] += 1
        data['header']['version'] = v
        if 'modules' in data:
            for m in data['modules']: m['version'] = v
        with open(manifest_path, 'w') as f:
            json.dump(data, f, indent=4)
        return v
    except: return [1, 0, 0]

def create_mcaddon(name, version):
    v_str = f"{version[0]}.{version[1]}.{version[2]}"
    filename = f"{name}_v{v_str}.mcaddon"
    
    # Alte Datei löschen
    for f in os.listdir(REPO_ROOT):
        if f.endswith(".mcaddon") and name in f:
            try: os.remove(f)
            except: pass

    with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        # WICHTIG: Packe BP und RP Ordner
        for folder in [BP_PATH, RP_PATH]:
            if os.path.exists(folder):
                for root, _, files in os.walk(folder):
                    for file in files:
                        abs_path = os.path.join(root, file)
                        rel_path = os.path.relpath(abs_path, REPO_ROOT)
                        zf.write(abs_path, rel_path)
    print(f"📦 Add-On erstellt: {filename}")

def main():
    print("🏭 Factory startet (Self-Healing Edition)...")
    if not API_KEY:
        print("❌ FEHLER: GEMINI_API_KEY fehlt!")
        exit(1)

    issue_body = os.environ.get("ISSUE_BODY", "Test Item")
    rules = load_rules()
    
    # Client starten & Modell wählen
    client = genai.Client(api_key=API_KEY)
    model_name = get_smart_model_name(client)
    print(f"🚀 Nutze Modell: {model_name}")

    prompt_parts = [
        "Du bist ein Minecraft Bedrock Add-On Experte.",
        "REGELN:", rules,
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
            # Merge Logic
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

        # WICHTIG: Manifeste prüfen VOR dem Verpacken
        ensure_manifests_exist()

        ver = bump_version(os.path.join(BP_PATH, "manifest.json"))
        bump_version(os.path.join(RP_PATH, "manifest.json"))
        create_mcaddon("MeinAddon", ver)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        exit(1)

if __name__ == "__main__":
    main()
        
