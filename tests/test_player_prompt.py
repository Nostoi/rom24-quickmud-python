from __future__ import annotations

import pytest

from mud.commands.auto_settings import do_prompt
from mud.models.constants import CommFlag
from mud.world import create_test_character, initialize_world
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from helpers_player import set_comm_flags


@pytest.fixture(autouse=True)
def setup_world():
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    room_registry.clear()


class TestPromptCommand:
    def test_prompt_sets_custom_string(self):
        player = create_test_character("Customizer", 3001)

        output = do_prompt(player, "<%h/%H hp>")

        assert player.pcdata is not None
        assert player.pcdata.prompt == "<%h/%H hp>"
        assert "set" in output.lower()

    def test_prompt_all_sets_default_format(self):
        player = create_test_character("DefaultUser", 3001)

        output = do_prompt(player, "all")

        assert player.pcdata is not None
        assert player.pcdata.prompt == "<%hhp %mm %vmv> "
        assert "set" in output.lower()

    def test_prompt_length_not_enforced_at_input(self):
        player = create_test_character("LongPrompt", 3001)
        long_prompt = "a" * 100

        do_prompt(player, long_prompt)

        assert player.pcdata is not None
        assert player.pcdata.prompt == long_prompt

    def test_prompt_toggle_off_from_on(self):
        player = create_test_character("Toggler", 3001)
        set_comm_flags(player, prompt=True)

        output = do_prompt(player, "")

        assert not (player.comm & CommFlag.PROMPT)
        assert "no longer" in output.lower() or "not" in output.lower()

    def test_prompt_toggle_on_from_off(self):
        player = create_test_character("Toggler", 3001)
        player.comm = 0

        output = do_prompt(player, "")

        assert "now see" in output.lower() or "will" in output.lower()

    def test_prompt_stores_arbitrary_text(self):
        player = create_test_character("AnyText", 3001)

        do_prompt(player, "This is not a valid prompt format")

        assert player.pcdata is not None
        assert player.pcdata.prompt == "This is not a valid prompt format"


class TestPromptPCDataRequirement:
    def test_prompt_requires_pcdata(self):
        player = create_test_character("NoPC", 3001)
        player.pcdata = None

        output = do_prompt(player, "<%h hp>")

        assert output == "Prompt set."
