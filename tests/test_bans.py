from mud.security import bans


def test_account_and_host_add_remove_checks():
    bans.clear_all_bans()
    # None and unknown are not banned
    assert not bans.is_host_banned(None)
    assert not bans.is_account_banned(None)
    assert not bans.is_host_banned("example.org")
    assert not bans.is_account_banned("alice")

    # Add and check
    bans.add_banned_host("example.org")
    bans.add_banned_account("alice")
    assert bans.is_host_banned("example.org")
    assert bans.is_account_banned("alice")

    # Remove and check
    bans.remove_banned_host("example.org")
    bans.remove_banned_account("alice")
    assert not bans.is_host_banned("example.org")
    assert not bans.is_account_banned("alice")


def test_save_deletes_when_empty(tmp_path):
    bans.clear_all_bans()
    path = tmp_path / "ban.txt"
    path.write_text("placeholder\n")
    assert path.exists()
    # No bans -> saving should delete the file
    bans.save_bans_file(path)
    assert not path.exists()


def test_load_ignores_non_permanent(tmp_path):
    bans.clear_all_bans()
    path = tmp_path / "ban.txt"
    # Write one non-permanent (D) and one permanent (DF)
    lines = [
        f"{'temp.example':<20}  0 D\n",
        f"{'perm.example':<20}  0 DF\n",
    ]
    path.write_text("".join(lines))
    loaded = bans.load_bans_file(path)
    assert loaded == 1
    assert not bans.is_host_banned("temp.example")
    assert bans.is_host_banned("perm.example")


def test_account_denies_persist_across_restart(tmp_path):
    bans.clear_all_bans()
    bans.add_banned_account("Denied")
    path = tmp_path / "ban.txt"

    bans.save_bans_file(path)
    account_path = path.with_name("ban_accounts.txt")
    assert account_path.exists()
    assert account_path.read_text().strip() == "denied"

    bans.clear_all_bans()
    bans.load_bans_file(path)
    assert bans.is_account_banned("denied")
