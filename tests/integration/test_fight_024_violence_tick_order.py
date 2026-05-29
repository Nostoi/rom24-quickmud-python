"""FIGHT-024 — violence_tick walks combatants in ROM char_list (head-first) order.

ROM `src/fight.c:76` `violence_update` iterates `char_list` from the head
(`for (ch = char_list; ...; ch = ch_next)`). Every newly created actor is
**prepended** to `char_list` — mobs in `create_mobile` (`src/db.c:2256-2257`)
and PCs at login in `nanny.c` (`src/nanny.c:757-758`). So `char_list` is in
reverse-creation order: the most-recently-loaded actor swings first.

Python's `character_registry` is append-order (creation order), so to match
ROM's swing order `violence_tick` must iterate it **reversed**. This is
load-bearing for the combat-tick RNG draw sequence — whoever swings first
consumes the shared RNG stream first (FINDING-009 facet 3). Pre-fix the forward
walk made the *earliest*-created combatant swing first, the reverse of ROM, so
the shared combat RNG stream was consumed in the wrong order.

This test pins the order: with two combatants registered A-then-B, ROM swings
B (created last) before A.
"""

from __future__ import annotations

import mud.combat.engine as engine
from mud.game_loop import violence_tick
from mud.models.character import character_registry
from mud.world import create_test_character, initialize_world


def test_violence_tick_swings_most_recently_created_first(monkeypatch):
    initialize_world()

    # Register two combatants in a known order: A first, then B.
    attacker_a = create_test_character("AlphaFighter", 3001)
    attacker_b = create_test_character("BetaFighter", 3001)

    # Both awake, same room, fighting each other so violence_tick calls
    # multi_hit on each (ROM src/fight.c:80 — IS_AWAKE && same room).
    attacker_a.fighting = attacker_b
    attacker_b.fighting = attacker_a

    # Sanity: A really is registered before B (registry is append-order).
    idx_a = character_registry.index(attacker_a)
    idx_b = character_registry.index(attacker_b)
    assert idx_a < idx_b, "test setup expects A registered before B"

    # Record the order violence_tick dispatches multi_hit. multi_hit is
    # imported function-locally inside violence_tick, so patch it on the engine
    # module. Stub it so nobody dies and fighting state persists.
    call_order: list[object] = []

    def recording_multi_hit(ch, *_a, **_k):
        call_order.append(ch)
        return []

    monkeypatch.setattr(engine, "multi_hit", recording_multi_hit)

    violence_tick(do_combat=True)

    # Filter to just our two combatants (the world may hold other actors).
    ours = [ch for ch in call_order if ch in (attacker_a, attacker_b)]

    # ROM char_list is reverse-creation order: B (created last) swings before A.
    assert ours == [attacker_b, attacker_a], (
        f"expected ROM head-first order [B, A], got {[getattr(c, 'name', c) for c in ours]}"
    )
