# Session Status — 2026-06-23 — Death autoloot autosplit differential coverage

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
  - **Death grouped `PLR_AUTOLOOT` + `PLR_AUTOSPLIT` differential coverage** —
    committed the `death_autoloot_autosplit` scenario + C golden. The mixed
    corpse path converges with ROM `src/fight.c:945-957` and
    `src/act_obj.c:162-184`: autoloot gets the carried lantern plus 17 silver
    and 2 gold from the NPC corpse, autosplit leaves the driver with 9 silver
    and 1 gold, and the descriptorless grouped peer receives 8 silver and
    1 gold. This closed the FIGHT-080 follow-up where Python updated balances
    but dropped the actor's split output lines from `do_get`.
- **Pointer to latest summary**:
  [SESSION_SUMMARY_2026-06-23_DEATH_AUTOLOOT_AUTOSPLIT_DIFF.md](SESSION_SUMMARY_2026-06-23_DEATH_AUTOLOOT_AUTOSPLIT_DIFF.md)

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.215 |
| Tests | 6042 passed, 4 skipped |
| Cross-file invariants | INV-054 added (✅ ENFORCED) |
| Differential scenarios | 55 committed scenarios; `death_autoloot_autosplit` added |
| Active focus | Cross-file invariants / divergence-class roster |

## Next Intended Task

Continue the active cross-file invariant / differential-harness pass. The next
natural probe is outside the death auto-action path: exercise direct `do_get`
money autosplit output through a non-death `get all corpse` or get-from-container
scenario, since the fixed `do_get` extra-output path is shared.
