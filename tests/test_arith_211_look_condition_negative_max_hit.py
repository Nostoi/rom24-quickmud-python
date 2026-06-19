"""ARITH-211 regression: look condition for a non-positive max_hit.

ROM ``show_char_to_char`` (``src/act_info.c:456-459``) computes
``percent = victim->max_hit > 0 ? 100 * victim->hit / victim->max_hit : -1``
and buckets ``-1`` to the worst tier ("is bleeding to death"). The Python port
used ``else 100`` — rendering "in excellent condition" for a victim with
``max_hit <= 0``.

This was latent for ``max_hit == 0`` but ARITH-208 made it freshly reachable:
a mob can now spawn with a **negative** ``max_hit`` (``dice()+bonus < 0``), which
fails the ``> 0`` guard. The fix mirrors ROM's ``-1`` so the existing
``percent < 0`` bucket fires.
"""

from __future__ import annotations

from mud.world.look import _look_char


def test_look_negative_max_hit_shows_bleeding_not_excellent(movable_char_factory):
    char = movable_char_factory("observer", 3001)
    victim = movable_char_factory("husk", 3001)
    victim.max_hit = -50
    victim.hit = -50

    rendered = _look_char(char, victim)

    assert "bleeding to death" in rendered
    assert "excellent condition" not in rendered
