"""INV-046 (PHANTOM-REGISTRY) — immortal commands must use the real char lookups.

ROM has exactly ONE live-character list: ``src/handler.c:2222-2243`` get_char_world
(room-first, then the char_list walk gated on can_see + is_name) and
``src/handler.c:2194-2213`` get_char_room. ``mud/commands/imm_commands.py`` shipped
a divergent duplicate pair that scanned ``getattr(registry, "char_list", [])`` /
``getattr(registry, "players", {})`` — attributes that do not exist on
``mud/registry.py`` in production; only the test suite injected them. Every
production immortal world-by-name lookup (notell/freeze/transfer/force/…)
therefore resolved nothing and answered "They aren't here." for live targets.

Family 1: the duplicate pair itself must delegate to ``mud.world.char_find``.
The autouse fixture below strips the phantom attributes so these tests exercise
the PRODUCTION registry shape, not the injected-fake one.
"""

from __future__ import annotations

import pytest

from mud import registry as global_registry
from mud.models.character import character_registry
from mud.world import create_test_character, initialize_world

_PHANTOM_ATTRS = ("char_list", "players", "descriptor_list")


@pytest.fixture(scope="module", autouse=True)
def setup_world():
    initialize_world("area/area.lst")
    yield


@pytest.fixture(autouse=True)
def _production_registry_shape():
    """Simulate production: ``mud.registry`` has NO char_list/players attrs.

    Other test files inject these module attributes; strip them here so any
    code path still reading the phantom attrs scans nothing — exactly the
    production state INV-046 describes.
    """
    saved = {}
    for attr in _PHANTOM_ATTRS:
        if hasattr(global_registry, attr):
            saved[attr] = getattr(global_registry, attr)
            delattr(global_registry, attr)
    yield
    for attr, value in saved.items():
        setattr(global_registry, attr, value)


def _imm(name: str, room_vnum: int):
    char = create_test_character(name, room_vnum)
    char.level = 60
    char.trust = 60
    return char


def _cleanup(*chars) -> None:
    for ch in chars:
        room = getattr(ch, "room", None)
        if room is not None and ch in room.people:
            room.people.remove(ch)
        if ch in character_registry:
            character_registry.remove(ch)


def test_transfer_resolves_world_target_without_phantom_registry():
    # mirrors ROM src/act_wiz.c:846-848 — do_transfer resolves its victim via
    # get_char_world (src/handler.c:2222-2243 char_list walk); ROM has no
    # separate "players" map, so a live char in another room MUST be found.
    from mud.commands.imm_commands import do_transfer

    admin = _imm("Zzinvimm", 3001)
    victim = create_test_character("Zzinvvictim", 3005)
    try:
        result = do_transfer(admin, "zzinvvictim")
        assert result == "Ok.", f"transfer must resolve a character_registry target, got: {result!r}"
        assert victim.room is admin.room, "victim must be moved to the immortal's room"
    finally:
        _cleanup(admin, victim)


def test_force_resolves_world_target_without_phantom_registry():
    # mirrors ROM src/act_wiz.c:4279-4320 — single-target do_force resolves via
    # get_char_world; production registry has no phantom lists to scan.
    from mud.commands.imm_commands import do_force

    admin = _imm("Zzinvforcer", 3001)
    victim = create_test_character("Zzinvforced", 3005)
    try:
        result = do_force(admin, "zzinvforced look")
        assert result == "Ok.\n\r", f"force must resolve a character_registry target, got: {result!r}"
    finally:
        _cleanup(admin, victim)


def test_imm_get_char_room_uses_rom_is_name_and_self():
    # mirrors ROM src/handler.c:2194-2213 — get_char_room honors the "self"
    # keyword (:2203) and gates on is_name (:2207), a whole-word PREFIX match
    # (src/handler.c:932-969): "zguard" is not a prefix of "zzparityguard" and
    # must NOT resolve (the old duplicate used substring matching).
    from mud.commands.imm_commands import get_char_room

    admin = _imm("Zzinvlooker", 3001)
    mob = create_test_character("zzparityguard", 3001)
    mob.is_npc = True
    try:
        assert get_char_room(admin, "self") is admin, "ROM 'self' keyword must resolve the actor"
        assert get_char_room(admin, "zzparity") is mob, "whole-word prefix must resolve"
        assert get_char_room(admin, "zparityguard") is None, "substring (non-prefix) must NOT resolve"
    finally:
        _cleanup(admin, mob)
