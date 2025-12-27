# ROM 2.4b to Python Port: Comprehensive Parity Testing Plan

**Project:** QuickMUD - ROM 2.4b Python Port  
**Purpose:** Ensure 100% behavioral parity with original ROM 2.4b6 C codebase  
**Status:** Planning Phase  
**Last Updated:** December 27, 2025

---

## Executive Summary

This document outlines the complete testing strategy to verify that QuickMUD matches ROM 2.4b behavior across all systems. Tests are organized by ROM C source file structure for traceability.

**Current Status:** ~1500 tests exist, need ~3000+ for complete parity

---

## Testing Philosophy

1. **Behavioral Parity Over Code Parity** - Match ROM's observable behavior, not implementation details
2. **ROM C as Ground Truth** - All tests reference specific `src/*.c` files and line numbers
3. **Golden File Testing** - Capture ROM C output and match it exactly
4. **Integration Over Unit** - Test workflows, not just components
5. **Incremental Coverage** - Focus on high-impact systems first

---

## Test Organization

Tests are organized by ROM system, mirroring `src/` directory structure:

```
tests/
├── test_player_*.py          # Player/Character (src/handler.c, src/act_info.c)
├── test_mob_*.py             # Mobiles/NPCs (src/mob_prog.c, src/update.c)
├── test_combat_*.py          # Combat System (src/fight.c)
├── test_magic_*.py           # Spell System (src/magic.c)
├── test_skill_*.py           # Skills (src/skills.c, src/act_*.c)
├── test_object_*.py          # Objects/Items (src/handler.c, src/act_obj.c)
├── test_room_*.py            # Rooms/Areas (src/db.c)
├── test_command_*.py         # Commands (src/act_*.c)
└── integration/              # End-to-end workflows
```

---

## Priority Matrix

| System | Priority | Impact | Complexity | Current Coverage | Target Tests |
|--------|----------|--------|------------|------------------|--------------|
| **Characters** | P0 | Critical | Medium | 129 tests (46%) | 280 tests |
| **Combat** | P0 | Critical | High | 50 tests (30%) | 150 tests |
| **Commands** | P0 | Critical | Medium | 20 tests (10%) | 200 tests |
| **Objects** | P1 | High | Medium | 30 tests (25%) | 120 tests |
| **Rooms/Areas** | P1 | High | Low | 40 tests (50%) | 80 tests |
| **Mobiles/NPCs** | P1 | High | Medium | 25 tests (20%) | 125 tests |
| **Magic System** | P2 | Medium | High | 35 tests (15%) | 200 tests |
| **Skills** | P2 | Medium | High | 40 tests (25%) | 150 tests |
| **Social System** | P3 | Low | Low | 10 tests (20%) | 50 tests |
| **OLC/Building** | P3 | Low | Medium | 5 tests (5%) | 100 tests |
| **IMC/Channels** | P4 | Low | Medium | 0 tests (0%) | 50 tests |
| **Admin Tools** | P4 | Low | Low | 10 tests (10%) | 100 tests |

---

## System-by-System Testing Plans

### 1. Character System (P0) - 280 tests

**Status:** 129/280 tests (46%)  
**ROM Files:** `src/handler.c`, `src/act_info.c`, `src/save.c`  
**Plan:** See [CHARACTER_TEST_PLAN.md](CHARACTER_TEST_PLAN.md)

**Critical Gaps:**
- Equipment system (30 tests needed)
- Stats & attributes (20 tests needed)
- Combat attributes (15 tests needed)
- Save/load persistence (10 tests needed)

**Timeline:** 3 weeks (75 tests/week)

---

### 2. Combat System (P0) - 150 tests

**Status:** 50/150 tests (30%)  
**ROM Files:** `src/fight.c` (3000+ lines)

#### Sub-Systems

**A. Damage Calculation (30 tests)**
- [ ] test_damage_basic_formula
- [ ] test_damage_with_hitroll_damroll
- [ ] test_damage_dice_rolling
- [ ] test_damage_weapon_type_modifiers
- [ ] test_damage_critical_hits
- [ ] test_damage_armor_reduction
- [ ] test_damage_resistance_multipliers
- [ ] test_damage_vulnerability_multipliers
- [ ] test_damage_sanctuary_halving
- [ ] test_damage_minimum_one

**B. To-Hit Mechanics (20 tests)**
- [ ] test_thac0_calculation
- [ ] test_hit_vs_ac
- [ ] test_hit_dexterity_modifier
- [ ] test_hit_blind_penalty
- [ ] test_hit_invisibility_penalty
- [ ] test_hit_position_modifiers
- [ ] test_hit_skill_influence

**C. Combat Flow (25 tests)**
- [ ] test_one_hit_sequence
- [ ] test_multi_attack_rounds
- [ ] test_attack_triggers_counterattack
- [ ] test_death_handling
- [ ] test_corpse_creation
- [ ] test_experience_gain_on_kill
- [ ] test_group_exp_distribution

**D. Special Attacks (30 tests)**
- [ ] Weapon specials (flaming, frost, vampiric, sharp, vorpal)
- [ ] Mob special attacks (bash, trip, tail)
- [ ] Offensive skills (bash, kick, disarm)
- [ ] Defensive skills (dodge, parry, shield block)

**E. Combat States (20 tests)**
- [ ] test_initiative_determination
- [ ] test_position_changes_in_combat
- [ ] test_flee_mechanics
- [ ] test_wimpy_auto_flee
- [ ] test_rescue_mechanics

**F. PVP Combat (25 tests)**
- [ ] test_pk_flagging
- [ ] test_pk_timer
- [ ] test_safe_rooms_block_combat
- [ ] test_level_range_restrictions

**ROM C References:**
- `src/fight.c:one_hit` (lines 1200-1400)
- `src/fight.c:damage` (lines 1500-1800)
- `src/fight.c:violence_update` (lines 2500-2700)

---

### 3. Command System (P0) - 200 tests

**Status:** 20/200 tests (10%)  
**ROM Files:** `src/act_*.c` (multiple files)

#### Command Categories

**A. Movement Commands (25 tests)**
- north, south, east, west, up, down
- open, close, lock, unlock
- enter, exits, scan, where

**B. Object Manipulation (30 tests)**
- get, drop, put, give
- wear, remove, wield, hold
- eat, drink, quaff, recite, zap
- sacrifice, junk

**C. Communication (20 tests)**
- say, tell, reply, yell, shout
- emote, pemote
- channels (gossip, auction, etc.)

**D. Information (25 tests)**
- look, examine, inventory, equipment
- score, whois, who, where
- time, weather, help

**E. Combat Commands (20 tests)**
- kill, flee, rescue
- bash, kick, trip, disarm
- backstab, circle, dirt kick

**F. Social Commands (30 tests)**
- 100+ ROM socials (bow, wave, smile, etc.)
- Targeted vs untargeted variants

**G. Group Commands (15 tests)**
- group, ungroup, follow, lose
- split, gtell

**H. Magic Commands (20 tests)**
- cast, practice, spells
- channel, concentrate

**I. Misc Commands (15 tests)**
- sleep, wake, rest, stand, sit
- save, quit, password
- title, description, prompt

**ROM C References:**
- `src/act_move.c` - Movement
- `src/act_obj.c` - Object manipulation
- `src/act_comm.c` - Communication
- `src/act_info.c` - Information display

---

### 4. Object System (P1) - 120 tests

**Status:** 30/120 tests (25%)  
**ROM Files:** `src/handler.c`, `src/act_obj.c`

#### Sub-Systems

**A. Object Types (40 tests)**
- [ ] Weapons (damage dice, weapon type, flags)
- [ ] Armor (AC values, wear locations)
- [ ] Containers (capacity, weight multiplier, keys)
- [ ] Food/Drink (nutrition, liquid types)
- [ ] Potions/Pills/Scrolls/Wands/Staves
- [ ] Keys, lights, boats, portals
- [ ] Money, corpses, fountains

**B. Object Attributes (25 tests)**
- [ ] Weight and carry limits
- [ ] Value and cost calculations
- [ ] Durability and condition
- [ ] Extra flags (magic, glow, hum, etc.)
- [ ] Affects and bonuses

**C. Object Manipulation (30 tests)**
- [ ] Create/destroy objects
- [ ] Move objects between containers
- [ ] Wear/remove equipment
- [ ] Object decay and timer
- [ ] Object resets in areas

**D. Special Objects (25 tests)**
- [ ] Quest items
- [ ] Unique items (no-take, no-drop)
- [ ] Cursed items
- [ ] Level-restricted items
- [ ] Class/race-restricted items

---

### 5. Room/Area System (P1) - 80 tests

**Status:** 40/80 tests (50%)  
**ROM Files:** `src/db.c`, `src/db2.c`

#### Sub-Systems

**A. Room Attributes (20 tests)**
- [ ] Room flags (dark, no-mob, safe, etc.)
- [ ] Sector types (city, forest, water, etc.)
- [ ] Exits and doors
- [ ] Room capacity limits

**B. Area Management (20 tests)**
- [ ] Area loading from JSON/ARE files
- [ ] Area resets (mobs, objects, doors)
- [ ] Area flags and settings
- [ ] Cross-area references

**C. Special Rooms (15 tests)**
- [ ] Safe rooms (no combat)
- [ ] No-recall rooms
- [ ] Private/solitary rooms
- [ ] Pet shops
- [ ] Death traps

**D. Environment (25 tests)**
- [ ] Weather system
- [ ] Time of day
- [ ] Light/dark mechanics
- [ ] Sector movement costs
- [ ] Swim/fly/boat requirements

---

### 6. Mobile/NPC System (P1) - 125 tests

**Status:** 25/125 tests (20%)  
**ROM Files:** `src/mob_prog.c`, `src/update.c`, `src/db.c`

#### Sub-Systems

**A. Mob Attributes (30 tests)**
- [ ] Stats (level, hp, mana, move)
- [ ] Act flags (aggressive, sentinel, scavenger)
- [ ] Affected by flags
- [ ] Immunity/resistance/vulnerability
- [ ] Mob programs

**B. Mob AI (35 tests)**
- [ ] Aggression and hunting
- [ ] Scavenging items
- [ ] Wandering behavior
- [ ] Memory of attackers
- [ ] Assists and guards

**C. Mob Programs (30 tests)**
- [ ] Trigger types (greet, fight, death, etc.)
- [ ] Conditional logic (if/else)
- [ ] Actions (mpforce, mpmload, mptransfer, etc.)
- [ ] Variables and substitution

**D. Special Mobs (30 tests)**
- [ ] Shopkeepers
- [ ] Trainers and practices
- [ ] Questmasters
- [ ] Healers
- [ ] Guards and patrols

---

### 7. Magic System (P2) - 200 tests

**Status:** 35/200 tests (15%)  
**ROM Files:** `src/magic.c`, `src/magic2.c`

#### Sub-Systems

**A. Spell Mechanics (40 tests)**
- [ ] Mana costs
- [ ] Casting success rates
- [ ] Spell levels and restrictions
- [ ] Concentration and interruption
- [ ] Spell saves

**B. Offensive Spells (50 tests)**
- [ ] Damage spells by element (fire, cold, lightning, acid)
- [ ] Area effect spells
- [ ] Drain/curse spells
- [ ] Dispel magic

**C. Defensive Spells (30 tests)**
- [ ] Armor, shield, protection
- [ ] Sanctuary, stone skin
- [ ] Resist spells
- [ ] Cure/healing spells

**D. Utility Spells (30 tests)**
- [ ] Detect spells (magic, invisible, evil, etc.)
- [ ] Teleport, summon, gate
- [ ] Identify, locate object
- [ ] Word of recall

**E. Enchantment Spells (25 tests)**
- [ ] Enchant armor/weapon
- [ ] Recharge, bless
- [ ] Curse, poison

**F. Summoning (25 tests)**
- [ ] Create food/water/spring
- [ ] Summon creature
- [ ] Animate dead
- [ ] Clone

---

### 8. Skills System (P2) - 150 tests

**Status:** 40/150 tests (25%)  
**ROM Files:** `src/skills.c`, various `src/act_*.c`

#### Skill Categories

**A. Weapon Skills (30 tests)**
- [ ] Sword, dagger, axe, etc. proficiencies
- [ ] Improved damage/to-hit with mastery
- [ ] Disarm, parry with weapon

**B. Thief Skills (35 tests)**
- [ ] Steal, pick lock, pick pocket
- [ ] Hide, sneak, backstab
- [ ] Poison weapon, envenom
- [ ] Peek, haggle

**C. Warrior Skills (25 tests)**
- [ ] Bash, trip, kick
- [ ] Rescue, shield block
- [ ] Fast healing, second attack, third attack
- [ ] Berserk

**D. Cleric/Mage Skills (20 tests)**
- [ ] Meditation
- [ ] Scrolls, wands, staves
- [ ] Spell groups

**E. Passive Skills (25 tests)**
- [ ] Dodge, parry, shield block
- [ ] Fast healing, enhanced damage
- [ ] Detect hidden, awareness

**F. Learning System (15 tests)**
- [ ] Practice mechanics
- [ ] Skill improvement from use
- [ ] Skill groups and defaults
- [ ] Creation points allocation

---

### 9-12. Lower Priority Systems

**Social System (P3)** - 50 tests  
**OLC/Building (P3)** - 100 tests  
**IMC/Channels (P4)** - 50 tests  
**Admin Tools (P4)** - 100 tests

---

## Integration Test Strategy

### Key Workflows to Test End-to-End

1. **New Player Flow** (20 tests)
   - Character creation → equip starter gear → kill first mob → level up → recall

2. **Combat Flow** (30 tests)
   - Enter combat → attack sequence → special attacks → flee/death → loot corpse

3. **Shopping Flow** (15 tests)
   - Find shop → list items → buy/sell → haggle → equip purchased items

4. **Grouping Flow** (20 tests)
   - Form group → group combat → exp split → group loot → group movement

5. **Magic Flow** (25 tests)
   - Learn spells → practice → cast offensive → cast defensive → run out of mana

6. **Exploration Flow** (15 tests)
   - Movement → open doors → search for hidden → find quest item → return to questmaster

7. **PVP Flow** (20 tests)
   - Challenge player → combat → kill → KILLER flag → timer expiry

8. **Death/Resurrection Flow** (10 tests)
   - Death → corpse creation → recall → retrieve corpse → resurrect

---

## Test Data Strategy

### Golden Files
Store ROM C output for comparison:
```
tests/golden/
├── combat/
│   ├── damage_calculations.txt
│   ├── to_hit_rolls.txt
│   └── special_attacks.txt
├── spells/
│   ├── fireball_damage.txt
│   ├── heal_amounts.txt
│   └── area_effects.txt
└── commands/
    ├── score_output.txt
    ├── who_list.txt
    └── look_descriptions.txt
```

### Test Fixtures
```python
# conftest.py additions needed
- warrior_factory()
- thief_factory()
- cleric_factory()
- mage_factory()
- aggressive_mob_factory()
- shopkeeper_factory()
- weapon_factory()
- armor_factory()
- spell_factory()
```

---

## Implementation Timeline

### Phase 1: Foundation (Weeks 1-4) - P0 Systems
- **Week 1-3:** Complete character tests (151 tests)
- **Week 4:** Combat system core (50 tests)

### Phase 2: Core Gameplay (Weeks 5-10) - P0/P1
- **Week 5-6:** Combat completion (100 tests)
- **Week 7-8:** Command system (200 tests)
- **Week 9:** Objects (90 tests)
- **Week 10:** Rooms/Areas (40 tests)

### Phase 3: Advanced (Weeks 11-16) - P1/P2
- **Week 11-12:** Mobiles/NPCs (100 tests)
- **Week 13-14:** Magic system (165 tests)
- **Week 15-16:** Skills (110 tests)

### Phase 4: Polish (Weeks 17-20) - P2/P3
- **Week 17:** Integration tests (155 tests)
- **Week 18:** Social/OLC (150 tests)
- **Week 19-20:** Admin/IMC (150 tests)

**Total:** ~3000 tests in 20 weeks (150 tests/week average)

---

## Success Metrics

### Coverage Targets
- [ ] 95%+ line coverage in core systems
- [ ] 100% function coverage for public APIs
- [ ] 100% ROM C command coverage (181/181 commands)
- [ ] 90%+ integration test coverage for player workflows

### Parity Verification
- [ ] All ROM combat formulas match exactly
- [ ] All ROM spell effects match exactly
- [ ] All ROM skill checks match exactly
- [ ] Save files compatible with ROM C (bidirectional)
- [ ] Player experience identical to ROM C

### Quality Gates
- [ ] All tests pass before merge
- [ ] No test marked as `@pytest.mark.skip` in main branch
- [ ] All test failures investigated and documented
- [ ] Integration tests run on every commit

---

## Risk Management

### High-Risk Areas
1. **Combat calculations** - Complex formulas, many edge cases
2. **Mob programs** - Conditional logic, state management
3. **Magic system** - 100+ spells with unique effects
4. **Save/load** - Data integrity critical

### Mitigation Strategies
1. Differential testing against ROM C binary
2. Property-based testing for formulas
3. Extensive logging of calculations
4. Automated regression testing

---

## References

- **ROM C Source:** `src/` directory (original ROM 2.4b6 C code)
- **Character Tests:** [CHARACTER_TEST_PLAN.md](CHARACTER_TEST_PLAN.md)
- **Common Pitfalls:** [COMMON_PITFALLS.md](COMMON_PITFALLS.md)
- **ROM Documentation:** `doc/` directory
- **ROM C Functions:** [FUNCTION_MAPPING.md](FUNCTION_MAPPING.md)

---

**Last Updated:** December 27, 2025  
**Current Phase:** Phase 1 - Foundation (Character Tests)  
**Next Milestone:** Complete Priority 1 character tests (75 tests)
