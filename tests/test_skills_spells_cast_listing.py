"""Regression coverage for do_skills, do_spells, and do_cast.

These tests guard against the bug class where the listing/cast commands read
from a non-existent data source (a phantom skill-table registry attribute) or use
exact-match parsing that breaks multi-word spell names. Both regressions
silently produced "no skills found" / "you don't know any spells of that name"
even when the character had learned skills and spells (provable via the
`practice` command, which uses the canonical `skill_registry.skills` source).

ROM parity references:
- `src/skills.c:381-485` — `do_skills`
- `src/skills.c:256-378` — `do_spells`
- `src/magic.c:299-360` — `do_cast` (uses `find_spell` for prefix matching)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mud.commands.combat import do_cast
from mud.commands.misc_info import do_skills, do_spells
from mud.models.character import Character
from mud.models.constants import Position
from mud.skills.registry import load_skills, skill_registry


@pytest.fixture(autouse=True)
def _load_skills():
    skill_registry.skills.clear()
    skill_registry.handlers.clear()
    load_skills(Path("data/skills.json"))
    yield
    skill_registry.skills.clear()
    skill_registry.handlers.clear()


def _make_mage(**overrides) -> Character:
    """Mage (class index 0) with a known skill and a known spell."""

    defaults = {
        "name": "Tester",
        "level": 20,
        "ch_class": 0,
        "is_npc": False,
        "perm_stat": [0, 18, 0, 0, 0],
        "mana": 200,
        "position": int(Position.STANDING),
        "wait": 0,
        "skills": {"dagger": 75, "magic missile": 85},
    }
    defaults.update(overrides)
    return Character(**defaults)


# ---------------------------------------------------------------------------
# do_skills (ROM src/skills.c:381-485)
# ---------------------------------------------------------------------------


def test_do_skills_lists_learned_non_spell_entries():
    char = _make_mage()

    output = do_skills(char, "")

    assert output != "No skills found."
    assert "dagger" in output
    # ROM groups by class-level header
    assert "Level " in output
    # Spells must not appear in the skills listing
    assert "magic missile" not in output


def test_do_skills_returns_no_skills_when_none_learned():
    char = _make_mage(skills={})
    assert do_skills(char, "") == "No skills found."


def test_do_skills_rejects_non_numeric_arg():
    char = _make_mage()
    # ROM: anything that isn't an "all" prefix and isn't a number errors out.
    assert do_skills(char, "garbage") == "Arguments must be numerical or all."


def test_do_skills_returns_empty_for_npc():
    npc = Character(name="Mob", is_npc=True, ch_class=0, level=20)
    assert do_skills(npc, "") == ""


# ---------------------------------------------------------------------------
# do_spells (ROM src/skills.c:256-378)
# ---------------------------------------------------------------------------


def test_do_spells_lists_learned_spell_with_mana_cost():
    char = _make_mage()

    output = do_spells(char, "")

    assert output != "No spells found."
    assert "magic missile" in output
    assert "mana" in output
    # Pure skills must not appear in the spells listing
    assert "dagger" not in output


def test_do_spells_returns_no_spells_when_none_learned():
    char = _make_mage(skills={"dagger": 75})
    assert do_spells(char, "") == "No spells found."


def test_do_spells_returns_empty_for_npc():
    npc = Character(name="Mob", is_npc=True, ch_class=0, level=20)
    assert do_spells(npc, "") == ""


# ---------------------------------------------------------------------------
# do_cast (ROM src/magic.c:299-360)
# ---------------------------------------------------------------------------


def test_do_cast_rejects_unknown_spell():
    char = _make_mage(skills={})
    assert do_cast(char, "magic missile fido") == "You don't know any spells of that name."


def test_do_cast_resolves_quoted_multi_word_spell_name():
    """ROM `one_argument` treats single-quoted strings as a single arg.

    With exact-match the previous implementation parsed `magic` and silently
    failed to find the spell. The find_spell-based path must resolve the full
    "magic missile" name and pass position/mana gates before any RNG roll.
    """

    char = _make_mage(level=1, mana=0)  # mana=0 forces a known, deterministic gate

    result = do_cast(char, "'magic missile' self")

    # We don't care if it succeeds — only that the parser found the spell and
    # advanced past the "don't know any spells" gate. Insufficient mana is the
    # next gate ROM hits, which proves the lookup worked.
    assert result != "You don't know any spells of that name."
    assert result == "You don't have enough mana."


def test_do_cast_prefix_matches_single_token_name():
    """ROM `find_spell` matches by prefix. `cast magic` against a learned
    `"magic missile"` should still resolve."""

    char = _make_mage(mana=0)

    result = do_cast(char, "magic self")

    assert result != "You don't know any spells of that name."
    assert result == "You don't have enough mana."


def test_do_cast_magic_missile_dispatches_handler_and_damages_target():
    """End-to-end regression: handler lookup uses `skill_registry.handlers`
    (not `getattr(skill, "handler", None)`), handlers are invoked with the
    (caster, target) signature, and the target is resolved via `room.people`
    (not the non-existent `room.characters`). With learned=100 and the RNG
    seeded so the percent roll succeeds, the spell must execute and the
    target must take damage."""

    from mud.models.room import Room
    from mud.utils import rng_mm

    room = Room(vnum=99000, name="Arena", description="A clean test room")
    caster = _make_mage(level=20, mana=200, skills={"magic missile": 100})
    victim = Character(name="Fido", level=20, ch_class=0, is_npc=True, hit=200, max_hit=200)
    caster.room = room
    victim.room = room
    room.people.extend([caster, victim])

    rng_mm.seed_mm(42)
    initial_hp = int(victim.hit)

    result = do_cast(caster, "'magic missile' Fido")

    assert result != "You don't know any spells of that name."
    assert "is not fully implemented yet" not in result
    assert "Spell cast failed" not in result
    # ROM intent: a successful cast either damages or, on save-for-half, at
    # least lands a hit. Either way HP should not be unchanged.
    assert victim.hit < initial_hp, f"victim hp unchanged: {victim.hit} (was {initial_hp})"
    assert caster.mana < 200, "mana should be consumed on cast"


def test_do_cast_offensive_no_target_defaults_to_fighting_victim():
    """ROM src/magic.c:371-387 — TAR_CHAR_OFFENSIVE with empty arg2
    defaults victim to ``ch->fighting`` (errors if not fighting).
    Regression: previous Python defaulted ``target = char`` so an
    offensive spell cast mid-combat without a named target hit the
    caster (`Your magic missile scratches you.`)."""

    from mud.models.room import Room
    from mud.utils import rng_mm

    room = Room(vnum=99001, name="Arena", description="A clean test room")
    caster = _make_mage(level=20, mana=200, skills={"magic missile": 100})
    victim = Character(
        name="wimpy monster",
        level=10,
        ch_class=0,
        is_npc=True,
        hit=200,
        max_hit=200,
    )
    caster.room = room
    victim.room = room
    room.people.extend([caster, victim])
    caster.fighting = victim  # mirrors ROM ch->fighting set by attack_round

    rng_mm.seed_mm(42)
    caster_initial_hp = int(caster.hit)
    victim_initial_hp = int(victim.hit)

    result = do_cast(caster, "'magic missile'")  # no target arg

    # ROM do_cast is silent on a successful cast (FINDING-013, src/magic.c:553-563);
    # the spell's own damage message is delivered via char.messages, not a
    # "You cast <spell>." confirmation line. The meaningful assertions below
    # (fighting victim takes damage, caster unharmed) prove the cast resolved.
    assert result == "", result
    assert victim.hit < victim_initial_hp, f"fighting victim should take damage; got victim.hit={victim.hit}"
    assert caster.hit == caster_initial_hp, f"caster must not damage self when fighting; got caster.hit={caster.hit}"


def test_do_cast_offensive_no_target_no_fight_errors():
    """ROM src/magic.c:374-378 — TAR_CHAR_OFFENSIVE with empty arg2 and
    no ``ch->fighting`` returns 'Cast the spell on whom?'."""

    caster = _make_mage(level=20, mana=200, skills={"magic missile": 100})
    # No room/fighting set — emulate idle caster

    result = do_cast(caster, "'magic missile'")

    assert result == "Cast the spell on whom?", result


def test_do_cast_defensive_obj_char_no_target_defaults_to_self():
    """CAST-002 — ROM src/magic.c:514-519 — ``TAR_OBJ_CHAR_DEF`` with an
    empty ``arg2`` defaults ``vo = ch`` (self), unlike ``TAR_OBJ_CHAR_OFF``
    (src/magic.c:466-473) which defaults to ``ch->fighting``. The three
    defensive object/char spells — ``bless`` / ``invisibility`` /
    ``remove curse`` (``TAR_OBJ_CHAR_DEF`` in src/const.c) — must self-cast on a
    no-target ``cast``. Regression: ``do_cast`` collapsed both ``TAR_OBJ_CHAR_*``
    types into the offensive default, so these three wrongly errored
    'Cast the spell on whom?' on a no-arg self-cast."""

    from mud.models.room import Room
    from mud.utils import rng_mm

    room = Room(vnum=99002, name="Chapel", description="A quiet test chapel")
    # bless is a cleric spell (mage level 53, cleric level 7 — src/const.c:967);
    # cast it as a level-24 cleric (ch_class=1) so the level/class gate passes
    # and the test exercises the TAR_OBJ_CHAR_DEF target dispatch.
    caster = _make_mage(level=24, mana=200, ch_class=1, skills={"bless": 100})
    caster.messages = []
    caster.room = room
    room.people.append(caster)

    rng_mm.seed_mm(42)
    result = do_cast(caster, "bless")  # no target arg → ROM self-default

    # do_cast is silent on a successful cast (FINDING-013, src/magic.c:553-563);
    # the bless affect landing on the caster proves the self-default resolved.
    assert result == "", result
    assert caster.has_spell_effect("bless"), "no-arg cast bless must self-cast"
    assert "You feel righteous." in caster.messages


def test_do_cast_offensive_obj_char_no_target_no_fight_still_errors():
    """CAST-002 guard + CAST-003 — ``TAR_OBJ_CHAR_OFF`` (``curse`` / ``poison``,
    src/const.c) keeps the offensive fighting-default after the vocabulary split:
    a no-arg cast with no ``ch->fighting`` errors and does NOT self-cast. ROM's
    error wording for this target type is distinct from ``TAR_CHAR_OFFENSIVE``:
    ``"Cast the spell on whom or what?"`` (src/magic.c:471) — the trailing
    "or what?" reflects that an object is also a legal operand — versus
    ``TAR_CHAR_OFFENSIVE``'s ``"Cast the spell on whom?"`` (src/magic.c:376)."""

    caster = _make_mage(level=24, mana=200, skills={"curse": 100})
    caster.messages = []
    # No room/fighting set — idle caster.

    result = do_cast(caster, "curse")

    # CAST-003: TAR_OBJ_CHAR_OFF errors "whom or what?", not "whom?".
    assert result == "Cast the spell on whom or what?", result
    assert not caster.has_spell_effect("curse"), "offensive spell must not self-cast"
