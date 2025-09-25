from dataclasses import dataclass, field

from mud.registry import shop_registry

from .base_loader import BaseTokenizer


@dataclass
class Shop:
    """Minimal representation of SHOP_DATA."""

    keeper: int
    buy_types: list[int] = field(default_factory=list)
    profit_buy: int = 100
    profit_sell: int = 100
    open_hour: int = 0
    close_hour: int = 23


def load_shops(tokenizer: BaseTokenizer, area) -> None:
    """Load shop entries and register by keeper vnum."""
    while True:
        line = tokenizer.next_line()
        if line is None:
            break
        line = line.strip()
        if not line or line.startswith("0"):
            break
        parts = line.split()
        keeper = int(parts[0])
        buy_types = [int(p) for p in parts[1:6]]
        profit_buy = int(parts[6]) if len(parts) > 6 else 100
        profit_sell = int(parts[7]) if len(parts) > 7 else 100
        open_hour = int(parts[8]) if len(parts) > 8 else 0
        close_hour = int(parts[9]) if len(parts) > 9 else 23
        shop_registry[keeper] = Shop(
            keeper=keeper,
            buy_types=buy_types,
            profit_buy=profit_buy,
            profit_sell=profit_sell,
            open_hour=open_hour,
            close_hour=close_hour,
        )
