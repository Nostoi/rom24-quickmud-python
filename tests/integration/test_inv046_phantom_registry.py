"""INV-046 (PHANTOM-REGISTRY) — immortal commands must use the real char lookups.

ROM has exactly ONE live-character list: ``src/handler.c:2222-2243`` get_char_world
(room-first, then the char_list walk gated on can_see + is_name) and
``src/handler.c:2194-2213`` get_char_room. ``mud/commands/imm_commands.py`` shipped
a divergent duplicate pair that scanned phantom registry attributes — names
that do not exist on ``mud/registry.py`` in production (see the guard test
``tests/test_phantom_registry_convention.py``); only the test suite injected them. Every
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
    production state INV-046 describes. (``descriptor_list`` IS real in
    production — mud/net/connection.py:240-246 lazily attaches it — but each
    test builds its own, so start from a clean slate and drop any leftovers.)
    """
    saved = {}
    for attr in _PHANTOM_ATTRS:
        if hasattr(global_registry, attr):
            saved[attr] = getattr(global_registry, attr)
            delattr(global_registry, attr)
    yield
    for attr in _PHANTOM_ATTRS:
        if hasattr(global_registry, attr):
            delattr(global_registry, attr)
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


def _attach_playing_descriptor(char):
    """Register a production-shaped descriptor for ``char``.

    Mirrors mud/net/connection.py:_register_descriptor/_mark_descriptor_playing
    — a SimpleNamespace on the lazily-attached ``registry.descriptor_list``.
    """
    from types import SimpleNamespace

    from mud.net.connection import CON_PLAYING, _descriptor_list

    desc = SimpleNamespace(character=char, connected=CON_PLAYING, connection=None, host="inv046", original=None)
    _descriptor_list().append(desc)
    return desc


def _detach_descriptor(desc) -> None:
    from mud.net.connection import _descriptor_list

    descriptors = _descriptor_list()
    if desc in descriptors:
        descriptors.remove(desc)


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


# --- Family 2: the remaining phantom char_list/players walk sites ---


def test_transfer_all_walks_descriptor_list():
    # mirrors ROM src/act_wiz.c:816-831 — "transfer all" walks descriptor_list
    # (CON_PLAYING, not self, in_room set, can_see) and recurses per victim.
    # The old code walked the phantom registry.players and moved nobody.
    from mud.commands.imm_commands import do_transfer

    admin = _imm("Zzinvadmin", 3001)
    victim = create_test_character("Zzinvtrans", 3005)
    desc = _attach_playing_descriptor(victim)
    try:
        do_transfer(admin, "all")
        assert victim.room is admin.room, "transfer all must move every CON_PLAYING descriptor's character"
    finally:
        _detach_descriptor(desc)
        _cleanup(admin, victim)


def test_force_players_and_gods_walk_character_registry():
    # mirrors ROM src/act_wiz.c:4233-4278 — "force players" walks char_list for
    # PCs below LEVEL_HERO; "force gods" for PCs at/above LEVEL_HERO. The old
    # code walked the phantom registry.char_list and forced nobody.
    from mud.commands.imm_commands import do_force
    from mud.models.constants import LEVEL_HERO

    admin = _imm("Zzinvruler", 3001)
    mortal = create_test_character("Zzinvmortal", 3005)
    mortal.level = 10
    hero = create_test_character("Zzinvhero", 3005)
    hero.level = LEVEL_HERO
    try:
        result = do_force(admin, "players look")
        assert result == "Ok.\n\r"
        assert any("forces you to 'look'" in m for m in mortal.messages), "mortal PC must be forced"
        assert not any("forces you to 'look'" in m for m in hero.messages), "hero is NOT in the players walk"

        result = do_force(admin, "gods look")
        assert result == "Ok.\n\r"
        assert any("forces you to 'look'" in m for m in hero.messages), "hero PC must be forced by 'force gods'"
    finally:
        _cleanup(admin, mortal, hero)


def test_force_all_accepts_port_con_playing_value():
    # mud/net/connection.py:81 defines CON_PLAYING = 1; the old "force all"
    # branch skipped any descriptor with connected != 0, i.e. every real
    # playing connection. ROM gates on d->connected == CON_PLAYING
    # (src/act_wiz.c:4225).
    from mud.commands.imm_commands import do_force

    admin = _imm("Zzinvomni", 3001)
    victim = create_test_character("Zzinvpawn", 3005)
    victim.level = 10
    desc = _attach_playing_descriptor(victim)
    try:
        result = do_force(admin, "all look")
        assert result == "Ok.\n\r"
        assert any("forces you to 'look'" in m for m in victim.messages), "CON_PLAYING descriptor must be forced"
    finally:
        _detach_descriptor(desc)
        _cleanup(admin, victim)


def test_gecho_walks_descriptor_list():
    # mirrors ROM src/interp.c:331 — {"gecho", do_echo, ...}: gecho IS do_echo
    # (src/act_wiz.c:674-696), a descriptor_list walk over CON_PLAYING
    # connections. The old body walked the phantom registry.players.
    from mud.commands.imm_emote import do_gecho

    admin = _imm("Zzinvvoice", 3001)
    victim = create_test_character("Zzinvears", 3005)
    desc = _attach_playing_descriptor(victim)
    try:
        do_gecho(admin, "the world trembles")
        assert any("the world trembles" in m for m in victim.messages), "gecho must reach CON_PLAYING descriptors"
    finally:
        _detach_descriptor(desc)
        _cleanup(admin, victim)


def test_mwhere_named_walks_character_registry_with_is_name():
    # mirrors ROM src/act_wiz.c:1993-2005 — named mwhere walks char_list gated
    # on is_name (whole-word prefix). The old code walked the phantom
    # registry.char_list with substring matching.
    from mud.commands.imm_search import do_mwhere

    admin = _imm("Zzinvseeker", 3001)
    mob = create_test_character("zzparitytarget", 3005)
    mob.is_npc = True
    try:
        out = do_mwhere(admin, "zzparitytarget")
        assert "3005" in out, f"named mwhere must find the live char via character_registry, got: {out!r}"
        out_prefix = do_mwhere(admin, "zzparity")
        assert "3005" in out_prefix, "is_name whole-word PREFIX match must resolve"
    finally:
        _cleanup(admin, mob)


def test_mwhere_no_arg_walks_descriptor_list():
    # mirrors ROM src/act_wiz.c:1958-1988 — no-arg mwhere walks descriptor_list
    # (CON_PLAYING + in_room + can_see + can_see_room).
    from mud.commands.imm_search import do_mwhere

    admin = _imm("Zzinvwatcher", 3001)
    victim = create_test_character("Zzinvplayerx", 3005)
    desc = _attach_playing_descriptor(victim)
    try:
        out = do_mwhere(admin, "")
        assert "Zzinvplayerx" in out, f"no-arg mwhere must list CON_PLAYING descriptors, got: {out!r}"
    finally:
        _detach_descriptor(desc)
        _cleanup(admin, victim)


def test_reboot_announces_via_descriptor_list():
    # mirrors ROM src/act_wiz.c:2034-2048 — do_reboot announces through do_echo
    # (descriptor_list, CON_PLAYING) and walks descriptor_list to save. The old
    # code announced to the phantom registry.players, so no live player saw it.
    from mud.commands.imm_server import do_reboot

    admin = _imm("Zzinvrebooter", 3001)
    victim = create_test_character("Zzinvbystander", 3005)
    desc = _attach_playing_descriptor(victim)
    try:
        do_reboot(admin, "")
        assert any("Reboot by Zzinvrebooter" in m for m in victim.messages), (
            "reboot announce must reach CON_PLAYING descriptors"
        )
    finally:
        global_registry.merc_down = False
        _detach_descriptor(desc)
        _cleanup(admin, victim)


def test_memory_in_use_counts_live_npcs():
    # mirrors ROM src/db.c:3307 — do_memory "(in use)" prints mobile_count, the
    # number of live NPC mobiles. The old code printed len() of the phantom
    # registry.char_list, i.e. always 0 in production.
    from mud.commands.imm_search import do_memory

    admin = _imm("Zzinvcounter", 3001)
    mob = create_test_character("Zzinvmobile", 3005)
    mob.is_npc = True
    try:
        out = do_memory(admin, "")
        in_use_line = next(line for line in out.splitlines() if "(in use)" in line)
        assert int(in_use_line.split(")")[-1]) >= 1, f"(in use) must count live NPCs, got: {in_use_line!r}"
    finally:
        _cleanup(admin, mob)


def test_die_follower_releases_cross_room_followers():
    # mirrors ROM src/act_comm.c:1658-1680 — die_follower walks char_list, so a
    # follower in ANOTHER room is released too. player_config._die_follower
    # walked the phantom registry.char_list plus the same room only, leaving
    # remote followers pointing at a deleted character.
    from mud.commands.player_config import _die_follower

    leader = create_test_character("Zzinvleader", 3001)
    follower = create_test_character("Zzinvminion", 3005)
    follower.master = leader
    try:
        _die_follower(leader)
        assert follower.master is None, "cross-room follower must be released via character_registry walk"
    finally:
        _cleanup(leader, follower)
