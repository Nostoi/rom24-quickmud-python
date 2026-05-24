# Session Summary — 2026-05-24 — `dam_message` PERS parity (DAMMSG-001/002/003)

## Scope

Closed the highest-volume PERS leak remaining in `mud/combat/`:
`dam_message` now produces per-direction templates that
`_broadcast_damage_messages` PERS-renders per recipient, matching ROM
`src/fight.c:2218-2228`'s three `act()` calls
(`TO_NOTVICT` / `TO_CHAR` / `TO_VICT`).

This finishes the `fight.c` PERS sweep: position-change broadcasts
(FIGHT-004..008), weapon-proc broadcasts (FIGHT-009..013),
auto-sacrifice (FIGHT-014), and now the per-hit damage-tier broadcast
surface (DAMMSG-001/002/003) are all ROM-faithful.

## Gaps closed

| ID | ROM ref | Direction | Test |
|----|---------|-----------|------|
| DAMMSG-001 | `src/fight.c:2222` | TO_NOTVICT — iterate `room.people`, PERS-render attacker + victim per observer | `tests/integration/test_dam_message_pers.py::TestDamMessagePers::test_dammsg_001_to_notvict_renders_attacker_and_victim_per_observer` |
| DAMMSG-002 | `src/fight.c:2224` | TO_VICT — PERS-render attacker for victim's view | `tests/integration/test_dam_message_pers.py::TestDamMessagePers::test_dammsg_002_to_vict_renders_attacker_per_victim` |
| DAMMSG-003 | `src/fight.c:2223` | TO_CHAR — PERS-render victim for attacker's view | `tests/integration/test_dam_message_pers.py::TestDamMessagePers::test_dammsg_003_to_char_renders_victim_per_attacker` |

## Implementation

- `mud/combat/messages.py`
  - `dam_message` now emits `.format()`-ready templates with
    `{attacker}` / `{victim}` placeholders. ROM colour codes
    (`{3...{x`, `{2...{x`, `{4...{x`) are doubled so `str.format`
    leaves them intact for the ANSI translation layer.
  - New `render_for(template, attacker, victim, observer)` helper
    substitutes both names through `mud.world.vision.pers()`,
    mirroring ROM's `act()` evaluating `PERS(ch, looker)` and
    `PERS(victim, looker)` per recipient.
  - Removed `_safe_name` (no longer needed; PERS handles fallback
    inside `pers()`).
- `mud/combat/engine.py`
  - `_dispatch_damage_messages` renamed `_broadcast_damage_messages`
    (back-compat alias kept). New body iterates `room.people` for
    TO_NOTVICT and calls `render_for` per occupant; TO_CHAR /
    TO_VICT render with the appropriate observer.
  - `damage()`'s return value (consumed by `multi_hit`'s
    `attack_message` results and various scripted callers) is also
    PERS-rendered for the attacker's view so test surfaces see the
    correct ROM-substituted string.
- `tests/test_combat_messages.py` updated to call `render_for` on
  the returned templates (the previous `messages.attacker == "..."`
  assertions tested baked names).

## Tests

- 3 new integration tests in `tests/integration/test_dam_message_pers.py`.
- 2 existing unit tests in `tests/test_combat_messages.py` updated for
  the template surface.
- All 32 tests in `tests/test_combat.py` still pass (the `damage()`
  return-site render preserves the `multi_hit` attack-message
  contract that `assert_attack_message` depends on).

## Files touched

- `mud/combat/messages.py`
- `mud/combat/engine.py`
- `tests/test_combat_messages.py`
- `tests/integration/test_dam_message_pers.py` (new)
- `docs/parity/FIGHT_C_AUDIT.md`
- `CHANGELOG.md`
- `pyproject.toml` (2.8.66 → 2.8.67)

## Next intended task

`fight.c` PERS surfaces in `mud/combat/engine.py` are now fully
normalized. Reasonable continuations:

1. **PMOTE-001** — `do_pmote` greenfield port (~50 lines of C on
   the `act_comm.c` shelf, per-recipient second-person substitution
   with apostrophe/possessive handling).
2. **FIGHT-015** — refactor `_auto_sacrifice` to dispatch to
   `do_sacrifice` like ROM does at `src/fight.c:970` (structural
   parity, no behavior change).
3. Pick the next ⚠️ Partial row from
   `docs/parity/ROM_C_SUBSYSTEM_AUDIT_TRACKER.md`.

## Operational follow-ups

- `log/orphaned_helps.txt` still tracked and drifts on test runs.
  Consider `git rm --cached log/orphaned_helps.txt` + `.gitignore`
  entry in a small hygiene commit.
- GitNexus index last analyzed at `de1893f`; re-run
  `npx gitnexus analyze --skip-agents-md` before the next session
  that needs reliable impact analysis on `mud/combat/engine.py`
  (the file is on the 32 KB scope-extractor failure list).
