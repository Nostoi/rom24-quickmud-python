"""`kill` must deliver each combat line to a connected PC exactly ONCE.

Broadens INV-001 (SINGLE-DELIVERY). The existing
``test_message_delivery_no_duplicate.py`` proves ``_push_message`` itself is
single-channel for a connected PC, but it never exercises a *command whose
return value re-delivers the pushed line*. ``do_kill`` did exactly that: it
returned ``multi_hit(...)[0]`` — the same attacker line ``apply_damage`` had
already pushed via ``_push_message`` — so ``mud/net/connection.py``'s read loop
sent it twice (once via the async ``_push_message`` send, once via
``send_to_char(char, response)``). Every other ``multi_hit`` caller
(``do_murder``, ``violence_tick``, ``assist``, aggressive AI, spec_funs)
discards the return and relies on the push, matching ROM's void ``do_kill``
(``src/fight.c`` — all output flows through ``act()``/``send_to_char`` to the
descriptor, there is no return channel).

This test drives the kill command through the *same delivery sequence* as the
live connection loop (``mud/net/connection.py``: ``process_command`` →
``send_to_char(char, response)`` → drain ``char.messages``) so the count it
asserts is exactly what a connected player's socket receives.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from mud.commands import process_command
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.net.protocol import send_to_char
from mud.skills import load_skills
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


class _RecordingConn:
    """Connection stub matching the duck-typed interface ``send_to_char`` uses."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def _deliver_one_command(char: Character, conn: _RecordingConn, command: str) -> list[str]:
    """Replay mud/net/connection.py's per-command delivery and return socket sends."""

    async def scenario() -> list[str]:
        response = process_command(char, command)
        # connection loop: send the command's return value first ...
        await send_to_char(char, response)
        # ... let the fire-and-forget _push_message create_task() sends fire ...
        for _ in range(5):
            await asyncio.sleep(0)
        # ... then drain the mailbox (empty for a connected PC, by INV-001).
        while char.messages:
            await send_to_char(char, char.messages.pop(0))
        return list(conn.sent)

    return asyncio.run(scenario())


def test_kill_command_delivers_attack_line_once() -> None:
    load_skills(Path("data/skills.json"))
    rng_mm.seed_mm(12345)

    room = Room(vnum=9001)
    attacker = Character(name="Attacker", is_npc=False, level=10)
    attacker.position = Position.STANDING
    attacker.skills["hand to hand"] = 100
    victim = Character(name="drunk", is_npc=True, level=2)
    victim.max_hit = victim.hit = 1000  # survive one round, no death path
    for ch in (attacker, victim):
        room.add_character(ch)

    conn = _RecordingConn()
    attacker.connection = conn

    sent = _deliver_one_command(attacker, conn, "kill drunk")

    attack_lines = [s for s in sent if "drunk" in s]
    assert len(attack_lines) == 1, (
        f"kill combat line delivered {len(attack_lines)}x to the connected PC "
        f"(expected 1 — SINGLE-DELIVERY/INV-001). Socket sends: {sent}"
    )


def test_kill_to_death_delivers_killing_blow_once_no_kill_line(monkeypatch: pytest.MonkeyPatch) -> None:
    """A fatal `kill` blow delivers the killing dam_message exactly once and no
    extra line. ROM (``src/fight.c:859-862``) sends the killer NOTHING on the
    death branch — only the victim (``You have been KILLED!!``) and the room
    (``$n is DEAD!!``). The killer's last line is the killing-blow dam_message,
    pushed by ``apply_damage`` before the death branch. ``_handle_death``'s
    returned ``You kill X.`` is a non-ROM line that only surfaced via
    ``do_kill``'s return; with the SINGLE-DELIVERY fix it is no longer delivered.
    """
    load_skills(Path("data/skills.json"))
    initialize_world("area/area.lst")
    # nat-19 forces a hit through the ROM THAC0 roll (FIGHT-019 model).
    monkeypatch.setattr(rng_mm, "number_bits", lambda *_: 19)
    monkeypatch.setattr(rng_mm, "number_range", lambda *args: args[1])

    attacker = create_test_character("Attacker", 3001)
    attacker.position = Position.STANDING
    attacker.skills["hand to hand"] = 100
    attacker.hitroll = 100
    victim = create_test_character("Victim", 3001)
    victim.is_npc = True
    victim.max_hit = victim.hit = 1  # one blow kills

    conn = _RecordingConn()
    attacker.connection = conn

    sent = _deliver_one_command(attacker, conn, "kill victim")

    assert victim.position == Position.DEAD, f"victim should be dead; sends={sent}"
    # The killer's combat line is the killing-blow dam_message, pushed by
    # apply_damage before the death branch — it must survive the fix (delivered
    # exactly once, not dropped). ROM-faithful damage messages render as
    # `{2...{x` (fight_yhit, green) to the attacker.
    killing_dam_message = [s for s in sent if s.startswith("{2") and "Victim" in s]
    assert len(killing_dam_message) == 1, f"killing-blow dam_message must be pushed exactly once; sends={sent}"
    # ROM (src/fight.c:859-862) sends the killer NOTHING on the death branch —
    # `You kill X.` is a non-ROM line that only surfaced via do_kill's return.
    assert not any("You kill" in s for s in sent), f"ROM sends the killer no 'You kill' line on death; got: {sent}"
