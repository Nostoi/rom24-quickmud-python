"""Integration tests for ROM `src/lookup.c` parity functions.

Currently covers LOOKUP-001 (`race_lookup`). LOOKUP-002..008 are documented
in `docs/parity/LOOKUP_C_AUDIT.md` and remain OPEN.
"""

from __future__ import annotations


def test_race_lookup_exists_at_module_level():
    # mirrors ROM src/lookup.c:110 — race_lookup is a public function
    # callers (mud/persistence.py:614) import directly: `from mud.models.races import race_lookup`.
    from mud.models import races

    assert hasattr(races, "race_lookup"), (
        "mud.models.races.race_lookup must exist — mud/persistence.py:614 "
        "imports it on every pet load with a non-None race snapshot."
    )


def test_race_lookup_full_name_returns_index():
    # mirrors ROM src/lookup.c:110-122 — exact-name match returns the index.
    from mud.models.races import RACE_TABLE, race_lookup

    idx = race_lookup("human")
    assert idx > 0
    assert RACE_TABLE[idx].name == "human"


def test_race_lookup_prefix_match():
    # mirrors ROM src/lookup.c:114-118 — `!str_prefix(name, race_table[i].name)`
    # accepts `name` when it is a prefix of the table entry's name.
    from mud.models.races import RACE_TABLE, race_lookup

    idx = race_lookup("hum")
    assert idx > 0, "ROM accepts `hum` as a prefix abbreviation of `human`"
    assert RACE_TABLE[idx].name == "human"


def test_race_lookup_case_insensitive():
    # mirrors ROM src/lookup.c:116 — `LOWER(name[0]) == LOWER(...)`
    from mud.models.races import RACE_TABLE, race_lookup

    idx = race_lookup("HUMAN")
    assert RACE_TABLE[idx].name == "human"


def test_race_lookup_unknown_returns_zero():
    # mirrors ROM src/lookup.c:121 — fall-through `return 0`.
    from mud.models.races import race_lookup

    assert race_lookup("zzznotarace") == 0


def test_position_lookup_prefix_and_unknown():
    # mirrors ROM src/lookup.c:67-79 — position_lookup uses str_prefix; -1 on miss.
    # Closes LOOKUP-004.
    from mud.utils.prefix_lookup import position_lookup

    assert position_lookup("rest") == 5  # Position.RESTING
    assert position_lookup("standing") == 8
    assert position_lookup("dead") == 0
    assert position_lookup("nonsense") == -1


def test_clan_lookup_prefix_match():
    # mirrors ROM src/lookup.c:53-65 — clan_lookup uses str_prefix.
    # Closes LOOKUP-003.
    from mud.models.clans import lookup_clan_id

    # CLAN_TABLE: 0="", 1="loner", 2="rom"
    assert lookup_clan_id("lo") == 1, "ROM accepts `lo` as a prefix of `loner`"
    assert lookup_clan_id("ro") == 2, "ROM accepts `ro` as a prefix of `rom`"


def test_persistence_pet_race_restore_does_not_raise_import_error():
    # mirrors ROM src/save.c pet load path. The QuickMUD persistence module
    # imports `race_lookup` lazily inside the pet-restore block; if the symbol
    # is missing, every pet load with a non-None race crashes ImportError.
    # This test simply asserts the import succeeds.
    from mud.models.races import race_lookup as _race_lookup

    assert callable(_race_lookup)
