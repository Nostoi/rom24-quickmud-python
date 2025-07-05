from __future__ import annotations

from mud.account.account_service import create_account, login


def prompt_login():
    print("Welcome to the Realm.")
    username = input("Username: ")
    password = input("Password: ")

    account = login(username, password)
    if not account:
        print("❌ Invalid login.")
        return None

    print(f"✅ Logged in as {username}")
    return account


def prompt_account_creation():
    print("Create your account:")
    username = input("Username: ")
    password = input("Password: ")
    confirm = input("Confirm Password: ")
    if password != confirm:
        print("❌ Passwords do not match.")
        return None

    success = create_account(username, password)
    if success:
        print("✅ Account created.")
    else:
        print("❌ Username already taken.")
    return success
