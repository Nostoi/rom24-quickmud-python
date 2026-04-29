"""ROM `fix_sex` helper — clamps `ch.sex` to [0,2].

Mirrors ROM src/comm.c:2178-2182:

    void fix_sex (CHAR_DATA * ch)
    {
        if (ch->sex < 0 || ch->sex > 2)
            ch->sex = IS_NPC (ch) ? 0 : ch->pcdata->true_sex;
    }
"""

from __future__ import annotations

from typing import Any


def fix_sex(ch: Any) -> None:
    sex = getattr(ch, "sex", 0)
    if sex < 0 or sex > 2:
        if getattr(ch, "is_npc", False):
            ch.sex = 0
        else:
            pcdata = getattr(ch, "pcdata", None)
            ch.sex = getattr(pcdata, "true_sex", 0) if pcdata is not None else 0
