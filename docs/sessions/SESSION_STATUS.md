# Session Status — 2026-05-03 — INV-005 / INV-006 / INV-007 / INV-008 closed (cross-file invariants 8/8)

## Current State

- **Cross-file invariant INV-008 — ENFORCED (this session, version
  2.7.6).** `mud/account/account_manager.py` is now a thin shim
  delegating `load_character` / `save_character` to `mud.persistence`.
  The JSON pfile owns all 51+ ROM-faithful gameplay fields; the DB
  row keeps `name` + `password_hash` for auth only. Vestigial DB
  gameplay columns left in place for now (drop in a later schema
  session). 30+ PC fields previously dropped on every WS logout
  (mana, move, gold, silver, exp, hitroll, damroll, AC, conditions,
  affects, skills, aliases, pets, item state, container contents…)
  now round-trip. Field-level audit at
  `docs/parity/INV008_DIVERGENCE_AUDIT.md`. Enforcement test:
  `tests/integration/test_inv008_persistence_coherence.py` (4 cases,
  all green). **All 8 cross-file invariants ✅ ENFORCED.**
- **Cross-file invariant INV-007 — ENFORCED (this session, version
  2.7.5).** `tests/test_rng_determinism.py` now scans `mud/combat/`,
  `mud/skills/`, and `mud/spells/` for any `import random` / `from
  random` / `random.` usage and fails with path:line detail. Prerequisite:
  vestigial `stdlib Random` removed from `SkillRegistry.__init__`
  (field was never read; all rolls already used `rng_mm`). 7/8
  cross-file invariants now ✅ ENFORCED; only INV-008
  (DUAL-LOAD-CHARACTER-COHERENCE) remains a known divergence.
- **Cross-file invariants INV-005 / INV-006 — ENFORCED (earlier
  today, version 2.7.4).** Both were ⚠️ VERIFIED MANUALLY in the
  cross-file invariants tracker; they now have failing-test-able
  enforcement at `tests/integration/test_inv005_same_room_combat.py`
  and `tests/integration/test_inv006_fighting_pointer_coherence.py`.
  Tracker rows flipped to ✅ ENFORCED.
- **Death-path parity sweep — SHIPPED (commits `f586d11`, `59bebf0`,
  + this session's release commit).** User reported "I die in combat
  and get disconnected." Live log proved two real bugs (not the
  reported one): combat messages were delivered TWICE to WS clients
  (causing the apparent "second death"), and `bust_a_prompt` showed
  raw negative `hit` between damage application and `raw_kill`'s
  clamp. Fixes: gate `_push_message` mailbox append on
  `connection is None`; clamp displayed `hit >= 0` at both prompt
  render sites; parity comment on `_handle_death`'s bidirectional
  `fighting` clear. 8 new tests; ROM refs `src/comm.c:write_to_buffer`,
  `src/comm.c:1420ff bust_a_prompt`, `src/fight.c:1718 raw_kill`.
- **Pointer to latest summary**:
  `docs/sessions/SESSION_SUMMARY_2026-05-02_DEATH_PATH_PARITY_SWEEP.md`.
- **Earlier this day (still in CHANGELOG)**: combat one-way bug
  (`d2fafcd` — `load_character` registry append) and empty-world fix
  (`3100b59` — JSON area resets); see
  `SESSION_SUMMARY_2026-05-02_COMBAT_BUG_TRIAGE.md` and
  `SESSION_SUMMARY_2026-05-02_EMPTY_WORLD_FIX.md`.

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.7.6 |
| Cross-file invariants enforced | **8/8 ✅ ENFORCED** |
| Audit-bound ROM C files | 40/40 audited (100%) |
| N/A ROM C files | 3/3 (`recycle.c`, `mem.c`, `imc.c`) |
| `comm.c` message delivery | ✅ single-delivery; mailbox is fallback only |
| `fight.c` death path | ✅ raw_kill keeps PC connected; prompt clamps hp; bidirectional fighting clear documented |
| Current sweep focus | live-game parity (death/combat); broad-sweep hedit rewrite remains the next planned item |

## Next Intended Task

1. **Live verification of the death-path fixes**: re-run the WS
   server (`MUD_DEBUG_VIOLENCE=1 python3 -m mud websocketserver
   2>&1 | tee ~/mud-death-after.log`), get killed, confirm exactly
   one "You have been KILLED!!" line and `<1hp ...>` (never `<0hp>`)
   prompt. If anything misbehaves, the new traceback in
   `mud/net/connection.py:1766` will name the exact line/exception.
2. **Resume broad-sweep**: rewrite `tests/test_builder_hedit.py`
   against the ROM-parity `cmd_hedit` (HEDIT-001..014, commit
   `cdcd0cc`). 19 stale tests; some recurse via the dispatcher and
   crash with `RecursionError`. Mirror the format from
   `tests/integration/test_olc_save_014_017_message_strings.py`.
3. After hedit, re-run `pytest -x -q --ignore=test_all_commands.py`
   and triage the next first failure.

## Open Follow-ups (not blocking the broad sweep)

- **DB schema cleanup (post INV-008):** vestigial gameplay columns
  on `mud/db/models.py:Character` (level, hp, race, ch_class, sex,
  alignment, act, hometown_vnum, perm_stats, size, form, parts,
  imm_flags, res_flags, vuln_flags, practice, train, perm_hit/mana/
  move, default_weapon_vnum, creation_points, creation_groups,
  creation_skills, newbie_help_seen, room_vnum, true_sex) are no
  longer read or written by production code under the hybrid scheme
  — only `name` and `password_hash` matter. Drop them in a future
  schema-migration session once the JSON-canonical path has soaked
  for a while.
- **Pre-existing persistence test failures (3):**
  `tests/test_persistence.py::test_character_json_persistence`,
  `tests/test_persistence.py::test_inventory_round_trip_preserves_object_state`,
  `tests/test_inventory_persistence.py::test_inventory_and_equipment_persistence`.
  Verified pre-existing at commit `3aef2b6` (before INV-008 work).
  All fail via `inventory_object_factory` returning None for vnum
  3022 — likely a world-init / fixture issue, not the persistence
  code. Triage separately.
- **Two ROM parity gaps surfaced during combat triage (separate
  FIGHT-XXX entries):**
  - `do_kill` calls `attack_round` (one swing); ROM `src/fight.c:2817`
    calls `multi_hit`. `mud/commands/combat.py:125`.
  - `is_safe()` is implemented (`mud/combat/safety.py`) but never
    gated inside the damage path. ROM calls `is_safe(ch, victim)`
    inside `damage()` and inside every special-attack handler.
    Combatants dragged into a safe room mid-fight keep swinging in
    Python; ROM stops them.
- **Pre-existing `tests/test_logging_admin.py` failures** (8 cases,
  "Huh?" dispatcher misses). Verified pre-existing during the
  death-path sweep via `git stash` baseline. Not blocking.
- **Scavenger RNG-order flake** at
  `tests/integration/test_mob_ai.py::TestScavengerBehavior::test_scavenger_prefers_valuable_items`
  — passes in isolation, fails under full-suite ordering despite the
  autouse `rng_mm.seed_mm(12345)` fixture. State is leaking from
  somewhere upstream.
- **Stale eddol.json save** (1 HP at login) — separate symptom: a
  previous combat death persisted at 1 HP. Worth checking whether
  `save_character` is being called on death; low priority.
