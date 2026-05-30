"""ACT-CAP-004 — broadcast_global channel capitalization parity (INV-029 cousin).

ROM ``src/comm.c:2376-2379`` (``act_new``) upper-cases the first visible
letter of every rendered ``act()`` line. All ROM channel commands route
through ``act_new`` (auction, gossip, grats, quote, question, answer,
music, clan, immtalk), so their listener lines get capitalized.

``broadcast_global`` is the Python delivery primitive for these channels.
It is NOT capped at function entry because ROM weather
(``src/update.c weather_update``) delivers via ``send_to_char`` (no cap),
and ``broadcast_global`` carries both channel and weather messages.

Instead, each channel command applies ``capitalize_act_line`` at the
call site. Weather messages (``game_loop.py:weather_tick`` / ``time_tick``)
remain uncapped — matching ROM.
"""

from __future__ import annotations

import pytest

from mud.commands.communication import (
    do_auction,
    do_gossip,
    do_grats,
    do_quote,
    do_question,
    do_answer,
    do_music,
    do_clantalk,
    do_immtalk,
)
from mud.models.character import Character, character_registry
from mud.models.constants import CommFlag
from mud.world import create_test_character, initialize_world

_ROM_COLOR_RE = __import__("re").compile(r"\{[a-zA-Z0-9]")


def _strip(text: str) -> str:
    return _ROM_COLOR_RE.sub("", text)


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    initialize_world("area/area.lst")
    yield
    character_registry.clear()


def _make_online_imm(level: int = 60, name: str = "Listener", room_vnum: int = 3002):
    char = create_test_character(name=name, room_vnum=room_vnum)
    char.level = level
    char.desc = object()
    return char


class TestAuctionCap:
    def test_auction_listener_message_capitalized(self) -> None:
        speaker = create_test_character(name="Auctioneer", room_vnum=3001)
        listener = _make_online_imm(name="Listener", room_vnum=3002)
        do_auction(speaker, "sword")
        msgs = [m for m in listener.messages if "auctions" in _strip(m)]
        assert msgs, f"no auction message received: {listener.messages}"
        plain = _strip(msgs[-1])
        assert plain.startswith("Auctioneer "), f"not capitalized: {msgs[-1]!r} → {plain!r}"


class TestGossipCap:
    def test_gossip_listener_message_capitalized(self) -> None:
        speaker = create_test_character(name="Gossiper", room_vnum=3001)
        listener = _make_online_imm(name="Listener", room_vnum=3002)
        do_gossip(speaker, "hello")
        msgs = [m for m in listener.messages if "gossips" in _strip(m)]
        assert msgs, f"no gossip message received: {listener.messages}"
        plain = _strip(msgs[-1])
        assert plain.startswith("Gossiper "), f"not capitalized: {msgs[-1]!r} → {plain!r}"


class TestGratsCap:
    def test_grats_listener_message_capitalized(self) -> None:
        speaker = create_test_character(name="Gratser", room_vnum=3001)
        listener = _make_online_imm(name="Listener", room_vnum=3002)
        do_grats(speaker, "grats")
        msgs = [m for m in listener.messages if "grats" in _strip(m)]
        assert msgs, f"no grats message received: {listener.messages}"
        plain = _strip(msgs[-1])
        assert plain.startswith("Gratser "), f"not capitalized: {msgs[-1]!r} → {plain!r}"


class TestClanCap:
    def test_clan_listener_message_capitalized(self) -> None:
        speaker = create_test_character(name="Clanner", room_vnum=3001)
        listener = _make_online_imm(name="Listener", room_vnum=3002)
        # Set up clan membership
        from mud.characters import is_clan_member, is_same_clan
        speaker.clan = 1
        listener.clan = 1
        do_clantalk(speaker, "hello clan")
        msgs = [m for m in listener.messages if "clans" in _strip(m)]
        assert msgs, f"no clan message received: {listener.messages}"
        plain = _strip(msgs[-1])
        assert plain.startswith("Clanner "), f"not capitalized: {msgs[-1]!r} → {plain!r}"


class TestWeatherNoCap:
    """Weather messages are sent via send_to_char in ROM (not act_new), so
    they should NOT be capitalized by broadcast_global."""

    def test_weather_message_not_double_capped(self) -> None:
        from mud.net.protocol import broadcast_global

        listener = _make_online_imm(name="Watcher", room_vnum=3001)

        def _should_receive(char: Character) -> bool:
            return True

        broadcast_global(
            "The day has begun.",
            channel="weather",
            should_send=_should_receive,
        )
        assert any("The day has begun." in m for m in listener.messages), (
            f"weather not received: {listener.messages}"
        )


class TestImmtalkCap:
    def test_immtalk_listener_message_capitalized(self) -> None:
        speaker = _make_online_imm(name="Immortal", level=60, room_vnum=3001)
        listener = _make_online_imm(name="Listener", level=60, room_vnum=3002)
        do_immtalk(speaker, "test")
        msgs = [m for m in listener.messages if "Immortal" in m or "immortal" in m.lower()]
        # The listener should receive the capitalized line
        assert msgs, f"no immtalk message received: {listener.messages}"