import os
import json
import zipfile
import re
import google.generativeai as genai

# KONFIGURATION
API_KEY = os.environ.get("GEMINI_API_KEY")
REPO_ROOT = "."
DOCS_PATH = os.path.join(REPO_ROOT, "docs", "00_best_practices.txt")
BP_PATH = os.path.join(REPO_ROOT, "BP")
RP_PATH = os.path.join(REPO_ROOT, "RP")

def setup_gemini():
    """
    Konfiguriert Gemini und sucht dynamisch nach dem besten verfügbaren Modell.
    Verhindert 404-Fehler bei falschen Modellnamen.
    """
    if not API_KEY:
        print("❌ FEHLER: GEMINI_API_KEY ist nicht gesetzt!")
        exit(1)
        
    genai.configure(api_key=API_KEY)
    
    print("🤖 Suche nach verfügbaren Gemini-Modellen...")
    try:
        # Wir listen alle Modelle auf, um sicherzugehen, dass wir ein existierendes treffen
        available_models = list(genai.list_models())
        chosen_model_name = None

        # Strategie: Suche nach 'flash' oder 'pro', bevorzuge 'latest' oder stabile Versionen
        preferred_keywords = ['gemini-1.5-flash', 'gemini-1.5-pro']
        
        for keyword in preferred_keywords:
            for m in available_models:
                if 'generateContent' in m.supported_generation_methods:
                    if keyword in m.name:
                        chosen_model_name = m.name
                        break
            if chosen_model_name:
                break
        
        # Fallback
        if not chosen_model_name:
            chosen_model_name = 'gemini-1.5-flash'
            print("⚠️ Warnung: Kein passendes Modell in der Liste gefunden. Versuche Standard 'gemini-1.5-flash'.")
        else:
            print(f"✅ Modell ausgewählt: {chosen_model_name}")

        return genai.GenerativeModel(chosen_model_name)

    except Exception as e:
        print(f"❌ Fehler bei der Modellsuche: {e}")
        # Letzter Notnagel
        return genai.GenerativeModel('gemini-1.5-flash')

def load_rules():
    """Lädt die Goldenen Regeln aus der Doku"""
    if os.path.exists(DOCS_PATH):
        with open(DOCS_PATH, 'r') as f:
            return f.read()
    return "Regeln nicht gefunden."

def bump_version(manifest_path):
    """Erhöht die Versionsnummer im Manifest für Updates"""
    if not os.path.exists(manifest_path):
        return [1, 0, 0]
    
    try:
        with open(manifest_path, 'r') as f:
            data = json.load(f)
        
        # Version format: [major, minor, patch]
        if 'header' in data and 'version' in data['header']:
            v = data['header']['version']
            v[2] += 1 # Patch erhöhen
            data['header']['version'] = v
            
            # Auch in den Modulen updaten
            if 'modules' in data:
                for module in data['modules']:
                    if 'version' in module:
                        module['version'] = v
            
            with open(manifest_path, 'w') as f:
                json.dump(data, f, indent=4)
            return v
    except Exception as e:
        print(f"⚠️ Konnte Version nicht erhöhen: {e}")
    
    return [1, 0, 0]

def create_mcaddon(name, version):
    """Erstellt die .mcaddon Datei"""
    version_str = f"{version[0]}.{version[1]}.{version[2]}"
    filename = f"{name}_v{version_str}.mcaddon"
    
    # Aufräumen alter Versionen (optional, hält Ordner sauber)
    for f in os.listdir(REPO_ROOT):
        if f.endswith(".mcaddon") and f.startswith(name):
            try:
                os.remove(f)
            except:
                pass

    with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        # BP Ordner packen
        if os.path.exists(BP_PATH):
            for root, dirs, files in os.walk(BP_PATH):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.join("BP", os.path.relpath(abs_path, BP_PATH))
                    zf.write(abs_path, rel_path)
        
        # RP Ordner packen
        if os.path.exists(RP_PATH):
            for root, dirs, files in os.walk(RP_PATH):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.join("RP", os.path.relpath(abs_path, RP_PATH))
                    zf.write(abs_path, rel_path)
                
    print(f"📦 Add-On verpackt: {filename}")
    return filename

def main():
    print("🏭 Add-On Fabrik startet...")
    
    # 1. Input lesen
    issue_body = os.environ.get("ISSUE_BODY", "Baue ein einfaches Test-Item")
    
    # 2. Regeln laden
    rules = load_rules()
    
    # 3. Gemini konfigurieren
    model = setup_gemini()
    
    # 4. Prompt sicher zusammenbauen (ohne f-strings für JSON, um Syntaxfehler zu vermeiden)
    prompt_parts = [
        "Du bist ein Experte für Minecraft Bedrock Add-Ons (Version 1.21+).",
        "",
        "HALTE DICH STRIKT AN DIESE PROJEKT-REGELN:",
        rules,
        "",
        "DIE AUFGABE (USER WUNSCH):",
        issue_body,
        "",
        "Generiere den vollständigen Code für die nötigen Dateien.",
        "WICHTIGE ANWEISUNGEN:",
        "1. Erfinde KEINE neuen Dateipfade. Nutze exakt `BP/items/...`, `RP/textures/...`.",
        "2. Gib den Output NUR als reine JSON-Liste zurück. Kein Markdown, kein `json` Wort.",
        "3. Prüfe jede Klammer `{}` doppelt.",
        "",
        "FORMAT (Beispiel):",
        "[",
        '    {"path": "BP/items/dein_item.json", "content": { "format_version": "1.21.0", ... } },',
        '    {"path": "RP/textures/item_texture.json", "content": { "resource_pack_name": ... } }',
        "]"
    ]
    
    full_prompt = "\n".join(prompt_parts)
    
    try:
        response = model.generate_content(full_prompt)
        
        # 5. Antwort verarbeiten
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        
        # JSON-Liste finden (falls die KI Text davor/dahinter packt)
        start_idx = clean_text.find('[')
        end_idx = clean_text.rfind(']') + 1
        if start_idx != -1 and end_idx != -1:
            clean_text = clean_text[start_idx:end_idx]
        
        files = json.loads(clean_text)
        
        for file_data in files:
            path = file_data['path']
            content = file_data['content']
            
            # Sicherheitscheck
            if ".." in path or path.startswith("/"):
                print(f"⚠️ Überspringe unsicheren Pfad: {path}")
                continue
            
            # Pfad korrigieren falls nötig (manchmal vergisst KI das Prefix)
            full_path = os.path.join(REPO_ROOT, path)
            
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Existierende Dateien mergen (wichtig für item_texture.json)
            if os.path.exists(full_path) and "item_texture.json" in path:
                 with open(full_path, 'r') as f:
                    try:
                        existing_data = json.load(f)
                        if "texture_data" in content and "texture_data" in existing_data:
                            existing_data["texture_data"].update(content["texture_data"])
                            content = existing_data
                    except:
                        pass 

            with open(full_path, 'w') as f:
                json.dump(content, f, indent=4)
            print(f"✅ Datei geschrieben: {path}")

    except json.JSONDecodeError as e:
        print(f"❌ FEHLER: Die KI hat ungültiges JSON geliefert.\nRAW: {clean_text}\nError: {e}")
        exit(1)
    except Exception as e:
        print(f"❌ Kritischer Fehler: {e}")
        exit(1)

    # 6. Versionierung & Verpacken
    current_ver = bump_version(os.path.join(BP_PATH, "manifest.json"))
    bump_version(os.path.join(RP_PATH, "manifest.json"))
    
    create_mcaddon("MeinAddon", current_ver)

if __name__ == "__main__":
    main()
    
