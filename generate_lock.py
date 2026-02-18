#!/usr/bin/env python3
"""
skill.lock generator.
Reads skill.toml, hashes all files, outputs skill.lock.
"""
import hashlib
import os
import sys
from datetime import datetime
import tomllib
import configparser

def hash_file(path):
    """SHA256 hash of file contents."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

def generate_lock(skill_dir='.'):
    """Generate skill.lock from skill.toml."""
    toml_path = os.path.join(skill_dir, 'skill.toml')
    
    if not os.path.exists(toml_path):
        print(f"Error: {toml_path} not found")
        sys.exit(1)
    
    # Parse skill.toml
    with open(toml_path, 'rb') as f:
        skill_data = tomllib.load(f)
    
    manifest = skill_data.get('manifest', {})
    name = manifest.get('name', 'unknown')
    version = manifest.get('version', '0.0.0')
    
    # Find all files in skill directory
    files = []
    for root, dirs, filenames in os.walk(skill_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for fn in filenames:
            if fn.startswith('.'):
                continue
            if fn.endswith('.lock'):
                continue
            fp = os.path.join(root, fn)
            rel_path = os.path.relpath(fp, skill_dir)
            files.append({
                'path': rel_path,
                'hash': hash_file(fp),
                'size': os.path.getsize(fp)
            })
    
    # Write skill.lock manually (toml-ish format)
    lock_path = os.path.join(skill_dir, 'skill.lock')
    with open(lock_path, 'w') as f:
        f.write("# skill.lock - GENERATED. Do not edit by hand.\n")
        f.write(f"# Generated at {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}\n\n")
        
        f.write("[manifest]\n")
        f.write(f'name = "{name}"\n')
        f.write(f'version = "{version}"\n')
        f.write(f'lockfile_version = "1.0"\n\n')
        
        author = skill_data.get('author', {})
        if author:
            f.write("[author]\n")
            for k, v in author.items():
                f.write(f'{k} = "{v}"\n')
            f.write("\n")
        
        f.write("[[files]]\n")
        for fi in files:
            f.write(f'path = "{fi["path"]}"\n')
            f.write(f'hash = "{fi["hash"]}"\n')
            f.write(f'size = {fi["size"]}\n')
            f.write("\n")
        
        # Optional attestation section
        attestation = skill_data.get('attestation', {})
        if attestation:
            f.write("[attestation]\n")
            for k, v in attestation.items():
                f.write(f'{k} = "{v}"\n')
    
    print(f"Generated {lock_path}")
    print(f"  Name: {name}")
    print(f"  Version: {version}")
    print(f"  Files: {len(files)}")

if __name__ == '__main__':
    skill_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    generate_lock(skill_dir)
