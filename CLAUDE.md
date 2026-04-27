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

# ⚠️ Known GitNexus Indexing Gap (load-bearing — read before trusting `gitnexus_impact`)

GitNexus's scope extractor has a **32 KB-per-file limit** in tree-sitter's binding (upstream bug, [issue #1097](https://github.com/abhigyanpatwari/GitNexus/issues/1097)). Failures show as `scope extraction failed for <file>: Invalid argument` during `npx gitnexus analyze -v`. Confirmed still present on **gitnexus 1.6.4-rc.13** (April 27, 2026) — [PR #1100](https://github.com/abhigyanpatwari/GitNexus/pull/1100) closed only the empty-`__init__.py` half of the bug, not the buffer cap.

**Important:** even when a file *itself* parses cleanly, if its callers or callees live in failing files the relationship edges drop on whichever side fails. So a symbol can show "0 incoming, 0 outgoing" in `gitnexus_context()` and `gitnexus_impact()` will silently report "0 callers, LOW risk" on real symbols that have many callers.

**Affected files** (confirmed `Invalid argument` on rc.13 with `-v` and `--max-file-size 32768`):

```
mud/skills/handlers.py            mud/handler.py
mud/combat/engine.py              mud/persistence.py
mud/game_loop.py                  mud/mobprog.py
mud/mob_cmds.py                   mud/models/character.py
mud/commands/build.py             mud/commands/dispatcher.py
mud/commands/shop.py              mud/spawning/reset_handler.py
mud/account/account_service.py    mud/net/connection.py
mud/imc/__init__.py
tests/test_imc.py                 tests/test_combat_death.py
tests/test_db_resets_rom_parity.py tests/test_shops.py
tests/test_skill_combat_rom_parity.py tests/test_spec_funs.py
tests/test_spawning.py            tests/integration/test_consumables.py
tests/integration/test_equipment_system.py
```

**Verified failure modes** (April 27, 2026, gitnexus 1.6.4-rc.13):
- `mud/commands/inventory.py::do_get` — file parses now but symbol still shows 0 in / 0 out (callers in `mud/commands/dispatcher.py`, which still fails).
- `mud/handler.py::extract_obj` and `mud/combat/engine.py::one_hit` — not in the graph at all.

**When your target is in one of those files, or a likely caller/callee is, do this instead:**

1. Run `gitnexus_impact` anyway. If it returns 0 callers / LOW risk on a clearly hot symbol, **do not trust it**.
2. Fall back to `grep -rn "<symbol_name>" mud/ tests/` for callers.
3. Run the relevant integration suite (`pytest tests/integration/test_<area>.py -v`) to catch regressions the static graph would have flagged.
4. Still report the (untrusted) `gitnexus_impact` result to the user with the caveat — do not pretend the symbol is safe.

This warning sits **above** the "MUST run impact analysis" rule below, not against it. Always run `gitnexus_impact`; just don't believe a clean result on a listed file. Tracked upstream — re-verify after the next gitnexus release and trim this section if the file list shrinks meaningfully.

**Operational note:** when re-running `npx gitnexus analyze`, pass `--skip-agents-md` if you don't want it to rewrite the auto-managed block in CLAUDE.md/AGENTS.md. The auto-update only touches text inside the `gitnexus:start`/`gitnexus:end` markers — this section sits *above* those markers on purpose so it survives. Pass `-v` to see scope-extraction errors at all on rc.x; the new RC is silent on per-file failures by default.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **rom24-quickmud-python** (33687 symbols, 56271 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
