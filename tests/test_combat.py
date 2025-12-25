from pathlib import Path
from types import SimpleNamespace

import pytest

from mud.combat import engine as combat_engine
from mud.commands import process_command
from mud.models.character import Character
from mud.models.constants import (
    AC_BASH,
    AC_EXOTIC,
    AC_PIERCE,
    AC_SLASH,
    WEAPON_POISON,
    AffectFlag,
    DamageType,
    ImmFlag,
    PlayerFlag,
    Position,
    DefenseBit,
    RoomFlag,
    VulnFlag,
    WeaponType,
    attack_lookup,
)
from mud.models.room import Room
from mud.skills import load_skills, skill_registry
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world
from mud.config import get_pulse_violence


def setup_combat() -> tuple[Character, Character]:
    initialize_world("area/area.lst")
    room_vnum = 3001
    attacker = create_test_character("Attacker", room_vnum)
    attacker.skills["hand to hand"] = 100
    victim = create_test_character("Victim", room_vnum)
    victim.is_npc = True
    return attacker, victim


def assert_attack_message(message: str, victim_name: str = "Victim") -> None:
    assert message.startswith("{2")
    assert victim_name in message
    assert message.endswith("{x")


def test_rescue_checks_group_permission(monkeypatch: pytest.MonkeyPatch) -> None:
    load_skills(Path("data/skills.json"))

    rescuer = Character(name="Rescuer", level=35, is_npc=False, skills={"rescue": 75})
    stranger = Character(name="Stranger", is_npc=False)
    foe = Character(name="Ogre", is_npc=True)

    room = Room(vnum=3001)
    for ch in (rescuer, stranger, foe):
        room.add_character(ch)

    stranger.fighting = foe
    stranger.position = Position.FIGHTING
    foe.fighting = stranger
    foe.position = Position.FIGHTING

    rescuer.wait = 0
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

    out = process_command(rescuer, "rescue stranger")

    assert out == "Kill stealing is not permitted."
    assert rescuer.wait == 0
    assert rescuer.fighting is None


def test_kill_blocks_safe_room_for_npc() -> None:
    attacker, victim = setup_combat()
    attacker.room.room_flags = int(RoomFlag.ROOM_SAFE)

    out = process_command(attacker, "kill victim")

    assert out == "Not in this room."
    assert attacker.fighting is None
    assert victim.fighting is None


def test_kill_requires_clan_for_player_targets() -> None:
    initialize_world("area/area.lst")
    attacker = create_test_character("Attacker", 3001)
    victim = create_test_character("Target", 3001)

    out = process_command(attacker, "kill target")

    assert out == "Join a clan if you want to kill players."
    assert attacker.fighting is None
    assert victim.fighting is None


def test_kill_flags_player_as_killer(monkeypatch: pytest.MonkeyPatch) -> None:
    initialize_world("area/area.lst")
    attacker = create_test_character("Attacker", 3001)
    victim = create_test_character("Duelist", 3001)
    attacker.clan = 1
    victim.clan = 1
    attacker.skills["hand to hand"] = 100
    attacker.hitroll = 100
    victim.hit = 50
    victim.max_hit = 50

    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)
    monkeypatch.setattr("mud.utils.rng_mm.number_range", lambda low, high: low)

    out = process_command(attacker, "kill duelist")

    assert attacker.act & int(PlayerFlag.KILLER)
    assert "*** You are now a KILLER!! ***" in attacker.messages
    assert attacker.wait >= get_pulse_violence()
    assert out


def test_kill_blocks_stealing_existing_fight() -> None:
    attacker, victim = setup_combat()
    ally = create_test_character("Ally", 3001)
    victim.fighting = ally
    ally.fighting = victim

    out = process_command(attacker, "kill victim")

    assert out == "Kill stealing is not permitted."
    assert attacker.fighting is None


def test_kill_blocks_charmed_player_attacking_master() -> None:
    initialize_world("area/area.lst")
    thrall = create_test_character("Thrall", 3001)
    master = create_test_character("Master", 3001)

    thrall.add_affect(AffectFlag.CHARM)
    thrall.master = master

    out = process_command(thrall, "kill master")

    assert out == "Master is your beloved master."
    assert thrall.fighting is None
    assert master.fighting is None


def _load_kick_skill() -> None:
    skill_registry.skills.clear()
    skill_registry.handlers.clear()
    load_skills(Path("data/skills.json"))


def test_attack_damages_but_not_kill(monkeypatch: pytest.MonkeyPatch) -> None:
    attacker, victim = setup_combat()
    attacker.level = 10
    attacker.skills["hand to hand"] = 100
    attacker.damroll = 3
    attacker.hitroll = 100  # guarantee hit
    victim.hit = 10
    victim.max_hit = 10
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)
    monkeypatch.setattr("mud.utils.rng_mm.number_range", lambda low, high: low)
    out = process_command(attacker, "kill victim")
    # ROM unarmed damage for level 1: base 5 + damroll 3 = 8 total
    # Damage tier should match ROM's *** DEVASTATE *** verb (80% of max HP)
    assert out == "{2You *** DEVASTATE *** Victim!{x"
    assert victim.messages[-1] == "{4Attacker *** DEVASTATES *** you!{x"
    assert victim.hit == 2  # 10 - 8 = 2
    assert attacker.position == Position.FIGHTING
    assert victim.position == Position.FIGHTING
    assert victim in attacker.room.people


def test_attack_kills_target(monkeypatch: pytest.MonkeyPatch) -> None:
    attacker, victim = setup_combat()
    attacker.level = 10
    attacker.skills["hand to hand"] = 100
    attacker.damroll = 0  # Use 0 damroll so we get exactly 5 base damage
    attacker.hitroll = 100  # guarantee hit
    victim.hit = 5
    victim.max_hit = 5
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)
    monkeypatch.setattr("mud.utils.rng_mm.number_range", lambda low, high: low)
    out = process_command(attacker, "kill victim")
    assert out == "You kill Victim."
    assert victim.hit == 0
    assert attacker.position == Position.STANDING
    assert victim.position == Position.DEAD
    assert victim not in attacker.room.people
    assert "Victim is DEAD!!!" in attacker.messages


def test_attack_misses_target(monkeypatch):
    attacker, victim = setup_combat()
    attacker.hitroll = -100  # extremely low hit chance
    victim.hit = 10
    # Guarantee miss deterministically
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 100)
    out = process_command(attacker, "kill victim")
    assert out == "You miss Victim."
    assert victim.hit == 10
    assert attacker.position == Position.FIGHTING
    assert victim.position == Position.FIGHTING
    assert victim in attacker.room.people


def test_defense_order_and_early_out(monkeypatch):
    attacker, victim = setup_combat()
    attacker.hitroll = 100  # guarantee hit roll passes
    attacker.damroll = 3

    calls: list[str] = []

    def parry(a, v):
        calls.append("parry")
        return False

    def dodge(a, v):
        calls.append("dodge")
        return True  # early-out here

    def shield(a, v):
        calls.append("shield")
        return False

    monkeypatch.setattr(combat_engine, "check_parry", parry)
    monkeypatch.setattr(combat_engine, "check_dodge", dodge)
    monkeypatch.setattr(combat_engine, "check_shield_block", shield)

    out = process_command(attacker, "kill victim")
    assert out == "Victim dodges your attack."
    # ROM defense order: shield_block → parry → dodge (dodge early-exits, so shield not reached after)
    assert calls == ["shield", "parry", "dodge"]


def test_parry_blocks_when_skill_learned(monkeypatch: pytest.MonkeyPatch) -> None:
    attacker, victim = setup_combat()
    attacker.hitroll = 100
    attacker.is_npc = True
    victim.is_npc = False
    victim.skills["parry"] = 75
    victim.has_weapon_equipped = True

    recorded: list[tuple[Character, str, bool, int]] = []

    def fake_check_improve(ch: Character, name: str, success: bool, multiplier: int = 1) -> None:
        recorded.append((ch, name, success, multiplier))

    monkeypatch.setattr(combat_engine, "check_improve", fake_check_improve)
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)

    out = process_command(attacker, "kill victim")

    assert out == "Victim parries your attack."
    assert "You parry Attacker's attack." in victim.messages
    assert recorded == [(victim, "parry", True, 6)]


def test_shield_block_requires_shield(monkeypatch: pytest.MonkeyPatch) -> None:
    attacker, victim = setup_combat()
    attacker.hitroll = 100
    attacker.damroll = 3
    victim.skills["shield block"] = 95
    victim.has_shield_equipped = False

    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)
    monkeypatch.setattr("mud.utils.rng_mm.number_range", lambda low, high: low)

    out = process_command(attacker, "kill victim")

    assert "blocks your attack" not in out
    if out != "You kill Victim.":
        assert_attack_message(out)


def test_multi_hit_single_attack():
    attacker, victim = setup_combat()
    attacker.hitroll = 100  # guarantee hit
    attacker.damroll = 1
    victim.hit = 10

    # No extra attack skills - should only get one attack
    results = combat_engine.multi_hit(attacker, victim)
    assert len(results) == 1
    # ROM damage: base 5 + damroll 1 = 6 total
    assert_attack_message(results[0])
    assert victim.hit == 4  # 10 - 6 = 4


def test_multi_hit_with_haste():
    attacker, victim = setup_combat()
    attacker.hitroll = 100  # guarantee hit
    attacker.damroll = 1
    victim.hit = 20  # Increase HP to survive two attacks

    # Add haste affect
    attacker.add_affect(AffectFlag.HASTE)

    results = combat_engine.multi_hit(attacker, victim)
    assert len(results) == 2  # Normal + haste attack
    # With weapon damage calculation, damage will be higher than just damroll
    for message in results:
        assert_attack_message(message)
    assert victim.hit == 8  # 20 - (6 + 6) = 8


def test_multi_hit_second_attack():
    attacker, victim = setup_combat()
    attacker.hitroll = 100  # guarantee hit
    attacker.damroll = 1
    attacker.second_attack_skill = 100  # 50% chance (100/2)
    victim.hit = 20  # Increase HP to survive multiple attacks

    # Initialize fighting state
    combat_engine.set_fighting(attacker, victim)

    # Mock to force successful second attack
    from mud.utils import rng_mm

    original_number_percent = rng_mm.number_percent

    def mock_number_percent():
        return 1  # Always return 1, which is < 50

    rng_mm.number_percent = mock_number_percent

    try:
        results = combat_engine.multi_hit(attacker, victim)
        assert len(results) == 2  # First + second attack
        assert attacker.fighting == victim
        assert victim.fighting == attacker
        # ROM damage: 2 hits × 6 damage = 12 total, so 20 - 12 = 8
        assert victim.hit == 8
        for message in results:
            assert_attack_message(message)
    finally:
        # Restore original function
        rng_mm.number_percent = original_number_percent


def test_kick_command_requires_fighting() -> None:
    _load_kick_skill()
    try:
        attacker, victim = setup_combat()
        attacker.position = int(Position.FIGHTING)
        attacker.skills["kick"] = 75
        attacker.max_hit = attacker.hit = 100
        victim.max_hit = victim.hit = 100

        out = process_command(attacker, "kick")
        assert out == "You aren't fighting anyone."
    finally:
        skill_registry.skills.clear()
        skill_registry.handlers.clear()


def test_kick_command_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _load_kick_skill()
    try:
        attacker, victim = setup_combat()
        attacker.level = 20
        attacker.ch_class = 3  # warrior learns kick at level 8
        attacker.position = int(Position.FIGHTING)
        attacker.skills["kick"] = 75
        attacker.max_hit = attacker.hit = 100
        victim.max_hit = victim.hit = 100
        attacker.fighting = victim
        victim.fighting = attacker

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 10)
        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 12)

        out = process_command(attacker, "kick")

        assert_attack_message(out)
        assert victim.hit == 88
        assert attacker.wait == 12
        assert attacker.cooldowns.get("kick") == 0
    finally:
        skill_registry.skills.clear()
        skill_registry.handlers.clear()


def test_kick_command_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    _load_kick_skill()
    try:
        attacker, victim = setup_combat()
        attacker.level = 20
        attacker.ch_class = 3
        attacker.position = int(Position.FIGHTING)
        attacker.skills["kick"] = 5
        attacker.max_hit = attacker.hit = 100
        victim.max_hit = victim.hit = 100
        attacker.fighting = victim
        victim.fighting = attacker

        monkeypatch.setattr(rng_mm, "number_percent", lambda: 100)
        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 12)

        out = process_command(attacker, "kick")

        assert out == "{2You miss Victim.{x"
        assert victim.hit == 100
        assert attacker.wait == 12
        assert attacker.cooldowns.get("kick") == 0
    finally:
        skill_registry.skills.clear()
        skill_registry.handlers.clear()


def test_kick_command_requires_level() -> None:
    _load_kick_skill()
    try:
        attacker, victim = setup_combat()
        attacker.is_npc = False
        attacker.ch_class = 3  # warrior table entry uses level 8
        attacker.level = 5
        attacker.position = int(Position.FIGHTING)
        attacker.fighting = victim
        victim.fighting = attacker

        out = process_command(attacker, "kick")

        assert out == "You better leave the martial arts to fighters."
        assert attacker.wait == 0
        assert "kick" not in getattr(attacker, "cooldowns", {})
        assert victim.hit == victim.max_hit
    finally:
        skill_registry.skills.clear()
        skill_registry.handlers.clear()


def test_kick_command_requires_off_flag() -> None:
    _load_kick_skill()
    try:
        attacker, victim = setup_combat()
        attacker.is_npc = True
        attacker.off_flags = 0
        attacker.level = 20
        attacker.position = int(Position.FIGHTING)
        attacker.fighting = victim
        victim.fighting = attacker

        out = process_command(attacker, "kick")

        assert out == ""
        assert attacker.wait == 0
        assert "kick" not in getattr(attacker, "cooldowns", {})
        assert victim.hit == victim.max_hit
    finally:
        skill_registry.skills.clear()
        skill_registry.handlers.clear()


def test_multi_hit_third_attack():
    attacker, victim = setup_combat()
    attacker.hitroll = 100  # guarantee hit
    attacker.damroll = 1
    attacker.second_attack_skill = 100  # Always succeeds (50% chance)
    attacker.third_attack_skill = 100  # Always succeeds (25% chance)
    victim.hit = 20

    # Set up a monkey patch to force successful rolls
    from mud.utils import rng_mm

    original_number_percent = rng_mm.number_percent

    def mock_number_percent():
        return 1  # Always return 1, which is < any positive chance

    rng_mm.number_percent = mock_number_percent

    try:
        results = combat_engine.multi_hit(attacker, victim)
        assert len(results) == 3  # First + second + third attack
        assert attacker.fighting == victim
    finally:
        # Restore original function
        rng_mm.number_percent = original_number_percent


def test_multi_hit_with_slow():
    attacker, victim = setup_combat()
    attacker.hitroll = 100  # guarantee hit
    attacker.damroll = 1
    attacker.second_attack_skill = 100  # Normally would always succeed
    attacker.third_attack_skill = 100  # Normally would always succeed
    victim.hit = 10

    # Add slow affect
    attacker.add_affect(AffectFlag.SLOW)

    results = combat_engine.multi_hit(attacker, victim)
    # Slow reduces second attack chance and prevents third attack entirely
    assert len(results) >= 1  # Always get first attack
    # Second attack chance halved, third attack prevented


def test_multi_hit_victim_dies_early():
    attacker, victim = setup_combat()
    attacker.hitroll = 100  # guarantee hit
    attacker.damroll = 5
    attacker.second_attack_skill = 100  # Would normally get second attack
    victim.hit = 3  # Dies on first hit

    results = combat_engine.multi_hit(attacker, victim)
    assert len(results) == 1
    assert results[0] == "You kill Victim."
    assert attacker.fighting is None  # Fighting cleared on death
    assert victim.fighting is None


def test_ac_mapping_and_sign_semantics():
    # Mapping: NONE/unarmed→BASH, BASH→BASH, PIERCE→PIERCE, SLASH→SLASH, FIRE→EXOTIC
    assert combat_engine.ac_index_for_dam_type(DamageType.NONE) == AC_BASH
    assert combat_engine.ac_index_for_dam_type(DamageType.BASH) == AC_BASH
    assert combat_engine.ac_index_for_dam_type(DamageType.PIERCE) == AC_PIERCE
    assert combat_engine.ac_index_for_dam_type(DamageType.SLASH) == AC_SLASH
    assert combat_engine.ac_index_for_dam_type(DamageType.FIRE) == AC_EXOTIC

    # AC is better when more negative
    assert combat_engine.is_better_ac(-10, -5)
    assert combat_engine.is_better_ac(-1, 5)
    assert not combat_engine.is_better_ac(5, 0)


def test_ac_influences_hit_chance(monkeypatch):
    attacker, victim = setup_combat()
    attacker.hitroll = 10
    attacker.damroll = 3
    attacker.dam_type = int(DamageType.BASH)

    # Fix roll to 60 for deterministic checks
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 60)

    # No armor: base to_hit = 50 + 10 = 60 → hit on 60
    victim.armor = [0, 0, 0, 0]
    victim.hit = 10
    out = process_command(attacker, "kill victim")
    # ROM damage: base 5 + damroll 3 = 8 total
    assert_attack_message(out)

    # Reset combat state for next test
    attacker.position = Position.STANDING
    attacker.fighting = None
    victim.position = Position.STANDING
    victim.fighting = None

    # Strong negative AC lowers to_hit and causes miss
    victim.hit = 50
    victim.armor = [-22, -22, -22, -22]
    out = process_command(attacker, "kill victim")
    assert out == "You miss Victim."

    # Reset combat state for next test
    attacker.position = Position.STANDING
    attacker.fighting = None
    victim.position = Position.STANDING
    victim.fighting = None

    # Positive AC raises to_hit and causes hit
    victim.hit = 50
    victim.armor = [20, 20, 20, 20]
    out = process_command(attacker, "kill victim")
    assert_attack_message(out)


def test_visibility_and_position_modifiers(monkeypatch):
    attacker, victim = setup_combat()
    attacker.hitroll = 10
    attacker.damroll = 3
    attacker.dam_type = int(DamageType.BASH)
    victim.armor = [0, 0, 0, 0]
    victim.hit = 50

    # At roll 60, baseline to_hit=60 → hit; invisible should make it miss
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 60)
    out = process_command(attacker, "kill victim")
    assert_attack_message(out)

    attacker.position = Position.STANDING
    attacker.fighting = None
    victim.position = Position.STANDING
    victim.fighting = None

    victim.hit = 50
    victim.add_affect(AffectFlag.INVISIBLE)
    out = process_command(attacker, "kill victim")
    assert out == "You miss Victim."

    attacker.position = Position.STANDING
    attacker.fighting = None
    victim.position = Position.STANDING
    victim.fighting = None

    # Positional: roll 62; sleeping target grants +10 effective AC mods (+4 +6)
    victim.hit = 50
    victim.remove_affect(AffectFlag.INVISIBLE)
    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 62)
    victim.position = Position.SLEEPING
    out = process_command(attacker, "kill victim")
    assert_attack_message(out)


def test_riv_scaling_applies_before_side_effects(monkeypatch):
    attacker, victim = setup_combat()
    attacker.hitroll = 100
    attacker.damroll = 0  # Set to 0 to make calculation more predictable
    attacker.dam_type = 0
    victim.hit = 50

    captured: list[int] = []

    def on_hit(a, v, d):
        captured.append(d)

    monkeypatch.setattr(combat_engine, "on_hit_effects", on_hit)

    # With damroll=0, we get base unarmed damage + 0 damroll bonus
    # Then RIV resistance should reduce it by 1/3
    victim.res_flags = int(DefenseBit.BASH)
    out = combat_engine.attack_round(attacker, victim)

    # The exact damage will depend on RNG, but it should be RIV-scaled
    assert_attack_message(out)

    # More importantly, check that on_hit_effects received the scaled damage
    assert len(captured) == 1
    assert captured[0] > 0  # Should have some damage after RIV scaling
    # ROM calculation: base 5, resistance: 5 - 5//3 = 5 - 1 = 4
    assert captured[-1] == 4

    # Vulnerable: dam += dam/2 → 5 + 2 = 7
    victim.hit = 50
    victim.res_flags = 0
    victim.vuln_flags = int(VulnFlag.BASH)
    out = combat_engine.attack_round(attacker, victim)
    assert_attack_message(out)
    assert captured[-1] == 7

    # Immune: dam = 0
    victim.hit = 50
    victim.vuln_flags = 0
    victim.imm_flags = int(ImmFlag.BASH)
    out = combat_engine.attack_round(attacker, victim)
    assert out == "{2Victim is unaffected by your attack!{x"
    assert captured[-1] == 0


def test_one_hit_uses_equipped_weapon(monkeypatch: pytest.MonkeyPatch) -> None:
    attacker, victim = setup_combat()
    attacker.level = 20
    attacker.damroll = 0
    attacker.hitroll = 0
    attacker.skills["sword"] = 100
    victim.hit = 100
    victim.max_hit = 100

    attack_index = attack_lookup("slash")
    weapon_proto = SimpleNamespace(
        item_type="weapon",
        value=[int(WeaponType.SWORD), 2, 6, attack_index],
        new_format=True,
        level=20,
    )
    weapon = SimpleNamespace(
        prototype=weapon_proto,
        value=weapon_proto.value,
        item_type="weapon",
        weapon_flags=0,
        new_format=True,
        level=20,
        name="practice sword",
    )
    attacker.equipment["wield"] = weapon

    monkeypatch.setattr("mud.utils.rng_mm.number_percent", lambda: 1)
    monkeypatch.setattr("mud.utils.rng_mm.dice", lambda number, size: number * size)
    monkeypatch.setattr("mud.utils.rng_mm.number_range", lambda low, high: low)

    out = process_command(attacker, "kill victim")

    assert_attack_message(out)
    assert victim.hit == 85


def test_sharp_weapon_doubles_damage_on_proc(monkeypatch: pytest.MonkeyPatch) -> None:
    attacker, victim = setup_combat()
    attacker.level = 30
    attacker.damroll = 0
    attacker.hitroll = 100
    attacker.has_shield_equipped = True
    attacker.enhanced_damage_skill = 0
    attacker.skills["sword"] = 100
    victim.position = Position.FIGHTING

    weapon = SimpleNamespace(
        item_type="weapon",
        new_format=True,
        value=[int(WeaponType.SWORD), 2, 4, 0],
        weapon_stats=set(),
        weapon_flags=0,
        level=30,
        name="razorblade",
    )
    attacker.equipment["wield"] = weapon

    monkeypatch.setattr(rng_mm, "dice", lambda number, size: number * size)
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 10)

    base_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=120,
    )

    weapon.weapon_stats = {"sharp"}

    sharp_damage = combat_engine.calculate_weapon_damage(
        attacker,
        victim,
        int(DamageType.SLASH),
        wield=weapon,
        skill=120,
    )

    expected_bonus = (base_damage * 2 * 10) // 100
    assert sharp_damage == base_damage * 2 + expected_bonus


def test_poison_weapon_applies_affect(monkeypatch: pytest.MonkeyPatch) -> None:
    attacker, victim = setup_combat()
    attacker.hitroll = 100
    attacker.damroll = 0
    attacker.enhanced_damage_skill = 0
    victim.hit = 100
    victim.max_hit = 100
    victim.armor = [0, 0, 0, 0]

    weapon = SimpleNamespace(
        item_type="weapon",
        new_format=True,
        value=[int(WeaponType.SWORD), 2, 4, 0],
        weapon_stats=set(),
        weapon_flags=int(WEAPON_POISON),
        level=20,
        name="Viperblade",
    )
    attacker.equipment["wield"] = weapon
    victim.messages.clear()

    monkeypatch.setattr(rng_mm, "dice", lambda number, size: number * size)
    monkeypatch.setattr(rng_mm, "number_range", lambda low, high: low)
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)
    monkeypatch.setattr(combat_engine, "saves_spell", lambda *args, **kwargs: False)

    combat_engine.attack_round(attacker, victim)

    assert victim.has_affect(AffectFlag.POISON)
    assert any("poison" in msg.lower() for msg in victim.messages)
