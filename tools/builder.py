import os
import json
import zipfile
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
    """
    Fragt die API, welche Modelle TATSÄCHLICH verfügbar sind,
    und wählt das beste verfügbare aus. Verhindert 404 Fehler.
    """
    print("🔎 DIAGNOSE: Scanne verfügbare Modelle...")
    try:
        # Wir holen die rohe Liste aller Modelle
        all_models = list(client.models.list())
        
        # Debug: Wir geben aus, was wir gefunden haben (hilft bei Fehlern)
        flash_candidates = []
        pro_candidates = []
        
        for m in all_models:
            name = m.name # z.B. "models/gemini-1.5-flash"
            if "flash" in name.lower():
                flash_candidates.append(name)
            if "pro" in name.lower() and "1.5" in name:
                pro_candidates.append(name)

        print(f"   Gefunden: {len(all_models)} Modelle gesamt.")
        print(f"   Flash Kandidaten: {flash_candidates}")

        # ENTSCHEIDUNGSLOGIK
        # 1. Versuche das neueste stabile Flash Modell
        # Wir bevorzugen '002' oder 'latest', wenn vorhanden, sonst das erste Flash
        best_choice = None
        
        if flash_candidates:
            # Nimm einfach den ersten Treffer, der 'flash' im Namen hat.
            # Die API liefert meist den genauen Resource-Namen (z.B. models/gemini-1.5-flash-001)
            best_choice = flash_candidates[0]
            
            # Falls wir '1.5-flash' spezifisch finden, nehmen wir das bevorzugt
            for fc in flash_candidates:
                if "1.5-flash" in fc:
                    best_choice = fc
                    break
        
        # 2. Fallback auf Pro (falls kein Flash da ist - z.B. API Key Einschränkung)
        elif pro_candidates:
            print("⚠️ Kein Flash gefunden. Weiche auf PRO aus (Achtung: Quota!).")
            best_choice = pro_candidates[0]
            
        # 3. Notfall-Fallback (Blindflug)
        else:
            print("⚠️ Keine passenden Modelle im Scan. Versuche Standard-Namen.")
            return "gemini-1.5-flash"

        # WICHTIG: Das 'models/' Präfix muss manchmal weg, manchmal bleiben.
        # Das neue SDK ist da meist tolerant, aber wir nehmen den Namen so, wie er in der Liste stand.
        # Manchmal ist der Name 'models/gemini-...' -> wir strippen 'models/' optional, 
        # aber beim neuen SDK ist der volle Name oft sicherer.
        # Wir probieren es mit dem Namen aus der Liste.
        
        # Workaround: Falls der Name mit "models/" beginnt, schneiden wir es ab, 
        # da generate_content oft nur die ID will (z.B. "gemini-1.5-flash").
        if best_choice.startswith("models/"):
             best_choice = best_choice.replace("models/", "")
             
        return best_choice

    except Exception as e:
        print(f"⚠️ Scan fehlgeschlagen ({e}). Nutze Standard.")
        return "gemini-1.5-flash"

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
    print("🏭 Factory startet (Smart Model Select)...")
    if not API_KEY:
        print("❌ FEHLER: GEMINI_API_KEY fehlt!")
        exit(1)

    issue_body = os.environ.get("ISSUE_BODY", "Test Item")
    rules = load_rules()
    
    # Client starten
    client = genai.Client(api_key=API_KEY)
    
    # Modell dynamisch wählen
    model_name = get_smart_model_name(client)
    print(f"🚀 ENTSCHEIDUNG: Nutze Modell '{model_name}'")

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
        print("TIPP: Wenn das ein 404 ist, stimmt der Modellname trotz Scan nicht.")
        exit(1)

if __name__ == "__main__":
    main()
    
