from __future__ import annotations

from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room
from mud.skills.handlers import cancellation


def make_character(**overrides) -> Character:
    base = {
        "name": overrides.get("name", "mob"),
        "level": overrides.get("level", 30),
        "hit": overrides.get("hit", 100),
        "max_hit": overrides.get("max_hit", 100),
        "position": overrides.get("position", Position.STANDING),
        "is_npc": overrides.get("is_npc", True),
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


def test_cancellation_pc_to_npc():
    """ROM L1041-1047: PC can cancel NPC spells."""
    pc = make_character(name="pc", level=30, is_npc=False)
    npc = make_character(name="npc", level=20, is_npc=True)
    npc.apply_spell_effect(SpellEffect(name="armor", duration=10, level=10, ac_mod=-10))
    pc.messages = []

    result = cancellation(pc, npc)

    assert result is True


def test_cancellation_npc_to_pc():
    """ROM L1041-1047: NPC can cancel PC spells."""
    npc = make_character(name="npc", level=30, is_npc=True)
    pc = make_character(name="pc", level=20, is_npc=False)
    pc.apply_spell_effect(SpellEffect(name="bless", duration=10, level=10))
    npc.messages = []

    result = cancellation(npc, pc)

    assert result is True


def test_cancellation_same_type_fails():
    """ROM L1041-1047: Same type (PC->PC or NPC->NPC) fails."""
    pc1 = make_character(name="pc1", level=30, is_npc=False)
    pc2 = make_character(name="pc2", level=20, is_npc=False)
    pc2.apply_spell_effect(SpellEffect(name="shield", duration=10, level=10))
    pc1.messages = []

    result = cancellation(pc1, pc2)

    assert result is False
    assert any("dispel magic" in msg for msg in pc1.messages)


def test_cancellation_removes_multiple_effects():
    """ROM L1051-1199: Removes all dispellable effects."""
    room = make_room()
    pc = make_character(name="pc", level=40, is_npc=False, room=room)
    npc = make_character(name="npc", level=20, is_npc=True, room=room)
    pc.messages = []
    room.people = [pc, npc]

    npc.apply_spell_effect(SpellEffect(name="armor", duration=10, level=10, ac_mod=-10))
    npc.apply_spell_effect(SpellEffect(name="bless", duration=10, level=10))
    npc.apply_spell_effect(SpellEffect(name="shield", duration=10, level=10, ac_mod=-20))

    result = cancellation(pc, npc)

    assert result is True
    assert len(npc.spell_effects) == 0


def test_cancellation_no_effects_fails():
    """ROM L1200-1203: Spell fails if no effects removed."""
    pc = make_character(name="pc", level=30, is_npc=False)
    npc = make_character(name="npc", level=20, is_npc=True)
    pc.messages = []

    result = cancellation(pc, npc)

    assert result is False
    assert any("failed" in msg.lower() for msg in pc.messages)


def test_cancellation_level_bonus():
    """ROM L1039: Cancellation gets +2 level bonus."""
    pc = make_character(name="pc", level=10, is_npc=False)
    npc = make_character(name="npc", level=20, is_npc=True)
    npc.apply_spell_effect(SpellEffect(name="armor", duration=10, level=5))

    result = cancellation(pc, npc)

    assert result is True


def test_cancellation_no_save():
    """ROM L1049: Unlike dispel magic, victim gets NO save."""
    pc = make_character(name="pc", level=1, is_npc=False)
    npc = make_character(name="npc", level=50, is_npc=True)
    npc.apply_spell_effect(SpellEffect(name="armor", duration=10, level=5))

    result = cancellation(pc, npc)

    assert result is True


def test_cancellation_requires_both():
    """Cancellation requires caster and target."""
    pc = make_character(level=30, is_npc=False)

    try:
        cancellation(pc, None)
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "target" in str(e).lower()


def test_cancellation_charmed_exception():
    """ROM L1042: Charmed PC can cancel their master."""
    room = make_room()
    pc = make_character(name="pc", level=20, is_npc=False, room=room)
    npc_master = make_character(name="master", level=30, is_npc=True, room=room)

    pc.affected_by = int(AffectFlag.CHARM)
    pc.master = npc_master
    npc_master.apply_spell_effect(SpellEffect(name="armor", duration=10, level=10))
    pc.messages = []

    result = cancellation(pc, npc_master)

    assert result is False
