from __future__ import annotations

from fastapi.testclient import TestClient

from mud.account.account_service import clear_active_accounts
from mud.db.models import Base
from mud.db.session import engine
from mud.network.websocket_server import app
from mud.registry import room_registry
from mud.security import bans
from mud.world.world_state import reset_lockdowns


def setup_module(module) -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()


def _receive_until_prompt(websocket, *, limit: int = 20) -> tuple[list[dict], dict]:
    seen: list[dict] = []
    for _ in range(limit):
        payload = websocket.receive_json()
        seen.append(payload)
        if payload.get("type") == "prompt":
            return seen, payload
    raise AssertionError("Expected prompt message before receive limit.")


def test_websocket_boots_loaded_world_and_uses_account_login_flow() -> None:
    """mirroring ROM nanny.c: login starts with Name:, new char gets confirm then password."""
    with TestClient(app) as client:
        assert room_registry

        with client.websocket_connect("/ws") as websocket:
            seen, prompt = _receive_until_prompt(websocket)
            if prompt["text"] == "Do you want ANSI? (Y/n) ":
                websocket.send_json({"type": "input", "text": "y"})
                seen, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Name: "

            # new character name → confirm prompt
            websocket.send_json({"type": "input", "text": "webacct"})
            _, prompt = _receive_until_prompt(websocket)
            assert "Did I get that right" in prompt["text"]
            assert "(Y/N)?" in prompt["text"]

            websocket.send_json({"type": "input", "text": "y"})
            _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "New password: "
            assert prompt["secret"] is True

            websocket.send_json({"type": "input", "text": "secret1"})
            _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Confirm password: "
            assert prompt["secret"] is True
