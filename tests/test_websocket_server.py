from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from mud.account.account_service import clear_active_accounts
from mud.db.models import Base, Character
from mud.db.session import SessionLocal, engine
from mud.network.websocket_server import app
from mud.registry import room_registry
from mud.security import bans
from mud.world.world_state import reset_lockdowns


@pytest.fixture(autouse=True)
def _reset_websocket_login_state() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()
    yield


def _receive_until_prompt(websocket, *, limit: int = 20) -> tuple[list[dict], dict]:
    seen: list[dict] = []
    for _ in range(limit):
        payload = websocket.receive_json()
        seen.append(payload)
        if payload.get("type") == "prompt":
            return seen, payload
    raise AssertionError("Expected prompt message before receive limit.")


def _continue_motd_prompt(websocket, prompt: dict) -> tuple[list[dict], dict]:
    assert prompt["text"] == "[Hit Return to continue] "
    assert prompt["session_state"] == "motd"
    websocket.send_json({"type": "input", "text": ""})
    return _receive_until_prompt(websocket, limit=200)


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
            assert prompt["text"] == "Give me a password for Webacct: "
            assert prompt["secret"] is True

            websocket.send_json({"type": "input", "text": "secret1"})
            _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Please retype password: "
            assert prompt["secret"] is True


def test_websocket_created_character_persists_and_reconnects_with_password_prompt() -> None:
    with TestClient(app) as client:
        assert room_registry

        with client.websocket_connect("/ws") as websocket:
            _, prompt = _receive_until_prompt(websocket)
            if prompt["text"] == "Do you want ANSI? (Y/n) ":
                websocket.send_json({"type": "input", "text": "y"})
                _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Name: "

            for text in (
                "Eddol",
                "y",
                "secret1",
                "secret1",
                "elf",
                "m",
                "mage",
                "g",
                "n",
                "dagger",
            ):
                websocket.send_json({"type": "input", "text": text})
                _, prompt = _receive_until_prompt(websocket)

            _, prompt = _continue_motd_prompt(websocket, prompt)
            assert prompt["text"].endswith("> ")

        session = SessionLocal()
        try:
            row = session.query(Character).filter_by(name="Eddol").first()
            assert row is not None
            assert row.level == 1
            assert row.race == 1
            assert row.ch_class == 0
            assert row.title == " the Apprentice of Magic"
        finally:
            session.close()

        with client.websocket_connect("/ws") as websocket:
            _, prompt = _receive_until_prompt(websocket)
            if prompt["text"] == "Do you want ANSI? (Y/n) ":
                websocket.send_json({"type": "input", "text": "y"})
                _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Name: "

            websocket.send_json({"type": "input", "text": "Eddol"})
            _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Password: "


def test_websocket_reconnect_does_not_replay_new_character_outfit_flow() -> None:
    """Returning level-1 characters must not re-run ROM first-login school outfit flow."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            _, prompt = _receive_until_prompt(websocket)
            if prompt["text"] == "Do you want ANSI? (Y/n) ":
                websocket.send_json({"type": "input", "text": "y"})
                _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Name: "

            for text in (
                "Replay",
                "y",
                "secret1",
                "secret1",
                "elf",
                "m",
                "mage",
                "g",
                "n",
                "dagger",
            ):
                websocket.send_json({"type": "input", "text": text})
                _, prompt = _receive_until_prompt(websocket)

            _, prompt = _continue_motd_prompt(websocket, prompt)
        with client.websocket_connect("/ws") as websocket:
            _, prompt = _receive_until_prompt(websocket)
            if prompt["text"] == "Do you want ANSI? (Y/n) ":
                websocket.send_json({"type": "input", "text": "y"})
                _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Name: "

            websocket.send_json({"type": "input", "text": "Replay"})
            _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Password: "

            websocket.send_json({"type": "input", "text": "secret1"})
            _, prompt = _receive_until_prompt(websocket, limit=200)
            seen, prompt = _continue_motd_prompt(websocket, prompt)
            assert prompt["session_state"] == "game"

            texts = [payload.get("text", "") for payload in seen]
            assert all("equipped by Mota" not in text for text in texts)
            assert all("Ah! Another mortal trying to find his way" not in text for text in texts)


def test_websocket_reconnect_preserves_school_outfit_state() -> None:
    """Returning players must keep the first-login outfit across save/load."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            _, prompt = _receive_until_prompt(websocket)
            if prompt["text"] == "Do you want ANSI? (Y/n) ":
                websocket.send_json({"type": "input", "text": "y"})
                _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Name: "

            for text in (
                "OutfitKeep",
                "y",
                "secret1",
                "secret1",
                "elf",
                "m",
                "mage",
                "g",
                "n",
                "dagger",
            ):
                websocket.send_json({"type": "input", "text": text})
                _, prompt = _receive_until_prompt(websocket)

            _, prompt = _continue_motd_prompt(websocket, prompt)
            websocket.send_json({"type": "input", "text": "score"})
            seen, prompt = _receive_until_prompt(websocket)
            assert prompt["session_state"] == "game"
            score_text = "".join(payload.get("text", "") for payload in seen)
            created_carry_line = next(
                line for line in score_text.splitlines() if line.startswith("You are carrying ")
            )

        with client.websocket_connect("/ws") as websocket:
            _, prompt = _receive_until_prompt(websocket)
            if prompt["text"] == "Do you want ANSI? (Y/n) ":
                websocket.send_json({"type": "input", "text": "y"})
                _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Name: "

            websocket.send_json({"type": "input", "text": "OutfitKeep"})
            _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Password: "

            websocket.send_json({"type": "input", "text": "secret1"})
            _, prompt = _receive_until_prompt(websocket, limit=200)
            _, prompt = _continue_motd_prompt(websocket, prompt)
            assert prompt["session_state"] == "game"

            websocket.send_json({"type": "input", "text": "score"})
            seen, prompt = _receive_until_prompt(websocket)
            assert prompt["session_state"] == "game"
            score_text = "".join(payload.get("text", "") for payload in seen)
            reloaded_carry_line = next(
                line for line in score_text.splitlines() if line.startswith("You are carrying ")
            )
            assert reloaded_carry_line == created_carry_line


def test_websocket_reconnect_score_matches_rom_act_info_lines() -> None:
    """NANNY-RECONNECT-001 — `score` on first command after reconnect matches ROM transcript.

    ROM C: src/act_info.c:1477-1507 (do_score). After reset_char on login
    (NANNY-014), an elf mage should report Race/Sex/Class as
    'Race: elf  Sex: male  Class: mage' and have hit/mana/move at full
    (hp == max_hit etc.).
    """
    import re

    with TestClient(app) as client:
        # Create elf mage and disconnect.
        with client.websocket_connect("/ws") as websocket:
            _, prompt = _receive_until_prompt(websocket)
            if prompt["text"] == "Do you want ANSI? (Y/n) ":
                websocket.send_json({"type": "input", "text": "y"})
                _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Name: "
            for text in ("Scorer", "y", "secret1", "secret1", "elf", "m", "mage", "g", "n", "dagger"):
                websocket.send_json({"type": "input", "text": text})
                _, prompt = _receive_until_prompt(websocket, limit=200)
            _, prompt = _continue_motd_prompt(websocket, prompt)
            assert prompt["session_state"] == "game"

        # Reconnect, log in with password, then issue `score`.
        with client.websocket_connect("/ws") as websocket:
            _, prompt = _receive_until_prompt(websocket)
            if prompt["text"] == "Do you want ANSI? (Y/n) ":
                websocket.send_json({"type": "input", "text": "y"})
                _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Name: "
            websocket.send_json({"type": "input", "text": "Scorer"})
            _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Password: "
            websocket.send_json({"type": "input", "text": "secret1"})
            _, prompt = _receive_until_prompt(websocket, limit=200)
            _, prompt = _continue_motd_prompt(websocket, prompt)
            assert prompt["session_state"] == "game"

            websocket.send_json({"type": "input", "text": "score"})
            seen, prompt = _receive_until_prompt(websocket, limit=200)
            assert prompt["session_state"] == "game"
            transcript = "".join(payload.get("text", "") for payload in seen)

        # ROM src/act_info.c:1482-1488 — title line.
        # Mage level-1 title from src/const.c title_table[0][1] = "Apprentice of Magic".
        # ROM emits "You are <name><title>, level N, ..." where title already has a leading space.
        title_match = re.search(
            r"You are Scorer the Apprentice of Magic, level 1, \d+ years old \(\d+ hours\)\.",
            transcript,
        )
        assert title_match, f"title line not ROM-exact; transcript:\n{transcript}"

        # ROM src/act_info.c:1496-1500 — race/sex/class line.
        # race_table[2].name == "elf"; class_table[0].name == "mage"; sex==1 == "male".
        assert "Race: elf  Sex: male  Class: mage" in transcript, (
            f"race/sex/class line not ROM-exact; transcript:\n{transcript}"
        )

        # ROM src/act_info.c:1503-1507 — hit/mana/move line; after reset_char hp==max_hit etc.
        resources_match = re.search(
            r"You have (\d+)/(\d+) hit, (\d+)/(\d+) mana, (\d+)/(\d+) movement\.",
            transcript,
        )
        assert resources_match, f"hit/mana/move line not ROM-exact; transcript:\n{transcript}"
        hit, max_hit, mana, max_mana, move, max_move = (int(x) for x in resources_match.groups())
        assert (hit, mana, move) == (max_hit, max_mana, max_move), (
            f"resources not at max after reconnect+reset_char: "
            f"hit={hit}/{max_hit} mana={mana}/{max_mana} move={move}/{max_move}"
        )


def test_websocket_reconnect_look_matches_room_registry_not_cached_snapshot() -> None:
    """NANNY-RECONNECT-002 — `look` on first command after reconnect matches live room.

    ROM C: src/act_info.c:1037-1116 (do_look, no-arg branch). After
    reset_char + char_to_room on login, `look` must emit the in_room's
    canonical name and description from the loaded area data, not a stale
    cached snapshot from before the disconnect.

    Strategy: capture the live room from `character_registry` after login,
    then assert both the room name and a substring of its description
    appear in the transcript produced by sending `look`.
    """
    from mud.models.character import character_registry

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            _, prompt = _receive_until_prompt(websocket)
            if prompt["text"] == "Do you want ANSI? (Y/n) ":
                websocket.send_json({"type": "input", "text": "y"})
                _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Name: "
            for text in ("Looker", "y", "secret1", "secret1", "elf", "m", "mage", "g", "n", "dagger"):
                websocket.send_json({"type": "input", "text": text})
                _, prompt = _receive_until_prompt(websocket, limit=200)
            _, prompt = _continue_motd_prompt(websocket, prompt)
            assert prompt["session_state"] == "game"

        with client.websocket_connect("/ws") as websocket:
            _, prompt = _receive_until_prompt(websocket)
            if prompt["text"] == "Do you want ANSI? (Y/n) ":
                websocket.send_json({"type": "input", "text": "y"})
                _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Name: "
            websocket.send_json({"type": "input", "text": "Looker"})
            _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Password: "
            websocket.send_json({"type": "input", "text": "secret1"})
            _, prompt = _receive_until_prompt(websocket, limit=200)
            _, prompt = _continue_motd_prompt(websocket, prompt)
            assert prompt["session_state"] == "game"

            # Snapshot what the live registry says the loaded character's room is.
            live_char = next(
                (c for c in character_registry if getattr(c, "name", "") == "Looker"),
                None,
            )
            assert live_char is not None, "reconnected Looker not in character_registry"
            live_room = live_char.room
            assert live_room is not None, "reconnected Looker has no room"
            expected_name = live_room.name
            expected_desc = (live_room.description or "").strip()
            assert expected_name, "room registry has empty name for reconnect target"
            assert expected_desc, "room registry has empty description for reconnect target"

            websocket.send_json({"type": "input", "text": "look"})
            seen, prompt = _receive_until_prompt(websocket, limit=200)
            assert prompt["session_state"] == "game"
            transcript = "".join(payload.get("text", "") for payload in seen)

        # ROM src/act_info.c:1084-1086 — room name printed bracketed by color codes.
        assert expected_name in transcript, (
            f"room name {expected_name!r} from registry not in look transcript:\n{transcript}"
        )
        # ROM src/act_info.c:1098-1105 — room description printed when arg is empty.
        # Use the first non-empty line as a discriminator so we catch stale snapshots.
        desc_signature = next(
            (line.strip() for line in expected_desc.splitlines() if line.strip()),
            expected_desc[:40],
        )
        assert desc_signature in transcript, (
            f"room description signature {desc_signature!r} from registry not in look transcript:\n{transcript}"
        )


def test_websocket_login_emits_board_summary_after_initial_look() -> None:
    """ROM CON_READ_MOTD ends with `do_board("")` after the initial look."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            _, prompt = _receive_until_prompt(websocket)
            if prompt["text"] == "Do you want ANSI? (Y/n) ":
                websocket.send_json({"type": "input", "text": "y"})
                _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Name: "

            for text in (
                "BoardLogin",
                "y",
                "secret1",
                "secret1",
                "elf",
                "m",
                "mage",
                "g",
                "n",
                "dagger",
            ):
                websocket.send_json({"type": "input", "text": text})
                _, prompt = _receive_until_prompt(websocket, limit=200)

            seen, prompt = _continue_motd_prompt(websocket, prompt)
            assert prompt["session_state"] == "game"
            transcript = "".join(payload.get("text", "") for payload in seen)
            assert "You current board is" in transcript


def test_websocket_login_emits_rom_welcome_line_on_entering_game() -> None:
    """ROM CON_READ_MOTD writes the welcome line when play actually begins."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            _, prompt = _receive_until_prompt(websocket)
            if prompt["text"] == "Do you want ANSI? (Y/n) ":
                websocket.send_json({"type": "input", "text": "y"})
                _, prompt = _receive_until_prompt(websocket)
            assert prompt["text"] == "Name: "

            for text in (
                "WelcomeLine",
                "y",
                "secret1",
                "secret1",
                "elf",
                "m",
                "mage",
                "g",
                "n",
                "dagger",
            ):
                websocket.send_json({"type": "input", "text": text})
                seen, prompt = _receive_until_prompt(websocket, limit=200)

            motd_transcript = "".join(payload.get("text", "") for payload in seen)
            assert prompt["session_state"] == "motd"
            assert "Welcome to ROM 2.4.  Please don't feed the mobiles!" not in motd_transcript
            assert "You have been equipped by Mota." not in motd_transcript

            websocket.send_json({"type": "input", "text": ""})
            seen, prompt = _receive_until_prompt(websocket, limit=200)
            transcript = "".join(payload.get("text", "") for payload in seen)
            assert prompt["session_state"] == "game"
            assert "Welcome to ROM 2.4.  Please don't feed the mobiles!" in transcript
            assert "You have been equipped by Mota." in transcript
