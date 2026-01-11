import os
import json
import uuid
import zipfile

def generate_uuid(): return str(uuid.uuid4())

def create_manifest(path, type_name, uuid1, uuid2, dep_uuid, version, logs):
    manifest = {
        "format_version": 2,
        "header": {
            "name": f"Factory {type_name}",
            "description": f"Auto-generated v{version}",
            "uuid": uuid1,
            "version": [1, 0, 0],
            "min_engine_version": [1, 21, 0]
        },
        "modules": [{"type": "data" if type_name == "BP" else "resources", "uuid": uuid2, "version": [1, 0, 0]}]
    }
    if dep_uuid:
        manifest["dependencies"] = [{"uuid": dep_uuid, "version": [1, 0, 0]}]
        
    with open(path, 'w') as f: json.dump(manifest, f, indent=4)
    logs.append(f"✅ Manifest erstellt: {type_name}")

def create_mcaddon(bp_dir, rp_dir, output_dir, addon_name, version):
    logs = []
    
    # UUIDs
    bp_u1, bp_u2 = generate_uuid(), generate_uuid()
    rp_u1, rp_u2 = generate_uuid(), generate_uuid()
    
    # Manifeste
    create_manifest(os.path.join(bp_dir, "manifest.json"), "BP", bp_u1, bp_u2, rp_u1, version, logs)
    create_manifest(os.path.join(rp_dir, "manifest.json"), "RP", rp_u1, rp_u2, None, version, logs)
    
    # ZIP
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    filename = f"{addon_name}_v{version}.mcaddon"
    output_path = os.path.join(output_dir, filename)
    
    with zipfile.ZipFile(output_path, 'w') as zipf:
        for d in [bp_dir, rp_dir]:
            for root, dirs, files in os.walk(d):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join(d, os.path.relpath(file_path, d))
                    zipf.write(file_path, arcname)
    
    logs.append(f"📦 .mcaddon gepackt: {filename}")
    return logs, filename
    
