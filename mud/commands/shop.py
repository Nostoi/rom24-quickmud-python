"""Shop command handlers."""

from mud.characters.follow import add_follower
from mud.handler import deduct_cost
from mud.math.c_compat import c_div, c_mod
from mud.models.character import Character
from mud.models.constants import (
    ITEM_GLOW,
    ITEM_HAD_TIMER,
    ITEM_INVENTORY,
    ITEM_INVIS,
    ITEM_NODROP,
    ITEM_SELL_EXTRACT,
    ITEM_VIS_DEATH,
    LEVEL_IMMORTAL,
    ActFlag,
    AffectFlag,
    CommFlag,
    ItemType,
    RoomFlag,
    WearLocation,
)
from mud.models.object import Object, create_object
from mud.registry import room_registry, shop_registry
from mud.skills import check_improve
from mud.spawning.mob_spawner import spawn_mob
from mud.spawning.obj_spawner import spawn_object
from mud.time import time_info
from mud.utils import rng_mm
from mud.utils.act import act_to_room, capitalize_act_line
from mud.utils.messaging import push_message
from mud.world.movement import can_carry_n, can_carry_w, get_carry_weight
from mud.world.vision import can_see_object, room_is_dark

_CLOSED_EARLY = "Sorry, I am closed. Come back later."
_CLOSED_LATE = "Sorry, I am closed. Come back tomorrow."
_CANT_SEE = "I don't trade with folks I can't see."


def _keeper_says(keeper, ch, message: str, *, obj=None) -> str:
    """Emit a keeper-spoken message and set ch.reply.

    ROM uses act() with TO_VICT — mirrors the $n expansion + first-char
    capitalization from src/comm.c:2376-2379.  The message arg is the literal
    suffix after "$n tells you '" (caller supplies ROM-exact punctuation,
    including whether the closing ' precedes or follows the period).
    """
    keeper_name = getattr(keeper, "short_descr", None) or getattr(keeper, "name", "The shopkeeper")
    if hasattr(ch, "reply"):
        ch.reply = keeper
    if obj is not None:
        obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", "it") or "it"
        message = message.replace("$p", obj_name)
    # mirroring ROM src/comm.c:2376-2379 — first char of act() output is capitalised
    return capitalize_act_line(f"{keeper_name} tells you '{message}")


def _act_to_char(keeper, message: str, *, obj=None) -> str:
    """Render a ROM act(message, keeper, obj, ch, TO_VICT) string.

    Expands $n to the keeper's short_descr and $p to the object's short_descr,
    then capitalises the first character (src/comm.c:2376-2379).
    """
    keeper_name = getattr(keeper, "short_descr", None) or getattr(keeper, "name", "The shopkeeper")
    result = message.replace("$n", keeper_name)
    if obj is not None:
        obj_name = getattr(obj, "short_descr", None) or getattr(obj, "name", "it") or "it"
        result = result.replace("$p", obj_name)
    return capitalize_act_line(result)


def _obj_to_keeper(obj: object, keeper) -> bool:
    """Mirror ROM src/act_obj.c:obj_to_keeper dedup logic.

    If keeper already carries an ITEM_INVENTORY-flagged object with the same
    prototype vnum, the sold object is destroyed (extracted) and True is
    returned to signal the caller NOT to add it to keeper inventory.
    Otherwise returns False (caller should add normally).
    """
    obj_proto = getattr(obj, "prototype", None)
    if obj_proto is None:
        return False
    obj_vnum = getattr(obj_proto, "vnum", None)
    obj_descr = (getattr(obj, "short_descr", None) or "").strip().lower()

    for existing in list(getattr(keeper, "inventory", []) or []):
        ex_proto = getattr(existing, "prototype", None)
        if ex_proto is None:
            continue
        if getattr(ex_proto, "vnum", None) != obj_vnum:
            continue
        ex_descr = (getattr(existing, "short_descr", None) or "").strip().lower()
        if ex_descr != obj_descr:
            continue
        # Matched — check ITEM_INVENTORY flag
        ex_flags = int(getattr(existing, "extra_flags", 0) or 0) | int(getattr(ex_proto, "extra_flags", 0) or 0)
        if ex_flags & int(ITEM_INVENTORY):
            # Destroy the sold object (extract_obj equivalent)
            if hasattr(obj, "location"):
                obj.location = None
            return True
        # Non-inventory duplicate: cost sync (keep it standard)
        existing_cost = int(getattr(existing, "cost", 0) or 0)
        if existing_cost:
            obj.cost = existing_cost
        break
    return False


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


def _format_coin_message(coins: int) -> str:
    gold = coins // 100
    silver = coins % 100
    if gold and silver:
        return f"{gold} gold and {silver} silver"
    if gold:
        return f"{gold} gold"
    return f"{silver} silver"


def _keeper_can_see_customer(keeper: Character, customer: Character) -> bool:
    if keeper.has_affect(AffectFlag.BLIND):
        return False
    if customer.has_affect(AffectFlag.INVISIBLE) and not keeper.has_affect(AffectFlag.DETECT_INVIS):
        return False
    if customer.has_affect(AffectFlag.HIDE) and not keeper.has_affect(AffectFlag.DETECT_HIDDEN):
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

    if keeper.has_affect(AffectFlag.BLIND):
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

    if flags & int(ITEM_INVIS) and not keeper.has_affect(AffectFlag.DETECT_INVIS):
        return False

    if flags & int(ITEM_GLOW):
        return True

    room = getattr(keeper, "room", None)
    if room is not None and room_is_dark(room) and not keeper.has_affect(AffectFlag.DARK_VISION):
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
        clone = create_object(proto)

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
    # ARITH-115: ROM src/act_obj.c:2747-2748 (do_buy item-shop branch)
    # adds keeper gold/silver raw — no floor.  When `cost` is negative
    # (player-refund branch from a winning haggle on a `profit_buy < 50`
    # shop, see ARITH-111), keeper wealth is allowed to drift negative.
    total = int(total)
    keeper.gold = c_div(total, 100)
    keeper.silver = c_mod(total, 100)


def _character_total_wealth(char: Character) -> int:
    gold = getattr(char, "gold", 0)
    silver = getattr(char, "silver", 0)
    return int(gold) * 100 + int(silver)


def _set_character_total_wealth(char: Character, total: int) -> None:
    # ARITH-115: companion to _set_keeper_total_wealth.  ROM has no
    # floor on raw gold/silver increments; the only safety net is
    # `deduct_cost`'s end-of-function rebalance at src/handler.c:2412-2421,
    # which Python's deduct_cost (mud/handler.py:918-923) already mirrors.
    total = int(total)
    char.gold = c_div(total, 100)
    char.silver = c_mod(total, 100)


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
    if proto is None:
        return 0
    shop = _get_shop(keeper)
    if not shop:
        return 0
    cost = 0
    # GETCOST-001: ROM get_cost (src/act_obj.c:2487,2499) uses the RUNTIME
    # obj->cost, NOT the prototype cost — do_buy clamps obj->cost down to the
    # haggled purchase price (:2765-2766), so resale must price from it.
    obj_cost = int(getattr(obj, "cost", getattr(proto, "cost", 0)) or 0)
    if buy:
        cost = c_div(obj_cost * shop.profit_buy, 100)
    else:
        # ensure shop buys this type
        item_type = int(getattr(proto, "item_type", getattr(obj, "item_type", 0)) or 0)
        if shop.buy_types and item_type not in shop.buy_types:
            return 0
        cost = c_div(obj_cost * shop.profit_sell, 100)
        # inventory discount if keeper already has same item
        obj_descr = (getattr(obj, "short_descr", None) or "").strip().lower()
        for other in getattr(keeper, "inventory", []) or []:
            op = getattr(other, "prototype", None)
            if not op:
                continue
            other_descr = (getattr(other, "short_descr", None) or "").strip().lower()
            if op is proto or (getattr(op, "vnum", None) == getattr(proto, "vnum", None) and other_descr == obj_descr):
                flags = int(getattr(other, "extra_flags", 0) or 0) | int(getattr(op, "extra_flags", 0) or 0)
                if flags & int(ITEM_INVENTORY):
                    cost = c_div(cost, 2)
                else:
                    cost = c_div(cost * 3, 4)
                break

    # Charge scaling for wand/staff
    if int(getattr(proto, "item_type", getattr(obj, "item_type", 0)) or 0) in (int(ItemType.WAND), int(ItemType.STAFF)):
        vals = getattr(proto, "value", getattr(obj, "value", [0, 0, 0, 0, 0]))
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
            # ROM src/act_obj.c:2605 — `cost -= cost / 2 * roll / 100`.
            # `max(0, ...)` is dead defensive code: max discount is
            # `(cost // 2) * 99 // 100 < cost // 2`, so the result is
            # always ≥ cost - cost//2 = cost - cost//2 ≥ 0 for any
            # cost ≥ 0. ARITH-110 reclassed N/A (2.9.73).
            discount = (cost // 2) * roll // 100
            cost = max(0, cost - discount)
            # INV-001 wrong-channel cousin: ROM src/act_obj.c:2606-2607 sends
            # this directly to the descriptor, with mailbox fallback only when
            # disconnected.
            push_message(char, f"You haggle the price down to {cost} coins.")
            check_improve(char, "haggle", True, 4)

    if total_wealth < cost:
        return "You can't afford it."

    proto = getattr(template, "prototype", None)
    if proto is None:
        return "Sorry, you can't buy that here."

    # ROM do_buy (src/act_obj.c:2613): re-create the pet via
    # create_mobile(pet->pIndexData) — a FRESH re-roll from the index
    # (gold -> hp -> mana -> damtype -> sex, src/db.c:2047-2113), NOT a clone of
    # the kennel template's already-rolled runtime fields (SHOP-PET-002). spawn_mob
    # is the create_mobile equivalent and registers the mob in character_registry,
    # so it must not be appended again here.
    pet = spawn_mob(proto.vnum)
    if pet is None:
        # ROM's create_mobile exit(1)s on a bad vnum (no fail-soft path); spawn_mob
        # returns None instead, so guard BEFORE charging. ROM deducts at
        # src/act_obj.c:2612, but only ever reaches a guaranteed-valid index — we
        # must not charge for a pet we could not create.
        return "Sorry, you can't buy that here."

    deduct_cost(char, cost)

    # create_mobile copies name <- player_name and short_descr from the index
    # (src/db.c:2038-2039); from_prototype sets name <- short_descr instead, so
    # restore the ROM keyword name the rename below appends to, plus short_descr.
    pet.name = getattr(proto, "player_name", None) or pet.name
    pet.short_descr = getattr(proto, "short_descr", None)

    # ROM do_buy overrides (src/act_obj.c:2614-2616).
    pet.act |= int(ActFlag.PET)
    pet.add_affect(AffectFlag.CHARM)
    # src/act_obj.c:2616 assigns comm outright; MobInstance has no comm-flag
    # helpers (NPCs key comm as a raw int, as _deserialize_pet restores it).
    pet.comm = int(CommFlag.NOTELL) | int(CommFlag.NOSHOUT) | int(CommFlag.NOCHANNELS)

    rename_token = (rename or "").strip()
    if rename_token:
        base = (pet.name or "").strip()
        pet.name = f"{base} {rename_token}".strip()

    owner_name = char.name or char.short_descr or "someone"
    base_description = pet.description or ""
    if base_description and not base_description.endswith("\n"):
        base_description = f"{base_description}\n"
    pet.description = f"{base_description}A neck tag says 'I belong to {owner_name}'.\n"

    current_room = room
    current_room.add_character(pet)

    add_follower(pet, char)
    pet.leader = char
    char.pet = pet

    # INV-001 (e) SINGLE-DELIVERY: ROM do_buy (src/act_obj.c:2635) sends
    # "Enjoy your pet." once via send_to_char and returns void. The connection
    # loop sends do_buy's return value AND drains char.messages, so this line must
    # live in ONE channel only — return it, do NOT also append it to the mailbox.
    buyer_message = "Enjoy your pet."

    # mirroring ROM src/act_obj.c:2636 — act("$n bought $N as a pet.", ch, NULL,
    # pet, TO_ROOM). INV-025/INV-027: act_to_room renders $n per recipient
    # (invisible buyer → "Someone") and dispatches TRIG_ACT; $N is the pet.
    act_to_room(current_room, "$n bought $N as a pet.", char, arg2=pet)

    return buyer_message


def do_list(char: Character, args: str = "") -> str:
    # LIST-002: pet shop branch (mirrors ROM src/act_obj.c:2777-2815)
    room = getattr(char, "room", None)
    if room is not None and getattr(room, "room_flags", 0) & int(RoomFlag.ROOM_PET_SHOP):
        room_vnum = getattr(room, "vnum", None)
        kennel_vnum = 9706 if room_vnum == 9621 else (room_vnum + 1 if room_vnum is not None else None)
        kennel = room_registry.get(kennel_vnum) if kennel_vnum is not None else None
        if kennel is None:
            return "You can't do that here."
        lines: list[str] = []
        for pet in getattr(kennel, "people", []) or []:
            if not _has_act_flag(pet, ActFlag.PET):
                continue
            level = int(getattr(pet, "level", 0) or 0)
            price = 10 * level * level
            short_descr = getattr(pet, "short_descr", None) or getattr(pet, "name", "a pet")
            lines.append(f"[{level:2d}] {price:8d} - {short_descr}")
        if not lines:
            return "Sorry, we're out of pets right now."
        return "Pets for sale:\n" + "\n".join(lines)

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
        # LIST-003: skip items the keeper is wearing/wielding (ROM line 2831: obj->wear_loc == WEAR_NONE)
        if int(getattr(obj, "wear_loc", int(WearLocation.NONE))) != int(WearLocation.NONE):
            continue
        # LIST-004: ROM line 2831 also gates on can_see_obj(ch, obj) — buyer only
        # (do_list, unlike get_obj_keeper, does NOT check the keeper's visibility).
        if not can_see_object(char, obj):
            continue
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
    # BUY-001: quantity out of range uses keeper voice (ROM line 2655)
    if quantity < 1 or quantity > 99:
        return _keeper_says(keeper, char, "Get real!")
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
        # BUY-007: mirror ROM src/act_obj.c:2459-2460 get_obj_keeper — both the
        # keeper and the buyer must be able to see the object, gated during
        # iteration so the N.name index only counts visible items.
        if not _keeper_can_see_object(keeper, candidate) or not can_see_object(char, candidate):
            continue
        if not _purchase_matches(name, candidate):
            continue
        match_count += 1
        if effective_index is None or match_count < effective_index:
            continue
        selected_obj = candidate
        selected_position = idx
        break

    proto = getattr(selected_obj, "prototype", None) if selected_obj is not None else None

    unit_price = _get_cost(keeper, selected_obj, buy=True) if selected_obj is not None else 0

    # BUY-002: "don't sell that" uses keeper voice (ROM line 2661-2665)
    if selected_obj is None or (unit_price <= 0 and not (proto is None and _is_inventory_item(selected_obj))):
        return _keeper_says(keeper, char, "I don't sell that -- try 'list''.")

    if unit_price <= 0 and proto is None and _is_inventory_item(selected_obj):
        unit_price = 0

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
            # ROM line 2681-2685: keeper voice for insufficient stock
            return _keeper_says(keeper, char, "I don't have that many in stock.")

    total_cost = unit_price * quantity
    # BUY-003: can't afford uses keeper voice (ROM src/act_obj.c:2688-2698)
    # mirroring ROM src/act_obj.c:2688 — afford check precedes level check (BUY-006)
    if _character_total_wealth(char) < total_cost:
        if quantity > 1:
            return _keeper_says(keeper, char, "You can't afford to buy that many.")
        return _keeper_says(keeper, char, "You can't afford to buy $p'.", obj=selected_obj)

    item_level = getattr(proto, "level", getattr(selected_obj, "level", 0))
    char_level = getattr(char, "level", 0)
    if int(char_level) < int(item_level or 0):
        # BUY-003b: level check uses keeper voice (ROM src/act_obj.c:2702-2706)
        if hasattr(char, "reply"):
            char.reply = keeper
        return _keeper_says(keeper, char, "You can't use $p yet'.", obj=selected_obj)

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

    # BUY-005: haggle on buy (ROM src/act_obj.c:2722-2730)
    skills = getattr(char, "skills", {}) or {}
    try:
        haggle_skill = int(skills.get("haggle", 0) or 0)
    except (TypeError, ValueError):
        haggle_skill = 0
    flags = int(getattr(selected_obj, "extra_flags", 0) or 0)
    if haggle_skill > 0 and not (flags & int(ITEM_SELL_EXTRACT)):
        roll = rng_mm.number_percent()
        if roll < haggle_skill:
            # BUY-009: ROM src/act_obj.c:2727 uses the RUNTIME obj->cost, not the
            # prototype cost (diverges once obj.cost has been clamped by a prior
            # haggle, mirroring GETCOST-001).
            base_cost = int(getattr(selected_obj, "cost", getattr(proto, "cost", 0)) or 0)
            discount = c_div(c_div(base_cost, 2) * roll, 100)
            # ROM src/act_obj.c:2727 — `cost -= obj->cost / 2 * roll / 100;`
            # is raw subtraction. When shop.profit_buy < 50, the discount can
            # exceed unit_price and cost goes negative; deduct_cost then
            # refunds the player (ROM src/handler.c:2410). Do not floor at 0.
            unit_price = unit_price - discount
            total_cost = unit_price * quantity
            # INV-001 wrong-channel cousin: ROM src/act_obj.c:2728 delivers
            # the TO_CHAR act line immediately.
            push_message(char, "You haggle with the shopkeeper.")
            check_improve(char, "haggle", True, 4)

    # ROM src/act_obj.c:2734-2745 — broadcast `$n buys $p[N].` or `$n buys $p.`
    # to the room before deducting cost so onlookers see the transaction.
    # INV-025/INV-027: act_to_room renders $n per recipient (invisible buyer →
    # "Someone") and dispatches TRIG_ACT; $p is the item, [N] the literal qty.
    room = getattr(char, "room", None)
    if room is not None:
        if quantity > 1:
            act_to_room(room, f"$n buys $p[{quantity}].", char, arg1=selected_obj)
        else:
            act_to_room(room, "$n buys $p.", char, arg1=selected_obj)

    deduct_cost(char, total_cost)
    # mirroring ROM src/act_obj.c:2747-2748 — keeper gold/silver incremented
    # independently, NOT via a total-wealth rebalance.
    keeper.gold = int(getattr(keeper, "gold", 0)) + total_cost // 100
    keeper.silver = int(getattr(keeper, "silver", 0)) + total_cost % 100

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
        # SELL-001: keeper voice for missing item (ROM line 2892-2896)
        return _keeper_says(keeper, char, "You don't have that item'.")

    if not _can_drop_object(char, selected_obj):
        return "You can't let go of it."

    if not _keeper_can_see_object(keeper, selected_obj):
        # SELL-002: mirroring ROM src/act_obj.c:2905-2908 — act("$n doesn't see what you are offering.", keeper, NULL, ch, TO_VICT)
        return _act_to_char(keeper, "$n doesn't see what you are offering.")

    price = _get_cost(keeper, selected_obj, buy=False)
    if price <= 0:
        # SELL-003: mirroring ROM src/act_obj.c:2911-2914 — act("$n looks uninterested in $p.", keeper, obj, ch, TO_VICT)
        return _act_to_char(keeper, "$n looks uninterested in $p.", obj=selected_obj)
    total_wealth = _keeper_total_wealth(keeper)
    if price > total_wealth:
        # SELL-004: keeper voice with $p substitution (ROM line 2917-2921)
        return _keeper_says(keeper, char, "I'm afraid I don't have enough wealth to buy $p.", obj=selected_obj)

    flags = int(getattr(selected_obj, "extra_flags", 0) or 0)
    skills = getattr(char, "skills", {}) or {}
    try:
        haggle_skill = int(skills.get("haggle", 0) or 0)
    except (TypeError, ValueError):
        haggle_skill = 0
    # mirroring ROM src/act_obj.c:2925 — number_percent() is unconditional; skill gate
    # only controls whether the bonus applies, not whether the RNG call happens.
    roll = rng_mm.number_percent()
    if haggle_skill > 0 and not (flags & int(ITEM_SELL_EXTRACT)) and roll < haggle_skill:
        proto = getattr(selected_obj, "prototype", None)
        base_cost = int(getattr(proto, "cost", getattr(selected_obj, "cost", 0)) or 0)
        bonus = (base_cost // 2) * roll // 100
        price += bonus
        buy_price = _get_cost(keeper, selected_obj, buy=True)
        if buy_price > 0:
            price = min(price, (95 * buy_price) // 100)
        price = min(price, total_wealth)
        # INV-001 wrong-channel cousin: ROM src/act_obj.c:2929 sends this
        # directly to the descriptor.
        push_message(char, "You haggle with the shopkeeper.")
        check_improve(char, "haggle", True, 4)

    # mirroring ROM src/act_obj.c:2923 — act("$n sells $p.", ch, obj, NULL, TO_ROOM).
    # INV-025/INV-027: act_to_room renders $n per recipient (invisible seller →
    # "Someone") and dispatches TRIG_ACT; $p is the item.
    room = getattr(char, "room", None)
    if room is not None:
        act_to_room(room, "$n sells $p.", char, arg1=selected_obj)

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
        # SELL-006: obj_to_keeper dedup — if keeper has ITEM_INVENTORY copy, extract sold obj
        if not _obj_to_keeper(selected_obj, keeper):
            # INV-039 / class-13: ROM obj_to_char head-inserts.
            add_obj = getattr(keeper, "add_object", None)
            if callable(add_obj):
                add_obj(selected_obj)
            else:
                add_inv = getattr(keeper, "add_to_inventory", None)
                if callable(add_inv):
                    add_inv(selected_obj)
                else:
                    inventory = getattr(keeper, "inventory", None)
                    if isinstance(inventory, list):
                        inventory.insert(0, selected_obj)

    # mirroring ROM src/act_obj.c:2938-2939 — gold and silver are incremented
    # independently, NOT via a total-wealth rebalance.  _set_character_total_wealth
    # would fold existing silver into gold (e.g. 200 silver → 2 gold), diverging
    # from ROM which leaves each bucket unchanged except for the sale proceeds.
    silver = price % 100
    gold = price // 100
    char.gold = int(getattr(char, "gold", 0)) + gold
    char.silver = int(getattr(char, "silver", 0)) + silver
    # mirroring ROM src/act_obj.c:2940 — use deduct_cost which subtracts from
    # silver first, then from gold, preserving the gold/silver split rather
    # than rebalancing the full total (_set_keeper_total_wealth would fold all
    # silver into gold, diverging when the keeper holds > 100 silver).
    deduct_cost(keeper, price)
    descriptor = selected_obj.short_descr or selected_obj.name or "item"
    suffix = "" if price == 1 else "s"
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
        # ROM line 2986-2990: keeper voice for missing item
        return _keeper_says(keeper, char, "You don't have that item'.")

    if not _keeper_can_see_object(keeper, selected_obj):
        # VAL-005: ROM src/act_obj.c:2994 — act("$n doesn't see what you are offering.",
        # keeper, NULL, ch, TO_VICT); $n = keeper name (mirrors do_sell SELL-002).
        return _act_to_char(keeper, "$n doesn't see what you are offering.")

    if not _can_drop_object(char, selected_obj):
        return "You can't let go of it."

    price = _get_cost(keeper, selected_obj, buy=False)
    if price <= 0:
        # VAL-005: ROM src/act_obj.c:3007 — act("$n looks uninterested in $p.", keeper,
        # obj, ch, TO_VICT); $n = keeper name, $p = item name (mirrors do_sell SELL-003).
        return _act_to_char(keeper, "$n looks uninterested in $p.", obj=selected_obj)

    # VAL-004: price quote via keeper voice with $p substitution (ROM line 3011-3015)
    silver = price % 100
    gold = price // 100
    keeper_name = getattr(keeper, "short_descr", None) or getattr(keeper, "name", "The shopkeeper")
    obj_name = getattr(selected_obj, "short_descr", None) or getattr(selected_obj, "name", "it") or "it"
    if hasattr(char, "reply"):
        char.reply = keeper
    return capitalize_act_line(
        f"{keeper_name} tells you 'I'll give you {silver} silver and {gold} gold coins for {obj_name}'."
    )
