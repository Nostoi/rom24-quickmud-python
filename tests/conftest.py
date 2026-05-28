import os
import tempfile

# xdist isolation: give each worker its own SQLite DB file. `mud/db/session.py`
# builds a module-level `engine` from `DATABASE_URL` (default `sqlite:///mud.db`)
# at import time, and several tests call `Base.metadata.drop_all/create_all` on
# it — under `-n auto` concurrent workers sharing one file wipe each other's
# tables. xdist sets `PYTEST_XDIST_WORKER` in each worker subprocess before any
# conftest/test module is imported, so setting the env here (before
# `mud.db.session` is ever imported) binds the engine to a per-worker file.
# Serial runs (`PYTEST_XDIST_WORKER` unset) keep the default and are unaffected.
_xdist_worker = os.environ.get("PYTEST_XDIST_WORKER")
if _xdist_worker and "DATABASE_URL" not in os.environ:
    _worker_db = os.path.join(tempfile.gettempdir(), f"quickmud_test_{_xdist_worker}.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{_worker_db}"

import pytest  # noqa: E402  (must follow the per-worker DATABASE_URL setup above)
from helpers import ensure_can_move as _ensure_can_move_helper  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_descriptor_list():
    """Prevent `registry.descriptor_list` leaking across tests.

    `wiznet()` (mud/wiznet.py) iterates `registry.descriptor_list` when it is
    present and non-empty, otherwise falls back to `character_registry`. Many
    net/wiznet tests set `registry.descriptor_list` directly; if one leaks a
    non-empty list, a later registry-only test (e.g.
    test_logging_admin::test_log_all_notifies_secure_wiznet) silently takes the
    descriptor path and never sees its test character. Snapshot/restore makes
    each test's mutation non-leaking while preserving any module-scoped setup.
    """
    from mud import registry

    had = hasattr(registry, "descriptor_list")
    snapshot = getattr(registry, "descriptor_list", None)
    yield
    if had:
        registry.descriptor_list = snapshot
    elif hasattr(registry, "descriptor_list"):
        delattr(registry, "descriptor_list")


@pytest.fixture(autouse=True)
def _redirect_save_area_list(tmp_path, monkeypatch):
    """Keep OLC `asave` tests from rewriting the repo's `data/areas/area.lst`.

    `mud/olc/save.py:save_area_list` defaults to the relative path
    `data/areas/area.lst`; `cmd_asave` ("list"/"world"/"changed") calls it with
    no argument, so any asave test that doesn't redirect the write clobbers the
    tracked file with the in-memory registry (dropping entries like `test.json`).
    Redirect only the default path to a per-test tmp file; explicit paths (the
    tests that pass `output_file=tmp_path/...`) pass through unchanged. cmd_asave
    re-imports the symbol at call time, so patching the module attribute works.
    """
    import mud.olc.save as _olc_save

    _real_save_area_list = _olc_save.save_area_list
    _default = "data/areas/area.lst"

    def _redirected(output_file=_default):
        if str(output_file) == _default:
            output_file = str(tmp_path / "area.lst")
        return _real_save_area_list(output_file=output_file)

    monkeypatch.setattr(_olc_save, "save_area_list", _redirected)


@pytest.fixture(autouse=True)
def _reset_object_registry():
    """INV-012: object_registry is global mutable state populated by
    spawn_object. Without this fixture, tests that call spawn_object would
    leak instances across the whole suite.
    """
    from mud.models.obj import object_registry

    snapshot = list(object_registry)
    object_registry.clear()
    yield
    object_registry.clear()
    object_registry.extend(snapshot)


@pytest.fixture
def ensure_can_move():
    """Callable fixture to provision movement points on a character-like entity.

    Usage: ensure_can_move(char[, points])
    """
    return _ensure_can_move_helper


@pytest.fixture
def movable_char_factory():
    """Factory fixture that creates a test character with movement set.

    Example:
        ch = movable_char_factory('Tester', 3001, points=200)
    """
    from mud.world import create_test_character

    def _factory(name: str, room_vnum: int, *, points: int = 100):
        ch = create_test_character(name, room_vnum)
        _ensure_can_move_helper(ch, points)
        return ch

    return _factory


@pytest.fixture
def movable_mob_factory():
    """Factory fixture that spawns a mob and ensures it can move.

    Example:
        mob = movable_mob_factory(3000, 3001, points=150)
    """
    from mud.registry import room_registry
    from mud.spawning.mob_spawner import spawn_mob

    def _factory(vnum: int, room_vnum: int, *, points: int = 100):
        mob = spawn_mob(vnum)
        room = room_registry[room_vnum]
        room.add_mob(mob)
        _ensure_can_move_helper(mob, points)
        return mob

    return _factory


@pytest.fixture
def place_object_factory():
    """Factory that places an object in a room.

    Usage:
        obj = place_object_factory(room_vnum=3001, vnum=3031)
        obj = place_object_factory(room_vnum=3001, proto_kwargs={"vnum": 9999, "short_descr": "a stone"})
    """
    from mud.models.obj import ObjIndex
    from mud.models.object import Object
    from mud.registry import room_registry
    from mud.spawning.obj_spawner import spawn_object

    def _factory(*, room_vnum: int, vnum: int | None = None, proto_kwargs: dict | None = None):
        room = room_registry[room_vnum]
        if vnum is not None:
            obj = spawn_object(vnum)
            assert obj is not None
        else:
            proto_kwargs = proto_kwargs or {}
            proto = ObjIndex(**proto_kwargs)
            obj = Object(instance_id=None, prototype=proto)
        room.add_object(obj)
        return obj

    return _factory


@pytest.fixture
def object_factory():
    """Factory that returns an object instance without placing it in a room.

    Usage:
        obj = object_factory({"vnum": 9999, "short_descr": "a stone"})
    """
    from mud.models.obj import ObjIndex
    from mud.models.object import Object

    def _factory(proto_kwargs: dict):
        proto = ObjIndex(**proto_kwargs)
        return Object(instance_id=None, prototype=proto)

    return _factory


@pytest.fixture
def inventory_object_factory():
    """Factory that spawns a ROM object by vnum for inventory use.

    Wraps spawn_object(vnum) for clarity in tests.
    """
    from mud.spawning.obj_spawner import spawn_object

    def _factory(vnum: int):
        obj = spawn_object(vnum)
        assert obj is not None
        return obj

    return _factory


@pytest.fixture
def portal_factory(place_object_factory):
    """Convenience to create a portal object in a room.

    Example:
        portal_factory(3001, to_vnum=3054, closed=True)
    """
    from mud.models.constants import EX_CLOSED, ItemType

    def _factory(
        room_vnum: int,
        *,
        to_vnum: int,
        closed: bool = False,
        gate_flags: int = 0,
        charges: int = 1,
    ):
        flags = EX_CLOSED if closed else 0
        obj = place_object_factory(
            room_vnum=room_vnum,
            proto_kwargs={
                "vnum": 9998,
                "name": "shimmering portal",
                "short_descr": "a shimmering portal",
                "item_type": int(ItemType.PORTAL),
            },
        )
        # ROM portal values: [charges, exit_flags, portal_flags, to_vnum, placeholder]
        values = [charges, flags, gate_flags, to_vnum, 0]
        obj.prototype.value = values.copy()
        if hasattr(obj, "value"):
            obj.value = values.copy()
        return obj

    return _factory
