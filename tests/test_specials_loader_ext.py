from mud.loaders.base_loader import BaseTokenizer
from mud.loaders.specials_loader import load_specials
from mud.models.mob import MobIndex
from mud.registry import mob_registry


def test_load_specials_handles_braces_and_invalid_lines():
    mob_registry.clear()
    vnum = 12345
    mob_registry[vnum] = MobIndex(vnum=vnum, short_descr="Tester", level=1)

    lines = [
        "#SPECIALS",
        "{ M 12345 spec_dummy }",
        "* comment line should be ignored",
        "M not_a_number spec_ignore",
        "S",
    ]
    tok = BaseTokenizer(lines)
    # consume header
    assert tok.next_line() == "#SPECIALS"
    load_specials(tok, area=None)

    assert mob_registry[vnum].spec_fun == "spec_dummy"
