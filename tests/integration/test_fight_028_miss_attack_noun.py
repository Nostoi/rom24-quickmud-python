"""FIGHT-028 — combat miss line must keep the attack noun (FINDING-011).

ROM `src/fight.c:dam_message` (2157-2213) chooses its template purely on
`dt == TYPE_HIT` vs not; `dam == 0` only swaps the verb to "misses". So an
NPC with a resolved attack type (e.g. the drunk #3064, `dt = TYPE_HIT + 13`
"beating") that *misses* renders `"The drunk's beating misses you."` — the
same noun template its *hit* path uses. Python previously routed every
`percent <= 0` event through the noun-less `TYPE_HIT` template, dropping the
noun on the miss path (and on low-damage hits that round to percent 0).
"""

from __future__ import annotations

from mud.combat.messages import TYPE_HIT, dam_message, render_for
from mud.models.character import Character
from mud.models.room import Room

_DUMMY_ROOM = Room(vnum=99999, name="X", description="", room_flags=0, sector_type=0)

# attack_table[13].noun == "beating" — the drunk #3064's dam_type.
_DT_BEATING = TYPE_HIT + 13


def _make_character(name: str) -> Character:
    char = Character(name=name, max_hit=100, hit=100, is_npc=False)
    char.room = _DUMMY_ROOM
    return char


def test_miss_keeps_attack_noun():
    # mirrors ROM src/fight.c:2200-2211 — dam == 0, dt != TYPE_HIT renders
    # "{4$n's %s misses you" (noun + "misses"), not the noun-less TYPE_HIT line.
    attacker = _make_character("Drunk")
    victim = _make_character("Victim")

    messages = dam_message(attacker, victim, 0, _DT_BEATING, immune=False)

    assert render_for(messages.victim, attacker, victim, victim) == "{4Drunk's beating misses you.{x"
    assert render_for(messages.attacker, attacker, victim, attacker) == "{2Your beating misses Victim.{x"
    assert render_for(messages.room, attacker, victim, attacker) == "{3Drunk's beating misses Victim.{x"


def test_low_damage_hit_keeps_attack_noun():
    # mirrors ROM src/fight.c:2200-2211 — a real hit that rounds to percent 0
    # (dam=1, max_hit=100 -> 1*100/100... here dam=1/200 via low ratio) still
    # uses the noun template with the "scratches" verb, not the noun-less line.
    attacker = _make_character("Drunk")
    victim = _make_character("Victim")
    victim.max_hit = 200  # 1*100/200 -> percent 0 (c_div), tier "scratch"

    messages = dam_message(attacker, victim, 1, _DT_BEATING, immune=False)

    assert render_for(messages.victim, attacker, victim, victim) == "{4Drunk's beating scratches you.{x"


def test_type_hit_miss_stays_noun_less():
    # mirrors ROM src/fight.c:2157-2169 — bare TYPE_HIT miss has no noun.
    attacker = _make_character("Drunk")
    victim = _make_character("Victim")

    messages = dam_message(attacker, victim, 0, TYPE_HIT, immune=False)

    assert render_for(messages.victim, attacker, victim, victim) == "{4Drunk misses you.{x"
    assert render_for(messages.attacker, attacker, victim, attacker) == "{2You miss Victim.{x"
