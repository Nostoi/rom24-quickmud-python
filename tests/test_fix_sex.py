"""COMM-009 — standalone fix_sex helper, mirrors ROM src/comm.c:2178-2182."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from mud.utils.fix_sex import fix_sex


def _pc(sex: int, true_sex: int) -> SimpleNamespace:
    return SimpleNamespace(sex=sex, is_npc=False, pcdata=SimpleNamespace(true_sex=true_sex))


def _npc(sex: int) -> SimpleNamespace:
    return SimpleNamespace(sex=sex, is_npc=True, pcdata=None)


@pytest.mark.parametrize("sex", [0, 1, 2])
def test_fix_sex_passes_through_valid_values(sex: int) -> None:
    ch = _pc(sex=sex, true_sex=1)
    fix_sex(ch)
    assert ch.sex == sex


def test_fix_sex_clamps_pc_out_of_range_to_true_sex() -> None:
    ch = _pc(sex=-1, true_sex=2)
    fix_sex(ch)
    assert ch.sex == 2

    ch = _pc(sex=3, true_sex=1)
    fix_sex(ch)
    assert ch.sex == 1


def test_fix_sex_clamps_npc_out_of_range_to_zero() -> None:
    ch = _npc(sex=-1)
    fix_sex(ch)
    assert ch.sex == 0

    ch = _npc(sex=5)
    fix_sex(ch)
    assert ch.sex == 0
