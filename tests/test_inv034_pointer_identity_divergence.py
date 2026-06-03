"""INV-034 — POINTER-IDENTITY-COMPARISON divergence (✅ ENFORCED).

ROM compares entities by **pointer** (`ch == victim`, `obj == X` are address
compares). The Python port's `Character` and `Object` used to be plain
`@dataclass` (`eq=True` by default), so `==` was **value-based** — and the live
spawn path sets `instance_id=None` (`mud/spawning/obj_spawner.py:35`) and leaves
`Character.id` at its default, so two freshly-spawned same-prototype entities
compared **equal** despite being distinct objects.

Consequence (before the fix): every `obj in <list>` / `<list>.remove(obj)` /
`<list>.index(obj)` idiom (91 production sites as of 2026-06-02) used `==`, so a
value-identical *duplicate* in a different container was found/removed in place
of the intended object — a membership lie vs ROM's pointer semantics.
INV-031(c) had already fixed ONE site of this class
(`group_commands.is_same_group` → `is`); this test now locks the root cause.

Status: **ENFORCED.** `Character` and `Object` are declared
`@dataclass(eq=False)`, so `__eq__`/`__hash__` are inherited from `object`
(identity compare + identity hash) — exactly ROM pointer semantics. See
`docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` INV-034 and
`docs/parity/DIVERGENCE_CLASS_ROSTER.md` class 6.

These tests assert the **correct ROM (identity) behavior** and pass under the
identity-equality model. If they ever fail again, a model dataclass has
regressed to value equality (`eq=True`) — restore `eq=False`.
"""

from __future__ import annotations


def test_distinct_objects_are_not_equal_or_members(object_factory):
    """Two distinct objects spawned from the same prototype must NOT be `==`,
    and one must NOT be reported `in` a list containing only the other."""
    a = object_factory({"vnum": 3000, "short_descr": "a thing"})
    b = object_factory({"vnum": 3000, "short_descr": "a thing"})

    assert a is not b  # genuinely distinct instances (holds today)
    # ROM: distinct pointers compare unequal. Python value-eq makes this fail.
    assert a != b
    # The membership lie: `a in [b]` must be False for distinct objects.
    assert a not in [b]


def test_membership_does_not_confuse_value_equal_twins(object_factory):
    """A carried object must not test `in` a room-contents list that merely holds
    a value-identical twin — ROM identity would say no; value-eq wrongly says yes."""
    carried = object_factory({"vnum": 3000, "short_descr": "a thing"})
    on_floor = object_factory({"vnum": 3000, "short_descr": "a thing"})

    inventory = [carried]
    floor = [on_floor]

    assert carried in inventory  # true under both semantics
    # ROM identity: the floor twin is a different pointer, so the carried object
    # is NOT in the floor list. Value-eq makes this membership wrongly True.
    assert carried not in floor


def test_distinct_characters_are_not_equal_or_members():
    """Two freshly-built characters with identical fields (both `id=0` until the
    spawn path assigns one) must NOT be `==` and must not confuse membership —
    ROM compares PCs/mobs by pointer."""
    from mud.models.character import Character

    a = Character(name="a guard")
    b = Character(name="a guard")

    assert a is not b
    assert a != b  # identity equality under @dataclass(eq=False)
    assert a not in [b]


def test_entity_runtime_types_use_identity_equality():
    """Regression guard for the INV-034 root fix: every live entity runtime type
    (PCs `Character`, mobs `MobInstance`, objects `Object`, plus the legacy
    `ObjectInstance`) must inherit `object`'s identity `__eq__`/`__hash__`, not a
    dataclass-generated value-based one. A failure here means a model dataclass
    regressed to `eq=True` — restore `@dataclass(eq=False)`."""
    from mud.models.character import Character
    from mud.models.object import Object
    from mud.spawning.templates import MobInstance, ObjectInstance

    for cls in (Character, Object, MobInstance, ObjectInstance):
        assert cls.__eq__ is object.__eq__, f"{cls.__name__} has value-based __eq__ (regressed to eq=True)"
        assert cls.__hash__ is object.__hash__, f"{cls.__name__} is not identity-hashable"
