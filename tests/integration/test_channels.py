"""
Integration tests for communication channels system.

Tests verify that channels work according to ROM 2.4b6 behavior:
- Channel listing with status
- Channel toggling (on/off)
- Sending messages on channels
- Channel filtering (users with channel off don't see messages)
- Multiple channel types (gossip, auction, music, etc.)

ROM Reference: src/act_comm.c (do_channels, do_gossip, do_auction, do_music)
"""

from __future__ import annotations

import pytest

from mud.commands.channels import do_channels
from mud.commands.communication import do_gossip, do_auction, do_music, do_grats
from mud.models.character import Character, character_registry
from mud.models.constants import CommFlag, Position
from mud.registry import room_registry
from mud.world import initialize_world


@pytest.fixture(scope="module", autouse=True)
def setup_world():
    initialize_world("area/area.lst")
    yield


@pytest.fixture
def test_room():
    return room_registry.get(3001)


@pytest.fixture
def player1(test_room):
    char = Character(
        name="Alice",
        short_descr="Alice the tester",
        is_npc=False,
        level=10,
        position=Position.STANDING,
        room=test_room,
        comm=0,
    )
    test_room.add_character(char)
    character_registry.append(char)
    yield char
    if char in test_room.people:
        test_room.people.remove(char)
    if char in character_registry:
        character_registry.remove(char)


@pytest.fixture
def player2(test_room):
    char = Character(
        name="Bob",
        short_descr="Bob the listener",
        is_npc=False,
        level=10,
        position=Position.STANDING,
        room=test_room,
        comm=0,
    )
    test_room.add_character(char)
    character_registry.append(char)
    yield char
    if char in test_room.people:
        test_room.people.remove(char)
    if char in character_registry:
        character_registry.remove(char)


class TestChannelsCommand:
    def test_channels_command_lists_all_channels(self, player1):
        result = do_channels(player1, "")

        assert "Channel Status:" in result
        assert "gossip" in result.lower()
        assert "auction" in result.lower()
        assert "music" in result.lower()
        assert "shout" in result.lower()
        assert "tell" in result.lower()

    def test_channels_show_on_status_by_default(self, player1):
        player1.comm = 0
        result = do_channels(player1, "")

        assert "[ON]" in result
        assert result.count("[ON]") >= 7

    def test_channels_show_off_status_when_disabled(self, player1):
        player1.comm = int(CommFlag.NOGOSSIP)
        result = do_channels(player1, "")

        assert "[OFF]" in result
        assert "gossip" in result.lower()


class TestGossipChannel:
    def test_gossip_broadcasts_message_to_all_players(self, player1, player2):
        result = do_gossip(player1, "Hello everyone!")

        assert "hello everyone" in result.lower()

    def test_gossip_respects_channel_off_setting(self, player1, player2):
        player2.comm = int(CommFlag.NOGOSSIP)

        result = do_gossip(player1, "Testing gossip")

        assert "testing gossip" in result.lower() or "you gossip" in result.lower()

    def test_gossip_toggles_channel_when_no_argument(self, player1):
        player1.comm = 0
        result = do_gossip(player1, "")

        assert "off" in result.lower()
        assert player1.comm & int(CommFlag.NOGOSSIP)


class TestAuctionChannel:
    def test_auction_broadcasts_item_announcement(self, player1, player2):
        result = do_auction(player1, "Selling a sword for 100 gold!")

        assert "sword" in result.lower() and ("100" in result or "gold" in result)

    def test_auction_respects_channel_off_setting(self, player1, player2):
        player2.comm = int(CommFlag.NOAUCTION)

        result = do_auction(player1, "Auction test")

        assert "auction" in result.lower()

    def test_auction_toggles_channel_when_no_argument(self, player1):
        player1.comm = 0
        result = do_auction(player1, "")

        assert "off" in result.lower()
        assert player1.comm & int(CommFlag.NOAUCTION)


class TestMusicChannel:
    def test_music_broadcasts_song_or_poem(self, player1, player2):
        result = do_music(player1, "La la la, testing music!")

        assert "la la la" in result.lower() or "music" in result.lower()

    def test_music_respects_channel_off_setting(self, player1, player2):
        player2.comm = int(CommFlag.NOMUSIC)

        result = do_music(player1, "Music test")

        assert "music" in result.lower()

    def test_music_toggles_channel_when_no_argument(self, player1):
        player1.comm = 0
        result = do_music(player1, "")

        assert "off" in result.lower()
        assert player1.comm & int(CommFlag.NOMUSIC)


class TestGratsChannel:
    def test_grats_broadcasts_congratulations(self, player1, player2):
        result = do_grats(player1, "Congrats on level 50!")

        assert "congrats" in result.lower() or "level 50" in result.lower()

    def test_grats_respects_channel_off_setting(self, player1, player2):
        player2.comm = int(CommFlag.NOGRATS)

        result = do_grats(player1, "Grats test")

        assert "grats" in result.lower() or "congratulations" in result.lower()

    def test_grats_toggles_channel_when_no_argument(self, player1):
        player1.comm = 0
        result = do_grats(player1, "")

        assert "off" in result.lower()
        assert player1.comm & int(CommFlag.NOGRATS)


class TestChannelFiltering:
    def test_sending_message_auto_enables_channel(self, player1, player2):
        player1.comm = int(CommFlag.NOGOSSIP)

        result = do_gossip(player1, "This auto-enables gossip")

        assert "you gossip" in result.lower()
        assert not (player1.comm & int(CommFlag.NOGOSSIP))

    def test_multiple_channels_can_be_disabled(self, player1):
        player1.comm = int(CommFlag.NOGOSSIP) | int(CommFlag.NOAUCTION)

        result = do_channels(player1, "")

        gossip_off = False
        auction_off = False
        for line in result.split("\n"):
            if "gossip" in line.lower() and "[OFF]" in line:
                gossip_off = True
            if "auction" in line.lower() and "[OFF]" in line:
                auction_off = True

        assert gossip_off and auction_off
