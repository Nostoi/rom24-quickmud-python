from pathlib import Path

import pytest

from mud.loaders import load_area_file
from mud.registry import area_registry

def test_duplicate_area_vnum_raises_value_error(tmp_path):
    area_registry.clear()
    src = Path('area') / 'midgaard.are'
    lines = src.read_text(encoding='latin-1').splitlines()
    lines[1] = 'dup.are~'
    dup = tmp_path / 'dup.are'
    dup.write_text("\n".join(lines), encoding='latin-1')
    load_area_file(str(src))
    with pytest.raises(ValueError):
        load_area_file(str(dup))
    area_registry.clear()


def test_areadata_parsing(tmp_path):
    area_registry.clear()
    content = (
        "#AREA\n"
        "test.are~\n"
        "Test Area~\n"
        "Credits~\n"
        "0 0\n"
        "#AREADATA\n"
        "Builders Alice~\n"
        "Security 9\n"
        "Flags 3\n"
        "#$\n"
    )
    path = tmp_path / "test.are"
    path.write_text(content, encoding="latin-1")
    area = load_area_file(str(path))
    assert area.builders == "Alice"
    assert area.security == 9
    assert area.area_flags == 3
    area_registry.clear()
