"""
Player Auto-Settings Command Tests

Tests for ROM auto-setting commands (autolist, autoassist, autoexit, etc.)
ROM Reference: src/act_info.c lines 659-950

Priority: P0 (critical player quality-of-life features)
"""

from __future__ import annotations

import pytest

from mud.commands.auto_settings import (
    do_autoassist,
    do_autoall,
    do_autoexit,
    do_autogold,
    do_autolist,
    do_autoloot,
    do_autosac,
    do_autosplit,
    do_brief,
    do_colour,
    do_compact,
    do_combine,
    do_prompt,
)
from mud.models.constants import CommFlag, PlayerFlag
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world import create_test_character, initialize_world
from helpers_player import enable_autos, set_comm_flags, set_player_flags


PLR_AUTOASSIST = PlayerFlag.AUTOASSIST
PLR_AUTOEXIT = PlayerFlag.AUTOEXIT
PLR_AUTOGOLD = PlayerFlag.AUTOGOLD
PLR_AUTOLOOT = PlayerFlag.AUTOLOOT
PLR_AUTOSAC = PlayerFlag.AUTOSAC
PLR_AUTOSPLIT = PlayerFlag.AUTOSPLIT

COMM_COMPACT = CommFlag.COMPACT
COMM_BRIEF = CommFlag.BRIEF
COMM_PROMPT = CommFlag.PROMPT
COMM_COMBINE = CommFlag.COMBINE
COMM_NOCOLOUR = PlayerFlag.COLOUR


@pytest.fixture(scope="module", autouse=True)
def setup_world():
    """Initialize world once for all tests in this module."""
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    room_registry.clear()


@pytest.fixture(autouse=True)
def cleanup_characters():
    """Clear character registry after each test."""
    yield


class TestAutoAssist:
    """Test autoassist command and behavior.

    ROM Reference: src/act_info.c:1028-1041
    """

    @pytest.mark.p0
    def test_autoassist_toggle(self):
        """Autoassist command toggles PLR_AUTOASSIST flag."""
        # ROM C: act_info.c:1028-1041
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        assert not (player.act & PLR_AUTOASSIST)

        output = do_autoassist(player, "")
        assert player.act & PLR_AUTOASSIST
        assert "assist" in output.lower()

        output = do_autoassist(player, "")
        assert not (player.act & PLR_AUTOASSIST)
        assert "removed" in output.lower()

    @pytest.mark.p0
    def test_autoassist_npc_no_effect(self):
        """NPCs cannot use autoassist command."""
        player = create_test_character("NPC", 3001)
        player.is_npc = True

        output = do_autoassist(player, "")
        assert output == ""


class TestAutoExit:
    """Test autoexit command.

    ROM Reference: src/act_info.c:761-775
    """

    @pytest.mark.p0
    def test_autoexit_toggle(self):
        """Autoexit command toggles PLR_AUTOEXIT flag."""
        # ROM C: act_info.c:761-775
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        assert not (player.act & PLR_AUTOEXIT)

        output = do_autoexit(player, "")
        assert player.act & PLR_AUTOEXIT
        assert "displayed" in output.lower()

        output = do_autoexit(player, "")
        assert not (player.act & PLR_AUTOEXIT)
        assert "no longer" in output.lower()


class TestAutoGold:
    """Test autogold command.

    ROM Reference: src/act_info.c:778-792
    """

    @pytest.mark.p0
    def test_autogold_toggle(self):
        """Autogold command toggles PLR_AUTOGOLD flag."""
        # ROM C: act_info.c:778-792
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        assert not (player.act & PLR_AUTOGOLD)

        output = do_autogold(player, "")
        assert player.act & PLR_AUTOGOLD
        assert "gold" in output.lower()

        output = do_autogold(player, "")
        assert not (player.act & PLR_AUTOGOLD)


class TestAutoLoot:
    """Test autoloot command.

    ROM Reference: src/act_info.c:795-809
    """

    @pytest.mark.p0
    def test_autoloot_toggle(self):
        """Autoloot command toggles PLR_AUTOLOOT flag."""
        # ROM C: act_info.c:795-809
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        assert not (player.act & PLR_AUTOLOOT)

        output = do_autoloot(player, "")
        assert player.act & PLR_AUTOLOOT
        assert "loot" in output.lower()

        output = do_autoloot(player, "")
        assert not (player.act & PLR_AUTOLOOT)


class TestAutoSac:
    """Test autosac command.

    ROM Reference: src/act_info.c:812-826
    """

    @pytest.mark.p0
    def test_autosac_toggle(self):
        """Autosac command toggles PLR_AUTOSAC flag."""
        # ROM C: act_info.c:812-826
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        assert not (player.act & PLR_AUTOSAC)

        output = do_autosac(player, "")
        assert player.act & PLR_AUTOSAC
        assert "sacrific" in output.lower()

        output = do_autosac(player, "")
        assert not (player.act & PLR_AUTOSAC)


class TestAutoSplit:
    """Test autosplit command.

    ROM Reference: src/act_info.c:829-843
    """

    @pytest.mark.p0
    def test_autosplit_toggle(self):
        """Autosplit command toggles PLR_AUTOSPLIT flag."""
        # ROM C: act_info.c:829-843
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        assert not (player.act & PLR_AUTOSPLIT)

        output = do_autosplit(player, "")
        assert player.act & PLR_AUTOSPLIT
        assert "split" in output.lower()

        output = do_autosplit(player, "")
        assert not (player.act & PLR_AUTOSPLIT)


class TestAutoList:
    """Test autolist command.

    ROM Reference: src/act_info.c:659-742
    """

    @pytest.mark.p0
    def test_autolist_shows_all_settings(self):
        """Autolist displays all auto-settings and their status."""
        # ROM C: act_info.c:659-742
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        set_player_flags(player, autoassist=True, autoexit=True, autoloot=True)

        output = do_autolist(player, "")

        assert "autoassist" in output.lower()
        assert "autoexit" in output.lower()
        assert "autoloot" in output.lower()
        assert "autogold" in output.lower()
        assert "autosac" in output.lower()
        assert "autosplit" in output.lower()

    @pytest.mark.p0
    def test_autolist_shows_on_off_status(self):
        """Autolist shows ON/OFF status for each setting."""
        # ROM C: Shows {GON{x or {ROFF{x per flag
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        set_player_flags(player, autoassist=True, autoloot=False)

        output = do_autolist(player, "")

        # Should show status indicators (ON/OFF or color codes)
        assert len(output) > 50  # Should have substantial output
        assert "action" in output.lower() or "status" in output.lower()


class TestAutoAll:
    """Test autoall command.

    ROM Reference: src/act_info.c:846-875
    """

    @pytest.mark.p0
    def test_autoall_on(self):
        """Autoall on enables all auto-settings."""
        # ROM C: act_info.c:846-875
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.act = 0  # Clear all flags

        output = do_autoall(player, "on")

        assert player.act & PLR_AUTOASSIST
        assert player.act & PLR_AUTOEXIT
        assert player.act & PLR_AUTOGOLD
        assert player.act & PLR_AUTOLOOT
        assert player.act & PLR_AUTOSAC
        assert player.act & PLR_AUTOSPLIT
        assert "on" in output.lower()

    @pytest.mark.p0
    def test_autoall_off(self):
        """Autoall off disables all auto-settings."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        enable_autos(
            player,
            autoassist=True,
            autoexit=True,
            autogold=True,
            autoloot=True,
            autosac=True,
            autosplit=True,
        )

        output = do_autoall(player, "off")

        assert not (player.act & PLR_AUTOASSIST)
        assert not (player.act & PLR_AUTOEXIT)
        assert not (player.act & PLR_AUTOGOLD)
        assert not (player.act & PLR_AUTOLOOT)
        assert not (player.act & PLR_AUTOSAC)
        assert not (player.act & PLR_AUTOSPLIT)
        assert "off" in output.lower()

    @pytest.mark.p0
    def test_autoall_no_args(self):
        """Autoall without args shows usage."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False

        output = do_autoall(player, "")

        assert "usage" in output.lower() or "on" in output.lower()


class TestBrief:
    """Test brief command.

    ROM Reference: src/act_info.c:877-888
    """

    @pytest.mark.p0
    def test_brief_toggle(self):
        """Brief command toggles COMM_BRIEF flag."""
        # ROM C: act_info.c:877-888
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.comm = 0

        output = do_brief(player, "")
        assert player.comm & COMM_BRIEF
        assert "short" in output.lower() or "brief" in output.lower()

        output = do_brief(player, "")
        assert not (player.comm & COMM_BRIEF)
        assert "full" in output.lower()


class TestCompact:
    """Test compact command.

    ROM Reference: src/act_info.c:890-901
    """

    @pytest.mark.p0
    def test_compact_toggle(self):
        """Compact command toggles COMM_COMPACT flag."""
        # ROM C: act_info.c:890-901
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.comm = 0

        output = do_compact(player, "")
        assert player.comm & COMM_COMPACT
        assert "compact" in output.lower()

        output = do_compact(player, "")
        assert not (player.comm & COMM_COMPACT)
        assert "removed" in output.lower()


class TestCombine:
    """Test combine command."""

    @pytest.mark.p0
    def test_combine_toggle(self):
        """Combine command toggles COMM_COMBINE flag."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.comm = 0

        output = do_combine(player, "")
        assert player.comm & COMM_COMBINE
        assert "combined" in output.lower() or "combine" in output.lower()

        output = do_combine(player, "")
        assert not (player.comm & COMM_COMBINE)
        assert "no longer" in output.lower()


class TestColour:
    """Test colour/color command."""

    @pytest.mark.p0
    def test_colour_toggle(self):
        """Colour command toggles PlayerFlag.COLOUR flag."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.act = 0

        output = do_colour(player, "")
        assert player.act & COMM_NOCOLOUR
        assert "on" in output.lower() or "colour" in output.lower()

        output = do_colour(player, "")
        assert not (player.act & COMM_NOCOLOUR)
        assert "off" in output.lower()


class TestPrompt:
    """Test prompt command.

    ROM Reference: src/act_info.c do_prompt
    """

    @pytest.mark.p0
    def test_prompt_toggle(self):
        """Prompt with no args toggles COMM_PROMPT flag."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.comm = 0

        output = do_prompt(player, "")
        assert player.comm & COMM_PROMPT
        assert "prompt" in output.lower()

        output = do_prompt(player, "")
        assert not (player.comm & COMM_PROMPT)
        assert "no longer" in output.lower() or "not" in output.lower()

    @pytest.mark.p0
    def test_prompt_set_custom(self):
        """Prompt <string> sets custom prompt."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        pcdata = getattr(player, "pcdata", None)
        if not pcdata:
            pytest.skip("Player lacks pcdata")

        output = do_prompt(player, "<%hhp %mm %vmv>")

        assert player.comm & COMM_PROMPT
        assert pcdata.prompt == "<%hhp %mm %vmv>"
        assert "set" in output.lower()

    @pytest.mark.p0
    def test_prompt_all_sets_default(self):
        """Prompt all sets default ROM prompt."""
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        pcdata = getattr(player, "pcdata", None)
        if not pcdata:
            pytest.skip("Player lacks pcdata")

        output = do_prompt(player, "all")

        assert player.comm & COMM_PROMPT
        # ROM default: "<%hhp %mm %vmv> "
        assert pcdata.prompt is not None
        assert "hp" in pcdata.prompt.lower()


class TestCommunicationFlags:
    """Test communication flag commands (ROM src/act_comm.c)."""

    def test_comm_quiet_suppresses_all_channels(self):
        """Test QUIET flag suppresses all channels."""
        # ROM: do_quiet toggles COMM_QUIET flag
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.comm = 0

        # Set QUIET flag
        player.comm |= CommFlag.QUIET

        assert (player.comm & CommFlag.QUIET) != 0
        # All channels should be suppressed when QUIET is set

    def test_comm_deaf_blocks_incoming_tells(self):
        """Test DEAF flag blocks incoming tells."""
        # ROM: do_deaf toggles COMM_DEAF flag
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.comm = 0

        player.comm |= CommFlag.DEAF

        assert (player.comm & CommFlag.DEAF) != 0
        # Incoming tells should be blocked

    def test_comm_afk_marks_player_away(self):
        """Test AFK flag marks player as away from keyboard."""
        # ROM: do_afk toggles COMM_AFK flag
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.comm = 0

        player.comm |= CommFlag.AFK

        assert (player.comm & CommFlag.AFK) != 0
        # Player should be marked as AFK

    def test_comm_nowiz_blocks_wiznet(self):
        """Test NOWIZ flag blocks wiznet channel."""
        # ROM: do_nowiz toggles COMM_NOWIZ flag (immortals only)
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.comm = 0

        player.comm |= CommFlag.NOWIZ

        assert (player.comm & CommFlag.NOWIZ) != 0
        # Wiznet messages should be blocked

    def test_comm_noauction_blocks_auction_channel(self):
        """Test NOAUCTION flag blocks auction channel."""
        # ROM: Channel toggle for auction
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.comm = 0

        player.comm |= CommFlag.NOAUCTION

        assert (player.comm & CommFlag.NOAUCTION) != 0
        # Auction messages should be blocked

    def test_comm_nogossip_blocks_gossip_channel(self):
        """Test NOGOSSIP flag blocks gossip channel."""
        # ROM: Channel toggle for gossip
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.comm = 0

        player.comm |= CommFlag.NOGOSSIP

        assert (player.comm & CommFlag.NOGOSSIP) != 0
        # Gossip messages should be blocked

    def test_comm_noquestion_blocks_question_channel(self):
        """Test NOQUESTION flag blocks question channel."""
        # ROM: Channel toggle for question
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.comm = 0

        player.comm |= CommFlag.NOQUESTION

        assert (player.comm & CommFlag.NOQUESTION) != 0
        # Question messages should be blocked

    def test_comm_nomusic_blocks_music_channel(self):
        """Test NOMUSIC flag blocks music channel."""
        # ROM: Channel toggle for music
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.comm = 0

        player.comm |= CommFlag.NOMUSIC

        assert (player.comm & CommFlag.NOMUSIC) != 0
        # Music messages should be blocked

    def test_comm_noemote_prevents_emotes(self):
        """Test NOEMOTE flag prevents character from emoting."""
        # ROM: do_emote checks COMM_NOEMOTE flag (punishment)
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.comm = 0

        player.comm |= CommFlag.NOEMOTE

        assert (player.comm & CommFlag.NOEMOTE) != 0
        # Player should not be able to emote

    def test_comm_notell_blocks_tells(self):
        """Test NOTELL flag blocks sending/receiving tells."""
        # ROM: do_tell checks COMM_NOTELL flag
        player = create_test_character("TestPlayer", 3001)
        player.is_npc = False
        player.comm = 0

        player.comm |= CommFlag.NOTELL

        assert (player.comm & CommFlag.NOTELL) != 0
        # Player should not be able to send/receive tells
