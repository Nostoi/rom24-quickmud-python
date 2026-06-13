"""MAGIC-020 — spell_curse object branch uses $p PERS + TO_ALL room broadcast.

ROM `spell_curse` object branch (`src/magic.c:1737/1751/1773`):
  - `act("$p is already filled with evil.", ch, obj, NULL, TO_CHAR)`   ($p, cap)
  - `act("$p glows with a red aura.", ch, obj, NULL, TO_ALL)`          ($p, cap, room+caster)
  - `act("$p glows with a malevolent aura.", ch, obj, NULL, TO_ALL)`   ($p, cap, room+caster)

`act()` caps buf[0] (so a lowercase short_descr renders capitalized) and TO_ALL
delivers to the whole room INCLUDING the caster. The Python baked the lowercase
short_descr and sent the aura lines only to the caster.
"""

from __future__ import annotations

from mud.models.constants import ExtraFlag
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.skills import handlers as skill_handlers
from mud.world import create_test_character


def _make_caster(room_vnum: int = 3001):
    from mud.registry import room_registry

    if room_vnum not in room_registry:
        room_registry[room_vnum] = Room(vnum=room_vnum, name="Lab", description="")
    char = create_test_character("Cursecaster", room_vnum)
    char.level = 30
    char.messages = []
    return char


def test_magic020_curse_object_malevolent_aura_caps_and_broadcasts(monkeypatch):
    caster = _make_caster()
    observer = create_test_character("Watcher", 3001)
    observer.messages = []

    proto = ObjIndex(vnum=1000, short_descr="a silver dagger")
    obj = Object(instance_id=1, prototype=proto, level=10, extra_flags=int(ExtraFlag.BLESS))
    monkeypatch.setattr(skill_handlers, "saves_dispel", lambda level, spell_level, duration: False)

    assert skill_handlers.curse(caster, obj) is True

    # ROM act() caps buf[0] -> "A silver dagger …".
    assert any("A silver dagger glows with a malevolent aura." in m for m in caster.messages), caster.messages
    # ROM TO_ALL delivers to the whole room, including the observer.
    assert any("A silver dagger glows with a malevolent aura." in m for m in observer.messages), observer.messages


def test_magic020_curse_object_already_evil_caps():
    caster = _make_caster(3002)

    proto = ObjIndex(vnum=1001, short_descr="a cursed blade")
    obj = Object(instance_id=2, prototype=proto, level=10, extra_flags=int(ExtraFlag.EVIL))

    assert skill_handlers.curse(caster, obj) is False
    # ROM act("$p is already filled with evil.", …, TO_CHAR) — $p cap.
    assert any("A cursed blade is already filled with evil." in m for m in caster.messages), caster.messages
