import os
import sys
import json
import datetime

# Importiere die Module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import content_processor
import packager

# --- KONFIGURATION ---
ADDON_NAME = "MeinAddon" # <-- Hier ist dein gewünschter Name wieder!
BP_DIR = "BP"
RP_DIR = "RP"
OUTPUT_DIR = "Addon"

def get_next_version(bp_dir):
    """Liest die aktuelle Version aus dem Manifest und erhöht sie."""
    manifest_path = os.path.join(bp_dir, "manifest.json")
    default_ver = [1, 0, 0]
    
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r') as f:
                data = json.load(f)
                header = data.get("header", {})
                current = header.get("version", default_ver)
                # Patch-Version erhöhen (z.B. 1.0.1 -> 1.0.2)
                new_ver = [current[0], current[1], current[2] + 1]
                return new_ver
        except:
            return default_ver
    return default_ver

def get_tree_structure(path, prefix=""):
    """Visuelle Baumstruktur"""
    tree_str = ""
    if not os.path.exists(path): return ""
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
    """Liest JSON/Lang Dateien für das Log"""
    dump = "\n💻 CODE DUMP\n"
    for root_dir in [bp_dir, rp_dir]:
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.endswith(".json") or file.endswith(".lang"):
                    path = os.path.join(root, file)
                    rel_path = os.path.join(os.path.basename(root_dir), os.path.relpath(path, root_dir))
                    dump += "\n" + "="*43 + f"\n📄 DATEI: {rel_path}\n" + "="*43 + "\n"
                    try:
                        with open(path, 'r', encoding='utf-8') as f: dump += f.read() + "\n"
                    except: dump += "[Fehler beim Lesen]\n"
    return dump

def main():
    log_buffer = []
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    # Version ermitteln
    version_list = get_next_version(BP_DIR)
    version_str = f"{version_list[0]}.{version_list[1]}.{version_list[2]}"
    
    print(f"--- STARTING FACTORY BUILDER v{version_str} ---")
    log_buffer.append(f"--- VERLAUF (SUMMARY) ---\n[{timestamp}] ℹ️ 🏭 Factory Start (Version {version_str})...")

    # 1. CONTENT PROCESSING
    print(">> Running Content Processor...")
    processor_logs = content_processor.process_all(BP_DIR, RP_DIR)
    log_buffer.extend(processor_logs)
    for l in processor_logs: print(f"   {l}")

    # 2. PACKAGING
    print(">> Packaging Add-On...")
    # WICHTIG: Wir übergeben jetzt die Listen-Version [1, 0, 2]
    package_logs, filename = packager.create_mcaddon(BP_DIR, RP_DIR, OUTPUT_DIR, ADDON_NAME, version_list)
    log_buffer.extend(package_logs)
    for l in package_logs: print(f"   {l}")
    
    print(f"--- SUCCESS! Created: {filename} ---")
    log_buffer.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ✅ Build Sauber!")

    # 3. LOGGING (Tree + Dump)
    log_buffer.append("\n" + "="*43 + "\n🌳 ORDNER STRUKTUR\n" + "="*43)
    log_buffer.append("Addon/")
    log_buffer.append(f"{BP_DIR}/\n{get_tree_structure(BP_DIR)}")
    log_buffer.append(f"{RP_DIR}/\n{get_tree_structure(RP_DIR)}")
    log_buffer.append(get_code_dump(BP_DIR, RP_DIR))

    # Log Datei schreiben (mit Version im Namen, wie früher!)
    log_filename = f"build_log_v{version_str}.txt"
    log_path = os.path.join(OUTPUT_DIR, log_filename)
    
    # Zusätzlich das "latest" log überschreiben für schnellen Zugriff
    with open(os.path.join(OUTPUT_DIR, "build_log.txt"), "w", encoding='utf-8') as f:
        f.write(f"Build Date: {timestamp}\n" + "\n".join(log_buffer))
        
    # Das versionierte Log schreiben
    with open(log_path, "w", encoding='utf-8') as f:
        f.write(f"Build Date: {timestamp}\n" + "\n".join(log_buffer))

if __name__ == "__main__":
    main()
