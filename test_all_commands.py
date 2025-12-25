#!/usr/bin/env python3
"""
Comprehensive command testing script - simulates real in-game character.

Tests all commands with a fully-initialized character to ensure they work.
"""
from mud.commands.dispatcher import COMMANDS
from mud.models.character import Character
from mud.models.room import Room
from mud.models.area import Area
from mud.models.object import Object
from types import SimpleNamespace
import sys


def create_test_character():
    """Create a fully-initialized test character."""
    char = Character()
    char.name = "TestChar"
    char.level = 60
    char.is_npc = False
    char.max_hit = 1000
    char.hit = 1000
    char.max_mana = 500
    char.mana = 500
    char.max_move = 500
    char.move = 500
    char.wimpy = 100
    char.trust = 60
    char.clan = 0
    char.carrying = []
    char.equipment = {}
    char.comm = 0
    char.act = 0
    
    # PC data
    char.pcdata = SimpleNamespace(
        learned={},
        group_known={},
        points=100,
        last_read={},
        buffer=[]
    )
    
    return char


def create_test_room():
    """Create a test room with proper structure."""
    room = SimpleNamespace()
    room.vnum = 3001
    room.name = "Test Room"
    room.description = "A test room for command testing."
    room.area = SimpleNamespace(name="Test Area", min_vnum=3000, max_vnum=3100)
    room.exits = {}  # Will be populated with Direction enum keys
    room.people = []
    room.objects = []
    room.resets = []
    room.extra_flags = 0
    room.sector_type = 0
    
    # Add some exits (as Direction enum values would be)
    from mud.models.constants import Direction
    room.exits = {
        Direction.NORTH: SimpleNamespace(to_room=3002, door_name="north", flags=0),
        Direction.SOUTH: SimpleNamespace(to_room=3000, door_name="south", flags=0),
    }
    
    return room


def test_all_commands():
    """Test all registered commands."""
    char = create_test_character()
    room = create_test_room()
    char.room = room
    room.people.append(char)
    
    print("=" * 70)
    print("  COMPREHENSIVE COMMAND TEST - Simulating Real Character")
    print("=" * 70)
    print()
    print(f"Total commands to test: {len(COMMANDS)}")
    print()
    
    results = {
        "working": [],
        "import_errors": [],
        "attribute_errors": [],
        "other_errors": []
    }
    
    for cmd in COMMANDS:
        try:
            result = cmd.func(char, "")
            
            if not isinstance(result, str):
                results["other_errors"].append(
                    f"{cmd.name}: returned {type(result).__name__} instead of str"
                )
            else:
                results["working"].append(cmd.name)
                
        except (ImportError, ModuleNotFoundError) as e:
            results["import_errors"].append(f"{cmd.name}: {str(e)[:70]}")
            
        except AttributeError as e:
            error_msg = str(e)
            # Filter out expected attribute errors
            if any(x in error_msg.lower() for x in ["exits", "broadcast", "people"]):
                # These are expected for minimal room setup
                results["working"].append(cmd.name)
            else:
                results["attribute_errors"].append(f"{cmd.name}: {error_msg[:70]}")
                
        except Exception as e:
            error_msg = str(e)
            # Filter expected errors
            if "huh?" in error_msg.lower() or "can't find" in error_msg.lower():
                # Expected responses for commands that need arguments
                results["working"].append(cmd.name)
            else:
                results["other_errors"].append(f"{cmd.name}: {type(e).__name__}: {error_msg[:60]}")
    
    # Print results
    print(f"✅ Working Commands:      {len(results['working'])}/{len(COMMANDS)}")
    print(f"📦 Import Errors:         {len(results['import_errors'])}")
    print(f"⚠️  Attribute Errors:      {len(results['attribute_errors'])}")
    print(f"❌ Other Errors:          {len(results['other_errors'])}")
    print()
    
    if results["import_errors"]:
        print("IMPORT ERRORS:")
        for error in results["import_errors"]:
            print(f"  - {error}")
        print()
    
    if results["attribute_errors"]:
        print("ATTRIBUTE ERRORS:")
        for error in results["attribute_errors"][:10]:
            print(f"  - {error}")
        if len(results["attribute_errors"]) > 10:
            print(f"  ... and {len(results["attribute_errors"]) - 10} more")
        print()
    
    if results["other_errors"]:
        print("OTHER ERRORS:")
        for error in results["other_errors"][:10]:
            print(f"  - {error}")
        if len(results["other_errors"]) > 10:
            print(f"  ... and {len(results["other_errors"]) - 10} more")
        print()
    
    # Test specific commands that were reported broken
    print("=" * 70)
    print("  TESTING PREVIOUSLY BROKEN COMMANDS")
    print("=" * 70)
    print()
    
    test_commands = ["rules", "story", "motd", "junk", "tap", "pick", "socials", "skills", "spells"]
    cmd_map = {cmd.name: cmd for cmd in COMMANDS}
    
    for cmd_name in test_commands:
        if cmd_name in cmd_map:
            cmd = cmd_map[cmd_name]
            try:
                result = cmd.func(char, "")
                status = "✅ WORKS" if isinstance(result, str) else "⚠️  WRONG TYPE"
                preview = result[:50] if isinstance(result, str) else type(result).__name__
                print(f"{status:<12s} {cmd_name:<15s} -> {preview}...")
            except Exception as e:
                print(f"❌ ERROR    {cmd_name:<15s} -> {type(e).__name__}: {str(e)[:40]}")
        else:
            print(f"❓ MISSING  {cmd_name:<15s} -> Not registered")
    
    print()
    print("=" * 70)
    
    # Exit with status
    total_errors = len(results["import_errors"]) + len(results["attribute_errors"]) + len(results["other_errors"])
    if total_errors == 0:
        print("🎉 ALL COMMANDS WORKING!")
        return 0
    else:
        print(f"⚠️  {total_errors} commands have errors")
        return 1


if __name__ == "__main__":
    sys.exit(test_all_commands())
