# Session Status — 2026-06-03 — `look in <container>` header/empty parity (FINDING-021) (2.13.2)

## Current State

- **Active mode**: cross-file invariants / divergence-class sweep (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **INV-039 OBJECT-LIST-HEAD-INSERT** — the prior session's complete-but-
    uncommitted head-insert work committed intact (`cdaaa31f`): three placement
    chokepoints `insert(0, obj)`, three corrected order tests.
  - **FINDING-021** — ✅ FIXED (`f34efe75`): `look in <container>` header now
    act-capitalized (`A bag holds:`) and an empty container prints `Nothing.`
    (ROM `show_list_to_char`), replacing the invented `"a bag is empty."`. Drink-con
    `"It is empty."` left untouched (genuine ROM).
- **Newly filed open**: **FINDING-022** — `look in` contents lines carry a 2-space
  indent ROM omits for a PC (source-suspected, not yet oracle-confirmed).

- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-03_LOOK_IN_CONTAINER_FINDING021.md](SESSION_SUMMARY_2026-06-03_LOOK_IN_CONTAINER_FINDING021.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.2 |
| Tests | Full suite `pytest` → **5393 passed, 4 skipped**; `ruff check .` clean |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | INV-039 (object-list head-insert) committed this session |
| Open engine bugs | FINDING-020 (remove carry-list position), FINDING-022 (`look in` contents indent) — both in `tools/diff_harness/FINDINGS.md` |

## Next Intended Task

1. **Class-13 bypass-site sweep** via `/rom-divergence-sweep` (roster to-do #7):
   per-site ROM read of the ~25 remaining `append` placement sites — runtime
   placements should head-insert (route through the chokepoint), reconstruction
   paths (`from_orm`, `clone_object`, serializers) must stay `append`. Not a
   lexical guard.
2. **FINDING-022** — confirm the `look in` contents-line indent against the live C
   oracle, then port `show_list_to_char` PC semantics if divergent.
3. Continue Phase C deterministic command/watch-set widening (light hold,
   money/shop paths); add RNG-locked combat only after seed alignment is proven.

## Other open / deferred items

- **FINDING-020** — equipment-dict carry-list-position divergence; needs a scoped
  architectural decision (ROM keeps equipped objects in the carry list), not a
  quick fix.
- **test-fixtures-lint** — manual-staged style lint; re-enable once legacy tests migrate.
- **`test_all_commands.py` `exits` attribute error** — pre-existing harness artifact.
