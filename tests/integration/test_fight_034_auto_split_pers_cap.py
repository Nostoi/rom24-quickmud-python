"""FIGHT-034 — auto-split per-member line PERS + capitalization.

ROM src/act_comm.c:1946-1962 do_split delivers the per-member split line
via act("$n splits %d silver coins. Your share is %d silver.",
ch, NULL, gch, TO_VICT), so $n resolves through PERS(ch, gch) and
act_new caps the first letter (src/comm.c:2376). Python used a fixed
f-string with raw char.name — no can_see masking, no capitalize.

Two divergences:
  1. INV-029/ACT-CAP-001: the line is not capitalized (NPC splitters
     render "the orc splits..." where ROM caps "The orc splits...").
  2. INV-027/ACT-PERS-NAME-MASKING: $n bypasses PERS — invisible
     splitters leak their name instead of rendering "someone".
"""

from __future__ import annotations

from mud.commands.group_commands import do_split
from mud.models.character import Character, character_registry
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room
from mud.registry import room_registry
from mud.world.world_state import create_test_character


def _setup(vnum: int = 5500):
    test_room = Room(
        vnum=vnum,
        name="Test Room",
        description="A test room.",
        room_flags=0,
        sector_type=0,
    )
    test_room.people = []
    test_room.contents = []
    room_registry[vnum] = test_room
    return test_room


def _cleanup(vnum: int = 5500):
    room_registry.pop(vnum, None)
    character_registry.clear()


def _make_group(leader, *members):
    """Set up group membership so is_same_group returns True."""
    leader.leader = leader
    for m in members:
        m.leader = leader
        m.master = leader


class TestAutoSplitPersAndCap:
    """FIGHT-034 — do_split per-member line uses PERS + capitalize."""

    def test_do_split_npc_uses_short_descr(self):
        """NPC splitter renders short_descr, not name (PERS)."""
        # mirrors ROM src/act_comm.c:1959-1962 act(buf, ch, NULL, gch, TO_VICT)
        room = _setup(5500)
        try:
            npc = Character(name="guard", level=10, room=room)
            npc.is_npc = True
            npc.short_descr = "the city guard"
            npc.long_descr = "The city guard stands here."
            npc.position = Position.STANDING
            npc.silver = 100
            room.people.append(npc)
            character_registry.append(npc)

            pc = create_test_character("Player", 5500)
            pc.level = 5
            pc.silver = 0
            _make_group(npc, pc)

            do_split(npc, "60")
            joined = "\n".join(pc.messages).lower()
            assert "the city guard splits" in joined, f"NPC should render short_descr via PERS: {pc.messages!r}"
        finally:
            _cleanup(5500)

    def test_do_split_invisible_splitter_masks_name(self):
        """Invisible splitter renders 'Someone' via PERS + cap."""
        _setup(5501)
        try:
            splitter = create_test_character("Hider", 5501)
            splitter.level = 10
            splitter.silver = 100
            splitter.add_affect(AffectFlag.INVISIBLE)

            member = create_test_character("Bystander", 5501)
            member.level = 5
            member.silver = 0
            member.connection = None
            member.messages = []
            _make_group(splitter, member)

            do_split(splitter, "60")
            joined = "\n".join(member.messages).lower()
            assert "someone splits" in joined, f"PERS should mask invisible splitter: {member.messages!r}"
            assert "hider" not in joined, f"invisible splitter name leaked: {member.messages!r}"
        finally:
            _cleanup(5501)

    def test_do_split_silver_per_member_pers_and_cap(self):
        """do_split silver-only line: NPC renders short_descr + capitalize."""
        room = _setup(5502)
        try:
            splitter = Character(name="SplitterNPC", level=10, room=room)
            splitter.is_npc = True
            splitter.short_descr = "the old warrior"
            splitter.long_descr = "The old warrior stands here."
            splitter.position = Position.STANDING
            splitter.silver = 100
            room.people.append(splitter)
            character_registry.append(splitter)

            member = create_test_character("Pal", 5502)
            member.level = 5
            member.silver = 0
            member.connection = None
            member.messages = []
            _make_group(splitter, member)

            do_split(splitter, "100")
            joined = "\n".join(member.messages).lower()
            assert "the old warrior splits 100 silver" in joined, f"should render short_descr: {member.messages!r}"
            assert member.messages[0].startswith("The old warrior splits"), (
                f"first letter must be capitalized (INV-029): {member.messages!r}"
            )
        finally:
            _cleanup(5502)

    def test_do_split_gold_per_member_pers_and_cap(self):
        """do_split gold-only line: PERS + capitalize."""
        _setup(5503)
        try:
            splitter = create_test_character("Richie", 5503)
            splitter.level = 10
            splitter.gold = 50
            splitter.silver = 0

            member = create_test_character("Pal", 5503)
            member.level = 5
            member.gold = 0
            member.silver = 0
            member.connection = None
            member.messages = []
            _make_group(splitter, member)

            do_split(splitter, "0 50")
            joined = "\n".join(member.messages).lower()
            assert member.messages[0].startswith("Richie splits"), (
                f"first letter must be capitalized: {member.messages!r}"
            )
            assert "splits 50 gold" in joined, f"gold split message missing: {member.messages!r}"
        finally:
            _cleanup(5503)

    def test_do_split_mixed_per_member_pers_and_cap(self):
        """do_split mixed silver+gold line: PERS + capitalize."""
        _setup(5504)
        try:
            splitter = create_test_character("SplitMixed", 5504)
            splitter.level = 10
            splitter.silver = 300
            splitter.gold = 300

            member = create_test_character("Buddy", 5504)
            member.level = 5
            member.gold = 0
            member.silver = 0
            member.connection = None
            member.messages = []
            _make_group(splitter, member)

            do_split(splitter, "100 100")
            joined = "\n".join(member.messages).lower()
            assert "splits 100 silver and 100 gold" in joined, f"mixed message missing: {member.messages!r}"
            assert member.messages[0].startswith("SplitMixed splits"), (
                f"first letter must be capitalized: {member.messages!r}"
            )
        finally:
            _cleanup(5504)
