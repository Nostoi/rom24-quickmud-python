"""FIGHT-032 — defense TO_CHAR/TO_VICT PERS parity.

ROM `src/fight.c:1317-1370` check_parry / check_shield_block / check_dodge
all use act() with $n/$N that route through PERS(victim/ch, looker):

  check_parry:    act("You parry $n's attack.", ch, NULL, victim, TO_VICT);
                  act("$N parries your attack.", ch, NULL, victim, TO_CHAR);
  check_shield_block: act("You block $n's attack with your shield.", ch, NULL, victim, TO_VICT);
                  act("$N blocks your attack with a shield.", ch, NULL, victim, TO_CHAR);
  check_dodge:    act("You dodge $n's attack.", ch, NULL, victim, TO_VICT);
                  act("$N dodges your attack.", ch, NULL, victim, TO_CHAR);

PERS(ch, looker) → can_see(looker, ch) → name/short_descr or "someone".
Previously Python used getattr(x, "name", "Something") — no can_see masking,
no short_descr for NPCs.
"""

from __future__ import annotations

from unittest.mock import patch

from mud.combat.engine import check_dodge, check_parry, check_shield_block
from mud.models.character import Character, character_registry
from mud.models.constants import AffectFlag, Position
from mud.models.room import Room
from mud.registry import room_registry
from mud.world.world_state import create_test_character


def _setup_room(vnum: int = 4200):
    test_room = Room(
        vnum=vnum, name="Test Room", description="A test room.",
        room_flags=0, sector_type=0,
    )
    test_room.people = []
    test_room.contents = []
    room_registry[vnum] = test_room
    return test_room


def _cleanup(vnum: int = 4200):
    room_registry.pop(vnum, None)
    character_registry.clear()


class TestCheckParryPers:
    """FIGHT-032 — check_parry routes $n/$N through PERS."""

    @patch("mud.combat.engine.rng_mm.number_percent", return_value=1)
    @patch("mud.combat.engine.check_improve")
    def test_parry_invisible_attacker_masks_name(self, mock_improve, mock_pct):
        """TO_VICT: invisible attacker renders as 'someone'."""
        # mirrors ROM src/fight.c:1317 act("You parry $n's attack.", …, TO_VICT)
        _setup_room(4200)
        try:
            defender = create_test_character("Defender", 4200)
            defender.level = 20
            defender.position = Position.STANDING
            defender.has_weapon_equipped = True

            attacker = create_test_character("Attaq", 4200)
            attacker.level = 10
            attacker.position = Position.STANDING
            attacker.add_affect(AffectFlag.INVISIBLE)

            defender.fighting = attacker
            defender.messages = []
            attacker.messages = []

            result = check_parry(attacker, defender)
            assert result is True

            # defender sees "someone" (PERS masks invisible attacker)
            joined = "\n".join(defender.messages).lower()
            assert "you parry someone" in joined, (
                f"PERS did not mask invisible attacker: {defender.messages!r}"
            )
            assert "attaq" not in joined, (
                f"invisible attacker name leaked: {defender.messages!r}"
            )
        finally:
            _cleanup(4200)

    @patch("mud.combat.engine.rng_mm.number_percent", return_value=1)
    @patch("mud.combat.engine.check_improve")
    def test_parry_invisible_defender_masks_name(self, mock_improve, mock_pct):
        """TO_CHAR: invisible defender renders as 'someone'."""
        # mirrors ROM src/fight.c:1318 act("$N parries your attack.", …, TO_CHAR)
        _setup_room(4201)
        try:
            attacker = create_test_character("Attaq", 4201)
            attacker.level = 10
            attacker.position = Position.STANDING

            defender = create_test_character("Defender", 4201)
            defender.level = 20
            defender.position = Position.STANDING
            defender.has_weapon_equipped = True
            defender.add_affect(AffectFlag.INVISIBLE)

            defender.fighting = attacker
            defender.messages = []
            attacker.messages = []

            result = check_parry(attacker, defender)
            assert result is True

            # attacker sees "someone" (PERS masks invisible defender)
            joined = "\n".join(attacker.messages).lower()
            assert "someone parries your attack" in joined, (
                f"PERS did not mask invisible defender: {attacker.messages!r}"
            )
            assert "defender" not in joined, (
                f"invisible defender name leaked: {attacker.messages!r}"
            )
        finally:
            _cleanup(4201)

    @patch("mud.combat.engine.rng_mm.number_percent", return_value=1)
    @patch("mud.combat.engine.check_improve")
    def test_parry_npc_defender_uses_short_descr(self, mock_improve, mock_pct):
        """TO_CHAR: NPC defender renders short_descr, not name."""
        # mirrors ROM src/fight.c:1318 — PERS(victim, ch) for NPC uses short_descr
        room = _setup_room(4202)
        try:
            attacker = create_test_character("Attaq", 4202)
            attacker.level = 10
            attacker.position = Position.STANDING

            defender = Character(name="guard", level=20, room=room)
            defender.is_npc = True
            defender.short_descr = "the city guard"
            defender.long_descr = "The city guard stands here."
            defender.position = Position.STANDING
            defender.parry_skill = 100
            defender.has_weapon_equipped = True

            room.people.append(defender)
            character_registry.append(defender)
            defender.fighting = attacker
            defender.messages = []
            attacker.messages = []

            result = check_parry(attacker, defender)
            assert result is True

            # attacker sees "The city guard parries your attack."
            joined = "\n".join(attacker.messages).lower()
            assert "the city guard parries your attack" in joined, (
                f"NPC defender should render short_descr: {attacker.messages!r}"
            )
        finally:
            _cleanup(4202)


class TestCheckShieldBlockPers:
    """FIGHT-032 — check_shield_block routes $n/$N through PERS."""

    @patch("mud.combat.engine.rng_mm.number_percent", return_value=1)
    @patch("mud.combat.engine.check_improve")
    def test_shield_block_invisible_attacker_masks_name(self, mock_improve, mock_pct):
        """TO_VICT: invisible attacker renders as 'someone'."""
        # mirrors ROM src/fight.c:1345 act("You block $n's attack with your shield.", …, TO_VICT)
        _setup_room(4300)
        try:
            defender = create_test_character("Defender", 4300)
            defender.level = 20
            defender.position = Position.STANDING
            defender.has_shield_equipped = True
            defender.shield_block_skill = 100

            attacker = create_test_character("Attaq", 4300)
            attacker.level = 10
            attacker.position = Position.STANDING
            attacker.add_affect(AffectFlag.INVISIBLE)

            defender.fighting = attacker
            defender.messages = []
            attacker.messages = []

            result = check_shield_block(attacker, defender)
            assert result is True

            joined = "\n".join(defender.messages).lower()
            assert "you block someone" in joined, (
                f"PERS did not mask invisible attacker: {defender.messages!r}"
            )
            assert "attaq" not in joined, (
                f"invisible attacker name leaked: {defender.messages!r}"
            )
        finally:
            _cleanup(4300)

    @patch("mud.combat.engine.rng_mm.number_percent", return_value=1)
    @patch("mud.combat.engine.check_improve")
    def test_shield_block_invisible_defender_masks_name(self, mock_improve, mock_pct):
        """TO_CHAR: invisible defender renders as 'someone'."""
        # mirrors ROM src/fight.c:1346 act("$N blocks your attack with a shield.", …, TO_CHAR)
        _setup_room(4301)
        try:
            attacker = create_test_character("Attaq", 4301)
            attacker.level = 10
            attacker.position = Position.STANDING

            defender = create_test_character("Defender", 4301)
            defender.level = 20
            defender.position = Position.STANDING
            defender.has_shield_equipped = True
            defender.shield_block_skill = 100
            defender.add_affect(AffectFlag.INVISIBLE)

            defender.fighting = attacker
            defender.messages = []
            attacker.messages = []

            result = check_shield_block(attacker, defender)
            assert result is True

            joined = "\n".join(attacker.messages).lower()
            assert "someone blocks your attack" in joined, (
                f"PERS did not mask invisible defender: {attacker.messages!r}"
            )
            assert "defender" not in joined, (
                f"invisible defender name leaked: {attacker.messages!r}"
            )
        finally:
            _cleanup(4301)


class TestCheckDodgePers:
    """FIGHT-032 — check_dodge routes $n/$N through PERS."""

    @patch("mud.combat.engine.rng_mm.number_percent", return_value=1)
    @patch("mud.combat.engine.check_improve")
    def test_dodge_invisible_attacker_masks_name(self, mock_improve, mock_pct):
        """TO_VICT: invisible attacker renders as 'someone'."""
        # mirrors ROM src/fight.c:1362 act("You dodge $n's attack.", …, TO_VICT)
        _setup_room(4400)
        try:
            defender = create_test_character("Defender", 4400)
            defender.level = 20
            defender.position = Position.STANDING
            defender.dodge_skill = 100

            attacker = create_test_character("Attaq", 4400)
            attacker.level = 10
            attacker.position = Position.STANDING
            attacker.add_affect(AffectFlag.INVISIBLE)

            defender.fighting = attacker
            defender.messages = []
            attacker.messages = []

            result = check_dodge(attacker, defender)
            assert result is True

            joined = "\n".join(defender.messages).lower()
            assert "you dodge someone" in joined, (
                f"PERS did not mask invisible attacker: {defender.messages!r}"
            )
            assert "attaq" not in joined, (
                f"invisible attacker name leaked: {defender.messages!r}"
            )
        finally:
            _cleanup(4400)

    @patch("mud.combat.engine.rng_mm.number_percent", return_value=1)
    @patch("mud.combat.engine.check_improve")
    def test_dodge_invisible_defender_masks_name(self, mock_improve, mock_pct):
        """TO_CHAR: invisible defender renders as 'someone'."""
        # mirrors ROM src/fight.c:1370 act("$N dodges your attack.", …, TO_CHAR)
        _setup_room(4401)
        try:
            attacker = create_test_character("Attaq", 4401)
            attacker.level = 10
            attacker.position = Position.STANDING

            defender = create_test_character("Defender", 4401)
            defender.level = 20
            defender.position = Position.STANDING
            defender.dodge_skill = 100
            defender.add_affect(AffectFlag.INVISIBLE)

            defender.fighting = attacker
            defender.messages = []
            attacker.messages = []

            result = check_dodge(attacker, defender)
            assert result is True

            joined = "\n".join(attacker.messages).lower()
            assert "someone dodges your attack" in joined, (
                f"PERS did not mask invisible defender: {attacker.messages!r}"
            )
            assert "defender" not in joined, (
                f"invisible defender name leaked: {attacker.messages!r}"
            )
        finally:
            _cleanup(4401)