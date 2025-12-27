# Mob Parity Test Plan

**Purpose**: Comprehensive testing strategy for ROM 2.4b mob behavior parity  
**Status**: Planning Document  
**Created**: 2025-12-26  
**Priority**: Medium (foundational for complete ROM parity)

---

## 🎯 Executive Summary

While MobProgs have achieved 100% parity, **mob AI behaviors, special procedures, and ACT flags** need comprehensive testing. This document outlines 6 major test areas covering 100+ individual mob behaviors.

**Test Coverage Goals**:
- 22 spec_fun behaviors (guards, janitors, breath weapons, casters)
- 30+ ACT flag behaviors (aggressive, wimpy, scavenger, sentinel)
- Damage modifiers (immunities, resistances, vulnerabilities)
- Mob memory and tracking systems
- Group assist mechanics
- Wandering/movement AI

---

## 📊 Current State Assessment

### What's Tested ✅
- MobProgs: 50/50 unit tests passing (100% coverage)
- Basic mob creation and spawning
- Mob combat mechanics (damage, fighting state)
- Basic spec_fun loading and registration

### What's Missing ⚠️
- **Spec function behaviors**: 22 functions, minimal behavior tests
- **ACT flag behaviors**: Flags defined, behaviors untested
- **Damage modifiers**: IMM/RES/VULN defined, not integrated
- **Mob memory**: Partially implemented, not tested
- **Assist mechanics**: Command exists, behavior untested
- **Wandering AI**: Basic wander exists, constraints untested

---

## 🧪 Test Priority Matrix

| Test Area | ROM Lines | Behaviors | Priority | Effort | Player Impact |
|-----------|-----------|-----------|----------|--------|---------------|
| Spec Functions | 1192 | 22 | **P0** | High | Critical |
| ACT Flags | 500+ | 30+ | **P1** | Medium | High |
| Damage Modifiers | 200+ | 15+ | **P1** | Low | High |
| Mob Memory | 150+ | 4 | **P2** | Medium | Medium |
| Assist Mechanics | 100+ | 3 | **P2** | Low | Low |
| Wandering AI | 80+ | 5 | **P3** | Low | Low |

---

## 📋 Detailed Test Plans

### P0: Special Procedures (spec_funs) - CRITICAL

**ROM Reference**: `src/special.c` (1192 lines)  
**Python**: `mud/spec_funs.py`  
**Current Tests**: `tests/test_spec_funs.py` (basic registration only)

#### Guard/Law Enforcement (High Impact)

**spec_guard** - Guards attack criminals
```python
# tests/test_spec_fun_behaviors.py

def test_spec_guard_attacks_criminal_in_room():
    """Guard should auto-attack characters with KILLER flag."""
    # ROM C: special.c:567-623
    guard = create_mob_with_spec("spec_guard")
    criminal = create_player()
    criminal.act = PLR_KILLER
    
    # Guard should initiate combat
    run_npc_specs()
    assert guard.fighting == criminal

def test_spec_guard_ignores_innocent_players():
    """Guard should not attack non-criminals."""
    guard = create_mob_with_spec("spec_guard")
    innocent = create_player()
    
    run_npc_specs()
    assert guard.fighting is None

def test_spec_guard_yells_warning():
    """Guard should yell 'PROTECT! PROTECT!' before attacking."""
    guard = create_mob_with_spec("spec_guard")
    criminal = create_player()
    criminal.act = PLR_KILLER
    
    with capture_output() as output:
        run_npc_specs()
    
    assert "PROTECT! PROTECT!" in output
```

**spec_executioner** - Hunts criminals across rooms
```python
def test_spec_executioner_hunts_criminals():
    """Executioner should track down KILLER/THIEF flagged chars."""
    # ROM C: special.c:624-680
    executioner = create_mob_with_spec("spec_executioner")
    criminal = create_player()
    criminal.act = PLR_KILLER
    place_in_adjacent_room(criminal)
    
    run_npc_specs()
    # Should move toward criminal
    assert executioner.room == criminal.room

def test_spec_executioner_yells_before_hunting():
    """Executioner yells before hunting."""
    executioner = create_mob_with_spec("spec_executioner")
    criminal = create_player()
    criminal.act = PLR_THIEF
    
    with capture_output() as output:
        run_npc_specs()
    
    assert "CRIMINAL! CRIMINAL!" in output
```

**spec_patrolman** - City patrol enforcement
```python
def test_spec_patrolman_arrests_criminals():
    """Patrolman arrests KILLER/THIEF in city areas."""
    # ROM C: special.c:1134-1192
    patrolman = create_mob_with_spec("spec_patrolman")
    criminal = create_player()
    criminal.act = PLR_THIEF
    
    run_npc_specs()
    assert patrolman.fighting == criminal
    assert "CRIMINAL! CRIMINAL!" in room_output
```

#### Scavenger Behaviors (Medium Impact)

**spec_janitor** - Cleans up trash
```python
def test_spec_janitor_picks_up_trash():
    """Janitor picks up trash-flagged items."""
    # ROM C: special.c:781-817
    janitor = create_mob_with_spec("spec_janitor")
    trash = create_object(item_type=ITEM_TRASH)
    room.add_object(trash)
    
    run_npc_specs()
    assert trash in janitor.inventory
    assert trash not in room.contents

def test_spec_janitor_ignores_non_trash():
    """Janitor only picks up trash items."""
    janitor = create_mob_with_spec("spec_janitor")
    sword = create_object(item_type=ITEM_WEAPON)
    
    run_npc_specs()
    assert sword not in janitor.inventory
```

**spec_fido** - Eats corpses
```python
def test_spec_fido_eats_corpses():
    """Fido (dog) eats PC corpses in room."""
    # ROM C: special.c:681-720
    fido = create_mob_with_spec("spec_fido")
    corpse = create_corpse(is_pc=True)
    room.add_object(corpse)
    
    run_npc_specs()
    assert corpse not in room.contents
    assert "fido" in room_output.lower()  # Eating message

def test_spec_fido_ignores_npc_corpses():
    """Fido only eats PC corpses, not NPC corpses."""
    fido = create_mob_with_spec("spec_fido")
    npc_corpse = create_corpse(is_pc=False)
    
    run_npc_specs()
    assert npc_corpse in room.contents  # Not eaten
```

#### Combat Specialists (High Impact)

**spec_poison** - Poison attacker
```python
def test_spec_poison_applies_poison_in_combat():
    """Poison mob applies poison affect to attacker."""
    # ROM C: special.c:914-951
    poison_mob = create_mob_with_spec("spec_poison")
    attacker = create_player()
    poison_mob.fighting = attacker
    
    run_npc_specs()
    assert has_affect(attacker, "poison")

def test_spec_poison_only_works_in_combat():
    """Poison spec only triggers when fighting."""
    poison_mob = create_mob_with_spec("spec_poison")
    nearby_player = create_player()
    
    run_npc_specs()
    assert not has_affect(nearby_player, "poison")
```

**spec_thief** - Steals from players
```python
def test_spec_thief_steals_gold():
    """Thief steals gold from players in room."""
    # ROM C: special.c:952-1018
    thief = create_mob_with_spec("spec_thief")
    victim = create_player()
    victim.gold = 1000
    
    run_npc_specs()
    assert victim.gold < 1000
    assert thief.gold > 0

def test_spec_thief_percentage_stolen():
    """Thief steals percentage of victim's gold."""
    thief = create_mob_with_spec("spec_thief")
    victim = create_player()
    victim.gold = 10000
    
    run_npc_specs()
    # ROM steals 1/2 to 3/4 of gold
    assert 2500 <= (10000 - victim.gold) <= 7500
```

#### Dragon Breath Weapons (High Impact)

**spec_breath_fire/acid/frost/gas/lightning/any** - Breath attacks
```python
def test_spec_breath_fire_damages_room():
    """Fire-breathing dragon damages all in room."""
    # ROM C: special.c:311-376
    dragon = create_mob_with_spec("spec_breath_fire", level=50)
    victim1 = create_player(hp=200)
    victim2 = create_player(hp=200)
    
    run_npc_specs()
    
    assert victim1.hit < 200  # Fire damage
    assert victim2.hit < 200  # Hits all in room
    assert "fire" in room_output.lower()

def test_spec_breath_any_uses_random_type():
    """spec_breath_any randomly chooses breath type."""
    # ROM C: special.c:269-310
    dragon = create_mob_with_spec("spec_breath_any")
    
    breath_types_seen = set()
    for _ in range(50):  # Run multiple times
        run_npc_specs()
    
    # Should use different breath types
    assert len(breath_types_seen) > 1

def test_spec_breath_respects_immunity():
    """Breath attacks respect damage immunities."""
    dragon = create_mob_with_spec("spec_breath_fire")
    immune_player = create_player()
    immune_player.imm_flags = IMM_FIRE
    
    run_npc_specs()
    assert immune_player.hit == immune_player.max_hit  # No damage
```

#### Caster AI (High Impact)

**spec_cast_cleric** - Cleric spell AI
```python
def test_spec_cast_cleric_heals_self():
    """Cleric casts heal when injured."""
    # ROM C: special.c:377-429
    cleric = create_mob_with_spec("spec_cast_cleric", level=20)
    cleric.hit = cleric.max_hit // 2  # 50% HP
    
    run_npc_specs()
    assert cleric.hit > (cleric.max_hit // 2)  # Healed

def test_spec_cast_cleric_casts_offensive_spells():
    """Cleric casts offensive spells in combat."""
    cleric = create_mob_with_spec("spec_cast_cleric")
    victim = create_player()
    cleric.fighting = victim
    
    run_npc_specs()
    # Should cast harm, dispel evil, or curse
    assert victim.hit < victim.max_hit or has_affect(victim, "curse")

def test_spec_cast_cleric_conserves_mana():
    """Cleric doesn't cast when low on mana."""
    cleric = create_mob_with_spec("spec_cast_cleric")
    cleric.mana = 10  # Very low mana
    cleric.fighting = create_player()
    
    run_npc_specs()
    assert cleric.mana >= 0  # Didn't go negative
```

**spec_cast_mage** - Mage spell AI
```python
def test_spec_cast_mage_offensive_spells():
    """Mage casts offensive spells in combat."""
    # ROM C: special.c:464-513
    mage = create_mob_with_spec("spec_cast_mage")
    victim = create_player()
    mage.fighting = victim
    
    run_npc_specs()
    # Should cast fireball, lightning bolt, etc.
    assert victim.hit < victim.max_hit

def test_spec_cast_mage_defensive_spells():
    """Mage casts shields when not in combat."""
    mage = create_mob_with_spec("spec_cast_mage")
    mage.mana = 500  # Plenty of mana
    
    run_npc_specs()
    # Should cast armor, shield, stone skin
    assert has_affect(mage, "armor") or has_affect(mage, "shield")
```

**spec_cast_undead** - Undead caster AI
```python
def test_spec_cast_undead_energy_drain():
    """Undead casters use energy drain."""
    # ROM C: special.c:514-566
    undead = create_mob_with_spec("spec_cast_undead")
    victim = create_player(level=10)
    undead.fighting = victim
    
    run_npc_specs()
    # Energy drain should reduce victim stats
    assert victim.hit < victim.max_hit
```

**spec_cast_judge** - Judge/justiciar AI
```python
def test_spec_cast_judge_high_damage():
    """Judge casts high damage spells."""
    # ROM C: special.c:430-463
    judge = create_mob_with_spec("spec_cast_judge", level=50)
    victim = create_player(hp=500)
    judge.fighting = victim
    
    run_npc_specs()
    # Judge uses high damage/slay
    damage = 500 - victim.hit
    assert damage > 100  # Significant damage
```

#### Social/Quest NPCs (Medium Impact)

**spec_mayor** - Mayor speeches
```python
def test_spec_mayor_gives_speeches():
    """Mayor gives timed speeches."""
    # ROM C: special.c:818-913
    mayor = create_mob_with_spec("spec_mayor")
    
    # Advance time to speech time
    game_time.hour = 12  # Noon
    
    run_npc_specs()
    assert "Citizens" in room_output  # Speech text
```

**spec_cast_adept** - Practice/healing adept
```python
def test_spec_cast_adept_heals_visitors():
    """Adept heals players who enter."""
    # ROM C: special.c:159-208
    adept = create_mob_with_spec("spec_cast_adept")
    injured_player = create_player(hp=50, max_hp=200)
    
    run_npc_specs()
    assert injured_player.hit > 50  # Healed
```

#### Faction/Guild Specialists (Low Impact)

**spec_troll_member** - Troll faction AI
```python
def test_spec_troll_member_assists_trolls():
    """Troll assists other trolls in combat."""
    # ROM C: special.c:1019-1074
    troll1 = create_mob_with_spec("spec_troll_member")
    troll2 = create_mob(race="troll")
    enemy = create_player()
    troll2.fighting = enemy
    
    run_npc_specs()
    assert troll1.fighting == enemy  # Assisted
```

**spec_ogre_member** - Ogre faction AI
```python
def test_spec_ogre_member_assists_ogres():
    """Ogre assists other ogres in combat."""
    # ROM C: special.c:1075-1133
    ogre1 = create_mob_with_spec("spec_ogre_member")
    ogre2 = create_mob(race="ogre")
    enemy = create_player()
    ogre2.fighting = enemy
    
    run_npc_specs()
    assert ogre1.fighting == enemy
```

**spec_nasty** - Random nasty behavior
```python
def test_spec_nasty_random_aggression():
    """Nasty mob randomly attacks or steals."""
    # ROM C: special.c:1019-1074 (shares with troll)
    nasty = create_mob_with_spec("spec_nasty")
    victim = create_player()
    
    behaviors_seen = set()
    for _ in range(20):
        run_npc_specs()
        if nasty.fighting:
            behaviors_seen.add("attack")
        if victim.gold < 100:
            behaviors_seen.add("steal")
    
    assert len(behaviors_seen) > 0  # Some behavior triggered
```

---

### P1: ACT Flag Behaviors

**ROM Reference**: `src/const.c` (act_flags table), `src/update.c` (mobile_update)  
**Python**: `mud/models/constants.py`, `mud/update.py`  
**Current Tests**: None

#### Combat ACT Flags

**ACT_AGGRESSIVE** - Auto-attack players
```python
# tests/test_mob_act_flags.py

def test_aggressive_mob_auto_attacks_players():
    """ACT_AGGRESSIVE mobs attack players on sight."""
    # ROM C: update.c:429-502
    aggro_mob = create_mob()
    aggro_mob.act = ACT_AGGRESSIVE
    player = create_player()
    
    mobile_update()
    assert aggro_mob.fighting == player

def test_aggressive_mob_ignores_other_mobs():
    """ACT_AGGRESSIVE only attacks players, not NPCs."""
    aggro_mob = create_mob()
    aggro_mob.act = ACT_AGGRESSIVE
    other_mob = create_mob()
    
    mobile_update()
    assert aggro_mob.fighting is None

def test_aggressive_mob_respects_level():
    """ACT_AGGRESSIVE doesn't attack high-level players."""
    aggro_mob = create_mob(level=10)
    aggro_mob.act = ACT_AGGRESSIVE
    high_level_player = create_player(level=50)
    
    mobile_update()
    assert aggro_mob.fighting is None  # Too scared
```

**ACT_WIMPY** - Flee at low HP
```python
def test_wimpy_mob_flees_low_hp():
    """ACT_WIMPY mobs flee when HP drops below 20%."""
    # ROM C: fight.c:1094-1136
    wimpy_mob = create_mob(hp=100, max_hp=100)
    wimpy_mob.act = ACT_WIMPY
    attacker = create_player()
    wimpy_mob.fighting = attacker
    
    # Damage to 15% HP
    wimpy_mob.hit = 15
    
    mobile_update()
    assert wimpy_mob.room != attacker.room  # Fled

def test_wimpy_mob_doesnt_flee_high_hp():
    """ACT_WIMPY mobs fight normally when healthy."""
    wimpy_mob = create_mob(hp=80, max_hp=100)
    wimpy_mob.act = ACT_WIMPY
    wimpy_mob.fighting = create_player()
    
    mobile_update()
    assert wimpy_mob.fighting is not None  # Still fighting
```

**ACT_SENTINEL** - Never leaves room
```python
def test_sentinel_mob_never_wanders():
    """ACT_SENTINEL mobs stay in their room."""
    sentinel = create_mob()
    sentinel.act = ACT_SENTINEL
    original_room = sentinel.room
    
    for _ in range(50):  # Many update ticks
        mobile_update()
    
    assert sentinel.room == original_room

def test_sentinel_mob_can_be_forced_to_move():
    """ACT_SENTINEL doesn't prevent forced movement."""
    sentinel = create_mob()
    sentinel.act = ACT_SENTINEL
    new_room = create_room()
    
    transfer_mob(sentinel, new_room)
    assert sentinel.room == new_room
```

#### Scavenger ACT Flags

**ACT_SCAVENGER** - Picks up items
```python
def test_scavenger_picks_up_items():
    """ACT_SCAVENGER mobs pick up valuable items."""
    # ROM C: update.c:429-502
    scavenger = create_mob()
    scavenger.act = ACT_SCAVENGER
    gold_pile = create_object(item_type=ITEM_MONEY, value=100)
    room.add_object(gold_pile)
    
    mobile_update()
    assert gold_pile in scavenger.inventory

def test_scavenger_prefers_valuable_items():
    """ACT_SCAVENGER picks up most valuable items first."""
    scavenger = create_mob()
    scavenger.act = ACT_SCAVENGER
    cheap_item = create_object(value=10)
    expensive_item = create_object(value=1000)
    
    mobile_update()
    assert expensive_item in scavenger.inventory
```

#### Class/Role ACT Flags

**ACT_CLERIC/MAGE/THIEF/WARRIOR** - Class-based AI
```python
def test_act_cleric_casts_heals():
    """ACT_CLERIC mobs cast healing spells."""
    cleric = create_mob()
    cleric.act = ACT_CLERIC
    cleric.hit = cleric.max_hit // 2
    
    mobile_update()
    assert cleric.hit > (cleric.max_hit // 2)  # Self-healed

def test_act_mage_casts_offensive():
    """ACT_MAGE mobs cast offensive spells."""
    mage = create_mob()
    mage.act = ACT_MAGE
    victim = create_player()
    mage.fighting = victim
    
    mobile_update()
    assert victim.hit < victim.max_hit  # Spell damage

def test_act_thief_backstabs():
    """ACT_THIEF mobs attempt backstab."""
    thief = create_mob()
    thief.act = ACT_THIEF
    victim = create_player()
    
    mobile_update()
    # Check for backstab attempt
    assert thief.fighting == victim
```

#### Special ACT Flags

**ACT_UNDEAD** - Undead interactions
```python
def test_undead_affected_by_holy_water():
    """ACT_UNDEAD takes extra damage from holy attacks."""
    undead = create_mob()
    undead.act = ACT_UNDEAD
    
    damage = calculate_damage(attacker, undead, damage_type=DAM_HOLY)
    assert damage > calculate_damage(attacker, undead, damage_type=DAM_BASH)

def test_undead_turned_by_clerics():
    """ACT_UNDEAD can be turned by clerics."""
    undead = create_mob()
    undead.act = ACT_UNDEAD
    cleric = create_player()
    
    cast_spell(cleric, "turn undead", target=undead)
    assert undead.fighting is None  # Fled or cowering
```

**ACT_PRACTICE** - Trains skills
```python
def test_practice_mob_trains_skills():
    """ACT_PRACTICE mobs can train player skills."""
    trainer = create_mob()
    trainer.act = ACT_PRACTICE
    player = create_player()
    
    result = do_practice(player, "kick")
    assert "You practice" in result
    assert player.pcdata.learned["kick"] > 0
```

**ACT_IS_HEALER** - Healer services
```python
def test_healer_mob_heals_for_gold():
    """ACT_IS_HEALER provides healing services."""
    healer = create_mob()
    healer.act = ACT_IS_HEALER
    injured_player = create_player(hp=50, max_hp=200, gold=1000)
    
    result = do_heal(injured_player)
    assert injured_player.hit > 50
    assert injured_player.gold < 1000  # Paid for healing
```

**ACT_GAIN** - Trains stats/skills
```python
def test_gain_mob_trains_stats():
    """ACT_GAIN mobs can train player attributes."""
    trainer = create_mob()
    trainer.act = ACT_GAIN
    player = create_player(str=16, gold=10000)
    
    result = do_train(player, "str")
    assert player.perm_stat[STAT_STR] > 16
```

---

### P1: Damage Modifiers (IMM/RES/VULN)

**ROM Reference**: `src/fight.c` (dam_message, damage calculations)  
**Python**: `mud/combat/engine.py`  
**Current Tests**: None

```python
# tests/test_mob_damage_modifiers.py

def test_immunity_blocks_all_damage():
    """IMM_FIRE mob takes 0 damage from fire."""
    # ROM C: fight.c:197-259
    fire_immune = create_mob()
    fire_immune.imm_flags = IMM_FIRE
    
    damage = calculate_damage(attacker, fire_immune, dam_type=DAM_FIRE, base_dam=100)
    assert damage == 0

def test_resistance_reduces_damage():
    """RES_COLD mob takes reduced damage from cold."""
    cold_resist = create_mob()
    cold_resist.res_flags = RES_COLD
    
    damage = calculate_damage(attacker, cold_resist, dam_type=DAM_COLD, base_dam=100)
    # ROM: resistance = 50% reduction
    assert 45 <= damage <= 55

def test_vulnerability_increases_damage():
    """VULN_LIGHTNING mob takes increased damage from lightning."""
    lightning_vuln = create_mob()
    lightning_vuln.vuln_flags = VULN_LIGHTNING
    
    damage = calculate_damage(attacker, lightning_vuln, dam_type=DAM_LIGHTNING, base_dam=100)
    # ROM: vulnerability = 150% damage
    assert 145 <= damage <= 155

def test_multiple_damage_types_stack():
    """Multiple IMM/RES/VULN flags work together."""
    complex_mob = create_mob()
    complex_mob.imm_flags = IMM_FIRE
    complex_mob.res_flags = RES_COLD
    complex_mob.vuln_flags = VULN_LIGHTNING
    
    fire_dam = calculate_damage(attacker, complex_mob, dam_type=DAM_FIRE, base_dam=100)
    cold_dam = calculate_damage(attacker, complex_mob, dam_type=DAM_COLD, base_dam=100)
    lightning_dam = calculate_damage(attacker, complex_mob, dam_type=DAM_LIGHTNING, base_dam=100)
    
    assert fire_dam == 0
    assert cold_dam < 100
    assert lightning_dam > 100

def test_damage_message_reflects_modifier():
    """Damage messages show immunity/resistance."""
    immune_mob = create_mob()
    immune_mob.imm_flags = IMM_BASH
    
    message = dam_message(attacker, immune_mob, damage=0, dam_type=DAM_BASH)
    assert "immune" in message.lower() or "unaffected" in message.lower()
```

---

### P2: Mob Memory & Tracking

**ROM Reference**: `src/update.c` (mobile_update), `src/act_info.c` (memory handling)  
**Python**: `mud/update.py`, `mud/models/character.py`  
**Current Tests**: None

```python
# tests/test_mob_memory.py

def test_mob_remembers_attacker():
    """Mob remembers who attacked it."""
    # ROM C: update.c memory handling
    mob = create_mob()
    attacker = create_player(name="BadGuy")
    
    mob.fighting = attacker
    mobile_update()  # Process memory
    
    assert "BadGuy" in mob.memory

def test_mob_hunts_remembered_enemy():
    """Mob seeks out remembered attackers."""
    mob = create_mob()
    mob.memory = ["BadGuy"]
    enemy = create_player(name="BadGuy")
    place_in_adjacent_room(enemy)
    
    for _ in range(10):  # Should eventually find
        mobile_update()
        if mob.room == enemy.room:
            break
    
    assert mob.room == enemy.room
    assert mob.fighting == enemy

def test_mob_forgets_after_timeout():
    """Mob memory fades after time."""
    mob = create_mob()
    mob.memory = ["BadGuy"]
    
    # Advance game time significantly
    for _ in range(1000):
        mobile_update()
    
    assert "BadGuy" not in mob.memory

def test_mob_memory_persists_across_rooms():
    """Mob remembers enemies even when separated."""
    mob = create_mob()
    enemy = create_player(name="BadGuy")
    
    mob.fighting = enemy
    mobile_update()
    
    # Separate them
    transfer_char(enemy, other_room)
    assert "BadGuy" in mob.memory
```

---

### P2: Assist Mechanics

**ROM Reference**: `src/fight.c` (check_assist), `src/update.c`  
**Python**: `mud/mob_cmds.py` (do_mpassist)  
**Current Tests**: None

```python
# tests/test_mob_assist.py

def test_mob_assists_same_vnum():
    """Mobs assist other mobs of the same vnum."""
    # ROM C: fight.c check_assist
    mob1 = create_mob(vnum=1000)
    mob2 = create_mob(vnum=1000)
    enemy = create_player()
    mob1.fighting = enemy
    
    check_assist(mob2)
    assert mob2.fighting == enemy

def test_mob_assists_group_member():
    """Mobs assist their group members."""
    mob1 = create_mob()
    mob2 = create_mob()
    mob1.leader = mob2  # Grouped
    enemy = create_player()
    mob2.fighting = enemy
    
    check_assist(mob1)
    assert mob1.fighting == enemy

def test_auto_assist_chain_reaction():
    """Multiple mobs assist in chain reaction."""
    mob1 = create_mob(vnum=1000)
    mob2 = create_mob(vnum=1000)
    mob3 = create_mob(vnum=1000)
    enemy = create_player()
    
    mob1.fighting = enemy
    mobile_update()
    
    # All should join fight
    assert mob2.fighting == enemy
    assert mob3.fighting == enemy

def test_assist_respects_distance():
    """Mobs only assist if in same room."""
    mob1 = create_mob(vnum=1000)
    mob2 = create_mob(vnum=1000)
    place_in_different_room(mob2)
    
    mob1.fighting = create_player()
    check_assist(mob2)
    
    assert mob2.fighting is None  # Too far
```

---

### P3: Wandering/Movement AI

**ROM Reference**: `src/update.c` (mobile_update wander section)  
**Python**: `mud/update.py`  
**Current Tests**: Basic wander exists

```python
# tests/test_mob_wandering.py

def test_mob_wanders_randomly():
    """Mobs without ACT_SENTINEL wander randomly."""
    # ROM C: update.c:429-502
    wanderer = create_mob()
    original_room = wanderer.room
    
    rooms_visited = set([original_room])
    for _ in range(100):
        mobile_update()
        rooms_visited.add(wanderer.room)
    
    assert len(rooms_visited) > 1  # Moved around

def test_sentinel_mob_never_wanders():
    """ACT_SENTINEL mobs stay put."""
    sentinel = create_mob()
    sentinel.act = ACT_SENTINEL
    original_room = sentinel.room
    
    for _ in range(100):
        mobile_update()
    
    assert sentinel.room == original_room

def test_mob_opens_doors_when_wandering():
    """Mobs open unlocked doors to wander."""
    wanderer = create_mob()
    create_door(wanderer.room, direction=DIR_NORTH, closed=True, locked=False)
    
    for _ in range(50):
        mobile_update()
        if wanderer.room != original_room:
            break
    
    assert wanderer.room != original_room  # Opened door

def test_mob_avoids_impassable_terrain():
    """Mobs don't wander into death traps or water (non-swimmers)."""
    wanderer = create_mob()
    wanderer.act = 0  # No special flags
    
    create_death_trap_room(direction=DIR_NORTH)
    
    for _ in range(100):
        mobile_update()
    
    assert wanderer.position == POS_STANDING  # Still alive

def test_wander_frequency_based_on_level():
    """Higher level mobs wander less frequently."""
    low_level = create_mob(level=1)
    high_level = create_mob(level=50)
    
    low_moves = count_moves(low_level, ticks=100)
    high_moves = count_moves(high_level, ticks=100)
    
    # ROM: higher level = less wandering
    assert low_moves > high_moves
```

---

## 🎯 Implementation Roadmap

### Phase 1: Critical Gameplay (P0) - 2-3 days
1. ✅ Create `tests/test_spec_fun_behaviors.py`
2. Implement 22 spec_fun behavior tests
3. Fix any discovered spec_fun bugs
4. Verify all spec_funs match ROM C behavior

### Phase 2: Core Behaviors (P1) - 2-3 days
1. ✅ Create `tests/test_mob_act_flags.py`
2. Implement ACT flag behavior tests (aggressive, wimpy, sentinel, etc.)
3. ✅ Create `tests/test_mob_damage_modifiers.py`
4. Implement IMM/RES/VULN integration tests
5. Fix damage calculation integration

### Phase 3: Advanced AI (P2) - 1-2 days
1. ✅ Create `tests/test_mob_memory.py`
2. Implement memory/tracking tests
3. ✅ Create `tests/test_mob_assist.py`
4. Implement assist mechanic tests

### Phase 4: Polish (P3) - 1 day
1. ✅ Create `tests/test_mob_wandering.py`
2. Implement wandering constraint tests
3. Create integration test suite

---

## 📊 Success Metrics

**Test Coverage Goals**:
- [ ] 22/22 spec_fun behaviors tested
- [ ] 15/30+ ACT flags tested (core flags)
- [ ] 15/15 damage modifiers tested
- [ ] 4/4 memory behaviors tested
- [ ] 3/3 assist behaviors tested
- [ ] 5/5 wandering constraints tested

**ROM Parity Verification**:
- [ ] All spec_fun behaviors match ROM C output
- [ ] ACT flag timing/frequency matches ROM C
- [ ] Damage modifier calculations exact match
- [ ] Memory persistence matches ROM C

**Acceptance Criteria**:
- [ ] 100+ new mob behavior tests created
- [ ] All tests passing with no regressions
- [ ] Differential testing vs ROM C (where possible)
- [ ] Documentation updated with test results

---

## 🔗 Related Documents

- [MOBPROG_TESTING_GUIDE.md](MOBPROG_TESTING_GUIDE.md) - MobProg testing methodology
- [ROM_PARITY_FEATURE_TRACKER.md](../parity/ROM_PARITY_FEATURE_TRACKER.md) - Overall parity status
- [PROJECT_COMPLETION_STATUS.md](../../PROJECT_COMPLETION_STATUS.md) - Subsystem confidence

---

## 📝 Notes

**Why This Matters**:
- Spec_funs create unique mob personalities (guards, dragons, thieves)
- ACT flags drive autonomous mob behavior (aggression, fleeing, scavenging)
- These systems make the world feel alive and reactive
- Direct impact on player experience and world immersion

**ROM C Compliance**:
- All tests should reference specific ROM C source locations
- Use differential testing where possible
- Document any intentional deviations from ROM C behavior

**Test Maintenance**:
- Run full mob test suite after any mob-related changes
- Update tests when ROM C reference behavior changes
- Keep ROM C source comments in tests for traceability

---

**Last Updated**: 2025-12-26  
**Next Review**: After Phase 1 completion
