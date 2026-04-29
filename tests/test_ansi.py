from mud.net.ansi import strip_ansi, translate_ansi


def test_translate_ansi_replaces_tokens():
    assert translate_ansi("{rRed{x") == "\x1b[31mRed\x1b[0m"


def test_translate_ansi_handles_rom_specials():
    """COMM-008 — ROM `colour()` specials at src/comm.c:2714-2728:
    {D=dark grey, {*=bell, {/=newline, {-=tilde, {{=literal brace."""

    assert translate_ansi("{Ddim{x") == "\x1b[1;30mdim\x1b[0m"
    assert translate_ansi("alert{*") == "alert\x07"
    assert translate_ansi("line{/end") == "line\n\rend"
    assert translate_ansi("name{-with{-tilde") == "name~with~tilde"
    assert translate_ansi("brace{{here") == "brace{here"


def test_strip_ansi_eats_rom_token_pairs():
    """ROM strip path (`send_to_char` non-colour branch, src/comm.c:1995-2007)
    eats both characters of any `{X` pair, including the `{{` literal-brace
    token and the new specials."""

    assert strip_ansi("{rRed{x") == "Red"
    assert strip_ansi("{Ddim{x") == "dim"
    assert strip_ansi("alert{*") == "alert"
    assert strip_ansi("brace{{here") == "bracehere"
    assert strip_ansi("line{/end") == "lineend"
