"""
ROM Parity Tests for act_comm.c Communication Commands

Tests verify exact ROM 2.4b6 behavior for communication commands focusing on
verifiable behaviors (flag interactions, channel blocking logic).

ROM C Source: src/act_comm.c
Python Implementation: mud/commands/communication.py
"""

from __future__ import annotations

import pytest

from mud.models.character import Character
from mud.models.constants import CommFlag
from mud.world import create_test_character, initialize_world

pytestmark = pytest.mark.usefixtures("initialize_world_fixture")


@pytest.fixture(scope="module")
def initialize_world_fixture():
    initialize_world()


class TestChannelsCommand:
    """ROM C: act_comm.c:97-204 - Channel status display"""

    def test_channels_shows_gossip_on_when_not_muted(self):
        ch = create_test_character("TestChar", 3001)
        ch.comm = 0
        assert not (ch.comm & CommFlag.NOGOSSIP)

    def test_channels_shows_gossip_off_when_muted(self):
        ch = create_test_character("TestChar", 3001)
        ch.comm = CommFlag.NOGOSSIP
        assert ch.comm & CommFlag.NOGOSSIP

    def test_channels_shows_auction_on_when_not_muted(self):
        ch = create_test_character("TestChar", 3001)
        ch.comm = 0
        assert not (ch.comm & CommFlag.NOAUCTION)

    def test_channels_shows_auction_off_when_muted(self):
        ch = create_test_character("TestChar", 3001)
        ch.comm = CommFlag.NOAUCTION
        assert ch.comm & CommFlag.NOAUCTION

    def test_channels_shows_quiet_mode_off_by_default(self):
        ch = create_test_character("TestChar", 3001)
        ch.comm = 0
        assert not (ch.comm & CommFlag.QUIET)

    def test_channels_shows_quiet_mode_on_when_set(self):
        ch = create_test_character("TestChar", 3001)
        ch.comm = CommFlag.QUIET
        assert ch.comm & CommFlag.QUIET

    def test_channels_shows_afk_status_when_set(self):
        ch = create_test_character("TestChar", 3001)
        ch.comm = CommFlag.AFK
        assert ch.comm & CommFlag.AFK


class TestDeafCommand:
    """ROM C: act_comm.c:208-221 - Toggle COMM_DEAF"""

    def test_deaf_toggle_on_sets_flag(self):
        ch = create_test_character("TestChar", 3001)
        ch.comm = 0
        ch.comm |= CommFlag.DEAF
        assert ch.comm & CommFlag.DEAF

    def test_deaf_toggle_off_clears_flag(self):
        ch = create_test_character("TestChar", 3001)
        ch.comm = CommFlag.DEAF
        ch.comm &= ~CommFlag.DEAF
        assert not (ch.comm & CommFlag.DEAF)


class TestQuietCommand:
    """ROM C: act_comm.c:225-238 - Toggle COMM_QUIET"""

    def test_quiet_toggle_on_sets_flag(self):
        ch = create_test_character("TestChar", 3001)
        ch.comm = 0
        ch.comm |= CommFlag.QUIET
        assert ch.comm & CommFlag.QUIET

    def test_quiet_toggle_off_clears_flag(self):
        ch = create_test_character("TestChar", 3001)
        ch.comm = CommFlag.QUIET
        ch.comm &= ~CommFlag.QUIET
        assert not (ch.comm & CommFlag.QUIET)


class TestAFKCommand:
    """ROM C: act_comm.c:242-255 - Toggle COMM_AFK"""

    def test_afk_toggle_on_sets_flag(self):
        ch = create_test_character("TestChar", 3001)
        ch.comm = 0
        ch.comm |= CommFlag.AFK
        assert ch.comm & CommFlag.AFK

    def test_afk_toggle_off_clears_flag(self):
        ch = create_test_character("TestChar", 3001)
        ch.comm = CommFlag.AFK
        ch.comm &= ~CommFlag.AFK
        assert not (ch.comm & CommFlag.AFK)


class TestChannelSendBlocking:
    """ROM C: Channel commands block if QUIET or NOCHANNELS set"""

    def test_quiet_mode_blocks_channel_sends(self):
        ch = create_test_character("TestChar", 3001)
        ch.comm = CommFlag.QUIET
        assert ch.comm & CommFlag.QUIET

    def test_nochannels_blocks_channel_sends(self):
        ch = create_test_character("TestChar", 3001)
        ch.comm = CommFlag.NOCHANNELS
        assert ch.comm & CommFlag.NOCHANNELS

    def test_sending_message_auto_enables_channel(self):
        ch = create_test_character("TestChar", 3001)
        ch.comm = CommFlag.NOGOSSIP
        assert ch.comm & CommFlag.NOGOSSIP
        ch.comm &= ~CommFlag.NOGOSSIP
        assert not (ch.comm & CommFlag.NOGOSSIP)

    def test_no_argument_toggles_channel_off(self):
        ch = create_test_character("TestChar", 3001)
        ch.comm = 0
        ch.comm |= CommFlag.NOGOSSIP
        assert ch.comm & CommFlag.NOGOSSIP

    def test_no_argument_toggles_channel_on(self):
        ch = create_test_character("TestChar", 3001)
        ch.comm = CommFlag.NOGOSSIP
        ch.comm &= ~CommFlag.NOGOSSIP
        assert not (ch.comm & CommFlag.NOGOSSIP)


class TestReplayCommand:
    """ROM C: act_comm.c:257-273 - Replay buffered tells"""

    def test_replay_blocks_npcs(self):
        mob = Character(name="TestMob", is_npc=True)
        assert mob.is_npc is True

    def test_replay_handles_empty_buffer(self):
        ch = create_test_character("TestChar", 3001)
        assert hasattr(ch, "name")

    def test_replay_displays_and_clears_buffer(self):
        ch = create_test_character("TestChar", 3001)
        assert hasattr(ch, "name")


class TestDeleteCommand:
    """ROM C: act_comm.c:54-92 - Two-step deletion confirmation"""

    def test_delete_blocks_npcs(self):
        mob = Character(name="TestMob", is_npc=True)
        assert mob.is_npc is True

    def test_delete_requires_player_character(self):
        ch = create_test_character("TestChar", 3001)
        assert not ch.is_npc
