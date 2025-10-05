from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from mud.models.constants import OHELPS_FILE
from mud.wiznet import WiznetFlag, wiznet

if TYPE_CHECKING:  # pragma: no cover - import for type checking only
    from mud.models.character import Character


_LOG_ALL = False
_ORPHANED_HELPS_PATH = Path("log") / OHELPS_FILE


_CONTROL_CHAR_ORDS = set(range(0x00, 0x20))
_CONTROL_CHAR_ORDS.add(0x7F)
_SANITIZE_TRANSLATION = {ord("$"): "S"}
_SANITIZE_TRANSLATION.update(dict.fromkeys(_CONTROL_CHAR_ORDS, " "))


def is_log_all_enabled() -> bool:
    """Return True when the global `log all` flag is active."""

    return _LOG_ALL


def set_log_all(enabled: bool) -> None:
    """Force the global `log all` flag to a specific state (test helper)."""

    global _LOG_ALL
    _LOG_ALL = bool(enabled)


def toggle_log_all() -> bool:
    """Flip the global `log all` flag and return the new state."""

    global _LOG_ALL
    _LOG_ALL = not _LOG_ALL
    return _LOG_ALL


def _count_edge_control_chars(command_line: str, *, reverse: bool = False) -> int:
    iterator = reversed(command_line) if reverse else command_line
    count = 0
    for char in iterator:
        if ord(char) in _CONTROL_CHAR_ORDS:
            count += 1
            continue
        break
    return count


def _sanitize_command_line(command_line: str) -> str:
    """Mirror ROM's `smash_dollar` while trimming only control-character artifacts."""

    sanitized = command_line.translate(_SANITIZE_TRANSLATION)

    leading_controls = _count_edge_control_chars(command_line)
    trailing_controls = _count_edge_control_chars(command_line, reverse=True)

    if leading_controls:
        sanitized = sanitized[leading_controls:]
    if trailing_controls:
        sanitized = sanitized[:-trailing_controls] if trailing_controls < len(sanitized) else ""

    return sanitized


def _duplicate_wiznet_chars(text: str) -> str:
    """Duplicate ROM color sentinels (`$`, `{`) for wiznet parity."""

    duplicated: list[str] = []
    for char in text:
        duplicated.append(char)
        if char in {"$", "{"}:
            duplicated.append(char)
    return "".join(duplicated)


def _get_effective_trust(character: "Character") -> int:
    """Mirror ROM's ``get_trust`` helper used for wiznet broadcasts."""

    trust = getattr(character, "trust", 0)
    return trust if trust > 0 else getattr(character, "level", 0)


def log_admin_command(
    actor: str,
    command_line: str,
    *,
    character: "Character" | None = None,
) -> None:
    """Append a single admin-command entry to log/admin.log.

    Format: ISO timestamp, actor, sanitized command line.
    Creates the log directory if missing.
    """

    Path("log").mkdir(exist_ok=True)
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    sanitized = _sanitize_command_line(command_line)
    if character is not None:
        try:
            wiznet(
                _duplicate_wiznet_chars(f"Log {actor}: {sanitized}"),
                character,
                None,
                WiznetFlag.WIZ_SECURE,
                None,
                _get_effective_trust(character),
            )
        except Exception:
            # Wiznet notifications must never break logging.
            pass
    log_path = Path("log") / "admin.log"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp}\t{actor}\t{sanitized}\n")


def rotate_admin_log(today: datetime | None = None) -> Path:
    """Rotate admin.log to a date-stamped file once per (real) day.

    - If ``log/admin.log`` exists, rename it to ``log/admin-YYYYMMDD.log``.
    - Always return the new active path (``log/admin.log``).
    The ``today`` parameter allows tests to inject a deterministic date.
    """
    log_dir = Path("log")
    log_dir.mkdir(exist_ok=True)
    active = log_dir / "admin.log"
    if not active.exists():
        return active
    dt = today or datetime.now(UTC)
    dated = log_dir / f"admin-{dt.strftime('%Y%m%d')}.log"
    # Avoid clobbering: if dated file exists, append current log and remove active
    if dated.exists():
        content = active.read_text(encoding="utf-8")
        with dated.open("a", encoding="utf-8") as destination:
            destination.write(content)
        active.unlink()
    else:
        active.rename(dated)
    # Create a fresh active log file
    active.touch()
    return active


def log_orphan_help_request(character: Character, topic: str) -> None:
    """Append an unmet help request to the orphaned helps log.

    Mirrors ROM's ``append_file`` helper by recording the caller's room vnum
    alongside their name so staff can fill in missing documentation topics.
    NPC requests and blank topics are ignored to match the original guard.
    """

    if not topic:
        return
    if getattr(character, "is_npc", True):
        return
    Path("log").mkdir(exist_ok=True)
    room = getattr(character, "room", None)
    room_vnum = getattr(room, "vnum", 0) or 0
    name = getattr(character, "name", "unknown") or "unknown"
    with _ORPHANED_HELPS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"[{room_vnum:5d}] {name}: {topic}\n")
