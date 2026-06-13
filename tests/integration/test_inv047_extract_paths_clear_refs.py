"""INV-047 (multi-path) — every extract path clears ROM's dangling target refs.

ROM has a single `extract_char` (`src/handler.c:2151-2157`) whose `char_list`
walk clears dangling `reply` pointers and the `mprog_target` quirk on EVERY
extraction. The Python port split extraction across several call sites
(`mud/mob_cmds.py:_extract_character`, the `do_quit`/link-dead leg in
`mud/game_loop.py:_auto_quit_character`, and the clean-disconnect teardown in
`mud/net/connection.py`). INV-047 originally landed the cleanup only inside
`_extract_character`; the PC quit / disconnect legs still leaked dangling
`reply` pointers — the same multi-path class INV-020 closed for
`nuke_pets`/`die_follower`.

This test exercises the link-dead `_auto_quit_character` leg (no `desc`, no
`connection` → synchronous extract) and asserts a mob whose `reply` pointed at
the quitter is cleared.
"""

from __future__ import annotations

import pytest

from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room


@pytest.fixture
def isolated_registry():
    saved = list(character_registry)
    character_registry.clear()
    yield character_registry
    character_registry[:] = saved


def test_link_dead_quit_clears_dangling_reply(isolated_registry) -> None:
    """ROM extract_char (handler.c:2153-2154) clears wch->reply == ch for every
    extracted char. The link-dead quit leg must do the same, not just
    _extract_character.
    """
    from mud import game_loop

    room = Room(vnum=9840, name="Quit ref-cleanup room")
    quitter = Character(name="Quitter", is_npc=False, position=Position.STANDING)
    quitter.desc = None
    quitter.connection = None
    room.add_character(quitter)
    isolated_registry.append(quitter)

    mob = Character(name="Watcher", is_npc=True, position=Position.STANDING)
    room.add_character(mob)
    isolated_registry.append(mob)
    mob.reply = quitter  # mob was going to reply to the quitter

    game_loop._auto_quit_character(quitter)

    assert quitter not in character_registry, "link-dead quit must extract the quitter"
    assert mob.reply is None, (
        "ROM extract_char clears wch->reply == ch on every extract path; the "
        "link-dead quit leg left a dangling reply pointer at the quitter."
    )


def test_link_dead_quit_clears_targeted_mprog_target(isolated_registry) -> None:
    """The mprog_target quirk (handler.c:2155-2156) must also fire on the quit
    leg: if the quitter targeted a mob, that mob's own mprog_target is cleared.
    """
    from mud import game_loop

    room = Room(vnum=9841, name="Quit mprog-cleanup room")
    quitter = Character(name="Quitter", is_npc=False, position=Position.STANDING)
    quitter.desc = None
    quitter.connection = None
    room.add_character(quitter)
    isolated_registry.append(quitter)

    target = Character(name="Remembered", is_npc=True, position=Position.STANDING)
    room.add_character(target)
    isolated_registry.append(target)

    quitter.mprog_target = target
    target.mprog_target = target

    game_loop._auto_quit_character(quitter)

    assert target.mprog_target is None, (
        "ROM extract_char clears wch->mprog_target when ch->mprog_target == wch; "
        "the quit leg must replicate the quirk on every extract path."
    )


def test_disconnect_cleanup_clears_dangling_reply(isolated_registry) -> None:
    """The clean-disconnect teardown (`_disconnect_extract_cleanup` in
    `mud/net/connection.py`, called from both the telnet and websocket
    finally-blocks) must also clear dangling `reply` pointers — same
    multi-path contract as INV-020's nuke_pets/die_follower legs.
    """
    from mud.net.connection import _disconnect_extract_cleanup

    room = Room(vnum=9842, name="Disconnect ref-cleanup room")
    leaver = Character(name="Leaver", is_npc=False, position=Position.STANDING)
    room.add_character(leaver)
    isolated_registry.append(leaver)

    mob = Character(name="DiscoWatcher", is_npc=True, position=Position.STANDING)
    room.add_character(mob)
    isolated_registry.append(mob)
    mob.reply = leaver

    _disconnect_extract_cleanup(leaver)

    assert mob.reply is None, (
        "ROM extract_char clears wch->reply == ch on every extract path; the "
        "disconnect cleanup leg left a dangling reply pointer at the leaver."
    )


def test_disconnect_cleanup_clears_targeted_mprog_target(isolated_registry) -> None:
    """The disconnect cleanup leg must also fire the mprog_target quirk
    (handler.c:2155-2156): a mob the leaver targeted has its own
    mprog_target cleared.
    """
    from mud.net.connection import _disconnect_extract_cleanup

    room = Room(vnum=9843, name="Disconnect mprog-cleanup room")
    leaver = Character(name="Leaver", is_npc=False, position=Position.STANDING)
    room.add_character(leaver)
    isolated_registry.append(leaver)

    target = Character(name="DiscoRemembered", is_npc=True, position=Position.STANDING)
    room.add_character(target)
    isolated_registry.append(target)

    leaver.mprog_target = target
    target.mprog_target = target

    _disconnect_extract_cleanup(leaver)

    assert target.mprog_target is None, (
        "ROM extract_char clears wch->mprog_target when ch->mprog_target == wch; "
        "the disconnect cleanup leg must replicate the quirk on every extract path."
    )
