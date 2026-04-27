# QuickMUD Development Guide for AI Agents

## Purpose

`rom24-quickmud-python` is a **ROM 2.4b6 → Python faithful port**. The goal is
100% behavioral parity with the original C engine, not improvement. When ROM C
behavior is "wrong" or quirky, we replicate it exactly.

The companion browser frontend lives in the sibling project
`quickmud-web-client` (`../quickmud-web-client`) and is versioned independently.

## Source of Truth

- Engine repo (this project): `https://github.com/Nostoi/rom24-quickmud-python`
- Original ROM C source: `src/` (read-only reference; do not modify)
- Frontend repo: `../quickmud-web-client`

Before changing engine behavior, read the corresponding ROM C function. Do not
guess.

---

## ROM Parity Rules (CRITICAL)

These are non-negotiable. Violations are bugs even if tests pass.

- **RNG:** use `mud.math.rng_mm.number_*`, never `random.*` in combat/affects.
- **Integer math:** use `c_div`/`c_mod` from `mud.math.c_compat`, never `//` or `%`.
- **Flag values:** use enums (`PlayerFlag.AUTOLOOT`, `WearFlag.NO_SAC`,
  `WearLocation.HOLD`, …). Never hardcode hex bit values — ROM C uses bit shifts
  and the hex you'd guess from the constant name is often wrong.
  - Wrong: `PLR_AUTOLOOT = 0x00000800`
  - Right: `PlayerFlag.AUTOLOOT`
- **Equipment lookup:** `char.equipment[WearLocation.HOLD]` (IntEnum keyed),
  not `char.equipped["held"]` and not `char.carrying`.
- **Character inventory:** `char.inventory`, not `char.carrying`.
- **Room occupants:** `room.people`, not `room.characters`.
- **Comments:** reference ROM C source on parity-sensitive code, e.g.
  `# mirroring ROM src/fight.c:one_hit`.
- **No deferring.** When an audit finds a missing/partial ROM C function,
  implement it; do not mark it "P2 — optional". ROM parity gaps are always P0.
- **Integration tests are mandatory** for new parity work — they must verify
  ROM behavior, not just code coverage.

Mandatory reading before any audit or integration-test work:
[`docs/ROM_PARITY_VERIFICATION_GUIDE.md`](docs/ROM_PARITY_VERIFICATION_GUIDE.md).

---

## Build / Lint / Test

```bash
# All tests (~16s)
pytest

# Integration tests
pytest tests/integration/ -v

# Coverage gate (CI requires ≥80%)
pytest --cov=mud --cov-report=term --cov-fail-under=80

# Lint / format
ruff check .
ruff format --check .

# Type check (strict on selected modules)
mypy mud/net/ansi.py mud/security/hash_utils.py --follow-imports=skip

# Comprehensive command registration check
python3 test_all_commands.py
```

Three test layers — unit (`tests/test_*.py`), integration
(`tests/integration/`), and command-registry (`test_all_commands.py`). Run all
three when adding commands.

### Test fixtures (from `conftest.py`)

```python
movable_char_factory(name, room_vnum, points=100)
movable_mob_factory(vnum, room_vnum, points=100)
object_factory(proto_kwargs)
place_object_factory(room_vnum, vnum=..., proto_kwargs=...)
portal_factory(room_vnum, to_vnum, closed=False)
ensure_can_move(entity, points=100)
```

Note: `Object.__post_init__` does **not** auto-sync `value` from the prototype.
Test fixtures must do `obj.value = list(proto.value)` after construction.

### Test determinism (RNG)

The Mitchell-Moore RNG (`mud.utils.rng_mm`) is **global mutable state**, so
RNG-dependent tests are flaky if state leaks across test boundaries.

- `tests/integration/conftest.py` has an autouse fixture that calls
  `rng_mm.seed_mm(12345)` before every integration test. Do **not** remove it.
  Without it, tests that depend on probabilistic outcomes (scavenger acts on
  a 1/64 roll, AoE saves, holy_word damage rolls, combat hit/miss) flake on
  ordering. This was added in v2.6.2 — see CHANGELOG.
- If your test needs a specific RNG sequence, call `rng_mm.seed_mm(<seed>)`
  inside the test (after fixture setup) — that overrides the autouse default.
- Never use `random.*` in production code or in tests that are checking ROM
  parity. Use `rng_mm.number_*` so the seed actually controls behavior.
- Don't write a new test that "just runs more iterations until something
  happens" without seeding. That's a flake waiting to surface in CI.

A test asserting a behavior that contradicts ROM C is a bug in the **test**,
not in the implementation. ROM is the source of truth. When a test fails:
read the corresponding ROM C function before assuming the Python code is
wrong. (Example: `test_giant_strength_refuses_to_stack` was originally
`test_stat_modifiers_stack_from_same_spell` — the test asserted stacking,
but ROM `magic.c:3022-3030` explicitly anti-stacks.)

---

## Code Style

- `from __future__ import annotations` first; stdlib / third-party / local.
- Strict type annotations; `TYPE_CHECKING` guard for circular imports.
- `snake_case` functions/vars, `PascalCase` classes, `UPPER_CASE` constants,
  `_prefix` private.
- Public functions have docstrings; parity-sensitive code cites ROM C source.
- Line length 120, double quotes, 4-space indent (ruff/black).

---

## Trackers (single source of truth — do not duplicate status into AGENTS.md)

| File | Purpose | When to update |
|------|---------|----------------|
| `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md` | Per-file ROM C audit status (43 files) | Any audit work |
| `docs/parity/INTEGRATION_TEST_COVERAGE_TRACKER.md` | Coverage of 21 gameplay systems | Adding integration tests |
| `docs/parity/ROM_PARITY_FEATURE_TRACKER.md` | Feature-level parity backlog | Implementing parity features |
| `docs/parity/ACT_OBJ_C_AUDIT.md`, `ACT_INFO_C_AUDIT.md`, etc. | Per-file gap tables (GET-001, PUT-002, …) | Closing specific gaps |
| `PROJECT_COMPLETION_STATUS.md` | Subsystem confidence scores | After major subsystem work |
| `CHANGELOG.md` | User-visible / dev-visible change log | Every push (see Repo Hygiene) |

`TODO.md` and `ARCHITECTURAL_TASKS.md` are historical and complete — do not
update them.

For the audit methodology itself (5 phases, ROM-C → audit doc → implementation
→ integration tests → completion), see
[`docs/ROM_PARITY_VERIFICATION_GUIDE.md`](docs/ROM_PARITY_VERIFICATION_GUIDE.md).

---

## Session Notes

Per-session work logs live under **`docs/sessions/`**. AGENTS.md itself does
**not** carry a running session narrative — keep it stable.

### Conventions

- **Filename:** `SESSION_SUMMARY_YYYY-MM-DD_<short-topic>.md`. Multi-session
  days get distinct topics (`..._ACT_MOVE_COMPLETE.md`,
  `..._ACT_OBJ_C_AUDIT_PHASES_1-4.md`).
- **Handoff documents** (when a session ends mid-stream and another agent
  picks up): `HANDOFF_YYYY-MM-DD_<topic>.md`, also under `docs/sessions/`.
- **Single canonical "current" pointer:** `docs/sessions/SESSION_STATUS.md`
  always reflects the latest state. Newer sessions overwrite it; the old
  contents are preserved in the dated `SESSION_SUMMARY_*.md` for that session.

### Workflow

1. **Start of session:** read `docs/sessions/SESSION_STATUS.md` and the most
   recent `SESSION_SUMMARY_*.md` for context. Skim the relevant tracker docs
   for the active audit.
2. **During session:** keep work-in-progress notes wherever you like, but do
   not commit transient scratch files to the repo root.
3. **End of session:** create `docs/sessions/SESSION_SUMMARY_<date>_<topic>.md`
   summarizing what landed (gaps closed, files touched, tests added). Update
   `docs/sessions/SESSION_STATUS.md` to point at the new summary and state the
   next intended task.
4. **Do not** add session logs to AGENTS.md, README.md, or CHANGELOG.md. Those
   are stable surfaces; sessions are an append-only log.

If you find new `SESSION_SUMMARY_*.md` or `HANDOFF_*.md` files at the repo
root, move them into `docs/sessions/` as part of repo hygiene.

---

## Repo Hygiene

Before pushing changes:

1. **Update `CHANGELOG.md`**
   - Add an entry under `## [Unreleased]` (or the next version section).
   - Format: Keep a Changelog (`Added` / `Changed` / `Fixed` / `Removed`).
   - Summarize user-visible behavior, dev-workflow changes, and important
     fixes — not internal refactors.

2. **Update `README.md` when needed**
   - Setup, usage, architecture, command-parity claims, badges, or test
     counts that changed.
   - Keep ROM-parity status badges honest. Do not claim percentages the
     trackers don't support.

3. **Update the version**
   - Single source: `pyproject.toml` `version = "X.Y.Z"`.
   - Bump on any branch push, PR update, or `master` push intended to be
     shared remotely. Use semver:
     - **patch** — fixes, docs, parity gap closures with no API surface change
     - **minor** — new commands, new gameplay features, new test infrastructure
     - **major** — breaking protocol/save-format/data-model changes
   - Keep the version bump in the same commit/PR as the related code and
     changelog entries.

4. **PR and `master` hygiene**
   - **Before opening or updating a PR:** bump `pyproject.toml` version,
     update `CHANGELOG.md`, update `README.md` if setup/workflow/parity
     status changed.
   - **Before merging or pushing to `master`:**
     - confirm `pyproject.toml` version reflects the full state being merged
     - confirm `CHANGELOG.md` describes the shipped behavior
     - confirm `README.md` still matches current setup and parity status
     - confirm `docs/sessions/SESSION_STATUS.md` is current
   - Treat `master` as the publish-ready branch. Do not push stale versions
     or stale changelog entries to `master`.

5. **Verify**
   - `pytest` passes (or the only failures are the documented pre-existing ones).
   - `ruff check .` clean.
   - For integration-test or audit work, update the relevant tracker doc.
   - Run `gitnexus_detect_changes()` before committing (see GitNexus section).

---

## Specialized Agent Files

| File | Use when |
|------|----------|
| [`AGENT.md`](AGENT.md) | Architectural integration analysis (subsystem confidence < 0.92) |
| [`AGENT.EXECUTOR.md`](AGENT.EXECUTOR.md) | Executing tasks already defined by AGENT.md |
| [`FUNCTION_COMPLETION_AGENT.md`](FUNCTION_COMPLETION_AGENT.md) | Implementing the remaining ~57 unmapped helper functions (optional) |

---

## Autonomous Mode

When the user explicitly says "auto mode" or "complete all tasks":

1. Build a todo list from the relevant tracker docs.
2. Execute sequentially without per-step approval; fix errors immediately.
3. Run `pytest` after each major task; do not proceed past a regression.
4. Update tracker docs and `docs/sessions/SESSION_STATUS.md` as you go.
5. Stop on time limit, scope completion, or unrecoverable error after 3 fix
   attempts.

Auto mode is not a license for destructive operations (force pushes, history
rewrites, dropping data). Those still need explicit confirmation.

---

## GitNexus — Code Intelligence

This project is indexed by GitNexus as **rom24-quickmud-python** (33 200
symbols, 54 952 relationships, 300 execution flows). If any GitNexus tool
warns the index is stale, run `npx gitnexus analyze` first.

### Always Do

- **Run impact analysis before editing any symbol.** Before modifying a
  function, class, or method, run
  `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report
  blast radius (callers, affected processes, risk) to the user.
- **Run `gitnexus_detect_changes()` before committing** to verify your changes
  only affect expected symbols and execution flows.
- **Warn the user** on HIGH/CRITICAL risk before proceeding.
- For unfamiliar code, prefer `gitnexus_query({query: "concept"})` over grep.
- For full context on a symbol (callers, callees, flows), use
  `gitnexus_context({name: "symbolName"})`.

### Never Do

- Edit a function/class/method without first running `gitnexus_impact`.
- Ignore HIGH or CRITICAL risk warnings.
- Rename symbols with find-and-replace — use `gitnexus_rename`.
- Commit without running `gitnexus_detect_changes()`.

### Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/rom24-quickmud-python/context` | Codebase overview, index freshness |
| `gitnexus://repo/rom24-quickmud-python/clusters` | Functional areas |
| `gitnexus://repo/rom24-quickmud-python/processes` | Execution flows |
| `gitnexus://repo/rom24-quickmud-python/process/{name}` | Step-by-step trace |

### Skill files

| Task | Skill file |
|------|-----------|
| "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Refactor / rename | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools / schema | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

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
