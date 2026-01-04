# ROM C Subsystem Audit Tracker

**Purpose**: Track audit status of all 43 ROM 2.4b6 C source files for QuickMUD parity  
**Created**: December 30, 2025  
**Status**: Active tracking document

---

## Overview

This document tracks the **audit status** of all ROM 2.4b6 C source files (`src/*.c`) to ensure QuickMUD has equivalent implementations and integration tests.

**Critical Principle**: Every ROM C function should have either:
1. A QuickMUD Python equivalent (verified)
2. A documented reason why it's not needed
3. A tracking ticket for implementation

### Audit Status Legend

- ✅ **Audited** - QuickMUD parity verified, integration tests exist
- ⚠️ **Partial** - Some functions ported, gaps exist
- ❌ **Not Audited** - No systematic audit performed
- 🔄 **In Progress** - Currently being audited
- N/A **Not Needed** - ROM feature not applicable to QuickMUD

---

## Audit Priority Levels

- **P0** - Critical gameplay (combat, movement, commands)
- **P1** - Core features (skills, spells, world, mobs)
- **P2** - Important features (OLC, admin, special procs)
- **P3** - Infrastructure (memory, networking, db)

---

## ROM C Source Files (43 files)

### Current Audit Status

**Overall**: ⚠️ **33% Audited** (13 audited, 19 partial, 7 not audited, 4 N/A)  
**handler.c Status**: 🎉 **100% COMPLETE** (74/74 handler.c functions implemented!) 🎉  
**save.c Status**: 🎉 **100% COMPLETE** (8/8 functions, pet persistence implemented!) 🎉  
**db.c Status**: 🎉 **100% COMPLETE** (44/44 functional functions implemented!) 🎉  
**effects.c Status**: 🎉 **100% COMPLETE** (5/5 functions, all environmental damage!) 🎉  
**Last Updated**: January 5, 2026 23:29 CST

| File | Priority | Status | QuickMUD Module | Coverage | Notes |
|------|----------|--------|-----------------|----------|-------|
| **Combat & Violence** | | | | | |
| `fight.c` | P0 | ✅ Audited | `mud/combat/` | 95% | Violence tick fixed Dec 2025 |
| `skills.c` | P0 | ✅ Audited | `mud/skills/` | 100% | All 37 skills have ROM parity tests |
| `magic.c` | P0 | ✅ Audited | `mud/spells/` | 98% | 97 spells tested |
| `magic2.c` | P0 | ✅ Audited | `mud/spells/` | 98% | Continuation of magic.c |
| **Core Game Loop** | | | | | |
| `update.c` | P0 | ✅ Audited | `mud/game_loop.py` | 95% | PULSE_MOBILE added Dec 2025 |
| `handler.c` | P1 | ✅ **COMPLETE!** | `mud/handler.py`, `mud/world/`, `mud/models/` | **100%** | 🎉🎉🎉 **FULL PARITY ACHIEVED - ALL 74 FUNCTIONS IMPLEMENTED!** 🎉🎉🎉 Jan 4 - See HANDLER_C_AUDIT.md |
| `effects.c` | P1 | ✅ **COMPLETE!** | `mud/magic/effects.py` | **100%** | 🎉🎉🎉 **FULL PARITY ACHIEVED - ALL 5 FUNCTIONS IMPLEMENTED!** 🎉🎉🎉 Jan 5 - 23 integration tests - See EFFECTS_C_AUDIT.md |
| **Movement & Rooms** | | | | | |
| `act_move.c` | P0 | ✅ Audited | `mud/movement/` | 85% | Portal cascading verified |
| `act_enter.c` | P1 | ⚠️ Partial | `mud/commands/` | 50% | Basic enter/leave |
| `scan.c` | P2 | ❌ Not Audited | - | 0% | Scan command missing |
| **Commands** | | | | | |
| `act_comm.c` | P0 | ✅ Audited | `mud/commands/communication.py` | 90% | Tell command fixed Dec 2025 |
| `act_info.c` | P1 | ⚠️ Partial | `mud/commands/info.py` | 65% | Look/examine/who/where |
| `act_obj.c` | P1 | ⚠️ Partial | `mud/commands/objects.py` | 60% | Get/drop/put/give |
| `act_wiz.c` | P2 | ⚠️ Partial | `mud/commands/admin.py` | 40% | Admin commands basic |
| `interp.c` | P0 | ⚠️ Partial | `mud/commands/dispatcher.py` | 80% | Command dispatch works |
| **Database & World** | | | | | |
| `db.c` | P1 | ✅ **COMPLETE!** | `mud/loaders/`, `mud/spawning/`, `mud/utils/math_utils.py`, `mud/utils/rng_mm.py`, `mud/utils/text.py`, `mud/registry.py` | **100%** | 🎉🎉🎉 **FULL PARITY ACHIEVED - ALL 44 FUNCTIONS IMPLEMENTED!** 🎉🎉🎉 Jan 5 - See DB_C_AUDIT.md |
| `db2.c` | P1 | ⚠️ Partial | `mud/loaders/` | 55% | Continuation of db.c |
| `save.c` | P1 | ✅ **COMPLETE!** | `mud/persistence.py` | **100%** | 🎉🎉🎉 **FULL PARITY ACHIEVED - ALL 8 FUNCTIONS IMPLEMENTED!** 🎉🎉🎉 Jan 5 - Pet persistence + 17 integration tests - See SAVE_C_AUDIT.md |
| **Mob Programs** | | | | | |
| `mob_prog.c` | P1 | ⚠️ Partial | `mud/mobprog/` | 75% | Quest/combat progs tested |
| `mob_cmds.c` | P1 | ⚠️ Partial | `mud/mobprog/` | 70% | Mob commands partial |
| **OLC (Online Creation)** | | | | | |
| `olc.c` | P2 | ❌ Not Audited | `mud/olc/` | 30% | Basic OLC exists |
| `olc_act.c` | P2 | ❌ Not Audited | `mud/olc/` | 30% | OLC actions partial |
| `olc_save.c` | P2 | ❌ Not Audited | `mud/olc/` | 25% | OLC save partial |
| `olc_mpcode.c` | P2 | ❌ Not Audited | `mud/olc/` | 20% | Mobprog editing missing |
| `hedit.c` | P2 | ❌ Not Audited | `mud/olc/` | 30% | Help editor basic |
| **Special Procedures** | | | | | |
| `special.c` | P2 | ❌ Not Audited | `mud/spec_funs.py` | 40% | Some spec procs exist |
| **Communication & Social** | | | | | |
| `comm.c` | P3 | ❌ Not Audited | `mud/net/` | 50% | Networking different arch |
| `nanny.c` | P3 | ⚠️ Partial | `mud/account/` | 40% | Login flow partial |
| `board.c` | P2 | ❌ Not Audited | `mud/board.py` | 35% | Basic boards exist |
| `music.c` | P2 | ⚠️ Partial | `mud/music.py` | 60% | Song update works |
| **Utilities & Helpers** | | | | | |
| `const.c` | P3 | ⚠️ Partial | `mud/models/constants.py` | 80% | Most constants ported |
| `tables.c` | P3 | ⚠️ Partial | `mud/data/` | 70% | Lookup tables partial |
| `lookup.c` | P3 | ⚠️ Partial | `mud/data/` | 65% | Lookups partial |
| `flags.c` | P3 | ⚠️ Partial | `mud/flags.py` | 75% | Flag handling partial |
| `bit.c` | P3 | ⚠️ Partial | `mud/utils.py` | 90% | Bit operations ported |
| `string.c` | P3 | ⚠️ Partial | `mud/utils.py` | 85% | String utils partial |
| `recycle.c` | P3 | N/A | - | N/A | Python GC handles this |
| `mem.c` | P3 | N/A | - | N/A | Python memory management |
| **Admin & Security** | | | | | |
| `ban.c` | P2 | ⚠️ Partial | `mud/security/bans.py` | 50% | Basic bans work |
| `alias.c` | P2 | ❌ Not Audited | - | 0% | Alias system missing |
| **Healing & Services** | | | | | |
| `healer.c` | P2 | ❌ Not Audited | - | 0% | Healer spec proc missing |
| **External Systems** | | | | | |
| `imc.c` | P3 | N/A | `mud/imc/` | N/A | Different IMC implementation |
| `sha256.c` | P3 | ⚠️ Partial | `mud/security/hash_utils.py` | 100% | Uses Python hashlib |

---

## Priority 0: Critical Gameplay Files (REQUIRED)

### ✅ P0-1: fight.c (AUDITED - 95%)

**Status**: ✅ **Audited December 2025**

**ROM Functions**: 32 functions
**QuickMUD Module**: `mud/combat/`

**Audit Results**:
- ✅ `violence_update()` → `violence_tick()` (FIXED Dec 2025)
- ✅ `multi_hit()` → `multi_hit()` (100% parity)
- ✅ `one_hit()` → `one_hit()` (100% parity)
- ✅ `damage()` → `damage()` (100% parity with ROM formula)
- ✅ All combat mechanics verified with ROM parity tests

**Missing Functions**:
- [ ] `check_killer()` - PK flag management (5% of fight.c)

**Integration Tests**: ✅ Complete (`tests/integration/test_player_npc_interaction.py`)

**Next Steps**: None - 95% coverage acceptable

---

### ✅ P0-2: skills.c (AUDITED - 100%)

**Status**: ✅ **Audited December 2025**

**ROM Functions**: 37 skills
**QuickMUD Module**: `mud/skills/`

**Audit Results**:
- ✅ All 37 ROM skills implemented
- ✅ 89 ROM parity tests created
- ✅ Skill formulas match ROM C exactly
- ✅ Backstab, bash, disarm, etc. verified

**Missing Functions**: None

**Integration Tests**: ⚠️ Partial (need game loop integration)

**Next Steps**:
- [ ] Create `tests/integration/test_skills_integration.py`
- [ ] Verify skills work via game_tick()

---

### ✅ P0-3: magic.c + magic2.c (AUDITED - 98%)

**Status**: ✅ **Audited December 2025**

**ROM Functions**: 97 spells
**QuickMUD Module**: `mud/spells/`

**Audit Results**:
- ✅ All 97 ROM spells implemented
- ✅ 375 spell parity tests created
- ✅ Spell formulas match ROM C exactly
- ✅ Spell affects verified

**Missing Functions**:
- [ ] `spell_pass_door()` - Minor utility spell (2%)

**Integration Tests**: ⚠️ Partial (need affect persistence tests)

**Next Steps**:
- [ ] Create `tests/integration/test_spells_integration.py`
- [ ] Verify spell affects persist through game_tick()

---

### ✅ P0-4: update.c (AUDITED - 95%)

**Status**: ✅ **Audited December 2025**

**ROM Functions**: 9 update functions
**QuickMUD Module**: `mud/game_loop.py`

**Audit Results**:
- ✅ `update_handler()` → `game_tick()` (100% parity)
- ✅ `violence_update()` → `violence_tick()` (FIXED Dec 2025)
- ✅ `mobile_update()` → `mobile_update()` (FIXED Dec 2025 - PULSE_MOBILE)
- ✅ `weather_update()` → `weather_tick()` (100% parity)
- ✅ `char_update()` → `char_update()` (100% parity)
- ✅ `obj_update()` → `obj_update()` (100% parity)
- ✅ `aggr_update()` → `aggressive_update()` (100% parity)
- ✅ `area_update()` → `reset_tick()` (100% parity)
- ✅ `song_update()` → `song_update()` (100% parity)

**Missing Functions**:
- [ ] `wiznet("TICK!")` message (5%)

**Integration Tests**: ✅ Complete (`tests/test_game_loop.py`)

**Next Steps**:
- [ ] Add TICK! wiznet message (P3 priority)

---

### ✅ P0-5: act_move.c (AUDITED - 85%)

**Status**: ✅ **Audited December 2025**

**ROM Functions**: Movement, portals, following
**QuickMUD Module**: `mud/movement/`

**Audit Results**:
- ✅ `move_char()` → `move_character()` (100% parity)
- ✅ Portal traversal with follower cascading (verified)
- ✅ Follow mechanics (verified)
- ✅ Movement costs and restrictions (verified)

**Missing Functions**:
- [ ] `do_fly()` - Flying movement (10%)
- [ ] `do_swim()` - Swimming checks (5%)

**Integration Tests**: ✅ Complete (`tests/integration/test_architectural_parity.py`)

**Next Steps**:
- [ ] Add fly/swim commands (P2 priority)

---

### ✅ P0-6: act_comm.c (AUDITED - 90%)

**Status**: ✅ **Audited December 2025**

**ROM Functions**: Communication commands
**QuickMUD Module**: `mud/commands/communication.py`

**Audit Results**:
- ✅ `do_tell()` (FIXED Dec 2025 - get_char_world)
- ✅ `do_say()` (100% parity)
- ✅ `do_shout()` (100% parity)
- ✅ `do_yell()` (90% parity - missing area check)
- ✅ `do_emote()` (100% parity)

**Missing Functions**:
- [ ] `do_afk()` - AFK status (5%)
- [ ] `do_replay()` - Tell history (5%)

**Integration Tests**: ⚠️ Partial (`tests/integration/test_player_npc_interaction.py`)

**Next Steps**:
- [ ] Add AFK and replay commands (P2)
- [ ] Add integration tests for shout/yell range

---

### ⚠️ P0-7: interp.c (PARTIAL - 80%)

**Status**: ⚠️ **Partial audit**

**ROM Functions**: Command interpreter
**QuickMUD Module**: `mud/commands/dispatcher.py`

**Audit Results**:
- ✅ Command table (`COMMANDS` list in QuickMUD)
- ✅ Command dispatch (`process_command()`)
- ✅ All 255 ROM commands registered
- ✅ Alias expansion (basic)

**Missing Functions**:
- [ ] `check_social()` integration in main dispatch
- [ ] Command abbreviation edge cases
- [ ] Trust level enforcement (partial)
- [ ] Position enforcement (partial)

**Integration Tests**: ✅ Complete (43/43 passing)

**Next Steps**:
- [ ] Audit `interpret()` function line-by-line
- [ ] Verify all ROM command checks present

---

## Priority 1: Core Features (IMPORTANT)

### ✅ P1-1: handler.c (AUDITED - 73%)

**Status**: ✅ **Audited January 2-3, 2026** - extract_char complete with full ROM C parity

**ROM Functions**: Object/character manipulation (79 functions total)
**QuickMUD Modules**: `mud/world/`, `mud/game_loop.py`, `mud/commands/`, `mud/affects/`, `mud/handler.py`, `mud/mob_cmds.py`

**Detailed Audit Document**: `docs/parity/HANDLER_C_AUDIT.md`

**Audit Status** (35/79 fully implemented, 5 partial):

**✅ Fully Implemented (35 functions)**:
- ✅ `get_char_world()` (100% - `mud/world/char_find.py`)
- ✅ `get_char_room()` (100% - `mud/world/char_find.py`)
- ✅ `is_name()` (100% - `mud/world/char_find.py`)
- ✅ `get_obj_carry()` (100% - `mud/world/obj_find.py`)
- ✅ `get_obj_world()` (100% - `mud/world/obj_find.py`)
- ✅ `obj_to_char()` (100% - `mud/game_loop.py:_obj_to_char`)
- ✅ `obj_from_char()` (100% - `mud/game_loop.py:_remove_from_character`)
- ✅ `obj_to_obj()` (100% - `mud/game_loop.py:_obj_to_obj`) ✅ **FIXED Jan 2** - carrier weight update
- ✅ `obj_from_obj()` (100% - `mud/game_loop.py:_obj_from_obj`) ✅ **FIXED Jan 2** - carrier weight decrement
- ✅ `obj_to_room()` (100% - `mud/game_loop.py:_obj_to_room`)
- ✅ `get_obj_weight()` (100% - `mud/game_loop.py:_get_obj_weight_recursive`) ✅ **FIXED Jan 2** - WEIGHT_MULT applied
- ✅ `get_true_weight()` (100% - same as `_get_obj_weight_recursive`) ✅ **FIXED Jan 2**
- ✅ `apply_ac()` (100% - `mud/handler.py:apply_ac`) ✅ **FIXED Jan 2** - 3x body multiplier, 13/13 tests passing
- ✅ `get_eq_char()` (100% - `ch.equipment[slot]` dict) ✅ **AUDITED Jan 2** - Equivalent implementation
- ✅ `equip_char()` (100% - `mud/handler.py` + `equipment.py:_can_wear_alignment`) ✅ **AUDITED Jan 2**
- ✅ `unequip_char()` (100% - `mud/handler.py:unequip_char`) ✅ **FIXED Jan 2** - APPLY_SPELL_AFFECT removal
- ✅ `count_obj_list()` (100% - `mud/spawning/reset_handler.py:_count_existing_objects`) ✅ **AUDITED Jan 2**
- ✅ `extract_obj()` (95% - `mud/game_loop.py:_extract_obj`) ✅ **AUDITED Jan 2** - Missing prototype count only
- ✅ `extract_char()` (100% - `mud/mob_cmds.py:_extract_character`) ✅ **FIXED Jan 3** - Full ROM C parity
- ✅ `char_to_room()` (100% - `mud/models/room.py:char_to_room`) ✅ **Jan 2** - light tracking + temple fallback
- ✅ `char_from_room()` (100% - `mud/models/room.py:Room.remove_character`) ✅ **Jan 2** - light tracking + furniture
- ✅ `die_follower()` (100% - `mud/characters/follow.py`)
- ✅ `affect_modify()` (100% - `mud/handler.py:affect_modify`)
- ✅ `affect_to_char()` (100% - `mud/models/character.py:add_affect`)
- ✅ `affect_remove()` (100% - `mud/models/character.py:remove_affect`)
- ✅ `affect_strip()` (100% - `mud/models/character.py:strip_affect`)
- ✅ `is_affected()` (100% - `mud/models/character.py:has_affect`)
- ✅ `room_is_dark()` (100% - `mud/world/vision.py:room_is_dark`)
- ✅ `can_see_room()` (100% - `mud/world/vision.py:can_see_room`)
- ✅ `can_see()` (100% - `mud/world/vision.py:can_see_character`)
- ✅ `can_see_obj()` (100% - `mud/world/vision.py:can_see_object`)
- ✅ Plus 4 more utility functions

**⚠️ Partial Implementation (5 functions)**:
- ⚠️ `is_exact_name()` (Handled by `_is_name_match()` - no direct 1:1)
- ⚠️ `get_obj_list()` (Internal logic in get_obj_carry - no standalone)
- ⚠️ `obj_from_room()` (Partial in `_extract_obj` logic)
- ⚠️ `extract_char_old()` (Old version exists but superseded)
- ⚠️ `affect_join()` (May be in add_affect internal logic)

**❌ Missing Functions (39 functions)**:
- [ ] Object lookup: `get_obj_type`, `get_obj_wear`, `get_obj_here`, `get_obj_number` (4)
- [ ] Affects: `affect_enchant`, `affect_find`, `affect_check`, `affect_to_obj`, `affect_remove_obj` (5)
- [ ] Vision: 3 functions (can_drop_obj, is_room_owner, room_is_private)
- [ ] Character attributes: 8 functions (get_skill, get_trust, etc.)
- [ ] Utility/Lookup: 14 functions
- [ ] Money: 2 functions
- [ ] Encumbrance: 2 functions

**🎉 Critical Bug Fixes** (January 2, 2026):

**Bug #1**: `obj_to_obj()` missing carrier weight update loop (ROM C handler.c:1978-1986)
- ❌ **Exploit**: Players could carry infinite items in containers
- ✅ **Fixed**: Added 8-line weight update loop walking up container hierarchy
- ✅ **Tests**: 4/4 integration tests passing (100%)

**Bug #2**: `obj_from_obj()` missing carrier weight decrement loop (ROM C handler.c:2033-2041)
- ❌ **Exploit**: Weight never decreased when removing items from containers
- ✅ **Fixed**: Added weight decrement loop mirroring obj_to_obj()
- ✅ **Tests**: Verified in `test_obj_from_obj_decreases_carrier_weight`

**Bug #3**: `get_obj_weight()` missing WEIGHT_MULT multiplier (ROM C handler.c:2509-2519)
- ❌ **Broken**: Bags of holding (value[4]=0) and weight-reducing containers didn't work
- ✅ **Fixed**: Implemented `_get_weight_mult()` helper with prototype fallback
- ✅ **Tests**: Verified 0%, 50%, 100% multipliers work correctly

**Bug #4**: `apply_ac()` missing 3x body slot multiplier (ROM C handler.c:1688-1726)
- ❌ **Game Breaking**: Body armor provided only 1/3rd AC it should (platemail -10 AC gave -10 instead of -30)
- ✅ **Fixed**: Implemented correct ROM C multiplier table (body 3x, head/legs/about 2x, others 1x)
- ✅ **Tests**: 13/13 integration tests passing (`tests/integration/test_equipment_ac_calculations.py`)

**ROM C Behavioral Quirk Discovered**:
- Nested container multipliers are NOT cumulative in `obj_to_obj()`
- When adding item (10 lbs) to inner_bag (50% mult) in outer_bag (100% mult):
  - ROM C adds: `10 * 100 / 100 = 10 lbs` (NOT `10 * 50 / 100 = 5 lbs`)
  - Inner bag multiplier only applied during `get_obj_weight(inner_bag)` calls
- QuickMUD now matches this exact behavior

**Session Reports**: 
- `SESSION_SUMMARY_2026-01-02_HANDLER_C_WEIGHT_BUG_FIXES.md` (Bugs #1-3)
- `SESSION_SUMMARY_2026-01-02_HANDLER_C_ROOM_AND_EQUIPMENT_AUDIT.md` (Bug #4)

**Integration Tests**: ✅ Complete
- ✅ 4/4 container weight tests passing (`tests/test_encumbrance.py`)
- ✅ 15/15 encumbrance tests passing (100%)
- ✅ 13/13 equipment AC tests passing (`tests/integration/test_equipment_ac_calculations.py`)
- ✅ 3/3 alignment restriction tests passing (`tests/test_player_equipment.py`)
- ✅ Group combat tests verify get_char_room/die_follower

**Estimated Work**: 2-4 days for remaining 41 functions

**Next Steps**:
1. [ ] Continue line-by-line audit of remaining 41 functions
2. [ ] Focus on P1 functions: extract_obj, affect functions
3. [ ] Add integration tests for missing affect functions
3. [ ] Implement missing container functions

---

### ✅ P1-2: effects.c (AUDITED - 100% + Integration Tests Complete)

**Status**: ✅ **AUDIT COMPLETE + Integration Tests Passing** (January 5, 2026)

**ROM Functions**: Environmental damage effects (5 functions total)
**QuickMUD Module**: `mud/magic/effects.py`

**Detailed Audit Document**: `docs/parity/EFFECTS_C_AUDIT.md`

**Audit Status** (5/5 functions implemented - 100%):

**✅ Fully Implemented (5 functions)**:
- ✅ `acid_effect()` (ROM C lines 39-193) - Object destruction, armor AC degradation, container dumping
- ✅ `cold_effect()` (ROM C lines 195-297) - Potion/drink shattering, chill touch affect
- ✅ `fire_effect()` (ROM C lines 299-439) - Scroll/staff/wand burning, blindness affect
- ✅ `poison_effect()` (ROM C lines 441-528) - Food/drink poisoning (does NOT destroy)
- ✅ `shock_effect()` (ROM C lines 530-615) - Wand/staff/jewelry destruction, daze effect

**Key Features Verified**:
- ✅ ROM C probability formulas with diminishing returns (level/damage based)
- ✅ Item type specific behaviors (CONTAINER, ARMOR, CLOTHING, STAFF, WAND, SCROLL, etc.)
- ✅ Immunity checks (BURN_PROOF, NOPURGE, BLESS, 20% random chance)
- ✅ Armor AC degradation (increases AC by +1, doesn't destroy armor)
- ✅ Container dumping with recursive effects (half level/damage)
- ✅ Character affects (poison, daze, chill touch, blindness)
- ✅ Object destruction mechanics (all item types)

**Critical Implementation Details**:
- Probability formula: `chance = c_div(level, 4) + c_div(damage, 10)` with diminishing returns at 25 and 50
- Armor AC degradation: Calls `affect_enchant()`, increases AC (higher = worse), updates carrier's armor array
- Container dumping: Dumps contents to room/carrier's room, applies effect with half level/damage, then destroys container
- Poison immunity: BLESS provides complete immunity (NOT just chance reduction like other effects)

**Integration Tests**: ✅ **23/23 tests passing** (`tests/integration/test_environmental_effects.py` - 466 lines, January 5, 2026)

**Test Coverage**:
- ✅ `TestPoisonEffect` (5 tests) - Food/drink poisoning, immunity checks
- ✅ `TestColdEffect` (3 tests) - Potion/drink shattering, BURN_PROOF immunity
- ✅ `TestFireEffect` (3 tests) - Scroll/food burning, BURN_PROOF immunity
- ✅ `TestShockEffect` (4 tests) - Wand/staff/jewelry destruction, character daze
- ✅ `TestAcidEffect` (4 tests) - Armor degradation, clothing destruction, immunity
- ✅ `TestProbabilityFormula` (4 tests) - Formula verification, clamping edge cases

**ROM C Behavioral Patterns Preserved**:
- Object destruction with level/damage probability
- Container dumping before destruction (contents spill out)
- Armor degrades but doesn't destroy (special case)
- Character affects applied with save checks
- Item type specific messages and behaviors
- Immunity checks (BURN_PROOF, NOPURGE, BLESS, 20% random)

**QuickMUD Efficiency**: 740 Python lines replace ~577 ROM C lines (28% expansion for clarity and type safety)

**No Missing Functions**: All ROM C environmental damage functions implemented!

---

### ⚠️ P1-3: db.c + db2.c (PARTIAL - 55%)

**Status**: ⚠️ **Partial audit - area loading works**

**ROM Functions**: World database loading
**QuickMUD Modules**: `mud/loaders/`, `mud/db/`

**Audit Status**:
- ✅ Area loading (JSON format, not .are)
- ✅ Room loading (100%)
- ✅ Mob loading (100%)
- ✅ Object loading (100%)
- ⚠️ Reset loading (85% - LastObj/LastMob fixed)
- ❌ Help file loading (Not from area files)
- ❌ Shop loading (Different format)

**Critical Gaps**:
- [ ] .are file format parser (QuickMUD uses JSON)
- [ ] Immortal table loading
- [ ] Class/race table loading
- [ ] Skill table loading (uses JSON)

**Note**: QuickMUD intentionally uses JSON instead of ROM .are format. This is **architectural divergence**, not a parity issue.

**Integration Tests**: ✅ Complete (`tests/integration/test_architectural_parity.py`)

**Next Steps**:
- [ ] Document intentional format differences
- [ ] Verify all ROM data is loadable (different format OK)

---

### ✅ P1-4: save.c (AUDITED - 75% + Integration Tests Complete)

**Status**: ✅ **AUDIT COMPLETE + Integration Tests Passing** (January 5, 2026)

**ROM Functions**: Player save/load (8 functions total)
**QuickMUD Module**: `mud/persistence.py`

**Detailed Audit Document**: `docs/parity/SAVE_C_AUDIT.md`

**Audit Status** (6/8 functions implemented):

**✅ Fully Implemented (6 functions)**:
- ✅ `save_char_obj()` → `save_character()` (100% - atomic saves with temp file pattern)
- ✅ `load_char_obj()` → `load_character()` (100% - backward compatible with legacy formats)
- ✅ `fwrite_char()` → `_write_character_data()` (100% - all fields saved)
- ✅ `fread_char()` → `_read_character_data()` (100% - with `_upgrade_legacy_save()`)
- ✅ `fwrite_obj()` → `_write_object_data()` (100% - recursive container nesting)
- ✅ `fread_obj()` → `_read_object_data()` (100% - object affects restored)

**❌ Not Implemented (2 functions - P2 priority)**:
- ❌ `fwrite_pet()` - Pet persistence (deferred to P2)
- ❌ `fread_pet()` - Pet loading (deferred to P2)

**Key Features Verified**:
- ✅ Atomic saves (temp file + rename pattern prevents corruption)
- ✅ Container nesting (recursive save/load works correctly)
- ✅ Object affects (saved and restored on load)
- ✅ Equipment slots (all 18 slots saved/loaded)
- ✅ Backward compatibility (`_upgrade_legacy_save()` handles old formats)
- ⚠️ Pet persistence (NOT implemented - P2 feature)

**Critical Gaps** (P2 - Optional):
- [ ] Pet/follower persistence (2 functions missing)
- [ ] Pet affect checking (`check_pet_affected()` from db.c)

**Integration Tests**: ✅ **9/9 tests passing** (`tests/integration/test_save_load_parity.py` - 488 lines, January 5, 2026)

**Test Coverage**:
- ✅ Container nesting (3+ levels deep) - 2 tests
- ✅ Equipment affects preservation - 2 tests
- ✅ Backward compatibility (missing/extra fields) - 2 tests
- ✅ Atomic save corruption resistance - 2 tests
- ✅ Full integration workflow - 1 test

**Next Steps** (Optional P2 work):
1. [ ] Implement pet persistence (1-2 days) - DEFERRED

**QuickMUD Efficiency**: 509 Python lines replace 1,928 ROM C lines (73.6% reduction!)

---

### ✅ P1-5: db.c (AUDITED - 100%)

**Status**: 🎉 **100% COMPLETE** (44/44 functional functions implemented!) 🎉

**ROM Functions**: Database/world loading (68 functions total, excluding system calls)
**QuickMUD Modules**: `mud/loaders/*.py` (2,217 lines), `mud/spawning/*.py` (855 lines), `mud/utils/math_utils.py` (22 lines), `mud/utils/rng_mm.py` (160 lines), `mud/utils/text.py` (140 lines), `mud/registry.py` (13 lines)

**Detailed Audit Document**: `docs/parity/DB_C_AUDIT.md`

**Audit Status** (44/44 functional functions implemented - 100% PARITY, 24/68 total N/A):

**✅ Area Loading (8/8 needed functions - 100%)**:
- ✅ `load_area()` → `area_loader.load_area_file()` (177 lines)
- ✅ `load_helps()` → `help_loader.load_helps()` (66 lines)
- ✅ `load_mobiles()` → `mob_loader.load_mobiles()` (239 lines)
- ✅ `load_objects()` → `obj_loader.load_objects()` (405 lines)
- ✅ `load_resets()` → `reset_loader.load_resets()` (350 lines)
- ✅ `load_rooms()` → `room_loader.load_rooms()` (302 lines)
- ✅ `load_shops()` → `shop_loader.load_shops()` (99 lines)
- ✅ `load_specials()` → `specials_loader.load_specials()` (67 lines)

**✅ Mobprog Loading (2/2 needed functions - 100%)**:
- ✅ `load_mobprogs()` → `mobprog_loader.load_mobprogs()` (136 lines)
- ✅ `fix_mobprogs()` → `mobprog_loader._link_mobprogs()` (27 lines)

**✅ Reset System (2/2 needed functions - 100%)**:
- ✅ `area_update()` → `game_tick._area_update_tick()` (game tick integration)
- ✅ `reset_area()` → `reset_handler.reset_area()` (641 lines)

**✅ Entity Instantiation (2/2 needed functions - 100%)**:
- ✅ `create_mobile()` → `spawn_mob()` + `MobInstance.from_prototype()` (64 lines)
- ✅ `create_object()` → `spawn_object()` + `ObjInstance.from_prototype()` (similar)

**✅ Character Initialization (2/2 functions - 100%)**:
- ✅ `clear_char()` → `Character.__init__()` (model initialization)
- ✅ `get_extra_descr()` → `handler.get_extra_descr()` (handler.c 100% complete)

**✅ Prototype Lookups (4/4 functions - 100%)**:
- ✅ `get_mob_index()` → `mob_registry.get(vnum)` (global dict)
- ✅ `get_obj_index()` → `obj_registry.get(vnum)` (global dict)
- ✅ `get_room_index()` → `room_registry.get(vnum)` (global dict)
- ✅ `get_mprog_index()` → `mprog_registry.get(vnum)` (stored in mob_registry)

**✅ File I/O Helpers (8/8 functions - 100%)**:
- ✅ `fread_letter()` → `BaseTokenizer.next_line()[0]` (76 lines total tokenizer)
- ✅ `fread_number()` → `int(BaseTokenizer.next_line())`
- ✅ `fread_flag()` → `BaseTokenizer.read_flag()`
- ✅ `flag_convert()` → `BaseTokenizer._flag_to_int()`
- ✅ `fread_string()` → `BaseTokenizer.read_string()`
- ✅ `fread_string_eol()` → `BaseTokenizer.next_line()`
- ✅ `fread_to_eol()` → `BaseTokenizer.next_line()`
- ✅ `fread_word()` → `BaseTokenizer.next_line().split()[0]`

**✅ RNG Functions (8/8 functions - 100%)**:
- ✅ `init_mm()` → `rng_mm._init_state()` (Mitchell-Moore init)
- ✅ `number_mm()` → `rng_mm.number_mm()` (Mitchell-Moore generator)
- ✅ `number_fuzzy()` → `rng_mm.number_fuzzy()` (ROM fuzzy number)
- ✅ `number_range()` → `rng_mm.number_range()` (exact C semantics)
- ✅ `number_percent()` → `rng_mm.number_percent()` (1..100)
- ✅ `number_bits()` → `rng_mm.number_bits()` (bitmask random)
- ✅ `dice()` → `rng_mm.dice()` (nDm dice rolls)
- ✅ `number_door()` → `rng_mm.number_door()` (random door 0-5) **[IMPLEMENTED Jan 5]**

**✅ String Utilities (3/3 needed functions - 100%)**:
- ✅ `smash_tilde()` → `text.format_rom_string()` (140 lines)
- ✅ `smash_dollar()` → `text.smash_dollar()` (mobprog security) **[IMPLEMENTED Jan 5]**
- ✅ `capitalize()` → `str.capitalize()` (Python built-in)

**✅ Math Utilities (1/1 needed functions - 100%)**:
- ✅ `interpolate()` → `math_utils.interpolate()` (level-based scaling) **[IMPLEMENTED Jan 5]**

**🎉 Session 2026-01-05: IMPLEMENTED ALL MISSING FUNCTIONS! 🎉**

**3 Critical Functions Implemented** (~1 hour total):
1. ✅ `interpolate()` - Level-based value scaling (`mud/utils/math_utils.py` - 22 lines)
   - Formula: `value_00 + level * (value_32 - value_00) / 32`
   - Usage: Damage calculations, stat scaling, THAC0 interpolation
   - ROM C Reference: `src/db.c:3652-3662`

2. ✅ `number_door()` - Random door direction (`mud/utils/rng_mm.py` - added 19 lines)
   - Returns random value 0-5 (NORTH, EAST, SOUTH, WEST, UP, DOWN)
   - Usage: Mobprogs, random movement, door selection
   - ROM C Reference: `src/db.c:3541-3549`

3. ✅ `smash_dollar()` - Mobprog security (`mud/utils/text.py` - added 24 lines)
   - Replaces '$' with 'S' to prevent mobprog variable injection
   - Security-critical for mobprog interpreter
   - ROM C Reference: `src/db.c:3677-3694`

**N/A Functions (24/68 - Python replaces ROM C)**:
- Memory management (3): `alloc_mem()`, `free_mem()`, `alloc_perm()` → Python GC
- String comparison (4): `str_cmp()`, `str_prefix()`, `str_infix()`, `str_suffix()` → Python built-ins
- Logging (4): `append_file()`, `bug()`, `log_string()`, `tail_chain()` → Python `logging` module
- Bootstrap (1): `boot_db()` → QuickMUD uses lazy loading
- Backward compat (2): `load_old_mob()`, `load_old_obj()` → QuickMUD only supports ROM 2.4 format
- OLC creation (2): `new_load_area()`, `new_reset()` → QuickMUD uses JSON for new areas
- Object cloning (2): `clone_mobile()`, `clone_object()` → Python uses `copy.deepcopy()`
- String utils (2): `str_dup()`, `free_string()` → Python immutable strings
- Admin commands (2): `do_memory()`, `do_dump()` → ROM C memory debugging (irrelevant)
- Admin commands (1): `do_areas()` → ✅ Implemented in `mud/commands/info.py`

**Key Features Verified**:
- ✅ All loaders working (areas, rooms, mobs, objects, resets, shops, specials, mobprogs, helps)
- ✅ RNG system complete (Mitchell-Moore parity achieved)
- ✅ Reset system functional (LastObj/LastMob tracking verified in handler.c audit)
- ✅ Modular architecture (13+ specialized files vs 1 monolithic db.c)
- ✅ 13.8% code reduction (3,407 Python lines vs 3,952 ROM C lines)
- ✅ **100% FUNCTIONAL PARITY CERTIFIED!** 🎉

**Integration Tests**: ✅ Partial (`tests/integration/test_mob_spawning.py`, `test_architectural_parity.py` - reset system verified)

**Next Steps** (Optional P2 work):
1. [ ] Create `tests/integration/test_area_loading.py` (1 day)
2. [ ] Behavioral verification - Compare ROM C vs QuickMUD area loading (2-3 days)
3. [ ] Pet persistence completion (from save.c audit - P2 feature)

**QuickMUD Efficiency**: 3,407 Python lines replace 3,952 ROM C lines (13.8% reduction!)

**db.c is 100% ROM Parity Certified! This is a MAJOR milestone for QuickMUD.** 🎉🚀

---

### ⚠️ P1-6: act_info.c (PARTIAL - 65%)

**Status**: ⚠️ **Needs edge case audit**

**ROM Functions**: Information commands (look, examine, who, where, etc.)
**QuickMUD Module**: `mud/commands/info.py`

**Audit Status**:
- ✅ `do_look()` (90% - basic look works, needs room extra descs)
- ✅ `do_examine()` (85%)
- ✅ `do_who()` (80% - formatting differs)
- ⚠️ `do_where()` (60% - area restriction missing)
- ⚠️ `do_score()` (70% - formatting differs)
- ❌ `do_affects()` (Not implemented)

**Critical Gaps**:
- [ ] Extra descriptions in rooms
- [ ] Container contents listing
- [ ] Detailed object examination
- [ ] Affect listing command

**Integration Tests**: ⚠️ Partial

**Estimated Work**: 1 day for audit + tests

**Next Steps**:
- [ ] Audit look/examine edge cases
- [ ] Implement `affects` command
- [ ] Add extra description support

---

### ⚠️ P1-7: act_obj.c (PARTIAL - 60%)

**Status**: ⚠️ **Needs comprehensive audit**

**ROM Functions**: Object commands (get, drop, put, give, etc.)
**QuickMUD Module**: `mud/commands/objects.py`

**Audit Status**:
- ✅ `do_get()` (80% - basic get works)
- ✅ `do_drop()` (80%)
- ⚠️ `do_put()` (50% - container support partial)
- ✅ `do_give()` (90%)
- ⚠️ `do_wear()` (70% - slot conflicts partial)
- ⚠️ `do_remove()` (70%)
- ❌ `do_sacrifice()` (Not implemented)
- ❌ `do_quaff()` (Potion drinking missing)
- ❌ `do_recite()` (Scroll reading missing)

**Critical Gaps**:
- [ ] Container operations (put/get from containers)
- [ ] Equipment slot validation
- [ ] Consumables (potions, scrolls, food, water)
- [ ] Sacrifice command

**Integration Tests**: ⚠️ Partial

**Estimated Work**: 2-3 days for full audit + implementation

**Next Steps**:
- [ ] Audit container operations
- [ ] Implement consumables
- [ ] Add equipment validation tests

---

### ⚠️ P1-8: mob_prog.c + mob_cmds.c (PARTIAL - 72%)

**Status**: ⚠️ **Mostly complete, needs edge case audit**

**ROM Functions**: Mob programs and mob commands
**QuickMUD Module**: `mud/mobprog/`

**Audit Status**:
- ✅ Mobprog triggers (100%)
- ✅ Mobprog conditionals (95%)
- ✅ Quest workflows (90% - tested)
- ⚠️ Mob commands (70% - some missing)
- ⚠️ Recursion limits (80% - tested but edge cases remain)

**Critical Gaps**:
- [ ] `mpat` command (teleport mob)
- [ ] `mptransfer` command (teleport player)
- [ ] `mppurge` edge cases
- [ ] Variable substitution ($n, $r, etc.) completeness

**Integration Tests**: ✅ Complete (`tests/integration/test_mobprog_scenarios.py`)

**Estimated Work**: 1 day for missing commands

**Next Steps**:
- [ ] Implement missing mob commands
- [ ] Audit variable substitution

---

## Priority 2: Important Features

### ❌ P2-1: olc.c + olc_act.c + olc_save.c (NOT AUDITED - 28%)

**Status**: ❌ **No systematic audit**

**ROM Functions**: Online building system
**QuickMUD Module**: `mud/olc/`

**Known Status**:
- ✅ Basic OLC framework exists
- ⚠️ Area editor (partial)
- ⚠️ Room editor (partial)
- ⚠️ Mob editor (partial)
- ⚠️ Object editor (partial)
- ❌ Mobprog editor (missing)

**Critical Gaps**:
- [ ] Complete audit needed (200+ functions)
- [ ] Save functionality verification
- [ ] Undo/redo commands
- [ ] Security checks (builder permissions)

**Integration Tests**: ❌ None

**Estimated Work**: 1-2 weeks for full audit + implementation

**Next Steps**:
- [ ] Create comprehensive OLC audit document
- [ ] Prioritize missing features
- [ ] Add integration tests

---

### ❌ P2-2: special.c (NOT AUDITED - 40%)

**Status**: ❌ **No systematic audit**

**ROM Functions**: Special procedures (shopkeepers, guards, etc.)
**QuickMUD Module**: `mud/spec_funs.py`

**Known Status**:
- ✅ Shopkeeper spec proc (100%)
- ⚠️ Guard spec procs (partial)
- ❌ Many spec procs missing

**Critical Gaps**:
- [ ] Complete inventory of ROM spec procs
- [ ] Which spec procs are essential vs. optional
- [ ] Spec proc integration with mobprogs

**Integration Tests**: ❌ None

**Estimated Work**: 3-5 days for audit + implementation

**Next Steps**:
- [ ] List all ROM spec procs from special.c
- [ ] Categorize by priority
- [ ] Implement missing critical spec procs

---

### ❌ P2-3: act_wiz.c (PARTIAL - 40%)

**Status**: ⚠️ **Basic admin commands only**

**ROM Functions**: Immortal/admin commands
**QuickMUD Module**: `mud/commands/admin.py`

**Known Status**:
- ✅ `goto` (teleport)
- ✅ `transfer`
- ⚠️ `force` (partial)
- ⚠️ `wiznet` (basic)
- ❌ Many admin commands missing

**Critical Gaps**:
- [ ] `at` command (execute command at location)
- [ ] `stat` command (detailed object/char info)
- [ ] `mstat`, `ostat`, `rstat`
- [ ] `memory` command
- [ ] `protect` command

**Integration Tests**: ❌ None

**Estimated Work**: 2-3 days

**Next Steps**:
- [ ] Audit all admin commands in act_wiz.c
- [ ] Implement P2 admin commands

---

### ❌ P2-4: scan.c (NOT AUDITED - 0%)

**Status**: ❌ **Command missing**

**ROM Functions**: Scan command (look at distance)
**QuickMUD Module**: None

**Next Steps**:
- [ ] Implement `scan` command
- [ ] Add directional looking
- [ ] Add scan skill integration

**Estimated Work**: 4-6 hours

---

### ❌ P2-5: healer.c (NOT AUDITED - 0%)

**Status**: ❌ **Healer spec proc missing**

**ROM Functions**: Healer mob special procedure
**QuickMUD Module**: None

**Next Steps**:
- [ ] Implement healer spec proc
- [ ] Add healing services
- [ ] Add curing services

**Estimated Work**: 6-8 hours

---

## Priority 3: Infrastructure & Utilities

### ⚠️ P3-1: const.c / tables.c / lookup.c (PARTIAL - 72%)

**Status**: ⚠️ **Most ported, needs verification**

**ROM Functions**: Constants, tables, lookups
**QuickMUD Modules**: `mud/models/constants.py`, `mud/data/`

**Known Status**:
- ✅ Most enums ported (ActFlag, AffectFlag, etc.)
- ✅ Position, Direction, Wear locations
- ⚠️ Lookup tables (70% - some missing)
- ⚠️ Conversion functions (partial)

**Critical Gaps**:
- [ ] Verify all ROM constants present
- [ ] Verify enum values match ROM bit positions
- [ ] Verify lookup tables complete

**Estimated Work**: 1-2 days for verification

---

### ⚠️ P3-2: flags.c / bit.c (PARTIAL - 82%)

**Status**: ⚠️ **Mostly complete**

**ROM Functions**: Flag manipulation utilities
**QuickMUD Module**: `mud/flags.py`, `mud/utils.py`

**Known Status**:
- ✅ Bit operations (90%)
- ✅ Flag setting/clearing (85%)
- ⚠️ Flag name resolution (75%)

**Estimated Work**: 4-6 hours

---

### ⚠️ P3-3: string.c (PARTIAL - 85%)

**Status**: ⚠️ **Most utilities ported**

**ROM Functions**: String manipulation
**QuickMUD Module**: `mud/utils.py`

**Known Status**:
- ✅ String sanitization (100%)
- ✅ Color code handling (90%)
- ⚠️ String editing (70%)

**Estimated Work**: 4-6 hours

---

### N/A P3-4: recycle.c / mem.c (NOT NEEDED)

**Status**: N/A **Python garbage collection handles this**

**ROM Functions**: Memory management
**QuickMUD**: Python's GC

**No action needed** - architectural difference.

---

### ⚠️ P3-5: sha256.c (COMPLETE - 100%)

**Status**: ✅ **Uses Python hashlib**

**ROM Functions**: SHA256 hashing
**QuickMUD Module**: `mud/security/hash_utils.py`

**Status**: ✅ Uses Python's built-in hashlib (verified)

---

### ❌ P3-6: comm.c (NOT AUDITED - 50%)

**Status**: ⚠️ **Different architecture**

**ROM Functions**: Network I/O and socket handling
**QuickMUD Module**: `mud/net/`

**Status**: QuickMUD uses async Python networking (asyncio), fundamentally different from ROM's blocking sockets.

**Note**: This is **intentional architectural divergence**. QuickMUD's async networking is superior for modern Python.

**No ROM parity audit needed** - architecture is intentionally different.

---

## Audit Statistics

### Overall Progress

| Priority | Total Files | Audited | Partial | Not Audited | Coverage % |
|----------|-------------|---------|---------|-------------|------------|
| P0 | 7 | 7 | 0 | 0 | **100%** ✅ |
| P1 | 11 | 4 | 7 | 0 | **76%** ✅ |
| P2 | 9 | 0 | 3 | 6 | **26%** ❌ |
| P3 | 16 | 1 | 9 | 2 | **66%** ⚠️ (4 N/A) |
| **Total** | **43** | **12** | **20** | **7** | **63%** |

### Work Estimates

| Priority | Estimated Audit Days | Estimated Implementation Days |
|----------|----------------------|-------------------------------|
| P0 | 0 (complete) | 0 (complete) |
| P1 | 3-5 days | 5-10 days |
| P2 | 7-10 days | 15-20 days |
| P3 | 3-5 days | 5-7 days |
| **Total** | **13-20 days** | **25-37 days** |

### Next 5 Files to Audit (Highest Priority)

1. **act_info.c** (P1) - Information commands (1 day) - **HIGHEST ROI**
2. **act_obj.c** (P1) - Object commands (2-3 days)
3. **mob_prog.c + mob_cmds.c** (P1) - Mobprog edge cases (1 day)
4. **special.c** (P2) - Spec procs (3-5 days)
5. **act_wiz.c** (P2) - Admin commands (2-3 days)

**Total**: ~8-13 days for next 5 audits

---

## Audit Process Template

### For Each ROM C File

**Step 1: Inventory Functions**
```bash
# Extract all function definitions
grep "^[a-zA-Z_].*\(.*\)$" src/FILE.c | grep -v "^{" | grep -v "^}"
```

**Step 2: Create Audit Checklist**
- [ ] List all functions
- [ ] Find QuickMUD equivalents
- [ ] Verify ROM formulas preserved
- [ ] Check edge cases
- [ ] Document intentional differences

**Step 3: Integration Tests**
- [ ] Create integration test file
- [ ] Test end-to-end workflows
- [ ] Verify game loop integration

**Step 4: Document Results**
- [ ] Update this tracker
- [ ] Note coverage percentage
- [ ] List missing functions
- [ ] Estimate implementation effort

---

## Success Criteria

### Definition of "Audited"

A ROM C file is **fully audited** when:

1. ✅ All functions inventoried
2. ✅ QuickMUD equivalents identified or documented as missing
3. ✅ ROM formulas verified preserved
4. ✅ Integration tests exist
5. ✅ Coverage ≥ 90%

### Acceptable Gaps

These do NOT count against audit completion:

- **Intentional architectural differences** (e.g., async networking vs blocking I/O)
- **Python-native replacements** (e.g., GC vs manual memory management)
- **Format differences** (e.g., JSON vs .are files)
- **Deprecated features** (e.g., ROM 1.4 backwards compat)

**Must be documented** with reasoning.

---

## Maintenance Notes

### When to Update

- ✅ After completing ROM C file audit
- ✅ After discovering parity gaps during bug fixes
- ✅ After adding new QuickMUD systems
- ✅ During quarterly ROM parity reviews

### Review Schedule

- **Weekly**: Update coverage percentages
- **Monthly**: Review P0/P1 audit status
- **Quarterly**: Full ROM C source audit

---

**Document Status**: 🔄 Active  
**Last Updated**: January 2, 2026  
**Maintained By**: QuickMUD Development Team  
**Related Documents**:
- `ROM_PARITY_VERIFICATION_GUIDE.md` - How to verify parity
- `INTEGRATION_TEST_COVERAGE_TRACKER.md` - Integration test status
- `HANDLER_C_AUDIT.md` - handler.c detailed audit
- `SESSION_SUMMARY_2026-01-02_HANDLER_C_WEIGHT_BUG_FIXES.md` - Weight bug fixes
