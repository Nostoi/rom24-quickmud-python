# Session Status — 2026-05-03 — INV-008 reversed to DB-canonical (cross-file invariants 8/8)

## Current State

- **INV-008 reversed — DB row is canonical (this session, version
  2.8.1).** The 2.7.6 hybrid (JSON pfile canonical, DB auth-only) had
  a hidden seam at `create_character` / `Character.from_orm`, which
  still wrote/read DB columns at first-login. Reversed in two phases:
  - **2.8.0 (Phase 1)** — extended `mud/db/models.py:Character` with
    39 new columns (21 scalars + 11 JSON collections + inventory_state
    / equipment_state JSON blobs); extended `Character.from_orm` to
    hydrate them; added `save_character_to_db(session, char)` to
    `mud/account/account_manager.py`. Round-trip proven by 7 new
    tests in `tests/integration/test_db_canonical_round_trip.py`.
    Driven by `docs/parity/INV008_REVERSAL_AUDIT.md` (71-field map).
  - **2.8.1 (Phase 2)** — `account_manager.save_character` /
    `load_character` swapped to the DB path; JSON-pfile delegation
    removed. `mud/persistence.py` reduced to a deprecation stub
    (still keeps `time_info` save/load). 7 pfile-only test files
    deleted (their surface no longer exists); coverage replaced by
    the DB-path suites. The 3 pre-existing vnum-3022 persistence
    failures retired with the deleted tests. INV-008 enforcement
    test rewritten (`tests/integration/test_inv008_persistence_coherence.py`,
    5 cases, all green). **All 8 cross-file invariants ✅ ENFORCED
    again under the new architecture.**
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
| Version | 2.8.1 |
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

- ~~**DB schema cleanup (post INV-008):**~~ Obsolete after INV-008
  reversal — those columns are now load-bearing under the
  DB-canonical scheme. New follow-up: `mud/persistence.py` is a
  deprecation stub holding only `time_info` save/load; consider
  moving those helpers to a `mud/world/time_persistence.py` and
  deleting `mud/persistence.py` outright once nothing imports the
  module's deprecated symbols.
- ~~**Pre-existing persistence test failures (3):**~~ Retired with
  the JSON-pfile path in 2.8.1 (the test files were deleted; the
  failing surface no longer exists).
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
