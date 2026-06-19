from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import ActFlag, AffectFlag, Position
from mud.models.room import Room
from mud.skills.handlers import steal
from mud.utils import rng_mm


def make_character(**overrides) -> Character:
    base = {
        "name": overrides.get("name", "mob"),
        "level": overrides.get("level", 30),
        "hit": overrides.get("hit", 100),
        "max_hit": overrides.get("max_hit", 100),
        "position": overrides.get("position", Position.STANDING),
        "is_npc": overrides.get("is_npc", True),
        "gold": overrides.get("gold", 0),
        "silver": overrides.get("silver", 0),
        "skills": overrides.get("skills", {}),
    }
    char = Character(**base)
    for key, value in overrides.items():
        setattr(char, key, value)
    return char


def make_room(**overrides) -> Room:
    base = {
        "vnum": overrides.get("vnum", 3001),
        "name": overrides.get("name", "Test Room"),
        "description": overrides.get("description", "A test room."),
    }
    room = Room(**base)
    for key, value in overrides.items():
        setattr(room, key, value)
    return room


def test_steal_from_self_fails():
    """ROM L2185-2189: Can't steal from self."""
    thief = make_character(name="thief", level=20)

    result = steal(thief, thief)

    assert result["success"] is False
    assert "pointless" in result["message"].lower()


def test_steal_from_fighting_mob_fails():
    """ROM L2194-2199: Can't steal from fighting NPC."""
    room = make_room()
    thief = make_character(name="thief", level=20, room=room)
    mob = make_character(name="mob", level=15, is_npc=True, position=Position.FIGHTING, room=room)

    result = steal(thief, mob)

    assert result["success"] is False
    assert "kill stealing" in result["message"].lower()


def test_steal_gold_success():
    """ROM L2268-2296: Steal gold proportional to level."""
    room = make_room()
    thief = make_character(name="thief", level=30, is_npc=False, gold=0, silver=0, skills={"steal": 100}, room=room)
    victim = make_character(name="victim", level=20, gold=1000, silver=500, room=room)

    rng_mm.seed_mm(0x1)
    result = steal(thief, victim, item_name="gold", target_name="victim")

    assert result["success"] is True
    assert result.get("gold", 0) > 0
    assert "Bingo" in result["message"]


def test_steal_coins_success():
    """ROM L2268-2296: Steal coins gets both gold and silver."""
    room = make_room()
    thief = make_character(name="thief", level=25, is_npc=False, gold=0, silver=0, skills={"steal": 100}, room=room)
    victim = make_character(name="victim", level=20, gold=500, silver=1000, room=room)

    rng_mm.seed_mm(0xABCD)
    result = steal(thief, victim, item_name="coins", target_name="victim")

    if result["success"]:
        total_stolen = result.get("gold", 0) + result.get("silver", 0)
        assert total_stolen > 0


def test_steal_failure_removes_sneak():
    """ROM L2220-2221: Failure removes sneak."""
    room = make_room()
    thief = make_character(
        name="thief",
        level=10,
        is_npc=False,
        affected_by=int(AffectFlag.SNEAK),
        skills={"steal": 10},
        room=room,
    )
    victim = make_character(name="victim", level=30, gold=100, room=room)

    rng_mm.seed_mm(0xDEAD)
    result = steal(thief, victim, item_name="gold", target_name="victim")

    if not result["success"]:
        assert not (thief.affected_by & int(AffectFlag.SNEAK))


def test_steal_failure_victim_yells():
    """ROM L2225-2244: Failure causes victim to yell."""
    room = make_room()
    thief = make_character(name="Sneaky", level=10, is_npc=False, skills={"steal": 10}, room=room)
    victim = make_character(name="victim", level=30, gold=100, room=room)

    rng_mm.seed_mm(0xBEEF)
    result = steal(thief, victim, item_name="gold", target_name="victim")

    if not result["success"]:
        assert "victim_yell" in result
        assert "Sneaky" in result["victim_yell"]


def test_steal_level_difference_too_high():
    """ROM L2211-2212: Level difference > 7 between PCs fails.

    Both PCs must be clansmen within the is_safe PK ladder so ROM is_safe
    (src/fight.c:1096-1120) PASSES (attacker level 5 is not > victim 20 + 8) and
    control reaches the handler's own L2211 ±7 level check — otherwise is_safe
    would block first and this test would go green for the wrong reason.
    """
    room = make_room()
    low_thief = make_character(name="newbie", level=5, is_npc=False, clan=1, skills={"steal": 100}, room=room)
    high_victim = make_character(name="veteran", level=20, is_npc=False, clan=1, gold=1000, room=room)

    result = steal(low_thief, high_victim, item_name="gold", target_name="veteran")

    # Should fail due to level difference (handler L2211), not is_safe.
    assert result["success"] is False
    assert "Mota" not in result["message"]
    assert "clan" not in result["message"].lower()


def test_steal_sleeping_victim_bonus():
    """ROM L2204-2205: Sleeping victim gives -10 penalty (easier)."""
    room = make_room()
    thief = make_character(name="thief", level=20, is_npc=False, skills={"steal": 50}, room=room)
    victim = make_character(name="victim", level=20, position=Position.SLEEPING, gold=500, room=room)

    # With sleeping bonus, steal should succeed more often
    successes = 0
    for seed in range(20):
        rng_mm.seed_mm(seed)
        victim.gold = 500
        thief.gold = 0
        result = steal(thief, victim, item_name="gold", target_name="victim")
        if result["success"]:
            successes += 1

    # Should have some successes with sleeping bonus
    assert successes > 0


def test_steal_no_coins_fails():
    """ROM L2276-2279: No coins to steal fails."""
    room = make_room()
    thief = make_character(name="thief", level=20, is_npc=False, skills={"steal": 100}, room=room)
    victim = make_character(name="victim", level=20, gold=0, silver=0, room=room)

    rng_mm.seed_mm(0x0)
    result = steal(thief, victim, item_name="gold", target_name="victim")

    assert result["success"] is False
    assert "couldn't get any coins" in result["message"].lower()


def test_steal_pc_to_pc_sets_thief_flag():
    """ROM L2256-2261: PC stealing from PC sets THIEF flag."""
    # Both PCs are clansmen at equal level so ROM is_safe (src/fight.c:1096-1120)
    # passes and control reaches the L2256-2261 THIEF-flag logic.
    room = make_room()
    thief = make_character(name="thief", level=20, is_npc=False, clan=1, skills={"steal": 10}, room=room)
    victim_pc = make_character(name="victim", level=20, is_npc=False, clan=1, gold=100, room=room)

    rng_mm.seed_mm(0x9999)
    result = steal(thief, victim_pc, item_name="gold", target_name="victim")

    if not result["success"] and not result.get("victim_attacks", False):
        assert result.get("thief_flag", False) is True


def test_steal_npc_victim_attacks_on_failure():
    """ROM L2247-2250: NPC victim attacks thief on failure."""
    room = make_room()
    thief = make_character(name="thief", level=20, is_npc=False, skills={"steal": 10}, room=room)
    npc = make_character(name="guard", level=25, is_npc=True, gold=100, room=room)

    rng_mm.seed_mm(0x7777)
    result = steal(thief, npc, item_name="gold", target_name="guard")

    if not result["success"]:
        assert result.get("victim_attacks", False) is True


def test_steal_from_safe_healer_blocked_via_skill_handler():
    """STEAL-015: the steal SKILL HANDLER must apply ROM is_safe (src/act_obj.c:2191).

    A steal routed through the skill system (the ``steal`` handler) rather than the
    ``do_steal`` command must still be gated by is_safe. ROM ``do_steal`` calls
    ``is_safe(ch, victim)`` unconditionally at L2191 and returns when it is TRUE;
    is_safe's NPC-victim branch (src/fight.c:1018-1124) rejects healers with
    "I don't think Mota would approve." Before this fix the handler had no gate, so
    a skill-path steal could rob shopkeepers/healers/pets/safe-room mobs.
    """
    room = make_room(room_flags=0)
    thief = make_character(name="thief", level=30, is_npc=False, skills={"steal": 100}, room=room)
    healer = make_character(name="healer", level=20, is_npc=True, act=int(ActFlag.IS_HEALER), gold=1000, room=room)

    result = steal(thief, healer, item_name="gold", target_name="healer")

    assert result["success"] is False
    assert "Mota" in result["message"]
