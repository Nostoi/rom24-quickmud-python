"""Integration tests for do_inventory command (ROM C parity).

ROM Reference: src/act_info.c do_inventory (lines 2254-2259)
"""

from __future__ import annotations

import pytest

from mud.models.constants import CommFlag


# P0 Tests (Critical - ROM C Behavioral Parity)


def test_inventory_header_separate_line(movable_char_factory, object_factory):
    """Test that 'You are carrying:' header is on separate line (ROM C line 2256)."""
    char = movable_char_factory("TestChar", 3001)

    # Add an object to inventory
    obj = object_factory({"vnum": 1, "name": "sword", "short_descr": "a wooden sword"})
    char.add_object(obj)

    # Execute command
    from mud.commands.inventory import do_inventory

    output = do_inventory(char, "")

    # Verify header on separate line (ROM C format)
    assert output.startswith("You are carrying:\n")
    assert "a wooden sword" in output
    # Should NOT be inline format "You are carrying: a wooden sword"
    assert not output.startswith("You are carrying: a wooden sword")


def test_inventory_object_combining_enabled(movable_char_factory, object_factory):
    """Test object combining with COMM_COMBINE flag enabled (ROM C lines 170-185)."""
    char = movable_char_factory("TestChar", 3001)

    # Enable COMM_COMBINE flag (ROM C line 170)
    char.comm = int(CommFlag.COMBINE)

    # Add 3 identical potions
    for i in range(3):
        obj = object_factory({"vnum": 100 + i, "name": "potion", "short_descr": "a healing potion"})
        char.add_object(obj)

    # Add 1 sword
    sword = object_factory({"vnum": 200, "name": "sword", "short_descr": "a wooden sword"})
    char.add_object(sword)

    # Execute command
    from mud.commands.inventory import do_inventory

    output = do_inventory(char, "")

    # Verify combining (ROM C lines 212-216: count prefix for duplicates)
    assert "( 3) a healing potion" in output  # Count prefix for 3 potions
    assert "     a wooden sword" in output  # Padding for single item

    # Should NOT show duplicates separately
    assert output.count("a healing potion") == 1  # Only one line for potions


def test_inventory_object_combining_disabled(movable_char_factory, object_factory):
    """Test object combining disabled without COMM_COMBINE flag (ROM C line 170)."""
    char = movable_char_factory("TestChar", 3001)

    # Disable COMM_COMBINE flag (clear all comm flags)
    char.comm = 0

    # Add 3 identical potions
    for i in range(3):
        obj = object_factory({"vnum": 100 + i, "name": "potion", "short_descr": "a healing potion"})
        char.add_object(obj)

    # Execute command
    from mud.commands.inventory import do_inventory

    output = do_inventory(char, "")

    # Verify NO combining: each object on separate line
    assert output.count("a healing potion") == 3  # Three separate lines

    # Should NOT have count prefix (ROM C lines 210-211: only with COMM_COMBINE)
    assert "( 3)" not in output
    assert "(3)" not in output


def test_inventory_count_prefix_format(movable_char_factory, object_factory):
    """Test count prefix format '(n)' for duplicates (ROM C lines 212-216)."""
    char = movable_char_factory("TestChar", 3001)
    char.comm = int(CommFlag.COMBINE)

    # Add 2 vests
    for i in range(2):
        obj = object_factory({"vnum": 100 + i, "name": "vest", "short_descr": "a leather vest"})
        char.add_object(obj)

    # Add 10 coins
    for i in range(10):
        obj = object_factory({"vnum": 200 + i, "name": "coin", "short_descr": "a gold coin"})
        char.add_object(obj)

    # Execute command
    from mud.commands.inventory import do_inventory

    output = do_inventory(char, "")

    # Verify count format (ROM C line 214: sprintf (buf, "(%2d) ", prgnShow[iShow]))
    assert "( 2) a leather vest" in output  # 2-digit right-aligned count
    assert "(10) a gold coin" in output  # 10 uses 2 digits

    # Verify format consistency
    lines = output.split("\n")
    for line in lines:
        if "(" in line and ")" in line:
            # Extract count portion
            count_part = line.split(")")[0] + ")"
            # Should be "(nn)" format with space padding
            assert count_part[0] == "("
            assert count_part[-1] == ")"


def test_inventory_empty_with_combine(movable_char_factory):
    """Test empty inventory shows 'Nothing' with padding (COMM_COMBINE, ROM C lines 227-232)."""
    char = movable_char_factory("TestChar", 3001)
    char.comm = int(CommFlag.COMBINE)

    # Empty inventory
    char.inventory = []

    # Execute command
    from mud.commands.inventory import do_inventory

    output = do_inventory(char, "")

    # Verify "Nothing" message with padding (ROM C lines 229-231)
    assert "You are carrying:\n" in output
    assert "     Nothing.\n" in output or "     Nothing." in output.rstrip()

    # Should have 5-space padding (ROM C line 230: send_to_char ("     ", ch))
    assert "     Nothing" in output


def test_inventory_empty_without_combine(movable_char_factory):
    """Test empty inventory shows 'Nothing' without padding (no COMM_COMBINE, ROM C line 231)."""
    char = movable_char_factory("TestChar", 3001)
    char.comm = 0  # No COMM_COMBINE

    # Empty inventory
    char.inventory = []

    # Execute command
    from mud.commands.inventory import do_inventory

    output = do_inventory(char, "")

    # Verify "Nothing" message without padding (ROM C line 231)
    assert "You are carrying:\n" in output
    assert "Nothing.\n" in output or "Nothing." in output.rstrip()

    # Should NOT have 5-space padding when COMM_COMBINE disabled
    assert "     Nothing" not in output


def test_inventory_multiline_format(movable_char_factory, object_factory):
    """Test inventory displays objects on separate lines (ROM C lines 222-223)."""
    char = movable_char_factory("TestChar", 3001)
    char.comm = 0  # Disable combining for simpler output

    # Add multiple objects
    obj1 = object_factory({"vnum": 1, "name": "sword", "short_descr": "a wooden sword"})
    obj2 = object_factory({"vnum": 2, "name": "vest", "short_descr": "a leather vest"})
    obj3 = object_factory({"vnum": 3, "name": "potion", "short_descr": "a healing potion"})
    char.add_object(obj1)
    char.add_object(obj2)
    char.add_object(obj3)

    # Execute command
    from mud.commands.inventory import do_inventory

    output = do_inventory(char, "")

    # Verify multi-line format (ROM C line 223: add_buf (output, "\n\r"))
    lines = output.split("\n")
    assert len(lines) >= 4  # Header + 3 objects + trailing newline

    # Verify each object on separate line
    assert any("a wooden sword" in line for line in lines)
    assert any("a leather vest" in line for line in lines)
    assert any("a healing potion" in line for line in lines)


# P1 Tests (Important - Edge Cases)


def test_inventory_npc_uses_combining(movable_char_factory, object_factory):
    """Test NPCs use object combining by default (ROM C line 170: IS_NPC check)."""
    char = movable_char_factory("TestMob", 3001)
    char.is_npc = True  # Mark as NPC
    char.comm = 0  # No COMM_COMBINE flag

    # Add 2 identical swords
    for i in range(2):
        obj = object_factory({"vnum": 100 + i, "name": "sword", "short_descr": "a rusty sword"})
        char.add_object(obj)

    # Execute command
    from mud.commands.inventory import do_inventory

    output = do_inventory(char, "")

    # Verify NPCs use combining even without COMM_COMBINE (ROM C line 170)
    assert "( 2) a rusty sword" in output or "(2) a rusty sword" in output
    assert output.count("a rusty sword") == 1  # Only one line


def test_inventory_mixed_counts(movable_char_factory, object_factory):
    """Test inventory with mix of single and multiple items."""
    char = movable_char_factory("TestChar", 3001)
    char.comm = int(CommFlag.COMBINE)

    # Add 3 potions
    for i in range(3):
        obj = object_factory({"vnum": 100 + i, "name": "potion", "short_descr": "a healing potion"})
        char.add_object(obj)

    # Add 1 sword
    sword = object_factory({"vnum": 200, "name": "sword", "short_descr": "a wooden sword"})
    char.add_object(sword)

    # Add 2 vests
    for i in range(2):
        obj = object_factory({"vnum": 300 + i, "name": "vest", "short_descr": "a leather vest"})
        char.add_object(obj)

    # Execute command
    from mud.commands.inventory import do_inventory

    output = do_inventory(char, "")

    # Verify mixed counts with proper formatting
    assert "( 3) a healing potion" in output  # Count for 3
    assert "     a wooden sword" in output  # Padding for 1
    assert "( 2) a leather vest" in output  # Count for 2


def test_inventory_case_sensitive_combining(movable_char_factory, object_factory):
    """Test object combining is case-sensitive (ROM C line 178: !strcmp)."""
    char = movable_char_factory("TestChar", 3001)
    char.comm = int(CommFlag.COMBINE)

    # Add objects with different capitalization
    obj1 = object_factory({"vnum": 1, "name": "sword", "short_descr": "a Wooden Sword"})  # Capital W
    obj2 = object_factory({"vnum": 2, "name": "sword", "short_descr": "a wooden sword"})  # Lowercase w
    char.add_object(obj1)
    char.add_object(obj2)

    # Execute command
    from mud.commands.inventory import do_inventory

    output = do_inventory(char, "")

    # Verify case-sensitive: should NOT combine (ROM C uses strcmp, not strcasecmp)
    assert "a Wooden Sword" in output
    assert "a wooden sword" in output
    # Should NOT show "( 2)"
    assert "( 2)" not in output


def test_inventory_duplicate_order_preserved(movable_char_factory, object_factory):
    """Test duplicate objects maintain first-seen order."""
    char = movable_char_factory("TestChar", 3001)
    char.comm = int(CommFlag.COMBINE)

    # Add objects in specific order
    sword = object_factory({"vnum": 1, "name": "sword", "short_descr": "a wooden sword"})
    potion1 = object_factory({"vnum": 2, "name": "potion", "short_descr": "a healing potion"})
    potion2 = object_factory({"vnum": 3, "name": "potion", "short_descr": "a healing potion"})
    vest = object_factory({"vnum": 4, "name": "vest", "short_descr": "a leather vest"})

    char.add_object(sword)
    char.add_object(potion1)
    char.add_object(vest)
    char.add_object(potion2)  # Second potion added last

    # Execute command
    from mud.commands.inventory import do_inventory

    output = do_inventory(char, "")

    # Verify order: sword, potion (combined), vest
    lines = [line.strip() for line in output.split("\n") if line.strip() and "You are carrying" not in line]

    # First object line should be sword
    assert "sword" in lines[0].lower()
    # Second should be potion with count
    assert "potion" in lines[1].lower() and "2" in lines[1]
    # Third should be vest
    assert "vest" in lines[2].lower()


# P2 Tests (Optional - Advanced Features)


def test_inventory_very_long_list(movable_char_factory, object_factory):
    """Test inventory with many objects (pagination would trigger in ROM C)."""
    char = movable_char_factory("TestChar", 3001)
    char.comm = 0

    # Add 50 different objects
    for i in range(50):
        obj = object_factory({"vnum": 100 + i, "name": f"item{i}", "short_descr": f"item number {i}"})
        char.add_object(obj)

    # Execute command
    from mud.commands.inventory import do_inventory

    output = do_inventory(char, "")

    # Verify all objects shown (QuickMUD doesn't paginate yet)
    assert "You are carrying:\n" in output
    # At least 50 lines (header + objects)
    lines = output.split("\n")
    # Should have header + 50 items
    assert len([l for l in lines if l.strip()]) >= 50


def test_inventory_special_characters_in_names(movable_char_factory, object_factory):
    """Test object names with special characters display correctly."""
    char = movable_char_factory("TestChar", 3001)
    char.comm = int(CommFlag.COMBINE)

    # Add objects with special characters
    obj1 = object_factory({"vnum": 1, "name": "special", "short_descr": "a sword of +5 slaying"})
    obj2 = object_factory({"vnum": 2, "name": "apostrophe", "short_descr": "Bob's sword"})
    obj3 = object_factory({"vnum": 3, "name": "quote", "short_descr": 'the "mighty" sword'})

    char.add_object(obj1)
    char.add_object(obj2)
    char.add_object(obj3)

    # Execute command
    from mud.commands.inventory import do_inventory

    output = do_inventory(char, "")

    # Verify special characters preserved
    assert "a sword of +5 slaying" in output
    assert "Bob's sword" in output
    assert 'the "mighty" sword' in output
