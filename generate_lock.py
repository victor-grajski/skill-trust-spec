#!/usr/bin/env python3
"""
skill.lock generator.
Reads skill.toml, hashes all files, outputs skill.lock.
Supports attestation block per skill.lock.md spec with Ed25519 signing.
"""
import base64
import hashlib
import json
import os
import sys
from datetime import datetime
import tomllib

try:
    from nacl.encoding import RawEncoder
    from nacl.signing import SigningKey
    from nacl.public import PrivateKey
    NACL_AVAILABLE = True
except ImportError:
    NACL_AVAILABLE = False

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

def generate_keypair():
    """Generate Ed25519 keypair for signing attestations."""
    if not NACL_AVAILABLE:
        print("Error: pynacl not installed. Run: pip install pynacl")
        sys.exit(1)
    
    private_key = SigningKey.generate()
    public_key = private_key.verify_key
    
    # Return as base58-like (base64url without padding)
    return {
        'private': base64.urlsafe_b64encode(bytes(private_key)).decode('utf-8').rstrip('='),
        'public': base64.urlsafe_b64encode(bytes(public_key)).decode('utf-8').rstrip('=')
    }

def load_or_generate_keypair(key_dir='.'):
    """Load existing keypair or generate new one."""
    priv_path = os.path.join(key_dir, '.attestation.key')
    pub_path = os.path.join(key_dir, '.attestation.pub')
    
    if os.path.exists(priv_path) and os.path.exists(pub_path):
        with open(priv_path, 'r') as f:
            priv_key = f.read().strip()
        with open(pub_path, 'r') as f:
            pub_key = f.read().strip()
        return {'private': priv_key, 'public': pub_key}
    else:
        keys = generate_keypair()
        # Save keys
        with open(priv_path, 'w') as f:
            f.write(keys['private'])
        os.chmod(priv_path, 0o600)  # Secure permissions
        with open(pub_path, 'w') as f:
            f.write(keys['public'])
        print(f"Generated new Ed25519 keypair in {key_dir}")
        return keys

def sign_scope_hash(scope_hash, private_key_b64):
    """Sign the scope_hash with Ed25519 private key."""
    if not NACL_AVAILABLE:
        return ""
    
    # Decode base64url private key
    padding = 4 - len(private_key_b64) % 4
    if padding != 4:
        private_key_b64 += '=' * padding
    priv_bytes = base64.urlsafe_b64decode(private_key_b64)
    
    signing_key = SigningKey(priv_bytes)
    signature = signing_key.sign(scope_hash.encode('utf-8'), encoder=RawEncoder)
    
    # Return signature as base64url
    return base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')

def compute_chain_id(public_key_b64):
    """Compute chain_id as first 16 hex chars of SHA256(public_key)."""
    padding = 4 - len(public_key_b64) % 4
    if padding != 4:
        public_key_b64 += '=' * padding
    pub_bytes = base64.urlsafe_b64decode(public_key_b64)
    
    h = hashlib.sha256()
    h.update(pub_bytes)
    return h.hexdigest()[:16]

def compute_issuer_id(public_key_b64):
    """Compute issuer_id in did:isnad format."""
    return f"did:isnad:{public_key_b64}"

def generate_lock(skill_dir='.', compute_attestation=False, sign=True):
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
    if compute_attestation and attestation and sign and NACL_AVAILABLE:
        # Generate or load keypair for signing
        keys = load_or_generate_keypair(skill_dir)
        
        # Compute scope_hash from content BEFORE attestation block
        content_before_attestation = '\n'.join(lines[:attestation_start_idx])
        scope_hash = compute_scope_hash(content_before_attestation)
        
        # Sign the scope_hash
        signature = sign_scope_hash(scope_hash, keys['private'])
        chain_id = compute_chain_id(keys['public'])
        issuer_id = compute_issuer_id(keys['public'])
        
        # Get subject_id from skill.toml or use issuer_id as default
        subject_id = attestation.get('subject_id', issuer_id)
        
        lines.append("[attestation]")
        lines.append(f'issuer_id = "{issuer_id}"')
        lines.append(f'subject_id = "{subject_id}"')
        lines.append(f'signature = "{signature}"')
        lines.append(f'chain_id = "{chain_id}"')
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
    elif mode == 'attest':
        generate_lock(skill_dir, compute_attestation=True, sign=True)
    else:
        generate_lock(skill_dir)
