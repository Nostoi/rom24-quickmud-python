from __future__ import annotations

from dataclasses import dataclass, field

from .shop_json import ShopJson


@dataclass
class Shop:
    """Runtime representation of a shop."""

    keeper: int
    buy_types: list[str] = field(default_factory=list)
    profit_buy: int = 100
    profit_sell: int = 100
    open_hour: int = 0
    close_hour: int = 23

    @classmethod
    def from_json(cls, data: ShopJson) -> Shop:
        return cls(**data.to_dict())
