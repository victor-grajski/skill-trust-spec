# skill.lock Specification

The `skill.lock` file is a machine-verifiable lockfile that provides cryptographic guarantees about skill integrity. It is **generated from `skill.toml`**, not written by hand.

---

## Purpose

- Pin exact versions of all dependencies (transitive closure)
- Provide content hashes for verification
- Enable signature/attestation for supply-chain security
- Support freshness checks for version rollback protection

---

## Location

`skill.lock` lives at the root of the skill package, next to `skill.toml`.

---

## Format

`skill.lock` uses TOML format for human readability, but is intended for machine processing.

---

## Sections

### `[manifest]`

Metadata about this lockfile.

| Field | Type | Description |
|-------|------|-------------|
| `name` | String | Skill name (from skill.toml) |
| `version` | String | Skill version (from skill.toml) |
| `generated_at` | String (ISO 8601) | When this lockfile was generated |
| `lockfile_version` | String | Version of the lockfile spec (e.g., "1.0") |

### `[author]`

Author identity information.

| Field | Type | Description |
|-------|------|-------------|
| `sigil_hash` | String (optional) | Sigil public key if present in skill.toml |
| `author_name` | String (optional) | Descriptive name if sigil not used |

### `[[files]]`

Array of all files in the skill package with their hashes.

| Field | Type | Description |
|-------|------|-------------|
| `path` | String | Relative path to file |
| `hash` | String | SHA256 hash of file content (hex) |
| `size` | Integer | File size in bytes |

### `[[dependencies]]`

Array of resolved dependencies (transitive closure).

| Field | Type | Description |
|-------|------|-------------|
| `name` | String | Skill name |
| `version` | String | Exact pinned version (semver) |
| `source` | String | Registry URL or source identifier |
| `hash` | String | SHA256 of the dependency's skill.lock or package |
| `dependencies` | Array (optional) | Nested dependencies (or reference to their lockfiles) |

### `[signature]` (Optional but Recommended)

Cryptographic attestation of this lockfile.

| Field | Type | Description |
|-------|------|-------------|
| `sigstore` | String | Sigstore signature for this lockfile |
| `sigil` | String | Sigil signature for this lockfile |

### `[attestation]` (Optional - for isnad interop)

Link to external attestation chain (e.g., Gendolf's isnad protocol).

**Required fields:**

| Field | Type | Description |
|-------|------|-------------|
| `issuer_id` | String | DID of attestation issuer (e.g., "did:isnad:{base58_ed25519_pubkey}") |
| `subject_id` | String | DID of the subject being attested (skill author or skill itself) |
| `signature` | String | Ed25519 signature over scope_hash (base64-encoded) |
| `chain_id` | String | Attestation chain reference (format: "isnad-v1:{network_id}:{chain_hash}") |
| `timestamp` | String (ISO 8601) | When the attestation was made |
| `scope_hash` | String | SHA256 of skill.lock content excluding the [attestation] block |

**Optional `[attestation.metadata]` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `trust_score` | Float | Trust score (0.0-1.0) from the attestation authority |
| `attestation_type` | String | Type of attestation (e.g., "skill_audit", "identity_proof") |
| `valid_until` | String (ISO 8601) | Expiration date of this attestation |

**chain_id format:** `isnad-v1:{network_id}:{chain_hash}`
- `network_id`: federation network ("mainnet", "testnet", or custom)
- `chain_hash`: first 8 chars of SHA-256 of the trust chain root attestation

**Example:**
```toml
[attestation]
issuer_id = "did:isnad:7Hk2PVLYzQm8NKpLwXqZ..."
subject_id = "did:isnad:9Xp4RWLZyNk3MLqRsTvw..."
signature = "base64_ed25519_signature_here"
chain_id = "isnad-v1:mainnet:a1b2c3d4"
timestamp = "2026-02-22T07:00:00Z"
scope_hash = "sha256:abc123def456..."

[attestation.metadata]
trust_score = 0.92
attestation_type = "skill_audit"
valid_until = "2026-08-22T07:00:00Z"
```

This field enables interoperability with external trust systems like isnad-rfc. The `scope_hash` is deterministic — verification recomputes the hash of skill.lock content excluding the [attestation] block, then verifies the Ed25519 signature against it.

### `[update]`

Freshness and update checking.

| Field | Type | Description |
|-------|------|-------------|
| `update_check_url` | String | URL to check for newer versions |
| `last_verified` | String (ISO 8601) | When this lockfile was last verified fresh |
| `registry_index` | String | URL of registry index for this skill |

---

## Generation Process

1. Parse `skill.toml` to extract metadata and version constraints
2. Resolve dependencies: for each dependency, find latest version matching constraints
3. Recursively resolve transitive dependencies
4. Calculate SHA256 hash for every file in the skill package
5. Record exact pinned versions and hashes
6. Add update check metadata
7. Optionally sign with Sigstore and/or Sigil
8. Write `skill.lock`

---

## Verification Process

When an agent installs a skill:

1. Download `skill.toml` and `skill.lock`
2. Verify `skill.lock` signature (if present)
3. Verify `skill.lock` hasn't been tampered with (self-check hash)
4. Download all files listed in `[[files]]`
5. Verify each file's SHA256 matches the lockfile
6. Recursively verify all `[[dependencies]]` using their lockfiles
7. Check `last_verified` timestamp and `update_check_url` for freshness

---

## Example

See `/example/skill.lock` for a complete example with a hypothetical "weather-check" skill.

---

## Security Notes

- The lockfile itself should be hashed and that hash stored/checked
- Signatures provide non-repudiation: the author attests this is the correct content
- Without signatures, the lockfile provides integrity but not authenticity (rely on TLS + registry trust)
- Agents should cache verified lockfiles to avoid redundant verification
