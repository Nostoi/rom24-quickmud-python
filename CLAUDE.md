@AGENTS.md

# Porting workflow — when to invoke which skill

The ROM 2.4b6 → Python parity loop is encoded in three project-local skills.
Use them; do not re-derive the workflow each session.

| Situation | Skill | Output |
|-----------|-------|--------|
| Starting a file-level audit (e.g. "audit `scan.c`", a P0/P1 file is Partial/Not Audited in `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`) | `/rom-parity-audit` | New/updated `docs/parity/<FILE>_C_AUDIT.md` with stable gap IDs |
| Closing one gap by ID (e.g. "fix `DROP-001`", working through a gap list from an audit doc) | `/rom-gap-closer` | One failing-test-first commit with `feat(parity)` / `fix(parity)` prefix; audit row flipped to ✅ FIXED |
| Wrapping up the session (multiple gaps closed, file just hit 100%, "write the session summary") | `/rom-session-handoff` | New `docs/sessions/SESSION_SUMMARY_<date>_<topic>.md`, refreshed `SESSION_STATUS.md`, CHANGELOG entries, version bump if pushing |
| Per-file audit tracker exhausted; surfacing the next cross-file contract gap (e.g. "scan affect-tick contracts for divergences", "audit position-transition edges") | (no skill — manual probe-then-scope; file as INV-NNN row in `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`) | New ✅ ENFORCED INV row + enforcement test, or single gap-closer commit |

When the per-file audit tracker has no ⚠️ Partial / ❌ Not Audited
rows (current state), **cross-file invariants is the active pass**.
See the "Cross-File Invariants" section in AGENTS.md for the
probe-then-scope method and current candidate areas.

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

# META - MAINTAINING THIS DOCUMENT

## When to Add a New Rule
Add a rule to this document when:
- You make the same mistake twice in one session
- You correct a pattern more than once across sessions
- A user correction reveals a structural assumption you keep getting wrong

## How to Write Good Rules
1. Use absolute directives — start with NEVER or ALWAYS
2. Include the anti-pattern alongside the correct pattern
3. If a rule could be enforced by tooling (ESLint, a hook, a git check),
   note that explicitly so it can be escalated to a hook
4. One rule per behavior — no bundling

## Escalation: When a Rule Should Become a Hook
If you find yourself adding a rule that says "ALWAYS run X before Y", consider whether it should instead be a PostToolUse or PreToolUse hook in .claude/settings.json — hooks are guarantees, rules are suggestions.
   - Repeated style/syntax issue → add an ESLint rule
   - Repeated pre-commit failure → add a Lefthook/husky hook
   - Repeated unsafe tool use → add a PreToolUse hook in .claude/settings.json

# GitNexus Indexing — 32 KB scope-extraction bug RESOLVED on 1.6.5 (verified 2026-05-31)

The tree-sitter scope-extraction bug that used to drop symbols/edges from any
`mud/*.py` file over ~32 KB ([issue #1097](https://github.com/abhigyanpatwari/GitNexus/issues/1097),
`scope extraction failed for <file>: Invalid argument`) is **fixed as of
gitnexus 1.6.5**. The old "Known Indexing Gap" warning here listed ~25
Python files to distrust; that list is obsolete — **do not re-add it**.

**Verification (2026-05-31, forced `analyze -v -f` on 1.6.5):**
- Previously-failing large files now parse with full relationship edges:
  `mud/handler.py` (52 KB) `equip_char` → 7 callers + 2 callees;
  `mud/combat/engine.py` (75 KB) `get_wielded_weapon` → 8 callers;
  `mud/skills/handlers.py` (275 KB) symbols appear as callers. Graph grew to
  ~42.8 K nodes / ~79.5 K edges (was ~39 K / ~65 K).
- **Zero** `Invalid argument` failures on Python files. The only 2 residual
  `scope extraction failed` lines are `src/recycle.h` and `src/olc.h` —
  declaration-only **C reference headers** (read-only ROM source, irrelevant to
  Python parity work), failing for a *different* reason ("no Module scope
  found"), not the byte-buffer cap.

**Net:** `gitnexus_impact` / `gitnexus_context` results on `mud/*.py` are now
trustworthy. The "run it anyway but don't believe a clean result, fall back to
grep" workaround is **retired**. Normal discipline applies: run `gitnexus_impact`
before edits, `gitnexus_detect_changes` before commits, and still cross-check
with the integration suite for behavioral regressions (that's parity hygiene,
not distrust of the graph).

**`--max-file-size` is NOT a knob for this** — per the GitNexus docs and
`--help`, `--max-file-size <kb>` / `GITNEXUS_MAX_FILE_SIZE` (default 512 KB) is a
*walker skip threshold* (which files to exclude), and its hard cap of 32768 *is*
the tree-sitter buffer ceiling. Our source files are already under 512 KB, so
they were never skipped; raising it would not have helped (and didn't, when
tested on rc.13). No GitNexus env var is needed for normal operation here.

**If scope-extraction failures on `mud/*.py` ever reappear** (e.g. a regressed
release): run `npx gitnexus analyze -v -f` and grep the log for
`scope extraction failed|Invalid argument`; if real Python files are listed,
re-instate a grep cross-check for symbols in those files and pin the working
gitnexus version. Otherwise trust the graph.

**Operational note:** when re-running `npx gitnexus analyze`, pass
`--skip-agents-md` so it doesn't rewrite the auto-managed block in
CLAUDE.md/AGENTS.md (the auto-update only touches text inside the
`gitnexus:start`/`gitnexus:end` markers — this section sits *above* them on
purpose). Pass `-v` to surface per-file scope-extraction errors (silent by
default). For long-running hosts (MCP server / CI shell), the useful env knobs
are `GITNEXUS_WORKER_SUB_BATCH_TIMEOUT_MS` (worker idle timeout, default 30000)
and `GITNEXUS_WORKER_POOL_SIZE` — not `GITNEXUS_MAX_FILE_SIZE`.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **rom24-quickmud-python** (39196 symbols, 65340 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> **🛑 STOP-AND-REINDEX RULE — NON-NEGOTIABLE.** The moment ANY GitNexus tool, MCP response, hook output, or PostToolUse message reports "index is stale", "last indexed: <sha>", "FTS index ensure failed", or any equivalent, **you MUST immediately run `npx gitnexus analyze --skip-agents-md` (via the `gitnexus-cli` skill) BEFORE the next non-trivial tool call.** Do not defer. Do not "note it for next session." Do not continue working with a stale graph because "the current task doesn't need it" — every subsequent `gitnexus_impact` / `gitnexus_detect_changes` / `gitnexus_context` call you make on a stale index returns wrong answers, and those wrong answers will mislead the user. Reindex is cheap (~1–3 minutes, run in background); skipping it is expensive (regressions land that impact analysis would have flagged). The ONLY exception is when the reindex itself is what's failing (read-only DB, disk full, etc.) — in that case, surface the failure to the user and stop, do not silently proceed. This rule overrides the "don't reindex mid-session" instinct: if the warning fires, reindex now.

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
