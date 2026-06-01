"""Integration tests for do_recall and do_train commands (act_move.c).

Tests complete workflows for recall and training with ROM 2.4b6 parity.

ROM Parity:
- src/act_move.c lines 1563-1628 (do_recall)
- src/act_move.c lines 1632-1799 (do_train)
"""

from __future__ import annotations

import pytest

from mud.commands.advancement import do_train
from mud.commands.session import do_recall
from mud.models.character import Character, PCData
from mud.models.constants import ROOM_VNUM_TEMPLE, AffectFlag, Position, RoomFlag
from mud.models.room import Room


@pytest.fixture
def recall_test_setup():
    """Create test environment for recall testing"""
    from mud.registry import room_registry

    temple = Room(vnum=ROOM_VNUM_TEMPLE, name="Temple", description="The temple of Mid", room_flags=0, sector_type=0)
    other_room = Room(vnum=8001, name="Other Room", description="Some other room.", room_flags=0, sector_type=0)
    no_recall_room = Room(
        vnum=8002,
        name="No Recall Room",
        description="No recall room.",
        room_flags=int(RoomFlag.ROOM_NO_RECALL),
        sector_type=0,
    )

    temple.people = []
    temple.contents = []
    other_room.people = []
    other_room.contents = []
    no_recall_room.people = []
    no_recall_room.contents = []

    room_registry[ROOM_VNUM_TEMPLE] = temple
    room_registry[8001] = other_room
    room_registry[8002] = no_recall_room

    char = Character(
        name="TestChar",
        level=10,
        room=other_room,
        is_npc=False,
        hit=100,
        max_hit=100,
        move=100,
        max_move=100,
        position=Position.STANDING,
    )
    char.pcdata = PCData()
    char.pcdata.learned = {"recall": 75}
    other_room.people.append(char)

    yield char, temple, other_room, no_recall_room

    room_registry.pop(ROOM_VNUM_TEMPLE, None)
    room_registry.pop(8001, None)
    room_registry.pop(8002, None)


@pytest.fixture
def train_test_setup():
    """Create test environment for train testing"""
    from mud.registry import room_registry

    room = Room(vnum=8010, name="Training Room", description="A training room.", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []

    room_registry[8010] = room

    char = Character(
        name="TestChar", level=10, room=room, is_npc=False, hit=100, max_hit=100, position=Position.STANDING
    )
    char.pcdata = PCData()
    char.train = 5
    char.ch_class = 0
    room.people.append(char)

    # ROM do_train (src/act_move.c:1643-1656) requires an ACT_TRAIN NPC in the
    # room (TRAIN-003); place one so the trainer-presence gate passes.
    from mud.models.constants import ActFlag

    trainer = Character(name="adept", short_descr="an adept", is_npc=True, act=int(ActFlag.TRAIN), room=room)
    room.people.append(trainer)

    yield char, room

    room_registry.pop(8010, None)


def test_recall_moves_to_temple(recall_test_setup):
    """Test that recall moves character to temple

    ROM Parity: src/act_move.c lines 1563-1628 (do_recall basic functionality)
    """
    char, temple, other_room, no_recall_room = recall_test_setup

    assert char.room == other_room, "Should start in other room"

    result = do_recall(char, "")

    assert char.room == temple, "Should be moved to temple after recall"
    assert char in temple.people, "Character should be in temple's people list"
    assert char not in other_room.people, "Character should not be in other room's people list"


def test_recall_already_in_temple_does_nothing(recall_test_setup):
    """Test that recall in temple does nothing

    ROM Parity: src/act_move.c lines 1583-1584 (already in temple check)
    """
    char, temple, other_room, no_recall_room = recall_test_setup

    char.room = temple
    temple.people.append(char)

    result = do_recall(char, "")

    assert char.room == temple, "Should still be in temple"
    assert result == "", "Should return empty string when already in temple"


def test_recall_from_no_recall_room_fails(recall_test_setup):
    """Test that recall fails in NO_RECALL rooms

    ROM Parity: src/act_move.c lines 1586-1591 (ROOM_NO_RECALL check)
    """
    char, temple, other_room, no_recall_room = recall_test_setup

    char.room = no_recall_room
    no_recall_room.people.append(char)

    result = do_recall(char, "")

    assert char.room == no_recall_room, "Should still be in no recall room"
    assert "mota" in result.lower() or "forsaken" in result.lower(), "Should mention Mota forsaken you"


def test_recall_halves_movement(recall_test_setup):
    """Test that recall halves current movement

    ROM Parity: src/act_move.c line 1617 (ch->move /= 2)
    """
    char, temple, other_room, no_recall_room = recall_test_setup

    initial_move = char.move

    result = do_recall(char, "")

    assert char.move == initial_move // 2, f"Movement should be halved: {initial_move} -> {char.move}"


def test_recall_npc_blocked(recall_test_setup):
    """Test that NPCs cannot recall

    ROM Parity: src/act_move.c lines 1569-1573 (NPC check)
    """
    char, temple, other_room, no_recall_room = recall_test_setup

    char.is_npc = True
    initial_room = char.room

    result = do_recall(char, "")

    assert char.room == initial_room, "NPC should not move"
    assert result == "", "Should return empty string for NPCs"


def test_train_hp_increases_stats(train_test_setup):
    """Test that training HP increases perm_hit, max_hit, and current hit

    ROM Parity: src/act_move.c lines 1747-1762 (HP training)
    """
    char, room = train_test_setup

    initial_train = char.train
    initial_max_hit = char.max_hit
    initial_hit = char.hit

    result = do_train(char, "hp")

    assert char.train == initial_train - 1, "Training sessions should decrease by 1"
    assert char.max_hit == initial_max_hit + 10, "Max HP should increase by 10"
    assert char.hit == initial_hit + 10, "Current HP should increase by 10"
    assert char.pcdata.perm_hit == 10, "Permanent HP should increase by 10"
    assert "durability" in result.lower(), "Should mention durability increases"


def test_train_mana_increases_stats(train_test_setup):
    """Test that training mana increases perm_mana, max_mana, and current mana

    ROM Parity: src/act_move.c lines 1764-1779 (mana training)
    """
    char, room = train_test_setup

    initial_train = char.train
    initial_max_mana = char.max_mana
    initial_mana = char.mana

    result = do_train(char, "mana")

    assert char.train == initial_train - 1, "Training sessions should decrease by 1"
    assert char.max_mana == initial_max_mana + 10, "Max mana should increase by 10"
    assert char.mana == initial_mana + 10, "Current mana should increase by 10"
    assert char.pcdata.perm_mana == 10, "Permanent mana should increase by 10"
    assert "power" in result.lower(), "Should mention power increases"


def test_train_str_increases_stat(train_test_setup):
    """Test that training str increases permanent strength

    ROM Parity: src/act_move.c lines 1781-1799 (stat training)
    """
    char, room = train_test_setup

    char.perm_stat = [13, 13, 13, 13, 13]
    initial_train = char.train
    initial_str = char.perm_stat[0]

    cost = 1

    result = do_train(char, "str")

    assert char.train == initial_train - cost, "Training sessions should decrease by cost"
    assert char.perm_stat[0] == initial_str + 1, "Permanent STR should increase by 1"
    assert "strength" in result.lower(), "Should mention strength increases"


def test_train_int_increases_stat(train_test_setup):
    """Test that training int increases permanent intelligence

    ROM Parity: src/act_move.c lines 1781-1799 (stat training)
    """
    char, room = train_test_setup

    char.perm_stat = [13, 13, 13, 13, 13]
    initial_train = char.train
    initial_int = char.perm_stat[1]

    # TRAIN-002 — ROM src/act_move.c do_train charges cost=1 for EVERY stat,
    # including non-prime ones (INT is non-prime for a warrior). The previous
    # cost=2 here asserted a QuickMUD divergence, not ROM behavior.
    cost = 1

    result = do_train(char, "int")

    assert char.train == initial_train - cost, "Training sessions should decrease by cost"
    assert char.perm_stat[1] == initial_int + 1, "Permanent INT should increase by 1"
    assert "intelligence" in result.lower(), "Should mention intelligence increases"


def test_train_shows_sessions_count(train_test_setup):
    """Test that train with no args shows training sessions

    ROM Parity: src/act_move.c lines 1658-1663 (no argument case)
    """
    char, room = train_test_setup

    char.train = 5

    result = do_train(char, "")

    assert "5" in result, "Should show number of training sessions"
    assert "train" in result.lower(), "Should mention training sessions"


def test_train_no_arg_falls_through_to_listing(train_test_setup):
    """Bare `train` shows the session count AND the trainable-stat listing.

    ROM `do_train` (src/act_move.c:1658-1663) prints "You have %d training
    sessions." then sets `argument = "foo"` and falls through; "foo" matches no
    stat/hp/mana so it lands in the listing branch (`:1713`), so the player also
    sees "You can train: ...". Python early-returned just the session count.
    (TRAIN-005)
    """
    char, room = train_test_setup

    char.train = 5

    result = do_train(char, "")

    # Both ROM outputs must appear: the session count and the listing branch.
    assert "5 training sessions" in result, result
    assert "You can train:" in result, result
    # The fixture char has trainable stats below max, so at least one stat shows.
    assert "hp mana" in result, result


def test_train_insufficient_sessions_fails(train_test_setup):
    """Test that training without enough sessions fails

    ROM Parity: src/act_move.c lines 1672-1676 (insufficient sessions check)
    """
    char, room = train_test_setup

    char.train = 0

    result = do_train(char, "hp")

    assert char.max_hit == 100, "Max HP should not change"
    assert "don't have enough" in result.lower() or "not enough" in result.lower(), "Should mention not enough sessions"


def test_train_npc_blocked(train_test_setup):
    """Test that NPCs cannot train

    ROM Parity: src/act_move.c lines 1640-1641 (NPC check)
    """
    char, room = train_test_setup

    char.is_npc = True
    initial_train = char.train
    initial_max_hit = char.max_hit

    result = do_train(char, "hp")

    assert char.train == initial_train, "NPC training sessions should not change"
    assert char.max_hit == initial_max_hit, "NPC max HP should not change"
    assert result == "", "Should return empty string for NPCs"


def test_train_nonprime_stat_costs_one_session(train_test_setup):
    """TRAIN-002 — training a stat costs exactly 1 session, never 2.

    ROM src/act_move.c do_train sets `cost = 1;` once before the stat
    dispatch chain. Each branch's `if (class_table[ch->class].attr_prime
    == STAT_X) cost = 1;` is a no-op (there is no `else cost = 2;`), so a
    NON-prime stat costs the same single session as a prime stat. Python
    had invented `cost = 1 if prime else 2`, charging 2 for non-prime
    stats. The fixture char is class 0 (WARRIOR, prime STR), so CON is
    non-prime and must still cost exactly 1.
    """
    char, room = train_test_setup
    # All stats below get_max_train (22) so the train succeeds.
    char.perm_stat = [15, 15, 15, 15, 15]
    char.train = 5

    # mirrors ROM src/act_move.c do_train — cost is 1 for every stat
    result = do_train(char, "con")  # CON: non-prime for a warrior

    assert char.perm_stat[4] == 16, "constitution should increase by 1 (STAT_CON)"
    assert char.train == 4, (
        "non-prime stat training must cost exactly 1 session; ROM do_train "
        "never sets cost=2"
    )
    assert "constitution increases" in result.lower()


def test_train_without_trainer_in_room_fails():
    """TRAIN-003 — do_train requires an ACT_TRAIN mob present in the room.

    ROM src/act_move.c:1643-1656 loops `ch->in_room->people` for an
    `IS_NPC(mob) && IS_SET(mob->act, ACT_TRAIN)` mob; if none is found it
    sends "You can't do that here." and returns BEFORE any stat/session
    handling. QuickMUD had this check commented out (stale "no trainer
    mobs exist yet" TODO), letting a player train from any room.
    """
    from mud.models.character import Character, PCData
    from mud.models.constants import Position
    from mud.models.room import Room

    room = Room(vnum=8011, name="No Trainer Here", description="An empty room.", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    char = Character(
        name="Lonely", level=10, room=room, is_npc=False, train=5, position=Position.STANDING
    )
    char.pcdata = PCData()
    room.people.append(char)

    # mirrors ROM src/act_move.c:1652-1655 — no ACT_TRAIN mob in the room
    assert do_train(char, "hp") == "You can't do that here."
    # the trainer gate precedes the no-arg session display too (ROM order)
    assert do_train(char, "") == "You can't do that here."


def test_train_caps_human_nonprime_stat_at_race_max(train_test_setup):
    """TRAIN-004 — stat cap is race/class-specific, not a hardcoded 22.

    ROM src/act_move.c:1781 gates on `get_max_train(ch, stat)`
    (src/handler.c:876): `pc_race_table[race].max_stats[stat]`, +3 for a
    human's prime stat / +2 otherwise, clamped to 25. A human's max_stats
    are all 18, so a human mage's STR (non-prime) caps at 18 — the old
    hardcoded `max_stat = 22` over-caps it.
    """
    from mud.models.races import race_lookup

    char, _room = train_test_setup
    char.race = race_lookup("human")
    char.ch_class = 0  # mage — prime stat is INT, so STR is non-prime
    char.perm_stat = [18, 13, 13, 13, 13]  # STR already at the human race max

    # mirrors ROM src/handler.c:876 get_max_train — human non-prime cap is 18
    result = do_train(char, "str")
    assert result == "Your strength is already at maximum."
    assert char.perm_stat[0] == 18, "STR must not exceed the race max of 18"


def test_train_caps_dwarf_dex_at_race_max(train_test_setup):
    """TRAIN-004 — non-uniform race exercises the per-stat max_stats index.

    Dwarf max_stats are (20, 16, 19, 14, 21); DEX (STAT_DEX index 3) caps
    at 14. The old hardcoded 22 over-caps it, and a wrong stat→index
    mapping would read a different ceiling.
    """
    from mud.models.races import race_lookup

    char, _room = train_test_setup
    char.race = race_lookup("dwarf")
    char.ch_class = 3  # warrior — prime STR, so DEX is non-prime
    char.perm_stat = [13, 13, 13, 14, 13]  # DEX already at the dwarf race max

    # mirrors ROM src/handler.c:883 — pc_race_table[dwarf].max_stats[STAT_DEX] == 14
    result = do_train(char, "dex")
    assert result == "Your dexterity is already at maximum."
    assert char.perm_stat[3] == 14, "DEX must not exceed the dwarf max of 14"


def test_train_prime_stat_gets_class_bonus(train_test_setup):
    """TRAIN-004 — a human's prime stat ceiling is race max + 3 (clamped 25).

    A human mage's prime stat is INT (max_stats 18 + 3 = 21), so INT=20 is
    still trainable up to 21. mirrors ROM src/handler.c:884-889.
    """
    from mud.models.races import race_lookup

    char, _room = train_test_setup
    char.race = race_lookup("human")
    char.ch_class = 0  # mage — prime stat is INT
    char.perm_stat = [13, 20, 13, 13, 13]  # INT below the 18+3 prime cap

    result = do_train(char, "int")
    assert result == "Your intelligence increases!"
    assert char.perm_stat[1] == 21, "prime INT trains up to race max + 3 = 21"


def test_train_prime_stat_nonhuman_bonus_is_plus_two(train_test_setup):
    """TRAIN-004 — a non-human's prime stat ceiling is race max + 2 (not +3).

    A giant warrior's prime stat is STR (max_stats 22 + 2 = 24, clamped 25),
    so STR=23 is still trainable. mirrors ROM src/handler.c:888 (`max += 2`
    for non-human prime). Also guards against wrongly applying the human +3
    (which would yield 25).
    """
    from mud.models.races import race_lookup

    char, _room = train_test_setup
    char.race = race_lookup("giant")  # giant max_stats = (22, 15, 18, 15, 20)
    char.ch_class = 3  # warrior — prime stat is STR
    char.perm_stat = [23, 13, 13, 13, 13]  # STR one below the 22+2 prime cap

    result = do_train(char, "str")
    assert result == "Your strength increases!"
    assert char.perm_stat[0] == 24, "non-human prime STR trains up to race max + 2 = 24"
