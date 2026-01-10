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
    genai.configure(api_key=API_KEY)
    # Nutzt Flash wie in der Bibel gewünscht 
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
    
    with open(manifest_path, 'r') as f:
        data = json.load(f)
    
    # Version format: [major, minor, patch]
    v = data['header']['version']
    v[2] += 1 # Patch erhöhen
    data['header']['version'] = v
    data['modules'][0]['version'] = v
    
    with open(manifest_path, 'w') as f:
        json.dump(data, f, indent=4)
    
    return v

def create_mcaddon(name, version):
    """Erstellt die .mcaddon Datei (Roadmap Punkt 2) """
    version_str = f"{version[0]}.{version[1]}.{version[2]}"
    filename = f"{name}_v{version_str}.mcaddon"
    
    with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(BP_PATH):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, REPO_ROOT)
                zf.write(abs_path, rel_path)
        
        for root, dirs, files in os.walk(RP_PATH):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, REPO_ROOT)
                zf.write(abs_path, rel_path)
                
    print(f"✅ Add-On verpackt: {filename}")
    return filename

def main():
    print("🏭 Add-On Fabrik startet...")
    
    # 1. Input lesen (aus Issue Body oder Argument)
    issue_body = os.environ.get("ISSUE_BODY", "Baue ein einfaches Test-Item")
    
    # 2. Regeln laden
    rules = load_rules()
    
    # 3. Gemini fragen
    model = setup_gemini()
    prompt = f"""
    Du bist ein Experte für Minecraft Bedrock Add-Ons.
    
    HALTE DICH STRIKT AN DIESE REGELN:
    {rules}
    
    AUFGABE:
    {issue_body}
    
    Generiere den Code für die nötigen Dateien.
    Gib den Output NUR als JSON-Liste von Objekten zurück, ohne Markdown-Formatierung.
    Format:
    [
        {{"path": "BP/items/bsp.json", "content": {{...}} }},
        {{"path": "RP/textures/item_texture.json", "content": {{...}} }}
    ]
    Achte penibel auf JSON Syntax (Klammern)!
    """
    
    response = model.generate_content(prompt)
    
    # 4. Antwort verarbeiten
    try:
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        files = json.loads(clean_text)
        
        for file_data in files:
            path = file_data['path']
            content = file_data['content'] # Ist bereits ein Dict/List durch json.loads
            
            # Pfad sicherstellen
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            # Datei schreiben
            with open(path, 'w') as f:
                json.dump(content, f, indent=4) # Formatiert schreiben
            print(f"✅ Datei erstellt: {path}")

    except json.JSONDecodeError as e:
        print(f"❌ FEHLER: Die KI hat ungültiges JSON geliefert.\n{e}")
        # Hier könnte später die Selbstheilung greifen (Roadmap Punkt 3) 
        exit(1)
    except Exception as e:
        print(f"❌ Unerwarteter Fehler: {e}")
        exit(1)

    # 5. Versionierung & Verpacken
    current_ver = bump_version(os.path.join(BP_PATH, "manifest.json"))
    bump_version(os.path.join(RP_PATH, "manifest.json"))
    
    create_mcaddon("MeinAddon", current_ver)

if __name__ == "__main__":
    main()
  
