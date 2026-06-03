# Session Status — 2026-06-03 — do_quit farewell messaging (GL-037 + QUIT-001) (2.12.97)

## Current State

This session closed the last open follow-up from the prior session and the new
gap it surfaced, both committed to `master` (2 commits, `de870f61..a6bed27c`,
not pushed):

1. **GL-037** (✅ FIXED, 2.12.97) — idle autoquit of a *connected* player now
   emits ROM `do_quit`'s "Alas, all good things must come to an end." (TO_CHAR)
   and broadcasts "$n has left the game." (TO_ROOM). `_auto_quit_character`
   emits both at the top of the function, before scheduling the transport close;
   verified no double-broadcast against the clean-disconnect `finally`.
2. **QUIT-001** (✅ FIXED, 2.12.97) — surfaced while closing GL-037: the
   *interactive* `do_quit` returned "May your travels be safe." instead of ROM's
   "Alas, all good things must come to an end." Fixed; corrected a false-✅ on
   the `ACT_COMM_C_AUDIT.md` do_quit row.

- **Pointer to this session's summary**:
  [SESSION_SUMMARY_2026-06-03_DO_QUIT_FAREWELL_MESSAGING.md](SESSION_SUMMARY_2026-06-03_DO_QUIT_FAREWELL_MESSAGING.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.12.97 |
| Tests | Full suite `pytest` → 5380 passed, 4 skipped |
| Lint | `ruff check .` + `ruff format --check .` clean repo-wide; 5 pre-commit hooks pass |
| ROM C files audited | 43 / 43 (per-file complete; cross-file invariants active) |
| Cross-file invariants | 31 active rows |
| Open engine bugs | **None** known. |

## Next Intended Task

No open engine bug remains. Per-file audit tracker has no ⚠️/❌ rows, so
cross-file invariants + the divergence-class roster (`/rom-divergence-sweep`)
are the active passes. Concrete candidates:

1. `diff_harness` Hypothesis widening — the only enumeration-independent path to
   *unknown* divergences.
2. New cross-INV probe (affect-tick / group-follower / position-transition edge).
3. Housekeeping: INV tracker consolidation (31 rows, past the ~20 soft cap).

## Other open / deferred items

- **test-fixtures-lint** — manual-staged style lint; re-enable once legacy tests migrate or it's reworked to changed-files-only.
- **`test_all_commands.py` `exits` attribute error** — pre-existing harness artifact (`SimpleNamespace` stub lacks `exit_info`); not an engine bug.
