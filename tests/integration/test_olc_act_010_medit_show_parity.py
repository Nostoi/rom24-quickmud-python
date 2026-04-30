"""OLC_ACT-010: `medit show` byte-parity with ROM `medit_show`.

Mirrors ROM `src/olc_act.c:3519-3699` for the structural rewrite.

This commit closes the structural / row-completeness half of the gap
(all rows present in ROM are now emitted in Python). Two follow-ups
remain as documented sub-gaps:

- OLC_ACT-010b: dice/AC are stored as strings ("15d8+50") in Python's
  MobIndex while ROM stores them as 3 ints (number/type/bonus). Emitted
  as-is in brackets here; full ROM `[%2dd%-3d+%4d]` column formatting
  needs the data model to expose the components.
- OLC_ACT-010c: shop / mprogs / spec_fun rows. ROM emits these
  conditionally when `pMob->pShop`, `pMob->mprogs`, or `pMob->spec_fun`
  are present. Python's MobIndex has the fields but they default to
  None; full conditional rendering needs MobShop / MProg model
  alignment with ROM and a spec_name lookup.
- ROM-faithful flag table names (e.g. ROM "stay_area" vs Python
  "STAY_AREA" lowercased): tracked alongside OLC_ACT-009's wear/extra
  display tables. Until ROM-display tables for act/affect/form/part/
  imm/res/vuln/off/size/position land, the flag_string output uses
  Python enum-name lowercase forms.
"""

from __future__ import annotations

from mud.commands.build import _medit_show
from mud.models.area import Area
from mud.models.constants import (
    ActFlag,
    AffectFlag,
    FormFlag,
    ImmFlag,
    OffFlag,
    PartFlag,
    Position,
    ResFlag,
    Size,
    VulnFlag,
)
from mud.models.mob import MobIndex
from mud.models.races import race_lookup


def _make_proto(**overrides) -> MobIndex:
    area = Area(vnum=42, name="Test Area")
    proto = MobIndex(vnum=4242)
    proto.area = area
    proto.player_name = "guard"
    proto.short_descr = "a guard"
    proto.long_descr = "A guard stands here.\n"
    proto.description = "Just a guard.\n"
    proto.race = "human"
    proto.act_flags = int(ActFlag.IS_NPC)
    proto.affected_by = 0
    proto.alignment = 0
    proto.level = 10
    proto.hitroll = 5
    proto.dam_type = 3  # "slash" in ATTACK_TABLE
    proto.hit_dice = "10d8+50"
    proto.mana_dice = "5d4+0"
    proto.damage_dice = "2d6+3"
    proto.ac = "10d1+0"
    proto.material = "flesh"
    proto.start_pos = "standing"
    proto.default_pos = "standing"
    proto.wealth = 250
    proto.form = 0
    proto.parts = 0
    proto.size = Size.MEDIUM
    proto.imm_flags = 0
    proto.res_flags = 0
    proto.vuln_flags = 0
    proto.off_flags = 0
    proto.group = 0
    for key, value in overrides.items():
        setattr(proto, key, value)
    return proto


def test_header_uses_rom_byte_layout() -> None:
    proto = _make_proto()
    output = _medit_show(proto)
    assert "Name:        [guard]" in output
    assert "Area:        [   42] Test Area" in output
    assert "Vnum:        [ 4242]" in output
    assert "Sex:" in output and "Race:" in output
    assert "Level:       [10]" in output
    assert "Align: [   0]" in output
    assert "Hitroll: [ 5]" in output
    assert "Dam Type:    [slash]" in output


def test_header_displays_race_name_from_rom_index() -> None:
    proto = _make_proto(race=race_lookup("human"))
    output = _medit_show(proto)
    assert "Race: [human]" in output


def test_act_and_affected_by_rows_present() -> None:
    proto = _make_proto(
        act_flags=int(ActFlag.IS_NPC | ActFlag.SENTINEL),
        affected_by=int(AffectFlag.SANCTUARY),
    )
    output = _medit_show(proto)
    assert "Act:         [" in output
    assert "Affected by: [" in output
    # ROM-faithful name strings deferred to OLC_ACT-010d display-table port;
    # for now just verify the rows render and reflect the bits set.
    assert "sentinel" in output.lower()


def test_armor_form_parts_imm_res_vuln_off_size_rows_present() -> None:
    proto = _make_proto(
        form=int(FormFlag.MAMMAL),
        parts=int(PartFlag.HEAD | PartFlag.ARMS),
        imm_flags=int(ImmFlag.FIRE),
        res_flags=int(ResFlag.COLD),
        vuln_flags=int(VulnFlag.LIGHTNING),
        off_flags=int(OffFlag.AREA_ATTACK),
    )
    output = _medit_show(proto)
    assert "Armor:       [pierce:" in output
    assert "Form:        [" in output
    assert "Parts:       [" in output
    assert "Imm:         [" in output
    assert "Res:         [" in output
    assert "Vuln:        [" in output
    assert "Off:         [" in output
    assert "Size:        [medium]" in output


def test_position_rows_present() -> None:
    proto = _make_proto(start_pos=int(Position.STANDING), default_pos=int(Position.SLEEPING))
    output = _medit_show(proto)
    assert "Start pos.   [standing]" in output
    assert "Default pos  [sleeping]" in output


def test_dice_rows_present_as_strings() -> None:
    """OLC_ACT-010b — dice fields emitted as-is (Python stores strings)."""
    proto = _make_proto(hit_dice="15d8+50", damage_dice="2d6+3", mana_dice="5d4+0")
    output = _medit_show(proto)
    assert "Hit dice:    [15d8+50]" in output
    assert "Damage dice: [2d6+3]" in output
    assert "Mana dice:   [5d4+0]" in output


def test_short_long_description_rows() -> None:
    proto = _make_proto()
    output = _medit_show(proto)
    assert "Short descr: a guard" in output
    assert "Long descr:\nA guard stands here." in output
    assert "Description:\nJust a guard." in output


def test_material_and_wealth_rows() -> None:
    proto = _make_proto(material="flesh", wealth=12345)
    output = _medit_show(proto)
    assert "Material:    [flesh]" in output
    assert "Wealth:      [12345]" in output


def test_python_only_header_removed() -> None:
    """Old "Mobile: ..." Python header is gone; ROM has no such line."""
    proto = _make_proto()
    output = _medit_show(proto)
    assert "Mobile: " not in output
