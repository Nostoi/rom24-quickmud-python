"""affect_check must consult equipped objects' prototype affects.

ROM contract (``src/handler.c:1182-1265 affect_check``)::

    for (paf = ch->affected; ...) { ... }
    for (obj = ch->carrying; ...) {
        if (obj->wear_loc == -1) continue;
        for (paf = obj->affected; ...) { ... }    /* per-instance */
        if (obj->enchanted) continue;
        for (paf = obj->pIndexData->affected; ...) { ... }   /* prototype */
    }

ROM walks three layers when deciding whether to re-set a cleared
bitvector: the wearer's other affects, each equipped object's
per-instance affects, and (for unenchanted items) each equipped
object's PROTOTYPE affects. The prototype walk is load-bearing —
the normal ROM pattern is for `.are` files to put the affect on the
prototype (`A` entries in area files), not on every spawned instance.

Python `mud/handler.py:affect_check` only walks the per-instance list,
missing the prototype fallback entirely. Symptom: a player wearing a
`+sanc` ring (granted via prototype affect) and a temporary `sanctuary`
spell will lose the AFF_SANCTUARY bit when the spell expires — the
ring's prototype-level grant is dropped on the floor.

`equip_char` / `unequip_char` already walk prototype affects correctly
(`mud/handler.py:179, 240`), so the bit is granted at equip time. The
asymmetry only surfaces during `affect_check` triggered by
`affect_remove`.
"""

from __future__ import annotations

from mud.handler import affect_check
from mud.models.character import Character
from mud.models.constants import AffectFlag, WearLocation
from mud.models.obj import Affect, ObjIndex
from mud.models.object import Object


def test_affect_check_walks_equipped_obj_prototype_affects() -> None:
    """ROM src/handler.c:1240-1257 falls back to obj->pIndexData->affected
    when the per-instance list does not match. Python must do the same.
    """
    proto = ObjIndex(vnum=99940, short_descr="a sanctuary ring")
    proto.affected = [
        Affect(where=0, type=0, level=20, duration=-1, location=0, modifier=0, bitvector=int(AffectFlag.SANCTUARY))
    ]

    ring = Object(instance_id=None, prototype=proto)
    ring.wear_loc = int(WearLocation.FINGER_L)
    ring.affected = []
    ring.enchanted = False

    char = Character(name="Cleric")
    char.affected = []
    char.affected_by = 0
    char.equipment = {WearLocation.FINGER_L: ring}

    affect_check(char, where=0, vector=int(AffectFlag.SANCTUARY))

    assert int(char.affected_by) & int(AffectFlag.SANCTUARY), (
        "ROM src/handler.c:1240-1257 walks obj->pIndexData->affected on "
        "every equipped item; an unenchanted ring whose prototype grants "
        "AFF_SANCTUARY must keep the wearer flagged after affect_check "
        f"runs. Got affected_by={int(char.affected_by):#x}"
    )


def test_affect_check_skips_prototype_when_enchanted() -> None:
    """ROM src/handler.c:1237-1238 — ``if (obj->enchanted) continue;``
    skips the prototype walk when the instance is enchanted. The
    enchanted instance's per-instance ``affected`` is the source of truth.
    """
    proto = ObjIndex(vnum=99941, short_descr="an enchanted ring")
    proto.affected = [
        Affect(where=0, type=0, level=20, duration=-1, location=0, modifier=0, bitvector=int(AffectFlag.SANCTUARY))
    ]

    ring = Object(instance_id=None, prototype=proto)
    ring.wear_loc = int(WearLocation.FINGER_L)
    ring.affected = []
    ring.enchanted = True

    char = Character(name="Cleric")
    char.affected = []
    char.affected_by = 0
    char.equipment = {WearLocation.FINGER_L: ring}

    affect_check(char, where=0, vector=int(AffectFlag.SANCTUARY))

    assert not (int(char.affected_by) & int(AffectFlag.SANCTUARY)), (
        "ROM src/handler.c:1237-1238 skips obj->pIndexData->affected when "
        "the instance is enchanted; the per-instance affected list (empty "
        "here) is authoritative. Got "
        f"affected_by={int(char.affected_by):#x}"
    )
