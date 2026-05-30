# Session Summary — 2026-05-30 — CAST-007 do_cast PK Gates

## Scope

Continued from `SESSION_SUMMARY_2026-05-30_DO_CAST_OBJECT_TARGETING.md`.

Picked up the carried-open `is_safe`/`check_killer` PK gates item from the
MAGIC_C_AUDIT.md scope notes.

## Outcome

### CAST-007 — do_cast PK safety gates ✅ FIXED (2.11.53)

Three ROM `TAR_CHAR_OFFENSIVE` / `TAR_OBJ_CHAR_OFF` safety gates that were
missing from the Python `do_cast` path:

- **is_safe / is_safe_spell gate** (`src/magic.c:400-404` / `:484-488`):
  Non-NPC casters targeting a character in a safe room, shopkeeper, healer,
  etc., are now blocked with "Not on that target." Self-targeting is exempt
  per ROM (`victim != ch`). `TAR_CHAR_OFFENSIVE` uses `is_safe`;
  `TAR_OBJ_CHAR_OFF` uses `is_safe_spell` (same logic with a self-cast check).
  Object targets bypass this gate entirely per ROM.

- **check_killer gate** (`src/magic.c:406` / `:490`): After the safety check
  passes, `check_killer` is called for non-NPC casters. This flags the
  attacker as `PLR_KILLER` when attacking an innocent PC clan member, and has
  the side effect of stripping charm via `stop_follower` when the attacker is
  charmed and the resolved victim is a PC (ROM `src/fight.c:1248-1257`).

- **AFF_CHARM master gate** (`src/magic.c:408-412` / `:490-495`): After
  `check_killer`, if the caster still has `AFF_CHARM` and their master is the
  target, the cast is blocked with "You can't do that on your own follower."
  This gate is unconditional (outside the `!IS_NPC(ch)` block) and is
  reachable for NPC casters and for PC casters whose `check_killer` returned
  early (e.g., when the resolved victim is an NPC, `check_killer` skips the
  charm-stripping branch at `src/fight.c:1241`).

Key ROM ordering subtlety: `check_killer` (stripping charm for PC-on-PC
cases) runs *before* the AFF_CHARM gate, so a charmed PC attacking a non-master
PC has their charm stripped and the cast proceeds. A charmed PC attacking
their NPC master has `check_killer` return early (resolved_victim is NPC), so
charm is NOT stripped and the gate blocks the cast.

Defensive spells (`TAR_CHAR_DEFENSIVE` / `TAR_OBJ_CHAR_DEF`) have no PK gates
per ROM.

## Files Modified

- `mud/commands/combat.py` — `do_cast` PK gates (is_safe, is_safe_spell,
  check_killer, AFF_CHARM master gate); imports
- `tests/integration/test_do_cast_pk_gates.py` — 17 new integration tests
  (TestCastOffensiveSafeRoomBlock 3, TestCastOffensiveCheckKiller 4,
  TestCastOffensiveCharmGate 4, TestCastOffensiveObjCharSafeRoomBlock 2,
  TestCastOffensiveObjCharCheckKiller 1,
  TestCastOffensiveObjCharCharmGate 1,
  TestCastDefensiveNoSafeRoomBlock 2)
- `docs/parity/MAGIC_C_AUDIT.md` — CAST-007 row + scope notes update
- `CHANGELOG.md` — 2.11.53 entry
- `pyproject.toml` — bump 2.11.52 → 2.11.53
- `docs/sessions/SESSION_STATUS.md` — advance the session pointer

## Verification

- `pytest tests/integration/test_do_cast_pk_gates.py -v` — 17 passed
- `pytest tests/test_skills_spells_cast_listing.py
  tests/integration/test_do_cast_object_target.py
  tests/integration/test_do_cast_pk_gates.py -v` — 42 passed
- `pytest` (full suite) — 5076 passed, 4 skipped
- GitNexus detect_changes: low risk, 5 files changed, 0 affected processes

## Outstanding

- Per-spell handler Object branches (bless, curse, poison, remove_curse,
  invisibility) still only accept `Character` targets — `do_cast` now routes
  Objects to them, but the handlers will need Object-accepting branches for
  full parity. This is future per-spell audit work.
- Continue cross-file invariant probe/close cycle.
- Known xdist flakes remain carried-open.
- `Character.pet` stale type annotation remains open.