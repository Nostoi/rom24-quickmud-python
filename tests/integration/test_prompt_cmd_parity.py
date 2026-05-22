"""PROMPT-CMD-NNN — ROM `do_prompt` command-side parity.

Surfaced by the NANNY-SAVELOAD-002 probe in 2.8.35: the persistence
layer round-trip is clean, but `do_prompt` itself has two parity gaps
versus `src/act_info.c:919-955`.

These tests pin the ROM-exact behavior on the live websocket path so
the fix doesn't drift.
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


def _send_command(websocket, command: str) -> tuple[str, dict]:
    websocket.send_json({"type": "input", "text": command})
    seen, prompt = _receive_until_prompt(websocket)
    transcript = "".join(payload.get("text", "") for payload in seen)
    return transcript, prompt


def test_prompt_cmd_002_success_reply_echoes_stored_template() -> None:
    """PROMPT-CMD-002 — `do_prompt` success reply matches ROM wording.

    ROM C: src/act_info.c:953-954
        sprintf (buf, "Prompt set to %s\\n\\r", ch->prompt);
        send_to_char (buf, ch);

    Python previously emitted the truncated `"Prompt set."`.
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            _create_elf_mage(websocket, "Promwa")
            transcript, _ = _send_command(websocket, "prompt CUSTOM>")
            assert "Prompt set to CUSTOM>" in transcript, (
                f"do_prompt success reply not ROM-exact; transcript:\n{transcript}"
            )


def test_prompt_cmd_001_preserves_trailing_whitespace_on_template() -> None:
    """PROMPT-CMD-001 — `prompt <template>` preserves trailing whitespace.

    ROM C: src/act_info.c:944 stores the raw `argument` string after
    one_argument has skipped leading whitespace; trailing whitespace
    is preserved. So `prompt MYTAG> ` stores `"MYTAG> "` (with the
    trailing space the player typed) and bust_a_prompt renders it
    verbatim.

    Python previously stripped the trailing whitespace at
    `mud/commands/dispatcher.py` (`core = trimmed.rstrip()`) and again
    at `mud/commands/auto_settings.py:do_prompt` (`arg = ... .strip()`),
    so the rendered prompt lost the trailing space the player typed.
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            _create_elf_mage(websocket, "Promwb")
            # Set a template with a deliberately significant trailing
            # space — the canonical "Bob> " convention.
            _send_command(websocket, "prompt BOB> ")
            # Read back via toggle-off + toggle-on or just look at the next
            # prompt: dispatch any cheap command to force a fresh prompt
            # render.
            _, prompt = _send_command(websocket, "look")
            assert "BOB> " in prompt["text"], (
                f"trailing space not preserved in rendered prompt; got {prompt['text']!r}"
            )
