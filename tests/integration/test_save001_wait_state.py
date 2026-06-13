"""SAVE-001 — do_save applies WAIT_STATE(ch, 4 * PULSE_VIOLENCE).

ROM ``do_save`` (``src/act_comm.c:1522-1532``)::

    save_char_obj (ch);
    send_to_char ("Saving. ...\n\r", ch);
    WAIT_STATE (ch, 4 * PULSE_VIOLENCE);

``PULSE_VIOLENCE`` == 12 (``src/merc.h:155-156``), so saving costs 48 pulses of
wait — an anti-spam lag. The Python ``mud/commands/session.py:do_save`` saved and
returned the message but applied no WAIT_STATE, so a player could spam ``save``
freely. (The audit doc's "save_char_obj() + WAIT_STATE ✅ 100%" row was a stale
false-✅.)
"""

from __future__ import annotations

import pytest

from mud.config import get_pulse_violence
from mud.models.room import Room
from mud.registry import room_registry
from mud.world import create_test_character


@pytest.fixture(autouse=True)
def _room_3001():
    created = 3001 not in room_registry
    if created:
        room_registry[3001] = Room(vnum=3001, name="Test Room", description="")
    yield
    if created:
        room_registry.pop(3001, None)


def test_do_save_applies_wait_state(monkeypatch):
    """ROM src/act_comm.c:1530 — WAIT_STATE(ch, 4 * PULSE_VIOLENCE) == 48."""
    from mud.commands import session as session_mod

    # Avoid touching the real DB — stub the save.
    monkeypatch.setattr(session_mod, "save_character", lambda ch: None, raising=False)
    import mud.account.account_manager as am

    monkeypatch.setattr(am, "save_character", lambda ch: None)

    ch = create_test_character("Saver", room_vnum=3001)
    ch.is_npc = False
    ch.wait = 0

    result = session_mod.do_save(ch, "")

    assert "Saving" in result, result
    assert ch.wait == 4 * get_pulse_violence() == 48, f"expected wait 48, got {ch.wait}"


def test_do_save_wait_state_uses_umax(monkeypatch):
    """WAIT_STATE is UMAX — a higher existing wait is preserved, not lowered to 48."""
    import mud.account.account_manager as am
    from mud.commands import session as session_mod

    monkeypatch.setattr(am, "save_character", lambda ch: None)

    ch = create_test_character("Saver", room_vnum=3001)
    ch.is_npc = False
    ch.wait = 100  # already higher than 48

    session_mod.do_save(ch, "")

    assert ch.wait == 100, f"UMAX must preserve the higher existing wait, got {ch.wait}"
