# Session Status — 2026-06-22 — Death autosac differential coverage

## Current State

- **Active focus**: Cross-file invariants / divergence-class roster.
- **Last completed**:
  - **INV-054** (DESCRIPTOR-WAIT-BUFFERS-INPUT) — live descriptor input typed
    while `ch.wait > 0` is now buffered at `_read_player_command` and replayed
    after recovery clears, mirroring ROM `src/comm.c:619-623`. This removes the
    Python-only visible `"You are still recovering."` line for live
    `cast magic`/combat-command input during kill/cast lag.
  - Regression: `tests/test_networking_telnet.py::test_wait_state_buffers_command_until_recovered_per_rom`.
  - **Death `PLR_AUTOSAC` differential coverage** — added `__plr_autosac=0|1`
    to the C/Python diff-harness drivers and committed the `death_auto_sac`
    scenario + C golden. The empty-NPC-corpse autosac path converges with ROM;
    no behavior fix was needed.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-22_DEATH_AUTOSAC_DIFF.md](SESSION_SUMMARY_2026-06-22_DEATH_AUTOSAC_DIFF.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.212 |
| Tests | Full suite: 6037 passed, 4 skipped; `ruff check .` clean |
| Cross-file invariants | INV-054 added (✅ ENFORCED) |
| Differential scenarios | 52 committed scenarios; `death_auto_sac` added |
| Active focus | Cross-file invariants / divergence-class roster |

## Next Intended Task

Continue the active cross-file invariant / differential-harness pass. The next
death-lifecycle probe is grouped reward `PLR_AUTOSPLIT`; add deterministic
grouped-PC setup to the diff harness first if the probe needs C-oracle coverage.
