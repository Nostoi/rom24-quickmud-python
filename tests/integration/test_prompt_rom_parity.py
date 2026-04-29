"""ROM parity tests for ``bust_a_prompt`` rendering — COMM-001.

mirrors ROM src/comm.c:1420-1595
"""

from __future__ import annotations

import pytest

from mud.commands.auto_settings import do_prompt
from mud.models.character import Character
from mud.models.constants import CommFlag
from mud.models.room import Room
from mud.utils.prompt import bust_a_prompt


@pytest.fixture
def char_with_stats(test_room: Room) -> Character:
    char = Character(
        name="Promptly",
        level=5,
        room=test_room,
        is_npc=False,
        hit=42,
        max_hit=120,
        mana=33,
        max_mana=80,
        move=21,
        max_move=99,
        exp=2500,
        gold=777,
        silver=12,
        alignment=350,
    )
    test_room.people.append(char)
    yield char
    if char in test_room.people:
        test_room.people.remove(char)


def test_default_prompt_renders_hp_mana_move(char_with_stats: Character) -> None:
    """When ``ch->prompt`` is unset, ROM renders ``<%dhp %dm %dmv>``.

    mirrors ROM src/comm.c:1437-1442
    """

    char_with_stats.prompt = None
    rendered = bust_a_prompt(char_with_stats)
    assert "<42hp 33m 21mv>" in rendered


def test_custom_prompt_token_expansion(char_with_stats: Character) -> None:
    """ROM expands ``%h %H %m %M %v %V %x %g %s`` against character stats.

    mirrors ROM src/comm.c:1489-1531
    """

    char_with_stats.prompt = "[%h/%H %m/%M %v/%V] %xxp %gg %ss "
    rendered = bust_a_prompt(char_with_stats)
    assert "[42/120 33/80 21/99] 2500xp 777g 12s " in rendered


def test_afk_prompt_short_circuits(char_with_stats: Character) -> None:
    """When ``COMM_AFK`` is set, ROM emits only ``<AFK>``.

    mirrors ROM src/comm.c:1445-1449
    """

    char_with_stats.prompt = "should-be-ignored %h"
    char_with_stats.comm = int(CommFlag.AFK)
    rendered = bust_a_prompt(char_with_stats)
    assert "<AFK>" in rendered
    assert "should-be-ignored" not in rendered
    assert "42" not in rendered


def test_percent_literal_token(char_with_stats: Character) -> None:
    """``%%`` renders as a single literal ``%``.

    mirrors ROM src/comm.c:1568-1571
    """

    char_with_stats.prompt = "100%% well "
    rendered = bust_a_prompt(char_with_stats)
    assert "100% well " in rendered


def test_alignment_token_below_level_10_is_word(char_with_stats: Character) -> None:
    """At level <10 ROM renders alignment as the textual word.

    mirrors ROM src/comm.c:1532-1540
    """

    char_with_stats.prompt = "align=%a "
    char_with_stats.level = 5
    char_with_stats.alignment = 500
    rendered = bust_a_prompt(char_with_stats)
    assert "align=good" in rendered


def test_alignment_token_at_level_10_or_above_is_numeric(char_with_stats: Character) -> None:
    """At level >9 ROM renders the numeric alignment.

    mirrors ROM src/comm.c:1532-1540
    """

    char_with_stats.prompt = "align=%a "
    char_with_stats.level = 15
    char_with_stats.alignment = -250
    rendered = bust_a_prompt(char_with_stats)
    assert "align=-250" in rendered


def test_room_token_renders_room_name(char_with_stats: Character) -> None:
    """``%r`` expands to the current room name when visible.

    mirrors ROM src/comm.c:1541-1553
    """

    char_with_stats.prompt = "in %r "
    rendered = bust_a_prompt(char_with_stats)
    assert f"in {char_with_stats.room.name}" in rendered


def test_do_prompt_stores_string_on_char_not_pcdata_color_triplet(
    char_with_stats: Character,
) -> None:
    """``do_prompt`` must store the ROM ``ch->prompt`` string on
    ``Character.prompt`` (the str field), not on ``PCData.prompt`` (the
    color triplet).

    mirrors ROM src/act_info.c:951-952
    """

    do_prompt(char_with_stats, "%h hp")
    assert char_with_stats.prompt == "%h hp"
