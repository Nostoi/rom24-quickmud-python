# Session Status — 2026-06-23 — Death autogold autosplit differential coverage

## Current State

- **Active focus**: Cross-file invariants / divergence-class roster.
- **Last completed**:
  - **INV-054** (DESCRIPTOR-WAIT-BUFFERS-INPUT) — live descriptor input typed
    while `ch.wait > 0` is now buffered at `_read_player_command` and replayed
    after recovery clears, mirroring ROM `src/comm.c:619-623`.
  - **Death `PLR_AUTOSAC` differential coverage** — added `__plr_autosac=0|1`
    to the C/Python diff-harness drivers and committed the `death_auto_sac`
    scenario + C golden. The empty-NPC-corpse autosac path converges with ROM.
  - **Death grouped `PLR_AUTOSAC` + `PLR_AUTOSPLIT` differential coverage** —
    added `__plr_autosplit=0|1` and descriptorless `__group_pc=<name>` to the
    C/Python diff-harness drivers and committed the `death_autosac_autosplit`
    scenario + C golden. The grouped autosac/autosplit path converges with ROM:
    driver 2 silver, grouped peer 1 silver, sacrifice + split output on the
    driver.
  - **Death grouped `PLR_AUTOGOLD` + `PLR_AUTOSPLIT` differential coverage** —
    committed the `death_autogold_autosplit` scenario + C golden. The plain
    corpse-money path converges with ROM `src/act_obj.c:162-184`: autogold gets
    17 silver from the NPC corpse, autosplit leaves the driver with 9 silver,
    and the descriptorless grouped peer receives 8 silver.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-23_DEATH_AUTOGOLD_AUTOSPLIT_DIFF.md](SESSION_SUMMARY_2026-06-23_DEATH_AUTOGOLD_AUTOSPLIT_DIFF.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.214 |
| Tests | Last full suite baseline: 6037 passed, 4 skipped; latest session ran focused diff-harness tests |
| Cross-file invariants | INV-054 added (✅ ENFORCED) |
| Differential scenarios | 54 committed scenarios; `death_autogold_autosplit` added |
| Active focus | Cross-file invariants / divergence-class roster |

## Next Intended Task

Continue the active cross-file invariant / differential-harness pass. The next
natural death-lifecycle widening is grouped `PLR_AUTOLOOT` + `PLR_AUTOSPLIT`
with mixed corpse contents, now that grouped descriptorless PCs and split flags
are both available in the diff harness.
