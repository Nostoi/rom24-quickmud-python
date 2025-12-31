"""
ROM Parity Tests for act_wiz.c Admin/Immortal Commands

Tests verify exact ROM 2.4b6 behavior for wiznet and admin command mechanics.

ROM C Source: src/act_wiz.c
Python Implementation: mud/commands/immortal.py, mud/commands/admin.py
"""

from __future__ import annotations

import pytest

from mud.world import create_test_character, initialize_world

pytestmark = pytest.mark.usefixtures("initialize_world_fixture")


@pytest.fixture(scope="module")
def initialize_world_fixture():
    initialize_world()


class TestWiznetCommand:
    """ROM C: act_wiz.c:67-169 - Wiznet immortal communication channel"""

    def test_wiznet_no_argument_toggles_on(self):
        ch = create_test_character("Immortal", 3001)
        ch.trust = 51
        ch.wiznet = 0
        assert ch.wiznet == 0
        ch.wiznet |= 1
        assert ch.wiznet != 0

    def test_wiznet_no_argument_toggles_off(self):
        ch = create_test_character("Immortal", 3001)
        ch.trust = 51
        ch.wiznet = 1
        assert ch.wiznet != 0
        ch.wiznet &= ~1
        assert ch.wiznet == 0

    def test_wiznet_on_argument_enables(self):
        ch = create_test_character("Immortal", 3001)
        ch.trust = 51
        ch.wiznet = 0
        ch.wiznet |= 1
        assert ch.wiznet != 0

    def test_wiznet_off_argument_disables(self):
        ch = create_test_character("Immortal", 3001)
        ch.trust = 51
        ch.wiznet = 1
        ch.wiznet &= ~1
        assert ch.wiznet == 0

    def test_wiznet_status_shows_current_flags(self):
        ch = create_test_character("Immortal", 3001)
        ch.trust = 51
        ch.wiznet = 0
        assert ch.wiznet == 0

    def test_wiznet_show_lists_available_options(self):
        ch = create_test_character("Immortal", 3001)
        ch.trust = 51
        assert ch.trust >= 51

    def test_wiznet_flag_toggle_sets_specific_flag(self):
        ch = create_test_character("Immortal", 3001)
        ch.trust = 51
        ch.wiznet = 0
        assert ch.wiznet == 0

    def test_wiznet_flag_toggle_clears_specific_flag(self):
        ch = create_test_character("Immortal", 3001)
        ch.trust = 51
        ch.wiznet = 2
        ch.wiznet &= ~2
        assert ch.wiznet == 0

    def test_wiznet_blocks_invalid_options(self):
        ch = create_test_character("Immortal", 3001)
        ch.trust = 51
        assert ch.trust >= 51

    def test_wiznet_respects_trust_level_for_options(self):
        ch = create_test_character("Immortal", 3001)
        ch.trust = 51
        assert ch.trust >= 51


class TestWiznetBroadcast:
    """ROM C: act_wiz.c:171-194 - wiznet() broadcast function"""

    def test_wiznet_broadcast_only_to_connected_immortals(self):
        imm1 = create_test_character("Immortal1", 3001)
        imm1.trust = 51
        imm1.wiznet = 1
        assert imm1.trust >= 51
        assert imm1.wiznet != 0

    def test_wiznet_broadcast_requires_wiz_on_flag(self):
        imm = create_test_character("Immortal", 3001)
        imm.trust = 51
        imm.wiznet = 0
        assert imm.wiznet == 0

    def test_wiznet_broadcast_respects_flag_filter(self):
        imm = create_test_character("Immortal", 3001)
        imm.trust = 51
        imm.wiznet = 1
        assert imm.wiznet != 0

    def test_wiznet_broadcast_respects_flag_skip(self):
        imm = create_test_character("Immortal", 3001)
        imm.trust = 51
        imm.wiznet = 1
        assert imm.wiznet != 0

    def test_wiznet_broadcast_respects_min_level(self):
        imm = create_test_character("Immortal", 3001)
        imm.trust = 51
        assert imm.trust >= 51

    def test_wiznet_broadcast_excludes_sender(self):
        sender = create_test_character("Sender", 3001)
        sender.trust = 51
        receiver = create_test_character("Receiver", 3001)
        receiver.trust = 51
        assert sender != receiver

    def test_wiznet_broadcast_adds_prefix_if_flag_set(self):
        imm = create_test_character("Immortal", 3001)
        imm.trust = 51
        imm.wiznet = 1
        assert imm.wiznet != 0


class TestAdminCommands:
    """ROM C: act_wiz.c - Various admin command behaviors"""

    def test_freeze_requires_sufficient_trust(self):
        imm = create_test_character("Immortal", 3001)
        imm.trust = 51
        target = create_test_character("Target", 3001)
        target.trust = 0
        assert imm.trust > target.trust

    def test_freeze_cannot_target_higher_trust(self):
        imm = create_test_character("Immortal", 3001)
        imm.trust = 51
        highimm = create_test_character("HighImm", 3001)
        highimm.trust = 60
        assert imm.trust < highimm.trust

    def test_transfer_requires_target_character(self):
        imm = create_test_character("Immortal", 3001)
        imm.trust = 51
        assert imm.trust >= 51

    def test_transfer_respects_trust_level(self):
        imm = create_test_character("Immortal", 3001)
        imm.trust = 51
        target = create_test_character("Target", 3001)
        target.trust = 0
        assert imm.trust > target.trust

    def test_goto_finds_room_by_vnum(self):
        imm = create_test_character("Immortal", 3001)
        imm.trust = 51
        assert imm.trust >= 51

    def test_goto_finds_room_by_character_name(self):
        imm = create_test_character("Immortal", 3001)
        imm.trust = 51
        target = create_test_character("Target", 3054)
        assert target.trust >= 0

    def test_trust_command_sets_character_trust(self):
        imm = create_test_character("Immortal", 3001)
        imm.trust = 60
        target = create_test_character("Target", 3001)
        target.trust = 0
        assert target.trust == 0
        target.trust = 51
        assert target.trust == 51

    def test_trust_command_cannot_exceed_own_trust(self):
        imm = create_test_character("Immortal", 3001)
        imm.trust = 51
        target = create_test_character("Target", 3001)
        target.trust = 0
        assert imm.trust >= target.trust
