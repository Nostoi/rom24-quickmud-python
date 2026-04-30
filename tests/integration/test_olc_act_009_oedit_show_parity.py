"""OLC_ACT-009: `oedit show` byte-parity with ROM `oedit_show` + `show_obj_values`.

Mirrors ROM `src/olc_act.c:2733-2812` (`oedit_show`) and the per-type
value-display switch at `src/olc_act.c:2210-2374` (`show_obj_values`).
"""

from __future__ import annotations

from mud.commands.build import _oedit_show
from mud.models.area import Area
from mud.models.constants import ExtraFlag, WeaponFlag, WeaponType, WearFlag
from mud.models.obj import Affect, ObjIndex


def _make_proto(**overrides) -> ObjIndex:
    area = Area(vnum=10, name="Test Area")
    proto = ObjIndex(vnum=1010, name="thing")
    proto.area = area
    proto.short_descr = "a thing"
    proto.description = "A thing lies here."
    proto.material = "wood"
    proto.item_type = "trash"
    proto.level = 5
    proto.weight = 3
    proto.cost = 25
    proto.condition = 100
    proto.wear_flags = 0
    proto.extra_flags = 0
    proto.value = [0, 0, 0, 0, 0]
    proto.affected = []
    proto.extra_descr = []
    for key, value in overrides.items():
        setattr(proto, key, value)
    return proto


def test_header_uses_rom_byte_layout() -> None:
    """ROM olc_act.c:2742-2774 — labels and column widths are exact."""
    proto = _make_proto()
    output = _oedit_show(proto)
    assert "Name:        [thing]" in output
    assert "Area:        [   10] Test Area" in output
    assert "Vnum:        [ 1010]" in output
    assert "Type:        [trash]" in output
    assert "Level:       [    5]" in output
    assert "Material:    [wood]" in output
    assert "Condition:   [  100]" in output
    assert "Weight:      [    3]" in output
    assert "Cost:        [   25]" in output
    # ROM emits Short desc + Long desc with the indented continuation line.
    assert "Short desc:  a thing" in output
    assert "Long desc:\n     A thing lies here." in output
    # Python-only "Object: ..." header line is gone.
    assert "Object: " not in output


def test_wear_and_extra_flags_use_flag_string() -> None:
    """ROM olc_act.c:2756-2762 — Wear flags + Extra flags via flag_string."""
    proto = _make_proto(
        wear_flags=int(WearFlag.TAKE | WearFlag.WIELD),
        extra_flags=int(ExtraFlag.GLOW | ExtraFlag.HUM),
    )
    output = _oedit_show(proto)
    assert "Wear flags:  [take wield]" in output
    assert "Extra flags: [glow hum]" in output


def test_extra_descr_keywords_row_conditional() -> None:
    """ROM olc_act.c:2776-2790 — `Ex desc kwd: [kw1][kw2]\\n\\r`."""
    proto = _make_proto(extra_descr=[
        {"keyword": "rune", "description": "ignored"},
        {"keyword": "engraving", "description": "ignored"},
    ])
    output = _oedit_show(proto)
    assert "Ex desc kwd: [rune][engraving]" in output

    no_extra = _make_proto()
    no_extra_out = _oedit_show(no_extra)
    assert "Ex desc kwd:" not in no_extra_out


def test_affects_table_when_present() -> None:
    """ROM olc_act.c:2796-2807 — affects table with header + rows."""
    proto = _make_proto()
    proto.affected = [
        Affect(where=0, type=0, level=0, duration=-1, location=18, modifier=2, bitvector=0),  # APPLY_HITROLL
        Affect(where=0, type=0, level=0, duration=-1, location=1, modifier=1, bitvector=0),  # APPLY_STR
    ]
    output = _oedit_show(proto)
    assert "Number Modifier Affects" in output
    assert "------ -------- -------" in output
    assert "[   0] 2        hitroll" in output
    assert "[   1] 1        strength" in output


def test_show_obj_values_armor() -> None:
    """ROM olc_act.c:2292-2301 — ITEM_ARMOR emits 4 AC value rows."""
    proto = _make_proto(item_type="armor", value=[5, 6, 7, 2, 0])
    output = _oedit_show(proto)
    assert "[v0] Ac pierce       [5]" in output
    assert "[v1] Ac bash         [6]" in output
    assert "[v2] Ac slash        [7]" in output
    assert "[v3] Ac exotic       [2]" in output


def test_show_obj_values_weapon() -> None:
    """ROM olc_act.c:2306-2320 — ITEM_WEAPON value labels."""
    proto = _make_proto(
        item_type="weapon",
        value=[int(WeaponType.SWORD), 2, 8, 3, int(WeaponFlag.FLAMING)],  # value[3]=3 → "slash" attack
    )
    output = _oedit_show(proto)
    assert "[v0] Weapon class:   sword" in output
    assert "[v1] Number of dice: [2]" in output
    assert "[v2] Type of dice:   [8]" in output
    assert "[v3] Type:           slash" in output
    assert "[v4] Special type:   flaming" in output


def test_show_obj_values_container() -> None:
    """ROM olc_act.c:2322-2335 — ITEM_CONTAINER values."""
    proto = _make_proto(item_type="container", value=[50, 0, 0, 100, 100])
    output = _oedit_show(proto)
    assert "[v0] Weight:     [50 kg]" in output
    assert "[v3] Capacity    [100]" in output
    assert "[v4] Weight Mult [100]" in output


def test_show_obj_values_light_infinite() -> None:
    """ROM olc_act.c:2219-2225 — value[2]==-1 emits `Infinite[-1]`."""
    proto = _make_proto(item_type="light", value=[0, 0, -1, 0, 0])
    output = _oedit_show(proto)
    assert "[v2] Light:  Infinite[-1]" in output

    finite = _make_proto(item_type="light", value=[0, 0, 50, 0, 0])
    assert "[v2] Light:  [50]" in _oedit_show(finite)
