# Skill Trust Manifest Threat Model

This document describes the security threats the skill trust manifest system defends against. The goal is to enable agents to install skills with confidence that they are receiving the code the author intended.

---

## Attack: MITM (Man-in-the-Middle)

**Description:** An attacker intercepts the skill download and modifies its content—injecting malicious code, changing behavior, or replacing the entire skill.

| Attribute | Assessment |
|-----------|------------|
| **Severity** | Critical |
| **Likelihood** | Medium-High (if downloading over HTTP or without verification) |
| **Impact** | Complete compromise of agent executing the skill |

**Mitigation:**
- All skill content is hashed (SHA256) and recorded in `skill.lock`
- Agents verify downloaded content against stored hashes before execution
- HTTPS/TLS for all skill registry communications
- Optional: Content signatures via Sigstore for additional non-repudiation

---

## Attack: Supply Chain Poison

**Description:** A malicious dependency (direct or transitive) is introduced into the skill's dependency tree. The skill itself is legitimate, but a dependency executes harmful code.

| Attribute | Assessment |
|-----------|------------|
| **Severity** | Critical |
| **Likelihood** | Medium (dependencies are common, poisoned ones are rare but high-impact) |
| **Impact** | Same as skill compromise—full agent control via dependency |

**Mitigation:**
- `skill.lock` pins exact versions of all transitive dependencies
- Dependencies are also skills with their own `skill.lock` files
- Agents recursively verify entire dependency tree before installation
- No automatic resolution of version ranges at install time—only exact pins from lockfile
- Registry maintains historical integrity (immutable versions)

---

## Attack: Author Spoofing

**Description:** An attacker publishes a skill claiming to be a trusted author (e.g., "Victor Grajski") when they are not.

| Attribute | Assessment |
|-----------|------------|
| **Severity** | High |
| **Likelihood** | Medium (trivial to claim any name, harder to forge cryptographic identity) |
| **Impact** | User trust misplaced, may install malicious code believing it trusted |

**Mitigation:**
- `skill.toml` supports `sigil_hash` for cryptographic author identity (Sigil protocol)
- `sigil_hash` format: `6LEMWpt1U8npqN4mKdcoW8UUQNPbXenXEd2NZabzyGrN`
- Agents can verify Sigil identity against known-good values
- Fallback: `author_name` is descriptive only (trust-on-first-use or external verification)
- Optional: Sigstore signatures in `skill.lock` for supply-chain attestation

---

## Attack: Version Rollback

**Description:** An attacker forces installation of an older, vulnerable version of a skill instead of the latest secure version.

| Attribute | Assessment |
|-----------|------------|
| **Severity** | High |
| **Likelihood** | Low-Medium (requires compromising update mechanism or registry) |
| **Impact** | Exploitation of known vulnerabilities in older versions |

**Mitigation:**
- `skill.lock` includes `last_verified` timestamp
- `skill.lock` includes `update_check_url` for freshness validation
- Agents can check if newer versions exist before installation
- Update policies: `auto`/`manual`/`notify` give users control over update behavior
- Registry should reject re-publishing of existing versions (immutable)

---

## Attack: Lockfile Tampering

**Description:** An attacker modifies `skill.lock` to substitute malicious hashes or redirect to malicious sources.

| Attribute | Assessment |
|-----------|------------|
| **Severity** | Critical |
| **Likelihood** | Low (requires write access to skill package) |
| **Impact** | Agent installs malicious code believing it verified |

**Mitigation:**
- `skill.lock` is generated, not hand-written
- Optional: Sigstore signing of `skill.lock` creates attestation
- Agents verify lockfile signature before trusting its contents
- Lockfile includes self-check: hash of the lockfile itself

---

## Summary: Trust Assumptions

The minimal trust model for safe skill installation:

1. **Registry**: Honest-but-curious (serves correct content, doesn't modify packages)
2. **Author Identity**: Either cryptographically verified (Sigil) or trusted-on-first-use
3. **Dependencies**: Same guarantees recursively apply to entire tree
4. **Agent User**: Reviews update policy and author identity appropriately

**Non-goals:**
- We do not verify that skill code is "good" or "safe"—only that it's the code the author published
- We do not prevent author maliciousness—only impersonation
- We do not guarantee availability—only integrity

---

## Minimal Guarantees

With this threat model addressed, an agent installing a skill receives these guarantees:

✅ The skill content matches what was published (hash verification)  
✅ All dependencies are exactly as specified (lockfile pins)  
✅ The author is who they claim to be (Sigil verification)  
✅ No silent downgrades to vulnerable versions (freshness check)  

This is "the smallest set of guarantees that lets an agent install a skill without paranoia."
