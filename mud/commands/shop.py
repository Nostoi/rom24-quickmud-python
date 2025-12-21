"""Shop command handlers."""

from mud.math.c_compat import c_div
from mud.characters.follow import add_follower
from mud.models.character import Character, character_registry
from mud.models.constants import (
    ActFlag,
    AffectFlag,
    CommFlag,
    ItemType,
    LEVEL_IMMORTAL,
    RoomFlag,
    ITEM_GLOW,
    ITEM_HAD_TIMER,
    ITEM_INVENTORY,
    ITEM_INVIS,
    ITEM_NODROP,
    ITEM_SELL_EXTRACT,
    ITEM_VIS_DEATH,
)
from mud.models.object import Object
from mud.registry import room_registry, shop_registry
from mud.skills import check_improve
from mud.spawning.obj_spawner import spawn_object
from mud.time import time_info
from mud.utils import rng_mm
from mud.world.movement import can_carry_n, can_carry_w, get_carry_weight
from mud.world.vision import room_is_dark

_CLOSED_EARLY = "Sorry, I am closed. Come back later."
_CLOSED_LATE = "Sorry, I am closed. Come back tomorrow."
_CANT_SEE = "I don't trade with folks I can't see."
_NO_WEALTH = "I'm afraid I don't have enough wealth to buy that."


def _split_first_argument(raw: str) -> tuple[str, str]:
    text = (raw or "").strip()
    if not text:
        return "", ""
    parts = text.split(maxsplit=1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def _has_act_flag(entity, flag: ActFlag) -> bool:
    checker = getattr(entity, "has_act_flag", None)
    if callable(checker):
        try:
            return bool(checker(flag))
        except TypeError:  # pragma: no cover - defensive fallback
            pass
    try:
        act_bits = int(getattr(entity, "act", 0) or 0)
    except (TypeError, ValueError):
        act_bits = 0
    if act_bits and act_bits & int(flag):
        return True
    proto = getattr(entity, "prototype", None)
    if proto is not None:
        proto_checker = getattr(proto, "has_act_flag", None)
        if callable(proto_checker):
            return bool(proto_checker(flag))
        try:
            proto_bits = int(getattr(proto, "act", 0) or 0)
        except (TypeError, ValueError):
            proto_bits = 0
        return bool(proto_bits & int(flag))
    return False


def _matches_pet_keyword(keyword: str, entity) -> bool:
    term = keyword.strip().lower()
    if not term:
        return False
    candidates: list[str] = []
    name = getattr(entity, "name", None)
    if isinstance(name, str):
        candidates.append(name.lower())
    proto = getattr(entity, "prototype", None)
    if proto is not None:
        player_name = getattr(proto, "player_name", None)
        if isinstance(player_name, str):
            candidates.append(player_name.lower())
        short_descr = getattr(proto, "short_descr", None)
        if isinstance(short_descr, str):
            candidates.append(short_descr.lower())
    for candidate in candidates:
        words = [chunk for chunk in candidate.split() if chunk]
        if term in words:
            return True
    return False


def _find_pet_template(room, keyword: str):
    for occupant in getattr(room, "people", []) or []:
        if not _has_act_flag(occupant, ActFlag.PET):
            continue
        if _matches_pet_keyword(keyword, occupant):
            return occupant
    return None


def _clone_pet_character(template) -> Character | None:
    proto = getattr(template, "prototype", None)
    if proto is None:
        return None

    pet = Character()
    base_name = getattr(proto, "player_name", None) or getattr(template, "name", None)
    pet.name = base_name or "pet"
    pet.short_descr = getattr(proto, "short_descr", None) or getattr(template, "name", None)
    pet.long_descr = getattr(proto, "long_descr", None)
    pet.description = getattr(proto, "description", None)

    def _coerce(value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    pet.level = _coerce(getattr(template, "level", getattr(proto, "level", 0)))
    current_hp = _coerce(getattr(template, "current_hp", 0))
    max_hit = _coerce(getattr(template, "max_hit", 0))
    if max_hit <= 0:
        max_hit = max(current_hp, 1)
    pet.max_hit = max_hit
    pet.hit = current_hp if current_hp > 0 else max_hit
    pet.max_mana = _coerce(getattr(template, "max_mana", 0))
    pet.mana = pet.max_mana
    pet.max_move = _coerce(getattr(template, "max_move", 0)) or 100
    pet.move = pet.max_move
    pet.gold = _coerce(getattr(template, "gold", 0))
    pet.silver = _coerce(getattr(template, "silver", 0))
    pet.alignment = _coerce(getattr(template, "alignment", 0))
    pet.damroll = _coerce(getattr(template, "damroll", 0))
    pet.hitroll = _coerce(getattr(template, "hitroll", 0))
    pet.dam_type = _coerce(getattr(template, "dam_type", 0))
    pet.perm_stat = [_coerce(value) for value in list(getattr(template, "perm_stat", []) or [])]
    pet.mod_stat = [0] * len(pet.perm_stat)
    pet.size = _coerce(getattr(template, "size", 0))
    pet.material = getattr(template, "material", None)
    pet.off_flags = _coerce(getattr(template, "off_flags", 0))
    pet.imm_flags = _coerce(getattr(template, "imm_flags", 0))
    pet.res_flags = _coerce(getattr(template, "res_flags", 0))
    pet.vuln_flags = _coerce(getattr(template, "vuln_flags", 0))
    pet.start_pos = _coerce(getattr(template, "start_pos", getattr(template, "position", 0)))
    pet.default_pos = _coerce(getattr(template, "default_pos", getattr(template, "position", 0)))
    pet.position = _coerce(getattr(template, "position", pet.default_pos))
    pet.carry_number = _coerce(getattr(template, "carry_number", 0))
    pet.carry_weight = _coerce(getattr(template, "carry_weight", 0))
    pet.armor = [_coerce(value) for value in list(getattr(template, "armor", (0, 0, 0, 0)))]
    pet.damage = [_coerce(value) for value in list(getattr(template, "damage", (0, 0, 0)))]
    pet.act = _coerce(getattr(template, "act", int(ActFlag.IS_NPC))) | int(ActFlag.IS_NPC)
    pet.affected_by = _coerce(getattr(template, "affected_by", 0))
    pet.mob_programs = list(getattr(template, "mob_programs", []) or [])
    pet.mprog_flags = _coerce(getattr(template, "mprog_flags", 0))
    pet.mprog_target = None
    pet.mprog_delay = 0
    pet.race = getattr(proto, "race", getattr(template, "race", 0))
    pet.prototype = proto
    return pet


def _format_coin_message(coins: int) -> str:
    gold = coins // 100
    silver = coins % 100
    if gold and silver:
        return f"{gold} gold and {silver} silver"
    if gold:
        return f"{gold} gold"
    return f"{silver} silver"


def _has_affect(entity, flag: AffectFlag) -> bool:
    checker = getattr(entity, "has_affect", None)
    if callable(checker):
        return checker(flag)
    affected_by = getattr(entity, "affected_by", 0)
    return bool(affected_by & int(flag))


def _keeper_can_see_customer(keeper: Character, customer: Character) -> bool:
    if _has_affect(keeper, AffectFlag.BLIND):
        return False
    if _has_affect(customer, AffectFlag.INVISIBLE) and not _has_affect(keeper, AffectFlag.DETECT_INVIS):
        return False
    if _has_affect(customer, AffectFlag.HIDE) and not _has_affect(keeper, AffectFlag.DETECT_HIDDEN):
        return False
    return True


def _can_drop_object(char: Character, obj: Object) -> bool:
    flags = int(getattr(obj, "extra_flags", 0) or 0)
    if not (flags & int(ITEM_NODROP)):
        return True
    if getattr(char, "is_npc", False):
        return False
    immortal_checker = getattr(char, "is_immortal", None)
    if callable(immortal_checker):
        try:
            if immortal_checker():
                return True
        except Exception:  # pragma: no cover - defensive fallback
            pass
    trust = int(getattr(char, "trust", 0) or 0)
    level = int(getattr(char, "level", 0) or 0)
    effective = trust if trust > 0 else level
    return effective >= LEVEL_IMMORTAL


def _keeper_can_see_object(keeper: Character, obj: Object) -> bool:
    if keeper is None or obj is None:
        return False

    flags = int(getattr(obj, "extra_flags", 0) or 0)
    if flags & int(ITEM_VIS_DEATH):
        return False

    if _has_affect(keeper, AffectFlag.BLIND):
        try:
            item_type = int(getattr(obj, "item_type", 0) or 0)
        except (TypeError, ValueError):
            item_type = 0
        if item_type != int(ItemType.POTION):
            return False

    try:
        item_type = int(getattr(obj, "item_type", 0) or 0)
    except (TypeError, ValueError):  # pragma: no cover - malformed data guard
        item_type = 0

    if item_type == int(ItemType.LIGHT):
        try:
            values = list(getattr(obj, "value", []) or [])
            if len(values) > 2:
                light_timer = int(values[2])
            else:
                light_timer = 0
        except (TypeError, ValueError):
            light_timer = 0
        if light_timer != 0:
            return True

    if flags & int(ITEM_INVIS) and not _has_affect(keeper, AffectFlag.DETECT_INVIS):
        return False

    if flags & int(ITEM_GLOW):
        return True

    room = getattr(keeper, "room", None)
    if room is not None and room_is_dark(room) and not _has_affect(keeper, AffectFlag.DARK_VISION):
        return False

    return True


def _find_shopkeeper(char: Character):
    for mob in getattr(char.room, "people", []):
        proto = getattr(mob, "prototype", None)
        if not proto:
            continue
        if proto.vnum not in shop_registry:
            continue
        shop = shop_registry.get(proto.vnum)
        if not shop:
            continue
        current_hour = time_info.hour
        if current_hour < shop.open_hour:
            return None, _CLOSED_EARLY
        if current_hour > shop.close_hour:
            return None, _CLOSED_LATE
        if not _keeper_can_see_customer(mob, char):
            return None, _CANT_SEE
        return mob, None
    return None, None


def _object_has_flag(value: int | ItemType | AffectFlag | None, flag: int) -> bool:
    try:
        return bool(int(value) & flag)
    except (TypeError, ValueError):
        return False


def _is_inventory_item(obj: Object) -> bool:
    if _object_has_flag(getattr(obj, "extra_flags", 0), int(ITEM_INVENTORY)):
        return True
    proto = getattr(obj, "prototype", None)
    if proto is None:
        return False
    return _object_has_flag(getattr(proto, "extra_flags", 0), int(ITEM_INVENTORY))


def _clone_inventory_object(template: Object) -> Object | None:
    proto = getattr(template, "prototype", None)
    if proto is None:
        return None

    clone = spawn_object(getattr(proto, "vnum", 0))
    if clone is None:
        clone = Object(instance_id=None, prototype=proto)

    # Mirror runtime overrides from the template copy so shop customisations persist.
    clone.value = list(getattr(template, "value", clone.value))
    clone.level = int(getattr(template, "level", clone.level) or 0)
    clone.cost = int(getattr(template, "cost", clone.cost) or 0)
    clone.extra_flags = int(getattr(template, "extra_flags", clone.extra_flags) or 0)
    clone.wear_flags = int(getattr(template, "wear_flags", clone.wear_flags) or 0)
    clone.condition = getattr(template, "condition", clone.condition)
    clone.item_type = getattr(template, "item_type", clone.item_type)
    clone.timer = int(getattr(template, "timer", clone.timer) or 0)
    clone.affected = list(getattr(template, "affected", []) or [])
    clone._short_descr_override = getattr(template, "_short_descr_override", None)
    clone._description_override = getattr(template, "_description_override", None)
    return clone


def _parse_purchase_quantity(raw: str) -> tuple[int, str]:
    """Return (quantity, remainder) mirroring ROM ``mult_argument`` semantics."""

    text = (raw or "").strip()
    if not text:
        return 1, ""
    if "*" not in text:
        return 1, text
    count_text, remainder = text.split("*", 1)
    try:
        quantity = int(count_text.strip() or "0")
    except ValueError:
        return 1, text
    return quantity, remainder.strip()


def _parse_numbered_keyword(raw: str) -> tuple[int, str]:
    """Return (index, remainder) mirroring ROM ``number_argument`` semantics."""

    text = (raw or "").strip()
    if not text:
        return 1, ""
    if "." not in text:
        return 1, text
    prefix, remainder = text.split(".", 1)
    try:
        index = int(prefix.strip() or "0")
    except ValueError:
        index = 0
    return index, remainder.strip()


def _purchase_matches(term: str, obj: Object) -> bool:
    """Check whether ``term`` matches ``obj`` keywords similar to ROM ``is_name``."""

    if not term:
        return False
    search_words = [chunk.lower() for chunk in term.split() if chunk]
    if not search_words:
        return False

    candidates: list[str] = []
    for attr in (getattr(obj, "name", None), getattr(obj, "short_descr", None)):
        if isinstance(attr, str):
            candidates.append(attr.lower())
    proto = getattr(obj, "prototype", None)
    if proto is not None:
        for attr in (getattr(proto, "name", None), getattr(proto, "short_descr", None)):
            if isinstance(attr, str):
                candidates.append(attr.lower())

    for candidate in candidates:
        if not candidate:
            continue
        candidate_words = [chunk for chunk in candidate.split() if chunk]
        if not candidate_words:
            continue
        if all(any(name_word.startswith(word) for name_word in candidate_words) for word in search_words):
            return True
    return False


def _collect_matching_stock(
    inventory: list[Object], template: Object, count: int, *, start_index: int = 0
) -> list[Object]:
    """Collect up to ``count`` objects matching ``template`` signature."""

    collected: list[Object] = []
    proto = getattr(template, "prototype", None)
    signature_name = (template.short_descr or template.name or "").strip().lower()
    for idx, candidate in enumerate(inventory):
        if idx < start_index:
            continue
        candidate_proto = getattr(candidate, "prototype", None)
        candidate_name = (candidate.short_descr or candidate.name or "").strip().lower()
        if candidate_proto is proto and candidate_name == signature_name:
            collected.append(candidate)
            if len(collected) >= count:
                break
    return collected


def _get_shop(keeper):
    proto = getattr(keeper, "prototype", None)
    if proto:
        return shop_registry.get(proto.vnum)
    return None


def _keeper_total_wealth(keeper) -> int:
    gold = getattr(keeper, "gold", 0)
    silver = getattr(keeper, "silver", 0)
    return gold * 100 + silver


def _set_keeper_total_wealth(keeper, total: int) -> None:
    total = max(total, 0)
    keeper.gold = total // 100
    keeper.silver = total % 100


def _character_total_wealth(char: Character) -> int:
    gold = getattr(char, "gold", 0)
    silver = getattr(char, "silver", 0)
    return int(gold) * 100 + int(silver)


def _set_character_total_wealth(char: Character, total: int) -> None:
    total = max(int(total), 0)
    char.gold = total // 100
    char.silver = total % 100


def _deduct_character_cost(char: Character, cost: int) -> None:
    """Remove silver-denominated ``cost`` mirroring ROM ``deduct_cost``."""

    cost = max(int(cost), 0)
    current_silver = int(getattr(char, "silver", 0) or 0)
    current_gold = int(getattr(char, "gold", 0) or 0)

    silver = current_silver if current_silver < cost else cost
    gold = 0
    if silver < cost:
        gold = (cost - silver + 99) // 100
        silver = cost - 100 * gold

    char.gold = current_gold - gold
    char.silver = current_silver - silver

    if char.gold < 0:
        char.gold = 0
    if char.silver < 0:
        char.silver = 0


def _get_cost(keeper, obj: Object, *, buy: bool) -> int:
    """Compute ROM-like shop price for an object.

    Mirrors src/act_obj.c:get_cost:
    - buy: base = obj.cost * profit_buy / 100
    - sell: base = obj.cost * profit_sell / 100 if type accepted; otherwise 0
    - inventory discount on sell when keeper already has same item:
        - if existing copy has ITEM_INVENTORY → base /= 2
        - else → base = base * 3 / 4
    - wand/staff charge scaling: value[1]==0 → base/=4; else base = base * value[2] / value[1]
    """
    proto = obj.prototype
    shop = _get_shop(keeper)
    if not shop:
        return 0
    cost = 0
    if buy:
        cost = c_div(getattr(proto, "cost", 0) * shop.profit_buy, 100)
    else:
        # ensure shop buys this type
        item_type = getattr(proto, "item_type", 0)
        if shop.buy_types and item_type not in shop.buy_types:
            return 0
        cost = c_div(getattr(proto, "cost", 0) * shop.profit_sell, 100)
        # inventory discount if keeper already has same item
        for other in getattr(keeper, "inventory", []) or []:
            op = getattr(other, "prototype", None)
            if not op:
                continue
            if op is proto or (
                getattr(op, "vnum", None) == getattr(proto, "vnum", None)
                and (getattr(op, "short_descr", None) or "") == (getattr(proto, "short_descr", None) or "")
            ):
                # treat bit 1<<18 as ITEM_INVENTORY in this port
                ITEM_INVENTORY = 1 << 18
                if getattr(op, "extra_flags", 0) & ITEM_INVENTORY:
                    cost = c_div(cost, 2)
                else:
                    cost = c_div(cost * 3, 4)
                break

    # Charge scaling for wand/staff
    if getattr(proto, "item_type", 0) in (int(ItemType.WAND), int(ItemType.STAFF)):
        vals = getattr(proto, "value", [0, 0, 0, 0, 0])
        total = vals[1]
        rem = vals[2]
        if total == 0:
            cost = c_div(cost, 4)
        elif total > 0:
            cost = c_div(cost * rem, total)
    return max(0, int(cost))


def _handle_pet_shop_purchase(char: Character, args: str) -> str:
    if getattr(char, "is_npc", False):
        return "You can't do that here."

    keyword, rename = _split_first_argument(args)
    if not keyword:
        return "Buy what?"

    room = getattr(char, "room", None)
    if room is None:
        return "You can't do that here."

    room_vnum = getattr(room, "vnum", None)
    if room_vnum is None:
        return "Sorry, you can't buy that here."
    kennel_vnum = 9706 if room_vnum == 9621 else room_vnum + 1
    kennel = room_registry.get(kennel_vnum)
    if kennel is None:
        return "Sorry, you can't buy that here."

    template = _find_pet_template(kennel, keyword)
    if template is None:
        return "Sorry, you can't buy that here."

    if char.pet is not None:
        return "You already own a pet."

    level = getattr(template, "level", getattr(getattr(template, "prototype", None), "level", 0)) or 0
    try:
        pet_level = int(level)
    except (TypeError, ValueError):
        pet_level = 0

    if int(getattr(char, "level", 0) or 0) < pet_level:
        return "You're not powerful enough to master this pet."

    cost = 10 * pet_level * pet_level
    if cost <= 0:
        cost = 10

    total_wealth = _character_total_wealth(char)
    if total_wealth < cost:
        return "You can't afford it."

    skills = getattr(char, "skills", {}) or {}
    try:
        haggle_skill = int(skills.get("haggle", 0) or 0)
    except (TypeError, ValueError):
        haggle_skill = 0

    if haggle_skill > 0:
        roll = rng_mm.number_percent()
        if roll < haggle_skill:
            discount = (cost // 2) * roll // 100
            cost = max(0, cost - discount)
            char.messages.append(f"You haggle the price down to {cost} coins.")
            check_improve(char, "haggle", True, 4)

    if total_wealth < cost:
        return "You can't afford it."

    pet = _clone_pet_character(template)
    if pet is None:
        return "Sorry, you can't buy that here."

    pet.act |= int(ActFlag.PET)
    pet.group = getattr(template, "group", 0)
    pet.add_affect(AffectFlag.CHARM)
    pet.set_comm_flag(CommFlag.NOTELL)
    pet.set_comm_flag(CommFlag.NOSHOUT)
    pet.set_comm_flag(CommFlag.NOCHANNELS)

    rename_token = (rename or "").strip()
    if rename_token:
        base = (pet.name or "").strip()
        pet.name = f"{base} {rename_token}".strip()

    owner_name = char.name or char.short_descr or "someone"
    base_description = pet.description or ""
    if base_description and not base_description.endswith("\n"):
        base_description = f"{base_description}\n"
    pet.description = f"{base_description}A neck tag says 'I belong to {owner_name}'.\n"

    _deduct_character_cost(char, cost)

    character_registry.append(pet)
    current_room = room
    current_room.add_character(pet)

    add_follower(pet, char)
    pet.leader = char
    char.pet = pet

    buyer_message = "Enjoy your pet."
    if hasattr(char, "messages"):
        char.messages.append(buyer_message)

    actor_name = char.short_descr or char.name or "Someone"
    target_name = pet.short_descr or pet.name or "a pet"
    current_room.broadcast(f"{actor_name} bought {target_name} as a pet.", exclude=char)

    return buyer_message


def do_list(char: Character, args: str = "") -> str:
    keeper, denial = _find_shopkeeper(char)
    if not keeper:
        return denial or "You can't do that here."
    shop = _get_shop(keeper)
    if not shop:
        return "You can't do that here."
    inventory = getattr(keeper, "inventory", []) or []
    filter_term = args.strip().lower()

    def _matches_name(term: str, name: str | None) -> bool:
        if not term:
            return True
        words = [chunk for chunk in term.split() if chunk]
        if not words:
            return True
        name_words = (name or "").lower().split()
        if not name_words:
            return False
        for word in words:
            if not any(candidate.startswith(word) for candidate in name_words):
                return False
        return True

    entries: list[tuple[int, int, str, bool, int]] = []
    seen: dict[tuple[int | None, str], int] = {}
    for obj in inventory:
        proto = getattr(obj, "prototype", None)
        if proto is None:
            continue
        cost = _get_cost(keeper, obj, buy=True)
        if cost <= 0:
            continue
        short_descr = obj.short_descr or obj.name or "item"
        if filter_term and not (_matches_name(filter_term, obj.name) or _matches_name(filter_term, short_descr)):
            continue
        signature = (getattr(proto, "vnum", None), short_descr.lower())
        flags = (getattr(obj, "extra_flags", 0) or 0) | (getattr(proto, "extra_flags", 0) or 0)
        infinite = bool(flags & int(ITEM_INVENTORY))
        if signature in seen:
            index = seen[signature]
            if not entries[index][3]:  # only increment finite stacks
                level, price, name, infinite_flag, count = entries[index]
                entries[index] = (level, price, name, infinite_flag, count + 1)
            continue
        level = getattr(proto, "level", getattr(obj, "level", 0))
        index = len(entries)
        entries.append((int(level), cost, short_descr, infinite, 1))
        seen[signature] = index

    if not entries:
        return "You can't buy anything here."

    lines = ["[Lv Price Qty] Item"]
    for level, price, name, infinite, count in entries:
        quantity = "--" if infinite else f"{count:2d}"
        lines.append(f"[{level:2d} {price:5d} {quantity} ] {name}")
    return "\n".join(lines)


def do_buy(char: Character, args: str) -> str:
    if not args:
        return "Buy what?"
    room = getattr(char, "room", None)
    if room is not None and getattr(room, "room_flags", 0) & int(RoomFlag.ROOM_PET_SHOP):
        return _handle_pet_shop_purchase(char, args)
    keeper, denial = _find_shopkeeper(char)
    if not keeper:
        return denial or "You can't do that here."
    shop = _get_shop(keeper)
    if not shop:
        return "You can't do that here."
    quantity, remainder = _parse_purchase_quantity(args)
    if quantity < 1 or quantity > 99:
        return "You can't buy that many."
    target_index, raw_name = _parse_numbered_keyword(remainder)
    name = raw_name.lower()
    if not name:
        return "Buy what?"

    inventory = list(getattr(keeper, "inventory", []) or [])
    effective_index = target_index if target_index > 0 else None
    match_count = 0
    selected_obj: Object | None = None
    selected_position = 0
    for idx, candidate in enumerate(inventory):
        if not _purchase_matches(name, candidate):
            continue
        match_count += 1
        if effective_index is None or match_count < effective_index:
            continue
        selected_obj = candidate
        selected_position = idx
        break

    if selected_obj is None:
        return "The shopkeeper doesn't sell that."

    proto = getattr(selected_obj, "prototype", None)

    unit_price = _get_cost(keeper, selected_obj, buy=True)
    if unit_price <= 0:
        # Allow prototype-less inventory templates to be purchased for free.
        if proto is None and _is_inventory_item(selected_obj):
            unit_price = 0
        else:
            return "The shopkeeper doesn't sell that."

    infinite_stock = _is_inventory_item(selected_obj) and proto is not None
    matching_stock: list[Object] = []
    if not infinite_stock:
        matching_stock = _collect_matching_stock(
            inventory,
            selected_obj,
            quantity,
            start_index=selected_position,
        )
        if len(matching_stock) < quantity:
            return "The shopkeeper doesn't have that many in stock."

    item_level = getattr(proto, "level", getattr(selected_obj, "level", 0))
    char_level = getattr(char, "level", 0)
    if int(char_level) < int(item_level or 0):
        return "You can't use that yet."

    current_number = int(getattr(char, "carry_number", 0) or 0)
    if current_number + quantity > can_carry_n(char):
        return "You can't carry that many items."

    current_weight = get_carry_weight(char)
    if infinite_stock:
        weight_per = int(getattr(selected_obj, "weight", None) or getattr(proto, "weight", 0) or 0)
        total_weight = weight_per * quantity
    else:
        total_weight = 0
        for item in matching_stock[:quantity]:
            item_proto = getattr(item, "prototype", None)
            total_weight += int(getattr(item, "weight", None) or getattr(item_proto, "weight", 0) or 0)
    if current_weight + total_weight > can_carry_w(char):
        return "You can't carry that much weight."

    total_cost = unit_price * quantity
    if _character_total_wealth(char) < total_cost:
        return "You can't afford that."

    _deduct_character_cost(char, total_cost)
    _set_keeper_total_wealth(keeper, _keeper_total_wealth(keeper) + total_cost)

    purchased_items: list[Object] = []
    if infinite_stock:
        for _ in range(quantity):
            clone = _clone_inventory_object(selected_obj)
            if clone is None:
                return "The shopkeeper doesn't have that many in stock."
            purchased_items.append(clone)
    else:
        for item in matching_stock[:quantity]:
            for idx, existing in enumerate(keeper.inventory):
                if existing is item:
                    del keeper.inventory[idx]
                    break
            purchased_items.append(item)

    for purchased in purchased_items:
        flags = int(getattr(purchased, "extra_flags", 0) or 0)
        if getattr(purchased, "timer", 0) > 0 and not (flags & int(ITEM_HAD_TIMER)):
            purchased.timer = 0
        purchased.extra_flags = flags & ~int(ITEM_HAD_TIMER)
        if unit_price < int(getattr(purchased, "cost", unit_price) or 0):
            purchased.cost = unit_price
        char.add_object(purchased)

    primary = purchased_items[0]
    descriptor = primary.short_descr or primary.name or "item"
    if quantity > 1:
        return f"You buy {descriptor}[{quantity}] for {total_cost} silver."
    return f"You buy {descriptor} for {total_cost} silver."


def do_sell(char: Character, args: str) -> str:
    if not args:
        return "Sell what?"
    keeper, denial = _find_shopkeeper(char)
    if not keeper:
        return denial or "You can't do that here."
    shop = _get_shop(keeper)
    if not shop:
        return "You can't do that here."

    raw_term = (args or "").strip()
    if not raw_term:
        return "Sell what?"
    target_index, keyword = _parse_numbered_keyword(raw_term)
    search_term = (keyword or raw_term).strip().lower()
    if not search_term:
        return "Sell what?"
    effective_index = target_index if target_index > 0 else 1

    match_count = 0
    selected_obj: Object | None = None
    for candidate in list(getattr(char, "inventory", []) or []):
        if not _purchase_matches(search_term, candidate):
            continue
        match_count += 1
        if match_count == effective_index:
            selected_obj = candidate
            break

    if selected_obj is None:
        if hasattr(char, "reply"):
            char.reply = keeper
        return "You don't have that."

    if not _can_drop_object(char, selected_obj):
        return "You can't let go of it."

    if not _keeper_can_see_object(keeper, selected_obj):
        return "The shopkeeper doesn't see what you are offering."

    price = _get_cost(keeper, selected_obj, buy=False)
    if price <= 0:
        return "The shopkeeper doesn't buy that."
    total_wealth = _keeper_total_wealth(keeper)
    if price > total_wealth:
        return _NO_WEALTH

    flags = int(getattr(selected_obj, "extra_flags", 0) or 0)
    skills = getattr(char, "skills", {}) or {}
    try:
        haggle_skill = int(skills.get("haggle", 0) or 0)
    except (TypeError, ValueError):
        haggle_skill = 0
    if haggle_skill > 0 and not (flags & int(ITEM_SELL_EXTRACT)):
        roll = rng_mm.number_percent()
        if roll < haggle_skill:
            proto = getattr(selected_obj, "prototype", None)
            base_cost = int(getattr(proto, "cost", getattr(selected_obj, "cost", 0)) or 0)
            bonus = (base_cost // 2) * roll // 100
            price += bonus
            buy_price = _get_cost(keeper, selected_obj, buy=True)
            if buy_price > 0:
                price = min(price, (95 * buy_price) // 100)
            price = min(price, total_wealth)
            if hasattr(char, "messages"):
                char.messages.append("You haggle with the shopkeeper.")
            check_improve(char, "haggle", True, 4)

    room = getattr(char, "room", None)
    if room is not None:
        seller_name = char.short_descr or char.name or "Someone"
        item_name = selected_obj.short_descr or selected_obj.name or "something"
        room.broadcast(f"{seller_name} sells {item_name}.", exclude=char)

    removed = False
    inventory_list = getattr(char, "inventory", None)
    if isinstance(inventory_list, list):
        for idx, candidate in enumerate(inventory_list):
            if candidate is selected_obj:
                del inventory_list[idx]
                removed = True
                break
        if removed:
            try:
                char.carry_number = max(int(getattr(char, "carry_number", 0)) - 1, 0)
            except (TypeError, ValueError):  # pragma: no cover - defensive fallback
                char.carry_number = 0
            recalc = getattr(char, "_recalculate_carry_weight", None)
            if callable(recalc):
                recalc()
    if not removed:
        remove_func = getattr(char, "remove_object", None)
        if callable(remove_func):
            remove_func(selected_obj)
            removed = True
        else:  # pragma: no cover - defensive fallback for legacy Character shapes
            if isinstance(inventory_list, list):
                try:
                    inventory_list.remove(selected_obj)
                    removed = True
                except ValueError:
                    removed = False
            else:
                removed = False
    if not removed:
        return "You don't have that."

    try:
        item_type = int(getattr(selected_obj, "item_type", 0) or 0)
    except (TypeError, ValueError):
        item_type = 0

    flags = int(getattr(selected_obj, "extra_flags", 0) or 0)
    extracted = item_type == int(ItemType.TRASH) or bool(flags & int(ITEM_SELL_EXTRACT))
    if extracted:
        if hasattr(selected_obj, "location"):
            selected_obj.location = None
    else:
        if getattr(selected_obj, "timer", 0):
            selected_obj.extra_flags = flags | int(ITEM_HAD_TIMER)
        else:
            selected_obj.timer = rng_mm.number_range(50, 100)
            selected_obj.extra_flags = flags & ~int(ITEM_HAD_TIMER)
        add_obj = getattr(keeper, "add_object", None)
        if callable(add_obj):
            add_obj(selected_obj)
        else:  # pragma: no cover - legacy fallback
            keeper.inventory.append(selected_obj)

    _set_character_total_wealth(char, _character_total_wealth(char) + price)
    _set_keeper_total_wealth(keeper, total_wealth - price)

    silver = price % 100
    gold = price // 100
    descriptor = selected_obj.short_descr or selected_obj.name or "item"

    if gold <= 0:
        return f"You sell {descriptor} for {silver} silver."

    suffix = "" if gold == 1 else "s"
    return f"You sell {descriptor} for {silver} silver and {gold} gold piece{suffix}."


def do_value(char: Character, args: str) -> str:
    if not args:
        return "Value what?"
    keeper, denial = _find_shopkeeper(char)
    if not keeper:
        return denial or "You can't do that here."

    raw_term = (args or "").strip()
    if not raw_term:
        return "Value what?"
    target_index, keyword = _parse_numbered_keyword(raw_term)
    search_term = (keyword or raw_term).strip().lower()
    if not search_term:
        return "Value what?"

    effective_index = target_index if target_index > 0 else 1
    match_count = 0
    selected_obj: Object | None = None
    for candidate in list(getattr(char, "inventory", []) or []):
        if not _purchase_matches(search_term, candidate):
            continue
        match_count += 1
        if match_count == effective_index:
            selected_obj = candidate
            break

    if selected_obj is None:
        if hasattr(char, "reply"):
            char.reply = keeper
        return "The shopkeeper tells you 'You don't have that item.'"

    if not _keeper_can_see_object(keeper, selected_obj):
        return "The shopkeeper doesn't see what you are offering."

    if not _can_drop_object(char, selected_obj):
        return "You can't let go of it."

    price = _get_cost(keeper, selected_obj, buy=False)
    if price <= 0:
        return "The shopkeeper looks uninterested in that."

    if hasattr(char, "reply"):
        char.reply = keeper

    descriptor = selected_obj.short_descr or selected_obj.name or "it"
    silver = price % 100
    gold = price // 100
    return f"The shopkeeper tells you 'I'll give you {silver} silver and {gold} gold coins for {descriptor}.'"
