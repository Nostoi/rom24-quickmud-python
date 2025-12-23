#!/usr/bin/env python3
"""
Fix orphaned characters in the database.

This script finds characters with NULL player_id and either:
1. Links them to a matching player account (if username matches character name)
2. Deletes them if no matching account exists

Run this after upgrading to fix any characters created before the player_id bug fix.
"""

from mud.db.models import Character, PlayerAccount
from mud.db.session import SessionLocal


def fix_orphaned_characters(delete_orphans: bool = False) -> None:
    """
    Fix characters with NULL player_id.
    
    Args:
        delete_orphans: If True, delete orphaned characters. If False, just report them.
    """
    session = SessionLocal()
    try:
        # Find all characters with NULL player_id
        orphaned = session.query(Character).filter(Character.player_id.is_(None)).all()
        
        if not orphaned:
            print("✅ No orphaned characters found!")
            return
        
        print(f"Found {len(orphaned)} orphaned character(s):")
        print()
        
        fixed = 0
        deleted = 0
        
        for char in orphaned:
            print(f"  - {char.name} (id={char.id}, level={char.level})")
            
            # Try to find a matching player account
            account = session.query(PlayerAccount).filter(
                PlayerAccount.username == char.name.lower()
            ).first()
            
            if account:
                print(f"    → Found matching account: {account.username} (id={account.id})")
                char.player_id = account.id
                fixed += 1
                print(f"    ✅ Linked character to account")
            else:
                print(f"    ⚠️  No matching account found")
                if delete_orphans:
                    session.delete(char)
                    deleted += 1
                    print(f"    🗑️  Deleted orphaned character")
                else:
                    print(f"    ℹ️  Character kept (run with --delete to remove)")
        
        if fixed > 0 or deleted > 0:
            session.commit()
            print()
            print(f"Summary:")
            print(f"  ✅ Fixed: {fixed}")
            if delete_orphans:
                print(f"  🗑️  Deleted: {deleted}")
            print()
        else:
            print()
            print("No changes made. Run with --delete flag to remove orphaned characters.")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    import sys
    
    delete = "--delete" in sys.argv
    
    if delete:
        print("⚠️  WARNING: This will DELETE orphaned characters that have no matching account!")
        response = input("Continue? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            sys.exit(0)
    
    fix_orphaned_characters(delete_orphans=delete)
