import os
import json
import zipfile
from google import genai # Das ist der neue Import

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
    
    # Aufräumen
    for f in os.listdir(REPO_ROOT):
        if f.endswith(".mcaddon") and name in f:
            try: os.remove(f)
            except: pass

    with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        for folder in [BP_PATH, RP_PATH]:
            if os.path.exists(folder):
                for root, _, files in os.walk(folder):
                    for file in files:
                        abs_path = os.path.join(root, file)
                        rel_path = os.path.relpath(abs_path, REPO_ROOT)
                        zf.write(abs_path, rel_path)
    print(f"📦 Add-On erstellt: {filename}")

def main():
    print("🏭 Factory startet (Neues Google GenAI SDK)...")
    
    if not API_KEY:
        print("❌ FEHLER: GEMINI_API_KEY fehlt!")
        exit(1)

    issue_body = os.environ.get("ISSUE_BODY", "Test Item")
    rules = load_rules()
    
    # NEUER CLIENT SETUP
    client = genai.Client(api_key=API_KEY)
    
    # Prompt bauen
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
        # NEUER API AUFRUF
        print("🚀 Sende Anfrage an Gemini 1.5 Flash...")
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
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

        ver = bump_version(os.path.join(BP_PATH, "manifest.json"))
        bump_version(os.path.join(RP_PATH, "manifest.json"))
        create_mcaddon("MeinAddon", ver)

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        exit(1)

if __name__ == "__main__":
    main()
                        
