"""PASSWORD-001 — do_password wrong-password WAIT_STATE uses UMAX, not assignment.

ROM ``do_password`` (``src/act_info.c:2890-2895``) applies ``WAIT_STATE(ch, 40)``
on a wrong old-password — the macro is ``ch->wait = UMAX(ch->wait, 40)``. The
Python ``mud/commands/character.py:do_password`` set ``ch.wait = 40`` (plain
assignment), which *lowers* a higher existing wait to 40 instead of preserving it.
Same UMAX-vs-assign class as PICK-002.
"""

from __future__ import annotations

from mud.world import create_test_character


def _char_with_pwd(monkeypatch):
    from mud.commands import character as character_mod

    ch = create_test_character("Secretkeeper", room_vnum=3001)
    ch.is_npc = False
    # Force the wrong-password branch regardless of the stored hash.
    monkeypatch.setattr(character_mod, "verify_password", lambda *a, **k: False)
    # Ensure pcdata.pwd is truthy so we reach the verify step.
    ch.pcdata.pwd = "irrelevant-hash"
    return ch, character_mod


def test_wrong_password_applies_wait_40_from_zero(monkeypatch):
    """ROM src/act_info.c:2895 — WAIT_STATE(ch, 40) on a wrong password."""
    ch, character_mod = _char_with_pwd(monkeypatch)
    ch.wait = 0

    result = character_mod.do_password(ch, "wrongold newpassword")

    assert "Wrong password" in result, result
    assert ch.wait == 40, f"expected wait 40, got {ch.wait}"


def test_wrong_password_wait_is_umax_not_assignment(monkeypatch):
    """UMAX must preserve a higher existing wait, not lower it to 40."""
    ch, character_mod = _char_with_pwd(monkeypatch)
    ch.wait = 100  # already higher than 40

    character_mod.do_password(ch, "wrongold newpassword")

    assert ch.wait == 100, f"UMAX must preserve the higher existing wait, got {ch.wait}"
