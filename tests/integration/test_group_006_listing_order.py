"""GROUP-006 / INV-045 — do_group lists group members NEWEST-first.

ROM head-inserts every new character into the global ``char_list``
(``src/db.c:2256`` create_mobile, ``src/nanny.c`` PC login:
``ch->next = char_list; char_list = ch``), so every walk of that list visits
the most-recently-created entity first. ``do_group`` (``src/act_comm.c:1787``)
walks ``char_list`` without reversing, so the displayed group roster is in
**reverse-creation** order.

Python's ``character_registry`` is append-order (oldest-first) — the REVERSE of
ROM — so ``do_group`` must iterate it reversed to match (the INV-045 contract).
The forward walk was an observable residual surfaced by the
``group_follow_cycle`` differential scenario: a charmed mob (created after the
PC) must list ABOVE the PC, exactly opposite to append order.
"""

from __future__ import annotations

from mud.commands.group_commands import do_group
from mud.models.character import Character, character_registry
from mud.models.constants import Position, Sex
from mud.models.room import Room
from mud.registry import room_registry


def _make_room(vnum: int = 9431) -> Room:
    room = Room(vnum=vnum, name="Order Room", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


def _make_char(name: str, room: Room) -> Character:
    ch = Character(name=name, is_npc=False, level=10, room=room, position=int(Position.STANDING))
    ch.messages = []
    ch.sex = Sex.MALE
    room.people.append(ch)
    character_registry.append(ch)
    return ch


def test_group_006_roster_is_newest_first():
    """ROM char_list head-insert => do_group lists the newer member first."""
    snapshot = list(character_registry)
    character_registry.clear()
    try:
        room = _make_room()
        leader = _make_char("Aolder", room)  # created first -> OLDEST
        member = _make_char("Znewer", room)  # created second -> NEWEST
        member.leader = leader
        leader.leader = None

        out = do_group(leader, "")
        lines = out.split("\n")
        # lines[0] is the "X's group:" header; member rows follow.
        member_rows = lines[1:]
        older_idx = next(i for i, ln in enumerate(member_rows) if "Aolder" in ln)
        newer_idx = next(i for i, ln in enumerate(member_rows) if "Znewer" in ln)

        # ROM newest-first: the later-created "Znewer" must precede "Aolder",
        # the opposite of character_registry append order.
        assert newer_idx < older_idx, (
            f"do_group must list group members newest-first (ROM char_list head-insert / INV-045); got order:\n{out}"
        )
    finally:
        character_registry.clear()
        character_registry.extend(snapshot)
        room_registry.pop(9431, None)
