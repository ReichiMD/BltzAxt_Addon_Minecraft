import os
import sys
import datetime

# Importiere die Module aus dem gleichen Ordner
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import content_processor
import packager

# --- KONFIGURATION ---
VERSION = datetime.datetime.now().strftime("%Y%m%d") # Version ist das Datum
ADDON_NAME = "MyFactoryAddon"
BP_DIR = "BP"
RP_DIR = "RP"
OUTPUT_DIR = "Addon"

def main():
    print(f"--- STARTING FACTORY BUILDER v{VERSION} ---")
    
    # 1. CLEANUP (Veraltete Dateien entfernen, falls nötig)
    # (Hier könnte man Code einfügen, um alte Builds zu löschen)
    
    # 2. CONTENT PROCESSING (Der Inspektor)
    print(">> Running Content Processor...")
    logs = content_processor.process_all(BP_DIR, RP_DIR)
    for log in logs:
        print(f"   [LOG] {log}")
        
    # 3. PACKAGING (Der Logistiker)
    print(">> Packaging Add-On...")
    file_name = packager.create_mcaddon(BP_DIR, RP_DIR, OUTPUT_DIR, ADDON_NAME, VERSION)
    
    print(f"--- SUCCESS! Created: {file_name} ---")
    
    # Log Datei schreiben (für den User im ZIP oder Repo)
    with open(os.path.join(OUTPUT_DIR, "build_log.txt"), "w") as f:
        f.write(f"Build Date: {VERSION}\n")
        f.write("Logs:\n")
        f.write("\n".join(logs))

if __name__ == "__main__":
    main()
    
