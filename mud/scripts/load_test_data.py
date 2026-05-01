from mud.account.account_service import create_account


def load_test_user():
    """Create a test character using ROM character-first login (no account table)."""
    if create_account("Tester", "test123"):
        print("✅ Test character created: name=Tester / pw=test123")
    else:
        print("ℹ️  Test character 'Tester' already exists.")
