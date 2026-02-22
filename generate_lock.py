#!/usr/bin/env python3
"""
skill.lock generator.
Reads skill.toml, hashes all files, outputs skill.lock.
Supports attestation block per skill.lock.md spec.
"""
import hashlib
import json
import os
import sys
from datetime import datetime
import tomllib

def hash_file(path):
    """SHA256 hash of file contents."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

def compute_scope_hash(lock_content_without_attestation):
    """Compute SHA256 of lock content excluding attestation block."""
    h = hashlib.sha256()
    h.update(lock_content_without_attestation.encode('utf-8'))
    return h.hexdigest()

def generate_lock(skill_dir='.', compute_attestation=False):
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
    
    # Build lock content in memory first (for scope_hash computation)
    lines = []
    lines.append("# skill.lock - GENERATED. Do not edit by hand.")
    lines.append(f"# Generated at {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}")
    lines.append("")
    
    lines.append("[manifest]")
    lines.append(f'name = "{name}"')
    lines.append(f'version = "{version}"')
    lines.append(f'lockfile_version = "1.0"')
    lines.append("")
    
    author = skill_data.get('author', {})
    if author:
        lines.append("[author]")
        for k, v in author.items():
            lines.append(f'{k} = "{v}"')
        lines.append("")
    
    lines.append("[[files]]")
    for fi in files:
        lines.append(f'path = "{fi["path"]}"')
        lines.append(f'hash = "{fi["hash"]}"')
        lines.append(f'size = {fi["size"]}')
        lines.append("")
    
    # Track where attestation section starts (for scope_hash)
    attestation_start_idx = len(lines)
    
    # Optional attestation section - read from skill.toml or compute
    attestation = skill_data.get('attestation', {})
    if compute_attestation and attestation:
        # Compute scope_hash from content BEFORE attestation block
        content_before_attestation = '\n'.join(lines[:attestation_start_idx])
        scope_hash = compute_scope_hash(content_before_attestation)
        
        lines.append("[attestation]")
        lines.append(f'issuer_id = "{attestation.get("issuer_id", "")}"')
        lines.append(f'subject_id = "{attestation.get("subject_id", "")}"')
        lines.append(f'signature = "{attestation.get("signature", "")}"')
        lines.append(f'chain_id = "{attestation.get("chain_id", "")}"')
        lines.append(f'timestamp = "{datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}"')
        lines.append(f'scope_hash = "{scope_hash}"')
        
        # Optional metadata
        metadata = attestation.get('metadata', {})
        if metadata:
            lines.append("")
            lines.append("[attestation.metadata]")
            for k, v in metadata.items():
                if isinstance(v, float):
                    lines.append(f'{k} = {v}')
                else:
                    lines.append(f'{k} = "{v}"')
    elif attestation:
        # Legacy/flat format - convert to new spec format
        lines.append("[attestation]")
        for k, v in attestation.items():
            if k == 'metadata':
                continue
            lines.append(f'{k} = "{v}"')
        
        # Compute scope_hash even for legacy
        content_before_attestation = '\n'.join(lines[:attestation_start_idx])
        scope_hash = compute_scope_hash(content_before_attestation)
        lines.append(f'scope_hash = "{scope_hash}"')
        
        metadata = attestation.get('metadata', {})
        if metadata:
            lines.append("")
            lines.append("[attestation.metadata]")
            for k, v in metadata.items():
                if isinstance(v, float):
                    lines.append(f'{k} = {v}')
                else:
                    lines.append(f'{k} = "{v}"')
    
    # Write to file
    lock_content = '\n'.join(lines)
    lock_path = os.path.join(skill_dir, 'skill.lock')
    with open(lock_path, 'w') as f:
        f.write(lock_content)
    
    print(f"Generated {lock_path}")
    print(f"  Name: {name}")
    print(f"  Version: {version}")
    print(f"  Files: {len(files)}")
    if compute_attestation and attestation:
        print(f"  Attestation: included (scope_hash computed)")

def verify_lock(skill_dir='.'):
    """Verify skill.lock against current files."""
    lock_path = os.path.join(skill_dir, 'skill.lock')
    
    if not os.path.exists(lock_path):
        print(f"Error: {lock_path} not found")
        return False
    
    # Parse skill.lock (simple parser for [[files]] sections)
    files_in_lock = {}
    current_file = None
    
    with open(lock_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('[[files]]'):
                current_file = {}
            elif line.startswith('path =') and current_file is not None:
                current_file['path'] = line.split('=')[1].strip().strip('"')
            elif line.startswith('hash =') and current_file is not None:
                current_file['hash'] = line.split('=')[1].strip().strip('"')
            elif line.startswith('size =') and current_file is not None:
                current_file['size'] = int(line.split('=')[1].strip())
                files_in_lock[current_file['path']] = current_file
                current_file = None
    
    # Verify each file
    all_valid = True
    for rel_path, lock_entry in files_in_lock.items():
        fp = os.path.join(skill_dir, rel_path)
        if not os.path.exists(fp):
            print(f"MISSING: {rel_path}")
            all_valid = False
            continue
        
        actual_hash = hash_file(fp)
        if actual_hash != lock_entry['hash']:
            print(f"MISMATCH: {rel_path}")
            print(f"  Expected: {lock_entry['hash'][:16]}...")
            print(f"  Actual:   {actual_hash[:16]}...")
            all_valid = False
    
    if all_valid:
        print(f"✓ All {len(files_in_lock)} files verified")
    else:
        print("✗ Verification failed")
    
    return all_valid

if __name__ == '__main__':
    skill_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    mode = sys.argv[2] if len(sys.argv) > 2 else 'generate'
    
    if mode == 'verify':
        verify_lock(skill_dir)
    else:
        generate_lock(skill_dir)
