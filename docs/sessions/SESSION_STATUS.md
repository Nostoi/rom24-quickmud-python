# Session Status — 2026-07-18 — Autonomous 15-iteration loop COMPLETE

## Current State

- **15/15 iterations complete** (user asked for a 15-session loop; paced for
  quality over count per the advisor — "iterations, not padded commits").
  **7 parity closures + 1 test fixup + 7 recall-oracle probes** (6 verified
  faithful/clean + 1 deep-probe filing). Full retrospective:
  [SESSION_SUMMARY_2026-07-18_AUTONOMOUS_LOOP_OLC_FIGHT.md](SESSION_SUMMARY_2026-07-18_AUTONOMOUS_LOOP_OLC_FIGHT.md)
- **Closures:** OLC_ACT-015/016/017/018/019 (redit/oedit/medit/aedit setters —
  incl. OLC_ACT-019's real *permission* fix), FIGHT-104 (inviso-strip order),
  ENV-005 (envenom head-insert).
- **Two subsystems swept clean:** the combat `damage()` pipeline (iters 4/6/8/9)
  and the affect-tick + condition machinery (iters 11/13/14) are now
  verified ROM-faithful by recall-oracle probes.
- **Active focus** (unchanged): cross-file invariants / divergence-class probe
  mode; the OLC per-field setter vein is largely swept (aedit_builder/vnum remain).

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.14.338 |
| Tests | **6265 passed, 4 skipped, 0 failed** (~148s parallel; the one OLC_ACT-014 assert that lagged OLC_ACT-019's message change was fixed) |
| ROM C files audited | 43 / 43 |
| Differential harness | 102/102 across 69 scenarios; diffshim C binary builds clean (2026-07-18) |
| Push status | On master since 2026-10-22 (PR #129, merge `c19888df`). Local commit `101d1e27` (Claude config isolation) was left out by the owner and is kept on branch `backup/local-master-2026-10-22`. |
| Active focus | Cross-file invariants / divergence-class + OLC setter sweep |

## Next Intended Task — durably-filed OPEN gaps (for the next session)

1. **OLC_ACT-020 — `aedit_builder`**: port ROM's single-arg TOGGLE grammar +
   proper-case name storage + two-line syntax/`"Builder added/removed."`
   messages. Full spec + blast radius (5 `test_olc_aedit.py` cases, no frontend)
   in OLC_ACT_C_AUDIT.md. **Verify `is_builder` is case-insensitive first.**
2. **OLC_ACT-021 — `aedit_vnum`**: ROM takes two args and sets `min_vnum`/
   `max_vnum` with `check_range`/`get_vnum_area` overlap validation; Python's
   `vnum <n>` sets the area-identity `area.vnum` instead. Needs care re: the
   Python area-registry keying model.
3. **ENV-006 — envenom `value[4]` bit**: envenom skips `affect_to_obj`'s
   `value[4] |= WEAPON_POISON`; verify poison-on-hit fires end-to-end and whether
   routing the whole path through `affect_to_obj` is the fix (subsumes ENV-005).
4. **ENV-003 (re-opened)** — envenom affect `type=-1` vs combat's `"poison"`
   level-lookup (`engine.py:1959`); the "never-walked" premise was stale.
5. **HANDLER-009 follow-up — tail inserts into `room.people`**:
   `char_list_walk_from_room_head` treats `room.people[0]` as the newest
   arrival (ROM `char_to_room` head-inserts), but `mload`
   (`mud/commands/imm_load.py`), `clone` (`mud/commands/imm_search.py`) and
   spec_mayor (`mud/spec_funs.py`) still `people.append`, so a mob added that
   way is skipped by check_assist and area-attack sweeps. Route them through
   `Room.add_mob`; check the other `people.append` sites too.
6. Continue recall-oracle probes on un-swept high-traffic surfaces (regen
   `hit_gain`/`mana_gain`/`move_gain`, `check_improve`, mob `mobile_update`).

## Outstanding — deferred by design (unchanged)

- **DESC-001** — OPEN by design (latent, unreachable in ROM's input range).
- **OLC spell-name lookup** — gated on a skill-by-index registry.
- **OLC_ACT-010b** — medit dice/AC stored as strings pending model split.
- **DB2-004/005** — theoretical multi-line `fread` (canonical areas never hit).
