"""ROM-parity integration tests for ``src/alias.c``."""

from __future__ import annotations

from mud.commands.dispatcher import process_command
from mud.world import create_test_character, initialize_world


def test_alias_command_uses_rom_messages_and_listing() -> None:
    """Mirror ROM ``src/alias.c:131-149,169-185,217-220``."""
    initialize_world("area/area.lst")
    char = create_test_character("AliasUser", 3001)

    assert process_command(char, "alia") == "I'm sorry, alias must be entered in full.\n\r"
    assert process_command(char, "alias") == "You have no aliases defined.\n\r"

    created = process_command(char, "alias lk look")
    assert created == "lk is now aliased to 'look'.\n\r"

    listing = process_command(char, "alias")
    assert listing == "Your current aliases are:\n\r    lk:  look\n\r"

    queried = process_command(char, "alias lk")
    assert queried == "lk aliases to 'look'.\n\r"


def test_alias_substitution_is_single_pass_like_rom() -> None:
    """Mirror ROM ``src/alias.c:73-99`` single-pass substitution."""
    initialize_world("area/area.lst")
    char = create_test_character("AliasChain", 3001)

    assert process_command(char, "alias a zzzcmd") == "a is now aliased to 'zzzcmd'.\n\r"
    assert process_command(char, "alias zzzcmd look") == "zzzcmd is now aliased to 'look'.\n\r"

    assert process_command(char, "a") == "Huh?"


def test_alias_command_rejects_reserved_and_forbidden_expansions() -> None:
    """Mirror ROM ``src/alias.c:153-190`` validation rules."""
    initialize_world("area/area.lst")
    char = create_test_character("AliasGuard", 3001)

    assert process_command(char, "alias alias look") == "Sorry, that word is reserved.\n\r"
    assert process_command(char, "alias lk delete") == "That shall not be done!\n\r"
    assert process_command(char, "alias lk prefix say") == "That shall not be done!\n\r"


def test_unalias_uses_rom_messages() -> None:
    """Mirror ROM ``src/alias.c:236-274`` removal semantics."""
    initialize_world("area/area.lst")
    char = create_test_character("AliasDelete", 3001)

    assert process_command(char, "unalias") == "Unalias what?\n\r"
    assert process_command(char, "alias lk look") == "lk is now aliased to 'look'.\n\r"
    assert process_command(char, "unalias lk") == "Alias removed.\n\r"
    assert process_command(char, "unalias lk") == "No alias of that name to remove.\n\r"
