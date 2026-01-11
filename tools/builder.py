import os
import sys
import datetime

# Importiere die Module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import content_processor
import packager

# --- KONFIGURATION ---
VERSION = datetime.datetime.now().strftime("%Y%m%d")
ADDON_NAME = "MyFactoryAddon"
BP_DIR = "BP"
RP_DIR = "RP"
OUTPUT_DIR = "Addon"

def get_tree_structure(path, prefix=""):
    """Erstellt eine visuelle Baumstruktur des Ordners"""
    tree_str = ""
    if not os.path.exists(path):
        return ""
    
    items = sorted(os.listdir(path))
    for i, item in enumerate(items):
        full_path = os.path.join(path, item)
        is_last = (i == len(items) - 1)
        connector = "└── " if is_last else "├── "
        
        tree_str += f"{prefix}{connector}{item}\n"
        
        if os.path.isdir(full_path):
            extension = "    " if is_last else "│   "
            tree_str += get_tree_structure(full_path, prefix + extension)
    return tree_str

def get_code_dump(bp_dir, rp_dir):
    """Liest alle relevanten JSON/Lang Dateien für das Log"""
    dump = "\n💻 CODE DUMP\n"
    
    for root_dir in [bp_dir, rp_dir]:
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.endswith(".json") or file.endswith(".lang"):
                    path = os.path.join(root, file)
                    rel_path = os.path.join(os.path.basename(root_dir), os.path.relpath(path, root_dir))
                    
                    dump += "\n" + "="*43 + "\n"
                    dump += f"📄 DATEI: {rel_path}\n"
                    dump += "="*43 + "\n"
                    
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            dump += f.read() + "\n"
                    except Exception as e:
                        dump += f"[Fehler beim Lesen: {e}]\n"
    return dump

def main():
    log_buffer = []
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    print(f"--- STARTING FACTORY BUILDER v{VERSION} ---")
    log_buffer.append(f"--- VERLAUF (SUMMARY) ---\n[{timestamp}] ℹ️ 🏭 Factory Start...")

    # 1. CONTENT PROCESSING
    print(">> Running Content Processor...")
    processor_logs = content_processor.process_all(BP_DIR, RP_DIR)
    log_buffer.extend(processor_logs)
    for l in processor_logs: print(f"   {l}")

    # 2. PACKAGING
    print(">> Packaging Add-On...")
    package_logs, filename = packager.create_mcaddon(BP_DIR, RP_DIR, OUTPUT_DIR, ADDON_NAME, VERSION)
    log_buffer.extend(package_logs)
    for l in package_logs: print(f"   {l}")
    
    print(f"--- SUCCESS! Created: {filename} ---")
    log_buffer.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ✅ Build Sauber!")

    # 3. TREE VIEW GENERIEREN
    log_buffer.append("\n" + "="*43)
    log_buffer.append("🌳 ORDNER STRUKTUR")
    log_buffer.append("="*43)
    log_buffer.append("Addon/")
    log_buffer.append(f"{BP_DIR}/\n{get_tree_structure(BP_DIR)}")
    log_buffer.append(f"{RP_DIR}/\n{get_tree_structure(RP_DIR)}")

    # 4. CODE DUMP GENERIEREN
    log_buffer.append(get_code_dump(BP_DIR, RP_DIR))

    # Log Datei schreiben
    log_path = os.path.join(OUTPUT_DIR, f"build_log.txt") # Überschreibt immer das aktuelle Log
    with open(log_path, "w", encoding='utf-8') as f:
        f.write(f"Build Date: {VERSION}\n")
        f.write("\n".join(log_buffer))

if __name__ == "__main__":
    main()
    
