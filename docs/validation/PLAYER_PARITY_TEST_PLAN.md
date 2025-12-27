/# Player/Character Parity Test Plan

**Purpose**: Comprehensive testing strategy for ROM 2.4b player-specific behavior parity  
**Status**: Planning Document - Research Phase Complete  
**Created**: 2025-12-26  
**Priority**: High (foundational for player experience)

---

## 🎯 Executive Summary

While **character creation** and **basic player mechanics** are well-tested, many **player-specific commands, state management, and quality-of-life features** lack comprehensive parity testing. This document identifies **8 major test areas** with **80+ specific behaviors** that need validation.

**Critical Finding**: Character/Player tests focus heavily on **creation workflow** but lack coverage for:
- Player information display commands (score, worth, whois)
- Player state management (wimpy, conditions, prompt)
- Player flags and reputation system (KILLER, THIEF, trust)
- Auto-settings and configuration
- Player-specific restrictions and permissions

---

## 📊 Current State Assessment

### What's Tested ✅
- **Character Creation**: 15+ tests for race/class/stats/skills/equipment
- **Authentication**: Login/logout, password, character selection
- **Basic Movement**: Follow, charm restrictions
- **Combat Death**: PK flags, corpse handling
- **Persistence**: Save/load character data

### What's Missing ⚠️
- **Information Commands**: score, worth, whois output format
- **Player Configuration**: wimpy, autoassist, autoloot, etc.
- **Conditions System**: Hunger, thirst, drunk effects
- **Prompt Customization**: Prompt parsing and substitution
- **Player Flags**: KILLER/THIEF flag application and decay
- **Trust/Security**: Trust levels, freeze, permission checks
- **Title/Description**: Player title and description management
- **Player Visibility**: AFK, wizinvis, incognito states

---

## 🧪 Test Priority Matrix

| Test Area | ROM Lines | Behaviors | Priority | Effort | Player Impact |
|-----------|-----------|-----------|----------|--------|---------------|
| Information Display | 500+ | 12 | **P0** | Low | Critical |
| Auto-Settings | 300+ | 15 | **P0** | Low | High |
| Conditions System | 200+ | 8 | **P1** | Medium | High |
| Player Flags/Reputation | 250+ | 10 | **P1** | Medium | High |
| Prompt Customization | 150+ | 6 | **P2** | Low | Medium |
| Title/Description | 200+ | 8 | **P2** | Low | Medium |
| Trust/Security | 300+ | 12 | **P2** | Medium | Medium |
| Player Visibility | 200+ | 10 | **P3** | Low | Low |

---

## 📋 Detailed Test Plans

### P0: Information Display Commands - CRITICAL

**ROM Reference**: `src/act_info.c` (2945 lines)  
**Python**: `mud/commands/session.py`, `mud/commands/info_extended.py`  
**Current Tests**: None

#### do_score - Character Statistics Display

**ROM C**: `act_info.c:1477-1632`

```python
# tests/test_player_info_commands.py

def test_score_displays_basic_stats():
    """Score shows name, level, class, race, hp/mana/mv."""
    # ROM C: act_info.c:1477-1632
    player = create_player(
        name="TestPlayer",
        level=10,
        char_class="warrior",
        race="human",
        hp=200, max_hp=250,
        mana=100, max_mana=150,
        move=300, max_move=350
    )
    
    output = do_score(player, "")
    
    assert "TestPlayer" in output
    assert "level 10" in output.lower()
    assert "warrior" in output.lower()
    assert "200/250 hp" in output or "200(250)" in output
    assert "100/150 mana" in output or "100(150)" in output
    assert "300/350 mv" in output or "300(350)" in output

def test_score_shows_alignment_and_hours():
    """Score displays alignment and play time."""
    player = create_player(alignment=750, played_hours=48)
    
    output = do_score(player, "")
    
    # ROM alignment descriptions
    assert ("angelic" in output.lower() or 
            "saintly" in output.lower() or
            "good" in output.lower())
    assert "48" in output  # Hours played

def test_score_shows_armor_class():
    """Score displays AC (armor class) breakdown."""
    # ROM C: Shows AC vs pierce/bash/slash/magic
    player = create_player()
    player.armor[AC_PIERCE] = 50
    player.armor[AC_BASH] = 60
    player.armor[AC_SLASH] = 55
    player.armor[AC_EXOTIC] = 45
    
    output = do_score(player, "")
    
    assert "armor" in output.lower() or "ac" in output.lower()
    # ROM shows: Armor: pierce: 50  bash: 60  slash: 55  magic: 45

def test_score_shows_hitroll_damroll():
    """Score displays to-hit and damage bonuses."""
    player = create_player(hitroll=15, damroll=12)
    
    output = do_score(player, "")
    
    assert ("hit" in output.lower() and "15" in output) or "hitroll" in output.lower()
    assert ("dam" in output.lower() and "12" in output) or "damroll" in output.lower()

def test_score_shows_wimpy_setting():
    """Score displays wimpy flee threshold."""
    player = create_player()
    player.wimpy = 50
    
    output = do_score(player, "")
    
    assert "wimpy" in output.lower()
    assert "50" in output

def test_score_shows_exp_and_tnl():
    """Score shows experience points and TNL (to next level)."""
    player = create_player(level=10, exp=45000)
    
    output = do_score(player, "")
    
    assert "45000" in output or "45,000" in output  # Experience
    # ROM shows "Exp: 45000  Exp to level: 5000"

def test_score_shows_gold_silver():
    """Score displays gold and silver separately."""
    # ROM C: Shows gold and silver as separate currencies
    player = create_player(gold=500, silver=75)
    
    output = do_score(player, "")
    
    assert "500" in output and "gold" in output.lower()
    assert "75" in output and "silver" in output.lower()

def test_score_shows_encumbrance():
    """Score displays carry weight and max capacity."""
    player = create_player()
    player.carry_weight = 150
    player.carry_number = 12
    max_carry = player.max_carry_weight()
    
    output = do_score(player, "")
    
    assert "150" in output  # Current weight
    assert "12" in output   # Item count

def test_score_shows_practice_trains():
    """Score displays practice sessions and training points."""
    player = create_player()
    player.pcdata.practice = 8
    player.pcdata.train = 3
    
    output = do_score(player, "")
    
    assert ("practice" in output.lower() and "8" in output)
    assert ("train" in output.lower() and "3" in output)

def test_score_shows_age():
    """Score shows character age in years."""
    player = create_player()
    # ROM calculates age based on creation time + race aging
    
    output = do_score(player, "")
    
    assert "age" in output.lower() or "years old" in output.lower()

def test_score_with_affects_flag():
    """Score shows affects when COMM_SHOW_AFFECTS is set."""
    # ROM C: Shows active affects in score if flag set
    player = create_player()
    player.comm = COMM_SHOW_AFFECTS
    add_affect(player, "sanctuary", duration=5)
    add_affect(player, "armor", duration=10)
    
    output = do_score(player, "")
    
    assert "sanctuary" in output.lower()
    assert "armor" in output.lower()
```

#### do_worth - Wealth and Possessions

**ROM C**: `act_info.c:1453-1475`

```python
def test_worth_shows_gold_silver():
    """Worth command displays gold and silver totals."""
    # ROM C: act_info.c:1453-1475
    player = create_player(gold=12500, silver=350)
    
    output = do_worth(player, "")
    
    assert "12500" in output or "12,500" in output
    assert "gold" in output.lower()
    assert "350" in output
    assert "silver" in output.lower()

def test_worth_shows_bank_balance():
    """Worth shows banked gold if banking system exists."""
    player = create_player(gold=5000)
    player.pcdata.bank_gold = 50000
    
    output = do_worth(player, "")
    
    assert "50000" in output or "50,000" in output
    assert "bank" in output.lower()
```

#### do_whois - Player Information Lookup

**ROM C**: `act_info.c` (whois command)  
**Python**: `mud/commands/info_extended.py:124-208`

```python
def test_whois_shows_player_info():
    """Whois shows online player's level, class, race, title."""
    # ROM C: Shows detailed player information
    target = create_player(
        name="Gandalf",
        level=50,
        char_class="mage",
        race="elf"
    )
    target.pcdata.title = "the Grey Wizard"
    make_player_visible(target)  # Online
    
    searcher = create_player(name="Frodo")
    output = do_whois(searcher, "Gandalf")
    
    assert "Gandalf" in output
    assert "50" in output  # Level
    assert "mage" in output.lower() or "Mag" in output
    assert "elf" in output.lower()
    assert "Grey Wizard" in output

def test_whois_shows_killer_thief_flags():
    """Whois shows KILLER and THIEF flags."""
    target = create_player(name="Badguy")
    target.act = PLR_KILLER | PLR_THIEF
    
    searcher = create_player(name="Goodguy")
    output = do_whois(searcher, "Badguy")
    
    assert "KILLER" in output
    assert "THIEF" in output

def test_whois_player_not_found():
    """Whois handles non-existent player."""
    searcher = create_player()
    output = do_whois(searcher, "NoSuchPlayer")
    
    assert "not found" in output.lower() or "isn't playing" in output.lower()
```

---

### P0: Auto-Settings and Player Configuration

**ROM Reference**: `src/act_info.c` (autolist, auto* functions)  
**Python**: `mud/commands/auto_settings.py`, `mud/commands/player_config.py`  
**Current Tests**: None

#### Auto-Assist

```python
# tests/test_player_auto_settings.py

def test_autoassist_toggle():
    """Autoassist command toggles PLR_AUTOASSIST flag."""
    # ROM C: act_info.c:1028-1041
    player = create_player()
    assert not (player.act & PLR_AUTOASSIST)
    
    output = do_autoassist(player, "")
    assert player.act & PLR_AUTOASSIST
    assert "assist" in output.lower()
    
    output = do_autoassist(player, "")
    assert not (player.act & PLR_AUTOASSIST)

def test_autoassist_joins_group_combat():
    """Players with autoassist join group member fights."""
    player = create_player()
    player.act = PLR_AUTOASSIST
    group_leader = create_player()
    enemy = create_mob()
    
    player.leader = group_leader
    group_leader.fighting = enemy
    
    # Trigger combat round
    check_assist(player)
    
    assert player.fighting == enemy  # Auto-joined fight
```

#### Auto-Loot/Gold/Sac/Split

```python
def test_autoloot_takes_corpse_items():
    """PLR_AUTOLOOT automatically loots corpses."""
    # ROM C: Player with autoloot gets corpse contents
    player = create_player()
    player.act = PLR_AUTOLOOT
    
    mob = create_mob()
    valuable_item = create_object(value=1000)
    mob.inventory.append(valuable_item)
    
    kill_mob(player, mob)  # Creates corpse
    
    assert valuable_item in player.inventory  # Auto-looted

def test_autogold_takes_corpse_gold():
    """PLR_AUTOGOLD automatically takes gold from corpses."""
    player = create_player(gold=0)
    player.act = PLR_AUTOGOLD
    
    mob = create_mob(gold=500)
    kill_mob(player, mob)
    
    assert player.gold == 500  # Auto-took gold

def test_autosac_sacrifices_corpses():
    """PLR_AUTOSAC automatically sacrifices empty corpses."""
    player = create_player()
    player.act = PLR_AUTOSAC
    
    mob = create_mob()
    kill_mob(player, mob)
    corpse = find_corpse_in_room()
    
    # After auto-loot/gold, corpse should be sacrificed
    assert corpse is None or "corpse" not in room.contents

def test_autosplit_shares_gold_with_group():
    """PLR_AUTOSPLIT divides gold with group members."""
    player = create_player(gold=0)
    player.act = PLR_AUTOSPLIT
    
    ally1 = create_player(gold=0)
    ally2 = create_player(gold=0)
    
    player.leader = player  # Group leader
    ally1.leader = player
    ally2.leader = player
    
    player.gold = 300  # Find 300 gold
    process_autosplit(player)
    
    # Should split 3 ways: 100 each
    assert player.gold == 100
    assert ally1.gold == 100
    assert ally2.gold == 100
```

#### Auto-Exit

```python
def test_autoexit_shows_exits_on_look():
    """PLR_AUTOEXIT automatically shows exits when looking."""
    player = create_player()
    player.act = PLR_AUTOEXIT
    room = create_room_with_exits(north=True, south=True, east=True)
    
    output = do_look(player, "")
    
    # Should include exit list
    assert "north" in output.lower() or "[N]" in output
    assert "south" in output.lower() or "[S]" in output
    assert "east" in output.lower() or "[E]" in output
```

#### Autolist Command

```python
def test_autolist_shows_all_settings():
    """Autolist displays all auto-settings and their status."""
    # ROM C: act_info.c:819-926
    player = create_player()
    player.act = PLR_AUTOASSIST | PLR_AUTOEXIT | PLR_AUTOLOOT
    
    output = do_autolist(player, "")
    
    assert "autoassist" in output.lower()
    assert "autoexit" in output.lower()
    assert "autoloot" in output.lower()
    assert "autogold" in output.lower()
    assert "autosac" in output.lower()
    assert "autosplit" in output.lower()
    # Shows ON/OFF status for each
```

---

### P1: Conditions System (Hunger/Thirst/Drunk/Full)

**ROM Reference**: `src/act_obj.c` (eat/drink functions), `src/update.c` (condition decay)  
**Python**: `mud/commands/consumption.py`, `mud/update.py`  
**Current Tests**: Partial (eat/drink command tests exist)

#### Condition Tracking

```python
# tests/test_player_conditions.py

def test_hunger_decreases_over_time():
    """Hunger condition decreases with game ticks."""
    # ROM C: update.c - gain_condition called periodically
    player = create_player()
    player.pcdata.condition[COND_HUNGER] = 48  # Full
    
    for _ in range(10):  # 10 game ticks
        update_player_conditions(player)
    
    assert player.pcdata.condition[COND_HUNGER] < 48

def test_thirst_decreases_faster_than_hunger():
    """Thirst decreases faster than hunger."""
    # ROM C: Thirst decays at different rate
    player = create_player()
    player.pcdata.condition[COND_HUNGER] = 48
    player.pcdata.condition[COND_THIRST] = 48
    
    for _ in range(5):
        update_player_conditions(player)
    
    hunger_lost = 48 - player.pcdata.condition[COND_HUNGER]
    thirst_lost = 48 - player.pcdata.condition[COND_THIRST]
    
    assert thirst_lost > hunger_lost

def test_drunk_condition_decreases():
    """Drunk condition decreases over time."""
    player = create_player()
    player.pcdata.condition[COND_DRUNK] = 20
    
    for _ in range(10):
        update_player_conditions(player)
    
    assert player.pcdata.condition[COND_DRUNK] < 20

def test_starving_player_takes_damage():
    """Player takes damage when hunger reaches 0."""
    # ROM C: Players at 0 hunger take damage
    player = create_player(hp=100, max_hp=100)
    player.pcdata.condition[COND_HUNGER] = 0
    
    update_player_conditions(player)
    
    assert player.hit < 100  # Took starvation damage

def test_dehydration_damage():
    """Player takes damage when thirst reaches 0."""
    player = create_player(hp=100, max_hp=100)
    player.pcdata.condition[COND_THIRST] = 0
    
    update_player_conditions(player)
    
    assert player.hit < 100  # Took dehydration damage

def test_drunk_affects_combat():
    """High drunk condition affects combat accuracy."""
    # ROM C: Drunk players have penalties
    sober = create_player(pcdata=PlayerData(condition={COND_DRUNK: 0}))
    drunk = create_player(pcdata=PlayerData(condition={COND_DRUNK: 20}))
    
    sober_hitroll = calculate_effective_hitroll(sober)
    drunk_hitroll = calculate_effective_hitroll(drunk)
    
    assert drunk_hitroll < sober_hitroll  # Penalty when drunk
```

#### Eating and Drinking

```python
def test_eating_increases_hunger():
    """Eating food increases hunger condition."""
    # ROM C: act_obj.c:1193-1350 (do_eat)
    player = create_player()
    player.pcdata.condition[COND_HUNGER] = 10  # Hungry
    
    food = create_food_object(nutrition=10)
    do_eat(player, food.name)
    
    assert player.pcdata.condition[COND_HUNGER] > 10

def test_drinking_decreases_thirst():
    """Drinking liquid decreases thirst condition."""
    # ROM C: act_obj.c:1243-1250 (liquid affects)
    player = create_player()
    player.pcdata.condition[COND_THIRST] = 10  # Thirsty
    
    waterskin = create_drink_container(liquid="water", amount=5)
    do_drink(player, waterskin.name)
    
    assert player.pcdata.condition[COND_THIRST] > 10  # Quenched

def test_alcohol_increases_drunk():
    """Drinking alcohol increases drunk condition."""
    player = create_player()
    player.pcdata.condition[COND_DRUNK] = 0
    
    ale = create_drink_container(liquid="ale", amount=10)
    do_drink(player, ale.name)
    
    assert player.pcdata.condition[COND_DRUNK] > 0
```

---

### P1: Player Flags and Reputation System

**ROM Reference**: `src/act_wiz.c` (pardon, flag commands)  
**Python**: `mud/commands/imm_punish.py`  
**Current Tests**: Minimal (kill command tests PLR_KILLER flag)

#### KILLER Flag

```python
# tests/test_player_flags.py

def test_killer_flag_set_on_player_kill():
    """Attacking another player sets PLR_KILLER flag."""
    # ROM C: Players who attack others get KILLER flag
    attacker = create_player(name="BadGuy")
    victim = create_player(name="Innocent")
    
    do_kill(attacker, "Innocent")
    
    assert attacker.act & PLR_KILLER
    assert "KILLER" in visible_flags(attacker)

def test_killer_flag_shown_in_who_list():
    """KILLER flag appears in who list."""
    killer = create_player(name="Murderer")
    killer.act = PLR_KILLER
    
    observer = create_player()
    output = do_who(observer, "")
    
    assert "Murderer" in output
    assert "(KILLER)" in output

def test_killer_flag_prevents_recall():
    """Players with KILLER flag cannot recall."""
    # ROM C: Killers can't recall to safety
    killer = create_player()
    killer.act = PLR_KILLER
    
    output = do_recall(killer, "")
    
    assert "fail" in output.lower() or "cannot" in output.lower()

def test_killer_flag_decays():
    """KILLER flag auto-removes after time period."""
    # ROM C: Killer flag removed after N deaths or time
    killer = create_player()
    killer.act = PLR_KILLER
    
    # Die 5 times or wait timeout
    for _ in range(5):
        kill_player(killer)
    
    assert not (killer.act & PLR_KILLER)  # Flag removed

def test_pardon_removes_killer_flag():
    """Admin 'pardon' command removes KILLER flag."""
    killer = create_player(name="Reformed")
    killer.act = PLR_KILLER
    
    admin = create_immortal()
    do_pardon(admin, "Reformed killer")
    
    assert not (killer.act & PLR_KILLER)
```

#### THIEF Flag

```python
def test_thief_flag_set_on_theft():
    """Stealing from player sets PLR_THIEF flag."""
    thief = create_player(name="Sneaky")
    victim = create_player(name="Mark")
    victim.gold = 1000
    
    do_steal(thief, "gold mark")
    
    assert thief.act & PLR_THIEF

def test_thief_flag_shown_to_players():
    """THIEF flag visible in look/who."""
    thief = create_player(name="Pickpocket")
    thief.act = PLR_THIEF
    
    observer = create_player()
    output = do_look(observer, "Pickpocket")
    
    assert "(THIEF)" in output
```

---

### P2: Prompt Customization

**ROM Reference**: `src/act_info.c:1361-1401` (do_prompt)  
**Python**: `mud/commands/player_config.py`  
**Current Tests**: None

```python
# tests/test_player_prompt.py

def test_prompt_substitution_hp():
    """Prompt %h shows current HP."""
    # ROM C: Prompt codes: %h=hp, %m=mana, %v=moves
    player = create_player(hp=150, max_hp=200)
    player.prompt = "<%hhp>"
    
    prompt_output = build_prompt(player)
    
    assert "150" in prompt_output or "150hp" in prompt_output

def test_prompt_substitution_mana():
    """Prompt %m shows current mana."""
    player = create_player(mana=80, max_mana=100)
    player.prompt = "<%mm>"
    
    output = build_prompt(player)
    
    assert "80" in output

def test_prompt_substitution_moves():
    """Prompt %v shows current movement."""
    player = create_player(move=250, max_move=300)
    player.prompt = "<%vmv>"
    
    output = build_prompt(player)
    
    assert "250" in output

def test_prompt_percentage_codes():
    """Prompt %h/%m/%v show percentages."""
    player = create_player(hp=100, max_hp=200)
    player.prompt = "<%h%>"  # 50%
    
    output = build_prompt(player)
    
    assert "50" in output  # 100/200 = 50%

def test_default_prompt():
    """Empty prompt argument shows default."""
    player = create_player()
    
    do_prompt(player, "")
    
    # ROM default: "<%hhp %mm %vmv> "
    assert player.prompt is not None
```

---

### P2: Title and Description

**ROM Reference**: `src/act_info.c:2547-2650` (do_title, do_description)  
**Python**: `mud/commands/character.py`  
**Current Tests**: None

```python
# tests/test_player_title_desc.py

def test_title_sets_custom_title():
    """Title command sets player's title."""
    # ROM C: act_info.c:2547-2575
    player = create_player(name="Gandalf")
    
    do_title(player, "the Grey Wizard")
    
    assert player.pcdata.title == " the Grey Wizard"  # Space prefix

def test_title_visible_in_who():
    """Player title appears in who list."""
    player = create_player(name="Aragorn", level=20)
    player.pcdata.title = " son of Arathorn"
    
    observer = create_player()
    output = do_who(observer, "")
    
    assert "Aragorn son of Arathorn" in output

def test_title_length_limit():
    """Title cannot exceed maximum length."""
    # ROM C: Title limited to 45 characters
    player = create_player()
    long_title = "x" * 100
    
    do_title(player, long_title)
    
    assert len(player.pcdata.title) <= 50  # Truncated

def test_description_sets_long_desc():
    """Description command sets player's long description."""
    # ROM C: act_info.c:2579-2650
    player = create_player(name="Frodo")
    description = "A small hobbit with bright eyes and curly hair."
    
    do_description(player, description)
    
    assert player.description == description

def test_description_shown_on_look():
    """Player description shown when looked at."""
    player = create_player(name="Frodo")
    player.description = "A brave hobbit."
    
    observer = create_player()
    output = do_look(observer, "Frodo")
    
    assert "brave hobbit" in output.lower()
```

---

### P2: Wimpy (Auto-Flee) System

**ROM Reference**: `src/act_info.c:2800-2831` (do_wimpy), `src/fight.c` (wimpy checks)  
**Python**: `mud/commands/remaining_rom.py`  
**Current Tests**: None

```python
# tests/test_player_wimpy.py

def test_wimpy_sets_flee_threshold():
    """Wimpy command sets HP threshold for auto-flee."""
    # ROM C: act_info.c:2800-2831
    player = create_player(max_hp=200)
    
    do_wimpy(player, "50")
    
    assert player.wimpy == 50

def test_wimpy_triggers_auto_flee():
    """Player auto-flees when HP drops below wimpy."""
    # ROM C: fight.c checks wimpy during combat
    player = create_player(hp=200, max_hp=200, wimpy=100)
    enemy = create_mob()
    player.fighting = enemy
    
    # Take damage to 80 HP (below wimpy 100)
    player.hit = 80
    
    process_combat_round(player)
    
    assert player.room != enemy.room  # Fled

def test_wimpy_max_hp_percent():
    """Wimpy cannot exceed max HP."""
    player = create_player(max_hp=200)
    
    do_wimpy(player, "500")  # Try to set above max
    
    assert player.wimpy <= 200

def test_wimpy_zero_disables():
    """Wimpy 0 disables auto-flee."""
    player = create_player(wimpy=50)
    
    do_wimpy(player, "0")
    
    assert player.wimpy == 0
```

---

### P2: Trust and Security Levels

**ROM Reference**: `src/act_wiz.c` (do_trust, do_advance)  
**Python**: `mud/commands/imm_admin.py`  
**Current Tests**: None

```python
# tests/test_player_trust.py

def test_trust_command_sets_trust_level():
    """Admin can set player trust levels."""
    # ROM C: act_wiz.c do_trust command
    admin = create_immortal(level=MAX_LEVEL)
    player = create_player(name="TrustedOne", level=10)
    
    do_trust(admin, "TrustedOne 52")  # Hero trust
    
    assert player.trust == 52

def test_trust_grants_immortal_commands():
    """Trust level grants access to immortal commands."""
    player = create_player(level=10, trust=52)
    
    # Should be able to use hero-level commands
    result = do_goto(player, "3001")  # Goto command
    
    assert "Huh?" not in result  # Command worked

def test_trust_shown_in_stat():
    """Player trust level shown in stat command."""
    player = create_player(name="Trusted", trust=52)
    admin = create_immortal()
    
    output = do_stat(admin, "Trusted")
    
    assert "trust" in output.lower()
    assert "52" in output
```

---

### P3: Player Visibility States

**ROM Reference**: `src/act_wiz.c`, `src/act_comm.c`  
**Python**: `mud/commands/imm_display.py`  
**Current Tests**: None

```python
# tests/test_player_visibility.py

def test_afk_flag_visible():
    """[AFK] flag shown when player is AFK."""
    player = create_player(name="Away")
    player.comm = COMM_AFK
    
    observer = create_player()
    output = do_who(observer, "")
    
    assert "[AFK]" in output
    assert "Away" in output

def test_wizinvis_hides_from_mortals():
    """Wizinvis immortals invisible to lower-level players."""
    immortal = create_immortal(level=55)
    immortal.invis_level = 52
    
    mortal = create_player(level=20)
    output = do_who(mortal, "")
    
    assert immortal.name not in output  # Not visible

def test_wizinvis_visible_to_higher_immortals():
    """Wizinvis immortals visible to higher-level immortals."""
    immortal = create_immortal(name="Sneaky", level=52)
    immortal.invis_level = 52
    
    higher_immortal = create_immortal(level=60)
    output = do_who(higher_immortal, "")
    
    assert "Sneaky" in output  # Visible to higher

def test_incognito_hides_true_level():
    """Incognito command masks immortal's true level."""
    immortal = create_immortal(name="Secret", level=58)
    
    do_incognito(immortal, "25")  # Appear as level 25
    
    mortal = create_player()
    output = do_whois(mortal, "Secret")
    
    assert "25" in output  # Shows incognito level
    assert "58" not in output  # True level hidden
```

---

## 🎯 Implementation Roadmap

### Phase 1: Critical Player Info (P0) - 2-3 days
1. ✅ Create `tests/test_player_info_commands.py`
2. Implement 12 score display tests
3. Implement 4 worth/whois tests
4. ✅ Create `tests/test_player_auto_settings.py`
5. Implement 15 auto-setting tests
6. Fix any command output format bugs

### Phase 2: Conditions and Flags (P1) - 2-3 days
1. ✅ Create `tests/test_player_conditions.py`
2. Implement 8 condition system tests
3. ✅ Create `tests/test_player_flags.py`
4. Implement 10 KILLER/THIEF flag tests
5. Verify flag decay mechanics

### Phase 3: Customization and Security (P2) - 2 days
1. ✅ Create `tests/test_player_prompt.py`
2. Implement 6 prompt customization tests
3. ✅ Create `tests/test_player_title_desc.py`
4. Implement 8 title/description tests
5. ✅ Create `tests/test_player_wimpy.py`
6. Implement 4 wimpy auto-flee tests
7. ✅ Create `tests/test_player_trust.py`
8. Implement trust/security tests

### Phase 4: Visibility and Polish (P3) - 1 day
1. ✅ Create `tests/test_player_visibility.py`
2. Implement AFK/wizinvis/incognito tests
3. Create integration test suite
4. Document any ROM C deviations

---

## 📊 Success Metrics

**Test Coverage Goals**:
- [ ] 12/12 score output tests
- [ ] 15/15 auto-setting tests
- [ ] 8/8 condition system tests
- [ ] 10/10 player flag tests
- [ ] 6/6 prompt tests
- [ ] 8/8 title/description tests
- [ ] 12/12 trust/security tests
- [ ] 10/10 visibility tests

**ROM Parity Verification**:
- [ ] Score output matches ROM C format
- [ ] Auto-settings work exactly like ROM C
- [ ] Condition decay rates match ROM C
- [ ] Flag application/removal matches ROM C
- [ ] Prompt codes match ROM C substitutions

**Acceptance Criteria**:
- [ ] 80+ new player behavior tests created
- [ ] All tests passing with no regressions
- [ ] Differential testing vs ROM C (where possible)
- [ ] Documentation updated with test results

---

## 🔗 Related Documents

- [MOB_PARITY_TEST_PLAN.md](MOB_PARITY_TEST_PLAN.md) - Mob behavior testing
- [ROM_PARITY_FEATURE_TRACKER.md](../parity/ROM_PARITY_FEATURE_TRACKER.md) - Overall parity status
- [PROJECT_COMPLETION_STATUS.md](../../PROJECT_COMPLETION_STATUS.md) - Subsystem confidence

---

## 📝 Notes

**Why This Matters**:
- Information commands are players' primary interface to game state
- Auto-settings dramatically improve quality of life
- Conditions add survival mechanics and immersion
- Player flags drive reputation system and consequences
- Prompt customization is highly visible to all players

**ROM C Compliance**:
- All tests should reference specific ROM C source locations
- Use differential testing where possible
- Document intentional deviations (e.g., modern JSON storage)

**Test Maintenance**:
- Run full player test suite after any player-related changes
- Update tests when ROM C reference behavior changes
- Keep ROM C source comments in tests for traceability

---

**Last Updated**: 2025-12-26  
**Next Review**: After Phase 1 completion
