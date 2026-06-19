"""Probe: do_group must notify victim and room per ROM.

ROM ``src/act_comm.c:1850-1854`` (add path):

    victim->leader = ch;
    act_new ("$N joins $n's group.", ch, NULL, victim, TO_NOTVICT, POS_RESTING);
    act_new ("You join $n's group.",  ch, NULL, victim, TO_VICT,   POS_SLEEPING);
    act_new ("$N joins your group.",  ch, NULL, victim, TO_CHAR,   POS_SLEEPING);

ROM ``src/act_comm.c:1840-1847`` (remove path):

    victim->leader = NULL;
    act_new ("$n removes $N from $s group.", ch, NULL, victim, TO_NOTVICT, ...);
    act_new ("$n removes you from $s group.", ch, NULL, victim, TO_VICT,   ...);
    act_new ("You remove $N from your group.", ch, NULL, victim, TO_CHAR,  ...);

Python ``mud/commands/group_commands.py:do_group`` returns only the
TO_CHAR string; the victim and onlookers receive nothing. Parallel
to the do_follow notify gap closed in 2.9.19.
"""

from __future__ import annotations

from mud.commands.dispatcher import process_command
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry


def _make_room(vnum: int = 9411) -> Room:
    room = Room(vnum=vnum, name="Group Room", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


def test_do_group_add_notifies_victim_and_room():
    """ROM src/act_comm.c:1850-1854 — victim and onlooker receive broadcasts on add."""
    snapshot = list(character_registry)
    character_registry.clear()
    try:
        room = _make_room()

        leader = Character(
            name="leader",
            is_npc=False,
            level=10,
            room=room,
            position=int(Position.STANDING),
        )
        leader.messages = []
        room.people.append(leader)
        character_registry.append(leader)

        victim = Character(
            name="victim",
            is_npc=False,
            level=10,
            room=room,
            position=int(Position.STANDING),
        )
        victim.messages = []
        victim.master = leader
        room.people.append(victim)
        character_registry.append(victim)

        onlooker = Character(
            name="onlooker",
            is_npc=False,
            level=10,
            room=room,
            position=int(Position.STANDING),
        )
        onlooker.messages = []
        room.people.append(onlooker)
        character_registry.append(onlooker)

        process_command(leader, "group victim")

        # ROM: victim receives "You join $n's group." (TO_VICT)
        joined_victim = "\n".join(victim.messages).lower()
        assert "join" in joined_victim and "group" in joined_victim, (
            f"victim must receive `You join $n's group.` "
            f"(ROM src/act_comm.c:1853); victim.messages = {victim.messages!r}"
        )

        # ROM: onlooker receives "$N joins $n's group." (TO_NOTVICT)
        joined_onlooker = "\n".join(onlooker.messages).lower()
        assert "joins" in joined_onlooker and "group" in joined_onlooker, (
            f"onlooker must receive `$N joins $n's group.` "
            f"(ROM src/act_comm.c:1851); onlooker.messages = {onlooker.messages!r}"
        )

        # State per ROM line 1850.
        assert victim.leader is leader
    finally:
        character_registry.clear()
        character_registry.extend(snapshot)


def test_do_group_display_includes_cross_room_members():
    """GROUP-003 — `group` display iterates the world char list (ROM char_list).

    ROM ``src/act_comm.c:1787`` shows every char where ``is_same_group(gch, ch)``
    by scanning the global ``char_list`` — group members in *other* rooms appear.
    Python scanned only ``room.people`` + a nonexistent ``leader.followers``, so a
    same-group member standing in a different room was silently dropped from the
    listing.
    """
    snapshot = list(character_registry)
    character_registry.clear()
    try:
        room_a = _make_room(9420)
        room_b = _make_room(9421)

        leader = Character(name="leader", is_npc=False, level=10, room=room_a, position=int(Position.STANDING))
        leader.messages = []
        room_a.people.append(leader)
        character_registry.append(leader)

        # Same group (shares leader pointer) but standing in a different room.
        faraway = Character(name="faraway", is_npc=False, level=8, room=room_b, position=int(Position.STANDING))
        faraway.messages = []
        faraway.master = leader
        faraway.leader = leader
        room_b.people.append(faraway)
        character_registry.append(faraway)

        listing = process_command(leader, "group") or ""

        assert "faraway" in listing.lower(), (
            f"cross-room group member must appear in `group` display "
            f"(ROM src/act_comm.c:1787 iterates char_list); got {listing!r}"
        )
    finally:
        character_registry.clear()
        character_registry.extend(snapshot)
        character_registry.extend(snapshot)
        room_registry.pop(9411, None)
