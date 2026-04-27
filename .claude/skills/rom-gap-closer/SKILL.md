---
name: rom-gap-closer
description: Close a single ROM parity gap by ID (e.g. DROP-001, ENTER-002, GET-013, HANDLER-014, QUAFF-001). Use when the user names a specific gap to fix, or when working through gaps from a docs/parity/<FILE>_C_AUDIT.md audit. Runs the standard TDD close flow: locate ROM C lines, locate Python entry point, gitnexus_impact upstream, write a failing integration test in tests/integration/, implement the fix in mud/, update the audit doc row to FIXED, add a CHANGELOG entry, and produce a single feat(parity) or fix(parity) commit. Not for bulk audits — use rom-parity-audit for those.
---

# ROM Gap Closer (single gap, TDD)

You are closing exactly one ROM parity gap identified by a stable ID like `DROP-001` or `ENTER-002`. One gap = one test = one commit.

## Inputs

- A gap ID (e.g. `DROP-001`).
- The gap row in `docs/parity/<FILE>_C_AUDIT.md` (find by grepping for the ID).

If the gap ID isn't documented yet, stop and run `rom-parity-audit` on the file first to get a stable ID.

## Mandatory pre-flight

Read these every time — they encode rules that have caused regressions when skipped:

- `AGENTS.md` ROM Parity Rules section (RNG, integer math, flag enums, attribute names).
- The gap row itself in the audit doc (severity, ROM C reference, Python reference).
- `docs/ROM_PARITY_VERIFICATION_GUIDE.md` "Common Parity Pitfalls" section.

## The flow

### 1. Locate

- Read the ROM C lines named in the gap row (`src/<file>.c:NNN-MMM`). Read the **whole** function, not just the cited line — context determines whether the fix needs surrounding state.
- Read the Python entry point named in the gap row (`mud/.../<file>.py:NNN`).
- Confirm with `gitnexus_context({name: "<python_function>"})` — verify the symbol still exists at the path the audit doc claims.

### 2. Impact analysis (mandatory)

Run `gitnexus_impact({target: "<python_function>", direction: "upstream"})`. Report blast radius (callers, processes, risk) to the user before editing. **Stop and ask** if the result is HIGH or CRITICAL — per CLAUDE.md, do not proceed silently.

### 3. Write the failing test first

- Decide which `tests/integration/test_<area>.py` the test belongs in (existing file with related tests, or a new one if no fit).
- Use the fixtures in `tests/integration/conftest.py` (`movable_char_factory`, `place_object_factory`, `portal_factory`, etc. — see AGENTS.md).
- The autouse `rng_mm.seed_mm(12345)` fixture runs for every integration test; do not remove it. If you need a specific seed, call `rng_mm.seed_mm(<seed>)` inside the test after fixture setup.
- Cite ROM C in a comment: `# mirrors ROM src/<file>.c:NNN — <one-line description>`.
- Run the new test and **verify it fails** for the expected reason. A test that passes before the fix is a broken test.

### 4. Implement the fix

- Edit only the Python file(s) under `mud/`. Never edit `src/`.
- Follow ROM Parity Rules (AGENTS.md): `rng_mm.number_*`, `c_div`/`c_mod`, IntEnum flags, `char.equipment[WearLocation.X]`, `char.inventory`, `room.people`.
- Add a code comment citing the ROM C source on parity-sensitive lines: `# mirroring ROM src/<file>.c:NNN`.
- Re-run the test — must pass.
- Run the broader area suite: `pytest tests/integration/test_<area>.py -v`. Must be green (or only documented pre-existing skips).

### 5. Update tracker + changelog

- Flip the gap row in `docs/parity/<FILE>_C_AUDIT.md`: status 🔄 OPEN → ✅ FIXED. Add a one-line note with commit reference.
- Update CHANGELOG.md under `## [Unreleased]`:
  - `Added` for new behavior (e.g. new TO_ROOM broadcast).
  - `Fixed` for divergence from ROM.
  - Reference the gap ID: `Fixed: DROP-001 — TO_ROOM "$n drops $p." broadcast (src/act_obj.c:768).`

### 6. Pre-commit verification

Run, in order:

```bash
pytest tests/integration/test_<area>.py -v   # area suite green
ruff check .                                  # lint clean
gitnexus_detect_changes()                     # confirm scope
```

If `gitnexus_detect_changes` shows symbols affected outside what the gap should touch, stop and investigate before committing.

### 7. Commit

One commit per gap. Conventional commit style:

```
fix(parity): <FILE>:<gap-id> — <one-line summary>

ROM C: src/<file>.c:NNN-MMM
Python: mud/.../<file>.py:NNN
Test: tests/integration/test_<area>.py::test_<name>
```

Use `feat(parity)` if the gap is "missing feature" (e.g. ITEM_PILL support added). Use `fix(parity)` for divergences from existing behavior.

## When NOT to use this skill

- Gap not yet documented in an audit doc → run `rom-parity-audit` on the file first.
- Multiple related gaps that share a single test → consider whether they're really one gap; if yes, give them one ID.
- Bug that isn't a ROM parity issue (e.g. Python-only crash) → use `superpowers:systematic-debugging` instead.

## Anti-patterns

- ❌ Skipping the failing-test step. "I'll add a test after the fix" is how regressions ship.
- ❌ Batching multiple gaps in one commit.
- ❌ Editing `src/<file>.c`. Read-only reference.
- ❌ Using `random.*`, `//`, or `%` in the fix. Use `rng_mm`, `c_div`, `c_mod`.
- ❌ Skipping `gitnexus_impact` because "it's a small change". CLAUDE.md says MUST.
- ❌ Hardcoding hex flag values. Use the IntEnum from `mud/models/constants.py`.
