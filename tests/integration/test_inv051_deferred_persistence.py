"""INV-051 — no character row is persisted until creation completes.

ROM mechanism: in ``src/nanny.c`` a new character lives only in memory through
``CON_GET_NAME`` → ``CON_CONFIRM_NEW_NAME`` → ``CON_GET_NEW_PASSWORD`` → race /
sex / class / alignment / weapon, and is written to disk *only* by
``save_char_obj`` at the very end of ``CON_READ_MOTD``. Nothing touches the
pfile before then.

The Python nanny diverged: ``_run_character_login`` INSERTed a bare level-0 row
via ``create_account`` the moment the player chose a password — before any race
/ class / stats existed. A player who quit (or whose server restarted) between
the password prompt and the end of the creation menu (the real-world ``Eddol``
case) left behind a loginable, half-initialised row. That row also crashed
``do_train`` because ``perm_stat`` was empty (TRAIN-006).

This test asserts the contract directly: after driving name → confirm →
password through ``_run_character_login`` with the *real* DB-backed
``create_account`` / ``login_with_host`` / ``character_exists``, **no** row
exists for the new name. It is RED while the password phase persists a bare
row, GREEN once persistence is deferred to ``create_character`` (creation end).
"""

from __future__ import annotations

import asyncio

import pytest

from mud.account.account_service import character_exists, clear_active_accounts
from mud.db.models import Base
from mud.db.session import engine
from mud.net import connection as connection_mod
from mud.security import bans
from mud.world.world_state import reset_lockdowns


@pytest.fixture(autouse=True)
def _clean_db():
    """Self-contained DB schema so the test is parallel-safe (AGENTS.md)."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()
    yield
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    clear_active_accounts()


def _drive_new_character_password_phase(monkeypatch, name: str):
    """Run ``_run_character_login`` through name → confirm → password.

    Only the IO boundary is stubbed (``_prompt`` / ``_send_line`` and the
    descriptor-dedup helper). ``create_account``, ``login_with_host`` and
    ``character_exists`` stay real so the DB side effect (or absence of it) is
    what the test observes.
    """

    sent: list[str] = []
    prompts: list[str] = []

    class FakeStream:
        host = "test.example"
        peer_host = "test.example"

        def set_ansi(self, _enabled):
            pass

    async def fake_prompt(_conn, label, *, hide_input=False):
        prompts.append(label)
        # Safety net: never loop the name prompt — if creation re-prompts for a
        # name something went wrong; bail so the test asserts rather than hangs.
        if sum(1 for p in prompts if p == "Name: ") > 1:
            return None
        if label == "Name: ":
            return name
        if label.startswith("Did I get that right"):
            return "y"
        if label.startswith("Give me a password"):
            return "secret"
        if label.startswith("Please retype password"):
            return "secret"
        return ""

    async def fake_send_line(_conn, msg):
        sent.append(msg)

    monkeypatch.setattr(connection_mod, "_prompt", fake_prompt)
    monkeypatch.setattr(connection_mod, "_send_line", fake_send_line)

    # No competing descriptors in the unit harness.
    async def _no_duplicates(_conn, _name):
        return False

    monkeypatch.setattr(connection_mod, "_close_duplicate_newbie_descriptors", _no_duplicates)

    result = asyncio.run(connection_mod._run_character_login(FakeStream(), None))
    return result, sent, prompts


@pytest.mark.p0
def test_no_db_row_after_password_phase(monkeypatch):
    """A new character that has only chosen a password leaves no DB row.

    mirrors ROM src/nanny.c — nothing is written before save_char_obj at the
    end of creation. INV-051.
    """
    result, _sent, prompts = _drive_new_character_password_phase(monkeypatch, "newbie")

    # The login coroutine should advance to the creation flow (is_new_character
    # True), not loop back to the name prompt.
    assert prompts.count("Name: ") == 1, f"unexpected re-prompt: {prompts}"
    assert result is not None, "new-character login should hand off to creation, not fail"
    _account, username, was_reconnect, is_new_character = result
    assert is_new_character is True
    assert was_reconnect is False
    assert username == "newbie"

    # The contract: no persisted row yet. Creation has not completed.
    assert character_exists("newbie") is False, (
        "INV-051 violated: a character row was persisted at the password phase, "
        "before race/class/stats were chosen. ROM writes nothing until "
        "save_char_obj at creation end (src/nanny.c)."
    )


@pytest.mark.p0
def test_transient_account_carries_password_hash(monkeypatch):
    """The handoff object holds the hashed password in memory (no DB write).

    create_character later reads ``account.password_hash`` to persist it in the
    single creation-end INSERT, so the in-memory carrier must expose a verifiable
    hash without having touched the DB.
    """
    from mud.security.hash_utils import verify_password

    result, _sent, _prompts = _drive_new_character_password_phase(monkeypatch, "newbie")
    assert result is not None
    account, _username, _was_reconnect, _is_new = result

    pwd_hash = getattr(account, "password_hash", None)
    assert pwd_hash, "transient account must carry the chosen password hash"
    assert verify_password("secret", pwd_hash)
    # Still nothing on disk.
    assert character_exists("newbie") is False
