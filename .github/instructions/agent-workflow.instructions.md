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
