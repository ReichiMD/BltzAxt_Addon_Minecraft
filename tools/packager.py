import os
import json
import uuid
import zipfile
import shutil

def generate_uuid():
    return str(uuid.uuid4())

def create_manifest(path, type_name, uuid1, uuid2, dep_uuid, version):
    """Erstellt ein valides Manifest für BP oder RP"""
    manifest = {
        "format_version": 2,
        "header": {
            "name": f"Factory {type_name}",
            "description": f"Auto-generated {type_name} v{version}",
            "uuid": uuid1,
            "version": [1, 0, 0],
            "min_engine_version": [1, 21, 0]
        },
        "modules": [
            {
                "type": "data" if type_name == "BP" else "resources",
                "uuid": uuid2,
                "version": [1, 0, 0]
            }
        ]
    }
    
    if dep_uuid:
        manifest["dependencies"] = [
            {
                "uuid": dep_uuid,
                "version": [1, 0, 0]
            }
        ]
        
    with open(path, 'w') as f:
        json.dump(manifest, f, indent=4)

def create_mcaddon(bp_dir, rp_dir, output_dir, addon_name, version):
    """Erstellt das finale .mcaddon Paket"""
    
    # 1. UUIDs generieren
    bp_uuid_header = generate_uuid()
    bp_uuid_module = generate_uuid()
    rp_uuid_header = generate_uuid()
    rp_uuid_module = generate_uuid()
    
    # 2. Manifeste schreiben
    create_manifest(os.path.join(bp_dir, "manifest.json"), "BP", bp_uuid_header, bp_uuid_module, rp_uuid_header, version)
    create_manifest(os.path.join(rp_dir, "manifest.json"), "RP", rp_uuid_header, rp_uuid_module, None, version)
    
    # 3. ZIP erstellen (.mcaddon)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    filename = f"{addon_name}_v{version}.mcaddon"
    output_path = os.path.join(output_dir, filename)
    
    with zipfile.ZipFile(output_path, 'w') as zipf:
        # BP Ordner hinzufügen
        for root, dirs, files in os.walk(bp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Relativer Pfad im Zip (z.B. "BP/items/sword.json")
                arcname = os.path.join("BP", os.path.relpath(file_path, bp_dir))
                zipf.write(file_path, arcname)
                
        # RP Ordner hinzufügen
        for root, dirs, files in os.walk(rp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.join("RP", os.path.relpath(file_path, rp_dir))
                zipf.write(file_path, arcname)
                
    return filename
              
