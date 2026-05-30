"""FIGHT-031 — combat act() output capitalized at the engine.py render
boundaries that bypass ``render_for`` (FIGHT-025's chokepoint).

ROM ``act_new`` (``src/comm.c:2376-2379``) upper-cases the first rendered
character of EVERY act() line, with a kludge for a leading ``{X`` colour code
(cap ``buf[2]`` instead of ``buf[0]``). FIGHT-025 capped only the ``dam_message``
render chokepoint (``render_for``). Two other combat act() render paths remained
uncapped:

  (a) ``_broadcast_pos_change`` — the per-listener PERS render for the
      position-change room broadcasts (``src/fight.c:837-861`` mortal / incap /
      stunned / DEAD) and the five weapon-special room broadcasts
      (``src/fight.c:614,643,654,663,673``).
  (b) direct-f-string ``_push_message`` sites: the defense TO_CHAR lines
      (``check_parry`` ``src/fight.c:1318``, ``check_shield_block`` ``:1345``,
      ``check_dodge`` ``:1370``) and the flaming victim line
      (``:655`` ``act("$p sears your flesh.", victim, wield, NULL, TO_CHAR)``).

ROM's POISON victim line (``src/fight.c:612``) is ``send_to_char``, NOT ``act()``,
so it is correctly left uncapped (it begins "You" anyway — the distinction is
the point).

The defense lines render the defender's name via the raw ``name`` field, not
ROM's ``$N``→PERS (a separate divergence tracked under FIGHT_C_AUDIT follow-ups /
INV-027 family). These tests therefore assert the *capitalization property*
(first visible char upper-cased) plus the line content — never the full
rendered name — so they survive the later PERS fix.
"""

from __future__ import annotations

from mud.combat import engine
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room


def _room_with_victim_and_listener(victim_name: str) -> tuple[Character, Character, Room]:
    room = Room(vnum=99931, name="FIGHT-031 probe room")
    victim = Character(name=victim_name, is_npc=False)
    victim.level = 10
    victim.position = Position.STANDING
    victim.hit = 20
    victim.max_hit = 20
    listener = Character(name="listener-pc", is_npc=False)
    listener.level = 30
    listener.position = Position.STANDING
    for ch in (victim, listener):
        room.add_character(ch)
    listener.messages = []
    return victim, listener, room


def _defender_and_attacker() -> tuple[Character, Character, Room]:
    """Defender with a lowercase name + maxed defenses; low-level attacker.

    The level gap makes every defense ``chance`` exceed 100, so the defense
    fires on every ``number_percent()`` draw regardless of the seed.
    """
    room = Room(vnum=99932, name="FIGHT-031 defense room")
    # Lowercase-led name so the cap is observable (existing tests use "Victim",
    # which is already capital, so they never exercised the cap).
    defender = Character(name="scruffy guard", is_npc=False)
    defender.level = 100
    defender.position = Position.STANDING
    defender.has_weapon_equipped = True
    defender.has_shield_equipped = True
    defender.parry_skill = 100
    defender.dodge_skill = 100
    defender.shield_block_skill = 100

    attacker = Character(name="Tester", is_npc=False)
    attacker.level = 1
    attacker.position = Position.STANDING
    attacker.messages = []

    for ch in (defender, attacker):
        room.add_character(ch)
    return defender, attacker, room


# --- (a) _broadcast_pos_change chokepoint --------------------------------


def test_broadcast_pos_change_caps_room_line() -> None:
    # mirrors ROM src/fight.c:837 act("$n is mortally wounded...", TO_ROOM) →
    # src/comm.c:2376 caps buf[0]. PERS renders a lowercase name token, ROM caps
    # it; without the fix the listener hears a lowercase-led line.
    victim, listener, _room = _room_with_victim_and_listener("the orc")
    engine._broadcast_pos_change(victim, "{name} is mortally wounded.")
    assert listener.messages, "listener heard nothing"
    msg = listener.messages[-1]
    assert msg[0].isupper(), f"first char not capitalized: {msg!r}"
    assert "is mortally wounded." in msg, msg
    # The pre-cap PERS token is lowercase ("the orc"/"someone"); proving the cap
    # ran means no lowercase-led opener survives.
    assert not msg[0].islower(), msg


def test_broadcast_pos_change_caps_dead_line_after_color_kludge() -> None:
    # mirrors ROM src/fight.c:860 act("{R$n is DEAD!!{x", TO_ROOM) → the
    # src/comm.c:2376 `{`-kludge caps buf[2] (first char after the 2-char {R
    # colour code), leaving the colour code itself intact.
    victim, listener, _room = _room_with_victim_and_listener("the orc")
    engine._broadcast_pos_change(victim, "{{R{name} is DEAD!!{{x")
    msg = listener.messages[-1]
    assert msg.startswith("{R"), f"colour code mangled: {msg!r}"
    assert msg[2].isupper(), f"char after colour code not capitalized: {msg!r}"
    assert "is DEAD!!{x" in msg, msg


# --- (b) direct-f-string defense TO_CHAR lines ---------------------------


def test_shield_block_to_char_line_capitalized() -> None:
    # mirrors ROM src/fight.c:1345 act("$N blocks your attack with a shield.",
    # ch, NULL, victim, TO_CHAR) — the defender's name leads the attacker's line.
    defender, attacker, _room = _defender_and_attacker()
    assert engine.check_shield_block(attacker, defender) is True
    assert attacker.messages, "attacker received no shield-block line"
    msg = attacker.messages[-1]
    assert "blocks your attack" in msg, msg
    assert msg[0].isupper(), f"defender name not capitalized: {msg!r}"


def test_parry_to_char_line_capitalized() -> None:
    # mirrors ROM src/fight.c:1318 act("$N parries your attack.", ch, NULL,
    # victim, TO_CHAR).
    defender, attacker, _room = _defender_and_attacker()
    assert engine.check_parry(attacker, defender) is True
    msg = attacker.messages[-1]
    assert "parries your attack" in msg, msg
    assert msg[0].isupper(), f"defender name not capitalized: {msg!r}"


def test_dodge_to_char_line_capitalized() -> None:
    # mirrors ROM src/fight.c:1370 act("$N dodges your attack.", ch, NULL,
    # victim, TO_CHAR).
    defender, attacker, _room = _defender_and_attacker()
    assert engine.check_dodge(attacker, defender) is True
    msg = attacker.messages[-1]
    assert "dodges your attack" in msg, msg
    assert msg[0].isupper(), f"defender name not capitalized: {msg!r}"
