from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import os


@dataclass(frozen=True)
class IMCChannel:
    """Snapshot of an IMC channel entry from `imc.channels`."""

    name: str
    local_name: str
    level: Optional[int]
    reg_format: str
    emote_format: str
    social_format: str


@dataclass(frozen=True)
class IMCHelp:
    """Single IMC help entry loaded from `imc.help`."""

    name: str
    permission: str
    text: str


@dataclass
class IMCState:
    """Runtime IMC state used by the Python port."""

    config: Dict[str, str]
    channels: List[IMCChannel]
    helps: Dict[str, IMCHelp]
    connected: bool
    config_path: Path
    channels_path: Path
    help_path: Path
    idle_pulses: int = 0


_state: Optional[IMCState] = None

_REQUIRED_CONFIG_FIELDS = {
    "LocalName",
    "ServerAddr",
    "ServerPort",
    "ClientPwd",
    "ServerPwd",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_imc_dir() -> Path:
    return _repo_root() / "imc"


def _resolve_path(env_name: str, default_filename: str) -> Path:
    override = os.getenv(env_name)
    if override:
        return Path(override)
    return _default_imc_dir() / default_filename


def _parse_config(path: Path) -> Dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(path)

    config: Dict[str, str] = {}
    with path.open(encoding="latin-1") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line == "End":
                break
            if line.startswith("$"):
                # IMC Freedom exports sometimes wrap config in $IMCCONFIG/$END.
                continue
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                continue
            key, value = parts
            config[key] = value.strip()

    missing = sorted(field for field in _REQUIRED_CONFIG_FIELDS if not config.get(field))
    if missing:
        raise ValueError(f"IMC configuration missing required fields: {', '.join(missing)}")

    return config


def _parse_channels(path: Path) -> List[IMCChannel]:
    if not path.exists():
        return []

    channels: List[IMCChannel] = []
    current: Dict[str, str] = {}

    def finalize() -> None:
        if "ChanName" not in current:
            return
        level_value = current.get("ChanLevel")
        try:
            level = int(level_value) if level_value is not None else None
        except ValueError:
            level = None
        channels.append(
            IMCChannel(
                name=current.get("ChanName", ""),
                local_name=current.get("ChanLocal", current.get("ChanName", "")),
                level=level,
                reg_format=current.get("ChanRegF", ""),
                emote_format=current.get("ChanEmoF", ""),
                social_format=current.get("ChanSocF", ""),
            )
        )

    with path.open(encoding="latin-1") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            upper = line.upper()
            if upper.startswith("#"):
                if upper == "#END":
                    break
                if upper in {"#IMCCHAN", "#CHANNEL"}:
                    finalize()
                    current = {}
                continue
            if line == "End":
                finalize()
                current = {}
                continue
            key, *value = line.split(maxsplit=1)
            current[key] = value[0].strip() if value else ""

    finalize()
    return channels


def _parse_helps(path: Path) -> Dict[str, IMCHelp]:
    if not path.exists():
        return {}

    helps: Dict[str, IMCHelp] = {}
    name: Optional[str] = None
    permission: str = ""
    text_lines: List[str] = []
    capturing_text = False

    def flush() -> None:
        nonlocal name, permission, text_lines, capturing_text
        if name:
            helps[name.lower()] = IMCHelp(name=name, permission=permission, text="\n".join(text_lines).strip())
        name = None
        permission = ""
        text_lines = []
        capturing_text = False

    with path.open(encoding="latin-1") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            stripped = line.strip()
            if not stripped and capturing_text:
                text_lines.append("")
                continue
            if stripped.startswith("#"):
                upper = stripped.upper()
                if upper == "#HELP":
                    flush()
                elif upper == "#END":
                    break
                continue
            if stripped == "End":
                flush()
                continue
            if stripped.startswith("Name "):
                name = stripped[5:].strip()
                continue
            if stripped.startswith("Perm "):
                permission = stripped[5:].strip()
                continue
            if stripped.startswith("Text "):
                text_lines = [stripped[5:].rstrip()]
                capturing_text = True
                continue
            if capturing_text:
                text_lines.append(line.rstrip("\n"))

    flush()
    return helps


def imc_enabled() -> bool:
    """Feature flag for IMC. Disabled by default."""

    return os.getenv("IMC_ENABLED", "false").lower() in {"1", "true", "yes"}


def reset_state() -> None:
    """Helper for tests to clear cached IMC state."""

    global _state
    _state = None


def get_state() -> Optional[IMCState]:
    return _state


def maybe_open_socket(force_reload: bool = False) -> Optional[IMCState]:
    """Load configuration tables when IMC is enabled."""

    if not imc_enabled():
        return None

    global _state

    config_path = _resolve_path("IMC_CONFIG_PATH", "imc.config")
    channels_path = _resolve_path("IMC_CHANNELS_PATH", "imc.channels")
    help_path = _resolve_path("IMC_HELP_PATH", "imc.help")

    if (
        _state
        and _state.connected
        and not force_reload
        and _state.config_path == config_path
        and _state.channels_path == channels_path
        and _state.help_path == help_path
    ):
        return _state

    config = _parse_config(config_path)
    channels = _parse_channels(channels_path)
    helps = _parse_helps(help_path)

    idle_pulses = _state.idle_pulses if _state else 0
    _state = IMCState(
        config=config,
        channels=channels,
        helps=helps,
        connected=True,
        config_path=config_path,
        channels_path=channels_path,
        help_path=help_path,
        idle_pulses=idle_pulses,
    )
    return _state


def pump_idle() -> None:
    """Mirror ROM's imc_loop() idle pump by tracking pulse cadence."""

    if not imc_enabled():
        return

    state = maybe_open_socket()
    if not state:
        return
    state.idle_pulses += 1
