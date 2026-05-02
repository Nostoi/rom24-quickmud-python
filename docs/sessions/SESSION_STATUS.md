# Session Status — 2026-05-02 — combat fix shipped; empty-world fix shipped

## Current State

- **Combat one-way bug — FIXED (committed `d2fafcd`).** Player kept getting
  hit by mobs but never swung back. Root cause: two parallel
  `load_character` implementations. The DB-backed one in
  `mud/account/account_manager.py` (the one production WebSocket logins go
  through) didn't append the loaded PC to `character_registry`, so the
  game-loop ticks (`violence_tick`, `char_update`, idle pump) never iterated
  the player. Combat was one-way (mobs reach PC via `pc.connection`
  directly), HP regen never fired, idle never tripped, save_world never
  saved. Diagnosed by env-gated `[VIOL]` instrumentation in `violence_tick`
  + live-server stdout capture (`registry=2169 pcs=[]` while user was
  fighting). Fix: idempotent append in `account_manager.load_character`.
  TDD test added.
- **Pointer to latest summary**:
  `docs/sessions/SESSION_SUMMARY_2026-05-02_COMBAT_BUG_TRIAGE.md`
  (debug-mode walkthrough; needs a follow-up summary noting the fix
  landed).
- **Shipped this session (committed `3100b59`)**: restored mob spawning
  across the entire world. 46 of 54 JSON area files were missing their
  `resets` array; wrote `scripts/patch_json_resets.py` to inject resets
  from `.are` without touching hand-edited fields. School arena and every
  other populated area now spawn their ROM mobs on boot. Folded in three
  stale-test fixes from earlier today and the autouse OLC-write redirect.
  See `SESSION_SUMMARY_2026-05-02_EMPTY_WORLD_FIX.md` and
  `SESSION_SUMMARY_2026-05-02_BROAD_SUITE_TRIAGE_HEDIT_BLOCKER.md`.

## Project Status (snapshot)

| Metric | Value |
|--------|-------|
| Version | 2.6.108 |
| Audit-bound ROM C files | 40/40 audited (100%) |
| N/A ROM C files | 3/3 (`recycle.c`, `mem.c`, `imc.c`) |
| `olc.c` audit | ✅ complete |
| Current sweep focus | stale/full-suite regressions outside the per-file audit tracker |
| Latest broad-sweep checkpoint | `pytest -x -q --ignore=test_all_commands.py` reaches **1107 passed** before tripping a pre-existing scavenger RNG-order flake; the test passes in isolation and is unrelated to today's fixes. The hedit rewrite still gates further sweep progress. |

## Next Intended Task

1. **Resume broad-sweep**: rewrite `tests/test_builder_hedit.py` against
   the new ROM-parity `cmd_hedit` (HEDIT-001..014, commit `cdcd0cc`).
   19 stale tests; some recurse via the dispatcher and crash with
   `RecursionError`. Mirror the format from
   `tests/integration/test_olc_save_014_017_message_strings.py`.
2. After hedit, re-run `pytest -x -q --ignore=test_all_commands.py` and
   triage the next first failure. Full-suite (no `-x`) currently reports
   **67 failed, 14 errors**; ~48 are downstream of hedit's `RecursionError`.

## Open Follow-ups (not blocking the broad sweep)

- **Tech-debt: two parallel `load_character`/`save_character`
  implementations.** The codebase has both a JSON-pfile path
  (`mud/persistence.py`) and a SQLAlchemy/SQLite path
  (`mud/account/account_manager.py`). The DB path is the only one
  production WebSocket logins go through; the JSON path is what
  `tests/test_player_save_format.py`,
  `tests/integration/test_save_load_parity.py`, and a couple of
  persistence integration tests exercise. They diverged on at least the
  `character_registry` membership invariant — fixed for the DB path in
  `d2fafcd`, but probably not the only divergence (compare
  `account_manager.save_character`'s field set vs.
  `persistence.save_character`'s). Right end-state: pick one canonical
  implementation (the DB-backed one, since auth depends on it) and either
  remove the JSON path or downgrade it to an export/import tool. Out of
  scope for the broad sweep but worth tracking — bugs hide in the gaps
  between them.
- **Two ROM parity gaps surfaced during combat triage (separate
  FIGHT-XXX entries):**
  - `do_kill` calls `attack_round` (one swing); ROM `src/fight.c:2817`
    calls `multi_hit`. `mud/commands/combat.py:125`.
  - `is_safe()` is implemented (`mud/combat/safety.py`) but never gated
    inside the damage path. ROM calls `is_safe(ch, victim)` inside
    `damage()` and inside every special-attack handler. Combatants
    dragged into a safe room mid-fight keep swinging in Python; ROM
    stops them.
- **Scavenger RNG-order flake** at
  `tests/integration/test_mob_ai.py::TestScavengerBehavior::test_scavenger_prefers_valuable_items`
  — passes in isolation, fails under full-suite ordering despite the
  autouse `rng_mm.seed_mm(12345)` fixture. State is leaking from
  somewhere upstream.
- **Stale eddol.json save** (1 HP at login) — separate symptom user
  noticed: a previous combat death persisted at 1 HP. Worth checking
  whether `save_character` is being called on death (or whether the
  persisted hit value is correct), but low priority — the combat fix
  alone should mean future deaths don't re-occur unless mob actually
  outdamages the player.
