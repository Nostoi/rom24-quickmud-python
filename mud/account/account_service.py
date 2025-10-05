import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import Final, Iterable, NamedTuple

from mud.db.models import Character, PlayerAccount
from mud.db.session import SessionLocal
from mud.models.classes import (
    ClassType,
    get_player_class as _get_player_class,
    list_player_classes as _list_player_classes,
)
from mud.models.constants import (
    OBJ_VNUM_SCHOOL_DAGGER,
    OBJ_VNUM_SCHOOL_MACE,
    OBJ_VNUM_SCHOOL_SWORD,
    ROOM_VNUM_SCHOOL,
    Sex,
    Stat,
)
from mud.models.races import (
    PcRaceType,
    RaceType,
    get_pc_race as _get_pc_race,
    get_race as _get_race,
    list_playable_races as _list_playable_races,
)
from mud.security import bans
from mud.security.bans import BanFlag
from mud.security.hash_utils import hash_password, verify_password
from mud.skills.groups import get_group, iter_group_names
from mud.world.world_state import (
    is_newlock_enabled,
    is_wizlock_enabled,
)
from mud.utils import rng_mm


class LoginFailureReason(Enum):
    """Reasons an account login can be rejected."""

    ACCOUNT_BANNED = "account_banned"
    HOST_BANNED = "host_banned"
    HOST_NEWBIES = "host_newbies"
    DUPLICATE_SESSION = "duplicate_session"
    WIZLOCK = "wizlock"
    NEWLOCK = "newlock"
    BAD_CREDENTIALS = "bad_credentials"
    UNKNOWN_ACCOUNT = "unknown_account"


class LoginResult(NamedTuple):
    """Outcome of a login attempt."""

    account: PlayerAccount | None
    failure: LoginFailureReason | None


_active_accounts: set[str] = set()

_RESERVED_NAMES = {
    "all",
    "auto",
    "immortal",
    "self",
    "someone",
    "something",
    "the",
    "you",
    "loner",
    "none",
}


_HOMETOWN_CHOICES: Final[tuple[tuple[str, int], ...]] = (
    ("Midgaard", ROOM_VNUM_SCHOOL),
)

_DEFAULT_WEAPONS: Final[tuple[str, ...]] = ("dagger",)

_WEAPON_CHOICES: Final[dict[str, tuple[str, ...]]] = {
    "mage": ("dagger",),
    "cleric": ("mace",),
    "thief": ("dagger", "sword"),
    "warrior": ("sword", "mace"),
}

_WEAPON_VNUMS: Final[dict[str, int]] = {
    "dagger": OBJ_VNUM_SCHOOL_DAGGER,
    "mace": OBJ_VNUM_SCHOOL_MACE,
    "sword": OBJ_VNUM_SCHOOL_SWORD,
}


@dataclass
class CreationSelection:
    """Track ROM-style group selections during nanny customization."""

    race: PcRaceType
    class_type: ClassType
    creation_points: int = field(init=False)
    _class_index: int = field(init=False, repr=False)
    _known_groups: set[str] = field(init=False, repr=False)
    _ordered_groups: list[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.creation_points = int(self.race.points)
        self._class_index = _class_index_for(self.class_type)
        self._known_groups = set()
        self._ordered_groups = []
        self.add_group("rom basics", deduct=False)
        self.add_group(self.class_type.base_group, deduct=False)

    def add_group(self, name: str, *, deduct: bool = True) -> bool:
        """Add a group when the class is allowed to learn it."""

        group = get_group(name)
        if group is None:
            return False

        normalized = group.name.strip().lower()
        if normalized in self._known_groups:
            return False

        cost = group.cost_for_class_index(self._class_index)
        if cost is None:
            return False

        self._known_groups.add(normalized)
        self._ordered_groups.append(group.name)
        if deduct and cost > 0:
            self.creation_points += cost

        for child_name in group.skills:
            child = get_group(child_name)
            if child is not None:
                # Nested groups become known for free once the parent is chosen.
                self.add_group(child.name, deduct=False)

        return True

    def has_group(self, name: str) -> bool:
        return name.strip().lower() in self._known_groups

    def cost_for_group(self, name: str) -> int | None:
        group = get_group(name)
        if group is None:
            return None
        return group.cost_for_class_index(self._class_index)

    def apply_default_group(self) -> None:
        self.add_group(self.class_type.default_group, deduct=True)

    def minimum_creation_points(self) -> int:
        base = int(self.race.points)
        cost = _group_cost_for_class(self.class_type.default_group, self.class_type)
        return base + (cost or 0)

    def train_value(self) -> int:
        if self.creation_points < 40:
            return max(0, (40 - self.creation_points + 1) // 2)
        return 3

    def group_names(self) -> tuple[str, ...]:
        return iter_group_names(self._ordered_groups)


def get_creation_races() -> tuple[PcRaceType, ...]:
    """Return playable races for the nanny creation prompts (ROM order)."""

    return _list_playable_races()


def lookup_creation_race(name: str) -> PcRaceType | None:
    """Lookup PC race metadata by case-insensitive name."""

    return _get_pc_race(name)


def get_race_archetype(name: str) -> RaceType | None:
    """Return base race flags (act/affect/res/etc.) for nanny initialization."""

    return _get_race(name)


def get_creation_classes() -> tuple[ClassType, ...]:
    """Return playable classes for the nanny creation prompts (ROM order)."""

    return _list_player_classes()


def lookup_creation_class(name: str) -> ClassType | None:
    """Lookup playable class metadata by case-insensitive name."""

    return _get_player_class(name)


def get_hometown_choices() -> tuple[tuple[str, int], ...]:
    """Return available hometown options for new characters."""

    return _HOMETOWN_CHOICES


def lookup_hometown(name: str) -> int | None:
    """Lookup hometown room vnum by case-insensitive name."""

    lowered = name.strip().lower()
    for label, vnum in _HOMETOWN_CHOICES:
        if label.lower() == lowered:
            return vnum
    return None


def get_weapon_choices(class_type: ClassType) -> tuple[str, ...]:
    """Return allowable starting weapon names for the class."""

    return _WEAPON_CHOICES.get(class_type.name, _DEFAULT_WEAPONS)


def lookup_weapon_choice(name: str) -> int | None:
    """Map a weapon name from creation prompts to its object vnum."""

    return _WEAPON_VNUMS.get(name.strip().lower())


def sanitize_account_name(username: str) -> str:
    """Trim surrounding whitespace from a submitted account name."""

    return username.strip()


def is_valid_account_name(username: str) -> bool:
    """Return True when the candidate matches ROM's `check_parse_name`."""

    candidate = sanitize_account_name(username)
    if not candidate:
        return False

    lowered = candidate.lower()
    if lowered in _RESERVED_NAMES:
        return False

    capitalized = candidate.capitalize()
    if capitalized != "Alander" and (
        capitalized.startswith("Alan") or capitalized.endswith("Alander")
    ):
        return False

    if len(candidate) < 2 or len(candidate) > 12:
        return False

    f_ill = True
    adjcaps = False
    cleancaps = False
    total_caps = 0
    for char in candidate:
        if not char.isalpha():
            return False
        if char.isupper():
            if adjcaps:
                cleancaps = True
            total_caps += 1
            adjcaps = True
        else:
            adjcaps = False
        if char.lower() not in {"i", "l"}:
            f_ill = False

    if f_ill:
        return False

    if cleancaps or (total_caps > len(candidate) // 2 and len(candidate) < 3):
        return False

    return True


def _normalize(username: str) -> str:
    return username.strip().lower()


def account_exists(username: str) -> bool:
    """Return True if the account name already exists."""

    username = sanitize_account_name(username)
    if not username:
        return False
    session = SessionLocal()
    try:
        return session.query(PlayerAccount).filter_by(username=username).first() is not None
    finally:
        session.close()


def roll_creation_stats(race: PcRaceType) -> list[int]:
    """Roll candidate stats within the race's base/max range (ROM style)."""

    stats: list[int] = []
    for idx in range(len(race.base_stats)):
        base = race.base_stats[idx]
        maximum = race.max_stats[idx]
        if maximum <= base:
            stats.append(base)
        else:
            bonus = rng_mm.number_range(0, maximum - base)
            stats.append(base + bonus)
    return stats


def _clamp_stats_to_race(stats: Iterable[int], race: PcRaceType) -> list[int]:
    values = [int(val) for val in stats]
    clamped: list[int] = []
    for idx, base in enumerate(race.base_stats):
        maximum = race.max_stats[idx]
        value = values[idx] if idx < len(values) else base
        value = max(base, min(value, maximum))
        clamped.append(value)
    return clamped


def finalize_creation_stats(
    race: PcRaceType, class_type: ClassType, stats: Iterable[int]
) -> list[int]:
    """Clamp rolled stats to race bounds and apply the class prime bonus."""

    clamped = _clamp_stats_to_race(stats, race)
    prime_index = int(class_type.prime_stat)
    if 0 <= prime_index < len(clamped):
        maximum = race.max_stats[prime_index]
        clamped[prime_index] = min(clamped[prime_index] + 3, maximum)
    return clamped


def _race_index_for(race: PcRaceType) -> int:
    for idx, entry in enumerate(get_creation_races()):
        if entry.name == race.name:
            return idx
    return 0


def _class_index_for(class_type: ClassType) -> int:
    for idx, entry in enumerate(get_creation_classes()):
        if entry.name == class_type.name:
            return idx
    return 0


def _group_cost_for_class(name: str, class_type: ClassType) -> int | None:
    group = get_group(name)
    if group is None:
        return None
    return group.cost_for_class_index(_class_index_for(class_type))


def _mark_account_active(username: str) -> None:
    _active_accounts.add(_normalize(username))


def release_account(username: str) -> None:
    """Clear the active-session marker for this account."""

    _active_accounts.discard(_normalize(username))


def clear_active_accounts() -> None:
    """Reset all active-session markers (test helper)."""

    _active_accounts.clear()


def active_accounts() -> Iterable[str]:
    """Return a snapshot of active account usernames (lowercased)."""

    return tuple(_active_accounts)


def _is_account_active(username: str) -> bool:
    return _normalize(username) in _active_accounts


def is_account_active(username: str) -> bool:
    """Return True when the account currently has an active session."""

    return _is_account_active(username)


def create_account(username: str, raw_password: str) -> bool:
    """Create a new PlayerAccount if username is available."""
    username = sanitize_account_name(username)
    if not is_valid_account_name(username):
        return False
    if is_newlock_enabled():
        return False
    session = SessionLocal()
    if session.query(PlayerAccount).filter_by(username=username).first():
        session.close()
        return False
    account = PlayerAccount(
        username=username,
        password_hash=hash_password(raw_password),
    )
    session.add(account)
    session.commit()
    session.close()
    return True


def login(username: str, raw_password: str) -> PlayerAccount | None:
    """Return PlayerAccount if credentials match."""
    username = sanitize_account_name(username)
    if not username:
        return None
    # Enforce account-name bans irrespective of host.
    if bans.is_account_banned(username):
        return None
    session = SessionLocal()
    account = session.query(PlayerAccount).filter_by(username=username).first()
    if account and verify_password(raw_password, account.password_hash):
        # pre-load characters before detaching
        _ = account.characters  # type: ignore[unused-any]
        session.expunge(account)
        session.close()
        return account
    session.close()
    return None


def login_with_host(
    username: str,
    raw_password: str,
    host: str | None,
    *,
    allow_reconnect: bool = False,
) -> LoginResult:
    """Login that also enforces site bans.

    Returns a :class:`LoginResult` detailing the authenticated account (if
    successful) or the reason the attempt failed so callers can mirror ROM's
    nanny prompts.
    """

    username = sanitize_account_name(username)
    if not is_valid_account_name(username):
        return LoginResult(None, LoginFailureReason.UNKNOWN_ACCOUNT)

    if bans.is_account_banned(username):
        return LoginResult(None, LoginFailureReason.ACCOUNT_BANNED)

    was_active = _is_account_active(username)
    if was_active and not allow_reconnect:
        return LoginResult(None, LoginFailureReason.DUPLICATE_SESSION)

    permit_host = bool(host and bans.is_host_banned(host, BanFlag.PERMIT))
    if host and not permit_host and bans.is_host_banned(host, BanFlag.ALL):
        return LoginResult(None, LoginFailureReason.HOST_BANNED)

    session = SessionLocal()
    account_record: PlayerAccount | None = None
    exists = False
    is_admin = False
    password_valid = False
    try:
        account_record = session.query(PlayerAccount).filter_by(username=username).first()
        if account_record:
            exists = True
            is_admin = bool(getattr(account_record, "is_admin", False))
            password_valid = verify_password(raw_password, account_record.password_hash)
            if password_valid:
                # Preload related characters before detaching.
                _ = account_record.characters  # type: ignore[unused-any]
                session.expunge(account_record)
    finally:
        session.close()

    if host and not permit_host and not exists and bans.is_host_banned(host, BanFlag.NEWBIES):
        return LoginResult(None, LoginFailureReason.HOST_NEWBIES)
    if is_newlock_enabled() and not exists:
        return LoginResult(None, LoginFailureReason.NEWLOCK)
    if is_wizlock_enabled() and not is_admin and not (allow_reconnect and was_active):
        return LoginResult(None, LoginFailureReason.WIZLOCK)

    account: PlayerAccount | None = None
    if password_valid and account_record is not None:
        account = account_record

    if account:
        if was_active:
            release_account(username)
        _mark_account_active(username)
        return LoginResult(account, None)

    failure = (
        LoginFailureReason.BAD_CREDENTIALS if exists else LoginFailureReason.UNKNOWN_ACCOUNT
    )
    return LoginResult(None, failure)


def list_characters(account: PlayerAccount) -> list[str]:
    """Return list of character names for this account."""
    return [char.name for char in getattr(account, "characters", [])]


def create_character(
    account: PlayerAccount,
    name: str,
    *,
    race: PcRaceType | None = None,
    class_type: ClassType | None = None,
    race_archetype: RaceType | None = None,
    sex: Sex | int | None = None,
    hometown_vnum: int | None = None,
    perm_stats: Iterable[int] | None = None,
    alignment: int = 0,
    practice: int | None = None,
    train: int | None = None,
    default_weapon_vnum: int | None = None,
    creation_points: int | None = None,
    creation_groups: Iterable[str] | None = None,
    starting_room_vnum: int = ROOM_VNUM_SCHOOL,
) -> bool:
    """Create a new character for the account with ROM creation metadata."""

    sanitized = sanitize_account_name(name)
    if not is_valid_account_name(sanitized):
        return False

    selected_race = race or get_creation_races()[0]
    selected_class = class_type or get_creation_classes()[0]
    archetype = race_archetype or _get_race(selected_race.name)
    stats_source = perm_stats if perm_stats is not None else selected_race.base_stats
    finalized_stats = finalize_creation_stats(selected_race, selected_class, stats_source)

    try:
        sex_value = int(sex) if sex is not None else int(Sex.MALE)
    except (TypeError, ValueError):
        sex_value = int(Sex.MALE)

    hometown = hometown_vnum if hometown_vnum is not None else starting_room_vnum
    weapon_vnum = (
        int(default_weapon_vnum)
        if default_weapon_vnum is not None
        else selected_class.first_weapon_vnum
    )
    default_groups = iter_group_names(
        (
            "rom basics",
            selected_class.base_group,
            selected_class.default_group,
        )
    )
    groups_tuple = (
        iter_group_names(creation_groups)
        if creation_groups is not None
        else default_groups
    )
    default_points = int(selected_race.points) + (
        _group_cost_for_class(selected_class.default_group, selected_class) or 0
    )
    creation_points_value = (
        int(creation_points)
        if creation_points is not None
        else default_points
    )
    practice_value = practice if practice is not None else 5
    train_value = train if train is not None else 3

    session = SessionLocal()
    try:
        if session.query(Character).filter_by(name=sanitized).first():
            return False

        new_char = Character(
            name=sanitized.capitalize(),
            level=1,
            hp=100,
            room_vnum=starting_room_vnum,
            race=_race_index_for(selected_race),
            ch_class=_class_index_for(selected_class),
            sex=sex_value,
            alignment=alignment,
            hometown_vnum=hometown,
            perm_stats=json.dumps([int(val) for val in finalized_stats]),
            size=int(selected_race.size),
            form=int(archetype.form_flags) if archetype else 0,
            parts=int(archetype.part_flags) if archetype else 0,
            imm_flags=int(archetype.immunity_flags) if archetype else 0,
            res_flags=int(archetype.resistance_flags) if archetype else 0,
            vuln_flags=int(archetype.vulnerability_flags) if archetype else 0,
            practice=int(practice_value),
            train=int(train_value),
            default_weapon_vnum=weapon_vnum,
            creation_points=int(creation_points_value),
            creation_groups=json.dumps(list(groups_tuple)),
            player_id=account.id,
        )
        session.add(new_char)
        session.commit()
        return True
    finally:
        session.close()
