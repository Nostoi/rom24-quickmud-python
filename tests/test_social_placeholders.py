from __future__ import annotations

from mud.models.character import Character
from mud.models.constants import Sex
from mud.models.social import expand_placeholders


def test_expand_placeholders_pronouns_actor_victim():
    actor = Character(name="Al", sex=Sex.MALE)
    victim = Character(name="Bea", sex=Sex.FEMALE)
    msg = "$n pokes $N; $e laughs at $M and steals $S hat."
    out = expand_placeholders(msg, actor, victim)
    assert out == "Al pokes Bea; he laughs at her and steals her hat."


def test_expand_placeholders_neuter_and_reflexive():
    actor = Character(name="Blob", sex=Sex.NONE)
    msg = "$n looks at $mself and nods $s head; $e is ready."
    out = expand_placeholders(msg, actor)
    assert out == "Blob looks at itself and nods its head; it is ready."
