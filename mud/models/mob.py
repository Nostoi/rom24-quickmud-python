from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .area import Area

from mud.models.constants import ActFlag, Sex, Size, convert_flags_from_letters


@dataclass
class MobProgram:
    """Representation of MPROG_LIST"""

    trig_type: int
    trig_phrase: str | None = None
    vnum: int = 0
    code: str | None = None


@dataclass
class MobIndex:
    """Python representation of MOB_INDEX_DATA"""

    vnum: int
    player_name: str | None = None
    short_descr: str | None = None
    long_descr: str | None = None
    description: str | None = None
    race: str | int = 0
    act_flags: str | ActFlag | int = ""
    affected_by: str = ""
    alignment: int = 0
    group: int = 0
    level: int = 1
    thac0: int = 20
    ac: str = "1d1+0"
    hit_dice: str = "1d1+0"
    mana_dice: str = "1d1+0"
    damage_dice: str = "1d4+0"
    damage_type: str = "beating"
    ac_pierce: int = 0
    ac_bash: int = 0
    ac_slash: int = 0
    ac_exotic: int = 0
    offensive: str = ""
    immune: str = ""
    resist: str = ""
    vuln: str = ""
    start_pos: str | int = "standing"
    default_pos: str | int = "standing"
    sex: Sex | str | int = Sex.NONE
    wealth: int = 0
    form: str | int = 0
    parts: str | int = 0
    size: Size | str | int = Size.MEDIUM
    material: str | None = "0"
    spec_fun: str | None = None
    pShop: object | None = None
    mprogs: list[MobProgram] = field(default_factory=list)
    area: Area | None = None
    new_format: bool = False
    count: int = 0
    killed: int = 0
    # Legacy compatibility fields
    act: int = 0
    hitroll: int = 0
    hit: tuple[int, int, int] = (0, 0, 0)
    mana: tuple[int, int, int] = (0, 0, 0)
    damage: tuple[int, int, int] = (0, 0, 0)
    dam_type: int = 0
    off_flags: int = 0
    imm_flags: int = 0
    res_flags: int = 0
    vuln_flags: int = 0
    mprog_flags: int = 0

    def __repr__(self) -> str:
        return f"<MobIndex vnum={self.vnum} name={self.short_descr!r}>"

    _act_cache: ActFlag | None = field(default=None, init=False, repr=False)

    def get_act_flags(self) -> ActFlag:
        """Return act flags as an IntFlag, converting from ROM letters on demand."""

        if self._act_cache is not None:
            return self._act_cache
        if isinstance(self.act_flags, ActFlag):
            self._act_cache = self.act_flags
            return self.act_flags
        if isinstance(self.act_flags, int):
            flags = ActFlag(self.act_flags)
            self._act_cache = flags
            return flags
        if isinstance(self.act_flags, str):
            flags = convert_flags_from_letters(self.act_flags, ActFlag)
            # Cache both numeric and enum forms for future lookups
            self.act = int(flags)
            self._act_cache = flags
            self.act_flags = flags
            return flags
        self._act_cache = ActFlag(0)
        return ActFlag(0)

    def has_act_flag(self, flag: ActFlag) -> bool:
        return bool(self.get_act_flags() & flag)


mob_registry: dict[int, MobIndex] = {}
