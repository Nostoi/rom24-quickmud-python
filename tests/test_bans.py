from pathlib import Path

from mud.security import bans
from mud.security.bans import BanFlag
from mud.commands import admin_commands


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


def test_ban_command_temporary_flag(tmp_path, monkeypatch):
    bans.clear_all_bans()
    monkeypatch.setattr(bans, "BANS_FILE", tmp_path / "ban.lst")

    message = admin_commands.cmd_ban(None, "temp.example")

    assert message == "Banned temp.example."
    entries = bans.get_ban_entries()
    assert len(entries) == 1
    assert not entries[0].flags & BanFlag.PERMANENT
    assert not (tmp_path / "ban.lst").exists()

