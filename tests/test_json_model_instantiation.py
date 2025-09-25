from mud.models import (
    AreaJson,
    BoardJson,
    CharacterJson,
    HelpJson,
    NoteJson,
    ObjectJson,
    ResourceJson,
    RoomJson,
    ShopJson,
    SkillJson,
    SocialJson,
    StatsJson,
    VnumRangeJson,
)


def test_area_room_instantiation():
    area = AreaJson(name="Test Area", vnum_range=VnumRangeJson(min=1, max=100))
    room = RoomJson(
        id=100,
        name="Test Room",
        description="",
        sector_type="inside",
        area=1,
    )
    area.rooms.append(room)
    assert area.name == "Test Area"
    assert area.rooms[0].name == "Test Room"


def test_object_instantiation():
    obj = ObjectJson(
        id=200,
        name="Stick",
        description="",
        item_type="misc",
        values=[0, 0, 0, 0, 0],
        weight=0,
        cost=0,
    )
    assert obj.item_type == "misc"
    assert obj.values == [0, 0, 0, 0, 0]


def test_character_instantiation():
    stats = StatsJson(
        str=10,
        int=10,
        wis=10,
        dex=10,
        con=10,
        hitpoints=ResourceJson(100, 100),
        mana=ResourceJson(50, 50),
        move=ResourceJson(30, 30),
    )
    char = CharacterJson(
        id=1,
        name="Hero",
        description="",
        level=10,
        stats=stats,
        position="standing",
    )
    assert char.level == 10
    assert char.stats.hitpoints.max == 100


def test_shop_instantiation():
    shop = ShopJson(keeper=1234)
    assert shop.keeper == 1234
    assert shop.profit_buy == 100


def test_skill_instantiation():
    skill = SkillJson(
        name="fireball",
        type="spell",
        function="spell_fireball",
        mana_cost=50,
    )
    assert skill.name == "fireball"
    assert skill.mana_cost == 50
    assert skill.messages == {}


def test_help_instantiation():
    entry = HelpJson(keywords=["look"], text="Look around.")
    assert entry.keywords == ["look"]
    assert entry.level == 0


def test_social_instantiation():
    social = SocialJson(name="smile", char_no_arg="You smile.")
    assert social.name == "smile"
    assert social.char_no_arg == "You smile."


def test_note_instantiation():
    note = NoteJson(
        sender="Alice",
        to="All",
        subject="Hi",
        text="Hello",
        timestamp=1.0,
    )
    assert note.sender == "Alice"
    assert note.subject == "Hi"


def test_board_instantiation():
    board = BoardJson(name="general", description="General board")
    assert board.name == "general"
    assert board.notes == []
