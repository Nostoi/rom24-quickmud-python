from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .character import Character
    from .room import Room

from .constants import WearLocation
from .obj import Affect, ObjIndex


@dataclass
class Object:
    """Instance of an object tied to a prototype."""

    instance_id: int | None
    prototype: ObjIndex
    contained_items: list[Object] = field(default_factory=list)
    level: int = 0
    value: list[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])
    timer: int = 0
    wear_loc: int = int(WearLocation.NONE)
    cost: int = 0
    extra_flags: int = 0
    wear_flags: int = 0
    condition: int | str = 0
    enchanted: bool = False
    item_type: str | None = None
    owner: str | None = None
    affected: list[Affect] = field(default_factory=list)
    # ROM-faithful container fields (INV-012). Initially None; populated by
    # spawn / obj_to_room / obj_to_char / obj_to_obj at runtime.
    # compare=False prevents __eq__ recursion through Room/Object/Character graphs.
    in_room: Room | None = field(default=None, compare=False)  # ROM: ROOM_INDEX_DATA *in_room
    in_obj: Object | None = field(default=None, compare=False)  # ROM: OBJ_DATA *in_obj (container)
    carried_by: Character | None = field(default=None, compare=False)  # ROM: CHAR_DATA *carried_by
    _short_descr_override: str | None = field(default=None, repr=False)
    _description_override: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Mirror prototype defaults onto the instance.

        ROM Reference: src/db.c:create_object — instance copies extra_flags,
        wear_flags, level, value, weight, etc. from the prototype unless the
        spawner has already supplied an override. Tests that build Object
        instances directly (without going through the spawner) rely on this
        sync so flags like ITEM_NOREMOVE / ITEM_NODROP are honored.
        """
        proto = self.prototype
        if proto is None:
            return
        if not self.extra_flags:
            proto_extra = getattr(proto, "extra_flags", 0)
            try:
                self.extra_flags = int(proto_extra) if proto_extra else 0
            except (TypeError, ValueError):
                self.extra_flags = 0
        if not self.wear_flags:
            proto_wear = getattr(proto, "wear_flags", 0)
            try:
                self.wear_flags = int(proto_wear) if proto_wear else 0
            except (TypeError, ValueError):
                self.wear_flags = 0
        if self.item_type is None:
            proto_item_type = getattr(proto, "item_type", None)
            if proto_item_type is not None:
                self.item_type = proto_item_type

    @property
    def name(self) -> str | None:
        return self.prototype.name

    @property
    def short_descr(self) -> str | None:
        if self._short_descr_override is not None:
            return self._short_descr_override
        return getattr(self.prototype, "short_descr", None)

    @short_descr.setter
    def short_descr(self, value: str | None) -> None:
        self._short_descr_override = value

    @property
    def description(self) -> str | None:
        if self._description_override is not None:
            return self._description_override
        return getattr(self.prototype, "description", None)

    @description.setter
    def description(self, value: str | None) -> None:
        self._description_override = value

    # ROM-faithful prototype accessor (INV-012). Same backing field as
    # `prototype`; no duplicate storage.
    @property
    def pIndexData(self) -> ObjIndex:
        return self.prototype

    @pIndexData.setter
    def pIndexData(self, value: ObjIndex) -> None:
        self.prototype = value

    # ROM-faithful contents accessor (INV-012). Same backing list as
    # `contained_items`; no setter — callers mutate the list in place.
    @property
    def contains(self) -> list[Object]:
        return self.contained_items

    # INV-013 OBJECT-LOCATION-COHERENCE. `location` is a polymorphic
    # accessor dispatching to the three ROM-faithful container fields
    # (`in_room`, `carried_by`, `in_obj`). ROM keeps these mutually
    # exclusive — see src/handler.c obj_to_room/obj_to_char/obj_to_obj
    # (each sets one and clears the other two).
    @property
    def location(self) -> Room | Character | Object | None:
        return self.in_room or self.carried_by or self.in_obj

    @location.setter
    def location(self, value: Room | Character | Object | None) -> None:
        from .character import Character as _Character
        from .room import Room as _Room

        if value is None:
            self.in_room = None
            self.carried_by = None
            self.in_obj = None
        elif isinstance(value, _Room):
            self.in_room = value
            self.carried_by = None
            self.in_obj = None
        elif isinstance(value, _Character):
            self.carried_by = value
            self.in_room = None
            self.in_obj = None
        elif isinstance(value, Object):
            self.in_obj = value
            self.in_room = None
            self.carried_by = None
        else:
            # Unknown type — preserve legacy permissive write to in_room
            # so callers that pass exotic placeholders (e.g. -1) still
            # mutate something rather than silently failing. Surface as
            # in_room since that was the legacy field's nominal type.
            self.in_room = value  # type: ignore[assignment]
            self.carried_by = None
            self.in_obj = None
