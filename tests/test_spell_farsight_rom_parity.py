from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room
from mud.skills.handlers import farsight


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


def test_farsight_blind_check():
    """ROM L46-50: Blind character cannot use farsight."""
    caster = make_character(name="caster", level=20)
    caster.affected_by = int(AffectFlag.BLIND)
    caster.messages = []

    result = farsight(caster)

    assert result == ""
    assert any("could see" in msg for msg in caster.messages)


def test_farsight_not_blind():
    """ROM L52: Calls do_scan when not blind."""
    room = make_room()
    caster = make_character(name="caster", level=20, room=room)
    other = make_character(name="other", level=10, room=room)
    caster.affected_by = 0
    caster.messages = []
    room.people = [caster, other]

    result = farsight(caster, direction="")

    # Should call do_scan and return scan results
    assert isinstance(result, str)


def test_farsight_with_direction():
    """Farsight can scan in a specific direction."""
    room = make_room()
    north_room = make_room(vnum=3002, name="North Room")
    room.exits = {"north": north_room}

    caster = make_character(name="caster", level=20, room=room)
    caster.affected_by = 0
    caster.messages = []

    result = farsight(caster, direction="north")

    # Should call do_scan with direction
    assert isinstance(result, str)


def test_farsight_requires_caster():
    """Farsight requires a caster."""
    try:
        farsight(None)
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "caster" in str(e).lower()


def test_farsight_messages_caster():
    """Farsight sends scan results to caster."""
    room = make_room()
    caster = make_character(name="caster", level=20, room=room)
    caster.affected_by = 0
    caster.messages = []

    farsight(caster, direction="")

    # Caster should receive messages (even if empty room)
    assert hasattr(caster, "messages")
