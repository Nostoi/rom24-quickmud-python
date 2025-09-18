from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .area import Area

from mud.models.constants import ActFlag, convert_flags_from_letters

@dataclass
class MobProgram:
    """Representation of MPROG_LIST"""
    trig_type: int
    trig_phrase: Optional[str] = None
    vnum: int = 0
    code: Optional[str] = None

@dataclass
class MobIndex:
    """Python representation of MOB_INDEX_DATA"""
    vnum: int
    player_name: Optional[str] = None
    short_descr: Optional[str] = None
    long_descr: Optional[str] = None
    description: Optional[str] = None
    race: Optional[str] = None
    act_flags: str = ''
    affected_by: str = ''
    alignment: int = 0
    group: int = 0
    level: int = 1
    thac0: int = 20
    ac: str = '1d1+0'
    hit_dice: str = '1d1+0'
    mana_dice: str = '1d1+0'
    damage_dice: str = '1d4+0'
    damage_type: str = 'beating'
    ac_pierce: int = 0
    ac_bash: int = 0
    ac_slash: int = 0
    ac_exotic: int = 0
    offensive: str = ''
    immune: str = ''
    resist: str = ''
    vuln: str = ''
    start_pos: str = 'standing'
    default_pos: str = 'standing'
    sex: str = 'neutral'
    wealth: int = 0
    form: str = '0'
    parts: str = '0'
    size: str = 'medium'
    material: str = '0'
    spec_fun: Optional[str] = None
    pShop: Optional[object] = None
    mprogs: List[MobProgram] = field(default_factory=list)
    area: Optional['Area'] = None
    new_format: bool = False
    count: int = 0
    killed: int = 0
    # Legacy compatibility fields
    act: int = 0
    hitroll: int = 0
    hit: Tuple[int, int, int] = (0, 0, 0)
    mana: Tuple[int, int, int] = (0, 0, 0)
    damage: Tuple[int, int, int] = (0, 0, 0)
    dam_type: int = 0
    off_flags: int = 0
    imm_flags: int = 0
    res_flags: int = 0
    vuln_flags: int = 0
    start_pos: int = 0
    default_pos: int = 0
    sex: int = 0
    race: int = 0
    wealth: int = 0
    form: int = 0
    parts: int = 0
    size: int = 0
    material: Optional[str] = None
    mprog_flags: int = 0

    def __repr__(self) -> str:
        return f"<MobIndex vnum={self.vnum} name={self.short_descr!r}>"

    def get_act_flags(self) -> ActFlag:
        """Return act flags as an IntFlag, converting from ROM letters on demand."""

        raw = getattr(self, "_act_cache", None)
        if isinstance(raw, ActFlag):
            return raw
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
