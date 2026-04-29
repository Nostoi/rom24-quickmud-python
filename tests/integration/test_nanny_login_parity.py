"""ROM nanny.c login-flow parity tests.

Closes gaps from docs/parity/NANNY_C_AUDIT.md.

ROM C reference: src/nanny.c CON_READ_MOTD case (lines 742-819).
"""

from __future__ import annotations

import pytest

from mud.models.character import Character, PCData


@pytest.mark.p1
def test_login_finalization_invokes_reset_char():
    """NANNY-014 — reset_char(ch) must run on every login.

    ROM C: src/nanny.c:760
        ```c
        ch->next = char_list;
        char_list = ch;
        d->connected = CON_PLAYING;
        reset_char (ch);
        ```

    reset_char (handler.c:520-745) clears mod_stat[], hitroll, damroll,
    saving_throw, restores max_hit/max_mana/max_move from pcdata->perm_*,
    and re-applies equipment affects. ROM calls it on the very first line
    of CON_READ_MOTD's body so a returning character with corrupted
    transient state always lands in a clean state.

    Python's `reset_char` exists in mud/handler.py:1046 but the login
    pipeline in mud/net/connection.py:handle_connection never calls it.
    This test asserts the network layer exposes a login-finalization
    helper that invokes reset_char.
    """
    from mud.net.connection import apply_login_state_refresh

    pcdata = PCData()
    pcdata.perm_hit = 100
    pcdata.perm_mana = 80
    pcdata.perm_move = 60
    pcdata.true_sex = 1
    pcdata.last_level = 5

    char = Character(name="Tester", level=10)
    char.is_npc = False
    char.pcdata = pcdata
    # Simulate transient corruption that ROM's reset_char fixes:
    char.max_hit = 50
    char.max_mana = 40
    char.max_move = 30
    char.hitroll = 17
    char.damroll = 9
    char.saving_throw = -3
    char.mod_stat = [4, 0, -1, 2, 0]
    char.armor = [200, 200, 200, 200]

    apply_login_state_refresh(char)

    # mirrors ROM src/handler.c:600-616 — reset_char restores from perm_* and zeros transients
    assert char.max_hit == 100
    assert char.max_mana == 80
    assert char.max_move == 60
    assert char.hitroll == 0
    assert char.damroll == 0
    assert char.saving_throw == 0
    assert list(char.mod_stat) == [0, 0, 0, 0, 0]
    assert char.armor == [100, 100, 100, 100]


@pytest.mark.p1
def test_login_broadcasts_entry_to_room():
    """NANNY-007 — `act("$n has entered the game.", TO_ROOM)` on login.

    ROM C: src/nanny.c:804
        ```c
        act ("$n has entered the game.", ch, NULL, NULL, TO_ROOM);
        ```

    Every other player in the room should see "<Name> has entered the
    game." when a character finishes the login state machine. The actor
    themselves does not receive the message (TO_ROOM excludes ch).
    """
    from mud.models.room import Room
    from mud.net.connection import broadcast_entry_to_room

    room = Room(vnum=9001, name="Login Test Room", description="", room_flags=0, sector_type=0)
    room.people = []

    arriver = Character(name="Arriver", level=10)
    arriver.is_npc = False
    onlooker = Character(name="Onlooker", level=10)
    onlooker.is_npc = False
    bystander = Character(name="Bystander", level=10)
    bystander.is_npc = False

    for occupant in (arriver, onlooker, bystander):
        room.people.append(occupant)
        occupant.room = room

    broadcast_entry_to_room(arriver)

    # mirrors ROM src/nanny.c:804 — TO_ROOM broadcast excludes the actor
    assert any("Arriver has entered the game." in m for m in onlooker.messages)
    assert any("Arriver has entered the game." in m for m in bystander.messages)
    assert all("entered the game" not in m for m in arriver.messages)


@pytest.mark.p1
def test_login_state_refresh_is_a_noop_for_npcs():
    """reset_char early-returns on NPCs (handler.py:1067-1069). The login helper
    must preserve that behaviour — NPCs never traverse nanny.c login states.
    """
    from mud.net.connection import apply_login_state_refresh

    npc = Character(name="MobGuard", level=10)
    npc.is_npc = True
    npc.max_hit = 50
    npc.hitroll = 7
    npc.mod_stat = [3, 0, 0, 0, 0]

    apply_login_state_refresh(npc)

    assert npc.max_hit == 50
    assert npc.hitroll == 7
    assert list(npc.mod_stat) == [3, 0, 0, 0, 0]
