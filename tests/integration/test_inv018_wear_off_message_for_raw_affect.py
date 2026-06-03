"""Raw AffectData entries (no spell_effects shadow) must emit msg_off on expiry.

ROM ``src/update.c:777-781`` emits ``skill_table[paf->type].msg_off`` to the
character when a positive-typed affect expires — regardless of which apply
path created the affect.  Every AFF_ entry in ``ch->affected`` gets the
wear-off line based on its skill SN, including ones landed via:

  - ``affect_to_char`` from plague spread
    (``src/update.c:828-840`` → ``mud/game_loop.py:614-624`` — bare
    ``AffectData`` built from constants, no ``apply_spell_effect`` shadow);
  - ``spell_poison`` poisoning food/drink that transfers to ch;
  - any future call path that bypasses ``apply_spell_effect``.

Python's ``mud/affects/engine.py:tick_spell_effects`` only yields a wear-off
message when the expiring affect's name appears in the ``spell_effects``
dict (line 70: ``isinstance(spell_name, str) and spell_name in effects``).
Raw AffectData entries — written directly to ``character.affected`` without
a parallel ``apply_spell_effect`` call — wear off silently.

ROM keys the message off ``skill_table[paf->type].msg_off`` (a per-skill
lookup), not off the affect struct.  Python's faithful equivalent is the
``skill_registry`` ``messages["wear_off"]`` field, mirroring the precedent
at ``mud/game_loop.py:1121-1131`` (``_broadcast_object_wear_off``) which
already does this hybrid lookup for object affects: prefer the affect's
own attribute, fall back to the skill registry by spell name.

Two tests pin the two paths:

1. Dynamic ``wear_off_message`` attribute set on the affect must surface.
2. Skill-registry fallback fires when the affect has no dynamic attribute
   set (the actual production trigger from plague-spread).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mud.affects.engine import tick_spell_effects
from mud.models.character import AffectData, Character, character_registry
from mud.models.constants import AffectFlag
from mud.skills.registry import skill_registry


@pytest.fixture(autouse=True)
def _isolated_registry():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)


@pytest.fixture
def loaded_skills():
    """Load data/skills.json into the global skill_registry for the test."""
    skills_path = Path(__file__).resolve().parents[2] / "data" / "skills.json"
    skill_registry.load(skills_path)
    return skill_registry


def _make_plague_affect(duration: int) -> AffectData:
    return AffectData(
        type="plague",
        level=20,
        duration=duration,
        location=0,
        modifier=0,
        bitvector=int(AffectFlag.PLAGUE),
    )


def _tick_until_expiry(ch: Character) -> list[str]:
    """Tick spell effects until expiry message lands (or 5 ticks max)."""
    collected: list[str] = []
    for _ in range(5):
        msgs = tick_spell_effects(ch)
        collected.extend(msgs)
        if msgs:
            return collected
        # affect duration was decremented; the next tick is the expiry pass
    return collected


def test_raw_affect_emits_dynamic_wear_off_message_on_expiry():
    """If the AffectData carries its own wear_off_message attribute, the
    tick must surface it on expiry — mirrors the object-affect precedent
    at game_loop.py:1121-1131."""
    ch = Character(name="Victim", is_npc=False)
    ch.messages = []
    character_registry.append(ch)

    affect = _make_plague_affect(duration=1)
    sentinel = "SENTINEL_DYNAMIC_PREFERRED_OVER_REGISTRY"
    affect.wear_off_message = sentinel
    ch.affected = [affect]
    ch.affected_by = int(AffectFlag.PLAGUE)

    msgs = _tick_until_expiry(ch)

    assert any(sentinel in m for m in msgs), (
        f"raw AffectData with dynamic wear_off_message must surface it on expiry; got {msgs!r}"
    )


def test_raw_affect_falls_back_to_skill_registry_wear_off(loaded_skills):
    """The production trigger: plague-spread creates an AffectData with no
    wear_off_message attribute. ROM looks up skill_table[paf->type].msg_off
    directly; Python must fall back to skill_registry by spell name."""
    plague_skill = loaded_skills.get("plague")
    rom_wear_off = (plague_skill.messages or {}).get("wear_off")
    assert rom_wear_off, "test setup requires skills.json to define plague.messages.wear_off"

    ch = Character(name="Victim", is_npc=False)
    ch.messages = []
    character_registry.append(ch)

    affect = _make_plague_affect(duration=1)
    # NOTE: deliberately NO wear_off_message attribute set — mirrors the
    # plague-spread path at mud/game_loop.py:614-624 which never sets one.
    ch.affected = [affect]
    ch.affected_by = int(AffectFlag.PLAGUE)

    msgs = _tick_until_expiry(ch)

    assert any(rom_wear_off in m for m in msgs), (
        f"raw AffectData with no dynamic wear_off_message must fall back "
        f"to skill_registry messages['wear_off'] for type {affect.type!r}; "
        f"expected substring {rom_wear_off!r}, got {msgs!r}"
    )
