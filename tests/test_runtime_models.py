from mud.models import (
    ShopJson,
    Shop,
    SkillJson,
    Skill,
    HelpJson,
    HelpEntry,
    SocialJson,
    Social,
    BoardJson,
    Board,
    NoteJson,
)


def test_shop_from_json():
    data = ShopJson(keeper=123, buy_types=["weapon"], profit_buy=110)
    shop = Shop.from_json(data)
    assert shop.keeper == 123
    assert shop.buy_types == ["weapon"]
    assert shop.profit_buy == 110


def test_skill_from_json():
    data = SkillJson(name="fireball", type="spell", function="do_fireball")
    skill = Skill.from_json(data)
    assert skill.name == "fireball"
    assert skill.function == "do_fireball"


def test_help_from_json():
    data = HelpJson(keywords=["foo"], text="bar", level=1)
    help_entry = HelpEntry.from_json(data)
    assert help_entry.keywords == ["foo"]
    assert help_entry.text == "bar"
    assert help_entry.level == 1


def test_social_from_json():
    data = SocialJson(name="smile", char_no_arg="You smile.")
    social = Social.from_json(data)
    assert social.name == "smile"
    assert social.char_no_arg == "You smile."


def test_board_from_json():
    data = BoardJson(
        name="general",
        description="General",
        notes=[
            NoteJson(
                sender="Alice",
                to="all",
                subject="Hi",
                text="Hello",
                timestamp=1.0,
            )
        ],
    )
    board = Board.from_json(data)
    assert board.name == "general"
    assert board.notes[0].subject == "Hi"
    round_trip = board.to_json()
    assert round_trip.notes[0].text == "Hello"
