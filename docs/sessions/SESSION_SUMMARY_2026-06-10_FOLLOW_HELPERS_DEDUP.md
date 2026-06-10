# Session Summary — 2026-06-10 — Follow Helpers Dedup (add_follower/stop_follower)

## Scope

Continuation from v2.13.81 (regen scenario suite complete). The active pass is
cross-file invariants. Session picked up by probing the group/follower chain for
divergences not yet covered by an INV row. Discovered that `mud/commands/group_commands.py`
contained stale local redefinitions of `add_follower` and `stop_follower` — duplicating
the canonical implementations in `mud/characters/follow.py`. The advisor confirmed the
charm-strip divergence was unreachable on any live path (charmed chars are blocked by a
guard before `stop_follower` is called), so this was filed as a code-duplication dedup
rather than a new INV. Correct approach per AGENTS.md: Layer-A grep-guard + clean import.
Session ends at v2.13.82.

## Outcomes

### `group_commands.py` local `add_follower`/`stop_follower` — ✅ DEDUPED

- **Python canonical**: `mud/characters/follow.py` — `add_follower`, `stop_follower`
- **ROM C**: `src/act_comm.c:1591-1607` (add_follower), `:1612-1636` (stop_follower)
- **Divergences in the stale local copy**:
  - `stop_follower`: only bit-cleared `affected_by & ~AFF_CHARM` — never called
    `remove_spell_effect("charm person")` as ROM's `affect_strip(ch, gsn_charm_person)`
    requires (canonical `follow.py` does this correctly).
  - `add_follower`: returned early if `char.master is not None` (any master) instead
    of calling `stop_follower` first and then re-following — diverging from ROM
    `src/act_comm.c:1591-1592`.
  - Both stale variants referenced `master.followers` list — absent from the data model.
- **Reachability**: `do_follow` guards charmed chars (`if affected_by & CHARM and
  char.master is not None: return ...`) before any `stop_follower` call, so the
  charm-strip divergence was unreachable on the live path. Not filed as INV.
- **Fix**: deleted both local function defs from `group_commands.py`; added top-level
  import `from mud.characters.follow import add_follower, stop_follower`.

### `tests/test_follow_canonical.py` — ✅ ADDED (Layer-A guard)

- **File**: `tests/test_follow_canonical.py`
- Two tests:
  - `test_no_local_follow_helpers_in_group_commands` — AST-scans `group_commands.py`,
    fails if `add_follower` or `stop_follower` are defined locally.
  - `test_group_commands_imports_canonical_follow_helpers` — asserts both names are
    imported from `mud.characters.follow`.
- Matches the Layer-A grep-guard pattern established by `test_rng_determinism.py`,
  `test_equipment_key_convention.py`, and `test_flag_hex_convention.py`.

## Files Modified

- `mud/commands/group_commands.py` — removed local `add_follower`/`stop_follower` defs;
  added `from mud.characters.follow import add_follower, stop_follower` at top
- `tests/test_follow_canonical.py` — new guard test (2 tests)
- `CHANGELOG.md` — `[2.13.82]` Fixed entries
- `pyproject.toml` — 2.13.81 → 2.13.82

## Test Status

- `pytest tests/test_follow_canonical.py` — **2/2 passing** (new)
- `pytest tests/integration/test_group_combat.py tests/test_act_enter_rom_parity.py` —
  **39/39 passing, 1 skipped** (no regressions in follow/group area)
- Full suite: **5548 passed, 4 skipped** (was 5546; +2 new guard tests)

## Next Steps

Cross-file invariants remains the active pass. The group/follower area was probed and
the only finding was the stale-duplicate code smell (now fixed).

Next probe candidates (none yet covered by an INV row, next free ID: INV-042):

1. **Affect-tick contracts** — ROM `src/update.c:762-786` duration-decay loop. Already
   implemented correctly in `mud/affects/engine.py:tick_spell_effects`, but the
   RNG short-circuit evaluation order (GL-026) and the LIFO expiry-message rule
   (only last-of-type emits `msg_off`) deserve cross-INV enforcement tests.
2. **Position-transition edges** — `update_pos` after `stop_fighting` clears
   `ch->position` to `default_pos` (NPC) or `STANDING` (PC) then re-evaluates HP;
   Python already correct, but no cross-INV enforcement test.
3. **MATH-002/003/004** — ⚠️ OPEN hygiene items in `docs/parity/audits/MATH_AND_RNG.md`
   (LOW severity, no observable gap). Held for a future PARITY008 lint rule.
