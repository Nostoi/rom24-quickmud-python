"""INV-001 — skill-registry caster lines must reach a connected PC on the socket
exactly once, never via the mailbox in addition.

ROM `src/skills.c:953`/`967` (`check_improve`) and `src/magic.c:551`
(`spell_*` failure) all write the caster-facing line via `send_to_char(buf, ch)`
— a single delivery channel to the descriptor.  The Python port routed these
through a local `_deliver_message` (socket-only, no mailbox fallback) *and*
`caster.messages.append(...)`.  For a connected PC that is dual delivery: the
async socket task delivers once, then the connection read loop replays the
mailbox copy on the player's NEXT prompt — the INV-001 SINGLE-DELIVERY class.

Fix: route every caster line through `mud.utils.messaging.push_message` (async
socket for connected PCs *xor* mailbox for tests/disconnected) and drop the
paired `caster.messages.append`, retiring the divergent `_deliver_message` copy.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from mud.models.character import Character
from mud.skills.registry import SkillRegistry
from mud.utils import rng_mm


def load_registry() -> SkillRegistry:
    reg = SkillRegistry()
    reg.load(Path("data/skills.json"))
    return reg


class _RecordingConn:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def _connected_caster() -> tuple[Character, _RecordingConn]:
    caster = Character(
        mana=20,
        ch_class=0,
        level=10,
        is_npc=False,
        perm_stat=[13, 18, 13, 13, 13],
        mod_stat=[0, 0, 0, 0, 0],
        skills={"fireball": 50},
    )
    caster.messages = []
    conn = _RecordingConn()
    caster.connection = conn
    return caster, conn


def test_failure_message_reaches_connected_caster_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed cast's failure line must hit the socket once and not the mailbox."""

    async def scenario():
        reg = load_registry()
        reg.get("fireball").rating[0] = 4
        caster, conn = _connected_caster()
        target = Character()

        # skill check fails (percent 100 > learned 50); check_improve gate fails
        # (range 1000 > chance) so no improvement line is emitted.
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 100)
        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1000)

        result = reg.use(caster, "fireball", target)
        for _ in range(5):
            await asyncio.sleep(0)
        return result.message, conn.sent, list(caster.messages)

    failure_message, sent, mailbox = asyncio.run(scenario())
    assert sent.count(failure_message) == 1, f"failure line must reach connected caster's socket once; sent={sent}"
    assert failure_message not in mailbox, f"failure line stranded/duplicated in mailbox for a connected PC: {mailbox}"


def test_improve_message_reaches_connected_caster_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """The "become better" improvement line must hit the socket once, not the mailbox."""

    async def scenario():
        reg = load_registry()
        reg.get("fireball").rating[0] = 4
        caster, conn = _connected_caster()
        target = Character()

        # skill check succeeds (percent 30 <= learned 50); improve gate passes
        # (range 1 <= chance); improve chance hits (percent 30 < improve_chance 50).
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 30)
        monkeypatch.setattr(rng_mm, "number_range", lambda a, b: 1)

        reg.use(caster, "fireball", target)
        for _ in range(5):
            await asyncio.sleep(0)
        return conn.sent, list(caster.messages)

    sent, mailbox = asyncio.run(scenario())
    improve = next((m for m in sent if "become better" in m), None)
    assert improve is not None, f"improve line must reach connected caster's socket; sent={sent}"
    assert sent.count(improve) == 1, f"improve line duplicated on socket; sent={sent}"
    assert not any("become better" in m for m in mailbox), f"improve line stranded/duplicated in mailbox: {mailbox}"


def test_recovering_line_reaches_connected_caster_on_socket() -> None:
    """The wait-state "You are still recovering." line must hit the socket, not
    the mailbox, for a connected caster.

    ``SkillRegistry.use`` gates on ``caster.wait > 0`` and (previously) appended
    the recovery line straight to ``caster.messages`` before ``raise``-ing.  It
    has no production callers (only tests invoke ``use``), so this was a single
    mailbox delivery — not a double — but for a connected PC it is still the
    wrong channel (late: the mailbox drains only on the next command).  Routed
    through ``push_message`` so a connected caster sees it at action time; the
    disconnected/test path (``test_skills.py:225``) keeps the mailbox fallback.
    """

    async def scenario():
        reg = load_registry()
        caster, conn = _connected_caster()
        caster.wait = 10  # already recovering → the wait-state guard fires first
        target = Character()
        with pytest.raises(ValueError):
            reg.use(caster, "fireball", target)
        for _ in range(5):
            await asyncio.sleep(0)
        return conn.sent, list(caster.messages)

    sent, mailbox = asyncio.run(scenario())
    assert "You are still recovering." in sent, f"recovery line must reach connected caster's socket; sent={sent}"
    assert "You are still recovering." not in mailbox, (
        f"recovery line stranded in mailbox for a connected PC: {mailbox}"
    )
