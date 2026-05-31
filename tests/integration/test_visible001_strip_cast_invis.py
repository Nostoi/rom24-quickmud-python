"""VISIBLE-001 — `do_visible` must actually strip cast invisibility.

ROM `do_visible` (`src/act_move.c:1549-1560`) does
``affect_strip(ch, gsn_invis); affect_strip(ch, gsn_mass_invis);
affect_strip(ch, gsn_sneak);`` then clears the AFF bits. ``affect_strip``
removes the affect *entirely* (its AFFECT_DATA, its modifiers, its bit).

The Python `do_visible` (`mud/commands/thief_skills.py`) instead called
``_strip_affect(char, "invisibility")`` / ``"mass invisibility"`` — but the
invisibility spells register ``SpellEffect(name="invis")`` /
``name="mass invis"`` (`mud/skills/handlers.py`). The names never matched, so
only the bare ``affected_by`` bit was cleared while the ``spell_effects["invis"]``
entry (and, post-GL-029, its shadow ``AffectData``) lingered — later firing a
spurious "You fade back into existence." wear-off, and leaving a re-settable
INVISIBLE source on ``char.affected``.

This test casts invisibility through the production apply path, runs
``do_visible``, and asserts the effect is fully gone (no spell_effects entry, no
shadow, no AFF bit) and that ticking afterwards emits no spurious wear-off.
"""

from __future__ import annotations

from mud.affects.engine import tick_spell_effects
from mud.commands.thief_skills import do_visible
from mud.models.character import Character, SpellEffect
from mud.models.constants import AffectFlag

_INVIS_WEAR_OFF = "You fade back into existence."


def _invisible_char(duration: int = 24) -> Character:
    ch = Character(level=12)
    ch.affected = []
    # Faithful to the production cast path (mud/skills/handlers.py:invis).
    ch.apply_spell_effect(
        SpellEffect(
            name="invis",
            duration=duration,
            level=12,
            affect_flag=AffectFlag.INVISIBLE,
            wear_off_message=_INVIS_WEAR_OFF,
        )
    )
    return ch


def test_do_visible_strips_cast_invisibility_completely():
    ch = _invisible_char()
    assert ch.has_affect(AffectFlag.INVISIBLE)
    assert "invis" in ch.spell_effects

    do_visible(ch, "")

    assert "invis" not in ch.spell_effects, "do_visible must remove the cast invis spell_effect"
    assert not ch.has_affect(AffectFlag.INVISIBLE), "AFF_INVISIBLE bit must be cleared"
    assert not any(getattr(a, "type", None) == "invis" for a in ch.affected), (
        "no invis shadow AffectData may linger on ch.affected"
    )


def test_do_visible_prevents_spurious_wear_off_message():
    # Short duration so a *lingering* (un-stripped) effect would expire and fire
    # its wear-off within the tick window — the failure mode VISIBLE-001 causes.
    ch = _invisible_char(duration=2)
    do_visible(ch, "")

    # With the effect already stripped, no later tick may emit the wear-off.
    messages: list[str] = []
    for _ in range(4):
        messages.extend(tick_spell_effects(ch))

    assert not any(_INVIS_WEAR_OFF in m for m in messages), (
        "stripped invisibility must not later fire 'You fade back into existence.'"
    )
