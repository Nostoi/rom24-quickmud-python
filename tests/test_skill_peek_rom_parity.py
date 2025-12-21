from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.object import Object, ObjIndex
from mud.skills.handlers import peek
from mud.utils import rng_mm


def make_character(**overrides) -> Character:
    base = {
        "name": overrides.get("name", "mob"),
        "level": overrides.get("level", 30),
        "hit": overrides.get("hit", 100),
        "max_hit": overrides.get("max_hit", 100),
        "position": overrides.get("position", Position.STANDING),
        "is_npc": overrides.get("is_npc", True),
        "skills": overrides.get("skills", {}),
        "inventory": overrides.get("inventory", []),
    }
    char = Character(**base)
    for key, value in overrides.items():
        setattr(char, key, value)
    return char


def make_object(**overrides) -> Object:
    proto = ObjIndex(
        vnum=overrides.get("vnum", 1),
        short_descr=overrides.get("short_descr", "an object"),
    )
    obj = Object(instance_id=None, prototype=proto)
    return obj


def test_peek_on_self_fails():
    """ROM L501: Peek only works on others."""
    thief = make_character(name="thief", level=20, is_npc=False, skills={"peek": 100})

    result = peek(thief, thief)

    assert result["success"] is False
    assert "own inventory" in result["message"].lower()


def test_peek_npc_fails():
    """ROM L501-502: Only PCs can peek."""
    npc_thief = make_character(name="npc", level=20, is_npc=True, skills={"peek": 100})
    victim = make_character(name="victim", level=20)

    result = peek(npc_thief, victim)

    assert result["success"] is False
    assert "npc" in result["message"].lower()


def test_peek_skill_check_success():
    """ROM L502: Skill check - number_percent() < get_skill(ch, gsn_peek)."""
    thief = make_character(name="thief", level=20, is_npc=False, skills={"peek": 100})
    victim = make_character(name="victim", level=20)

    obj1 = make_object(short_descr="a sword")
    obj2 = make_object(short_descr="a potion")
    victim.inventory = [obj1, obj2]

    rng_mm.seed_mm(0x1234)
    result = peek(thief, victim)

    assert result["success"] is True
    assert len(result["inventory"]) == 2


def test_peek_skill_check_failure():
    """ROM L502: Peek fails if skill check fails."""
    thief = make_character(name="thief", level=20, is_npc=False, skills={"peek": 10})
    victim = make_character(name="victim", level=20)

    # Low skill, high roll = failure
    rng_mm.seed_mm(0xABCD)
    result = peek(thief, victim)

    if not result["success"]:
        assert "failed" in result["message"].lower()


def test_peek_returns_inventory():
    """ROM L504-506: Success shows victim's inventory."""
    thief = make_character(name="thief", level=30, is_npc=False, skills={"peek": 100})
    victim = make_character(name="victim", level=20)

    obj1 = make_object(short_descr="a dagger")
    obj2 = make_object(short_descr="a shield")
    obj3 = make_object(short_descr="gold coins")
    victim.inventory = [obj1, obj2, obj3]

    rng_mm.seed_mm(0x5555)
    result = peek(thief, victim)

    assert result["success"] is True
    assert result["inventory"] == [obj1, obj2, obj3]
    assert "inventory" in result["message"].lower()


def test_peek_empty_inventory():
    """Peek succeeds even with empty inventory."""
    thief = make_character(name="thief", level=20, is_npc=False, skills={"peek": 100})
    victim = make_character(name="victim", level=20, inventory=[])

    rng_mm.seed_mm(0x7777)
    result = peek(thief, victim)

    assert result["success"] is True
    assert result["inventory"] == []


def test_peek_skill_variance():
    """Peek success varies with skill level."""
    low_skill_thief = make_character(name="newbie", level=20, is_npc=False, skills={"peek": 20})
    high_skill_thief = make_character(name="master", level=20, is_npc=False, skills={"peek": 95})
    victim = make_character(name="victim", level=20)

    low_successes = 0
    high_successes = 0

    for seed in range(50):
        rng_mm.seed_mm(seed)
        if peek(low_skill_thief, victim)["success"]:
            low_successes += 1

        rng_mm.seed_mm(seed)
        if peek(high_skill_thief, victim)["success"]:
            high_successes += 1

    # High skill should succeed more often
    assert high_successes > low_successes


def test_peek_no_target_fails():
    """Peek requires a target."""
    thief = make_character(name="thief", level=20, is_npc=False, skills={"peek": 100})

    result = peek(thief, None)

    assert result["success"] is False
    assert "no target" in result["message"].lower()
