"""Integration test: PC death must NOT disconnect the WebSocket descriptor.

ROM Reference: src/handler.c:2103-2187 ``extract_char(ch, FALSE)`` for PCs leaves
the descriptor open; PC respawns at clan hall / altar with hp/mana/move set to
min 1 and position RESTING. The connection persists -- ROM does not call
``close_socket`` on death.

Test runs the death path inside an asyncio event loop (matching the production
WS / Telnet server, where ``async_game_loop`` schedules ``game_tick`` from a
running loop).
"""

from __future__ import annotations

import asyncio

import pytest

from mud.combat.engine import apply_damage, multi_hit
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.utils.prompt import bust_a_prompt
from mud.world import create_test_character, initialize_world


class _FakeConn:
    """Minimal stand-in for a WebSocket / Telnet connection."""

    def __init__(self) -> None:
        self.closed = False
        self.sent: list[str] = []
        self.prompts: list[str] = []
        self.lines: list[str] = []

    async def send(self, data: str) -> None:
        self.sent.append(data)

    async def send_line(self, data: str) -> None:
        self.lines.append(data)

    async def send_prompt(self, prompt: str, *, go_ahead: bool = False) -> None:
        self.prompts.append(prompt)

    async def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def _reset_registry():
    character_registry.clear()
    yield
    character_registry.clear()


def _ensure_world() -> None:
    initialize_world("area/area.lst")


def test_pc_death_keeps_connection_open() -> None:
    """Run the death path under a real asyncio loop (production-equivalent)."""

    async def _body():
        _ensure_world()

        pc = create_test_character("Tester", 3001)
        pc.is_npc = False
        pc.level = 10
        pc.hit = 1
        pc.max_hit = 50
        pc.mana = 10
        pc.max_mana = 10
        pc.move = 10
        pc.max_move = 10
        pc.clan = 0  # forces ROOM_VNUM_ALTAR (3054)

        conn = _FakeConn()
        pc.connection = conn
        pc.desc = conn

        room = pc.room
        assert room is not None

        attacker = Character(name="Killer", is_npc=True, level=20)
        attacker.hit = 100
        attacker.max_hit = 100
        room.add_character(attacker)

        # Kill the PC. apply_damage runs the full death path with show=True so
        # _push_message / room.broadcast / _send all fire (matching production
        # violence_tick combat path).
        apply_damage(attacker, pc, 500, dt=None, show=True)

        # Drain any tasks _push_message / broadcast scheduled (mirrors the
        # event-loop yield between game_tick and the WS read loop).
        for _ in range(5):
            await asyncio.sleep(0)

        # ROM-parity post-death state.
        assert pc in character_registry, "PC removed from character_registry"
        assert pc.room is not None, "PC has no room (death-room placement failed)"
        assert pc.position == Position.RESTING, f"position={pc.position!r}"
        assert pc.hit >= 1
        assert pc.mana >= 1
        assert pc.move >= 1

        # Disconnect-bug guards.
        assert pc.connection is conn, "PC.connection nulled on death"
        assert getattr(pc, "desc", None) is conn, "PC.desc nulled on death"
        assert not conn.closed, "conn.close() called on death"

        # The WS read loop calls bust_a_prompt(char) every iteration. If this
        # raises after death, the loop's outer except Exception breaks the
        # connection (mud/net/connection.py:1766-1768).
        try:
            rendered = bust_a_prompt(pc)
        except Exception as exc:  # pragma: no cover - this is what we're checking
            pytest.fail(f"bust_a_prompt raised after PC death: {exc!r}")
        assert isinstance(rendered, str)

        # And conn.send_prompt must accept the prompt without raising.
        await conn.send_prompt(rendered)

    asyncio.run(_body())
