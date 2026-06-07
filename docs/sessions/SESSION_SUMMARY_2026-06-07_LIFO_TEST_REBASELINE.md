# Session Summary — 2026-06-07 — INV-039 LIFO Test Rebaseline (2.13.18)

## Scope

Picked up from SESSION_STATUS "Next Intended Task — continue cross-INV probe-then-scope."
The full test suite had 10 pre-existing test failures, all caused by the INV-039 head-insert
fix (v2.13.1) changing `Room.add_character` and `Character.add_object` from append (FIFO)
to `insert(0, ...)` (LIFO, matching ROM `char_to_room`/`obj_to_char`). The tests were
written assuming FIFO iteration order for `room.people` and needed re-baselining to match
ROM-correct LIFO behavior.

All 10 tests were fixed; no production code changes were needed. The suite now passes
cleanly: **5434 passed, 4 skipped, 0 failures**.

## Outcomes

### INV-039 LIFO test re-baseline — 10 tests fixed

| Test | Issue | Fix |
|------|-------|-----|
| `test_chain_lightning_bounces_with_level_decay` | Bounce target order reversed: LIFO scans v3, v2, v1. v3 gets 6d6, v2 gets 2d6. | Swap v2/v3 expected damage values |
| `test_chain_lightning_arcs_room_targets` | Second/third bounce targets swapped | Update expected HP values (second=158, third=142) |
| `test_mass_invis_fades_group` | Caster processed last in LIFO; act_to_room lands after ally's TO_CHAR | `ally.messages[-1]` → `in ally.messages` |
| `test_mass_invis_applies_to_group_members_in_room` | Same as above, without already_invis member | Same fix: `in ally.messages` |
| `test_holy_word_good_buffs_good_harms_evil_not_neutral` | LIFO processes evil victim before caster; `apply_damage` → `set_fighting` → caster.POS_FIGHTING blocks self-bless (ROM `spell_bless` src/magic.c:840) | Assert `not caster.has_spell_effect("bless")` |
| `test_spec_thief_fails_against_awake_player` | Observer (Bystander) is first non-NPC in LIFO, receives victim message; victim gets observer alert | Swap observer/victim message expectations |
| `test_mpforce_numbered_target_selects_second_match` | `2.guard` counts in LIFO order; 1.guard = most-recently-added | Expect `Guard One` for `2.guard` |
| `test_steal_other_not_blocked_by_own_name_substring` | Victim must be added AFTER thief so `get_char_room("bob")` resolves to Bob, not Bobby | Add thief first, then victim |
| `test_random_trigger_picks_visible_pc` | `_get_random_char` iterates LIFO; bravo gets first roll, alpha gets second | bravo gets 30, alpha gets 80 → alpha wins |
| `test_2name_selects_second_occupant_not_first` | Numbered selectors count LIFO; 1.guard=most-recent, 2.guard=first-added | 1.guard=g2, 2.guard=g1 |

### Root cause analysis

All 10 failures share one root cause: tests were written assuming `Room.add_character`/`Character.add_object`
append-order (FIFO) iteration. The INV-039 fix (v2.13.1) changed these to head-insert (LIFO),
matching ROM's `char_to_room`/`obj_to_char`. The production code is **ROM-correct**; the tests
were asserting non-ROM FIFO behavior.

The fix pattern falls into three categories:
1. **Order-dependent assertions** (chain_lightning, arc_room_targets, holy_word, spec_thief,
   numbered selector, random trigger): swap or update expected values to match LIFO iteration.
2. **Message-order assertions** (mass_invis): use `in` instead of `[-1]` since act_to_room
   broadcasts from later-processed characters overwrite earlier TO_CHAR messages.
3. **Setup-order dependencies** (steal name-substring): add the victim AFTER the thief so
   `get_char_room` resolves the victim's name first in the LIFO list.

## Files Modified

- `tests/test_spell_damage_additional_rom_parity.py` — chain_lightning bounce order
- `tests/test_skills_damage.py` — chain_lightning arc targets
- `tests/test_skills_buffs.py` — mass_invis message order
- `tests/test_spec_funs.py` — spec_thief victim/observer message swap
- `tests/test_spell_area_effects_rom_parity.py` — mass_invis message order + holy_word self-bless
- `tests/test_mobprog.py` — random trigger roll order
- `tests/test_mobprog_commands.py` — numbered target selector
- `tests/integration/test_handler001_get_char_room_self.py` — steal name-substring setup order
- `tests/integration/test_handler002_get_char_room_count_once.py` — numbered selector LIFO
- `CHANGELOG.md` — 2.13.18 section
- `pyproject.toml` — 2.13.17 → 2.13.18

## Test Status

- **Full suite: 5434 passed, 0 failed, 4 skipped** (up from 5424 passed, 10 failed)
- Diff harness: 34/34 passing
- `ruff check .` clean

## Next Steps

1. Continue cross-INV probe-then-scope as the active pass mode. The liquid/drink surface
   for the deterministic harness is now conformed. Remaining surface areas for diff-harness
   widening: mob scripts, spell casting (requires seed alignment), shop interactions,
   affect expiration.
2. The INV-039 test re-baseline is now complete — all room.people iteration-order tests
   match ROM LIFO semantics. Any new tests should use LIFO assumptions.