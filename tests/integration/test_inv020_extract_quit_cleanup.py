"""INV-020 expansion — every PC-extract path must call nuke_pets +
die_follower.

ROM contract (``src/handler.c:2117-2122 extract_char``)::

    nuke_pets (ch);
    ch->pet = NULL;
    if (fPull)
        die_follower (ch);
    stop_fighting (ch, TRUE);

``extract_char`` is the canonical "remove a character from the world"
chokepoint. Every PC-extract trigger funnels through it: ``do_quit``
(``src/act_comm.c:1499``), ``do_pull`` immortal commands,
``raw_kill`` for PCs (``src/fight.c:1718`` — covered by INV-020's
original raw_kill enforcement). Pre-expansion, INV-020 only locked
the raw_kill leg. Python's quit paths (``mud/commands/session.py:do_quit``
→ disconnect cleanup in ``mud/net/connection.py`` finally-block, plus
``mud/game_loop.py:_auto_quit_character`` for void-quit) skipped both
cleanups, leaking:

- **Pet-cleanup miss**: a player quits with a charmed pet — the pet
  stays in the world with ``pet.master`` pointing at the now-extracted
  player. The pet keeps ``AFF_CHARM`` set even though the master is
  gone, and the master's prior ``pet`` reference is dangling on a
  character that may be GC'd or re-loaded under a new identity.
- **Follower-cleanup miss**: every other character with
  ``fch.master == quitter`` or ``fch.leader == quitter`` keeps a
  dangling pointer to the extracted Character. ``is_same_group``
  then false-positives matches via the stale leader pointer, the
  same dangling-pointer hazard INV-020 closed at the raw_kill leg.

This test pins the void-quit path (``_auto_quit_character`` in
``mud/game_loop.py``). The disconnect-cleanup path (``connection.py``
finally-block) is intentionally split into a separate gap-closer so
the helper-extraction refactor lands cleanly.

Two sub-contracts tested independently per quit path:
- ``test_void_quit_nukes_pets`` / ``test_disconnect_nukes_pets`` — pet-cleanup leg
- ``test_void_quit_calls_die_follower`` / ``test_disconnect_calls_die_follower`` — follower-cleanup leg
"""

from __future__ import annotations

import pytest

from mud.game_loop import _auto_quit_character
from mud.models.character import Character, character_registry
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room
from mud.net.connection import _disconnect_extract_cleanup


@pytest.fixture(autouse=True)
def _cleanup():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)


def test_void_quit_nukes_pets() -> None:
    """``_auto_quit_character`` must call ``_nuke_pets`` so a charmed
    pet does not survive past its master's quit. Mirrors ROM
    ``src/handler.c:2117 extract_char → nuke_pets``.
    """
    room = Room(vnum=99950, name="Quit pet probe")
    master = Character(name="Master", is_npc=False, position=Position.STANDING)
    pet = Character(name="Imp", is_npc=True, position=Position.STANDING)
    pet.affected_by = int(AffectFlag.CHARM)
    master.pet = pet
    pet.master = master
    room.add_character(master)
    room.add_character(pet)
    character_registry.extend([master, pet])

    _auto_quit_character(master)

    assert pet not in character_registry, (
        "ROM src/handler.c:2117 nuke_pets → extract_char(pet, TRUE) "
        "removes the pet from char_list when the master extracts. "
        "Python void-quit must do the same; the pet remained in "
        "character_registry."
    )
    assert master.pet is None, "ROM src/handler.c:2118 sets ch->pet = NULL after nuke_pets."


def test_void_quit_calls_die_follower() -> None:
    """``_auto_quit_character`` must call ``die_follower`` so other
    characters' ``master``/``leader`` pointers do not dangle at the
    extracted quitter. Mirrors ROM ``src/handler.c:2120-2122 ``.

    Specifically: any ``fch.leader is quitter`` must reset to
    ``fch.leader = fch`` (NOT None — ``is_same_group`` would still
    equate two former members via the dangling pointer).
    """
    room = Room(vnum=99951, name="Quit follower probe")
    leader = Character(name="Leader", is_npc=False, position=Position.STANDING)
    grouped = Character(name="Grouped", is_npc=False, position=Position.STANDING)
    follower = Character(name="Follower", is_npc=False, position=Position.STANDING)

    grouped.leader = leader
    follower.master = leader

    room.add_character(leader)
    room.add_character(grouped)
    room.add_character(follower)
    character_registry.extend([leader, grouped, follower])

    _auto_quit_character(leader)

    assert grouped.leader is grouped, (
        "ROM src/act_comm.c:1675-1676 — die_follower resets leader to "
        "fch (NOT None) so is_same_group does not false-positive via a "
        f"dangling pointer at the extracted leader. Got leader={grouped.leader!r}"
    )
    assert follower.master is None, (
        "ROM src/act_comm.c:1673-1674 — die_follower calls stop_follower "
        "for every fch.master == ch, clearing the master pointer. "
        f"Got master={follower.master!r}"
    )


def test_disconnect_nukes_pets() -> None:
    """``_disconnect_extract_cleanup`` (called from the telnet+websocket
    connection ``finally`` blocks on clean disconnect) must call
    ``_nuke_pets``. Same contract as void-quit; different trigger
    (socket close vs ``do_quit`` command).
    """
    room = Room(vnum=99952, name="Disconnect pet probe")
    master = Character(name="DiscoMaster", is_npc=False, position=Position.STANDING)
    pet = Character(name="DiscoImp", is_npc=True, position=Position.STANDING)
    pet.affected_by = int(AffectFlag.CHARM)
    master.pet = pet
    pet.master = master
    room.add_character(master)
    room.add_character(pet)
    character_registry.extend([master, pet])

    _disconnect_extract_cleanup(master)

    assert pet not in character_registry, (
        "ROM src/handler.c:2117 nuke_pets → extract_char(pet, TRUE). "
        "Disconnect path must do the same; pet remained in registry."
    )
    assert master.pet is None, "ROM src/handler.c:2118 sets ch->pet = NULL after nuke_pets."


def test_disconnect_calls_die_follower() -> None:
    """``_disconnect_extract_cleanup`` must call ``die_follower`` so a
    grouped follower's ``leader`` does not dangle at the disconnected
    Character (which gets dropped from ``character_registry`` in the
    same ``finally`` block).
    """
    room = Room(vnum=99953, name="Disconnect follower probe")
    leader = Character(name="DiscoLeader", is_npc=False, position=Position.STANDING)
    grouped = Character(name="DiscoGrouped", is_npc=False, position=Position.STANDING)
    follower = Character(name="DiscoFollower", is_npc=False, position=Position.STANDING)

    grouped.leader = leader
    follower.master = leader

    room.add_character(leader)
    room.add_character(grouped)
    room.add_character(follower)
    character_registry.extend([leader, grouped, follower])

    _disconnect_extract_cleanup(leader)

    assert grouped.leader is grouped, (
        "ROM src/act_comm.c:1675-1676 — die_follower resets leader to fch "
        "(NOT None). Disconnect path must invoke this. "
        f"Got leader={grouped.leader!r}"
    )
    assert follower.master is None, (
        "ROM src/act_comm.c:1673-1674 — die_follower calls stop_follower "
        f"for every fch.master == ch. Got master={follower.master!r}"
    )


def test_void_quit_stops_attackers_fighting() -> None:
    """``_auto_quit_character`` (link-dead extract leg) must call
    ``stop_fighting(ch, both=True)`` — step (iv) of ROM's extract_char
    cleanup chain (``src/handler.c:2121``). Without it, a mob still
    fighting the extracted PC keeps ``fighting`` pointing at a character
    that has been removed from the registry/room — a dangling-pointer
    hazard the next combat tick would dereference.
    """
    room = Room(vnum=99954, name="Quit fight probe")
    quitter = Character(name="Quitter", is_npc=False, position=Position.FIGHTING)
    quitter.desc = None
    quitter.connection = None
    attacker = Character(name="Attacker", is_npc=True, position=Position.FIGHTING)
    attacker.default_pos = int(Position.STANDING)

    room.add_character(quitter)
    room.add_character(attacker)
    character_registry.extend([quitter, attacker])

    quitter.fighting = attacker
    attacker.fighting = quitter

    _auto_quit_character(quitter)

    assert attacker.fighting is None, (
        "ROM src/handler.c:2121 — extract_char calls stop_fighting(ch, TRUE); "
        "fBoth clears every fch->fighting == ch. The link-dead quit leg left "
        f"the attacker fighting an extracted char. Got fighting={attacker.fighting!r}"
    )


def test_disconnect_stops_attackers_fighting() -> None:
    """The clean-disconnect teardown (``_disconnect_extract_cleanup``)
    must also run ``stop_fighting(ch, both=True)`` so a mob fighting the
    disconnected PC does not keep a dangling ``fighting`` pointer. Same
    step (iv) of the extract_char chain, different trigger.
    """
    room = Room(vnum=99955, name="Disconnect fight probe")
    leaver = Character(name="Leaver", is_npc=False, position=Position.FIGHTING)
    attacker = Character(name="DiscoAttacker", is_npc=True, position=Position.FIGHTING)
    attacker.default_pos = int(Position.STANDING)

    room.add_character(leaver)
    room.add_character(attacker)
    character_registry.extend([leaver, attacker])

    leaver.fighting = attacker
    attacker.fighting = leaver

    _disconnect_extract_cleanup(leaver)

    assert attacker.fighting is None, (
        "ROM src/handler.c:2121 — extract_char calls stop_fighting(ch, TRUE). "
        "The disconnect cleanup leg left the attacker fighting an extracted "
        f"char. Got fighting={attacker.fighting!r}"
    )
