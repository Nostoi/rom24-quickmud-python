# Session Status — 2026-06-03 — Room-contents show_list_to_char parity (2.13.5)

## Current State

- **Active mode**: cross-file invariants / divergence-class sweep (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **Room-contents `look()` parity** — `_look_room` now calls
    `show_list_to_char(room.contents, char, f_short=False, f_show_nothing=False)`,
    matching ROM `src/act_info.c:1106`. Previous code used a hand-rolled for-loop
    that omitted `can_see_object` visibility, aura prefixes, and COMBINE
    coalescence. 10 new integration tests.
  - **FINDING-022** — `look in <container>` contents indent (2.13.4, committed this session).
  - **Class-13 bypass sweep** — 15 runtime-placement sites fixed (2.13.3, committed this session).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-03_FINDING022_SHOW_LIST_PARITY.md](SESSION_SUMMARY_2026-06-03_FINDING022_SHOW_LIST_PARITY.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.5 |
| Tests | Full suite `pytest` → **5414 passed, 4 skipped**; `ruff check .` clean |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | INV-039 + INV-029 + room-contents parity resolved |
| Open engine bugs | FINDING-020 (remove carry-list position), FINDING-022 ✅ resolved |

## Next Intended Task

1. **FINDING-020** — equipment-dict carry-list position divergence; needs a scoped
   architectural decision (ROM keeps equipped objects in the carry list).
2. Continue Phase C deterministic command/watch-set widening (light hold,
   money/shop paths); add RNG-locked combat only after seed alignment is proven.
3. `show_list_to_char` coverage: inventory-list path (`do_inventory` already has
   its own COMBINE logic — could unify with `show_list_to_char` but not required
   for parity).

## Other open / deferred items

- **test-fixtures-lint** — manual-staged style lint; re-enable once legacy tests migrate.
- **`test_all_commands.py` `exits` attribute error** — pre-existing harness artifact.