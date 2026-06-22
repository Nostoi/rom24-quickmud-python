"""INV-009 — REGISTRY-DISCONNECT-CLEANUP enforcement.

Cross-file invariant complementing INV-003 (REGISTRY-MEMBERSHIP):
a clean websocket/telnet disconnect must remove the Character from
`mud.models.character.character_registry`. Otherwise, reconnecting by
the same name loads a fresh Character via INV-003 and the registry
accumulates duplicates — anything that iterates by name then can pick
the stale entry (broadcasts, mob targeting, area effects, etc.).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from mud.account.account_service import clear_active_accounts
from mud.db.models import Base
from mud.db.session import engine
from mud.models.character import character_registry
from mud.network.websocket_server import app
from mud.security import bans
from mud.world.world_state import reset_lockdowns


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()
    # Make registry leakage from earlier tests in the run visible/local
    # to this test only — clearing here ensures the count probe below
    # reflects only what *this* test produces.
    character_registry.clear()
    yield


def _receive_until_prompt(websocket, *, limit: int = 200):
    seen: list[dict] = []
    for _ in range(limit):
        payload = websocket.receive_json()
        seen.append(payload)
        if payload.get("type") == "prompt":
            return seen, payload
    raise AssertionError("Expected prompt message before receive limit.")


def _continue_motd(websocket, prompt):
    assert prompt["text"] == "[Hit Return to continue] "
    websocket.send_json({"type": "input", "text": ""})
    return _receive_until_prompt(websocket)


def _create_elf_mage(websocket, name: str) -> None:
    _, prompt = _receive_until_prompt(websocket)
    if prompt["text"] == "Do you want ANSI? (Y/n) ":
        websocket.send_json({"type": "input", "text": "y"})
        _, prompt = _receive_until_prompt(websocket)
    assert prompt["text"] == "Name: "
    for text in (name, "y", "secret1", "secret1", "elf", "m", "mage", "g", "n", "dagger"):
        websocket.send_json({"type": "input", "text": text})
        _, prompt = _receive_until_prompt(websocket)
    _, prompt = _continue_motd(websocket, prompt)
    assert prompt["session_state"] == "game"


def _reconnect(websocket, name: str) -> None:
    _, prompt = _receive_until_prompt(websocket)
    if prompt["text"] == "Do you want ANSI? (Y/n) ":
        websocket.send_json({"type": "input", "text": "y"})
        _, prompt = _receive_until_prompt(websocket)
    assert prompt["text"] == "Name: "
    websocket.send_json({"type": "input", "text": name})
    _, prompt = _receive_until_prompt(websocket)
    assert prompt["text"] == "Password: "
    websocket.send_json({"type": "input", "text": "secret1"})
    _, prompt = _receive_until_prompt(websocket)
    # Divergence-class 14: a link-dead reconnect rebinds straight into the game
    # (ROM check_reconnect → CON_PLAYING) with NO MOTD continue. (Before class 14
    # the prior char was removed on disconnect, so this was a fresh disk-load
    # login that DID show the MOTD.)
    assert prompt["session_state"] == "game"


def test_inv009_registry_has_single_entry_after_disconnect_and_reconnect() -> None:
    """INV-009 no-duplicate invariant holds via the class-14 mechanism.

    A clean websocket close (no `quit`) is a net-death link drop: the char
    LINGERS link-dead (ROM close_socket keeps it in char_list), and a reconnect
    REBINDS that same instance (ROM check_reconnect) — so the registry never
    accumulates a duplicate. (Before class 14 the disconnect removed the char
    and reconnect loaded a fresh one; the invariant — at most one entry per
    name — is unchanged, only the mechanism is.)
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            _create_elf_mage(websocket, "Regista")

        # Clean ws close == link drop → the char lingers link-dead.
        after_disconnect = [c for c in character_registry if getattr(c, "name", "") == "Regista"]

        with client.websocket_connect("/ws") as websocket:
            _reconnect(websocket, "Regista")
            # Capture WHILE the websocket is open.
            after_reconnect = [c for c in character_registry if getattr(c, "name", "") == "Regista"]

    # Class 14: the link drop leaves exactly ONE lingering, link-dead entry.
    assert len(after_disconnect) == 1, (
        f"class 14: a net-death link drop must LINGER exactly one 'Regista' "
        f"(link-dead), got {len(after_disconnect)} "
        f"(states: {[(c.hit, id(c)) for c in after_disconnect]})"
    )
    assert after_disconnect[0].link_dead is True, "the lingering char must be flagged link-dead"
    assert after_disconnect[0].desc is None, "the lingering char must have no descriptor"

    # INV-009: reconnect must NOT duplicate — and it must be the SAME instance
    # (a rebind, not a second disk load), which is what keeps the count at one.
    assert len(after_reconnect) == 1, (
        f"INV-009: after reconnect, expected exactly 1 'Regista' entry, got "
        f"{len(after_reconnect)} (states: {[(c.hit, id(c)) for c in after_reconnect]})"
    )
    assert after_reconnect[0] is after_disconnect[0], (
        "reconnect must REBIND the same in-world instance (check_reconnect), not load a 2nd from disk"
    )
