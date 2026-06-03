# Session Status — 2026-06-03 — FINDING-022 show_list_to_char parity (2.13.4)

## Current State

- **Active mode**: cross-file invariants / divergence-class sweep (per-file audit
  tracker has no ⚠️ Partial / ❌ Not Audited rows).
- **Last completed**:
  - **FINDING-022** — ✅ FIXED: `look in <container>` contents lines carried a
    2-space indent matching neither ROM's no-indent PC path nor the 5-space
    COMBINE path. Ported `show_list_to_char` and `format_obj_to_char` from ROM
    `src/act_info.c:87-243` to `mud/utils/act.py`; `_look_in` now calls
    `show_list_to_char(contents, char, f_short=True, f_show_nothing=True)` for
    correct formatting: no indent for non-COMBINE PCs, 5-space/(N) for
    COMBINE/NPC viewers. 11 new tests (7 unit + 4 end-to-end).
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-03_FINDING022_SHOW_LIST_PARITY.md](SESSION_SUMMARY_2026-06-03_FINDING022_SHOW_LIST_PARITY.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.13.4 |
| Tests | Full suite `pytest` → **5400+ passed, 4 skipped**; `ruff check .` clean |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | INV-039 (object-list head-insert) + INV-029 (act-cap) + FINDING-022 resolved |
| Open engine bugs | FINDING-020 (remove carry-list position), FINDING-022 ✅ resolved |

## Next Intended Task

1. **FINDING-020** — equipment-dict carry-list position divergence; needs a scoped
   architectural decision (ROM keeps equipped objects in the carry list).
2. Continue Phase C deterministic command/watch-set widening (light hold,
   money/shop paths); add RNG-locked combat only after seed alignment is proven.
3. Port room-contents `look()` path through `show_list_to_char` (currently
   `for obj in room.contents` without COMBINE/aura logic — separate gap from
   FINDING-022 but same `show_list_to_char` function).

## Other open / deferred items

- **test-fixtures-lint** — manual-staged style lint; re-enable once legacy tests migrate.
- **`test_all_commands.py` `exits` attribute error** — pre-existing harness artifact.