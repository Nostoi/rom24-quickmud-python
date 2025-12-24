"""
Parity tests for user-defined aliases against ROM 2.4 C src/alias.c

Tests alias substitution logic, prefix handling, and edge cases.
"""

import pytest

from mud.commands.dispatcher import _expand_aliases, process_command
from mud.models.character import Character
from mud.world import create_test_character, initialize_world


def setup_alias_test() -> Character:
    """Create test character with alias support."""
    initialize_world("area/area.lst")
    char = create_test_character("AliasTester", 3001)
    char.aliases = {}  # Ensure clean alias dict
    return char


def test_alias_substitution_basic():
    """Test basic alias substitution matches ROM C logic."""
    char = setup_alias_test()

    # Set up alias: "lk" -> "look"
    char.aliases["lk"] = "look"

    # Test substitution
    result, alias_used = _expand_aliases(char, "lk")
    assert alias_used is True
    assert result == "look"


def test_alias_substitution_with_args():
    """Test alias substitution with arguments matches ROM C logic."""
    char = setup_alias_test()

    # Set up alias: "gt" -> "get all"
    char.aliases["gt"] = "get all"

    # Test substitution with additional args
    result, alias_used = _expand_aliases(char, "gt corpse")
    assert alias_used is True
    assert result == "get all corpse"


def test_alias_substitution_exact_match():
    """Test that alias requires exact match (not prefix) like ROM C."""
    char = setup_alias_test()

    # Set up alias: "l" -> "look"
    char.aliases["l"] = "look"

    # "look" should not trigger "l" alias (exact match required)
    result, alias_used = _expand_aliases(char, "look")
    assert alias_used is False
    assert result == "look"


def test_alias_blocked_commands_in_dispatcher():
    """Test that alias, unalias, prefix commands bypass alias expansion.

    ROM C (src/alias.c:63-69) blocks alias expansion for commands starting
    with "alias", "una" (unalias), or "prefix".
    """
    char = setup_alias_test()

    char.aliases["alias"] = "look"
    char.aliases["una"] = "look"
    char.aliases["prefix"] = "look"

    result1, used1 = _expand_aliases(char, "alias")
    assert used1 is False
    assert result1 == "alias"

    result2, used2 = _expand_aliases(char, "unalias foo")
    assert used2 is False
    assert result2 == "unalias foo"

    result3, used3 = _expand_aliases(char, "prefix test")
    assert used3 is False
    assert result3 == "prefix test"

    result = process_command(char, "alias")
    assert "alias" in result.lower() or "No aliases" in result


def test_alias_max_depth_protection():
    """Test protection against recursive aliases like ROM C."""
    char = setup_alias_test()

    # Set up recursive alias: "a" -> "b", "b" -> "a"
    char.aliases["a"] = "b"
    char.aliases["b"] = "a"

    # Should stop at max_depth and not infinite loop
    # With max_depth=5: a->b->a->b->a->b, returns "b" (even iterations)
    result, alias_used = _expand_aliases(char, "a", max_depth=5)
    assert alias_used is True
    # After 5 expansions starting from "a", we get "b" (alternates)
    assert result in ("a", "b")  # Either is acceptable, just no infinite loop


def test_alias_case_sensitivity():
    """Test alias case sensitivity matches ROM C."""
    char = setup_alias_test()

    # Set up lowercase alias
    char.aliases["lk"] = "look"

    # Uppercase should not match
    result, alias_used = _expand_aliases(char, "LK")
    assert alias_used is False
    assert result == "LK"


def test_alias_empty_argument():
    """Test alias behavior with empty arguments."""
    char = setup_alias_test()

    # Empty command should not trigger alias expansion
    result, alias_used = _expand_aliases(char, "")
    assert alias_used is False
    assert result == ""


def test_alias_whitespace_handling():
    """Test alias whitespace handling matches ROM C."""
    char = setup_alias_test()

    # Set up alias with trailing space
    char.aliases["gt"] = "get all "

    result, alias_used = _expand_aliases(char, "gt")
    assert alias_used is True
    # Should preserve trailing space like ROM C
    assert result == "get all "


def test_alias_command_integration():
    """Test alias system integration with command dispatcher."""
    char = setup_alias_test()

    # Set up alias that maps to existing command
    char.aliases["lk"] = "look"

    # Process command through dispatcher - should expand and execute look
    result = process_command(char, "lk")
    # Look command output contains room description or exits
    assert result != "Huh?" and result != "What?"


def test_alias_chain_expansion():
    """Test alias chain expansion stops appropriately."""
    char = setup_alias_test()

    # Set up chain: "a" -> "b", "b" -> "look"
    char.aliases["a"] = "b"
    char.aliases["b"] = "look"

    result, alias_used = _expand_aliases(char, "a")
    assert alias_used is True
    assert result == "look"


def test_alias_with_multiple_words():
    """Test alias expansion with multi-word commands."""
    char = setup_alias_test()

    # Set up alias: "gs" -> "get sword"
    char.aliases["gs"] = "get sword"

    result, alias_used = _expand_aliases(char, "gs from corpse")
    assert alias_used is True
    assert result == "get sword from corpse"


def test_alias_no_partial_match():
    """Test that alias only matches first word, not partial."""
    char = setup_alias_test()

    char.aliases["look"] = "examine"

    # "looking" should not trigger "look" alias
    result, alias_used = _expand_aliases(char, "looking")
    assert alias_used is False
    assert result == "looking"


def test_alias_preserves_arguments():
    """Test that alias expansion preserves all arguments."""
    char = setup_alias_test()

    char.aliases["k"] = "kill"

    result, alias_used = _expand_aliases(char, "k rat quickly")
    assert alias_used is True
    assert result == "kill rat quickly"


def test_alias_parity_golden_sequence():
    """Golden test sequence for alias parity against ROM C behavior."""
    char = setup_alias_test()

    # Set up test aliases
    char.aliases["g"] = "get"
    char.aliases["ga"] = "get all"
    char.aliases["k"] = "kill"

    # Test sequence that would be processed in ROM C
    test_cases = [
        ("g sword", "get sword", True),  # Simple expansion
        ("ga corpse", "get all corpse", True),  # Expansion with args
        ("k rat", "kill rat", True),  # Another expansion
        ("look", "look", False),  # No alias
        ("", "", False),  # Empty input
    ]

    for input_cmd, expected_output, should_expand in test_cases:
        result, alias_used = _expand_aliases(char, input_cmd)
        assert alias_used is should_expand, f"Alias used mismatch for '{input_cmd}'"
        assert result == expected_output, f"Output mismatch for '{input_cmd}'"


if __name__ == "__main__":
    pytest.main([__file__])
