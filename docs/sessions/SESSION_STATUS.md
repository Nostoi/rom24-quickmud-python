# Session Status — 2026-06-10 — INV-043 Nuke-Pets Stop-Fighting (2.13.85)

## Current State

- **Active mode**: cross-file invariants pass
- **Last completed**:
  - **INV-043 NUKE-PETS-STOP-FIGHTING** — found and fixed a real ghost-fighting-pointer bug.
    `mud/combat/death.py:_nuke_pets` now calls `stop_fighting(pet, both=True)` before
    `character_registry.remove(pet)`. ROM `src/act_comm.c:nuke_pets` → `extract_char(pet, TRUE)`
    → `src/handler.c:stop_fighting(pet, TRUE)` clears all fighters targeting the extracted pet;
    Python's manual extraction path was missing this sweep. Two mutation-verified tests in
    `tests/integration/test_inv043_nuke_pets_stop_fighting.py`. Cross-file tracker: 28 enforced
    INVs; next free ID: **INV-044**.
  - **Group XP penalty signed-math probe** — confirmed clean. `mud/combat/engine.py:1358`
    correctly uses `c_div(2 * (floor - victim.exp), 3) + 50`. No gap.
  - **`char_update` autosave slot coherence probe** — confirmed clean. `Session.descriptor_id`
    is `count(1)` (sequential, equivalent to ROM socket fds); rotation math identical; `desc is
    not None` gate matches ROM. `id()` fallback on game_loop.py:945 is dead code in production.
  - Previous session's INV-042 kill-death-XP-trigger ordering (2.13.84).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-10_INV043_NUKE_PETS_STOP_FIGHTING.md](SESSION_SUMMARY_2026-06-10_INV043_NUKE_PETS_STOP_FIGHTING.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.85 |
| Tests | 5554 passed, 4 skipped (full suite) |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-INV rows | 28 enforced (next free ID: INV-044) |
| Diff-harness scenarios | 40 scenarios, 67 C-oracle tests passing, 0 skipped, 0 xfailed |
| FINDINGS.md highest ID | FINDING-033 (✅ RESOLVED — all findings resolved) |

## Next Intended Task

Cross-file invariants remains the active pass.

1. **Affect expiry → `affect_remove` → `affect_check` ordering** — when a raw `AffectData`
   with `duration == 0` expires, `tick_spell_effects` calls `affect_remove` which calls
   `affect_modify(FALSE)` then `affect_check`. ROM `src/handler.c:1317-1348 affect_remove`
   clears the bitvector then re-sets it only if another affect still provides it. The
   cross-file chain `affects/engine.py → handler.py:affect_remove → handler.py:affect_check`
   is the probe area. INV-015 covers the entry point; whether `affect_check` correctly
   re-sets bitvectors from remaining affects is unverified under the cross-INV lens.
   Probe method: read `src/handler.c:1317-1348` → `mud/handler.py:affect_remove` →
   `mud/handler.py:affect_check` → write one failing test if a gap is found.

2. **`do_flee` / `do_recall` position-transition coherence** — ROM `src/fight.c:3022-3095`
   calls `stop_fighting(ch, TRUE)` on both the fleeing character and the victim before
   moving the character. Python's flee path needs a probe to verify the same ordering
   (stop fighting before char_from_room). Probe method: read ROM C → grep Python flee →
   confirm ordering with a test if needed.

3. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.
