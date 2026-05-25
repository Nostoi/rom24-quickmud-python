# Session Status — 2026-05-24 — INV-010 ROOM-PEOPLE-COHERENCE locked in

## Current State

- **Active pass**: cross-file invariants — backstop for per-file audits.
- **Last completed**: INV-010 ROOM-PEOPLE-COHERENCE added to
  `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` with a 6-test
  enforcement suite. A dual `room_registry` divergence was discovered
  and closed (`mud/models/room.py` now re-exports the canonical
  `mud.registry.room_registry`). Version bumped 2.8.77 → 2.8.78.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-05-24_INV010_ROOM_PEOPLE_COHERENCE.md](SESSION_SUMMARY_2026-05-24_INV010_ROOM_PEOPLE_COHERENCE.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.8.78 |
| Tests | 4673 passed, 1 pre-existing failure (`test_wait_and_daze_decrement_on_violence_pulse`, present on master) |
| Cross-file invariants | 10 of ~20 budget; INV-001 … INV-010 all ✅ ENFORCED |
| Active focus | Next cross-file invariant — either INV-011 (object_list / extract_obj cleanup) or INV-012 (`carry_weight` coherence), per tracker watch list |

## Next Intended Task

Pick the next watch-list candidate from
`docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` and lock it in with an
enforcement test. The object-list / `extract_obj` analogue of INV-003
is the higher-value one — large cross-module surface, no current
coverage. Alternatively, if a per-file audit surfaces a contract that
crosses modules, document and close it under the same flow.

Also worth triaging (separately, out of cross-file scope): the
pre-existing `test_wait_and_daze_decrement_on_violence_pulse` failure
in `tests/test_game_loop_wait_daze.py`.

## Push gate

No `origin/master` push without explicit user approval. Local commits
ready: one (`feat(parity)`) for INV-010 + dual-registry fix +
CHANGELOG + version bump. Session handoff (`docs(session)`) covers
this summary and the `SESSION_STATUS.md` refresh.
