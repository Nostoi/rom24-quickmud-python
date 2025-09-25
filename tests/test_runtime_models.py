from mud.models import (
    Board,
    BoardJson,
    HelpEntry,
    HelpJson,
    NoteJson,
    Sex,
    Shop,
    ShopJson,
    Skill,
    SkillJson,
    Social,
    SocialJson,
)
from mud.models.social import expand_placeholders


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


def test_register_social():
    data = SocialJson(name="wave", char_no_arg="You wave.")
    social = Social.from_json(data)
    from mud.models.social import register_social, social_registry

    register_social(social)
    assert social_registry["wave"] is social


def test_expand_placeholders_mself_male():
    actor = type("Dummy", (), {"name": "Bob", "sex": Sex.MALE})()
    out = expand_placeholders("$n laughs at $mself.", actor)
    assert out == "Bob laughs at himself."


def test_expand_placeholders_mself_female():
    actor = type("Dummy", (), {"name": "Alice", "sex": Sex.FEMALE})()
    out = expand_placeholders("$n laughs at $mself.", actor)
    assert out == "Alice laughs at herself."


def test_expand_placeholders_mself_neutral():
    actor = type("Dummy", (), {"name": "Blob", "sex": Sex.NONE})()
    out = expand_placeholders("$n pokes $mself.", actor)
    assert out == "Blob pokes itself."


def test_expand_placeholders_mself_default():
    actor = type("Dummy", (), {"name": "Sam"})()
    out = expand_placeholders("$n thinks about $mself.", actor)
    assert out == "Sam thinks about themselves."


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
