---
description: "Update the CHANGELOG.md after completing a task. Use after: finishing a feature, fixing a bug, updating docs, changing config, any notable modification."
---

Update `CHANGELOG.md` with an entry for the work just completed.

## Format

Follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/):

```markdown
## [Unreleased]

### Added
- New features or capabilities

### Changed
- Modifications to existing functionality

### Fixed
- Bug fixes

### Removed
- Removed features or files

### Security
- Security-related changes

### Deprecated
- Soon-to-be removed features
```

## Rules

1. **Always add under `## [Unreleased]`** — never create a new version header (that's done at release time)
2. **One bullet per logical change** — concise, starts with lowercase verb
3. **Group by type** — use the correct subsection (Added/Changed/Fixed/etc.)
4. **Reference context** — mention file, endpoint, or component affected
5. **No duplicate entries** — check existing bullets before adding
6. **Keep chronological** — newest entries at the top of each section

## Examples

Good:
```markdown
### Added
- `vt-docs-writer` and `vt-docs-reviewer` agents for documentation workflow
- cursor-based pagination for `/v1/news` endpoint

### Fixed
- rate limiter returning 500 instead of 429 on quota exceeded
- broken internal link to authentication guide

### Changed
- migrated HTTP client from requests to httpx for async support
```

Bad:
```markdown
### Added
- Updated stuff
- Fixed things
- Added new feature
```
