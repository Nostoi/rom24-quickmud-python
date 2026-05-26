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
        room_registry.pop(9411, None)
