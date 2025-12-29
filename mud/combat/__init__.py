"""Combat engine utilities."""

from .assist import check_assist
from .engine import attack_round, multi_hit
from .messages import dam_message

__all__ = ["attack_round", "check_assist", "dam_message", "multi_hit"]
