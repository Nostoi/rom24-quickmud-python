from mud.scripts.convert_player_to_json import convert_player
from mud.models.player_json import PlayerJson


def _bit(ch: str) -> int:
    return 1 << (ord(ch) - ord('A'))


def test_convert_legacy_player_flags_roundtrip():
    pj = convert_player('player/Shemp')
    # Basic parsed fields
    assert pj.name == 'Shemp'
    assert pj.level == 2
    assert pj.room_vnum == 3714
    # Flags: Act QT => Q and T set
    assert pj.plr_flags & _bit('Q')
    assert pj.plr_flags & _bit('T')
    # Comm NOP => N,O,P set
    for ch in 'NOP':
        assert pj.comm_flags & _bit(ch)
    # Round-trip through dict preserves exact integers
    data = pj.to_dict()
    pj2 = PlayerJson.from_dict(data)
    assert pj2.plr_flags == pj.plr_flags
    assert pj2.comm_flags == pj.comm_flags


def test_missing_header_footer_and_bad_hmv(tmp_path):
    # Missing #PLAYER header
    bad1 = tmp_path / 'bad1'
    bad1.write_text('Name Bob~\n#END\n', encoding='latin-1')
    try:
        convert_player(str(bad1))
        assert False, 'expected ValueError for missing header'
    except ValueError as e:
        assert 'missing #PLAYER' in str(e)

    # Missing #END footer
    bad2 = tmp_path / 'bad2'
    bad2.write_text('#PLAYER\nName Bob~\n', encoding='latin-1')
    try:
        convert_player(str(bad2))
        assert False, 'expected ValueError for missing footer'
    except ValueError as e:
        assert 'missing #END' in str(e)

    # Bad HMV width (not 6 ints)
    bad3 = tmp_path / 'bad3'
    bad3.write_text('#PLAYER\nName Bob~\nLevl 1\nRoom 3001\nHMV 1 2 3\n#END\n', encoding='latin-1')
    try:
        convert_player(str(bad3))
        assert False, 'expected ValueError for HMV width'
    except ValueError as e:
        assert 'HMV' in str(e)

    # Bad Act letters
    bad4 = tmp_path / 'bad4'
    bad4.write_text('#PLAYER\nName Bob~\nLevl 1\nRoom 3001\nHMV 1 2 3 4 5 6\nAct Q1\n#END\n', encoding='latin-1')
    try:
        convert_player(str(bad4))
        assert False, 'expected ValueError for Act flags'
    except ValueError as e:
        assert 'Act flags' in str(e)


def test_invalid_level_and_room(tmp_path):
    bad = tmp_path / 'bad'
    bad.write_text('#PLAYER\nName Bob~\nLevl X\nRoom 3001\nHMV 1 2 3 4 5 6\n#END\n', encoding='latin-1')
    try:
        convert_player(str(bad))
        assert False
    except ValueError as e:
        assert 'invalid Levl' in str(e)

    bad2 = tmp_path / 'bad2'
    bad2.write_text('#PLAYER\nName Bob~\nLevl 1\nRoom ROOM\nHMV 1 2 3 4 5 6\n#END\n', encoding='latin-1')
    try:
        convert_player(str(bad2))
        assert False
    except ValueError as e:
        assert 'invalid Room' in str(e)


def test_multi_letter_flags(tmp_path):
    good = tmp_path / 'good'
    good.write_text('#PLAYER\nName Bob~\nLevl 1\nRoom 3001\nHMV 1 2 3 4 5 6\nAct ABC\nComm NOP\n#END\n', encoding='latin-1')
    pj = convert_player(str(good))
    def bit(ch):
        return 1 << (ord(ch) - ord('A'))
    assert pj.plr_flags == bit('A') | bit('B') | bit('C')
    assert pj.comm_flags == bit('N') | bit('O') | bit('P')


def test_player_json_field_order():
    pj = PlayerJson(
        name='X', level=1, hit=1, max_hit=1, mana=1, max_mana=1,
        move=1, max_move=1, gold=0, silver=0, exp=0, position=0,
        room_vnum=3001, inventory=[], equipment={}, plr_flags=0, comm_flags=0,
    )
    data = pj.to_dict()
    keys = list(data.keys())
    expected = [
        'name','level','hit','max_hit','mana','max_mana','move','max_move',
        'gold','silver','exp','position','room_vnum','inventory','equipment',
        'plr_flags','comm_flags'
    ]
    assert keys == expected
