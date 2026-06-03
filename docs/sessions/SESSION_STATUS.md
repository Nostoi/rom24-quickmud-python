# Session Status — 2026-06-03 — diff-harness Phase C containers → INV-039 object-list head-insert (2.13.1)

## Current State

Phase C `diff_harness` Hypothesis widening added container `put`/get-from-container
coverage, which surfaced a structural divergence class: ROM head-inserts objects
into every list (`obj_to_{char,room,obj}`, LIFO) while the Python port appended.

- **INV-039 (OBJECT-LIST-HEAD-INSERT) — ✅ ENFORCED (chokepoints only):** fixed
  the three placement chokepoints to `insert(0, obj)` —
  `Character.add_object` (FINDING-017), `Room.add_object` (FINDING-018),
  `obj_manipulation._obj_to_obj` (FINDING-019). Verified against the live C oracle.
- **Two open siblings filed (not fixed):** FINDING-020 (`remove` re-append loses
  ROM carry-list position — equipment-dict architecture) and FINDING-021
  (`look in <container>` header not capitalized — INV-029 territory).
- **Scope honesty:** INV-039 covers the 3 chokepoints only; ~25 bypass `append`
  placement sites are an open `DIVERGENCE_CLASS_ROSTER` sweep (class 13, to-do #7).
- Three tests that asserted the old append order were corrected to ROM LIFO.

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-03_DIFF_HARNESS_PHASE_C_CONTAINERS_INV039.md](SESSION_SUMMARY_2026-06-03_DIFF_HARNESS_PHASE_C_CONTAINERS_INV039.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.1 |
| Tests | Full suite `pytest` → **5391 passed, 4 skipped**; `ruff check .` clean |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | INV-039 added (object-list head-insert) |
| Open engine bugs | FINDING-020 (remove carry-list position), FINDING-021 (`look in` header cap) — both filed in `tools/diff_harness/FINDINGS.md` |

## Next Intended Task

1. **Class-13 bypass-site sweep** via `/rom-divergence-sweep` (roster to-do #7):
   per-site ROM read of the ~25 remaining `append` placement sites — runtime
   placements should head-insert (route through the chokepoint), reconstruction
   paths (`from_orm`, `clone_object`, serializers) must stay `append`. Not a
   lexical guard.
2. **FINDING-021** — close the `look in <container>` header-cap gap (likely a
   one-line act-cap fix in the do_look-in-container path).
3. Continue Phase C deterministic command/watch-set widening (light hold,
   money/shop paths); add RNG-locked combat only after seed alignment is proven.

## Other open / deferred items

- **FINDING-020** — equipment-dict carry-list-position divergence; needs a scoped
  architectural decision (ROM keeps equipped objects in the carry list), not a
  quick fix.
- **test-fixtures-lint** — manual-staged style lint; re-enable once legacy tests migrate.
- **`test_all_commands.py` `exits` attribute error** — pre-existing harness artifact.
