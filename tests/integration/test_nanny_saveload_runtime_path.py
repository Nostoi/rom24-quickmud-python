"""NANNY-SAVELOAD-NNN — live-websocket save → reload → retained-state parity.

Closes Plan Task 4's final bullet: verify that state changes made
mid-session round-trip through a clean disconnect + reconnect on the
real server path (not helper-only DB fixtures). Existing helper tests
cover the DB layer in isolation; these tests exercise the full
websocket → nanny → save → load → first-command loop.

ROM source-of-truth:
- `src/save.c:fwrite_char` / `fread_char` — save & load of all
  per-character state.
- `src/act_info.c:1477-1556` (do_score) — wimpy + condition lines are
  the user-visible read-back of saved state.
- `src/comm.c:1420-1595` (bust_a_prompt) — prompt template is read
  from `pcdata->prompt` on every prompt render.
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


def _reconnect(websocket, name: str):
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
    return _continue_motd(websocket, prompt)


def _send_command(websocket, command: str) -> tuple[str, dict]:
    """Send a command, return (transcript, prompt) for the response."""
    websocket.send_json({"type": "input", "text": command})
    seen, prompt = _receive_until_prompt(websocket)
    transcript = "".join(payload.get("text", "") for payload in seen)
    return transcript, prompt


def _quit(websocket) -> None:
    """End the session ROM-cleanly via ``do_quit`` (save + extract), so the next
    login is a fresh DISK round-trip rather than a class-14 link-dead rebind.

    A bare websocket close is a net-death link drop (the char lingers link-dead),
    which would make the reconnect rebind the in-memory instance — defeating the
    save/load round-trip these tests exist to prove. Draining to the server-side
    close confirms the quit's extract+save ran before we reconnect.
    """
    from contextlib import suppress

    websocket.send_json({"type": "input", "text": "quit"})
    with suppress(Exception):
        for _ in range(100):
            websocket.receive_json()


def test_nanny_saveload_002_prompt_template_round_trips_through_reconnect() -> None:
    """NANNY-SAVELOAD-002 — custom prompt template persists across reconnect.

    ROM C: `src/act_info.c:919-960` (do_prompt) writes `ch->prompt`;
    `src/save.c:fwrite_char` persists it; `src/comm.c:1420-1595`
    (bust_a_prompt) renders the saved template on every prompt. After a
    clean disconnect + reconnect, the FIRST in-game prompt must render
    the saved template (no ROM-default `<Nhp Nm Nmv>` fallback) — proving
    that `pcdata->prompt` round-trips through `from_orm`.
    """
    # Use a tokenless tag with no leading/trailing whitespace so the
    # round-trip assertion is independent of how the dispatcher strips
    # argument whitespace (separate parity concern — see SAVELOAD-002
    # follow-up notes).
    custom_prompt = "ROMSAVELOADPROMPT>"
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            _create_elf_mage(websocket, "Promter")
            transcript, _ = _send_command(websocket, f"prompt {custom_prompt}")
            # mirroring ROM src/act_info.c:953-954 — success reply echoes
            # the stored template (PROMPT-CMD-002).
            assert f"Prompt set to {custom_prompt}" in transcript, f"do_prompt did not confirm set:\n{transcript}"
            _quit(websocket)  # save + extract so the reconnect is a fresh disk load

        with client.websocket_connect("/ws") as websocket:
            _, prompt = _reconnect(websocket, "Promter")
            assert prompt["session_state"] == "game"
            # The post-MOTD prompt is the first "live" prompt on the
            # reconnected session; it must come from the saved template,
            # not the ROM default `<Nhp Nm Nmv>` fallback.
            assert custom_prompt in prompt["text"], (
                f"reconnect's first in-game prompt did not render saved template "
                f"{custom_prompt!r}; got {prompt['text']!r}"
            )


def test_nanny_saveload_003_alias_round_trips_through_reconnect() -> None:
    """NANNY-SAVELOAD-003 — per-character aliases persist across reconnect.

    ROM C: `src/alias.c:102-220` (do_alias) writes `ch->pcdata->alias`;
    `src/save.c:fwrite_char` persists the alias array; `do_alias` with
    no args at `src/alias.c:165-175` renders the saved list as
    ``    <name>:  <expansion>``. After a clean disconnect + reconnect,
    `alias` must list the previously-set alias — proving the JSON
    column round-trips through `from_orm`.
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            _create_elf_mage(websocket, "Aliaser")
            transcript, _ = _send_command(websocket, "alias k kill")
            assert "k is now aliased to 'kill'." in transcript, f"set-alias response not ROM-exact:\n{transcript}"
            _quit(websocket)  # save + extract so the reconnect is a fresh disk load

        with client.websocket_connect("/ws") as websocket:
            _, prompt = _reconnect(websocket, "Aliaser")
            assert prompt["session_state"] == "game"

            transcript, _ = _send_command(websocket, "alias")
            # ROM listing format: "    <name>:  <expansion>"
            assert "    k:  kill" in transcript, (
                f"alias did not round-trip through reconnect; listing transcript:\n{transcript}"
            )


def test_nanny_saveload_001_wimpy_round_trips_through_reconnect() -> None:
    """NANNY-SAVELOAD-001 — wimpy threshold persists across disconnect/reconnect.

    ROM C: `src/act_info.c:2800-2830` (do_wimpy) writes `ch->wimpy`;
    `src/save.c:fwrite_char` persists it; `do_score` reads it back at
    `src/act_info.c:1548-1549` as ``"Wimpy set to %d hit points.\\n\\r"``.
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            _create_elf_mage(websocket, "Wimper")
            transcript, _ = _send_command(websocket, "wimpy 30")
            assert "Wimpy set to 30 hit points." in transcript, f"set-wimpy response not ROM-exact:\n{transcript}"
            _quit(websocket)  # save + extract so the reconnect is a fresh disk load

        # Reconnect and read back via score.
        with client.websocket_connect("/ws") as websocket:
            _, prompt = _reconnect(websocket, "Wimper")
            assert prompt["session_state"] == "game"

            transcript, _ = _send_command(websocket, "score")
            assert "Wimpy set to 30 hit points." in transcript, (
                f"wimpy did not round-trip through reconnect; score transcript:\n{transcript}"
            )
