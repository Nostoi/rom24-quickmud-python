"""Core runtime configuration for the QuickMUD Python port."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Configuration for servers
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///mud.db")
PORT = int(os.getenv("PORT", 5000))
HOST = os.getenv("HOST", "0.0.0.0")

# Comma separated list of allowed CORS origins
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",")]

# ----- ROM tick cadence (PULSE constants) -----
# ROM defines PULSE_PER_SECOND=4 and PULSE_TICK=60*PULSE_PER_SECOND (see src/merc.h)
# Keep these values here so engine code can reference parity timings.
PULSE_PER_SECOND: int = 4


def get_pulse_tick() -> int:
    """Return pulses per game tick hour (ROM PULSE_TICK).

    Matches ROM's PULSE_TICK = 60 * PULSE_PER_SECOND.
    """

    scale = max(1, int(os.getenv("TIME_SCALE", os.getenv("MUD_TIME_SCALE", "1")) or 1))
    # Allow in-test overrides via module variable as well
    try:
        from mud import config as _cfg  # local import to avoid cycles

        scale = max(scale, int(getattr(_cfg, "TIME_SCALE", 1)))
    except Exception:
        pass
    base = 60 * PULSE_PER_SECOND
    # Ensure at least 1 pulse per tick when scaled up
    return max(1, base // scale)


def get_pulse_violence() -> int:
    """Return pulses per violence update (ROM PULSE_VIOLENCE).

    ROM sets PULSE_VIOLENCE = 3 * PULSE_PER_SECOND.
    Honor TIME_SCALE in the same way as ticks by dividing the base.
    """

    scale = max(1, int(os.getenv("TIME_SCALE", os.getenv("MUD_TIME_SCALE", "1")) or 1))
    try:
        from mud import config as _cfg

        scale = max(scale, int(getattr(_cfg, "TIME_SCALE", 1)))
    except Exception:
        pass
    base = 3 * PULSE_PER_SECOND
    return max(1, base // scale)


def get_pulse_area() -> int:
    """Return pulses per area update (ROM PULSE_AREA).

    ROM defines PULSE_AREA = 120 * PULSE_PER_SECOND. Apply TIME_SCALE like
    other cadence helpers so tests can speed up resets deterministically.
    """

    scale = max(1, int(os.getenv("TIME_SCALE", os.getenv("MUD_TIME_SCALE", "1")) or 1))
    try:
        from mud import config as _cfg

        scale = max(scale, int(getattr(_cfg, "TIME_SCALE", 1)))
    except Exception:
        pass
    base = 120 * PULSE_PER_SECOND
    return max(1, base // scale)


def get_pulse_music() -> int:
    """Return pulses per music update (ROM PULSE_MUSIC)."""

    scale = max(1, int(os.getenv("TIME_SCALE", os.getenv("MUD_TIME_SCALE", "1")) or 1))
    try:
        from mud import config as _cfg

        scale = max(scale, int(getattr(_cfg, "TIME_SCALE", 1)))
    except Exception:
        pass
    base = 6 * PULSE_PER_SECOND
    return max(1, base // scale)


# Feature flags
COMBAT_USE_THAC0: bool = False

# Optional test-only time scaling (1 = real ROM cadence)
TIME_SCALE: int = 1

# When True, schedule weather/reset strictly on point pulses (ROM-like).
# Default False to preserve existing test expectations.
GAME_LOOP_STRICT_POINT: bool = False


@dataclass
class QuickmudConfig:
    """Runtime toggles loaded from QuickMUD's ``qmconfig.rc``."""

    ansiprompt: bool = True
    ansicolor: bool = True
    telnetga: bool = True
    ip_address: str = "0.0.0.0"


_CONFIG_PATH = Path(__file__).resolve().parent.parent / "area" / "qmconfig.rc"
_STATE = QuickmudConfig()


def get_qmconfig() -> QuickmudConfig:
    """Return the current QuickMUD configuration snapshot."""

    return _STATE


def set_ansiprompt(value: bool) -> None:
    _update_config(ansiprompt=bool(value))


def set_ansicolor(value: bool) -> None:
    _update_config(ansicolor=bool(value))


def set_telnetga(value: bool) -> None:
    _update_config(telnetga=bool(value))


def set_ip_address(value: str) -> None:
    _update_config(ip_address=str(value))


def load_qmconfig(path: Path | str | None = None) -> QuickmudConfig:
    """Load ``qmconfig.rc`` style data from *path* into the runtime state."""

    target_path = Path(path) if path is not None else _CONFIG_PATH
    if not target_path.exists():
        return get_qmconfig()

    ansiprompt = _STATE.ansiprompt
    ansicolor = _STATE.ansicolor
    telnetga = _STATE.telnetga
    ip_address = _STATE.ip_address

    try:
        with target_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("#") or line.startswith("*"):
                    continue
                comment_index = len(line)
                for marker in ("#", "*"):
                    idx = line.find(marker)
                    if idx != -1:
                        comment_index = min(comment_index, idx)
                if comment_index != len(line):
                    line = line[:comment_index].rstrip()
                if not line:
                    continue
                parts = line.split()
                if not parts:
                    continue
                if parts[0].upper() == "END":
                    break
                if len(parts) < 2:
                    continue
                key = parts[0].lower()
                value_token = parts[1]
                truthy: bool
                try:
                    truthy = int(value_token, 10) != 0
                except ValueError:
                    lowered = value_token.lower()
                    truthy = lowered.startswith("on")

                if key == "ansiprompt":
                    ansiprompt = truthy
                elif key == "ansicolor":
                    ansicolor = truthy
                elif key == "telnetga":
                    telnetga = truthy
                elif key == "ipaddress":
                    ip_address = value_token
    except OSError:
        return get_qmconfig()

    _update_config(
        ansiprompt=ansiprompt,
        ansicolor=ansicolor,
        telnetga=telnetga,
        ip_address=ip_address,
    )
    return get_qmconfig()


def config_path() -> Path:
    """Return the active ``qmconfig.rc`` file path."""

    return _CONFIG_PATH


def set_config_path(path: Path | str) -> None:
    """Override the default ``qmconfig.rc`` path (primarily for tests)."""

    global _CONFIG_PATH
    _CONFIG_PATH = Path(path)


def _update_config(**changes: object) -> None:
    global _STATE
    _STATE = replace(_STATE, **changes)
