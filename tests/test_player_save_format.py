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

