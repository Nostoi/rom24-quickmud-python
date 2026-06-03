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
            assert "BOB> " in prompt["text"], f"trailing space not preserved in rendered prompt; got {prompt['text']!r}"


def test_prompt_cmd_004_truncates_template_to_50_chars() -> None:
    """PROMPT-CMD-004 — `prompt <template>` truncates to 50 chars before storing.

    ROM C: src/act_info.c:943-944
        if (strlen (argument) > 50)
            argument[50] = '\\0';
        strcpy (buf, argument);

    Python previously stored the full untruncated argument. A 60-char
    template should store the first 50 chars only.

    Note: ROM's 50-char cap is applied BEFORE smash_tilde and BEFORE
    the `%c`-suffix space-append. After truncation ROM also appends a
    trailing space (PROMPT-CMD-005) unless the truncated string ends
    in `%c`, so the rendered success reply will read
    `"Prompt set to AAAA...A "` (50 As + space).
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            _create_elf_mage(websocket, "Promwd")
            template = "A" * 60
            transcript, _ = _send_command(websocket, f"prompt {template}")
            expected_stored = "A" * 50
            assert f"Prompt set to {expected_stored}" in transcript, (
                f"do_prompt did not truncate to 50 chars; transcript:\n{transcript}"
            )
            assert "A" * 51 not in transcript, "stored prompt template exceeded ROM's 50-char cap"


def test_prompt_cmd_005_appends_trailing_space_unless_pct_c_suffix() -> None:
    """PROMPT-CMD-005 — `do_prompt` appends `" "` unless buf ends with `%c`.

    ROM C: src/act_info.c:946-947
        if (str_suffix ("%c", buf))
            strcat (buf, " ");

    ROM's `str_suffix(a, b)` (src/db.c:3784) returns TRUE when `a` is
    NOT a suffix of `b`. So this branch appends a trailing space to
    every prompt template UNLESS the template already ends in `%c`
    (a colour-code escape that handles its own spacing).

    Two cases covered here:
      • `prompt TAG>` → stored as `"TAG> "` (trailing space appended).
      • `prompt TAG%c` → stored as `"TAG%c"` (no append; `%c` suffix).
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            _create_elf_mage(websocket, "Promwe")
            transcript, _ = _send_command(websocket, "prompt TAG>")
            assert "Prompt set to TAG> \n" in transcript or "Prompt set to TAG> \r" in transcript, (
                f"do_prompt did not append trailing space to non-%c template; transcript:\n{transcript!r}"
            )

        with client.websocket_connect("/ws") as websocket:
            _create_elf_mage(websocket, "Promwf")
            transcript, _ = _send_command(websocket, "prompt TAG%c")
            assert "Prompt set to TAG%c\n" in transcript or "Prompt set to TAG%c\r" in transcript, (
                f"do_prompt incorrectly appended space to %c-suffixed template; transcript:\n{transcript!r}"
            )
            assert "Prompt set to TAG%c " not in transcript, (
                "ROM does not append a trailing space when buf ends with %c"
            )


def test_prompt_cmd_003_smash_tilde_on_custom_template() -> None:
    """PROMPT-CMD-003 — `do_prompt` runs smash_tilde on the custom template.

    ROM C: src/act_info.c:945
        strcpy (buf, argument);
        smash_tilde (buf);

    `smash_tilde` (src/db.c:3663) replaces every '~' with '-' so the
    stored string cannot corrupt the player file (ROM uses '~' as an
    end-of-string marker on disk). Python's `do_prompt` previously
    stored the raw argument including any tildes the player typed.

    Note: ROM truncates `argument` to 50 chars BEFORE smash_tilde, so
    keep the template short enough to avoid coupling this test to
    PROMPT-CMD-004 (length-cap).
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            _create_elf_mage(websocket, "Promwc")
            transcript, _ = _send_command(websocket, "prompt T~AG>")
            assert "Prompt set to T-AG>" in transcript, f"smash_tilde not applied; transcript:\n{transcript}"
            assert "Prompt set to T~AG>" not in transcript, (
                "tilde leaked through to stored template — would corrupt pfile"
            )
