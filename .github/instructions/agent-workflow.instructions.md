---
description: "Shared workflow rules for all VecTrade agents. Defines the standard process for completing tasks: implement → test → document → changelog."
applyTo: "**/*.agent.md"
---

# VecTrade Agent Workflow

All agents MUST follow this workflow when completing tasks:

## Task Completion Checklist

After finishing any task (feature, fix, refactor, docs, config change):

1. **Implement** — Make the code/content changes
2. **Verify** — Run relevant checks (lint, test, build, typecheck)
3. **Changelog** — Update `CHANGELOG.md` under `[Unreleased]` with a bullet describing the change
4. **Commit** — Use conventional commit format: `type(scope): description`

## Commit Message Format

```
type(scope): short description

[optional body]
```

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`, `perf`, `style`

Examples:
```
feat(quotes): add batch quote endpoint support
fix(auth): handle expired tokens with proper 401 response
docs(guides): add webhook setup tutorial
chore(deps): update httpx to 0.27.0
```

## Changelog Rules

- ALWAYS update `CHANGELOG.md` after completing work
- Add entry under `## [Unreleased]` in the correct section (Added/Changed/Fixed/etc.)
- One concise bullet per logical change
- Reference the affected component/file/endpoint
- Never create version headers (done at release time)

## When NOT to Update Changelog

- Typo fixes in comments/docs (too trivial)
- CI-only changes that don't affect users
- Reformatting without behavior change

## Architecture Decision Records (ADRs)

For platform-wide "why" decisions (tech choices, pattern changes, deprecations), create an ADR in `vectrade-core/docs/decisions/` instead of a changelog entry.

Use ADR when:
- Choosing a technology or library
- Changing an architectural pattern
- Deprecating an approach
- Making a cross-repo decision

ADRs are NOT for: bug fixes, feature implementation details, or routine changes.

## Version & Release Discipline

### Version Source of Truth

| Component | Version location | Current |
|-----------|-----------------|---------|
| Platform changelog | `vectrade-core/web/site/docs/general/platform/changelog.md` | v2.5.0 |
| Python SDK | `vectrade-python/pyproject.toml` | 1.0.0 |
| Node SDK | `vectrade-node/package.json` | 1.0.0 |
| AI Provider | `vectrade-ai-provider/package.json` | 1.0.0 |
| MCP Server | `vectrade-mcp/package.json` | 1.0.0 |
| CLI | `vectrade-cli/Makefile` (git tag) | — |
| FinKit | `finkit/pyproject.toml` | 1.0.0 |
| OpenAPI Spec | `vectrade-openapi/pyproject.toml` | 1.0.0 |
| Public docs | `vectrade-docs/changelog.mdx` | — |

### Rules

1. **When bumping a version** in `pyproject.toml` or `package.json`, you MUST also add a release entry in that repo's `CHANGELOG.md` (move `[Unreleased]` items under a new `## [x.y.z] — YYYY-MM-DD` header)
2. **SDK versions** are independent of the platform version. SDKs version by their own API surface changes (semver)
3. **Platform changelog entries** (v2.1, v2.5, etc.) are marketing milestones tracked in `vectrade-core/web/site/docs/general/platform/changelog.md` — NOT the same as package versions
4. **vectrade-docs must stay aligned**: when releasing an SDK version, update `vectrade-docs/sdks/` and `vectrade-docs/changelog.mdx` to reflect new install instructions or breaking changes
5. **Never reference platform changelog numbers** (v2.1, v2.5) as software versions — they are release note identifiers only

### Version Bump Policy (STRICT)

All packages are currently at **1.x**. The following rules are enforced:

| Bump | When | Example |
|------|------|---------|
| **Patch** (1.0.x → 1.0.1) | Bug fixes, dependency updates, typo fixes, small improvements | 1.0.0 → 1.0.1 |
| **Minor** (1.x.0 → 1.1.0) | New features, new endpoints, meaningful changes | 1.0.0 → 1.1.0 |
| **Major** (1.x → 2.0) | ⛔ **NEVER without explicit human approval** | — |

🚫 **NEVER bump to 2.0.0** (or any major version increase) without the project owner's explicit signal. This applies to ALL packages. If you believe a breaking change warrants a major bump, propose it in the CHANGELOG under `[Unreleased]` and flag it — do NOT bump the version yourself.

### Cross-Repo Propagation

When a change in one repo requires updates elsewhere:

| Change in | Must also update |
|-----------|-----------------|
| `vectrade-core` (new API endpoint) | `vectrade-openapi` spec → `vectrade-python` + `vectrade-node` SDKs → `vectrade-docs` |
| `vectrade-python` or `vectrade-node` (version bump) | `vectrade-docs/sdks/` install instructions + `vectrade-docs/changelog.mdx` |
| `vectrade-openapi` (spec change) | Run SDK generator → update SDKs → update docs |
| `vectrade-core` auth gateway (error codes) | `vectrade-python` + `vectrade-node` error handling |
| `finkit` (new feature) | `vectrade-docs/resources/` if user-facing |

### LLM-Generated Content: Version References

When generating social posts, emails, or marketing content:
- NEVER invent version numbers — check the actual `pyproject.toml`/`package.json`
- Platform changelog numbers (v2.1, v2.5) are NOT the SDK version
- If referencing a release, cite the correct SDK version from the source of truth table above
