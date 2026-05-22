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
    _, prompt = _continue_motd(websocket, prompt)
    assert prompt["session_state"] == "game"


def test_inv009_registry_has_single_entry_after_disconnect_and_reconnect() -> None:
    """After a clean disconnect, the prior Character must be gone from registry."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            _create_elf_mage(websocket, "Regista")

        # Snapshot the registry state between disconnect and reconnect.
        after_disconnect = [c for c in character_registry if getattr(c, "name", "") == "Regista"]

        with client.websocket_connect("/ws") as websocket:
            _reconnect(websocket, "Regista")
            # Capture WHILE the websocket is open — once the context
            # manager exits the INV-009 disconnect cleanup will remove
            # the live entry too.
            after_reconnect = [c for c in character_registry if getattr(c, "name", "") == "Regista"]

    # Diagnose: after_disconnect tells us the "remove on disconnect" question;
    # after_reconnect tells us the duplicate question.
    assert len(after_disconnect) == 0, (
        f"INV-009: after clean disconnect, expected 0 'Regista' entries in "
        f"character_registry, got {len(after_disconnect)} "
        f"(states: {[(c.hit, id(c)) for c in after_disconnect]})"
    )
    assert len(after_reconnect) == 1, (
        f"INV-009: after reconnect, expected exactly 1 'Regista' entry in "
        f"character_registry, got {len(after_reconnect)} "
        f"(states: {[(c.hit, id(c)) for c in after_reconnect]})"
    )
