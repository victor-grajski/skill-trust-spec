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
