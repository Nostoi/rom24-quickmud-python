@AGENTS.md

# Porting workflow — when to invoke which skill

The ROM 2.4b6 → Python parity loop is encoded in three project-local skills.
Use them; do not re-derive the workflow each session.

| Situation | Skill | Output |
|-----------|-------|--------|
| Starting a file-level audit (e.g. "audit `scan.c`", a P0/P1 file is Partial/Not Audited in `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`) | `/rom-parity-audit` | New/updated `docs/parity/<FILE>_C_AUDIT.md` with stable gap IDs |
| Closing one gap by ID (e.g. "fix `DROP-001`", working through a gap list from an audit doc) | `/rom-gap-closer` | One failing-test-first commit with `feat(parity)` / `fix(parity)` prefix; audit row flipped to ✅ FIXED |
| Wrapping up the session (multiple gaps closed, file just hit 100%, "write the session summary") | `/rom-session-handoff` | New `docs/sessions/SESSION_SUMMARY_<date>_<topic>.md`, refreshed `SESSION_STATUS.md`, CHANGELOG entries, version bump if pushing |

Decision tree:

1. **Is the gap already documented with a stable ID in `docs/parity/<FILE>_C_AUDIT.md`?**
   - No → invoke `rom-parity-audit` first to produce the audit doc and gap IDs.
   - Yes → continue.
2. **Are you closing one specific gap?**
   - Yes → invoke `rom-gap-closer` with the ID.
   - No (multiple gaps in one go) → invoke `rom-gap-closer` once per gap, sequentially. One gap = one test = one commit. Do not batch.
3. **Done with the session's work?**
   - Yes → invoke `rom-session-handoff` to write the summary, refresh `SESSION_STATUS.md`, update CHANGELOG, and bump version if anything is being pushed.

These skills sit on top of (and call out to) the existing rules:

- ROM Parity Rules from `AGENTS.md` (RNG via `rng_mm`, integer math via `c_div`/`c_mod`, IntEnum flags, `char.equipment[WearLocation.X]`, `char.inventory`, `room.people`).
- GitNexus discipline from this file (`gitnexus_impact` before edits, `gitnexus_detect_changes` before commits).
- TDD discipline from `superpowers:test-driven-development` (failing test before implementation).

Do not invoke `rom-gap-closer` without a documented gap ID. Do not invoke `rom-parity-audit` for a single-gap fix. Do not skip `rom-session-handoff` at session end — `SESSION_STATUS.md` and `CHANGELOG.md` rot fast otherwise.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **rom24-quickmud-python** (33689 symbols, 56215 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/rom24-quickmud-python/context` | Codebase overview, check index freshness |
| `gitnexus://repo/rom24-quickmud-python/clusters` | All functional areas |
| `gitnexus://repo/rom24-quickmud-python/processes` | All execution flows |
| `gitnexus://repo/rom24-quickmud-python/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
