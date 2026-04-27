"""ROM act_comm.c parity gap regression tests.

Covers EMOTE-001..002, PMOTE-001..003, COLOUR-001..004, SPLIT-001..003,
and POSE-001..002 from ``docs/parity/ACT_COMM_C_AUDIT.md``.
"""
from __future__ import annotations

import pytest

from mud.commands.auto_settings import do_colour
from mud.commands.communication import do_emote, do_pose
from mud.commands.group_commands import do_split
from mud.commands.imm_emote import do_pmote
from mud.models.character import Character, character_registry
from mud.models.constants import AffectFlag, CommFlag, PlayerFlag, Position
from mud.registry import room_registry
from mud.world import initialize_world


@pytest.fixture(scope="module", autouse=True)
def _setup_world():
    initialize_world("area/area.lst")
    yield


@pytest.fixture
def room():
    return room_registry.get(3001)


def _make_pc(name: str, room, *, level: int = 10, ch_class: int = 0) -> Character:
    char = Character(
        name=name,
        short_descr=name,
        is_npc=False,
        level=level,
        position=Position.STANDING,
        room=room,
        comm=0,
    )
    char.ch_class = ch_class
    char.desc = object()
    char.silver = 0
    char.gold = 0
    char.messages = []
    room.add_character(char)
    character_registry.append(char)
    return char


@pytest.fixture
def alice(room):
    char = _make_pc("Alice", room)
    yield char
    if char in room.people:
        room.people.remove(char)
    if char in character_registry:
        character_registry.remove(char)


@pytest.fixture
def bob(room):
    char = _make_pc("Bob", room)
    yield char
    if char in room.people:
        room.people.remove(char)
    if char in character_registry:
        character_registry.remove(char)


# -----------------------------------------------------------------------------
# EMOTE-001 / EMOTE-002: COMM_NOEMOTE check + first-char validation
# -----------------------------------------------------------------------------

class TestEmoteGaps:
    def test_emote_blocked_by_noemote_flag(self, alice):
        alice.comm = int(CommFlag.NOEMOTE)
        result = do_emote(alice, "smiles")
        assert result == "You can't show your emotions."

    def test_emote_npc_bypasses_noemote_flag(self, alice):
        alice.is_npc = True
        alice.comm = int(CommFlag.NOEMOTE)
        result = do_emote(alice, "smiles")
        assert "smiles" in result

    def test_emote_rejects_non_alpha_first_char(self, alice):
        result = do_emote(alice, ",{ broken")
        assert result == "Moron!"

    def test_emote_rejects_leading_whitespace(self, alice):
        result = do_emote(alice, " leadingspace")
        assert result == "Moron!"


# -----------------------------------------------------------------------------
# PMOTE-001 / PMOTE-002 / PMOTE-003: pronoun substitution faithfulness
# -----------------------------------------------------------------------------

class TestPmoteGaps:
    def test_pmote_blocked_by_noemote_flag(self, alice):
        alice.comm = int(CommFlag.NOEMOTE)
        assert do_pmote(alice, "waves at Bob") == "You can't show your emotions."

    def test_pmote_rejects_non_alpha_first_char(self, alice):
        assert do_pmote(alice, ",broken") == "Moron!"

    def test_pmote_substitutes_viewer_name_with_you(self, alice, bob):
        bob.output_buffer = []
        do_pmote(alice, "smiles at Bob.")
        # Bob (the viewer) should see "Bob" rewritten to "you".
        assert "Alice smiles at you." in bob.output_buffer

    def test_pmote_handles_possessive_apostrophe(self, alice, bob):
        bob.output_buffer = []
        do_pmote(alice, "grabs Bob's cloak.")
        # ROM rewrites "Bob's" -> "your" (you + 'r).
        assert "Alice grabs your cloak." in bob.output_buffer

    def test_pmote_absorbs_trailing_plural_s(self, alice, bob):
        bob.output_buffer = []
        do_pmote(alice, "looks at Bobs over there.")
        # ROM: name + 's' (plural) drops the s; "Bobs" -> "you".
        assert "Alice looks at you over there." in bob.output_buffer


# -----------------------------------------------------------------------------
# COLOUR-001..004: ROM colour menu/toggle/default/all/per-field
# -----------------------------------------------------------------------------

class TestColourGaps:
    def test_colour_no_arg_toggles_on(self, alice):
        alice.act = 0
        out = do_colour(alice, "")
        assert int(alice.act) & int(PlayerFlag.COLOUR)
        assert "ColoUr is now ON" in out

    def test_colour_no_arg_toggles_off(self, alice):
        alice.act = int(PlayerFlag.COLOUR)
        out = do_colour(alice, "")
        assert not (int(alice.act) & int(PlayerFlag.COLOUR))
        assert "OFF" in out

    def test_colour_npc_blocked(self, alice):
        alice.is_npc = True
        out = do_colour(alice, "")
        assert "Way Moron" in out

    def test_colour_default_clears_overrides(self, alice):
        from mud.models.character import PCData

        alice.pcdata = PCData()
        alice.pcdata.colour = {"text": "{R"}
        out = do_colour(alice, "default")
        assert "default values" in out
        assert alice.pcdata.colour == {}

    def test_colour_all_sets_every_field(self, alice):
        from mud.models.character import PCData
        from mud.commands.auto_settings import _COLOUR_FIELDS

        alice.pcdata = PCData()
        out = do_colour(alice, "all {R")
        assert out == "New Colour Parameter Set."
        for field in _COLOUR_FIELDS:
            assert alice.pcdata.colour[field] == "{R"

    def test_colour_per_field_set(self, alice):
        from mud.models.character import PCData

        alice.pcdata = PCData()
        out = do_colour(alice, "tell {Y")
        assert out == "New Colour Parameter Set."
        assert alice.pcdata.colour["tell"] == "{Y"

    def test_colour_unknown_field_rejected(self, alice):
        from mud.models.character import PCData

        alice.pcdata = PCData()
        out = do_colour(alice, "bogus {R")
        assert "Unrecognised" in out


# -----------------------------------------------------------------------------
# SPLIT-001 / SPLIT-002 / SPLIT-003: ROM dual silver+gold split
# -----------------------------------------------------------------------------

class TestSplitGaps:
    def _setup_group(self, alice, bob):
        # Group bob to alice (alice = leader).
        bob.leader = alice
        alice.leader = None

    def test_split_dual_silver_and_gold_simultaneously(self, alice, bob):
        self._setup_group(alice, bob)
        alice.silver = 100
        alice.gold = 50
        bob.silver = 0
        bob.gold = 0

        result = do_split(alice, "100 50")

        # 100 silver / 2 = 50 each, 50 gold / 2 = 25 each
        assert alice.silver == 50, alice.silver
        assert alice.gold == 25, alice.gold
        assert bob.silver == 50, bob.silver
        assert bob.gold == 25, bob.gold
        assert "100 silver" in result
        assert "50 gold" in result

    def test_split_negative_amount_rejected(self, alice, bob):
        self._setup_group(alice, bob)
        alice.silver = 100
        result = do_split(alice, "-5")
        assert result == "Your group wouldn't like that."

    def test_split_zero_zero_rejected(self, alice, bob):
        self._setup_group(alice, bob)
        result = do_split(alice, "0 0")
        assert result == "You hand out zero coins, but no one notices."

    def test_split_insufficient_funds(self, alice, bob):
        self._setup_group(alice, bob)
        alice.silver = 1
        alice.gold = 0
        result = do_split(alice, "100 0")
        assert result == "You don't have that much to split."

    def test_split_solo_keeps_all(self, alice):
        alice.silver = 100
        result = do_split(alice, "50")
        assert result == "Just keep it all."
        assert alice.silver == 100

    def test_split_cheapskate_zero_share(self, alice, bob):
        self._setup_group(alice, bob)
        alice.silver = 1
        alice.gold = 0
        # 1 silver / 2 members = share=0 -> cheapskate.
        result = do_split(alice, "1")
        assert result == "Don't even bother, cheapskate."

    def test_split_silver_extra_goes_to_actor(self, alice, bob):
        self._setup_group(alice, bob)
        alice.silver = 11
        alice.gold = 0
        do_split(alice, "11")
        # 11 / 2 -> share=5, extra=1; actor keeps share+extra=6, bob gets 5.
        assert alice.silver == 6
        assert bob.silver == 5

    def test_split_legacy_silver_keyword_still_works(self, alice, bob):
        self._setup_group(alice, bob)
        alice.silver = 100
        do_split(alice, "100 silver")
        assert bob.silver == 50
        assert alice.silver == 50

    def test_split_legacy_gold_keyword_routes_to_gold(self, alice, bob):
        self._setup_group(alice, bob)
        alice.gold = 50
        do_split(alice, "50 gold")
        assert bob.gold == 25
        assert alice.gold == 25


# -----------------------------------------------------------------------------
# POSE-001 / POSE-002: pose_table by class+level
# -----------------------------------------------------------------------------

class TestPoseGaps:
    def test_pose_npc_returns_empty(self, alice):
        alice.is_npc = True
        assert do_pose(alice, "") == ""

    def test_pose_uses_class_specific_table(self, alice):
        from mud.utils.poses import POSE_TABLE

        alice.is_npc = False
        alice.level = 0
        alice.ch_class = 3  # warrior

        # With level=0, only pose_table[0] is reachable.
        result = do_pose(alice, "")
        assert result == POSE_TABLE[0][2 * 3 + 0]  # warrior TO_CHAR row 0
