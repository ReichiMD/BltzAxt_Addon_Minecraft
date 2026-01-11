import os
import json
import uuid
import zipfile

def generate_uuid(): return str(uuid.uuid4())

def create_manifest(path, type_name, uuid1, uuid2, dep_uuid, version_list, logs):
    """Erstellt Manifest mit korrekter Versionsnummer"""
    
    # Version String für Beschreibung (z.B. "1.0.5")
    ver_str = f"{version_list[0]}.{version_list[1]}.{version_list[2]}"
    
    manifest = {
        "format_version": 2,
        "header": {
            "name": f"Factory {type_name}",
            "description": f"Auto-generated v{ver_str}",
            "uuid": uuid1,
            "version": version_list,  # <-- Hier kommt jetzt [1, 0, X] rein!
            "min_engine_version": [1, 21, 0]
        },
        "modules": [{"type": "data" if type_name == "BP" else "resources", "uuid": uuid2, "version": version_list}]
    }
    if dep_uuid:
        manifest["dependencies"] = [{"uuid": dep_uuid, "version": version_list}]
        
    with open(path, 'w') as f: json.dump(manifest, f, indent=4)
    logs.append(f"✅ Manifest Update: {type_name} v{ver_str}")

def create_mcaddon(bp_dir, rp_dir, output_dir, addon_name, version_list):
    logs = []
    
    # Version String für Dateinamen
    ver_str = f"{version_list[0]}.{version_list[1]}.{version_list[2]}"
    
    # UUIDs generieren
    bp_u1, bp_u2 = generate_uuid(), generate_uuid()
    rp_u1, rp_u2 = generate_uuid(), generate_uuid()
    
    # Manifeste schreiben (mit Versions-Liste!)
    create_manifest(os.path.join(bp_dir, "manifest.json"), "BP", bp_u1, bp_u2, rp_u1, version_list, logs)
    create_manifest(os.path.join(rp_dir, "manifest.json"), "RP", rp_u1, rp_u2, None, version_list, logs)
    
    # ZIP erstellen
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    filename = f"{addon_name}_v{ver_str}.mcaddon"  # <-- Dateiname: MeinAddon_v1.0.X.mcaddon
    output_path = os.path.join(output_dir, filename)
    
    with zipfile.ZipFile(output_path, 'w') as zipf:
        for d in [bp_dir, rp_dir]:
            for root, dirs, files in os.walk(d):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join(d, os.path.relpath(file_path, d))
                    zipf.write(file_path, arcname)
    
    # Log Datei auch mit ins ZIP packen (optional, aber praktisch)
    # (Lassen wir hier weg, um Loop-Fehler zu vermeiden, da das Log erst danach geschrieben wird)
    
    logs.append(f"📦 .mcaddon gepackt: {filename}")
    return logs, filename
