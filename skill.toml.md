# skill.toml Specification

The `skill.toml` file is a human-readable manifest that describes a skill. Authors write this file by hand (or generate it). It declares intent; the actual security guarantees come from `skill.lock`.

---

## Location

`skill.toml` lives at the root of the skill package, next to `skill.lock`.

---

## Required Fields

### `name`
- **Type:** String
- **Format:** kebab-case, alphanumeric + hyphens only
- **Example:** `"weather-check"`, `"file-utils"`
- **Description:** Unique identifier for the skill within the registry namespace

### `version`
- **Type:** String
- **Format:** [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH)
- **Example:** `"1.2.3"`
- **Description:** Version of this skill release

### `description`
- **Type:** String
- **Max Length:** 280 characters
- **Example:** `"Fetch current weather conditions for any city"`
- **Description:** Human-readable summary of what the skill does

---

## Author Identity

Exactly one of the following must be present:

### `sigil_hash` (Recommended)
- **Type:** String
- **Format:** Sigil public key (43-character Base64URL)
- **Example:** `"6LEMWpt1U8npqN4mKdcoW8UUQNPbXenXEd2NZabzyGrN"`
- **Description:** Cryptographic identity of the skill author. Agents can verify this against the Sigil protocol to confirm authorship.

### `author_name` (Fallback)
- **Type:** String
- **Example:** `"Victor Grajski"`, `"OpenClaw Team"`
- **Description:** Descriptive author name. Not cryptographically verifiable. Use only when Sigil is unavailable; implies trust-on-first-use or external verification.

---

## Optional Fields

### `dependencies`
- **Type:** Array of tables
- **Description:** Other skills this skill depends on

Each dependency entry:
```toml
[[dependencies]]
name = "http-client"        # Required: skill name
version = ">=2.0.0, <3.0.0" # Required: version constraint (semver range)
optional = false            # Optional: default false
```

Version constraints use [semantic versioning range syntax](https://docs.npmjs.com/cli/v6/using-npm/semver#ranges):
- `1.2.3` — exact version
- `^1.2.3` — compatible with (>=1.2.3 <2.0.0)
- `~1.2.3` — approximately equivalent to (>=1.2.3 <1.3.0)
- `>=1.0.0` — greater than or equal to
- `^1.0.0 || ^2.0.0` — union of ranges

### `update_policy`
- **Type:** String
- **Values:** `"auto"`, `"manual"`, `"notify"`
- **Default:** `"notify"`
- **Description:** How the agent should handle updates:
  - `auto`: Automatically install new compatible versions
  - `manual`: Only install when explicitly requested
  - `notify`: Alert user/agent that updates are available but don't install

### `repository`
- **Type:** String (URL)
- **Example:** `"https://github.com/example/skill-name"`
- **Description:** Source code repository for the skill

### `license`
- **Type:** String
- **Example:** `"MIT"`, `"Apache-2.0"`, `"Proprietary"`
- **Description:** SPDX license identifier or "Proprietary"

---

## Complete Example

```toml
# skill.toml - Human-readable manifest
# This file declares intent. Security guarantees come from skill.lock.

name = "weather-check"
version = "1.2.3"
description = "Fetch current weather conditions for any city using OpenWeatherMap"

# Author identity - use sigil_hash for cryptographic verification
sigil_hash = "6LEMWpt1U8npqN4mKdcoW8UUQNPbXenXEd2NZabzyGrN"
# Alternative (not recommended): author_name = "Victor Grajski"

# How updates are handled
update_policy = "notify"

# Optional metadata
repository = "https://github.com/example/weather-check-skill"
license = "MIT"

# Dependencies with version constraints
# The actual pinned versions will be in skill.lock
[[dependencies]]
name = "http-client"
version = "^2.0.0"

[[dependencies]]
name = "json-parser"
version = "~1.5.0"

[[dependencies]]
name = "geo-location"
version = ">=1.0.0, <2.0.0"
optional = true
```

---

## Notes

- `skill.toml` is for humans to read and write
- `skill.lock` is for machines to verify—it's generated from `skill.toml`
- Version constraints in `skill.toml` express flexibility; exact pins in `skill.lock` provide security
- Authors should commit both files to version control
