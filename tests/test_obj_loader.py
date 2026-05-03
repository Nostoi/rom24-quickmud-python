from mud.loaders.obj_loader import _resolve_item_type_code
from mud.models.constants import ItemType


def test_resolve_item_type_code_accepts_integer_tokens():
    assert _resolve_item_type_code(int(ItemType.WEAPON)) == int(ItemType.WEAPON)
    assert _resolve_item_type_code(int(ItemType.MAP)) == int(ItemType.MAP)

