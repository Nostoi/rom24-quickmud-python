"""INV-034 — POINTER-IDENTITY-COMPARISON divergence (OPEN, demonstration).

ROM compares entities by **pointer** (`ch == victim`, `obj == X` are address
compares). The Python port's `Character` and `Object` are plain `@dataclass`
(`eq=True` by default), so `==` is **value-based** — and the live spawn path sets
`instance_id=None` (`mud/spawning/obj_spawner.py:35`) and leaves `Character.id`
at its default, so two freshly-spawned same-prototype entities compare **equal**
despite being distinct objects.

Consequence: every `obj in <list>` / `<list>.remove(obj)` / `<list>.index(obj)`
idiom (91 production sites as of 2026-06-02) uses `==`, so a value-identical
*duplicate* in a different container is found/removed in place of the intended
object — a membership lie vs ROM's pointer semantics. INV-031(c) already fixed
ONE site of this class (`group_commands.is_same_group` → `is`); this row tracks
the unfixed root cause.

Status: **OPEN.** The root-cause fix (identity-based equality on the model
dataclasses, e.g. `eq=False`, or `compare=False` on every field) has real blast
radius — it must be preceded by a sweep of tests that rely on value-equality
(`grep -rn "assert .*== .*" tests/` over Character/Object). Deferred to a scoped
session per the divergence-sweep probe mandate; see
`docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` INV-034 and
`docs/parity/DIVERGENCE_CLASS_ROSTER.md` class 6.

These tests assert the **correct ROM (identity) behavior**, so they xfail today
and will flip to xpass (strict → loud failure) the moment the root fix lands —
that is the signal to delete the markers and promote INV-034 to ✅ ENFORCED.
"""

from __future__ import annotations

import pytest


@pytest.mark.xfail(
    strict=True,
    reason="INV-034 OPEN: Object is value-eq dataclass + instance_id=None, so distinct "
    "same-proto objects compare ==. ROM compares pointers. Fix = identity equality.",
)
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


@pytest.mark.xfail(
    strict=True,
    reason="INV-034 OPEN: list.remove/in use ==, so a value-identical object in a "
    "different container is confused with the carried one.",
)
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
