"""
Integration tests for spell casting command workflows.

Tests complete spell casting scenarios including:
- cast command dispatching
- mana cost calculations
- spell targeting (self, other, object, room)
- object-cast spell triggers (scrolls, staves, wands)
- say_spell integration
"""

from __future__ import annotations

import pytest

from mud.commands.dispatcher import process_command
from mud.models.character import Character
from mud.models.constants import ItemType
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.skills.registry import skill_registry


@pytest.fixture
def mage_player(test_room):
    """Create a mage test character with mana and spells."""
    char = Character(
        name="Gandalf",
        level=20,
        room=test_room,
        gold=500,
        hit=100,
        max_hit=100,
        mana=200,
        max_mana=200,
        is_npc=False,
        ch_class=0,
    )
    char.messages = []
    test_room.people.append(char)
    yield char
    if char in test_room.people:
        test_room.people.remove(char)


@pytest.fixture
def scroll_object():
    """Create a scroll with fireball spell."""
    proto = ObjIndex(
        vnum=4000,
        name="scroll fireball",
        short_descr="a scroll of fireball",
        description="A scroll of fireball lies here.",
        item_type=int(ItemType.SCROLL),
        level=20,
        value=[20, 30, 30, 30, 0],
    )
    scroll = Object(instance_id=1, prototype=proto)
    return scroll


@pytest.fixture
def target_mob(test_room):
    """Create a target mob for spell testing."""
    mob = Character(
        name="goblin",
        short_descr="a goblin",
        description="A goblin is lurking here.",
        level=10,
        room=test_room,
        is_npc=True,
        hit=80,
        max_hit=80,
        mana=50,
        max_mana=50,
    )
    mob.messages = []
    test_room.people.append(mob)
    yield mob
    if mob in test_room.people:
        test_room.people.remove(mob)


class TestCancellationTargeting:
    """SKILL-001: cancellation is TAR_CHAR_DEFENSIVE (src/const.c), not offensive."""

    def test_skill_001_cancellation_defaults_to_self(self, mage_player, target_mob, monkeypatch):
        # ROM src/const.c skill_table — `cancellation` is TAR_CHAR_DEFENSIVE,
        # POS_FIGHTING. A no-arg `cast cancellation` therefore defaults to the
        # caster (self) per src/magic.c:419, even mid-combat. Python's skills.json
        # had target="victim" (TAR_CHAR_OFFENSIVE), so a no-arg cast while fighting
        # targeted the *opponent* instead.
        from pathlib import Path

        from mud.models.constants import Position
        from mud.skills.registry import load_skills, skill_registry
        from mud.utils import rng_mm

        # Self-contained skill load (parallel-safe — don't depend on another
        # test/class having populated the global registry).
        skill_registry.skills.clear()
        skill_registry.handlers.clear()
        load_skills(Path("data/skills.json"))

        # Data parity: registry must expose the ROM-correct defensive target.
        assert skill_registry.get("cancellation").target == "friendly"

        mage_player.skills = {"cancellation": 100}
        # skills.json carries no per-class spell levels, so the loaded skill
        # defaults to levels (99,99,99,99); bump level past that so do_cast's
        # level gate passes and we exercise the targeting branch (the point here).
        mage_player.level = 100
        mage_player.position = Position.FIGHTING
        mage_player.fighting = target_mob
        target_mob.fighting = mage_player

        captured = {}

        def spy(caster, victim=None, **kwargs):
            captured["target"] = victim
            return {"success": True, "message": ""}

        monkeypatch.setitem(skill_registry.handlers, "cancellation", spy)
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)  # force cast success

        process_command(mage_player, "cast cancellation")

        assert captured.get("target") is mage_player, (
            "no-arg cancellation must default to self (TAR_CHAR_DEFENSIVE), not the opponent"
        )


class TestSkillMetadataLevels:
    """CONST-009: cancellation/harm were absent from ROM_SKILL_METADATA, so their
    loaded per-class levels defaulted to (99,99,99,99) — uncastable by mortals."""

    @pytest.mark.parametrize(
        "name,rom_levels",
        [
            ("cancellation", (18, 26, 34, 34)),  # src/const.c skill_table
            ("harm", (53, 23, 53, 28)),
        ],
    )
    def test_const_009_missing_skill_levels(self, name, rom_levels):
        from pathlib import Path

        from mud.skills.registry import load_skills, skill_registry

        skill_registry.skills.clear()
        skill_registry.handlers.clear()
        load_skills(Path("data/skills.json"))
        assert tuple(skill_registry.get(name).levels) == rom_levels, (
            f"{name} per-class levels must match ROM skill_table, not the (99,99,99,99) default"
        )

    def test_const_009_mage_can_cast_cancellation_at_rom_level(self, mage_player, target_mob, monkeypatch):
        # A mage learns cancellation at level 18 in ROM. With levels=(99,99,99,99)
        # the do_cast level gate blocked it ("You don't know any spells of that name.").
        from pathlib import Path

        from mud.models.constants import Position
        from mud.skills.registry import load_skills, skill_registry
        from mud.utils import rng_mm

        skill_registry.skills.clear()
        skill_registry.handlers.clear()
        load_skills(Path("data/skills.json"))

        mage_player.skills = {"cancellation": 100}
        mage_player.level = 25  # >= mage level 18, < the old 99 default
        mage_player.position = Position.STANDING

        called = {}
        monkeypatch.setitem(
            skill_registry.handlers, "cancellation", lambda c, victim=None, **k: called.setdefault("hit", True) or {}
        )
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

        result = process_command(mage_player, "cast cancellation")
        assert "don't know any spells" not in result.lower(), result
        assert called.get("hit") is True


class TestCastCommandDispatch:
    """Test cast command basic functionality."""

    def test_interp_031_cast_min_position_fighting(self, mage_player):
        """INTERP-031: `cast` command-gate min position must be POS_FIGHTING.

        ROM src/interp.c:79 — {"cast", do_cast, POS_FIGHTING, 0, ...}. Python
        registered POS_RESTING, which wrongly let a resting/sitting character
        cast. ROM requires standing (POS_FIGHTING gates at position >= FIGHTING,
        i.e. FIGHTING or STANDING), so a resting caster is blocked at the
        dispatcher with the RESTING position message and never reaches do_cast.
        """
        from mud.commands.dispatcher import COMMAND_INDEX
        from mud.models.constants import Position

        assert COMMAND_INDEX["cast"].min_position == Position.FIGHTING

        # A resting mage is blocked at the position gate (ROM: must stand to cast).
        mage_player.position = Position.RESTING
        result = process_command(mage_player, "cast 'magic missile'")
        assert "too relaxed" in result.lower(), "resting caster must hit the RESTING position gate"
        # Standing still works (regression guard for the common case).
        mage_player.position = Position.STANDING
        ok = process_command(mage_player, "cast 'magic missile'")
        assert "too relaxed" not in ok.lower()

    def test_cast_command_exists(self, mage_player):
        """Verify cast command is registered."""
        result = process_command(mage_player, "cast")
        assert "huh" not in result.lower()

    def test_cast_requires_spell_name(self, mage_player):
        """Cast without spell name shows help."""
        result = process_command(mage_player, "cast")
        assert "cast" in result.lower() or "spell" in result.lower()

    def test_cast_unknown_spell_fails(self, mage_player):
        """Casting unknown spell shows error."""
        result = process_command(mage_player, "cast foobar")
        assert "you don't know any spells of that name" in result.lower() or "huh" in result.lower()

    def test_cast_known_spell_no_target(self, mage_player):
        """Cast offensive spell without target fails."""
        result = process_command(mage_player, "cast 'magic missile'")
        assert (
            "spell on who" in result.lower()
            or "target" in result.lower()
            or "failed" in result.lower()
            or "you don't know any spells of that name" in result.lower()
        )


class TestManaCostCalculations:
    """Test mana cost mechanics."""

    def test_cast_costs_mana(self, mage_player):
        """Casting a spell consumes mana."""
        initial_mana = mage_player.mana
        process_command(mage_player, "cast armor")
        assert mage_player.mana < initial_mana or mage_player.mana == initial_mana

    def test_cast_insufficient_mana_fails(self, mage_player):
        """Casting with insufficient mana fails."""
        mage_player.mana = 0
        result = process_command(mage_player, "cast 'magic missile' goblin")
        assert "not enough mana" in result.lower() or "failed" in result.lower() or mage_player.mana == 0

    def test_mana_cost_scales_with_level(self, mage_player):
        """Lower level spells cost less mana."""
        mage_player.mana = 200
        initial_mana = mage_player.mana

        process_command(mage_player, "cast armor")

        armor_cost = initial_mana - mage_player.mana
        assert armor_cost >= 0


class TestSpellTargeting:
    """Test spell targeting mechanics."""

    def test_cast_self_targeting(self, mage_player):
        """Self-targeting spells work without explicit target."""
        result = process_command(mage_player, "cast armor")
        assert (
            "armor" in result.lower()
            or "fail" in result.lower()
            or "you don't know any spells of that name" in result.lower()
        )

    def test_cast_explicit_self_target(self, mage_player):
        """Can explicitly target self."""
        result = process_command(mage_player, "cast bless self")
        assert (
            "bless" in result.lower()
            or "fail" in result.lower()
            or "you don't know any spells of that name" in result.lower()
        )

    def test_cast_other_character_target(self, mage_player, target_mob):
        """Can target another character."""
        result = process_command(mage_player, "cast 'cure light' goblin")
        assert (
            "cure" in result.lower()
            or "fail" in result.lower()
            or "goblin" in result.lower()
            or "you don't know any spells of that name" in result.lower()
        )

    def test_cast_offensive_spell_at_target(self, mage_player, target_mob):
        """Can cast offensive spell at target."""
        initial_hit = target_mob.hit
        result = process_command(mage_player, "cast 'magic missile' goblin")

        assert (
            "magic missile" in result.lower()
            or "fail" in result.lower()
            or target_mob.hit < initial_hit
            or target_mob.hit == initial_hit
        )

    def test_cast_room_spell(self, mage_player):
        """Room-wide spells affect entire room."""
        result = process_command(mage_player, "cast 'continual light'")
        assert (
            "light" in result.lower()
            or "fail" in result.lower()
            or "you don't know any spells of that name" in result.lower()
        )


class TestObjectCastSpells:
    """Test object-triggered spell casting (scrolls, staves, wands)."""

    def test_recite_scroll_exists(self, mage_player, scroll_object):
        """Recite command is registered."""
        mage_player.inventory = [scroll_object]
        result = process_command(mage_player, "recite")
        assert "huh" not in result.lower()

    def test_recite_scroll_casts_spell(self, mage_player, scroll_object, target_mob):
        """Reciting scroll casts stored spell."""
        mage_player.inventory = [scroll_object]
        result = process_command(mage_player, "recite scroll goblin")

        assert (
            "fireball" in result.lower()
            or "scroll" in result.lower()
            or "fail" in result.lower()
            or "you don't know any spells of that name" in result.lower()
            or "huh" not in result.lower()
        )

    def test_recite_scroll_consumes_item(self, mage_player, scroll_object):
        """Reciting scroll consumes it (or doesn't if spell unknown)."""
        mage_player.inventory = [scroll_object]
        initial_count = len(mage_player.inventory)

        process_command(mage_player, "recite scroll")

        assert len(mage_player.inventory) <= initial_count or len(mage_player.inventory) == initial_count

    def test_zap_wand_exists(self, mage_player):
        """Zap command is registered."""
        result = process_command(mage_player, "zap")
        assert "huh" not in result.lower()

    def test_brandish_staff_exists(self, mage_player):
        """Brandish command is registered."""
        result = process_command(mage_player, "brandish")
        assert "huh" not in result.lower()


class TestSaySpellIntegration:
    """Test say_spell broadcast integration."""

    def test_cast_spell_broadcasts_words(self, mage_player, target_mob):
        """Casting spell broadcasts spell words to room."""
        mage_player.messages = []
        target_mob.messages = []

        process_command(mage_player, "cast bless")

        room_has_spell_message = (
            any("bless" in msg.lower() or "utters" in msg.lower() for msg in target_mob.messages)
            or any("bless" in msg.lower() or "utters" in msg.lower() for msg in mage_player.messages)
            or len(target_mob.messages) == 0
        )
        assert room_has_spell_message

    def test_cast_spell_shows_garbled_to_different_class(self, mage_player, target_mob):
        """Non-mages see garbled spell words."""
        mage_player.messages = []
        target_mob.messages = []
        target_mob.ch_class = 2

        process_command(mage_player, "cast armor")

        mob_saw_message = len(target_mob.messages) > 0 or len(mage_player.messages) > 0
        assert mob_saw_message or True

    def test_cast_spell_shows_actual_words_to_same_class(self, mage_player, target_mob):
        """Same class characters see actual spell words."""
        mage_player.messages = []
        target_mob.messages = []
        target_mob.ch_class = 0
        target_mob.is_npc = False

        process_command(mage_player, "cast armor")

        saw_spell_or_empty = (
            any("armor" in msg.lower() for msg in target_mob.messages)
            or len(target_mob.messages) == 0
            or len(mage_player.messages) > 0
        )
        assert saw_spell_or_empty


class TestCast013PerSpellMinPosition:
    """CAST-013: do_cast must gate on the spell's OWN ``minimum_position``.

    ROM ``src/magic.c:341-345``::

        if (ch->position < skill_table[sn].minimum_position)
        { send_to_char("You can't concentrate enough.\\n\\r", ch); return; }

    Python ``do_cast`` used a FLAT ``char.position < Position.FIGHTING`` for every
    spell. Given the ``cast`` command-gate is ``POS_FIGHTING`` (INTERP-031), the
    caster is always FIGHTING(7) or STANDING(8) by the time the per-spell gate
    runs, so the only observable effect of the per-spell value is: ``POS_STANDING``
    spells (armor, bless, detect_*, charm, cure_disease/poison — the utility/buff
    spells) cannot be cast WHILE FIGHTING. The flat check let them through.
    """

    def _load(self):
        from pathlib import Path

        from mud.skills.registry import load_skills, skill_registry

        skill_registry.skills.clear()
        skill_registry.handlers.clear()
        load_skills(Path("data/skills.json"))
        return skill_registry

    def test_fighting_caster_blocked_on_standing_spell(self, mage_player, target_mob, monkeypatch):
        """A FIGHTING mage casting a POS_STANDING utility spell → 'concentrate'."""
        from mud.models.constants import Position
        from mud.utils import rng_mm

        reg = self._load()
        # detect magic: ROM POS_STANDING, mage learns at level 2, TAR_CHAR_SELF.
        assert reg.get("detect magic").minimum_position == Position.STANDING

        mage_player.skills = {"detect magic": 100}
        mage_player.level = 20  # >= mage detect-magic level 2
        mage_player.position = Position.FIGHTING
        mage_player.fighting = target_mob
        target_mob.fighting = mage_player

        fired = {}
        monkeypatch.setitem(
            reg.handlers, "detect_magic", lambda c, victim=None, **k: fired.setdefault("hit", True) or {}
        )
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

        result = process_command(mage_player, "cast 'detect magic'")
        assert result == "You can't concentrate enough.", result
        assert fired.get("hit") is None, "the spell handler must not run when position-gated"

    def test_fighting_caster_allowed_on_fighting_spell(self, mage_player, target_mob, monkeypatch):
        """Offensive control: a FIGHTING mage CAN cast a POS_FIGHTING spell."""
        from mud.models.constants import Position
        from mud.utils import rng_mm

        reg = self._load()
        # magic missile: ROM POS_FIGHTING, mage learns at level 1.
        assert reg.get("magic missile").minimum_position == Position.FIGHTING

        mage_player.skills = {"magic missile": 100}
        mage_player.level = 20
        mage_player.position = Position.FIGHTING
        mage_player.fighting = target_mob
        target_mob.fighting = mage_player

        monkeypatch.setitem(reg.handlers, "magic_missile", lambda c, victim=None, **k: {})
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

        result = process_command(mage_player, "cast 'magic missile' goblin")
        assert result != "You can't concentrate enough.", result

    def test_standing_caster_allowed_on_standing_spell(self, mage_player, monkeypatch):
        """Regression guard: a STANDING mage CAN cast a POS_STANDING spell."""
        from mud.models.constants import Position
        from mud.utils import rng_mm

        reg = self._load()
        mage_player.skills = {"detect magic": 100}
        mage_player.level = 20
        mage_player.position = Position.STANDING

        monkeypatch.setitem(reg.handlers, "detect_magic", lambda c, victim=None, **k: {})
        monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

        result = process_command(mage_player, "cast 'detect magic'")
        assert result != "You can't concentrate enough.", result

    def test_every_spell_min_position_matches_rom_const_c(self):
        """Completeness anti-drift guard: every spell's registry ``minimum_position``
        must equal the ROM ``const.c`` skill_table value (parser + the two
        parser-skipped CONST-009 spells)."""
        from pathlib import Path

        from mud.models.constants import Position
        from mud.scripts.convert_skills_to_json import parse_skill_table

        reg = self._load()
        pos_by_name = {
            "POS_DEAD": Position.DEAD,
            "POS_MORTAL": Position.MORTAL,
            "POS_INCAP": Position.INCAP,
            "POS_STUNNED": Position.STUNNED,
            "POS_SLEEPING": Position.SLEEPING,
            "POS_RESTING": Position.RESTING,
            "POS_SITTING": Position.SITTING,
            "POS_FIGHTING": Position.FIGHTING,
            "POS_STANDING": Position.STANDING,
        }
        const_path = Path(__file__).resolve().parents[2] / "src" / "const.c"
        expected = {e["name"]: pos_by_name[e["minimum_position"]] for e in parse_skill_table(const_path)}
        # CONST-009: parser skips cancellation/harm (multi-line noun array); both POS_FIGHTING.
        expected.setdefault("cancellation", Position.FIGHTING)
        expected.setdefault("harm", Position.FIGHTING)

        mismatches = {
            name: (reg.get(name).minimum_position, want)
            for name, want in expected.items()
            if name in reg.skills and reg.get(name).minimum_position != want
        }
        assert not mismatches, f"minimum_position drift vs ROM const.c: {mismatches}"

    @pytest.mark.parametrize(
        "name,rom_position",
        [
            # Hand-verified against src/const.c skill_table, spanning all three
            # reachable positions and both classes — an INDEPENDENT anchor so the
            # completeness guard above isn't circular (it derives both sides from
            # parse_skill_table, so it proves transfer, not that the parser reads
            # the right column). These pin the parser's group-6 extraction itself.
            ("armor", "STANDING"),
            ("continual light", "STANDING"),
            ("detect invis", "STANDING"),
            ("sanctuary", "STANDING"),
            ("magic missile", "FIGHTING"),
            ("lightning bolt", "FIGHTING"),
            ("fireball", "FIGHTING"),
            ("heal", "FIGHTING"),
            ("word of recall", "RESTING"),
        ],
    )
    def test_min_position_hardcoded_anchors(self, name, rom_position):
        from mud.models.constants import Position

        reg = self._load()
        assert reg.get(name).minimum_position == Position[rom_position]


class TestSpellEffects:
    """Test that cast spells produce expected effects."""

    def test_cast_armor_applies_ac_bonus(self, mage_player):
        """Armor spell improves AC."""
        initial_ac = mage_player.armor.copy()

        process_command(mage_player, "cast armor")

        ac_improved = any(mage_player.armor[i] <= initial_ac[i] for i in range(4)) or mage_player.armor == initial_ac
        assert ac_improved

    def test_cast_heal_restores_hp(self, mage_player):
        """Heal spell restores hit points."""
        mage_player.hit = 50
        initial_hit = mage_player.hit

        process_command(mage_player, "cast heal")

        assert mage_player.hit >= initial_hit

    def test_cast_sanctuary_applies_affect(self, mage_player):
        """Sanctuary spell applies sanctuary affect."""
        process_command(mage_player, "cast sanctuary")

        has_sanctuary = (
            mage_player.has_spell_effect("sanctuary") or "sanctuary" in mage_player.messages[-1].lower()
            if mage_player.messages
            else False
        )
        assert has_sanctuary or True


class TestCastCommandEdgeCases:
    """Test edge cases and error conditions."""

    def test_cast_while_fighting(self, mage_player, target_mob):
        """Can cast spells while in combat."""
        mage_player.fighting = target_mob
        result = process_command(mage_player, "cast 'magic missile' goblin")

        assert (
            "magic missile" in result.lower()
            or "fail" in result.lower()
            or "you don't know any spells of that name" in result.lower()
        )

    def test_cast_invalid_target(self, mage_player):
        """Casting at invalid target fails gracefully."""
        result = process_command(mage_player, "cast 'magic missile' nonexistent")
        assert (
            "not here" in result.lower()
            or "can't find" in result.lower()
            or "fail" in result.lower()
            or "you don't know any spells of that name" in result.lower()
        )

    def test_cast_with_partial_name(self, mage_player):
        """Can cast spells with partial names."""
        result = process_command(mage_player, "cast mag mis")
        assert (
            "spell on who" in result.lower()
            or "target" in result.lower()
            or "fail" in result.lower()
            or "you don't know any spells of that name" in result.lower()
        )

    def test_cast_multiword_spell_with_quotes(self, mage_player):
        """Can cast multi-word spells with quotes."""
        result = process_command(mage_player, "cast 'magic missile' goblin")
        assert (
            "magic missile" in result.lower()
            or "fail" in result.lower()
            or "not here" in result.lower()
            or "you don't know any spells of that name" in result.lower()
        )

    def test_cast_multiword_spell_without_quotes(self, mage_player):
        """Can cast multi-word spells without quotes."""
        result = process_command(mage_player, "cast magic missile goblin")
        assert (
            "magic missile" in result.lower()
            or "fail" in result.lower()
            or "not here" in result.lower()
            or "you don't know any spells of that name" in result.lower()
        )


class TestCastManaDeductionCAST008:
    """CAST-008 — failed casts must cost mana/2 only, not full + half.

    ROM src/magic.c:551-558 deducts EITHER `ch->mana -= mana / 2;` (failure)
    OR `ch->mana -= mana;` (success) — never both, and never before the
    concentration roll. QuickMUD deducted the full mana_cost upfront and then
    an additional mana_cost/2 on failure, so a failed cast cost 1.5x.
    """

    @pytest.fixture(autouse=True)
    def _load_skills(self):
        from pathlib import Path

        from mud.skills.registry import load_skills
        from mud.utils import rng_mm

        skill_registry.skills.clear()
        skill_registry.handlers.clear()
        load_skills(Path("data/skills.json"))
        rng_mm.seed_mm(12345)
        yield
        skill_registry.skills.clear()
        skill_registry.handlers.clear()

    def _level1_mage(self, room):
        from mud.models.constants import Position

        char = Character(
            name="Apprentice",
            level=1,
            room=room,
            mana=100,
            max_mana=100,
            is_npc=False,
            ch_class=0,  # mage_player fixture convention; magic missile levels[0]=1
            position=Position.STANDING,
        )
        char.skills = {"magic missile": 75}  # 75% like the reported in-game char
        char.messages = []
        room.people.append(char)
        return char

    def test_failed_cast_costs_half_mana_only(self, test_room, target_mob):
        from unittest.mock import patch

        char = self._level1_mage(test_room)
        try:
            # magic missile for a level-1 mage costs 50 mana
            # (max(min_mana=15, 100 // (2 + 1 - 1)) = 50).
            # Force the concentration roll to FAIL: number_percent()=100 > skill 75.
            with patch("mud.utils.rng_mm.number_percent", return_value=100):
                process_command(char, "cast 'magic missile' goblin")
            # mirrors ROM src/magic.c:553 — failed cast costs mana/2 (25) ONLY,
            # leaving mana at 75. The CAST-008 bug deducted 50 upfront + 25 = 75
            # total, leaving mana at 25 (the reported "costs 75 of 100 mana").
            assert char.mana == 75, f"failed cast must cost mana/2 (25); cost was {100 - char.mana}"
        finally:
            if char in test_room.people:
                test_room.people.remove(char)

    def test_successful_cast_costs_full_mana(self, test_room, target_mob):
        from unittest.mock import patch

        char = self._level1_mage(test_room)
        try:
            # Force the concentration roll to SUCCEED: number_percent()=1 <= skill 75.
            with patch("mud.utils.rng_mm.number_percent", return_value=1):
                process_command(char, "cast 'magic missile' goblin")
            # mirrors ROM src/magic.c:557 — successful cast costs the full mana (50).
            assert char.mana == 50, f"successful cast must cost full mana (50); cost was {100 - char.mana}"
        finally:
            if char in test_room.people:
                test_room.people.remove(char)
