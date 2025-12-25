from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills.handlers import mass_healing


def make_character(**overrides) -> Character:
    base = {
        "name": overrides.get("name", "mob"),
        "level": overrides.get("level", 30),
        "hit": overrides.get("hit", 50),
        "max_hit": overrides.get("max_hit", 100),
        "move": overrides.get("move", 50),
        "max_move": overrides.get("max_move", 100),
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


def test_mass_healing_heals_same_type_npcs():
    """ROM L3818: Both NPCs should be healed."""
    room = make_room()
    caster = make_character(name="caster", level=20, is_npc=True, room=room)
    npc1 = make_character(name="npc1", hit=50, max_hit=100, move=50, max_move=100, is_npc=True, room=room)
    npc2 = make_character(name="npc2", hit=30, max_hit=100, move=30, max_move=100, is_npc=True, room=room)

    room.people = [caster, npc1, npc2]

    result = mass_healing(caster)

    assert result is True
    assert npc1.hit == 100  # 50 + 100 capped at max_hit
    assert npc2.hit == 100  # 30 + 100 capped at max_hit
    assert npc1.move >= 50 + 20  # 50 + level refresh
    assert npc2.move >= 30 + 20


def test_mass_healing_heals_same_type_pcs():
    """ROM L3818: Both PCs should be healed."""
    room = make_room()
    caster = make_character(name="caster", level=25, is_npc=False, room=room)
    pc1 = make_character(name="pc1", hit=40, max_hit=200, move=40, max_move=100, is_npc=False, room=room)
    pc2 = make_character(name="pc2", hit=60, max_hit=200, move=60, max_move=100, is_npc=False, room=room)

    room.people = [caster, pc1, pc2]

    result = mass_healing(caster)

    assert result is True
    assert pc1.hit == 140
    assert pc2.hit == 160
    assert pc1.move >= 40 + 25
    assert pc2.move >= 60 + 25


def test_mass_healing_skips_different_types():
    """ROM L3818: PC caster should not heal NPCs."""
    room = make_room()
    pc_caster = make_character(name="caster", level=20, hit=50, max_hit=200, is_npc=False, room=room)
    npc = make_character(name="npc", hit=50, max_hit=100, move=50, max_move=100, is_npc=True, room=room)

    room.people = [pc_caster, npc]

    result = mass_healing(pc_caster)

    assert pc_caster.hit == 150
    assert npc.hit == 50


def test_mass_healing_heals_caster():
    """ROM L3816-3822: Caster is in room and same type, so gets healed."""
    room = make_room()
    caster = make_character(name="caster", level=30, hit=40, max_hit=200, move=40, max_move=100, is_npc=True, room=room)

    room.people = [caster]

    result = mass_healing(caster)

    assert result is True
    assert caster.hit == 140
    assert caster.move >= 40 + 30


def test_mass_healing_empty_room():
    """No targets if no room."""
    caster = make_character(name="caster", level=20, is_npc=True)
    caster.room = None

    result = mass_healing(caster)

    assert result is False


def test_mass_healing_mixed_room():
    """ROM L3818: Only same-type occupants get healed."""
    room = make_room()
    npc_caster = make_character(name="npc_caster", level=20, hit=50, max_hit=200, is_npc=True, room=room)
    npc1 = make_character(name="npc1", hit=50, max_hit=200, is_npc=True, room=room)
    pc1 = make_character(name="pc1", hit=50, max_hit=100, is_npc=False, room=room)
    pc2 = make_character(name="pc2", hit=50, max_hit=100, is_npc=False, room=room)

    room.people = [npc_caster, npc1, pc1, pc2]

    result = mass_healing(npc_caster)

    assert result is True
    assert npc_caster.hit == 150
    assert npc1.hit == 150
    assert pc1.hit == 50
    assert pc2.hit == 50


def test_mass_healing_caps_at_max_hit():
    """Heal doesn't exceed max_hit."""
    room = make_room()
    caster = make_character(name="caster", level=20, hit=95, max_hit=100, is_npc=True, room=room)

    room.people = [caster]

    result = mass_healing(caster)

    assert result is True
    assert caster.hit == 100  # Capped at max_hit


def test_mass_healing_caps_at_max_move():
    """Refresh doesn't exceed max_move."""
    room = make_room()
    caster = make_character(name="caster", level=20, move=95, max_move=100, is_npc=True, room=room)

    room.people = [caster]

    result = mass_healing(caster)

    assert result is True
    assert caster.move == 100  # Capped at max_move
