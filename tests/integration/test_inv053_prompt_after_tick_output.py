"""INV-053 — PROMPT-AFTER-TICK-OUTPUT.

ROM `src/comm.c:game_loop_unix` runs one output phase per pulse, AFTER
`update_handler()`. For every descriptor where the game produced output this
pulse (`d->outtop > 0`) OR the player typed a command (`d->fcommand`), it calls
`process_output(d, TRUE)` which flushes the buffer AND appends a fresh
`bust_a_prompt` (`src/comm.c:868-883`, `1376-1377`). So any tick-generated
message (combat round, a spell cast on you by a mob/mobprog, a poison/plague
affect) is followed by a refreshed prompt showing post-tick HP/mana/move within
the same 250 ms pulse.

The Python port splits ROM's single loop into two coroutines: `async_game_loop`
drives `game_tick()` (messages pushed via `asyncio.create_task(send_to_char)`),
and a per-connection loop renders the prompt only at its top, then BLOCKS on the
player's next command. Tick-pushed messages therefore reached the client with no
trailing prompt — the HP/mana on the prompt line stayed frozen until the player
typed something. Silent regen (no message) is correctly invisible in ROM too, so
the contract is specifically: *output → prompt*, never *regen → prompt*.

Enforcement mirrors ROM's once-per-pulse output phase: `begin_tick_output()`
wraps the synchronous `game_tick()`, every tick-context delivery chokepoint
marks the recipient, and `schedule_tick_prompts()` (called after the tick) emits
one fresh prompt per marked, still-connected PC.
"""

from __future__ import annotations

import asyncio

import pytest

from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.net.connection import schedule_tick_prompts
from mud.net.protocol import broadcast_room
from mud.utils.messaging import begin_tick_output, end_tick_output, push_message, reset_prompt_dirty


@pytest.fixture(autouse=True)
def _reset_tick_state():
    reset_prompt_dirty()
    yield
    reset_prompt_dirty()


class _RecordingConn:
    """Records message sends and prompt sends in arrival order."""

    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    async def send_line(self, msg: str) -> None:
        self.events.append(("msg", msg))

    async def send(self, msg: str) -> None:
        self.events.append(("msg", msg))

    async def send_prompt(self, prompt: str, *, go_ahead: bool | None = None) -> None:
        self.events.append(("prompt", prompt))


def _connected_pc(name: str = "Conn", *, hit: int = 30) -> tuple[Character, _RecordingConn]:
    pc = Character(
        name=name,
        is_npc=False,
        level=10,
        position=int(Position.STANDING),
        hit=hit,
        max_hit=50,
        mana=20,
        move=40,
    )
    pc.messages = []
    conn = _RecordingConn()
    pc.connection = conn
    return pc, conn


async def _drain() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


def test_tick_output_appends_fresh_prompt_with_post_tick_hp() -> None:
    """A message pushed during the tick is followed by a prompt showing new HP."""

    async def scenario():
        pc, conn = _connected_pc(hit=30)
        begin_tick_output()
        try:
            push_message(pc, "{RYou take 10 damage from the plague!{x")
            pc.hit = 20  # affect_update applied the damage this pulse
        finally:
            end_tick_output()
        schedule_tick_prompts()
        await _drain()
        return conn.events

    events = asyncio.run(scenario())
    kinds = [kind for kind, _ in events]
    assert "prompt" in kinds, f"tick output must be followed by a fresh prompt: {events}"
    # ROM appends the prompt AFTER the buffered output — message precedes prompt.
    assert kinds.index("msg") < kinds.index("prompt"), f"prompt must follow the message: {events}"
    prompt_text = next(text for kind, text in events if kind == "prompt")
    assert "20hp" in prompt_text, f"prompt must show post-tick HP (20), got: {prompt_text!r}"


def test_silent_regen_emits_no_prompt() -> None:
    """Idle regen with no message must NOT push a prompt — ROM-correct (parity)."""

    async def scenario():
        pc, conn = _connected_pc(hit=30)
        begin_tick_output()
        try:
            pc.hit = 31  # silent hit_gain — NO send_to_char in ROM char_update
        finally:
            end_tick_output()
        schedule_tick_prompts()
        await _drain()
        return conn.events

    events = asyncio.run(scenario())
    assert events == [], f"silent regen must not emit a prompt (ROM char_update is silent): {events}"


def test_command_context_push_does_not_trigger_a_tick_prompt() -> None:
    """A push outside tick context (e.g. a social during command processing) must
    not leave the PC marked, or the next tick emits a stray double prompt."""

    async def scenario():
        pc, conn = _connected_pc(hit=30)
        # Command context: NOT wrapped in begin/end_tick_output.
        push_message(pc, "You smile happily.")
        # A later tick fires with no NEW output for this PC.
        begin_tick_output()
        end_tick_output()
        schedule_tick_prompts()
        await _drain()
        return conn.events

    events = asyncio.run(scenario())
    kinds = [kind for kind, _ in events]
    assert ("msg", "You smile happily.") in events, events
    assert kinds.count("prompt") == 0, f"command-context push must not arm a tick prompt: {events}"


def test_broadcast_room_during_tick_marks_bystander() -> None:
    """broadcast_room bypasses push_message (direct create_task); it must still
    mark connected bystanders for a tick prompt (ROM: they had outtop > 0)."""

    async def scenario():
        room = Room(vnum=1, name="r", description="", room_flags=0, sector_type=0)
        room.people = []
        pc, conn = _connected_pc(hit=30)
        pc.room = room
        room.people.append(pc)
        begin_tick_output()
        try:
            broadcast_room(room, "A fountain bubbles softly.")
        finally:
            end_tick_output()
        schedule_tick_prompts()
        await _drain()
        return conn.events

    events = asyncio.run(scenario())
    kinds = [kind for kind, _ in events]
    assert "prompt" in kinds, f"broadcast_room bystander must get a tick prompt: {events}"
