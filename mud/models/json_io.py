from __future__ import annotations

import json
from dataclasses import MISSING, asdict, fields, is_dataclass
from typing import Any, TypeVar, cast, get_args, get_origin, get_type_hints

T = TypeVar("T")
JsonT = TypeVar("JsonT", bound="JsonDataclass")


def _convert_value(annotation, value):
    origin = get_origin(annotation)
    if is_dataclass(annotation):
        return dataclass_from_dict(annotation, value)
    if origin is list:
        (item_type,) = get_args(annotation)
        return [_convert_value(item_type, v) for v in value]
    if origin is dict:
        key_type, val_type = get_args(annotation)
        # assume keys are primitive; only convert values
        return {k: _convert_value(val_type, v) for k, v in value.items()}
    return value


def dataclass_from_dict(cls: type[T], data: dict) -> T:
    """Instantiate ``cls`` from ``data`` applying dataclass defaults."""
    kwargs = {}
    hints = get_type_hints(cls)
    for f in fields(cast(Any, cls)):
        ann = hints.get(f.name, f.type)
        if f.name in data:
            kwargs[f.name] = _convert_value(ann, data[f.name])
        elif f.default is not MISSING:
            kwargs[f.name] = f.default
        elif f.default_factory is not MISSING:  # type: ignore[attr-defined]
            kwargs[f.name] = f.default_factory()  # type: ignore[misc]
    return cls(**kwargs)  # type: ignore[arg-type]


def dataclass_to_dict(obj: Any) -> dict:
    """Convert ``obj`` into a JSON-serializable ``dict``."""
    return asdict(obj)


def load_dataclass(cls: type[T], fp) -> T:
    """Load ``cls`` from a JSON file-like object."""
    data = json.load(fp)
    return dataclass_from_dict(cls, data)


def dump_dataclass(obj: Any, fp, **json_kwargs) -> None:
    """Dump dataclass instance ``obj`` to ``fp`` as JSON."""
    json.dump(dataclass_to_dict(obj), fp, **json_kwargs)


class JsonDataclass:
    """Mixin adding ``to_dict``/``from_dict`` helpers to dataclasses."""

    def to_dict(self) -> dict:
        return dataclass_to_dict(self)

    @classmethod
    def from_dict(cls: type[JsonT], data: dict) -> JsonT:
        return dataclass_from_dict(cls, data)
