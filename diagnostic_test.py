#!/usr/bin/env python3
"""
Quick diagnostic test to understand the current issues.
"""

import sys
sys.path.insert(0, 'mud')

from mud.world.world_state import initialize_world, get_room
from mud.models.character import Character
from mud.commands.inspection import do_look
from mud.models.constants import Position
from mud.account.account_service import login, create_account

def test_world_state():
    """Test if world is properly initialized."""
    print("=== WORLD STATE TEST ===")
    try:
        initialize_world()
        temple = get_room(3001)  # Temple of Mota
        if temple:
            print(f"✓ Temple room found: {temple.name}")
            print(f"  Description: {temple.description[:50]}...")
            print(f"  Exits: {len(temple.exits) if temple.exits else 0}")
        else:
            print("✗ Temple room (3001) not found")
    except Exception as e:
        print(f"✗ World initialization failed: {e}")

def test_look_command():
    """Test if look command works with a test character."""
    print("\n=== LOOK COMMAND TEST ===")
    try:
        initialize_world()
        temple = get_room(3001)
        if not temple:
            print("✗ No temple room for testing")
            return
            
        # Create test character
        char = Character()
        char.name = "TestChar"
        char.room = temple
        char.position = Position.STANDING
        
        # Test look command
        result = do_look(char)
        print(f"✓ Look command result:\n{result}")
        
    except Exception as e:
        print(f"✗ Look command failed: {e}")
        import traceback
        traceback.print_exc()

def test_authentication():
    """Test authentication system."""
    print("\n=== AUTHENTICATION TEST ===")
    try:
        # Try to create account
        result = create_account("testuser", "testpass")
        print(f"Create account result: {result}")
        
        # Try to login
        login_result = login("testuser", "testpass")
        print(f"Login result: {login_result}")
        
    except Exception as e:
        print(f"✗ Authentication test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_world_state()
    test_look_command()
    test_authentication()
    print("\n=== DIAGNOSTIC COMPLETE ===")