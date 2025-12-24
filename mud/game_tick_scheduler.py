"""Shared game tick scheduler for all MUD servers.

Provides a standardized way to run the ROM 2.4 game tick loop
alongside any server (telnet, websocket, SSH).

ROM runs at 4 pulses per second (PULSE_PER_SECOND = 4).
"""

from __future__ import annotations

import asyncio

from mud.config import PULSE_PER_SECOND
from mud.game_loop import game_tick


async def start_game_tick_scheduler() -> None:
    """Start the game tick scheduler running at ROM cadence.

    This should be called from any server that wants the game world
    to continue evolving (time advancement, mob AI, combat, etc.).

    The scheduler runs at PULSE_PER_SECOND (4 Hz) which matches
    ROM's timing: every 0.25 seconds.
    """
    tick_interval = 1.0 / PULSE_PER_SECOND  # 0.25 seconds per pulse

    print(f"[Game] Starting game tick scheduler ({PULSE_PER_SECOND} Hz)")

    async def scheduler_loop():
        """Run game_tick() at ROM cadence (4 Hz)."""
        while True:
            try:
                game_tick()
            except Exception as e:
                print(f"[Game] Game tick error: {e}")
            await asyncio.sleep(tick_interval)

    # Start the scheduler and run forever
    scheduler_task = asyncio.create_task(scheduler_loop())

    try:
        # Wait forever - this keeps the scheduler running
        await asyncio.Future()
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
        print("[Game] Game tick scheduler stopped")
