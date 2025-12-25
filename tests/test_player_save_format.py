import mud.persistence as persistence
from mud.models.area import Area
from mud.models.character import Character, PCData, character_registry
from mud.models.constants import ROOM_VNUM_LIMBO, ROOM_VNUM_TEMPLE
from mud.models.player_json import PlayerJson
from mud.models.room import Room
from mud.registry import room_registry
from mud.scripts.convert_player_to_json import convert_player
from mud.world import create_test_character, initialize_world


def _bit(ch: str) -> int:
    return 1 << (ord(ch) - ord("A"))


def _lower_bit(ch: str) -> int:
    return 1 << (26 + ord(ch) - ord("a"))


def test_convert_legacy_player_flags_roundtrip():
    pj = convert_player("player/Shemp")
    # Basic parsed fields
    assert pj.name == "Shemp"
    assert pj.level == 2
    assert pj.race == 0
    assert pj.ch_class == 3
    assert pj.sex == 1
    assert pj.trust == 0
    assert pj.security == 0
    assert pj.gold == 0
    assert pj.silver == 0
    assert pj.exp == 2088
    assert pj.position == 8
    assert pj.room_vnum == 3714
    assert pj.conditions == [0, 42, 45, 45]
    assert pj.perm_hit == 29
    assert pj.perm_mana == 102
    assert pj.perm_move == 106
    assert pj.practice == 1
    assert pj.train == 1
    assert pj.saving_throw == -1
    assert pj.alignment == 750
    assert pj.hitroll == 1
    assert pj.damroll == 0
    assert pj.wimpy == 0
    assert pj.armor == [95, 95, 95, 99]
    assert pj.perm_stat == [19, 13, 13, 13, 13]
    assert pj.mod_stat == [0, 0, 0, 0, 0]
    assert pj.points == 40
    assert pj.true_sex == 1
    assert pj.last_level == 0
    assert pj.affected_by == 0
    assert pj.wiznet == 0
    # Flags: Act QT => Q and T set
    assert pj.plr_flags & _bit("Q")
    assert pj.plr_flags & _bit("T")
    # Comm NOP => N,O,P set
    for ch in "NOP":
        assert pj.comm_flags & _bit(ch)
    # Round-trip through dict preserves exact integers
    data = pj.to_dict()
    pj2 = PlayerJson.from_dict(data)
    assert pj2.plr_flags == pj.plr_flags
    assert pj2.affected_by == pj.affected_by
    assert pj2.comm_flags == pj.comm_flags
    assert pj2.wiznet == pj.wiznet
    assert pj2.conditions == pj.conditions


def test_convert_player_accepts_zero_flag_sentinel(tmp_path):
    fixture = tmp_path / "zero"
    fixture.write_text(
        "\n".join(
            [
                "#PLAYER",
                "Name Zero~",
                "Race human~",
                "Sex  1",
                "Cla  3",
                "Levl 2",
                "Room 3001",
                "HMV  1 2 3 4 5 6",
                "Act  0",
                "AfBy 0",
                "Comm 0",
                "Wizn 0",
                "#END",
            ]
        ),
        encoding="latin-1",
    )

    pj = convert_player(fixture)
    assert pj.plr_flags == 0
    assert pj.affected_by == 0
    assert pj.comm_flags == 0
    assert pj.wiznet == 0


def test_convert_player_decodes_lowercase_flags(tmp_path):
    fixture = tmp_path / "mixed"
    fixture.write_text(
        "\n".join(
            [
                "#PLAYER",
                "Name Lower~",
                "Race human~",
                "Sex  1",
                "Cla  3",
                "Levl 2",
                "Room 3001",
                "HMV  1 2 3 4 5 6",
                "Act  Qa",
                "AfBy d",
                "Comm bc",
                "Wizn ef",
                "#END",
            ]
        ),
        encoding="latin-1",
    )

    pj = convert_player(fixture)
    expected_act = _bit("Q") | _lower_bit("a")
    expected_comm = _lower_bit("b") | _lower_bit("c")
    assert pj.plr_flags == expected_act
    assert pj.affected_by == _lower_bit("d")
    assert pj.comm_flags == expected_comm
    assert pj.wiznet == (_lower_bit("e") | _lower_bit("f"))


def test_player_save_roundtrip_preserves_invis_level(tmp_path, monkeypatch):
    initialize_world("area/area.lst")
    character_registry.clear()
    char = create_test_character("InviImm", 3001)
    char.invis_level = 51

    monkeypatch.setattr(persistence, "PLAYERS_DIR", tmp_path)
    persistence.save_character(char)

    character_registry.clear()
    loaded = persistence.load_character("InviImm")
    assert loaded is not None
    assert loaded.invis_level == 51


def test_player_save_roundtrip_preserves_incog_level(tmp_path, monkeypatch):
    initialize_world("area/area.lst")
    character_registry.clear()
    char = create_test_character("IncogImm", 3001)
    char.incog_level = 52

    monkeypatch.setattr(persistence, "PLAYERS_DIR", tmp_path)
    persistence.save_character(char)

    character_registry.clear()
    loaded = persistence.load_character("IncogImm")
    assert loaded is not None
    assert loaded.incog_level == 52


def test_player_save_roundtrip_preserves_prefix(tmp_path, monkeypatch):
    initialize_world("area/area.lst")
    character_registry.clear()
    char = create_test_character("PrefSaver", 3001)
    char.prefix = "say"

    monkeypatch.setattr(persistence, "PLAYERS_DIR", tmp_path)
    persistence.save_character(char)

    character_registry.clear()
    loaded = persistence.load_character("PrefSaver")
    assert loaded is not None
    assert loaded.prefix == "say"


def test_player_save_roundtrip_preserves_clan(tmp_path, monkeypatch):
    initialize_world("area/area.lst")
    character_registry.clear()
    char = create_test_character("ClanKeeper", 3001)
    char.clan = 2

    monkeypatch.setattr(persistence, "PLAYERS_DIR", tmp_path)
    persistence.save_character(char)

    character_registry.clear()
    loaded = persistence.load_character("ClanKeeper")
    assert loaded is not None
    assert loaded.clan == 2


def test_player_save_roundtrip_preserves_newbie_help_flag(tmp_path, monkeypatch):
    initialize_world("area/area.lst")
    character_registry.clear()
    char = create_test_character("NewbieSeen", 3001)
    char.newbie_help_seen = True

    monkeypatch.setattr(persistence, "PLAYERS_DIR", tmp_path)
    persistence.save_character(char)

    character_registry.clear()
    loaded = persistence.load_character("NewbieSeen")
    assert loaded is not None
    assert loaded.newbie_help_seen is True


def test_save_character_uses_was_in_room_for_limbo(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "PLAYERS_DIR", tmp_path)

    original_rooms = dict(room_registry)
    original_characters = list(character_registry)
    room_registry.clear()
    character_registry.clear()

    try:
        area = Area(name="Idle")
        limbo = Room(vnum=ROOM_VNUM_LIMBO, area=area)
        home = Room(vnum=ROOM_VNUM_TEMPLE + 42, area=area)
        temple = Room(vnum=ROOM_VNUM_TEMPLE, area=area)
        room_registry[limbo.vnum] = limbo
        room_registry[home.vnum] = home
        room_registry[temple.vnum] = temple

        char = Character(
            name="Voidling",
            level=12,
            hit=20,
            max_hit=20,
            mana=10,
            max_mana=10,
            move=10,
            max_move=10,
            is_npc=False,
            pcdata=PCData(condition=[48, 48, 48, 48]),
        )
        limbo.add_character(char)
        char.was_in_room = home
        character_registry.append(char)

        persistence.save_character(char)

        limbo.remove_character(char)
        character_registry.clear()

        loaded = persistence.load_character("Voidling")
        assert loaded is not None
        assert loaded.room is home
        assert loaded in home.people
        assert limbo.people == []

        character_registry.clear()
    finally:
        room_registry.clear()
        room_registry.update(original_rooms)
        character_registry.clear()
        character_registry.extend(original_characters)


def test_save_character_defaults_to_temple_when_room_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "PLAYERS_DIR", tmp_path)

    original_rooms = dict(room_registry)
    original_characters = list(character_registry)
    room_registry.clear()
    character_registry.clear()

    try:
        area = Area(name="Recall")
        limbo = Room(vnum=ROOM_VNUM_LIMBO, area=area)
        temple = Room(vnum=ROOM_VNUM_TEMPLE, area=area)
        room_registry[limbo.vnum] = limbo
        room_registry[temple.vnum] = temple

        char = Character(
            name="Recall",
            level=8,
            hit=18,
            max_hit=18,
            mana=12,
            max_mana=12,
            move=14,
            max_move=14,
            is_npc=False,
            pcdata=PCData(condition=[48, 48, 48, 48]),
        )
        limbo.add_character(char)
        character_registry.append(char)

        # Explicitly clear was_in_room to trigger the temple fallback.
        char.was_in_room = None
        persistence.save_character(char)

        limbo.remove_character(char)
        character_registry.clear()

        loaded = persistence.load_character("Recall")
        assert loaded is not None
        assert loaded.room is temple

        character_registry.clear()
    finally:
        room_registry.clear()
        room_registry.update(original_rooms)
        character_registry.clear()
        character_registry.extend(original_characters)


def test_load_character_defaults_to_limbo_when_room_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "PLAYERS_DIR", tmp_path)

    original_rooms = dict(room_registry)
    original_characters = list(character_registry)
    room_registry.clear()
    character_registry.clear()

    try:
        area = Area(name="Crash")
        limbo = Room(vnum=ROOM_VNUM_LIMBO, area=area)
        lost = Room(vnum=ROOM_VNUM_TEMPLE + 99, area=area)
        room_registry[limbo.vnum] = limbo
        room_registry[lost.vnum] = lost

        char = Character(
            name="Crash",
            level=12,
            hit=24,
            max_hit=24,
            mana=18,
            max_mana=18,
            move=16,
            max_move=16,
            is_npc=False,
            pcdata=PCData(condition=[48, 48, 48, 48]),
        )
        lost.add_character(char)
        character_registry.append(char)

        persistence.save_character(char)

        lost.remove_character(char)
        room_registry.pop(lost.vnum)
        character_registry.clear()

        loaded = persistence.load_character("Crash")
        assert loaded is not None
        assert loaded.room is limbo
        assert loaded in limbo.people

        character_registry.clear()
    finally:
        room_registry.clear()
        room_registry.update(original_rooms)
        character_registry.clear()
        character_registry.extend(original_characters)


def test_load_character_defaults_to_temple_when_limbo_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "PLAYERS_DIR", tmp_path)

    original_rooms = dict(room_registry)
    original_characters = list(character_registry)
    room_registry.clear()
    character_registry.clear()

    try:
        area = Area(name="Fallback")
        temple = Room(vnum=ROOM_VNUM_TEMPLE, area=area)
        lost = Room(vnum=ROOM_VNUM_TEMPLE + 51, area=area)
        room_registry[temple.vnum] = temple
        room_registry[lost.vnum] = lost

        char = Character(
            name="NoLimbo",
            level=18,
            hit=30,
            max_hit=30,
            mana=20,
            max_mana=20,
            move=22,
            max_move=22,
            is_npc=False,
            pcdata=PCData(condition=[48, 48, 48, 48]),
        )
        lost.add_character(char)
        character_registry.append(char)

        persistence.save_character(char)

        lost.remove_character(char)
        room_registry.pop(lost.vnum)
        character_registry.clear()

        loaded = persistence.load_character("NoLimbo")
        assert loaded is not None
        assert loaded.room is temple

        character_registry.clear()
    finally:
        room_registry.clear()
        room_registry.update(original_rooms)
        character_registry.clear()
        character_registry.extend(original_characters)


def test_save_character_defaults_to_temple_when_was_in_room_invalid(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "PLAYERS_DIR", tmp_path)

    original_rooms = dict(room_registry)
    original_characters = list(character_registry)
    room_registry.clear()
    character_registry.clear()

    try:
        area = Area(name="Corrupt")
        limbo = Room(vnum=ROOM_VNUM_LIMBO, area=area)
        temple = Room(vnum=ROOM_VNUM_TEMPLE, area=area)
        room_registry[limbo.vnum] = limbo
        room_registry[temple.vnum] = temple

        char = Character(
            name="CorruptLimbo",
            level=14,
            hit=26,
            max_hit=26,
            mana=17,
            max_mana=17,
            move=15,
            max_move=15,
            is_npc=False,
            pcdata=PCData(condition=[48, 48, 48, 48]),
        )
        limbo.add_character(char)
        char.was_in_room = object()
        character_registry.append(char)

        persistence.save_character(char)

        limbo.remove_character(char)
        character_registry.clear()

        loaded = persistence.load_character("CorruptLimbo")
        assert loaded is not None
        assert loaded.room is temple

        character_registry.clear()
    finally:
        room_registry.clear()
        room_registry.update(original_rooms)
        character_registry.clear()
        character_registry.extend(original_characters)


def test_missing_header_footer_and_bad_hmv(tmp_path):
    # Missing #PLAYER header
    bad1 = tmp_path / "bad1"
    bad1.write_text("Name Bob~\n#END\n", encoding="latin-1")
    try:
        convert_player(str(bad1))
        assert False, "expected ValueError for missing header"
    except ValueError as e:
        assert "missing #PLAYER" in str(e)

    # Missing #END footer
    bad2 = tmp_path / "bad2"
    bad2.write_text("#PLAYER\nName Bob~\n", encoding="latin-1")
    try:
        convert_player(str(bad2))
        assert False, "expected ValueError for missing footer"
    except ValueError as e:
        assert "missing #END" in str(e)

    # Bad HMV width (not 6 ints)
    bad3 = tmp_path / "bad3"
    bad3.write_text("#PLAYER\nName Bob~\nLevl 1\nRoom 3001\nHMV 1 2 3\n#END\n", encoding="latin-1")
    try:
        convert_player(str(bad3))
        assert False, "expected ValueError for HMV width"
    except ValueError as e:
        assert "HMV" in str(e)

    # Bad Act letters
    bad4 = tmp_path / "bad4"
    bad4.write_text("#PLAYER\nName Bob~\nLevl 1\nRoom 3001\nHMV 1 2 3 4 5 6\nAct Q1\n#END\n", encoding="latin-1")
    try:
        convert_player(str(bad4))
        assert False, "expected ValueError for Act flags"
    except ValueError as e:
        assert "Act flags" in str(e)

    # Bad Cnd width (not 4 ints)
    bad5 = tmp_path / "bad5"
    bad5.write_text("#PLAYER\nName Bob~\nLevl 1\nRoom 3001\nHMV 1 2 3 4 5 6\nCnd 1 2 3\n#END\n", encoding="latin-1")
    try:
        convert_player(str(bad5))
        assert False, "expected ValueError for Cnd width"
    except ValueError as e:
        assert "Cnd" in str(e)


def test_invalid_level_and_room(tmp_path):
    bad = tmp_path / "bad"
    bad.write_text("#PLAYER\nName Bob~\nLevl X\nRoom 3001\nHMV 1 2 3 4 5 6\n#END\n", encoding="latin-1")
    try:
        convert_player(str(bad))
        assert False
    except ValueError as e:
        assert "invalid Levl" in str(e)

    bad2 = tmp_path / "bad2"
    bad2.write_text("#PLAYER\nName Bob~\nLevl 1\nRoom ROOM\nHMV 1 2 3 4 5 6\n#END\n", encoding="latin-1")
    try:
        convert_player(str(bad2))
        assert False
    except ValueError as e:
        assert "invalid Room" in str(e)


def test_multi_letter_flags(tmp_path):
    good = tmp_path / "good"
    good.write_text(
        "#PLAYER\nName Bob~\nLevl 1\nRoom 3001\nHMV 1 2 3 4 5 6\nAct ABC\nComm NOP\n#END\n", encoding="latin-1"
    )
    pj = convert_player(str(good))

    def bit(ch):
        return 1 << (ord(ch) - ord("A"))

    assert pj.plr_flags == bit("A") | bit("B") | bit("C")
    assert pj.comm_flags == bit("N") | bit("O") | bit("P")


def test_player_json_field_order():
    pj = PlayerJson(
        name="X",
        level=1,
        race=2,
        ch_class=3,
        sex=1,
        trust=4,
        security=9,
        hit=1,
        max_hit=1,
        mana=1,
        max_mana=1,
        move=1,
        max_move=1,
        perm_hit=2,
        perm_mana=3,
        perm_move=4,
        gold=5,
        silver=6,
        exp=7,
        practice=8,
        train=9,
        saving_throw=-1,
        alignment=100,
        hitroll=10,
        damroll=11,
        wimpy=12,
        points=13,
        true_sex=1,
        last_level=2,
        position=0,
        room_vnum=3001,
        inventory=[],
        equipment={},
        plr_flags=0,
        comm_flags=0,
    )
    data = pj.to_dict()
    keys = list(data.keys())
    expected = [
        "name",
        "level",
        "race",
        "ch_class",
        "sex",
        "trust",
        "security",
        "hit",
        "max_hit",
        "mana",
        "max_mana",
        "move",
        "max_move",
        "perm_hit",
        "perm_mana",
        "perm_move",
        "gold",
        "silver",
        "exp",
        "practice",
        "train",
        "saving_throw",
        "alignment",
        "hitroll",
        "damroll",
        "wimpy",
        "points",
        "true_sex",
        "last_level",
        "position",
        "room_vnum",
        "conditions",
        "armor",
        "perm_stat",
        "mod_stat",
        "inventory",
        "equipment",
        "plr_flags",
        "affected_by",
        "comm_flags",
        "wiznet",
    ]
    assert keys == expected


def test_condition_roundtrip(tmp_path):
    old_dir = persistence.PLAYERS_DIR
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    try:
        initialize_world("area/area.lst")
        char = create_test_character("Conditioned", 3001)
        char.pcdata.condition = [3, 40, 22, 17]
        persistence.save_character(char)
        character_registry.clear()
        loaded = persistence.load_character("Conditioned")
        assert loaded is not None
        assert loaded.pcdata.condition == [3, 40, 22, 17]
    finally:
        persistence.PLAYERS_DIR = old_dir
        character_registry.clear()


def test_identity_fields_roundtrip(tmp_path):
    old_dir = persistence.PLAYERS_DIR
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        char = create_test_character("Identity", 3001)
        char.race = 2
        char.ch_class = 3
        char.sex = 1
        char.trust = 52
        char.pcdata.security = 9
        persistence.save_character(char)
        character_registry.clear()
        loaded = persistence.load_character("Identity")
        assert loaded is not None
        assert loaded.race == 2
        assert loaded.ch_class == 3
        assert loaded.sex == 1
        assert loaded.trust == 52
        assert loaded.pcdata.security == 9
    finally:
        persistence.PLAYERS_DIR = old_dir
        character_registry.clear()


def test_hmvp_creation_stats_roundtrip(tmp_path):
    old_dir = persistence.PLAYERS_DIR
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        char = create_test_character("HMVP", 3001)
        char.pcdata.perm_hit = 120
        char.pcdata.perm_mana = 90
        char.pcdata.perm_move = 80
        char.pcdata.points = 35
        char.pcdata.true_sex = 2
        char.pcdata.last_level = 12
        persistence.save_character(char)
        character_registry.clear()
        loaded = persistence.load_character("HMVP")
        assert loaded is not None
        assert loaded.pcdata.perm_hit == 120
        assert loaded.pcdata.perm_mana == 90
        assert loaded.pcdata.perm_move == 80
        assert loaded.pcdata.points == 35
        assert loaded.pcdata.true_sex == 2
        assert loaded.pcdata.last_level == 12
    finally:
        persistence.PLAYERS_DIR = old_dir
        character_registry.clear()


def test_combat_stats_roundtrip(tmp_path):
    old_dir = persistence.PLAYERS_DIR
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        char = create_test_character("Combatant", 3001)
        char.practice = 4
        char.train = 2
        char.saving_throw = -5
        char.alignment = -350
        char.hitroll = 7
        char.damroll = 5
        char.wimpy = 18
        char.perm_stat = [18, 16, 14, 13, 12]
        char.mod_stat = [1, -1, 0, 2, -2]
        char.armor = [42, 33, 21, 15]
        persistence.save_character(char)
        character_registry.clear()
        loaded = persistence.load_character("Combatant")
        assert loaded is not None
        assert loaded.practice == 4
        assert loaded.train == 2
        assert loaded.saving_throw == -5
        assert loaded.alignment == -350
        assert loaded.hitroll == 7
        assert loaded.damroll == 5
        assert loaded.wimpy == 18
        assert loaded.perm_stat == [18, 16, 14, 13, 12]
        assert loaded.mod_stat == [1, -1, 0, 2, -2]
        assert loaded.armor == [42, 33, 21, 15]
    finally:
        persistence.PLAYERS_DIR = old_dir
        character_registry.clear()


def test_act_and_comm_flags_roundtrip(tmp_path):
    from mud.models.constants import PlayerFlag

    old_dir = persistence.PLAYERS_DIR
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        char = create_test_character("Flagged", 3001)
        act_flags = (1 << 2) | (1 << 9)
        comm_flags = (1 << 1) | (1 << 7)
        affect_flags = 1 << 5
        wiznet_flags = 1 << 3
        char.act = act_flags
        char.comm = comm_flags
        char.affected_by = affect_flags
        char.wiznet = wiznet_flags
        char.ansi_enabled = False
        persistence.save_character(char)
        character_registry.clear()
        loaded = persistence.load_character("Flagged")
        assert loaded is not None
        assert (loaded.act & act_flags) == act_flags
        assert loaded.comm == comm_flags
        assert loaded.affected_by == affect_flags
        assert loaded.wiznet == wiznet_flags
    finally:
        persistence.PLAYERS_DIR = old_dir
        character_registry.clear()
